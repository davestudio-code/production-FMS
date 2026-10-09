from datetime import date
from decimal import Decimal
from production.db import openTransaction
from .billofmaterials import BillOfMaterials

class ProductionOrder:
    VALID_STATUSES = ("Draft", "Released", "In Progress", "Completed")

    def __init__(self, data=None):
        if data:
            self.orderID = data.get("order_id")
            self.furnitureID = data.get("furniture_id")
            self.furnitureName = data.get("furniture_name", "")
            self.furnitureType = data.get("furniture_type", "")
            self.salesOrderItemID = data.get("sales_order_item_id")
            self.plannedQuantity = data.get("planned_quantity", 0)
            self.orderDate = data.get("order_date")
            self.plannedStartDate = data.get("planned_start_date")
            self.dueDate = data.get("due_date")
            self.status = data.get("status", "Draft")
        else:
            self.orderID = None
            self.furnitureID = None
            self.furnitureName = ""
            self.furnitureType = ""
            self.salesOrderItemID = None
            self.plannedQuantity = 0
            self.orderDate = None
            self.plannedStartDate = None
            self.dueDate = None
            self.status = "Draft"

    @property
    def orderType(self):
        if self.salesOrderItemID is None:
            return "Make-to-Stock"
        return f"Make-to-Order (Sales #{self.salesOrderItemID})"

    @property
    def scheduleHealth(self):
        if self.status == "Completed":
            return "Completed"
        if not self.plannedStartDate and not self.dueDate:
            return "Needs Dates"
        today = date.today()
        if self.dueDate and today > self.dueDate:
            return "Overdue"
        return "On Schedule"

    @classmethod
    def getAll(cls, statusFilter=None, searchQuery=None, conn=None):
        query = """
            SELECT po.order_id, po.furniture_id, f.furniture_name, f.furniture_type,
                   po.sales_order_item_id, po.planned_quantity, po.order_date, po.planned_start_date,
                   po.due_date, po.status
            FROM prod_productionorder po
            JOIN prod_furniture f ON po.furniture_id = f.furniture_id
            WHERE 1=1
        """
        params = []

        if statusFilter and statusFilter in cls.VALID_STATUSES:
            query += " AND po.status = %s"
            params.append(statusFilter)

        if searchQuery:
            query += " AND (f.furniture_name ILIKE %s OR CAST(po.order_id AS TEXT) ILIKE %s)"
            searchPattern = f"%{searchQuery}%"
            params.extend([searchPattern, searchPattern])

        query += " ORDER BY po.order_id DESC"

        with openTransaction(conn) as connection:
            with connection.cursor() as cursor:
                cursor.execute(query, tuple(params))
                rows = cursor.fetchall()
                return [cls(row) for row in rows]

    @classmethod
    def getPlanningOrders(cls, statusFilter=None, searchQuery=None, conn=None):
        query = """
            SELECT po.order_id, po.furniture_id, f.furniture_name, f.furniture_type,
                   po.sales_order_item_id, po.planned_quantity, po.order_date, po.planned_start_date,
                   po.due_date, po.status
            FROM prod_productionorder po
            JOIN prod_furniture f ON po.furniture_id = f.furniture_id
            WHERE 1=1
        """
        params = []
        if statusFilter and statusFilter in cls.VALID_STATUSES:
            query += " AND po.status = %s"
            params.append(statusFilter)
        if searchQuery:
            query += " AND (f.furniture_name ILIKE %s OR CAST(po.order_id AS TEXT) ILIKE %s)"
            searchPattern = f"%{searchQuery}%"
            params.extend([searchPattern, searchPattern])

        query += " ORDER BY po.due_date ASC NULLS LAST, po.planned_start_date ASC NULLS LAST, po.order_id DESC"

        with openTransaction(conn) as connection:
            with connection.cursor() as cursor:
                cursor.execute(query, tuple(params))
                rows = cursor.fetchall()
                return [cls(row) for row in rows]

    @classmethod
    def getByID(cls, orderID, conn=None):
        query = """
            SELECT po.order_id, po.furniture_id, f.furniture_name, f.furniture_type,
                   po.sales_order_item_id, po.planned_quantity, po.order_date, po.planned_start_date,
                   po.due_date, po.status
            FROM prod_productionorder po
            JOIN prod_furniture f ON po.furniture_id = f.furniture_id
            WHERE po.order_id = %s
        """
        with openTransaction(conn) as connection:
            with connection.cursor() as cursor:
                cursor.execute(query, (orderID,))
                row = cursor.fetchone()
                return cls(row) if row else None

    @classmethod
    def getSummaryCounts(cls, conn=None):
        query = """
            SELECT
                COUNT(*) AS total_count,
                COUNT(*) FILTER (WHERE status = 'Draft') AS draft_count,
                COUNT(*) FILTER (WHERE status = 'Released') AS released_count,
                COUNT(*) FILTER (WHERE status = 'In Progress') AS in_progress_count,
                COUNT(*) FILTER (WHERE status = 'Completed') AS completed_count
            FROM prod_productionorder
        """
        with openTransaction(conn) as connection:
            with connection.cursor() as cursor:
                cursor.execute(query)
                row = cursor.fetchone()
                return {
                    "total": row["total_count"] if row else 0,
                    "draft": row["draft_count"] if row else 0,
                    "released": row["released_count"] if row else 0,
                    "inProgress": row["in_progress_count"] if row else 0,
                    "completed": row["completed_count"] if row else 0
                }

    @classmethod
    def createOrder(cls, furnitureID, plannedQuantity, plannedStartDate=None, dueDate=None, salesOrderItemID=None, conn=None):
        if not isinstance(plannedQuantity, int) or plannedQuantity < 1 or plannedQuantity > 100000:
            raise ValueError("Planned quantity must be a whole number between 1 and 100,000.")

        if plannedStartDate and dueDate:
            if dueDate < plannedStartDate:
                raise ValueError("Due date cannot be earlier than planned start date.")

        bom = BillOfMaterials.getByFurnitureID(furnitureID, autoCreate=False, conn=conn)
        if not bom or len(bom.getItems(conn=conn)) == 0:
            raise ValueError("Cannot create production order: Product has no Bill of Materials (recipe). Please configure its BOM first.")

        with openTransaction(conn) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO prod_productionorder (
                        furniture_id, sales_order_item_id, planned_quantity,
                        order_date, planned_start_date, due_date, status
                    )
                    VALUES (%s, %s, %s, CURRENT_DATE, %s, %s, 'Draft')
                    RETURNING order_id
                    """,
                    (furnitureID, salesOrderItemID, plannedQuantity, plannedStartDate, dueDate)
                )
                newID = cursor.fetchone()["order_id"]
                return newID

    @classmethod
    def updateStatus(cls, orderID, newStatus, conn=None):
        if newStatus not in cls.VALID_STATUSES:
            raise ValueError(f"Invalid status '{newStatus}'.")

        order = cls.getByID(orderID, conn=conn)
        if not order:
            raise ValueError("Order not found.")

        currentStatus = order.status
        allowedTransitions = {
            "Draft": ["Released"],
            "Released": ["In Progress"],
            "In Progress": ["Completed"],
            "Completed": []
        }

        if newStatus not in allowedTransitions.get(currentStatus, []):
            raise ValueError(f"Invalid status transition from '{currentStatus}' to '{newStatus}'.")

        with openTransaction(conn) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE prod_productionorder SET status = %s WHERE order_id = %s",
                    (newStatus, orderID)
                )
                return True

    @classmethod
    def updateSchedule(cls, orderID, plannedStartDate, dueDate, conn=None):
        if plannedStartDate and dueDate:
            if dueDate < plannedStartDate:
                raise ValueError("Target due date cannot be earlier than planned start date.")

        with openTransaction(conn) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE prod_productionorder
                    SET planned_start_date = %s, due_date = %s
                    WHERE order_id = %s
                    """,
                    (plannedStartDate, dueDate, orderID)
                )
                return True

    @classmethod
    def canDelete(cls, orderID, conn=None):
        with openTransaction(conn) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT status FROM prod_productionorder WHERE order_id = %s",
                    (orderID,)
                )
                row = cursor.fetchone()
                if not row or row["status"] != "Draft":
                    return False, "Only orders in Draft status can be deleted."

                cursor.execute(
                    "SELECT COUNT(*) AS c FROM prod_materialissuance WHERE order_id = %s",
                    (orderID,)
                )
                if cursor.fetchone()["c"] > 0:
                    return False, "Cannot delete order with issued materials."

                cursor.execute(
                    "SELECT COUNT(*) AS c FROM prod_productionmonitoring WHERE order_id = %s",
                    (orderID,)
                )
                if cursor.fetchone()["c"] > 0:
                    return False, "Cannot delete order with production monitoring progress."

                cursor.execute(
                    "SELECT COUNT(*) AS c FROM prod_productionoutput WHERE order_id = %s",
                    (orderID,)
                )
                if cursor.fetchone()["c"] > 0:
                    return False, "Cannot delete order with inspection records."

                return True, ""

    @classmethod
    def deleteOrder(cls, orderID, conn=None):
        allowed, reason = cls.canDelete(orderID, conn=conn)
        if not allowed:
            raise ValueError(reason)

        with openTransaction(conn) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM prod_productionorder WHERE order_id = %s AND status = 'Draft'",
                    (orderID,)
                )
                return True
