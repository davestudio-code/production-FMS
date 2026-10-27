import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, send_from_directory
from decimal import Decimal, InvalidOperation
from datetime import date, timedelta
from psycopg2.errors import UniqueViolation
from .db import openTransaction
from .auth import (
    authenticate_credentials,
    login_required,
    manager_required,
    is_manager_session,
    is_staff_session,
    sync_and_verify_session,
    clear_employee_verify_cache,
    MANAGER_POSITION_ID
)
from .models.furniture import Furniture
from .models.material import Material
from .models.billofmaterials import BillOfMaterials
from .models.bomitem import BOMItem
from .models.productionorder import ProductionOrder
from .models.materialissuance import MaterialIssuance
from .models.monitoring import ProductionMonitoring
from .models.productionoutput import ProductionOutput
from .models.productioncost import ProductionCost
from .models.workflow import (
    ProductionAttachment,
    uploadToSupabaseStorage,
    getLiveNotificationsForUser,
    getProductionStaffRoster,
    isValidActiveProdStaff
)
from . import integration
from .cache import clearAllCache, invalidateKeys

productionBlueprint = Blueprint(
    "production",
    __name__,
    template_folder="templates",
    static_folder="static"
)

@productionBlueprint.app_template_filter("date_fmt")
def dateFmtFilter(val):
    if not val:
        return ""
    if hasattr(val, "strftime"):
        return val.strftime("%b. %d, %Y")
    try:
        from datetime import datetime, date
        s = str(val).strip()
        if "T" in s or " " in s:
            return datetime.fromisoformat(s).strftime("%b. %d, %Y")
        return date.fromisoformat(s).strftime("%b. %d, %Y")
    except Exception:
        return str(val)

@productionBlueprint.before_request
def requireLogin():
    if request.endpoint in ("production.login", "production.logout", "production.static", "production.loginpageStatic", "production.featureStatic"):
        return
    if not session.get("user_id"):
        return redirect(url_for("production.login", next=request.path))
    if not sync_and_verify_session():
        session.clear()
        flash("Access restricted to active Production Department Managers and Production Staff.", "warning")
        return redirect(url_for("production.login"))

@productionBlueprint.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id") and sync_and_verify_session():
        return redirect(url_for("production.index"))
    session.clear()
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        user_record, error_message = authenticate_credentials(email, password)
        if error_message:
            if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.is_json:
                return jsonify({"success": False, "error": error_message}), 401
            flash(error_message, "danger")
            return render_template("production/loginpage/login.html")
        emp_id = int(user_record["employee_id"])
        dept_id = int(user_record["department_id"])
        pos_id = int(user_record["position_id"])
        session["user_id"] = user_record.get("user_id") or emp_id or str(user_record.get("auth_user_id"))
        session["employee_id"] = emp_id
        session["department_id"] = dept_id
        session["position_id"] = pos_id
        session["email"] = user_record.get("email")
        name = user_record.get("name") or ""
        last_name = user_record.get("last_name") or ""
        full_name = f"{name} {last_name}".strip()
        session["employee_name"] = full_name if full_name else user_record.get("email")
        session["position"] = user_record.get("position_name") or ("Manager" if pos_id == MANAGER_POSITION_ID else "Production Staff")
        clear_employee_verify_cache(emp_id)
        flash(f"Welcome back, {session['employee_name']}!", "success")
        next_page = request.args.get("next")
        next_url = next_page if (next_page and next_page.startswith("/production") and not next_page.startswith("/production/logout") and not next_page.startswith("/production/login")) else url_for("production.index")
        if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.is_json:
            return jsonify({"success": True, "redirect": next_url, "user": session["employee_name"]}), 200
        return redirect(next_url)
    return render_template("production/loginpage/login.html")

@productionBlueprint.route("/feature-static/<path:filename>")
def featureStatic(filename):
    folder = os.path.join(os.path.dirname(__file__), "templates", "production")
    return send_from_directory(folder, filename)

@productionBlueprint.route("/loginpage-static/<path:filename>")
def loginpageStatic(filename):
    folder = os.path.join(os.path.dirname(__file__), "templates", "production", "loginpage")
    return send_from_directory(folder, filename)

@productionBlueprint.route("/logout")
def logout():
    clear_employee_verify_cache(session.get("employee_id"))
    session.clear()
    flash("You have been signed out successfully.", "info")
    return redirect(url_for("production.login"))

@productionBlueprint.route("/refresh", methods=["POST", "GET"])
def refreshCache():
    clearAllCache()
    clear_employee_verify_cache()
    if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.is_json:
        return jsonify({"status": "success", "message": "Live database synchronized."})
    flash("Live database synchronized.", "success")
    return redirect(request.referrer or url_for("production.index"))

def getDatabaseStatus():
    try:
        with openTransaction() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                return None
    except Exception as connectionError:
        return f"Database Offline: {str(connectionError)}"

@productionBlueprint.context_processor
def injectGlobalNavData():
    isMgr = is_manager_session()
    isStaff = is_staff_session()
    if not session.get("user_id"):
        return {
            "isManager": False,
            "isProdStaff": False,
            "stockoutAlertCount": 0,
            "navNotifications": [],
            "accountUnreadCount": 0,
            "totalNotifBadgeCount": 0
        }
    stockoutCount = 0
    try:
        if isMgr:
            stockouts = integration.get_warehouse_stockouts()
            stockoutCount = len(stockouts)
    except Exception:
        stockoutCount = 0

    try:
        navNotifications = getLiveNotificationsForUser(
            employeeID=session.get("employee_id"),
            isManager=isMgr,
            isProdStaff=isStaff
        )
    except Exception:
        navNotifications = []

    accountUnreadCount = len(navNotifications)
    totalBadgeCount = accountUnreadCount + (1 if (isMgr and stockoutCount > 0) else 0)
    return {
        "isManager": isMgr,
        "isProdStaff": isStaff,
        "stockoutAlertCount": stockoutCount,
        "navNotifications": navNotifications,
        "accountUnreadCount": accountUnreadCount,
        "totalNotifBadgeCount": totalBadgeCount
    }

@productionBlueprint.route("/")
def index():
    databaseStatusMessage = getDatabaseStatus()
    try:
        allOrders = ProductionOrder.getAll()
        materials = Material.getAll()
    except Exception:
        allOrders = []
        materials = []

    draftOrders = sum(1 for o in allOrders if o.status == "Draft")
    releasedOrders = sum(1 for o in allOrders if o.status == "Released")
    inProgressOrders = sum(1 for o in allOrders if o.status == "In Progress")
    completedOrders = sum(1 for o in allOrders if o.status == "Completed")
    lowStockMaterials = [m for m in materials if m.currentStock <= Decimal("0.000")]

    stockouts = []
    try:
        stockouts = integration.get_warehouse_stockouts()
    except Exception:
        stockouts = []

    try:
        allMonitoring = ProductionMonitoring.getAll()
    except Exception:
        allMonitoring = []

    activeMonitoring = [m for m in allMonitoring if m.orderStatus == "In Progress"]
    activeStageBatches = len(activeMonitoring)

    stagesConfig = [
        {"name": "Cutting & Sizing", "threshold": 25},
        {"name": "Joinery & Assembly", "threshold": 50},
        {"name": "Sanding & Finishing", "threshold": 75},
        {"name": "Ready for QA", "threshold": 90},
        {"name": "Quality Inspection (QC)", "threshold": 100}
    ]

    stageReadiness = []
    for sc in stagesConfig:
        if activeStageBatches > 0:
            clearedCount = sum(1 for m in activeMonitoring if m.progress >= sc["threshold"])
            pct = int(round((clearedCount / activeStageBatches) * 100))
        else:
            clearedCount = 0
            pct = 0
        stageReadiness.append({
            "name": sc["name"],
            "count": clearedCount,
            "percent": pct
        })

    utilizationPercent = min(100, (inProgressOrders * 35) + (releasedOrders * 20) + (draftOrders * 10))

    metricsData = {
        "totalOrders": len(allOrders),
        "draftOrders": draftOrders,
        "releasedOrders": releasedOrders,
        "inProgressOrders": inProgressOrders,
        "completedOrders": completedOrders,
        "lowStockCount": len(lowStockMaterials),
        "lowStockItems": lowStockMaterials[:4],
        "stockouts": stockouts[:4],
        "stockoutTotal": len(stockouts),
        "utilizationPercent": utilizationPercent
    }

    today = date.today()
    uncompletedOrders = [o for o in allOrders if o.status != "Completed"]
    overdueOrders = [o for o in uncompletedOrders if o.dueDate and o.dueDate < today]
    dueTodayOrders = [o for o in uncompletedOrders if o.dueDate and o.dueDate == today]
    dueThisWeekOrders = [o for o in uncompletedOrders if o.dueDate and 0 < (o.dueDate - today).days <= 7]

    datedOrders = [o for o in uncompletedOrders if o.dueDate]
    datedOrders.sort(key=lambda o: o.dueDate)
    undatedOrders = [o for o in uncompletedOrders if not o.dueDate]

    upcomingDeadlines = []
    for o in datedOrders[:3]:
        daysLeft = (o.dueDate - today).days
        if daysLeft < 0:
            urgency = "overdue"
            tag = f"{abs(daysLeft)}d overdue"
        elif daysLeft == 0:
            urgency = "today"
            tag = "Due today"
        elif daysLeft <= 3:
            urgency = "urgent"
            tag = f"Due in {daysLeft}d"
        else:
            urgency = "normal"
            tag = f"Due {o.dueDate.strftime('%b %d')}"
        statusClass = "completed" if o.status == "Completed" else ("inProgress" if o.status == "In Progress" else ("released" if o.status == "Released" else "draft"))
        upcomingDeadlines.append({
            "orderID": o.orderID,
            "furnitureName": o.furnitureName,
            "plannedQuantity": o.plannedQuantity,
            "hasDueDate": True,
            "dueDateStr": o.dueDate.strftime("%b %d"),
            "daysLeft": daysLeft,
            "urgency": urgency,
            "tag": tag,
            "status": o.status,
            "statusClass": statusClass
        })

    remainingSlots = 3 - len(upcomingDeadlines)
    if remainingSlots > 0:
        for o in undatedOrders[:remainingSlots]:
            statusClass = "completed" if o.status == "Completed" else ("inProgress" if o.status == "In Progress" else ("released" if o.status == "Released" else "draft"))
            upcomingDeadlines.append({
                "orderID": o.orderID,
                "furnitureName": o.furnitureName,
                "plannedQuantity": o.plannedQuantity,
                "hasDueDate": False,
                "dueDateStr": "",
                "daysLeft": 999,
                "urgency": "unscheduled",
                "tag": "Set Date",
                "status": o.status,
                "statusClass": statusClass
            })

    scheduleTracker = {
        "overdue": len(overdueOrders),
        "dueToday": len(dueTodayOrders),
        "dueThisWeek": len(dueThisWeekOrders),
        "totalPending": len(uncompletedOrders),
        "needsDateCount": len(undatedOrders),
        "upcoming": upcomingDeadlines
    }

    try:
        weekOffset = int(request.args.get("week_offset", 0))
    except (ValueError, TypeError):
        weekOffset = 0

    targetDate = today + timedelta(days=weekOffset * 7)
    monday = targetDate - timedelta(days=targetDate.weekday())
    sunday = monday + timedelta(days=6)
    dayNames = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    prevMonday = monday - timedelta(days=7)
    prevSunday = monday - timedelta(days=1)

    dailyActivityMap = {}
    prevWeeklyBatches = 0
    prevWeeklyUnits = 0
    try:
        with openTransaction() as connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT order_date, COUNT(*) AS order_count, COALESCE(SUM(planned_quantity), 0) AS total_units
                    FROM prod_productionorder
                    WHERE order_date >= %s AND order_date <= %s
                    GROUP BY order_date
                """, (monday, sunday))
                for r in cursor.fetchall():
                    dailyActivityMap[r["order_date"]] = {
                        "orders": int(r["order_count"]),
                        "units": int(r["total_units"])
                    }
                cursor.execute("""
                    SELECT COUNT(*) AS order_count, COALESCE(SUM(planned_quantity), 0) AS total_units
                    FROM prod_productionorder
                    WHERE order_date >= %s AND order_date <= %s
                """, (prevMonday, prevSunday))
                prevRow = cursor.fetchone()
                if prevRow:
                    prevWeeklyBatches = int(prevRow.get("order_count") or 0)
                    prevWeeklyUnits = int(prevRow.get("total_units") or 0)
    except Exception:
        dailyActivityMap = {}
        prevWeeklyBatches = 0
        prevWeeklyUnits = 0

    dailyCapacityBenchmark = 5
    maxDailyOrders = max([d["orders"] for d in dailyActivityMap.values()] + [dailyCapacityBenchmark])

    weekActivity = []
    totalWeeklyBatches = 0
    totalWeeklyUnits = 0
    for i in range(7):
        currentDayDate = monday + timedelta(days=i)
        stats = dailyActivityMap.get(currentDayDate, {"orders": 0, "units": 0})
        totalWeeklyBatches += stats["orders"]
        totalWeeklyUnits += stats["units"]
        isToday = (currentDayDate == today)
        isFuture = (currentDayDate > today)

        if stats["orders"] > 0:
            heightPct = max(16, min(100, int((stats["orders"] / maxDailyOrders) * 100)))
        else:
            heightPct = 0

        weekActivity.append({
            "dayName": dayNames[i],
            "dayNumber": currentDayDate.strftime("%d"),
            "dateStr": currentDayDate.strftime("%b. %d"),
            "isToday": isToday,
            "isFuture": isFuture,
            "orders": stats["orders"],
            "units": stats["units"],
            "heightPct": heightPct
        })

    weekDateRangeStr = f"{monday.strftime('%b %d')} – {sunday.strftime('%b %d')}"
    recentOrdersList = allOrders[:6]
    integrationEventsList = []

    return render_template(
        "production/dashboard/dashboard.html",
        activeTab="dashboard",
        databaseStatus=databaseStatusMessage,
        metrics=metricsData,
        recentOrders=recentOrdersList,
        integrationEvents=integrationEventsList,
        weekActivity=weekActivity,
        weekDateRange=weekDateRangeStr,
        todayDateStr=today.strftime("%b. %d"),
        totalWeeklyBatches=totalWeeklyBatches,
        totalWeeklyUnits=totalWeeklyUnits,
        prevWeeklyBatches=prevWeeklyBatches,
        prevWeeklyUnits=prevWeeklyUnits,
        weekOffset=weekOffset,
        stageReadiness=stageReadiness,
        activeStageBatches=activeStageBatches,
        scheduleTracker=scheduleTracker
    )

@productionBlueprint.route("/furniture")
def furnitureList():
    searchQuery = request.args.get("q", "").strip()
    selectedCategory = request.args.get("category", "").strip()
    try:
        furnitureItemList = Furniture.getAll()
        categoriesList = Furniture.getCategories()
    except Exception as err:
        flash(f"Failed to load products from database: {str(err)}", "alert")
        furnitureItemList = []
        categoriesList = []

    return render_template(
        "production/products/furniture_list.html",
        activeTab="furniture",
        furnitureItems=furnitureItemList,
        categories=categoriesList,
        searchQuery=searchQuery,
        selectedCategory=selectedCategory
    )

@productionBlueprint.route("/furniture/add", methods=["POST"])
@manager_required
def addFurniture():
    furnitureName = request.form.get("furnitureName", "").strip()
    furnitureType = request.form.get("furnitureType", "").strip()
    priceRaw = request.form.get("sellingPrice", "").strip()

    if not furnitureName or not furnitureType:
        flash("Product name and category are required.", "error")
        return redirect(url_for("production.furnitureList"))

    sellingPrice = Decimal("0.00")
    if priceRaw:
        try:
            sellingPrice = Decimal(priceRaw)
            if sellingPrice < 0:
                flash("Selling price must be 0 or greater.", "error")
                return redirect(url_for("production.furnitureList"))
        except Exception:
            flash("Invalid price format. Please enter a valid number.", "error")
            return redirect(url_for("production.furnitureList"))

    try:
        if Furniture.existsByName(furnitureName):
            flash(f"A product named '{furnitureName}' already exists in the catalog.", "warning")
            return redirect(url_for("production.furnitureList"))

        Furniture.addFurniture(furnitureName, furnitureType, sellingPrice)
        flash(f"Product '{furnitureName}' registered successfully.", "success")
    except UniqueViolation:
        flash(f"A product named '{furnitureName}' already exists in the catalog.", "warning")
    except Exception as err:
        flash(f"Database error while adding product: {str(err)}", "error")

    return redirect(url_for("production.furnitureList"))

@productionBlueprint.route("/furniture/edit/<int:furnitureID>", methods=["POST"])
@manager_required
def editFurniture(furnitureID):
    furnitureName = request.form.get("furnitureName", "").strip()
    furnitureType = request.form.get("furnitureType", "").strip()
    priceRaw = request.form.get("sellingPrice", "").strip()

    if not furnitureName or not furnitureType:
        flash("Product name and category are required.", "error")
        return redirect(url_for("production.furnitureList"))

    sellingPrice = Decimal("0.00")
    if priceRaw:
        try:
            sellingPrice = Decimal(priceRaw)
            if sellingPrice < 0:
                flash("Selling price must be 0 or greater.", "error")
                return redirect(url_for("production.furnitureList"))
        except Exception:
            flash("Invalid price format. Please enter a valid number.", "error")
            return redirect(url_for("production.furnitureList"))

    try:
        if Furniture.existsByName(furnitureName, excludeID=furnitureID):
            flash(f"Another product with the name '{furnitureName}' already exists.", "warning")
            return redirect(url_for("production.furnitureList"))

        updated = Furniture.updateFurniture(furnitureID, furnitureName, furnitureType, sellingPrice)
        if updated:
            flash(f"Product '{furnitureName}' updated successfully.", "success")
        else:
            flash("Product not found.", "error")
    except UniqueViolation:
        flash(f"Another product with the name '{furnitureName}' already exists.", "warning")
    except Exception as err:
        flash(f"Database error while updating product: {str(err)}", "error")

    return redirect(url_for("production.furnitureList"))

@productionBlueprint.route("/furniture/delete/<int:furnitureID>", methods=["POST"])
@manager_required
def deleteFurniture(furnitureID):
    try:
        Furniture.deleteFurniture(furnitureID)
        flash("Product deleted successfully.", "success")
    except ValueError as valErr:
        flash(str(valErr), "warning")
    except Exception as err:
        flash(f"Database error while deleting product: {str(err)}", "error")

    return redirect(url_for("production.furnitureList"))

@productionBlueprint.route("/materials")
def materialList():
    rawMaterialList = []
    return render_template(
        "production/materials/material_list.html",
        activeTab="materials",
        rawMaterials=rawMaterialList,
        sufficientCount=0,
        lowStockCount=0
    )

@productionBlueprint.route("/bom")
def bomList():
    try:
        furnitureItemList = Furniture.getAll()
    except Exception as err:
        flash(f"Failed to load products: {str(err)}", "error")
        furnitureItemList = []

    furnitureIDParam = request.args.get("furniture_id", "").strip()
    selectedFurniture = None

    if furnitureIDParam and furnitureIDParam.isdigit():
        try:
            selectedFurniture = Furniture.getByID(int(furnitureIDParam))
        except Exception:
            selectedFurniture = None

    if not selectedFurniture and furnitureItemList:
        selectedFurniture = furnitureItemList[0]

    bom = None
    bomItems = []
    requirements = []
    unitTotalCost = Decimal("0.00")
    batchTotalCost = Decimal("0.00")
    batchQuantity = Decimal("1")

    if selectedFurniture:
        try:
            bom = BillOfMaterials.getByFurnitureID(selectedFurniture.furnitureID, autoCreate=True)
            bomItems = bom.getItems()

            batchParam = request.args.get("batch_qty", "1").strip()
            try:
                parsedBatch = Decimal(batchParam)
                batchQuantity = parsedBatch if parsedBatch > Decimal("0") else Decimal("1")
            except Exception:
                batchQuantity = Decimal("1")

            requirements = bom.calculateRequirements(batchQuantity)
            unitTotalCost = sum((item.quantityRequired * item.unitCost for item in bomItems), Decimal("0.00"))
            batchTotalCost = sum((req["batchCost"] for req in requirements), Decimal("0.00"))
            suggestedMarkupPrice = (unitTotalCost * Decimal("1.40")).quantize(Decimal("0.01"))
        except Exception as err:
            flash(f"Failed to load BOM recipe: {str(err)}", "error")
            suggestedMarkupPrice = Decimal("0.00")
    else:
        suggestedMarkupPrice = Decimal("0.00")

    try:
        materialsList = Material.getAll()
    except Exception as err:
        flash(f"Failed to load raw materials: {str(err)}", "error")
        materialsList = []

    return render_template(
        "production/products/bom_list.html",
        activeTab="bom",
        furnitureItems=furnitureItemList,
        selectedFurniture=selectedFurniture,
        bom=bom,
        bomItems=bomItems,
        requirements=requirements,
        materials=materialsList,
        batchQuantity=batchQuantity,
        unitTotalCost=unitTotalCost,
        batchTotalCost=batchTotalCost,
        suggestedMarkupPrice=suggestedMarkupPrice
    )

@productionBlueprint.route("/bom/add", methods=["POST"])
@productionBlueprint.route("/bom/items/add", methods=["POST"])
@manager_required
def addBomItem():
    furnitureID = request.form.get("furnitureID", "").strip()
    materialID = request.form.get("materialID", "").strip()
    quantityRaw = request.form.get("quantityRequired", "").strip()

    if not furnitureID or not furnitureID.isdigit():
        flash("Invalid product reference.", "error")
        return redirect(url_for("production.bomList"))

    if not materialID or not materialID.isdigit():
        flash("Please select a valid raw material.", "error")
        return redirect(url_for("production.bomList", furniture_id=furnitureID))

    if not quantityRaw:
        flash("Quantity required is required.", "error")
        return redirect(url_for("production.bomList", furniture_id=furnitureID))

    try:
        quantityRequired = Decimal(quantityRaw)
        if not quantityRequired.is_finite() or quantityRequired.is_nan():
            flash("Invalid quantity format.", "error")
            return redirect(url_for("production.bomList", furniture_id=furnitureID))

        if quantityRequired <= Decimal("0"):
            flash("Quantity required must be greater than 0.", "error")
            return redirect(url_for("production.bomList", furniture_id=furnitureID))

        if quantityRequired > Decimal("999999999.999"):
            flash("Quantity exceeds maximum allowable limit (999,999,999.999).", "error")
            return redirect(url_for("production.bomList", furniture_id=furnitureID))

        if quantityRequired.as_tuple().exponent < -3:
            flash("Quantity cannot have more than 3 decimal places.", "error")
            return redirect(url_for("production.bomList", furniture_id=furnitureID))
    except (InvalidOperation, ValueError, TypeError):
        flash("Invalid quantity format.", "error")
        return redirect(url_for("production.bomList", furniture_id=furnitureID))

    try:
        bom = BillOfMaterials.getByFurnitureID(int(furnitureID), autoCreate=True)
        bomItemID, wasUpdated = bom.addMaterial(int(materialID), quantityRequired)
        material = Material.getByID(int(materialID))
        materialName = material.materialName if material else "Material"

        if wasUpdated:
            flash(f"Updated '{materialName}' quantity to {quantityRequired} in BOM.", "success")
        else:
            flash(f"Added '{materialName}' ({quantityRequired}) to BOM.", "success")
    except Exception as err:
        flash(f"Database error while saving BOM item: {str(err)}", "error")

    return redirect(url_for("production.bomList", furniture_id=furnitureID))

@productionBlueprint.route("/bom/remove/<int:bomItemID>", methods=["POST"])
@productionBlueprint.route("/bom/items/delete/<int:bomItemID>", methods=["POST"])
@manager_required
def removeBomItem(bomItemID):
    furnitureID = request.form.get("furnitureID", "").strip()
    if not furnitureID or not furnitureID.isdigit():
        flash("Invalid product reference.", "error")
        return redirect(url_for("production.bomList"))

    try:
        bom = BillOfMaterials.getByFurnitureID(int(furnitureID), autoCreate=False)
        if not bom:
            flash("Bill of materials not found.", "error")
            return redirect(url_for("production.bomList", furniture_id=furnitureID))

        bom.removeMaterial(bomItemID)
        flash("Component removed from BOM recipe.", "success")
    except Exception as err:
        flash(f"Database error while removing component: {str(err)}", "error")

    return redirect(url_for("production.bomList", furniture_id=furnitureID))

@productionBlueprint.route("/bom/update-price", methods=["POST"])
@manager_required
def updateFurniturePriceFromBom():
    furnitureID = request.form.get("furnitureID", "").strip()
    priceRaw = request.form.get("sellingPrice", "").strip()
    if not furnitureID or not furnitureID.isdigit():
        flash("Invalid product reference.", "error")
        return redirect(url_for("production.bomList"))
    try:
        newPrice = Decimal(priceRaw) if priceRaw else Decimal("0.00")
        if newPrice < 0:
            flash("Selling price must be 0 or greater.", "error")
            return redirect(url_for("production.bomList", furniture_id=furnitureID))
    except Exception:
        flash("Invalid price format. Please enter a valid number.", "error")
        return redirect(url_for("production.bomList", furniture_id=furnitureID))
    try:
        f = Furniture.getByID(int(furnitureID))
        if f:
            Furniture.updateFurniture(f.furnitureID, f.furnitureName, f.furnitureType, newPrice)
            flash(f"Updated catalog selling price for '{f.furnitureName}' to ₱{newPrice:,.2f}.", "success")
        else:
            flash("Product not found.", "error")
    except Exception as err:
        flash(f"Database error while updating price: {str(err)}", "error")
    return redirect(url_for("production.bomList", furniture_id=furnitureID))

@productionBlueprint.route("/orders")
def orderList():
    statusFilter = request.args.get("status", "").strip()
    searchQuery = request.args.get("q", "").strip()
    try:
        productionOrderList = ProductionOrder.getAll()
    except Exception as err:
        flash(f"Failed to load production orders: {str(err)}", "error")
        productionOrderList = []

    try:
        summary = ProductionOrder.getSummaryCounts()
    except Exception:
        summary = {"total": 0, "draft": 0, "released": 0, "inProgress": 0, "completed": 0}

    try:
        furnitureItemList = Furniture.getAll()
    except Exception as err:
        flash(f"Failed to load products: {str(err)}", "error")
        furnitureItemList = []

    try:
        stockoutAlerts = integration.get_warehouse_stockouts()
    except Exception:
        stockoutAlerts = []

    furnitureBomMap = {}
    for f in furnitureItemList:
        try:
            b = BillOfMaterials.getByFurnitureID(f.furnitureID, autoCreate=False)
            if b:
                items = b.getItems()
                furnitureBomMap[f.furnitureID] = [
                    {
                        "materialName": it.materialName,
                        "unit": it.unit,
                        "quantityRequired": float(it.quantityRequired),
                        "currentStock": float(getattr(it, "currentStock", 0.0) or 0.0)
                    }
                    for it in items
                ]
            else:
                furnitureBomMap[f.furnitureID] = []
        except Exception:
            furnitureBomMap[f.furnitureID] = []

    return render_template(
        "production/orders/order_list.html",
        activeTab="orders",
        orders=productionOrderList,
        summary=summary,
        furnitureItems=furnitureItemList,
        stockoutAlerts=stockoutAlerts,
        furnitureBomMap=furnitureBomMap,
        statusFilter=statusFilter,
        searchQuery=searchQuery
    )

@productionBlueprint.route("/orders/<int:orderID>")
def orderDetail(orderID):
    try:
        order = ProductionOrder.getByID(orderID)
        if not order:
            flash("Production order not found.", "error")
            return redirect(url_for("production.orderList"))

        bom = BillOfMaterials.getByFurnitureID(order.furnitureID, autoCreate=False)
        bomItems = bom.getItems() if bom else []
        estimatedUnitMaterialCost = sum((item.quantityRequired * item.unitCost for item in bomItems), Decimal("0.00"))
        estimatedBatchMaterialCost = estimatedUnitMaterialCost * Decimal(str(order.plannedQuantity))
        rawRequirements = bom.calculateRequirements(order.plannedQuantity) if bom else []

        reservedMap = {}
        if order.status == "Draft":
            otherReleased = [o for o in ProductionOrder.getAll() if o.status == "Released" and o.orderID != order.orderID]
            for ro in otherReleased:
                try:
                    roBom = BillOfMaterials.getByFurnitureID(ro.furnitureID, autoCreate=False)
                    if roBom:
                        for r in roBom.calculateRequirements(Decimal(str(ro.plannedQuantity))):
                            mid = r["materialID"]
                            reservedMap[mid] = reservedMap.get(mid, Decimal("0.000")) + r["batchQuantity"]
                except Exception:
                    pass

        matsMap = {m.materialID: m for m in Material.getAll()}
        issuances = MaterialIssuance.getByOrderID(orderID)
        issuedByMaterial = {}
        for iss in issuances:
            issuedByMaterial[iss.materialID] = issuedByMaterial.get(iss.materialID, Decimal("0.000")) + iss.quantityIssued

        requirements = []
        shortageCount = 0
        for req in rawRequirements:
            mid = req["materialID"]
            mat = matsMap.get(mid)
            onHand = mat.currentStock if mat else Decimal("0.000")
            reserved = reservedMap.get(mid, Decimal("0.000"))
            availableNet = max(Decimal("0.000"), onHand - reserved)
            required = req["batchQuantity"]
            if order.status == "Draft":
                isShort = availableNet < required
                shortage = max(Decimal("0.000"), required - availableNet)
            elif order.status == "Released":
                isShort = onHand < required
                shortage = max(Decimal("0.000"), required - onHand)
            else:
                isShort = False
                shortage = Decimal("0.000")
            if isShort:
                shortageCount += 1
            enriched = dict(req)
            enriched["itemCode"] = (mat.itemCode if mat and mat.itemCode else req.get("itemCode")) or f"RM-{mid:03d}"
            enriched["onHandQuantity"] = onHand
            enriched["availableNet"] = availableNet
            enriched["shortageQuantity"] = shortage
            enriched["isShort"] = isShort
            enriched["issuedQuantity"] = issuedByMaterial.get(mid, Decimal("0.000"))
            requirements.append(enriched)

        monitoring = ProductionMonitoring.getByOrderID(orderID)
        qaRecords = ProductionOutput.getByOrderID(orderID)
        qaSummary = ProductionOutput.getOrderInspectionSummary(orderID)
        costRecord = ProductionCost.getByOrderID(orderID)
        stageProofs = ProductionAttachment.getByOrderID(orderID)
    except Exception as err:
        flash(f"Failed to load order details: {str(err)}", "error")
        return redirect(url_for("production.orderList"))

    return render_template(
        "production/orders/order_detail.html",
        activeTab="orders",
        order=order,
        requirements=requirements,
        shortageCount=shortageCount,
        monitoring=monitoring,
        issuances=issuances,
        qaRecords=qaRecords,
        qaSummary=qaSummary,
        costRecord=costRecord,
        stageProofs=stageProofs,
        estimatedUnitMaterialCost=estimatedUnitMaterialCost,
        estimatedBatchMaterialCost=estimatedBatchMaterialCost
    )

@productionBlueprint.route("/orders/create", methods=["POST"])
@manager_required
def createOrder():
    furnitureIDRaw = request.form.get("furnitureID", "").strip()
    quantityRaw = request.form.get("plannedQuantity", "").strip()
    startDateRaw = request.form.get("plannedStartDate", "").strip()
    dueDateRaw = request.form.get("dueDate", "").strip()
    purposeRaw = request.form.get("purpose", "").strip()
    purpose = purposeRaw if purposeRaw in ("Warehouse Restock", "Scheduled Batch") else "Warehouse Restock"

    if not furnitureIDRaw or not furnitureIDRaw.isdigit():
        flash("Please select a valid furniture product.", "error")
        return redirect(url_for("production.orderList"))

    furnitureID = int(furnitureIDRaw)

    if not quantityRaw:
        flash("Planned batch quantity is required.", "error")
        return redirect(url_for("production.orderList"))

    try:
        plannedQuantity = int(quantityRaw)
        if plannedQuantity < 1 or plannedQuantity > 100000:
            flash("Planned quantity must be a whole number between 1 and 100,000.", "error")
            return redirect(url_for("production.orderList"))
    except (ValueError, TypeError):
        flash("Planned quantity must be a valid whole number.", "error")
        return redirect(url_for("production.orderList"))

    parsedStartDate = None
    if startDateRaw:
        try:
            parsedStartDate = date.fromisoformat(startDateRaw)
        except ValueError:
            flash("Invalid planned start date format.", "error")
            return redirect(url_for("production.orderList"))

    parsedDueDate = None
    if dueDateRaw:
        try:
            parsedDueDate = date.fromisoformat(dueDateRaw)
        except ValueError:
            flash("Invalid target due date format.", "error")
            return redirect(url_for("production.orderList"))

    if parsedStartDate and parsedDueDate and parsedDueDate < parsedStartDate:
        flash("Target due date cannot be earlier than planned start date.", "error")
        return redirect(url_for("production.orderList"))

    bom = BillOfMaterials.getByFurnitureID(furnitureID, autoCreate=False)
    if not bom or len(bom.getItems()) == 0:
        flash("Cannot create production order: Selected product does not have a configured Bill of Materials recipe. Please configure its BOM first.", "error")
        return redirect(url_for("production.orderList"))

    try:
        newOrderID = ProductionOrder.createOrder(
            furnitureID=furnitureID,
            plannedQuantity=plannedQuantity,
            plannedStartDate=parsedStartDate,
            dueDate=parsedDueDate,
            purpose=purpose
        )
        flash(f"Production Order #PO-{newOrderID} created successfully in Draft status.", "success")
    except ValueError as valErr:
        flash(str(valErr), "warning")
    except Exception as err:
        flash(f"Database error while creating production order: {str(err)}", "error")

    return redirect(url_for("production.orderList"))

@productionBlueprint.route("/orders/delete/<int:orderID>", methods=["POST"])
@manager_required
def deleteOrder(orderID):
    try:
        ProductionOrder.deleteOrder(orderID)
        flash(f"Draft Production Order #PO-{orderID} deleted successfully.", "success")
    except ValueError as valErr:
        flash(str(valErr), "warning")
    except Exception as err:
        flash(f"Database error while deleting order: {str(err)}", "error")

    return redirect(url_for("production.orderList"))

@productionBlueprint.route("/planning")
def planningList():
    statusFilter = request.args.get("status", "").strip()
    searchQuery = request.args.get("q", "").strip()
    try:
        plannedOrders = ProductionOrder.getPlanningOrders()
        staffRoster = getProductionStaffRoster()
        totalCount = len(plannedOrders)
        scheduledCount = sum(1 for o in plannedOrders if o.scheduleHealth == "On Schedule")
        needsPlanCount = sum(1 for o in plannedOrders if o.scheduleHealth == "Needs Plan")
        overdueCount = sum(1 for o in plannedOrders if o.scheduleHealth == "Overdue")
        summary = {
            "total": totalCount,
            "scheduled": scheduledCount,
            "needsPlan": needsPlanCount,
            "overdue": overdueCount
        }
    except Exception as err:
        flash(f"Failed to load production planning orders: {str(err)}", "error")
        plannedOrders = []
        staffRoster = []
        summary = {"total": 0, "scheduled": 0, "needsPlan": 0, "overdue": 0}

    return render_template(
        "production/planning/planning.html",
        activeTab="planning",
        plannedOrders=plannedOrders,
        staffRoster=staffRoster,
        summary=summary,
        statusFilter=statusFilter,
        searchQuery=searchQuery
    )

@productionBlueprint.route("/planning/update/<int:orderID>", methods=["POST"])
@manager_required
def updateOrderSchedule(orderID):
    nextUrl = request.form.get("next_url") or request.args.get("next_url")
    targetRedirect = nextUrl if (nextUrl and nextUrl.startswith("/production/")) else url_for("production.planningList")

    startDateRaw = request.form.get("plannedStartDate", "").strip()
    dueDateRaw = request.form.get("dueDate", "").strip()
    assignedToRaw = request.form.get("assignedTo", "").strip()

    parsedStartDate = None
    if startDateRaw:
        try:
            parsedStartDate = date.fromisoformat(startDateRaw)
        except ValueError:
            flash("Invalid planned start date format.", "error")
            return redirect(targetRedirect)

    parsedDueDate = None
    if dueDateRaw:
        try:
            parsedDueDate = date.fromisoformat(dueDateRaw)
        except ValueError:
            flash("Invalid target due date format.", "error")
            return redirect(targetRedirect)

    if parsedStartDate and parsedDueDate and parsedDueDate < parsedStartDate:
        flash("Target due date cannot be earlier than planned start date.", "error")
        return redirect(targetRedirect)

    assignedToID = int(assignedToRaw) if (assignedToRaw and assignedToRaw.isdigit()) else None
    if not parsedStartDate or not parsedDueDate or not assignedToID:
        flash("Please specify Planned Start Date, Target Due Date, and Assigned Workshop Staff to save the production plan.", "warning")
        return redirect(targetRedirect)

    if not isValidActiveProdStaff(assignedToID):
        flash("Selected employee is not an active Production Department Workshop Staff member.", "error")
        return redirect(targetRedirect)

    try:
        ProductionOrder.updateSchedule(
            orderID,
            parsedStartDate,
            parsedDueDate,
            assignedTo=assignedToID,
            updateAssignment=True
        )
        updatedOrder = ProductionOrder.getByID(orderID)
        staffLabel = updatedOrder.assignedStaffName if updatedOrder and updatedOrder.assignedStaffName else "assigned staff"
        flash(f"Production plan saved for Order #PO-{orderID} (Assigned to {staffLabel}).", "success")
    except ValueError as valErr:
        flash(str(valErr), "warning")
    except Exception as err:
        flash(f"Database error while updating schedule: {str(err)}", "error")

    return redirect(targetRedirect)

@productionBlueprint.route("/requirements")
@productionBlueprint.route("/requirement")
def requirementList():
    try:
        allOrders = ProductionOrder.getAll()
    except Exception as err:
        flash(f"Failed to load production orders: {str(err)}", "error")
        allOrders = []

    filterType = request.args.get("filter", "active").strip().lower()
    if filterType not in ("active", "all"):
        filterType = "active"

    needsActionOrders = [o for o in allOrders if o.status in ("Draft", "Released")]
    displayedOrders = needsActionOrders if filterType == "active" else allOrders
    if not displayedOrders and filterType == "active":
        displayedOrders = allOrders

    orderIDParam = request.args.get("order_id", "").strip()
    selectedOrder = None

    if orderIDParam and orderIDParam.isdigit():
        targetID = int(orderIDParam)
        selectedOrder = next((o for o in allOrders if o.orderID == targetID), None)

    if not selectedOrder and displayedOrders:
        selectedOrder = displayedOrders[0]

    reservedMap = {}
    otherReleased = [o for o in allOrders if o.status == "Released" and (not selectedOrder or o.orderID != selectedOrder.orderID)]
    for ro in otherReleased:
        try:
            roBom = BillOfMaterials.getByFurnitureID(ro.furnitureID, autoCreate=False)
            if roBom:
                roReqs = roBom.calculateRequirements(Decimal(str(ro.plannedQuantity)))
                for r in roReqs:
                    mid = r["materialID"]
                    reservedMap[mid] = reservedMap.get(mid, Decimal("0.000")) + r["batchQuantity"]
        except Exception:
            pass

    requirementsList = []
    hasShortage = False
    shortageCount = 0
    hasBOM = False
    totalEstimatedCost = Decimal("0.00")

    if selectedOrder:
        try:
            bom = BillOfMaterials.getByFurnitureID(selectedOrder.furnitureID, autoCreate=True)
            batchQty = Decimal(str(selectedOrder.plannedQuantity))
            rawReqs = bom.calculateRequirements(batchQty)
            hasBOM = len(rawReqs) > 0

            matsMap = {m.materialID: m for m in Material.getAll()}
            for req in rawReqs:
                mid = req["materialID"]
                mat = matsMap.get(mid)
                itemCode = mat.itemCode if mat and mat.itemCode else f"RM-{mid:03d}"
                onHand = mat.currentStock if mat else Decimal("0.000")
                reserved = reservedMap.get(mid, Decimal("0.000"))
                availableNet = max(Decimal("0.000"), onHand - reserved)
                required = req["batchQuantity"]

                if selectedOrder.status == "Draft":
                    isShort = availableNet < required
                    shortage = max(Decimal("0.000"), required - availableNet)
                elif selectedOrder.status == "Released":
                    isShort = onHand < required
                    shortage = max(Decimal("0.000"), required - onHand)
                else:
                    isShort = False
                    shortage = Decimal("0.000")

                if isShort:
                    hasShortage = True
                    shortageCount += 1

                totalEstimatedCost += req["batchCost"]

                requirementsList.append({
                    "materialID": mid,
                    "itemCode": itemCode,
                    "materialName": req["materialName"],
                    "unit": req["unit"],
                    "quantityRequired": req["quantityRequired"],
                    "requiredQuantity": required,
                    "onHandQuantity": onHand,
                    "reservedQuantity": reserved,
                    "availableNet": availableNet,
                    "shortageQuantity": shortage,
                    "isShort": isShort,
                    "unitCost": req["unitCost"],
                    "batchCost": req["batchCost"]
                })
        except Exception as err:
            flash(f"Failed to calculate material requirements: {str(err)}", "error")

    return render_template(
        "production/materials/requirement.html",
        activeTab="requirement",
        filterType=filterType,
        needsActionCount=len(needsActionOrders),
        allOrdersCount=len(allOrders),
        displayedOrders=displayedOrders,
        activeOrders=displayedOrders,
        allOrders=allOrders,
        selectedOrder=selectedOrder,
        requirementsList=requirementsList,
        hasShortage=hasShortage,
        shortageCount=shortageCount,
        hasBOM=hasBOM,
        totalEstimatedCost=totalEstimatedCost
    )

@productionBlueprint.route("/requirements/release/<int:orderID>", methods=["POST"])
@productionBlueprint.route("/requirement/release/<int:orderID>", methods=["POST"])
@manager_required
def releaseOrder(orderID):
    try:
        order = ProductionOrder.getByID(orderID)
        if not order:
            flash("Production order not found.", "error")
            return redirect(url_for("production.requirementList"))

        if order.status != "Draft":
            flash(f"Order #PO-{orderID} cannot be released because it is currently '{order.status}'.", "warning")
            return redirect(url_for("production.requirementList", order_id=orderID))

        if not order.plannedStartDate or not order.dueDate or not order.assignedTo:
            flash(f"Release blocked: Complete Production Planning (Timeline Dates and Assigned Workshop Staff) for Order #PO-{orderID} before releasing.", "warning")
            return redirect(url_for("production.requirementList", order_id=orderID))

        bom = BillOfMaterials.getByFurnitureID(order.furnitureID, autoCreate=True)
        batchQty = Decimal(str(order.plannedQuantity))
        reqs = bom.calculateRequirements(batchQty)

        if not reqs:
            flash(f"Cannot release order: No BOM recipe components defined for '{order.furnitureName}'.", "warning")
            return redirect(url_for("production.requirementList", order_id=orderID))

        matsMap = {m.materialID: m for m in Material.getAll()}
        shortageList = []
        for r in reqs:
            mat = matsMap.get(r["materialID"])
            onHand = mat.currentStock if mat else Decimal("0.000")
            if onHand < r["batchQuantity"]:
                shortQty = r["batchQuantity"] - onHand
                cleanShort = "{:,.3f}".format(shortQty).rstrip("0").rstrip(".") or "0"
                shortageList.append(f"{r['materialName']} (Deficit: {cleanShort} {r['unit']})")

        if shortageList:
            flash(f"Release blocked: Material shortages detected: {', '.join(shortageList)}. Replenish inventory stock before releasing.", "error")
            return redirect(url_for("production.requirementList", order_id=orderID))

        ProductionOrder.updateStatus(orderID, "Released")
        flash(f"Order #PO-{orderID} released to production successfully. Ready for Material Issuance.", "success")
    except Exception as err:
        flash(f"Failed to release order: {str(err)}", "error")

    return redirect(url_for("production.requirementList", order_id=orderID))

@productionBlueprint.route("/issuance")
def issuanceList():
    try:
        allOrders = ProductionOrder.getAll()
        releasedOrders = [o for o in allOrders if o.status == "Released"]
        bomCache = {}
        for o in releasedOrders:
            if o.furnitureID not in bomCache:
                bomCache[o.furnitureID] = BillOfMaterials.getByFurnitureID(o.furnitureID, autoCreate=False)
            bom = bomCache[o.furnitureID]
            if bom:
                o.requirements = bom.calculateRequirements(Decimal(str(o.plannedQuantity)))
            else:
                o.requirements = []
        materialIssuanceList = MaterialIssuance.getAll()
    except Exception as err:
        flash(f"Failed to load issuance records: {str(err)}", "error")
        releasedOrders = []
        materialIssuanceList = []

    return render_template(
        "production/materials/issuance_list.html",
        activeTab="issuance",
        releasedOrders=releasedOrders,
        issuances=materialIssuanceList
    )

@productionBlueprint.route("/issuance/issue/<int:orderID>", methods=["POST"])
@manager_required
def issueOrderMaterials(orderID):
    try:
        order = ProductionOrder.getByID(orderID)
        if not order:
            flash("Production order not found.", "error")
            return redirect(url_for("production.issuanceList"))

        if order.status != "Released":
            flash(f"Order #PO-{orderID} cannot be issued because it is currently '{order.status}' (Must be 'Released').", "warning")
            return redirect(url_for("production.issuanceList"))

        bom = BillOfMaterials.getByFurnitureID(order.furnitureID, autoCreate=False)
        if not bom:
            flash(f"Cannot issue materials: No Bill of Materials found for '{order.furnitureName}'.", "error")
            return redirect(url_for("production.issuanceList"))

        reqs = bom.calculateRequirements(Decimal(str(order.plannedQuantity)))
        if not reqs:
            flash(f"Cannot issue materials: BOM has no items for '{order.furnitureName}'.", "error")
            return redirect(url_for("production.issuanceList"))

        with openTransaction() as conn:
            for r in reqs:
                integration.deduct_material_stock(r["materialID"], r["batchQuantity"], conn=conn)
                MaterialIssuance.recordIssuance(orderID, r["materialID"], r["batchQuantity"], recordedBy=session.get("employee_name", "Dave Cagalitan"), conn=conn)

            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO prod_productionmonitoring (order_id, progress, start_date)
                    VALUES (%s, 0.0, CURRENT_DATE)
                    ON CONFLICT (order_id) DO NOTHING
                """, (orderID,))

            ProductionOrder.updateStatus(orderID, "In Progress", conn=conn)

        flash(f"Materials dispatched for Order #PO-{orderID}! Order moved to 'In Progress' for workshop assembly.", "success")
    except ValueError as valErr:
        flash(f"Issuance blocked: {str(valErr)}", "error")
    except Exception as err:
        flash(f"Failed to issue materials: {str(err)}", "error")

    return redirect(url_for("production.issuanceList"))

@productionBlueprint.route("/monitoring")
def monitoringList():
    try:
        productionMonitoringList = ProductionMonitoring.getAll()
        latestProofMap = ProductionAttachment.getLatestByOrderIDs([m.orderID for m in productionMonitoringList])
        for m in productionMonitoringList:
            m.latestProof = latestProofMap.get(m.orderID)
        currentEmpID = session.get("employee_id")
        summary = {
            "total": len(productionMonitoringList),
            "inProgress": sum(1 for m in productionMonitoringList if m.progress < 100),
            "completed": sum(1 for m in productionMonitoringList if m.progress >= 100),
            "myAssigned": sum(1 for m in productionMonitoringList if m.progress < 100 and currentEmpID and m.assignedTo == currentEmpID)
        }
    except Exception as err:
        flash(f"Failed to load monitoring records: {str(err)}", "error")
        productionMonitoringList = []
        summary = {"total": 0, "inProgress": 0, "completed": 0, "myAssigned": 0}

    return render_template(
        "production/manufacturing/monitoring_list.html",
        activeTab="monitoring",
        monitorings=productionMonitoringList,
        summary=summary
    )

@productionBlueprint.route("/monitoring/update/<int:monitoringID>", methods=["POST"])
def updateMonitoringProgress(monitoringID):
    stageLabels = {
        25: "Stage 1: Cutting & Sizing",
        50: "Stage 2: Joinery & Assembly",
        75: "Stage 3: Sanding & Finishing",
        90: "Stage 4: Ready for QA Inspection",
        100: "QA Passed & Completed"
    }
    progressRaw = request.form.get("progress", "").strip()
    stageNote = request.form.get("stageNote", "").strip()
    proofFile = request.files.get("proofPhoto")

    try:
        progressVal = float(progressRaw)
        if progressVal < 0 or progressVal > 100:
            flash("Progress must be between 0% and 100%.", "warning")
            return redirect(url_for("production.monitoringList"))

        existing = ProductionMonitoring.getByID(monitoringID)
        if not existing:
            flash("Monitoring record not found.", "error")
            return redirect(url_for("production.monitoringList"))

        if existing.orderStatus != "In Progress":
            flash(f"Order #PO-{existing.orderID} is '{existing.orderStatus}'. Stage updates are only permitted while 'In Progress'.", "warning")
            return redirect(url_for("production.monitoringList"))

        currentEmpID = session.get("employee_id")
        if not is_staff_session() or not existing.assignedTo or currentEmpID != existing.assignedTo:
            ownerLabel = existing.assignedStaffName or "Unassigned — assign in Production Planning"
            flash(f"Workshop stage updates are restricted to the assigned Production Staff ({ownerLabel}).", "warning")
            return redirect(url_for("production.monitoringList"))

        rawBytes = None
        cleanMime = None
        cleanFilename = None
        if proofFile and proofFile.filename:
            mimeCandidate = (proofFile.mimetype or "").lower().strip()
            if mimeCandidate == "image/jpg":
                mimeCandidate = "image/jpeg"
            if mimeCandidate not in ("image/jpeg", "image/png", "image/webp"):
                flash("Proof attachment must be a JPG, PNG, or WebP image.", "error")
                return redirect(url_for("production.monitoringList"))
            dataBytes = proofFile.read()
            if len(dataBytes) > 4 * 1024 * 1024:
                flash("Proof photo exceeds the 4 MB maximum file size.", "error")
                return redirect(url_for("production.monitoringList"))
            if len(dataBytes) > 0:
                rawBytes = dataBytes
                cleanMime = mimeCandidate
                cleanFilename = os.path.basename(proofFile.filename)[:180]

        stageInt = int(round(progressVal))
        isRollback = progressVal < existing.progress
        isAdvancingToQA = (stageInt >= 90 and not isRollback)
        if isAdvancingToQA and not rawBytes:
            flash("A workshop photo proof is required when submitting Stage 4 (Ready for QA Inspection).", "error")
            return redirect(url_for("production.monitoringList"))

        uploadedFileUrl = None
        if rawBytes:
            uploadedFileUrl = uploadToSupabaseStorage(
                rawBytes=rawBytes,
                mimeType=cleanMime,
                entityType="stage_proof",
                orderID=existing.orderID,
                stageProgress=stageInt
            )

        with openTransaction() as conn:
            updated = ProductionMonitoring.updateProgress(monitoringID, progressVal, conn=conn)
            if updated and stageInt in (25, 50, 75, 90) and (not isRollback or stageNote or uploadedFileUrl):
                ProductionAttachment.createAttachment(
                    orderID=existing.orderID,
                    stageProgress=stageInt,
                    note=stageNote,
                    fileName=cleanFilename,
                    fileUrl=uploadedFileUrl,
                    uploadedBy=currentEmpID,
                    entityType="stage_proof",
                    conn=conn
                )

        if updated:
            stageName = stageLabels.get(stageInt, f"{stageInt}% Progress")
            if stageInt >= 90 and stageInt < 100:
                flash(f"Order #PO-{updated.orderID} submitted with Stage 4 proof! Ready for Manager Quality Inspection.", "success")
            else:
                flash(f"Order #PO-{updated.orderID} updated to {stageName} ({stageInt}%).", "success")
    except RuntimeError as storageErr:
        flash(str(storageErr), "error")
    except ValueError:
        flash("Invalid progress percentage entered.", "error")
    except Exception as err:
        flash(f"Failed to update progress: {str(err)}", "error")

    return redirect(url_for("production.monitoringList"))

@productionBlueprint.route("/finished-goods")
def finishedGoodsList():
    try:
        allMonitoring = ProductionMonitoring.getAll()
        activeCandidateOrders = [m for m in allMonitoring if m.orderStatus == "In Progress" and m.progress >= 90.0]
        pendingOrders = []
        needsAttentionOrders = []
        for m in activeCandidateOrders:
            summaryCounts = ProductionOutput.getOrderInspectionSummary(m.orderID)
            m.alreadyPassed = summaryCounts["passed"]
            m.alreadyFailed = summaryCounts["failed"]
            m.pendingInspectionQty = max(0, int(m.plannedQuantity) - m.alreadyPassed - m.alreadyFailed)
            if m.pendingInspectionQty > 0:
                pendingOrders.append(m)
            else:
                needsAttentionOrders.append(m)

        latestImgMap = ProductionAttachment.getLatestByOrderIDs([m.orderID for m in pendingOrders], requireImage=True)
        for m in pendingOrders:
            m.latestProof = latestImgMap.get(m.orderID)

        outputRecords = ProductionOutput.getAll()
        passedOrderIDs = {o.orderID for o in outputRecords if o.qualityStatus == "Passed"}
        reworkOrdersCount = sum(1 for m in allMonitoring if m.orderStatus == "In Progress" and (m.reworkCount or 0) > 0 and m.progress < 90.0)
        summary = {
            "pending": len(pendingOrders),
            "passed": len(passedOrderIDs),
            "rework": reworkOrdersCount,
            "failed": sum(1 for o in outputRecords if o.qualityStatus == "Failed"),
            "totalUnits": sum(o.quantity for o in outputRecords if o.qualityStatus == "Passed")
        }
    except Exception as err:
        flash(f"Failed to load quality inspection records: {str(err)}", "error")
        pendingOrders = []
        needsAttentionOrders = []
        outputRecords = []
        summary = {"pending": 0, "passed": 0, "rework": 0, "failed": 0, "totalUnits": 0}

    return render_template(
        "production/manufacturing/finished_goods_list.html",
        activeTab="finishedGoods",
        pendingOrders=pendingOrders,
        needsAttentionOrders=needsAttentionOrders,
        outputRecords=outputRecords,
        summary=summary
    )

@productionBlueprint.route("/finished-goods/inspect/<int:orderID>", methods=["POST"])
@manager_required
def recordInspection(orderID):
    passedRaw = request.form.get("passedQuantity", "").strip()
    failedRaw = request.form.get("failedQuantity", "").strip()
    reworkRaw = request.form.get("reworkQuantity", "").strip()
    reason = request.form.get("reason", "").strip()
    scrapConfirmed = request.form.get("scrapConfirmed", "").strip()

    for rawVal in [passedRaw, failedRaw, reworkRaw]:
        if rawVal and (len(rawVal) > 6 or not rawVal.isdecimal()):
            flash("Quantities must be non-negative whole numbers up to 6 digits.", "error")
            return redirect(url_for("production.finishedGoodsList"))

    passedQty = int(passedRaw) if passedRaw else 0
    failedQty = int(failedRaw) if failedRaw else 0
    reworkQty = int(reworkRaw) if reworkRaw else 0

    if passedQty < 0 or failedQty < 0 or reworkQty < 0:
        flash("Quantities cannot be negative numbers.", "error")
        return redirect(url_for("production.finishedGoodsList"))

    if len(reason) > 255:
        flash("Inspection reason cannot exceed 255 characters.", "error")
        return redirect(url_for("production.finishedGoodsList"))

    if (failedQty > 0 or reworkQty > 0) and not reason:
        flash("A reason is mandatory when recording Failed or Rework units.", "error")
        return redirect(url_for("production.finishedGoodsList"))

    if failedQty > 0 and scrapConfirmed != "on":
        flash("Please confirm that failed units will be scrapped.", "warning")
        return redirect(url_for("production.finishedGoodsList"))

    try:
        with openTransaction() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT po.order_id, po.furniture_id, po.planned_quantity, po.status, po.assigned_to, f.furniture_name
                    FROM prod_productionorder po
                    JOIN prod_furniture f ON po.furniture_id = f.furniture_id
                    WHERE po.order_id = %s
                    FOR UPDATE
                """, (orderID,))
                orderRow = cursor.fetchone()

                if not orderRow:
                    flash("Production order not found.", "error")
                    return redirect(url_for("production.finishedGoodsList"))

                if orderRow["status"] != "In Progress":
                    flash(f"Order #PO-{orderID} is '{orderRow['status']}'. Quality inspection is only allowed for 'In Progress' orders.", "warning")
                    return redirect(url_for("production.finishedGoodsList"))

                cursor.execute("""
                    SELECT monitoring_id, progress, COALESCE(rework_count, 0) AS rework_count
                    FROM prod_productionmonitoring
                    WHERE order_id = %s
                    FOR UPDATE
                """, (orderID,))
                monitoringRow = cursor.fetchone()

                if not monitoringRow or float(monitoringRow["progress"]) < 90.0:
                    currentProg = int(round(float(monitoringRow["progress"]))) if monitoringRow else 0
                    flash(f"Order #PO-{orderID} assembly is at {currentProg}%. Workshop assembly must reach at least 90% before inspection.", "warning")
                    return redirect(url_for("production.finishedGoodsList"))

                cursor.execute("""
                    SELECT 
                        COALESCE(SUM(CASE WHEN quality_status = 'Passed' THEN quantity ELSE 0 END), 0) AS total_passed,
                        COALESCE(SUM(CASE WHEN quality_status = 'Failed' THEN quantity ELSE 0 END), 0) AS total_failed
                    FROM prod_productionoutput
                    WHERE order_id = %s
                """, (orderID,))
                countsRow = cursor.fetchone()
                alreadyPassed = int(countsRow["total_passed"])
                alreadyFailed = int(countsRow["total_failed"])
                plannedQty = int(orderRow["planned_quantity"])
                pendingQty = plannedQty - alreadyPassed - alreadyFailed

                totalInspect = passedQty + failedQty + reworkQty
                if pendingQty <= 0 or totalInspect != pendingQty:
                    flash("Pending units changed, please refresh and try again.", "error")
                    return redirect(url_for("production.finishedGoodsList"))

                currentReworks = int(monitoringRow["rework_count"])
                if reworkQty > 0 and currentReworks >= 2:
                    flash(f"Order #PO-{orderID} has reached maximum allowed reworks (2). Units must either Pass or be marked as Failed/Scrapped.", "error")
                    return redirect(url_for("production.finishedGoodsList"))

                inspectorName = session.get("employee_name", "Dave Cagalitan")
                rawUserID = session.get("user_id")
                inspectorID = int(rawUserID) if (rawUserID and str(rawUserID).isdecimal()) else None

                if passedQty > 0:
                    ProductionOutput.recordOutput(
                        orderID=orderID,
                        furnitureID=orderRow["furniture_id"],
                        quantity=passedQty,
                        qualityStatus="Passed",
                        recordedBy=inspectorName,
                        reason=None,
                        inspectorID=inspectorID,
                        conn=conn
                    )
                    integration.add_finished_goods_stock(orderRow["furniture_id"], passedQty, conn=conn)

                if reworkQty > 0:
                    ProductionOutput.recordOutput(
                        orderID=orderID,
                        furnitureID=orderRow["furniture_id"],
                        quantity=reworkQty,
                        qualityStatus="Rework",
                        recordedBy=inspectorName,
                        reason=reason,
                        inspectorID=inspectorID,
                        conn=conn
                    )
                    reworkProgress = ProductionMonitoring.REWORK_STAGE_PROGRESS
                    ProductionMonitoring.updateProgressAndRework(
                        monitoringRow["monitoring_id"],
                        reworkProgress,
                        currentReworks + 1,
                        conn=conn
                    )

                if failedQty > 0:
                    ProductionOutput.recordOutput(
                        orderID=orderID,
                        furnitureID=orderRow["furniture_id"],
                        quantity=failedQty,
                        qualityStatus="Failed",
                        recordedBy=inspectorName,
                        reason=reason,
                        inspectorID=inspectorID,
                        conn=conn
                    )

                unitWord = "unit" if failedQty == 1 else "units"
                if reworkQty == 0:
                    ProductionMonitoring.updateProgress(monitoringRow["monitoring_id"], 100.0, conn=conn)
                    ProductionOrder.updateStatus(orderID, "Completed", conn=conn)
                    msg = f"Order #PO-{orderID} finalized: {passedQty} passed & stocked to Finished Goods"
                    if failedQty > 0:
                        msg += f", {failedQty} {unitWord} scrapped"
                    flash(msg + ".", "success")
                else:
                    msg = f"Order #PO-{orderID} QA submitted: {passedQty} passed, {reworkQty} returned to workshop (Rework #{currentReworks + 1}/2 at {int(ProductionMonitoring.REWORK_STAGE_PROGRESS)}%)"
                    if failedQty > 0:
                        msg += f", {failedQty} {unitWord} scrapped"
                    flash(msg + ".", "warning")

    except ValueError as valErr:
        flash(str(valErr), "warning")
    except Exception as err:
        flash(f"Database error during quality inspection: {str(err)}", "error")

    return redirect(url_for("production.finishedGoodsList"))

@productionBlueprint.route("/costing")
@manager_required
def costingList():
    try:
        allOrders = ProductionOrder.getAll()
        costOrders = [o for o in allOrders if o.status in ("In Progress", "Completed")]
        for o in costOrders:
            savedCost = ProductionCost.getByOrderID(o.orderID)
            if savedCost:
                o.hasCostSheet = True
                o.costID = savedCost.costID
                o.materialCost = savedCost.materialCost
                o.laborCost = savedCost.laborCost
                o.overheadCost = savedCost.overheadCost
                o.totalCost = savedCost.totalCost
                o.unitCost = savedCost.unitCost
                o.costDate = savedCost.costDate
                o.formattedCostDate = savedCost.formattedCostDate
            else:
                o.hasCostSheet = False
                o.costID = None
                o.materialCost = ProductionCost.calculateActualMaterialCost(o.orderID)
                o.laborCost = Decimal("0.00")
                o.overheadCost = ProductionCost.calculateOverhead(o.materialCost)
                o.totalCost = o.materialCost + o.laborCost + o.overheadCost
                o.unitCost = (o.totalCost / Decimal(str(o.plannedQuantity))).quantize(Decimal("0.01")) if o.plannedQuantity else Decimal("0.00")
                o.costDate = None
                o.formattedCostDate = "-"

            goodCost, passedUnits = ProductionCost.calculateCostPerGoodUnit(o.orderID, o.totalCost)
            o.costPerGoodUnit = goodCost
            o.passedUnits = passedUnits

        allCostRecords = ProductionCost.getAll()
        totalRecordedCost = sum(c.totalCost for c in allCostRecords)
        summary = {
            "totalCost": totalRecordedCost,
            "costedOrders": len(allCostRecords),
            "pendingCosting": sum(1 for o in costOrders if not o.hasCostSheet),
            "activeOrders": len(costOrders),
            "overheadPercent": int(round(ProductionCost.DEFAULT_OVERHEAD_PERCENT * 100))
        }
    except Exception as err:
        flash(f"Failed to load production costing records: {str(err)}", "error")
        costOrders = []
        allCostRecords = []
        summary = {"totalCost": Decimal("0.00"), "costedOrders": 0, "pendingCosting": 0, "activeOrders": 0, "overheadPercent": int(round(ProductionCost.DEFAULT_OVERHEAD_PERCENT * 100))}

    return render_template(
        "production/costing/costing_list.html",
        activeTab="costing",
        costOrders=costOrders,
        costs=allCostRecords,
        summary=summary
    )

@productionBlueprint.route("/costing/save/<int:orderID>", methods=["POST"])
@manager_required
def saveOrderCost(orderID):
    matRaw = request.form.get("materialCost", "").strip()
    labRaw = request.form.get("laborCost", "").strip()
    overRaw = request.form.get("overheadCost", "").strip()

    try:
        order = ProductionOrder.getByID(orderID)
        if not order:
            flash("Production order not found.", "error")
            return redirect(url_for("production.costingList"))

        if matRaw:
            try:
                matCost = Decimal(matRaw)
            except InvalidOperation:
                flash("Invalid material cost entered.", "error")
                return redirect(url_for("production.costingList"))
        else:
            matCost = ProductionCost.calculateActualMaterialCost(orderID)

        try:
            labCost = Decimal(labRaw) if labRaw else Decimal("0.00")
        except InvalidOperation:
            flash("Invalid labor cost entered.", "error")
            return redirect(url_for("production.costingList"))

        try:
            overCost = Decimal(overRaw) if overRaw else ProductionCost.calculateOverhead(matCost)
        except InvalidOperation:
            flash("Invalid overhead cost entered.", "error")
            return redirect(url_for("production.costingList"))

        if matCost < Decimal("0.00") or labCost < Decimal("0.00") or overCost < Decimal("0.00"):
            flash("Cost values cannot be negative.", "warning")
            return redirect(url_for("production.costingList"))

        saved = ProductionCost.saveCost(
            orderID=orderID,
            materialCost=matCost,
            laborCost=labCost,
            overheadCost=overCost
        )
        flash(f"Cost sheet saved for Order #PO-{orderID} (Total: ₱{saved.totalCost:,.2f})! Available for Team 5 Finance.", "success")
    except ValueError as valErr:
        flash(str(valErr), "warning")
    except Exception as err:
        flash(f"Database error while saving production cost: {str(err)}", "error")

    return redirect(url_for("production.costingList"))

@productionBlueprint.route("/report")
@productionBlueprint.route("/reports")
@manager_required
def reportView():
    statusFilter = request.args.get("status", "All").strip()

    try:
        with openTransaction() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT po.order_id,
                           po.planned_quantity,
                           po.status,
                           po.order_date,
                           po.planned_start_date,
                           po.due_date,
                           f.furniture_name,
                           f.furniture_type,
                           f.selling_price,
                           COALESCE(pm.progress, 0.00) AS progress,
                           pm.start_date AS actual_start_date,
                           pm.completion_date,
                           pc.cost_id,
                           pc.material_cost,
                           pc.labor_cost,
                           pc.overhead_cost,
                           pc.total_cost,
                           pc.cost_date
                    FROM prod_productionorder po
                    JOIN prod_furniture f ON po.furniture_id = f.furniture_id
                    LEFT JOIN prod_productionmonitoring pm ON po.order_id = pm.order_id
                    LEFT JOIN prod_productioncost pc ON po.order_id = pc.order_id
                    ORDER BY po.order_id DESC
                """)
                rawOrders = cur.fetchall()

                cur.execute("""
                    SELECT rm.raw_material_id,
                           im.item_name AS material_name,
                           im.unit,
                           rm.unit_cost,
                           COALESCE(SUM(mi.quantity_issued), 0) AS total_quantity_issued,
                           COALESCE(SUM(mi.quantity_issued * rm.unit_cost), 0.00) AS total_material_expense,
                           COUNT(DISTINCT mi.order_id) AS orders_consumed_count
                    FROM prod_materialissuance mi
                    JOIN raw_material rm ON mi.material_id = rm.raw_material_id
                    JOIN item_master im ON rm.item_id = im.item_id
                    GROUP BY rm.raw_material_id, im.item_name, im.unit, rm.unit_cost
                    ORDER BY total_material_expense DESC
                """)
                materialUsageRows = cur.fetchall()

        allOrders = []
        for r in rawOrders:
            item = dict(r)
            item["formattedOrderDate"] = item["order_date"].strftime("%b. %d, %Y") if item.get("order_date") else "-"
            item["formattedDueDate"] = item["due_date"].strftime("%b. %d, %Y") if item.get("due_date") else "-"
            item["formattedStartDate"] = item["actual_start_date"].strftime("%b. %d, %Y") if item.get("actual_start_date") else (item["planned_start_date"].strftime("%b. %d, %Y") if item.get("planned_start_date") else "-")
            item["formattedCompletionDate"] = item["completion_date"].strftime("%b. %d, %Y") if item.get("completion_date") else ("In Progress" if item["status"] == "In Progress" else "-")
            qty = Decimal(str(item.get("planned_quantity") or 0))
            price = Decimal(str(item.get("selling_price") or 0))
            item["estimatedValue"] = qty * price
            allOrders.append(item)

        totalOrders = len(allOrders)
        completedOrders = sum(1 for o in allOrders if o["status"] == "Completed")
        inProgressOrders = sum(1 for o in allOrders if o["status"] == "In Progress")
        releasedOrders = sum(1 for o in allOrders if o["status"] == "Released")
        draftOrders = sum(1 for o in allOrders if o["status"] == "Draft")

        totalPlannedUnits = sum(int(o["planned_quantity"]) for o in allOrders)
        totalCompletedUnits = sum(int(o["planned_quantity"]) for o in allOrders if o["status"] == "Completed")
        completionRate = int(round((completedOrders / totalOrders * 100))) if totalOrders > 0 else 0

        totalRecordedCost = sum(Decimal(str(o["total_cost"])) for o in allOrders if o.get("total_cost") is not None)
        totalMaterialExpense = sum(Decimal(str(m["total_material_expense"])) for m in materialUsageRows)
        totalPlannedValue = sum(o["estimatedValue"] for o in allOrders)

        summary = {
            "totalOrders": totalOrders,
            "completedOrders": completedOrders,
            "inProgressOrders": inProgressOrders,
            "releasedOrders": releasedOrders,
            "draftOrders": draftOrders,
            "totalPlannedUnits": totalPlannedUnits,
            "totalCompletedUnits": totalCompletedUnits,
            "completionRate": completionRate,
            "totalRecordedCost": totalRecordedCost,
            "totalMaterialExpense": totalMaterialExpense,
            "totalPlannedValue": totalPlannedValue
        }

        if statusFilter in ("Completed", "In Progress", "Released", "Draft"):
            filteredOrders = [o for o in allOrders if o["status"] == statusFilter]
        else:
            statusFilter = "All"
            filteredOrders = allOrders

        issuances = MaterialIssuance.getAll()
        outputRecords = ProductionOutput.getAll()
        activityDates = []
        for iss in issuances:
            if iss.issueDate:
                activityDates.append(iss.issueDate)
        for o in outputRecords:
            if o.inspectionDate:
                activityDates.append(o.inspectionDate)
        if activityDates:
            latest = max(activityDates)
            lastActivity = latest.strftime("%b. %d, %Y") if hasattr(latest, "strftime") else str(latest)
        else:
            lastActivity = "-"

    except Exception as err:
        flash(f"Failed to load production reports: {str(err)}", "error")
        filteredOrders = []
        materialUsageRows = []
        issuances = []
        outputRecords = []
        lastActivity = "-"
        summary = {
            "totalOrders": 0,
            "completedOrders": 0,
            "inProgressOrders": 0,
            "releasedOrders": 0,
            "draftOrders": 0,
            "totalPlannedUnits": 0,
            "totalCompletedUnits": 0,
            "completionRate": 0,
            "totalRecordedCost": Decimal("0.00"),
            "totalMaterialExpense": Decimal("0.00"),
            "totalPlannedValue": Decimal("0.00")
        }

    return render_template(
        "production/reports/report_view.html",
        activeTab="report",
        reportRows=filteredOrders,
        materialUsage=materialUsageRows,
        summary=summary,
        currentFilter=statusFilter,
        issuances=issuances,
        outputRecords=outputRecords,
        lastActivity=lastActivity
    )

@productionBlueprint.route("/logs")
@manager_required
def logsView():
    return redirect(url_for("production.reportView", tab="audit"))



