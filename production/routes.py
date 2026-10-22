from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from decimal import Decimal, InvalidOperation
from datetime import date
from psycopg2.errors import UniqueViolation
from .db import openTransaction
from .auth import authenticate_credentials, login_required, roles_required
from .models.furniture import Furniture
from .models.material import Material
from .models.billofmaterials import BillOfMaterials
from .models.bomitem import BOMItem
from .models.productionorder import ProductionOrder
from .models.materialissuance import MaterialIssuance
from .models.monitoring import ProductionMonitoring
from .models.productionoutput import ProductionOutput
from .models.productioncost import ProductionCost
from . import integration

productionBlueprint = Blueprint(
    "production",
    __name__,
    template_folder="templates",
    static_folder="static"
)

@productionBlueprint.before_request
def requireLogin():
    if request.endpoint in ("production.login", "production.logout", "production.static"):
        return
    if not session.get("user_id"):
        return redirect(url_for("production.login", next=request.path))

@productionBlueprint.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("production.index"))
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        user_record, error_message = authenticate_credentials(email, password)
        if error_message:
            flash(error_message, "danger")
            return render_template("production/login.html")
        session["user_id"] = user_record.get("user_id") or user_record.get("employee_id") or user_record.get("auth_user_id")
        session["email"] = user_record.get("email")
        name = user_record.get("name") or ""
        last_name = user_record.get("last_name") or ""
        full_name = f"{name} {last_name}".strip()
        session["employee_name"] = full_name if full_name else user_record.get("email")
        session["role"] = user_record.get("assigned_role", "prodStaff")
        session["position"] = user_record.get("position_name")
        flash(f"Welcome back, {session['employee_name']}!", "success")
        next_page = request.args.get("next")
        if next_page and next_page.startswith("/production") and not next_page.startswith("/production/logout") and not next_page.startswith("/production/login"):
            return redirect(next_page)
        return redirect(url_for("production.index"))
    return render_template("production/login.html")

@productionBlueprint.route("/logout")
def logout():
    session.clear()
    flash("You have been signed out successfully.", "info")
    return redirect(url_for("production.login"))

def getDatabaseStatus():
    try:
        with openTransaction() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                return None
    except Exception as connectionError:
        return f"Database Offline: {str(connectionError)}"

@productionBlueprint.route("/")
def index():
    databaseStatusMessage = getDatabaseStatus()
    try:
        allOrders = ProductionOrder.getAll()
        materials = Material.getAll()
    except Exception as err:
        allOrders = []
        materials = []

    metricsData = {
        "totalOrders": len(allOrders),
        "inProgressOrders": sum(1 for o in allOrders if o.status == "In Progress"),
        "completedOrders": sum(1 for o in allOrders if o.status == "Completed"),
        "lowStockCount": sum(1 for m in materials if m.currentStock <= Decimal("0.000"))
    }

    recentOrdersList = allOrders[:5]
    integrationEventsList = []

    return render_template(
        "production/dashboard.html",
        activeTab="dashboard",
        databaseStatus=databaseStatusMessage,
        metrics=metricsData,
        recentOrders=recentOrdersList,
        integrationEvents=integrationEventsList
    )

@productionBlueprint.route("/furniture")
def furnitureList():
    searchQuery = request.args.get("q", "").strip()
    selectedCategory = request.args.get("category", "").strip()
    try:
        furnitureItemList = Furniture.getAll(
            searchQuery=searchQuery if searchQuery else None,
            category=selectedCategory if selectedCategory else None
        )
        categoriesList = Furniture.getCategories()
    except Exception as err:
        flash(f"Failed to load products from database: {str(err)}", "alert")
        furnitureItemList = []
        categoriesList = []

    return render_template(
        "production/furniture_list.html",
        activeTab="furniture",
        furnitureItems=furnitureItemList,
        categories=categoriesList,
        searchQuery=searchQuery,
        selectedCategory=selectedCategory
    )

@productionBlueprint.route("/furniture/add", methods=["POST"])
@roles_required("prodManager")
def addFurniture():
    furnitureName = request.form.get("furnitureName", "").strip()
    furnitureType = request.form.get("furnitureType", "").strip()
    priceRaw = request.form.get("sellingPrice", "").strip()

    if not furnitureName or not furnitureType or not priceRaw:
        flash("Product name, category, and selling price are required.", "error")
        return redirect(url_for("production.furnitureList"))

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
@roles_required("prodManager")
def editFurniture(furnitureID):
    furnitureName = request.form.get("furnitureName", "").strip()
    furnitureType = request.form.get("furnitureType", "").strip()
    priceRaw = request.form.get("sellingPrice", "").strip()

    if not furnitureName or not furnitureType or not priceRaw:
        flash("Product name, category, and selling price are required.", "error")
        return redirect(url_for("production.furnitureList"))

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
@roles_required("prodManager")
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
        "production/material_list.html",
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
        except Exception as err:
            flash(f"Failed to load BOM recipe: {str(err)}", "error")

    try:
        materialsList = Material.getAll()
    except Exception as err:
        flash(f"Failed to load raw materials: {str(err)}", "error")
        materialsList = []

    return render_template(
        "production/bom_list.html",
        activeTab="bom",
        furnitureItems=furnitureItemList,
        selectedFurniture=selectedFurniture,
        bom=bom,
        bomItems=bomItems,
        requirements=requirements,
        materials=materialsList,
        batchQuantity=batchQuantity,
        unitTotalCost=unitTotalCost,
        batchTotalCost=batchTotalCost
    )

@productionBlueprint.route("/bom/add", methods=["POST"])
@roles_required("prodManager")
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
@roles_required("prodManager")
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

@productionBlueprint.route("/orders")
def orderList():
    statusFilter = request.args.get("status", "").strip()
    searchQuery = request.args.get("q", "").strip()
    try:
        productionOrderList = ProductionOrder.getAll(statusFilter=statusFilter, searchQuery=searchQuery)
        summary = ProductionOrder.getSummaryCounts()
        furnitureItemList = Furniture.getAll()
    except Exception as err:
        flash(f"Failed to load production orders: {str(err)}", "error")
        productionOrderList = []
        summary = {"total": 0, "draft": 0, "released": 0, "inProgress": 0, "completed": 0}
        furnitureItemList = []

    return render_template(
        "production/order_list.html",
        activeTab="orders",
        orders=productionOrderList,
        summary=summary,
        furnitureItems=furnitureItemList,
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
        requirements = bom.calculateRequirements(order.plannedQuantity) if bom else []
    except Exception as err:
        flash(f"Failed to load order details: {str(err)}", "error")
        return redirect(url_for("production.orderList"))

    return render_template(
        "production/order_detail.html",
        activeTab="orders",
        order=order,
        requirements=requirements,
        estimatedUnitMaterialCost=estimatedUnitMaterialCost,
        estimatedBatchMaterialCost=estimatedBatchMaterialCost
    )

@productionBlueprint.route("/orders/create", methods=["POST"])
@roles_required("prodManager")
def createOrder():
    furnitureIDRaw = request.form.get("furnitureID", "").strip()
    quantityRaw = request.form.get("plannedQuantity", "").strip()
    startDateRaw = request.form.get("plannedStartDate", "").strip()
    dueDateRaw = request.form.get("dueDate", "").strip()

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
        flash("Cannot create production order: Selected product has no Bill of Materials (recipe). Please configure its BOM first.", "warning")
        return redirect(url_for("production.orderList"))

    try:
        newOrderID = ProductionOrder.createOrder(
            furnitureID=furnitureID,
            plannedQuantity=plannedQuantity,
            plannedStartDate=parsedStartDate,
            dueDate=parsedDueDate
        )
        flash(f"Production Order #PO-{newOrderID} created successfully in Draft status.", "success")
    except ValueError as valErr:
        flash(str(valErr), "warning")
    except Exception as err:
        flash(f"Database error while creating production order: {str(err)}", "error")

    return redirect(url_for("production.orderList"))

@productionBlueprint.route("/orders/delete/<int:orderID>", methods=["POST"])
@roles_required("prodManager")
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
        plannedOrders = ProductionOrder.getPlanningOrders(statusFilter=statusFilter, searchQuery=searchQuery)
        totalCount = len(plannedOrders)
        scheduledCount = sum(1 for o in plannedOrders if o.plannedStartDate and o.dueDate)
        needsDatesCount = sum(1 for o in plannedOrders if not o.plannedStartDate and not o.dueDate)
        overdueCount = sum(1 for o in plannedOrders if o.scheduleHealth == "Overdue")
        summary = {
            "total": totalCount,
            "scheduled": scheduledCount,
            "needsDates": needsDatesCount,
            "overdue": overdueCount
        }
    except Exception as err:
        flash(f"Failed to load production planning orders: {str(err)}", "error")
        plannedOrders = []
        summary = {"total": 0, "scheduled": 0, "needsDates": 0, "overdue": 0}

    return render_template(
        "production/planning.html",
        activeTab="planning",
        plannedOrders=plannedOrders,
        summary=summary,
        statusFilter=statusFilter,
        searchQuery=searchQuery
    )

@productionBlueprint.route("/planning/update/<int:orderID>", methods=["POST"])
@roles_required("prodManager")
def updateOrderSchedule(orderID):
    startDateRaw = request.form.get("plannedStartDate", "").strip()
    dueDateRaw = request.form.get("dueDate", "").strip()

    parsedStartDate = None
    if startDateRaw:
        try:
            parsedStartDate = date.fromisoformat(startDateRaw)
        except ValueError:
            flash("Invalid planned start date format.", "error")
            return redirect(url_for("production.planningList"))

    parsedDueDate = None
    if dueDateRaw:
        try:
            parsedDueDate = date.fromisoformat(dueDateRaw)
        except ValueError:
            flash("Invalid target due date format.", "error")
            return redirect(url_for("production.planningList"))

    if parsedStartDate and parsedDueDate and parsedDueDate < parsedStartDate:
        flash("Target due date cannot be earlier than planned start date.", "error")
        return redirect(url_for("production.planningList"))

    try:
        ProductionOrder.updateSchedule(orderID, parsedStartDate, parsedDueDate)
        flash(f"Schedule updated for Order #PO-{orderID}.", "success")
    except ValueError as valErr:
        flash(str(valErr), "warning")
    except Exception as err:
        flash(f"Database error while updating schedule: {str(err)}", "error")

    return redirect(url_for("production.planningList"))

@productionBlueprint.route("/requirements")
def requirementList():
    try:
        allOrders = ProductionOrder.getAll()
    except Exception as err:
        flash(f"Failed to load production orders: {str(err)}", "error")
        allOrders = []

    activeOrdersList = [o for o in allOrders if o.status != "Completed"]
    if not activeOrdersList:
        activeOrdersList = allOrders

    orderIDParam = request.args.get("order_id", "").strip()
    selectedOrder = None

    if orderIDParam and orderIDParam.isdigit():
        try:
            selectedOrder = ProductionOrder.getByID(int(orderIDParam))
        except Exception:
            selectedOrder = None

    if not selectedOrder and activeOrdersList:
        selectedOrder = activeOrdersList[0]

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

            for req in rawReqs:
                mat = Material.getByID(req["materialID"])
                onHand = mat.currentStock if mat else Decimal("0.000")
                required = req["batchQuantity"]
                shortage = max(Decimal("0.000"), required - onHand)
                isShort = onHand < required

                if isShort:
                    hasShortage = True
                    shortageCount += 1

                totalEstimatedCost += req["batchCost"]

                requirementsList.append({
                    "materialID": req["materialID"],
                    "materialName": req["materialName"],
                    "unit": req["unit"],
                    "quantityRequired": req["quantityRequired"],
                    "requiredQuantity": required,
                    "onHandQuantity": onHand,
                    "shortageQuantity": shortage,
                    "isShort": isShort,
                    "unitCost": req["unitCost"],
                    "batchCost": req["batchCost"]
                })
        except Exception as err:
            flash(f"Failed to calculate material requirements: {str(err)}", "error")

    return render_template(
        "production/requirement.html",
        activeTab="requirement",
        activeOrders=allOrders,
        selectedOrder=selectedOrder,
        requirementsList=requirementsList,
        hasShortage=hasShortage,
        shortageCount=shortageCount,
        hasBOM=hasBOM,
        totalEstimatedCost=totalEstimatedCost
    )

@productionBlueprint.route("/requirements/release/<int:orderID>", methods=["POST"])
@roles_required("prodManager")
def releaseOrder(orderID):
    try:
        order = ProductionOrder.getByID(orderID)
        if not order:
            flash("Production order not found.", "error")
            return redirect(url_for("production.requirementList"))

        if order.status != "Draft":
            flash(f"Order #PO-{orderID} cannot be released because it is currently '{order.status}'.", "warning")
            return redirect(url_for("production.requirementList", order_id=orderID))

        bom = BillOfMaterials.getByFurnitureID(order.furnitureID, autoCreate=True)
        batchQty = Decimal(str(order.plannedQuantity))
        reqs = bom.calculateRequirements(batchQty)

        if not reqs:
            flash(f"Cannot release order: No BOM recipe components defined for '{order.furnitureName}'.", "warning")
            return redirect(url_for("production.requirementList", order_id=orderID))

        shortageList = []
        for r in reqs:
            mat = Material.getByID(r["materialID"])
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
        for o in releasedOrders:
            bom = BillOfMaterials.getByFurnitureID(o.furnitureID, autoCreate=False)
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
        "production/issuance_list.html",
        activeTab="issuance",
        releasedOrders=releasedOrders,
        issuances=materialIssuanceList
    )

@productionBlueprint.route("/issuance/issue/<int:orderID>", methods=["POST"])
@roles_required("prodManager")
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
                MaterialIssuance.recordIssuance(orderID, r["materialID"], r["batchQuantity"], conn=conn)

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
        summary = {
            "total": len(productionMonitoringList),
            "inProgress": sum(1 for m in productionMonitoringList if m.progress < 100),
            "completed": sum(1 for m in productionMonitoringList if m.progress >= 100)
        }
    except Exception as err:
        flash(f"Failed to load monitoring records: {str(err)}", "error")
        productionMonitoringList = []
        summary = {"total": 0, "inProgress": 0, "completed": 0}

    return render_template(
        "production/monitoring_list.html",
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

        updated = ProductionMonitoring.updateProgress(monitoringID, progressVal)
        if updated:
            stageName = stageLabels.get(int(round(progressVal)), f"{int(round(progressVal))}% Progress")
            if progressVal >= 90 and progressVal < 100:
                flash(f"Order #PO-{updated.orderID} workshop assembly completed: {stageName} ({int(round(progressVal))}%)! Ready for Quality Inspection.", "success")
            elif progressVal >= 100:
                flash(f"Order #PO-{updated.orderID} finalized: {stageName} (100%)!", "success")
            else:
                flash(f"Order #PO-{updated.orderID} updated to {stageName} ({int(round(progressVal))}%).", "success")
    except ValueError:
        flash("Invalid progress percentage entered.", "error")
    except Exception as err:
        flash(f"Failed to update progress: {str(err)}", "error")

    return redirect(url_for("production.monitoringList"))

@productionBlueprint.route("/finished-goods")
def finishedGoodsList():
    try:
        allMonitoring = ProductionMonitoring.getAll()
        pendingOrders = [m for m in allMonitoring if m.orderStatus == "In Progress" and m.progress >= 90.0]
        outputRecords = ProductionOutput.getAll()
        summary = {
            "pending": len(pendingOrders),
            "passed": sum(1 for o in outputRecords if o.qualityStatus == "Passed"),
            "rework": sum(1 for o in outputRecords if o.qualityStatus == "Rework"),
            "failed": sum(1 for o in outputRecords if o.qualityStatus == "Failed"),
            "totalUnits": sum(o.quantity for o in outputRecords if o.qualityStatus == "Passed")
        }
    except Exception as err:
        flash(f"Failed to load quality inspection records: {str(err)}", "error")
        pendingOrders = []
        outputRecords = []
        summary = {"pending": 0, "passed": 0, "rework": 0, "failed": 0, "totalUnits": 0}

    return render_template(
        "production/finished_goods_list.html",
        activeTab="finishedGoods",
        pendingOrders=pendingOrders,
        outputRecords=outputRecords,
        summary=summary
    )

@productionBlueprint.route("/finished-goods/inspect/<int:orderID>", methods=["POST"])
@roles_required("prodManager")
def recordInspection(orderID):
    statusChoice = request.form.get("qualityStatus", "Passed").strip()
    qtyRaw = request.form.get("quantity", "").strip()

    if statusChoice not in ProductionOutput.VALID_STATUSES:
        flash("Invalid quality inspection status selected.", "error")
        return redirect(url_for("production.finishedGoodsList"))

    try:
        order = ProductionOrder.getByID(orderID)
        if not order:
            flash("Production order not found.", "error")
            return redirect(url_for("production.finishedGoodsList"))

        if order.status != "In Progress":
            flash(f"Order #PO-{orderID} is '{order.status}'. Quality inspection is only allowed for 'In Progress' orders.", "warning")
            return redirect(url_for("production.finishedGoodsList"))

        monitoring = ProductionMonitoring.getByOrderID(orderID)
        if not monitoring or monitoring.progress < 90.0:
            currentProg = int(round(monitoring.progress)) if monitoring else 0
            flash(f"Order #PO-{orderID} assembly is at {currentProg}%. Workshop assembly must reach at least 90% before inspection.", "warning")
            return redirect(url_for("production.finishedGoodsList"))

        inspectQty = int(qtyRaw) if qtyRaw else int(order.plannedQuantity)
        if inspectQty < 1:
            flash("Inspected quantity must be at least 1 unit.", "error")
            return redirect(url_for("production.finishedGoodsList"))

        with openTransaction() as conn:
            ProductionOutput.recordOutput(
                orderID=orderID,
                furnitureID=order.furnitureID,
                quantity=inspectQty,
                qualityStatus=statusChoice,
                conn=conn
            )

            if statusChoice == "Passed":
                ProductionMonitoring.updateProgress(monitoring.monitoringID, 100.0, conn=conn)
                ProductionOrder.updateStatus(orderID, "Completed", conn=conn)
                integration.add_finished_goods_stock(order.furnitureID, inspectQty, conn=conn)
                flash(f"Quality inspection PASSED for Order #PO-{orderID}! {inspectQty} units of '{order.furnitureName}' transferred to Finished Goods inventory.", "success")
            elif statusChoice == "Rework":
                ProductionMonitoring.updateProgress(monitoring.monitoringID, 75.0, conn=conn)
                flash(f"Order #PO-{orderID} marked for REWORK. Assembly progress rolled back to 75% for workshop correction.", "warning")
            elif statusChoice == "Failed":
                flash(f"Order #PO-{orderID} recorded as FAILED inspection. {inspectQty} units rejected.", "error")

    except ValueError as valErr:
        flash(str(valErr), "warning")
    except Exception as err:
        flash(f"Database error during quality inspection: {str(err)}", "error")

    return redirect(url_for("production.finishedGoodsList"))

@productionBlueprint.route("/costing")
@roles_required("prodManager")
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
        "production/costing_list.html",
        activeTab="costing",
        costOrders=costOrders,
        costs=allCostRecords,
        summary=summary
    )

@productionBlueprint.route("/costing/save/<int:orderID>", methods=["POST"])
@roles_required("prodManager")
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
@roles_required("prodManager")
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
            item["formattedOrderDate"] = item["order_date"].strftime("%b %d, %Y") if item.get("order_date") else "-"
            item["formattedDueDate"] = item["due_date"].strftime("%b %d, %Y") if item.get("due_date") else "-"
            item["formattedStartDate"] = item["actual_start_date"].strftime("%b %d, %Y") if item.get("actual_start_date") else (item["planned_start_date"].strftime("%b %d, %Y") if item.get("planned_start_date") else "-")
            item["formattedCompletionDate"] = item["completion_date"].strftime("%b %d, %Y") if item.get("completion_date") else ("In Progress" if item["status"] == "In Progress" else "-")
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

    except Exception as err:
        flash(f"Failed to load production reports: {str(err)}", "error")
        filteredOrders = []
        materialUsageRows = []
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
        "production/report_view.html",
        activeTab="report",
        reportRows=filteredOrders,
        materialUsage=materialUsageRows,
        summary=summary,
        currentFilter=statusFilter
    )

@productionBlueprint.route("/logs")
@roles_required("prodManager")
def logsView():
    try:
        issuances = MaterialIssuance.getAll()
        outputRecords = ProductionOutput.getAll()
    except Exception as err:
        flash(f"Failed to load production logs: {str(err)}", "error")
        issuances = []
        outputRecords = []

    return render_template(
        "production/logs.html",
        activeTab="logs",
        issuances=issuances,
        outputRecords=outputRecords
    )

