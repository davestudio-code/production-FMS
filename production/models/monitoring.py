from datetime import date
from decimal import Decimal
from production.db import openTransaction

class ProductionMonitoring:
    def __init__(self, data=None):
        if data:
            self.monitoringID = data.get("monitoring_id")
            self.orderID = data.get("order_id")
            rawProgress = data.get("progress")
            self.progress = float(rawProgress) if rawProgress is not None else 0.0
            self.startDate = data.get("start_date")
            self.completionDate = data.get("completion_date")
            self.furnitureName = data.get("furniture_name", "")
            self.plannedQuantity = data.get("planned_quantity", 0)
            self.orderStatus = data.get("order_status", "")
            self.dueDate = data.get("due_date")
        else:
            self.monitoringID = None
            self.orderID = None
            self.progress = 0.0
            self.startDate = None
            self.completionDate = None
            self.furnitureName = ""
            self.plannedQuantity = 0
            self.orderStatus = ""
            self.dueDate = None

    @property
    def formattedStartDate(self):
        if not self.startDate:
            return "-"
        try:
            return self.startDate.strftime("%b %d")
        except AttributeError:
            return str(self.startDate)

    @property
    def formattedDueDate(self):
        if not self.dueDate:
            return None
        try:
            return self.dueDate.strftime("%b %d")
        except AttributeError:
            return str(self.dueDate)

    @property
    def formattedCompletionDate(self):
        if not self.completionDate:
            return None
        try:
            return self.completionDate.strftime("%b %d")
        except AttributeError:
            return str(self.completionDate)

    @property
    def dueStatus(self):
        if not self.dueDate or self.completionDate or self.orderStatus != "In Progress":
            return None
        d = self.dueDate if hasattr(self.dueDate, "year") else date.fromisoformat(str(self.dueDate))
        today = date.today()
        daysLeft = (d - today).days
        if daysLeft < 0:
            return {"label": f"{abs(daysLeft)}d Overdue", "isOverdue": True}
        elif daysLeft == 0:
            return {"label": "Due Today", "isOverdue": False}
        elif daysLeft <= 3:
            return {"label": f"Due in {daysLeft}d", "isOverdue": False}
        return None

    @classmethod
    def getAll(cls, conn=None):
        with openTransaction(conn) as connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT pm.monitoring_id,
                           pm.order_id,
                           pm.progress,
                           pm.start_date,
                           pm.completion_date,
                           po.planned_quantity,
                           po.status AS order_status,
                           po.due_date,
                           f.furniture_name
                    FROM prod_productionmonitoring pm
                    JOIN prod_productionorder po ON pm.order_id = po.order_id
                    JOIN prod_furniture f ON po.furniture_id = f.furniture_id
                    ORDER BY pm.monitoring_id DESC
                """)
                rows = cursor.fetchall()
                return [cls(r) for r in rows]

    @classmethod
    def getByID(cls, monitoringID, conn=None):
        with openTransaction(conn) as connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT pm.monitoring_id,
                           pm.order_id,
                           pm.progress,
                           pm.start_date,
                           pm.completion_date,
                           po.planned_quantity,
                           po.status AS order_status,
                           po.due_date,
                           f.furniture_name
                    FROM prod_productionmonitoring pm
                    JOIN prod_productionorder po ON pm.order_id = po.order_id
                    JOIN prod_furniture f ON po.furniture_id = f.furniture_id
                    WHERE pm.monitoring_id = %s
                """, (monitoringID,))
                row = cursor.fetchone()
                return cls(row) if row else None

    @classmethod
    def getByOrderID(cls, orderID, conn=None):
        with openTransaction(conn) as connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT pm.monitoring_id,
                           pm.order_id,
                           pm.progress,
                           pm.start_date,
                           pm.completion_date,
                           po.planned_quantity,
                           po.status AS order_status,
                           po.due_date,
                           f.furniture_name
                    FROM prod_productionmonitoring pm
                    JOIN prod_productionorder po ON pm.order_id = po.order_id
                    JOIN prod_furniture f ON po.furniture_id = f.furniture_id
                    WHERE pm.order_id = %s
                """, (orderID,))
                row = cursor.fetchone()
                return cls(row) if row else None

    @classmethod
    def updateProgress(cls, monitoringID, progressVal, conn=None):
        val = max(0.0, min(100.0, float(progressVal)))
        with openTransaction(conn) as connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE prod_productionmonitoring
                    SET progress = %s,
                        completion_date = CASE WHEN %s >= 100.0 THEN CURRENT_DATE ELSE NULL END
                    WHERE monitoring_id = %s
                    RETURNING monitoring_id, order_id, progress, start_date, completion_date
                """, (val, val, monitoringID))
                row = cursor.fetchone()
                return cls(row) if row else None
