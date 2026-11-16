from production.db import fetchAll, executeReturning
from production.timefmt import formatManilaDateTime, toManilaDatetime, manilaToday
from production.cache import getCached, setCached, invalidateKeys

class ActivityLog:
    def __init__(self, data=None):
        if data:
            self.id = data.get("id")
            self.orderID = data.get("order_id")
            self.category = data.get("category") or "created"
            self.title = data.get("title") or ""
            self.meta = data.get("meta") or ""
            self.employeeID = data.get("employee_id")
            self.employeeName = (data.get("employee_name") or "").strip()
            self.positionName = (data.get("position_name") or "").strip()
            self.createdAt = data.get("created_at")
        else:
            self.id = None
            self.orderID = None
            self.category = "created"
            self.title = ""
            self.meta = ""
            self.employeeID = None
            self.employeeName = ""
            self.positionName = ""
            self.createdAt = None

    @property
    def dateStr(self):
        if not self.createdAt:
            return ""
        dtVal = toManilaDatetime(self.createdAt)
        today = manilaToday()
        includeYear = bool(dtVal and dtVal.year != today.year)
        return formatManilaDateTime(self.createdAt, includeYear=includeYear)

    @classmethod
    def record(cls, category, title, meta=None, orderID=None, employeeID=None, createdAt=None, conn=None):
        cleanCat = (category or "created").strip()[:30]
        cleanTitle = (title or "").strip()[:200]
        cleanMeta = meta.strip() if meta else None
        cleanOrderID = int(orderID) if orderID is not None else None
        cleanEmpID = int(employeeID) if employeeID is not None else None

        if createdAt is not None:
            sql = """
                INSERT INTO prod_activitylog (order_id, category, title, meta, employee_id, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id, order_id, category, title, meta, employee_id, created_at
            """
            row = executeReturning(sql, (cleanOrderID, cleanCat, cleanTitle, cleanMeta, cleanEmpID, createdAt), conn=conn)
        else:
            sql = """
                INSERT INTO prod_activitylog (order_id, category, title, meta, employee_id)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, order_id, category, title, meta, employee_id, created_at
            """
            row = executeReturning(sql, (cleanOrderID, cleanCat, cleanTitle, cleanMeta, cleanEmpID), conn=conn)
        invalidateKeys("orders_all")
        return cls(row) if row else None

    @classmethod
    def getRecent(cls, isManager=False, currentEmployeeID=None, limit=20, conn=None):
        cacheKey = f"activity_recent:{'mgr' if isManager else 'staff'}:{currentEmployeeID or 0}:{int(limit)}"
        if conn is None:
            cached = getCached(cacheKey)
            if cached is not None:
                return cached
        baseSql = """
            SELECT al.id,
                   al.order_id,
                   al.category,
                   al.title,
                   al.meta,
                   al.employee_id,
                   al.created_at,
                   COALESCE(NULLIF(TRIM(emp.email), ''), TRIM(COALESCE(emp.name, '') || ' ' || COALESCE(emp.last_name, ''))) AS employee_name,
                   pos.position_name
            FROM prod_activitylog al
            LEFT JOIN public.employee emp ON emp.employee_id = al.employee_id
            LEFT JOIN public.position pos ON pos.position_id = emp.position_id
        """
        params = []
        if not isManager:
            baseSql += " WHERE al.employee_id = %s"
            params.append(int(currentEmployeeID) if currentEmployeeID else -1)
        baseSql += " ORDER BY al.created_at DESC, al.id DESC LIMIT %s"
        params.append(int(limit))

        rows = fetchAll(baseSql, tuple(params), conn=conn)
        result = [cls(r) for r in rows]
        if conn is None:
            setCached(cacheKey, result)
        return result
