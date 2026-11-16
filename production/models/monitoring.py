from decimal import Decimal
from production.db import fetchAll, fetchOne, executeReturning
from production.timefmt import manilaToday, toManilaDate, formatManilaDateTime, formatManilaDateOnly
from production.cache import getCached, setCached, invalidateKeys

class ProductionMonitoring:
    STAGE_LABELS = {
        25: "Stage 1: Cutting & Sizing",
        50: "Stage 2: Joinery & Assembly",
        75: "Stage 3: Sanding & Finishing",
        90: "Stage 4: Ready for QC",
        100: "QC Passed & Completed"
    }
    REWORK_STAGE_PROGRESS = 75.0

    def __init__(self, data=None):
        if data:
            self.monitoringID = data.get("monitoring_id")
            self.orderID = data.get("order_id")
            rawProgress = data.get("progress")
            self.progress = float(rawProgress) if rawProgress is not None else 0.0
            self.startDate = data.get("start_date")
            self.completionDate = data.get("completion_date")
            self.updatedAt = data.get("updated_at")
            self.furnitureName = data.get("furniture_name", "")
            self.plannedQuantity = data.get("planned_quantity", 0)
            self.orderStatus = data.get("order_status", "")
            self.dueDate = data.get("due_date")
            self.reworkCount = int(data.get("rework_count", 0)) if data.get("rework_count") is not None else 0
            rawAssigned = data.get("assigned_to")
            self.assignedTo = int(rawAssigned) if rawAssigned is not None else None
            firstName = data.get("assigned_first_name") or ""
            lastName = data.get("assigned_last_name") or ""
            assignedEmail = (data.get("assigned_email") or "").strip()
            self.assignedStaffName = assignedEmail or f"{firstName} {lastName}".strip()
        else:
            self.monitoringID = None
            self.orderID = None
            self.progress = 0.0
            self.startDate = None
            self.completionDate = None
            self.updatedAt = None
            self.furnitureName = ""
            self.plannedQuantity = 0
            self.orderStatus = ""
            self.dueDate = None
            self.reworkCount = 0
            self.assignedTo = None
            self.assignedStaffName = ""

    @property
    def formattedStartDate(self):
        return formatManilaDateTime(self.startDate)

    @property
    def formattedDueDate(self):
        return formatManilaDateOnly(self.dueDate) if self.dueDate else None

    @property
    def formattedCompletionDate(self):
        return formatManilaDateTime(self.completionDate) if self.completionDate else None

    @property
    def dueStatus(self):
        if not self.dueDate or self.completionDate or self.orderStatus != "In Progress":
            return None
        d = toManilaDate(self.dueDate)
        if not d:
            return None
        today = manilaToday()
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
        if conn is None:
            cached = getCached("monitoring_all")
            if cached is not None:
                return cached
        sql = """
            SELECT pm.monitoring_id,
                   pm.order_id,
                   pm.progress,
                   pm.start_date,
                   pm.completion_date,
                   pm.updated_at,
                   COALESCE(pm.rework_count, 0) AS rework_count,
                   po.planned_quantity,
                   po.status AS order_status,
                   po.due_date,
                   po.assigned_to,
                   emp.name AS assigned_first_name,
                   emp.last_name AS assigned_last_name,
                   emp.email AS assigned_email,
                   f.furniture_name
            FROM prod_productionmonitoring pm
            JOIN prod_productionorder po ON pm.order_id = po.order_id
            JOIN prod_furniture f ON po.furniture_id = f.furniture_id
            LEFT JOIN public.employee emp ON emp.employee_id = po.assigned_to
            ORDER BY pm.monitoring_id DESC
        """
        rows = fetchAll(sql, conn=conn)
        result = [cls(r) for r in rows]
        if conn is None:
            setCached("monitoring_all", result)
        return result

    @classmethod
    def getByID(cls, monitoringID, conn=None):
        sql = """
            SELECT pm.monitoring_id,
                   pm.order_id,
                   pm.progress,
                   pm.start_date,
                   pm.completion_date,
                   pm.updated_at,
                   COALESCE(pm.rework_count, 0) AS rework_count,
                   po.planned_quantity,
                   po.status AS order_status,
                   po.due_date,
                   po.assigned_to,
                   emp.name AS assigned_first_name,
                   emp.last_name AS assigned_last_name,
                   emp.email AS assigned_email,
                   f.furniture_name
            FROM prod_productionmonitoring pm
            JOIN prod_productionorder po ON pm.order_id = po.order_id
            JOIN prod_furniture f ON po.furniture_id = f.furniture_id
            LEFT JOIN public.employee emp ON emp.employee_id = po.assigned_to
            WHERE pm.monitoring_id = %s
        """
        row = fetchOne(sql, (monitoringID,), conn=conn)
        return cls(row) if row else None

    @classmethod
    def getByOrderID(cls, orderID, conn=None):
        sql = """
            SELECT pm.monitoring_id,
                   pm.order_id,
                   pm.progress,
                   pm.start_date,
                   pm.completion_date,
                   pm.updated_at,
                   COALESCE(pm.rework_count, 0) AS rework_count,
                   po.planned_quantity,
                   po.status AS order_status,
                   po.due_date,
                   po.assigned_to,
                   emp.name AS assigned_first_name,
                   emp.last_name AS assigned_last_name,
                   emp.email AS assigned_email,
                   f.furniture_name
            FROM prod_productionmonitoring pm
            JOIN prod_productionorder po ON pm.order_id = po.order_id
            JOIN prod_furniture f ON po.furniture_id = f.furniture_id
            LEFT JOIN public.employee emp ON emp.employee_id = po.assigned_to
            WHERE pm.order_id = %s
        """
        row = fetchOne(sql, (orderID,), conn=conn)
        return cls(row) if row else None

    @classmethod
    def updateProgress(cls, monitoringID, progressVal, conn=None):
        val = max(0.0, min(100.0, float(progressVal)))
        sql = """
            UPDATE prod_productionmonitoring
            SET progress = %s,
                completion_date = CASE WHEN %s >= 100.0 THEN NOW() ELSE NULL END,
                updated_at = NOW()
            WHERE monitoring_id = %s
            RETURNING monitoring_id, order_id, progress, start_date, completion_date, rework_count, updated_at
        """
        row = executeReturning(sql, (val, val, monitoringID), conn=conn)
        invalidateKeys("monitoring_all")
        return cls(row) if row else None

    @classmethod
    def updateProgressAndRework(cls, monitoringID, progressVal, reworkCount, conn=None):
        val = max(0.0, min(100.0, float(progressVal)))
        sql = """
            UPDATE prod_productionmonitoring
            SET progress = %s,
                rework_count = %s,
                completion_date = CASE WHEN %s >= 100.0 THEN NOW() ELSE NULL END,
                updated_at = NOW()
            WHERE monitoring_id = %s
            RETURNING monitoring_id, order_id, progress, start_date, completion_date, rework_count, updated_at
        """
        row = executeReturning(sql, (val, reworkCount, val, monitoringID), conn=conn)
        invalidateKeys("monitoring_all")
        return cls(row) if row else None
