import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import date
from production.db import openTransaction
from production.auth import PRODUCTION_DEPARTMENT_ID, STAFF_POSITION_ID


def isValidActiveProdStaff(employeeID, conn=None):
    if not employeeID:
        return False
    try:
        with openTransaction(conn) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT 1
                    FROM public.employee
                    WHERE employee_id = %s
                      AND is_active = TRUE
                      AND department_id = %s
                      AND position_id = %s
                    LIMIT 1
                    """,
                    (int(employeeID), PRODUCTION_DEPARTMENT_ID, STAFF_POSITION_ID)
                )
                return cursor.fetchone() is not None
    except Exception:
        return False


def getProductionStaffRoster(conn=None):
    query = """
        SELECT e.employee_id,
               e.name,
               e.last_name,
               e.email,
               p.position_name,
               COALESCE(act.active_batches, 0) AS active_batches
        FROM public.employee e
        LEFT JOIN public.position p ON p.position_id = e.position_id
        LEFT JOIN LATERAL (
            SELECT COUNT(*) AS active_batches
            FROM prod_productionorder po
            WHERE po.assigned_to = e.employee_id
              AND po.status IN ('Draft', 'Released', 'In Progress')
        ) act ON true
        WHERE e.is_active = TRUE
          AND e.department_id = %s
          AND e.position_id = %s
        ORDER BY e.name ASC, e.last_name ASC
    """
    roster = []
    try:
        with openTransaction(conn) as connection:
            with connection.cursor() as cursor:
                cursor.execute(query, (PRODUCTION_DEPARTMENT_ID, STAFF_POSITION_ID))
                rows = cursor.fetchall()
                for r in rows:
                    fullName = f"{r.get('name') or ''} {r.get('last_name') or ''}".strip() or (r.get("email") or f"Employee #{r['employee_id']}")
                    roster.append({
                        "employeeID": int(r["employee_id"]),
                        "fullName": fullName,
                        "positionName": r.get("position_name") or "Production Staff",
                        "activeBatches": int(r.get("active_batches") or 0)
                    })
    except Exception:
        return []
    return roster


def _resolveSupabaseBaseUrl():
    explicitUrl = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
    if explicitUrl:
        return explicitUrl
    dbUser = os.getenv("DB_USER", "").strip()
    if dbUser.startswith("postgres.") and len(dbUser.split(".", 1)[1]) >= 8:
        ref = dbUser.split(".", 1)[1]
        return f"https://{ref}.supabase.co"
    dbHost = os.getenv("DB_HOST", "").strip()
    if dbHost.startswith("db.") and dbHost.endswith(".supabase.co"):
        parts = dbHost.split(".")
        if len(parts) >= 4:
            return f"https://{parts[1]}.supabase.co"
    return ""


def uploadToSupabaseStorage(rawBytes, mimeType="image/jpeg", entityType="stage_proof", orderID=None, stageProgress=None):
    baseUrl = _resolveSupabaseBaseUrl()
    serviceKey = (
        os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        or os.getenv("SUPABASE_KEY")
        or ""
    ).strip()
    bucketName = os.getenv("SUPABASE_STORAGE_BUCKET", "prod-attachments").strip() or "prod-attachments"

    if not baseUrl or not serviceKey:
        raise RuntimeError(
            "Supabase Storage is not configured. Add SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY to your .env file."
        )

    extMap = {
        "image/jpeg": "jpg",
        "image/png": "png",
        "image/webp": "webp"
    }
    ext = extMap.get((mimeType or "").lower(), "jpg")
    stamp = int(time.time() * 1000)
    token = uuid.uuid4().hex[:8]
    folder = (entityType or "attachment").replace("_", "-")
    if orderID is not None and stageProgress is not None:
        objectPath = f"{folder}/po-{int(orderID)}/s{int(stageProgress)}-{stamp}-{token}.{ext}"
    elif orderID is not None:
        objectPath = f"{folder}/po-{int(orderID)}/{stamp}-{token}.{ext}"
    else:
        objectPath = f"{folder}/{stamp}-{token}.{ext}"

    encodedBucket = urllib.parse.quote(bucketName, safe="")
    uploadUrl = f"{baseUrl}/storage/v1/object/{encodedBucket}/{objectPath}"
    headers = {
        "apikey": serviceKey,
        "Content-Type": mimeType or "image/jpeg",
        "x-upsert": "true",
        "User-Agent": "VelmoraERP-Server/1.0"
    }
    if not serviceKey.startswith("sb_"):
        headers["Authorization"] = f"Bearer {serviceKey}"

    req = urllib.request.Request(uploadUrl, data=rawBytes, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            resp.read()
    except urllib.error.HTTPError as httpErr:
        detail = ""
        try:
            bodyText = httpErr.read().decode("utf-8", errors="ignore")
            parsed = json.loads(bodyText)
            detail = parsed.get("message") or parsed.get("error") or bodyText[:140]
        except Exception:
            detail = str(httpErr)
        raise RuntimeError(f"Supabase Storage upload failed ({bucketName}): {detail}")
    except Exception as netErr:
        raise RuntimeError(f"Supabase Storage connection error: {str(netErr)}")

    return f"{baseUrl}/storage/v1/object/public/{encodedBucket}/{objectPath}"


class ProductionAttachment:
    STAGE_NAMES = {
        25: "Stage 1: Cutting & Sizing",
        50: "Stage 2: Joinery & Assembly",
        75: "Stage 3: Sanding & Finishing",
        90: "Stage 4: Ready for QA"
    }

    def __init__(self, data=None):
        if data:
            self.attachmentID = data.get("attachment_id")
            self.proofID = self.attachmentID
            self.entityType = data.get("entity_type") or "stage_proof"
            self.orderID = data.get("order_id")
            self.stageProgress = int(data.get("stage_progress") or 25)
            self.note = data.get("note") or ""
            self.fileName = data.get("file_name") or ""
            self.fileUrl = data.get("file_url") or ""
            self.hasImage = bool(self.fileUrl)
            self.uploadedBy = data.get("uploaded_by")
            uploaderName = (data.get("uploader_name") or "").strip()
            self.submittedBy = uploaderName or data.get("uploader_email") or "Workshop Staff"
            self.createdAt = data.get("created_at")
        else:
            self.attachmentID = None
            self.proofID = None
            self.entityType = "stage_proof"
            self.orderID = None
            self.stageProgress = 25
            self.note = ""
            self.fileName = ""
            self.fileUrl = ""
            self.hasImage = False
            self.uploadedBy = None
            self.submittedBy = "Workshop Staff"
            self.createdAt = None

    @property
    def stageLabel(self):
        return self.STAGE_NAMES.get(self.stageProgress, f"{self.stageProgress}% Milestone")

    @property
    def formattedCreatedAt(self):
        if not self.createdAt:
            return "-"
        try:
            return self.createdAt.strftime("%b. %d, %Y · %I:%M %p")
        except AttributeError:
            return str(self.createdAt)

    @classmethod
    def createAttachment(cls, orderID=None, stageProgress=None, note=None, fileName=None, fileUrl=None, uploadedBy=None, entityType="stage_proof", conn=None):
        cleanNote = (note or "").strip()[:300] or None
        cleanName = (fileName or "").strip()[:180] or None
        cleanUrl = (fileUrl or "").strip() or None
        cleanType = (entityType or "stage_proof").strip()[:30]
        cleanStage = int(stageProgress) if stageProgress is not None else None
        cleanUploader = int(uploadedBy) if uploadedBy is not None else None

        with openTransaction(conn) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO public.prod_attachments (
                        entity_type, order_id, stage_progress, note, file_name, file_url, uploaded_by
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING attachment_id
                    """,
                    (cleanType, orderID, cleanStage, cleanNote, cleanName, cleanUrl, cleanUploader)
                )
                return cursor.fetchone()["attachment_id"]

    @classmethod
    def getByOrderID(cls, orderID, entityType="stage_proof", conn=None):
        try:
            with openTransaction(conn) as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT a.attachment_id, a.entity_type, a.order_id, a.stage_progress,
                               a.note, a.file_name, a.file_url, a.uploaded_by, a.created_at,
                               TRIM(COALESCE(e.name, '') || ' ' || COALESCE(e.last_name, '')) AS uploader_name,
                               e.email AS uploader_email
                        FROM public.prod_attachments a
                        LEFT JOIN public.employee e ON e.employee_id = a.uploaded_by
                        WHERE a.order_id = %s
                          AND a.entity_type = %s
                        ORDER BY a.created_at DESC, a.attachment_id DESC
                        """,
                        (int(orderID), entityType)
                    )
                    return [cls(r) for r in cursor.fetchall()]
        except Exception:
            return []

    @classmethod
    def getLatestByOrderIDs(cls, orderIDs, requireImage=False, entityType="stage_proof", conn=None):
        cleanIDs = [int(oid) for oid in (orderIDs or []) if oid is not None]
        if not cleanIDs:
            return {}
        imgFilter = "AND a.file_url IS NOT NULL AND a.file_url <> ''" if requireImage else ""
        query = f"""
            SELECT DISTINCT ON (a.order_id)
                   a.attachment_id, a.entity_type, a.order_id, a.stage_progress,
                   a.note, a.file_name, a.file_url, a.uploaded_by, a.created_at,
                   TRIM(COALESCE(e.name, '') || ' ' || COALESCE(e.last_name, '')) AS uploader_name,
                   e.email AS uploader_email
            FROM public.prod_attachments a
            LEFT JOIN public.employee e ON e.employee_id = a.uploaded_by
            WHERE a.order_id = ANY(%s)
              AND a.entity_type = %s
              {imgFilter}
            ORDER BY a.order_id, a.created_at DESC, a.attachment_id DESC
        """
        try:
            with openTransaction(conn) as connection:
                with connection.cursor() as cursor:
                    cursor.execute(query, (cleanIDs, entityType))
                    rows = cursor.fetchall()
                    return {int(r["order_id"]): cls(r) for r in rows}
        except Exception:
            return {}


def _fmtShortDate(val):
    if not val:
        return "TBD"
    if hasattr(val, "strftime"):
        return val.strftime("%b. %d")
    return str(val)


def getLiveNotificationsForUser(employeeID=None, isManager=False, isProdStaff=False, conn=None):
    items = []
    todayVal = date.today()
    try:
        with openTransaction(conn) as connection:
            with connection.cursor() as cursor:
                if isManager:
                    cursor.execute(
                        """
                        SELECT po.order_id,
                               po.planned_quantity,
                               po.status,
                               po.planned_start_date,
                               po.due_date,
                               po.assigned_to,
                               f.furniture_name,
                               COALESCE(pm.progress, 0.0) AS progress,
                               COALESCE(pm.rework_count, 0) AS rework_count,
                               TRIM(COALESCE(e.name, '') || ' ' || COALESCE(e.last_name, '')) AS staff_name
                        FROM prod_productionorder po
                        JOIN prod_furniture f ON f.furniture_id = po.furniture_id
                        LEFT JOIN prod_productionmonitoring pm ON pm.order_id = po.order_id
                        LEFT JOIN public.employee e ON e.employee_id = po.assigned_to
                        WHERE po.status != 'Completed'
                        ORDER BY po.order_id DESC
                        """
                    )
                    rows = cursor.fetchall()
                    for r in rows:
                        oid = int(r["order_id"])
                        qty = int(r["planned_quantity"] or 0)
                        fname = r.get("furniture_name") or "Product"
                        prog = float(r.get("progress") or 0.0)
                        rwk = int(r.get("rework_count") or 0)
                        staff = (r.get("staff_name") or "").strip() or "Workshop Staff"
                        status = r.get("status") or "Draft"
                        dueDate = r.get("due_date")

                        if status == "In Progress" and prog >= 90.0:
                            items.append({
                                "notifKey": f"qa-ready-{oid}-r{rwk}",
                                "title": f"Order #PO-{oid} Ready for QA",
                                "message": f"{fname} ({qty} units) submitted by {staff} is at 90% awaiting inspection.",
                                "targetUrl": "/production/finished-goods",
                                "timeLabel": "Stage 4 Complete · Inspect QA →"
                            })

                        if dueDate and dueDate < todayVal:
                            items.append({
                                "notifKey": f"overdue-{oid}-{dueDate.isoformat()}",
                                "title": f"Order #PO-{oid} Overdue",
                                "message": f"{fname} ({qty} units) passed target due date ({_fmtShortDate(dueDate)}).",
                                "targetUrl": "/production/planning?view=timeline",
                                "timeLabel": "Schedule Alert · View Timeline →"
                            })

                        if status == "Draft" and (not r.get("planned_start_date") or not dueDate or not r.get("assigned_to")):
                            items.append({
                                "notifKey": f"plan-needed-{oid}",
                                "title": f"Order #PO-{oid} Needs Planning",
                                "message": f"Assign timeline dates and workshop staff for {fname} ({qty} units).",
                                "targetUrl": "/production/planning",
                                "timeLabel": "Draft · Plan & Assign →"
                            })

                elif isProdStaff and employeeID:
                    cursor.execute(
                        """
                        SELECT po.order_id,
                               po.planned_quantity,
                               po.status,
                               po.planned_start_date,
                               po.due_date,
                               f.furniture_name,
                               COALESCE(pm.progress, 0.0) AS progress,
                               COALESCE(pm.rework_count, 0) AS rework_count,
                               rwk_out.reason AS rework_reason
                        FROM prod_productionorder po
                        JOIN prod_furniture f ON f.furniture_id = po.furniture_id
                        LEFT JOIN prod_productionmonitoring pm ON pm.order_id = po.order_id
                        LEFT JOIN LATERAL (
                            SELECT reason
                            FROM prod_productionoutput outp
                            WHERE outp.order_id = po.order_id
                              AND outp.quality_status = 'Rework'
                            ORDER BY outp.output_id DESC
                            LIMIT 1
                        ) rwk_out ON true
                        WHERE po.assigned_to = %s
                          AND po.status != 'Completed'
                        ORDER BY (po.status = 'In Progress') DESC, po.due_date ASC NULLS LAST, po.order_id DESC
                        """,
                        (int(employeeID),)
                    )
                    rows = cursor.fetchall()
                    for r in rows:
                        oid = int(r["order_id"])
                        qty = int(r["planned_quantity"] or 0)
                        fname = r.get("furniture_name") or "Product"
                        status = r.get("status") or "Draft"
                        prog = float(r.get("progress") or 0.0)
                        rwk = int(r.get("rework_count") or 0)
                        reason = (r.get("rework_reason") or "").strip()
                        startFmt = _fmtShortDate(r.get("planned_start_date"))
                        dueFmt = _fmtShortDate(r.get("due_date"))

                        if status == "In Progress" and rwk > 0 and prog < 90.0:
                            reasonSuffix = f": {reason}" if reason else "."
                            items.append({
                                "notifKey": f"staff-rework-{oid}-r{rwk}",
                                "title": f"QA Rework #{rwk} — Order #PO-{oid}",
                                "message": f"{fname} ({qty} units) returned to Stage 3 (75%){reasonSuffix}",
                                "targetUrl": "/production/monitoring",
                                "timeLabel": "Rework Needed · Open Monitoring →"
                            })
                        elif status == "In Progress" and prog < 90.0:
                            items.append({
                                "notifKey": f"staff-active-{oid}",
                                "title": f"Workshop Assembly — Order #PO-{oid}",
                                "message": f"Materials dispatched for {fname} ({qty} units) · Currently at {int(round(prog))}%.",
                                "targetUrl": "/production/monitoring",
                                "timeLabel": f"Due {dueFmt} · Log Stage →"
                            })
                        elif status in ("Draft", "Released"):
                            items.append({
                                "notifKey": f"staff-assigned-{oid}-{status.lower()}",
                                "title": f"Order #PO-{oid} Assigned to You",
                                "message": f"{fname} ({qty} units) scheduled {startFmt} to {dueFmt} ({status}).",
                                "targetUrl": f"/production/orders/{oid}",
                                "timeLabel": "Scheduled · View Order →"
                            })
    except Exception:
        return []
    return items[:15]
