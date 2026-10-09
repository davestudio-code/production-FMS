from flask import Blueprint, render_template, request, redirect, url_for, flash
from decimal import Decimal, InvalidOperation
from datetime import date
from psycopg2.errors import UniqueViolation
from .db import openTransaction
from .models.furniture import Furniture
from .models.material import Material
from .models.billofmaterials import BillOfMaterials
from .models.bomitem import BOMItem
from .models.productionorder import ProductionOrder

productionBlueprint = Blueprint(
    "production",
    __name__,
    template_folder="templates",
    static_folder="static"
)

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
    metricsData = {
        "totalOrders": 0,
        "inProgressOrders": 0,
        "completedOrders": 0,
        "lowStockCount": 0
    }
    recentOrdersList = []
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
    materialIssuanceList = []
    return render_template(
        "production/issuance_list.html",
        activeTab="issuance",
        issuances=materialIssuanceList
    )

@productionBlueprint.route("/monitoring")
def monitoringList():
    productionMonitoringList = []
    return render_template(
        "production/monitoring_list.html",
        activeTab="monitoring",
        monitorings=productionMonitoringList
    )

@productionBlueprint.route("/finished-goods")
def finishedGoodsList():
    finishedGoodsRecordList = []
    return render_template(
        "production/finished_goods_list.html",
        activeTab="finishedGoods",
        finishedGoodsList=finishedGoodsRecordList
    )

@productionBlueprint.route("/costing")
def costingList():
    productionCostList = []
    return render_template(
        "production/costing_list.html",
        activeTab="costing",
        costs=productionCostList
    )

@productionBlueprint.route("/report")
def reportView():
    productionReportList = []
    return render_template(
        "production/report_view.html",
        activeTab="report",
        reportRows=productionReportList
    )
