import os
import math
import re
import logging
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, send_from_directory
from decimal import Decimal, InvalidOperation
from datetime import datetime, date, timedelta
from psycopg2.errors import UniqueViolation
from .db import openTransaction, fetchAll, fetchOne, execute, executeReturning
from .auth import (
    authenticate_credentials,
    login_required,
    manager_required,
    is_manager_session,
    is_staff_session,
    sync_and_verify_session,
    clear_employee_verify_cache,
    update_employee_profile,
    change_employee_password,
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
from .security import check_ip_security, record_failed_login, record_successful_login, get_client_ip

productionBlueprint = Blueprint(
    "production",
    __name__,
    template_folder="templates",
    static_folder="static"
)

DASHBOARD_WEEKS = 4
logger = logging.getLogger(__name__)

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

def _clearAuthSessionKeys():
    for key in (
        "user_id",
        "auth_user_id",
        "employee_id",
        "department_id",
        "position_id",
        "email",
        "first_name",
        "last_name",
        "phone",
        "employee_name",
        "position",
        "access_level",
        "role",
    ):
        session.pop(key, None)

@productionBlueprint.before_request
def requireLogin():
    if request.endpoint in ("production.login", "production.logout", "production.static", "production.loginpageStatic", "production.featureStatic"):
        return
    if not session.get("user_id"):
        return redirect(url_for("production.login", next=request.path))
    if not sync_and_verify_session():
        _clearAuthSessionKeys()
        flash("[403] Forbidden Access.", "warning")
        return redirect(url_for("production.login"))

@productionBlueprint.after_request
def preventHtmlCacheAfterSignout(response):
    if request.endpoint not in ("production.static", "production.loginpageStatic", "production.featureStatic"):
        content_type = response.headers.get("Content-Type", "")
        if "text/html" in content_type:
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"
    return response

@productionBlueprint.route("/login", methods=["GET", "POST"])
def login():
    try:
        if session.get("user_id") and sync_and_verify_session():
            return redirect(url_for("production.index"))
    except Exception:
        pass
    if session.get("user_id"):
        _clearAuthSessionKeys()

    client_ip = get_client_ip()
    is_allowed, ban_status = check_ip_security(client_ip)

    if request.method == "POST":
        if not is_allowed:
            err_msg = ban_status.get("message", "Access restricted due to security policy.")
            if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.is_json:
                return jsonify({"success": False, "error": err_msg, "security": ban_status}), 403
            flash(err_msg, "danger")
            return render_template("production/loginpage/login.html", ban_status=ban_status), 403

        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not email or not re.match(email_pattern, email):
            err_msg = "Please enter a valid email address."
            if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.is_json:
                return jsonify({"success": False, "error": err_msg}), 400
            flash(err_msg, "danger")
            return render_template("production/loginpage/login.html", ban_status=ban_status), 400

        try:
            user_record, error_message = authenticate_credentials(email, password)
        except Exception as err:
            user_record, error_message = None, f"Authentication error: {str(err)}"

        if error_message:
            security_info = record_failed_login(client_ip)
            full_error = security_info.get("message", error_message)
            status_code = 403 if security_info.get("action") in ("blocked", "banned") else 401
            if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.is_json:
                return jsonify({"success": False, "error": full_error, "security": security_info}), status_code
            flash(full_error, "danger")
            return render_template("production/loginpage/login.html", ban_status=security_info), status_code

        record_successful_login(client_ip)
        try:
            emp_id = int(user_record["employee_id"])
            dept_id = int(user_record["department_id"])
            pos_id = int(user_record["position_id"])
            session["user_id"] = user_record.get("user_id") or emp_id or str(user_record.get("auth_user_id"))
            if user_record.get("auth_user_id"):
                session["auth_user_id"] = str(user_record.get("auth_user_id"))
            session["employee_id"] = emp_id
            session["department_id"] = dept_id
            session["position_id"] = pos_id
            session["email"] = user_record.get("email")
            name = (user_record.get("name") or "").strip()
            last_name = (user_record.get("last_name") or "").strip()
            session["first_name"] = name
            session["last_name"] = last_name
            session["phone"] = (user_record.get("phone") or "").strip()
            full_name = f"{name} {last_name}".strip()
            session["employee_name"] = full_name if full_name else user_record.get("email")
            session["position"] = user_record.get("position_name") or ("Manager" if pos_id == MANAGER_POSITION_ID else "Production Staff")
            session["access_level"] = user_record.get("access_level") or ("manager" if pos_id == MANAGER_POSITION_ID else "staff")
            clear_employee_verify_cache(emp_id)
            flash(f"Welcome back, {session['employee_name']}!", "success")
            next_page = request.args.get("next")
            next_url = next_page if (next_page and next_page.startswith("/production") and not next_page.startswith("/production/logout") and not next_page.startswith("/production/login")) else url_for("production.index")
            if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.is_json:
                return jsonify({"success": True, "redirect": next_url, "user": session["employee_name"]}), 200
            return redirect(next_url)
        except Exception as err:
            err_msg = f"Session initialization error: {str(err)}"
            if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.is_json:
                return jsonify({"success": False, "error": err_msg}), 500
            flash(err_msg, "danger")
            return render_template("production/loginpage/login.html")

    return render_template("production/loginpage/login.html", ban_status=ban_status)

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
    try:
        clear_employee_verify_cache(session.get("employee_id"))
        session.clear()
        flash("You have been signed out successfully.", "info")
    except Exception:
        session.clear()
    return redirect(url_for("production.login"))

@productionBlueprint.route("/account/update-profile", methods=["POST"])
@login_required
def updateAccountProfile():
    try:
        payload = request.get_json(silent=True) if request.is_json else request.form
        first_name = (payload.get("first_name") or "").strip()
        last_name = (payload.get("last_name") or "").strip()
        phone = (payload.get("phone") or "").strip()
        emp_id = session.get("employee_id")

        updated, err = update_employee_profile(emp_id, first_name, last_name, phone)
        if err:
            if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.is_json:
                return jsonify({"success": False, "error": err}), 400
            flash(err, "error")
            return redirect(request.referrer or url_for("production.index"))

        session["first_name"] = (updated.get("name") or "").strip()
        session["last_name"] = (updated.get("last_name") or "").strip()
        session["phone"] = (updated.get("phone") or "").strip()
        full_name = f"{session['first_name']} {session['last_name']}".strip()
        if full_name:
            session["employee_name"] = full_name
        initial = (session["employee_name"] or "U")[:1].upper()

        if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.is_json:
            return jsonify({
                "success": True,
                "message": "Account profile updated successfully.",
                "first_name": session["first_name"],
                "last_name": session["last_name"],
                "phone": session["phone"],
                "employee_name": session["employee_name"],
                "initial": initial,
            }), 200
        flash("Account profile updated successfully.", "success")
        return redirect(request.referrer or url_for("production.index"))
    except Exception as err:
        err_msg = f"Profile update error: {str(err)}"
        if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.is_json:
            return jsonify({"success": False, "error": err_msg}), 500
        flash(err_msg, "error")
        return redirect(request.referrer or url_for("production.index"))

@productionBlueprint.route("/account/change-password", methods=["POST"])
@login_required
def changeAccountPassword():
    try:
        payload = request.get_json(silent=True) if request.is_json else request.form
        current_password = payload.get("current_password") or ""
        new_password = payload.get("new_password") or ""
        confirm_password = payload.get("confirm_password") or ""

        if new_password != confirm_password:
            err = "New password and confirmation password do not match."
            if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.is_json:
                return jsonify({"success": False, "error": err}), 400
            flash(err, "error")
            return redirect(request.referrer or url_for("production.index"))

        ok, err = change_employee_password(session.get("employee_id"), current_password, new_password)
        if not ok:
            if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.is_json:
                return jsonify({"success": False, "error": err}), 400
            flash(err, "error")
            return redirect(request.referrer or url_for("production.index"))

        if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.is_json:
            return jsonify({"success": True, "message": "Password changed successfully."}), 200
        flash("Password changed successfully.", "success")
        return redirect(request.referrer or url_for("production.index"))
    except Exception as err:
        err_msg = f"Password change error: {str(err)}"
        if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.is_json:
            return jsonify({"success": False, "error": err_msg}), 500
        flash(err_msg, "error")
        return redirect(request.referrer or url_for("production.index"))

@productionBlueprint.route("/refresh", methods=["POST", "GET"])
def refreshCache():
    try:
        clearAllCache()
        clear_employee_verify_cache()
    except Exception:
        pass
    if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.is_json:
        return jsonify({"status": "success", "message": "Live database synchronized."})
    flash("Live database synchronized.", "success")
    return redirect(request.referrer or url_for("production.index"))

def getDatabaseStatus():
    try:
        fetchOne("SELECT 1")
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
        {"name": "Ready for QC", "threshold": 90},
        {"name": "QC Passed & Completed", "threshold": 100}
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

    activeWipUnits = sum(int(o.plannedQuantity or 0) for o in allOrders if o.status == "In Progress")
    readyForIssuanceUnits = sum(int(o.plannedQuantity or 0) for o in allOrders if o.status == "Released")
    awaitingQCOrders = sum(1 for m in allMonitoring if m.orderStatus == "In Progress" and m.progress and m.progress >= 90)
    needsPlanCount = sum(1 for o in allOrders if o.status == "Draft" and (not o.dueDate or not o.assignedTo))

    today = date.today()
    datedOrdersTotal = sum(1 for o in allOrders if o.dueDate)
    onTimeOrders = sum(1 for o in allOrders if o.dueDate and (o.status == "Completed" or o.dueDate >= today))
    otdRate = int(round((onTimeOrders / datedOrdersTotal) * 100)) if datedOrdersTotal > 0 else 100

    metricsData = {
        "totalOrders": len(allOrders),
        "draftOrders": draftOrders,
        "releasedOrders": releasedOrders,
        "inProgressOrders": inProgressOrders,
        "completedOrders": completedOrders,
        "activeWipUnits": activeWipUnits,
        "readyForIssuanceUnits": readyForIssuanceUnits,
        "awaitingQCCount": awaitingQCOrders,
        "needsPlanCount": needsPlanCount,
        "otdRate": otdRate,
        "lowStockCount": len(lowStockMaterials),
        "lowStockItems": lowStockMaterials[:5],
        "stockouts": stockouts[:4],
        "stockoutTotal": len(stockouts),
        "utilizationPercent": utilizationPercent
    }

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

    onScheduleCount = len([o for o in uncompletedOrders if o.dueDate and o.dueDate >= today])
    scheduleTracker = {
        "overdue": len(overdueOrders),
        "dueToday": len(dueTodayOrders),
        "dueThisWeek": len(dueThisWeekOrders),
        "onSchedule": onScheduleCount,
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
        dailyRows = fetchAll("""
            SELECT order_date, COUNT(*) AS order_count, COALESCE(SUM(planned_quantity), 0) AS total_units
            FROM prod_productionorder
            WHERE order_date >= %s AND order_date <= %s
            GROUP BY order_date
        """, (monday, sunday))
        for r in dailyRows:
            dailyActivityMap[r["order_date"]] = {
                "orders": int(r["order_count"]),
                "units": int(r["total_units"])
            }
        prevRow = fetchOne("""
            SELECT COUNT(*) AS order_count, COALESCE(SUM(planned_quantity), 0) AS total_units
            FROM prod_productionorder
            WHERE order_date >= %s AND order_date <= %s
        """, (prevMonday, prevSunday))
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
    monitoringMap = {m.orderID: m for m in allMonitoring}
    recentOrdersList = []
    for o in allOrders[:6]:
        mon = monitoringMap.get(o.orderID)
        rawProg = mon.progress if (mon and mon.progress is not None) else 0.0
        prog = float(rawProg)

        if o.status == "Completed":
            stageLabel = "QC Passed & Stocked"
            prog = 100.0
        elif o.status == "Draft":
            stageLabel = "Draft · Unscheduled" if not o.dueDate else "Draft · Scheduled"
            prog = 0.0
        elif o.status == "Released":
            stageLabel = "Released to Floor"
            prog = 0.0
        elif prog <= 25.0:
            stageLabel = "Stage 1: Cutting & Sizing"
        elif prog <= 50.0:
            stageLabel = "Stage 2: Joinery & Assembly"
        elif prog <= 75.0:
            stageLabel = "Stage 3: Sanding & Finishing"
        elif prog <= 90.0:
            stageLabel = "Stage 4: Ready for QC"
        else:
            stageLabel = "QC Inspection"

        daysLeft = (o.dueDate - today).days if o.dueDate else None
        if daysLeft is not None:
            if daysLeft < 0:
                urgency = "overdue"
                urgencyText = f"{abs(daysLeft)} Days Overdue"
            elif daysLeft == 0:
                urgency = "today"
                urgencyText = "Due Today"
            elif daysLeft <= 3:
                urgency = "urgent"
                urgencyText = f"Due in {daysLeft}d"
            else:
                urgency = "normal"
                urgencyText = f"Due {o.dueDate.strftime('%b %d')}"
        else:
            urgency = "unscheduled"
            urgencyText = "Unscheduled"

        smartAction = {
            "label": "View",
            "url": f"/production/orders/{o.orderID}",
            "cls": "secondary",
            "icon": "fa-eye"
        }
        if o.status == "Completed":
            smartAction = {
                "label": "View QC",
                "url": "/production/finished-goods",
                "cls": "secondary",
                "icon": "fa-certificate"
            }
        elif prog >= 90.0:
            smartAction = {
                "label": "Inspect QC",
                "url": "/production/finished-goods",
                "cls": "primary",
                "icon": "fa-microscope"
            }
        elif o.status == "In Progress":
            smartAction = {
                "label": "Update Stage",
                "url": "/production/monitoring",
                "cls": "secondary",
                "icon": "fa-sliders"
            }
        elif o.status == "Released":
            smartAction = {
                "label": "Issue Materials",
                "url": "/production/issuance",
                "cls": "primary",
                "icon": "fa-dolly"
            }
        elif o.status == "Draft" and (not o.dueDate or not getattr(o, "assignedTo", None)):
            smartAction = {
                "label": "Plan & Assign",
                "url": "/production/planning",
                "cls": "warning",
                "icon": "fa-calendar-plus"
            }

        recentOrdersList.append({
            "orderID": o.orderID,
            "furnitureName": o.furnitureName,
            "furnitureType": getattr(o, "furnitureType", "") or "Furniture",
            "plannedQuantity": o.plannedQuantity,
            "status": o.status,
            "dueDate": o.dueDate,
            "dueDateStr": o.dueDate.strftime("%b %d, %Y") if o.dueDate else "",
            "stageLabel": stageLabel,
            "progress": int(round(prog)),
            "urgency": urgency,
            "urgencyText": urgencyText,
            "hasDueDate": bool(o.dueDate),
            "assignedStaffName": getattr(o, "assignedStaffName", "") or "Unassigned",
            "hasProof": bool(mon and mon.progress and mon.progress >= 90),
            "smartAction": smartAction
        })
    integrationEventsList = []

    def _safeEventDate(val):
        if not val:
            return today
        if isinstance(val, date):
            return val
        if hasattr(val, "date"):
            return val.date()
        return today

    isMgr = is_manager_session()
    currentEmpID = session.get("employee_id")
    orderMap = {o.orderID: o for o in allOrders}

    def _matchesEmp(val, target):
        if not val or not target:
            return False
        return str(val).strip() == str(target).strip()

    activityTimeline = []
    allOutputs = []
    try:
        allOutputs = ProductionOutput.getAll()
        for out in allOutputs:
            ordObj = orderMap.get(out.orderID)
            assignedTo = getattr(ordObj, "assignedTo", None) if ordObj else None
            actorEmpID = out.inspectorID if (out.inspectorID and str(out.inspectorID).strip()) else None
            if out.qualityStatus == "Passed":
                activityTimeline.append({
                    "orderID": out.orderID,
                    "category": "passed",
                    "title": f"#PO-{out.orderID} passed QC",
                    "meta": f"{out.quantity} units added to finished goods",
                    "sortKey": (_safeEventDate(out.inspectionDate), 4, int(out.outputID or 0)),
                    "assignedTo": assignedTo,
                    "actorEmpID": actorEmpID
                })
            elif out.qualityStatus == "Rework":
                activityTimeline.append({
                    "orderID": out.orderID,
                    "category": "rework",
                    "title": f"#PO-{out.orderID} sent back for rework",
                    "meta": out.reason or out.furnitureName,
                    "sortKey": (_safeEventDate(out.inspectionDate), 4, int(out.outputID or 0)),
                    "assignedTo": assignedTo,
                    "actorEmpID": actorEmpID
                })
    except Exception:
        allOutputs = []

    for mon in activeMonitoring:
        if mon.progress and mon.progress > 0:
            stageLabel = "Cutting & Sizing" if mon.progress <= 25 else (
                "Joinery & Assembly" if mon.progress <= 50 else (
                    "Sanding & Finishing" if mon.progress <= 75 else "Ready for QC"
                )
            )
            ordObj = orderMap.get(mon.orderID)
            assignedTo = mon.assignedTo or (getattr(ordObj, "assignedTo", None) if ordObj else None)
            activityTimeline.append({
                "orderID": mon.orderID,
                "category": "stage",
                "title": f"#PO-{mon.orderID} moved to {int(mon.progress)}% · {stageLabel}",
                "meta": "Workshop update",
                "sortKey": (_safeEventDate(mon.startDate), 3, int(mon.monitoringID or 0)),
                "assignedTo": assignedTo,
                "actorEmpID": assignedTo
            })

    try:
        recentIssuances = MaterialIssuance.getAll()
        seenIssuanceOrders = set()
        for iss in recentIssuances:
            if iss.orderID not in seenIssuanceOrders:
                seenIssuanceOrders.add(iss.orderID)
                ordObj = orderMap.get(iss.orderID)
                assignedTo = getattr(ordObj, "assignedTo", None) if ordObj else None
                activityTimeline.append({
                    "orderID": iss.orderID,
                    "category": "issued",
                    "title": f"Materials issued for #PO-{iss.orderID}",
                    "meta": "Stock deducted from inventory",
                    "sortKey": (_safeEventDate(iss.issueDate), 2, int(iss.issuanceID or 0)),
                    "assignedTo": assignedTo,
                    "actorEmpID": None
                })
    except Exception:
        pass

    for o in allOrders:
        dueText = f"due {o.dueDate.strftime('%b. %d')}" if o.dueDate else "not scheduled"
        activityTimeline.append({
            "orderID": o.orderID,
            "category": "created",
            "title": f"#PO-{o.orderID} created · {o.furnitureName}",
            "meta": f"{o.plannedQuantity} units · {dueText}",
            "sortKey": (_safeEventDate(o.orderDate), 1, int(o.orderID or 0)),
            "assignedTo": getattr(o, "assignedTo", None),
            "actorEmpID": None
        })

    if not isMgr:
        activityTimeline = [
            act for act in activityTimeline
            if currentEmpID and (_matchesEmp(act.get("assignedTo"), currentEmpID) or _matchesEmp(act.get("actorEmpID"), currentEmpID))
        ]

    activityTimeline.sort(key=lambda x: x["sortKey"], reverse=True)
    for act in activityTimeline:
        act["dateStr"] = act["sortKey"][0].strftime("%b. %d")

    def _ringDash(pct):
        pct = max(0, min(100, int(round(pct))))
        return f"{pct} {100 - pct}"

    datedActive = [o for o in uncompletedOrders if o.dueDate]
    datedOnTrack = [o for o in datedActive if o.dueDate >= today]
    onSchedulePct = int(round(len(datedOnTrack) / len(datedActive) * 100)) if datedActive else None

    progressValues = [float(m.progress or 0) for m in activeMonitoring]
    avgProgressPct = int(round(sum(progressValues) / len(progressValues))) if progressValues else None

    inspectedOutputs = [out for out in allOutputs if out.qualityStatus in ("Passed", "Rework", "Failed")]
    inspectedUnits = sum(int(out.quantity or 0) for out in inspectedOutputs)
    passedUnits = sum(int(out.quantity or 0) for out in inspectedOutputs if out.qualityStatus == "Passed")
    qcPassPct = int(round(passedUnits / inspectedUnits * 100)) if inspectedUnits > 0 else None

    try:
        allFurniture = Furniture.getAll()
    except Exception:
        allFurniture = []

    totalProducts = len(allFurniture)
    stockoutFurnitureIDs = {s["furniture_id"] for s in stockouts}
    productsInStockCount = max(0, totalProducts - len(stockoutFurnitureIDs))
    productsInStockPct = int(round(productsInStockCount / totalProducts * 100)) if totalProducts > 0 else None
    totalIncomingUnits = sum(int(s.get("total_incoming_qty") or 0) for s in stockouts)

    if totalProducts == 0 or productsInStockCount == 0:
        stockDotColor = "#9A4A3A"
    elif productsInStockCount == totalProducts:
        stockDotColor = "#66754C"
    else:
        stockDotColor = "#8E9B6D"

    awaitingQCUnits = sum(
        int(orderMap[m.orderID].plannedQuantity or 0)
        for m in activeMonitoring
        if m.progress and m.progress >= 90 and m.orderID in orderMap
    )

    if isMgr:
        if overdueOrders:
            schedVal = f"{len(overdueOrders)} Overdue"
            schedNote = f"Next: {datedOrders[0].dueDate.strftime('%b %d')}" if datedOrders else "Overdue orders"
        elif datedActive:
            schedVal = f"{len(datedOnTrack)} On Track"
            schedNote = f"Next due: {datedOrders[0].dueDate.strftime('%b %d')}"
        else:
            schedVal = "No Deadlines"
            schedNote = "None scheduled"

        if activeMonitoring:
            wipNote = f"{len(activeMonitoring)} active batch{'es' if len(activeMonitoring) != 1 else ''}"
        elif readyForIssuanceUnits > 0:
            wipNote = f"{readyForIssuanceUnits} awaiting materials"
        else:
            wipNote = "No active batches"

        if awaitingQCOrders > 0:
            qcVal = f"{awaitingQCOrders} {'Batch' if awaitingQCOrders == 1 else 'Batches'}"
            qcPct = 100
            qcNote = "Awaiting inspection"
        elif inspectedUnits > 0:
            qcVal = f"{qcPassPct}% Pass"
            qcPct = qcPassPct
            qcNote = f"{passedUnits}/{inspectedUnits} passed"
        else:
            qcVal = "0 Pending"
            qcPct = 0
            qcNote = "No batches at QC"

        if not stockouts:
            fgNote = "All products stocked"
        elif totalIncomingUnits > 0:
            fgNote = f"{totalIncomingUnits} incoming"
        else:
            fgNote = f"{len(stockouts)} out of stock"

        dashRings = [
            {
                "label": "In Progress",
                "value": f"{inProgressOrders} {'Batch' if inProgressOrders == 1 else 'Batches'}",
                "note": f"{activeWipUnits} units in workshop" if inProgressOrders else "No active batches",
                "dash": _ringDash(avgProgressPct) if avgProgressPct is not None else "",
                "pct": max(0, min(100, int(round(avgProgressPct)))) if avgProgressPct is not None else 0,
                "isAlert": False,
                "showDot": False,
                "color": "#66754C",
                "url": url_for("production.monitoringList")
            },
            {
                "label": "Total Orders",
                "value": str(len(allOrders)),
                "note": f"{completedOrders} completed | {inProgressOrders} active",
                "dash": _ringDash(int(round(completedOrders / len(allOrders) * 100))) if allOrders else "",
                "pct": int(round(completedOrders / len(allOrders) * 100)) if allOrders else 0,
                "isAlert": False,
                "showDot": False,
                "color": "#66754C",
                "url": url_for("production.orderList")
            },
            {
                "label": "Inventory Stocks",
                "value": f"{productsInStockCount} / {totalProducts}" if totalProducts > 0 else "0 / 0",
                "note": fgNote,
                "dash": _ringDash(productsInStockPct) if productsInStockPct is not None else "",
                "pct": max(0, min(100, int(round(productsInStockPct)))) if productsInStockPct is not None else 0,
                "isAlert": productsInStockCount == 0,
                "showDot": True,
                "color": stockDotColor,
                "url": "/production/orders?stockouts=1" if stockouts else url_for("production.furnitureList")
            }
        ]
    else:
        myUncompleted = [o for o in uncompletedOrders if currentEmpID and o.assignedTo == currentEmpID]
        myInProgress = [o for o in myUncompleted if o.status == "In Progress"]
        myProgVals = []
        for o in myInProgress:
            mon = monitoringMap.get(o.orderID)
            prog = float(mon.progress or 0) if mon else 0.0
            myProgVals.append(prog)
        myAvgProg = int(round(sum(myProgVals) / len(myProgVals))) if myProgVals else 0

        myAllOrders = [o for o in allOrders if currentEmpID and o.assignedTo == currentEmpID]
        myCompleted = [o for o in myAllOrders if o.status == "Completed"]
        myTotalPct = int(round(len(myCompleted) / len(myAllOrders) * 100)) if myAllOrders else 0

        dashRings = [
            {
                "label": "In Progress",
                "value": f"{len(myInProgress)} {'Batch' if len(myInProgress) == 1 else 'Batches'}",
                "note": f"{myAvgProg}% avg progress" if myInProgress else "No active batches",
                "dash": _ringDash(myAvgProg),
                "pct": max(0, min(100, myAvgProg)),
                "isAlert": False,
                "showDot": False,
                "color": "#66754C",
                "url": url_for("production.monitoringList")
            },
            {
                "label": "Total Orders",
                "value": str(len(myAllOrders)),
                "note": f"{len(myCompleted)} completed | {len(myInProgress)} active",
                "dash": _ringDash(myTotalPct),
                "pct": myTotalPct,
                "isAlert": False,
                "showDot": False,
                "color": "#66754C",
                "url": url_for("production.orderList")
            },
            {
                "label": "Inventory Stocks",
                "value": f"{productsInStockCount} / {totalProducts}" if totalProducts > 0 else "0 / 0",
                "note": fgNote,
                "dash": _ringDash(productsInStockPct) if productsInStockPct is not None else "",
                "pct": max(0, min(100, int(round(productsInStockPct)))) if productsInStockPct is not None else 0,
                "isAlert": productsInStockCount == 0,
                "showDot": True,
                "color": stockDotColor,
                "url": url_for("production.furnitureList")
            }
        ]

    chartOutputs = []
    chartError = False
    try:
        chartOutputs = ProductionOutput.getAll(startDate=monday, endDate=sunday, qualityStatus="Passed")
    except Exception as err:
        logger.exception("Failed to query chart inspection outputs: %s", err)
        chartOutputs = []
        chartError = True

    ordersPerDay = [0] * 7
    unitsPassedPerDay = [0] * 7
    for i in range(7):
        dayDate = monday + timedelta(days=i)
        stats = dailyActivityMap.get(dayDate, {"orders": 0, "units": 0})
        ordersPerDay[i] = stats["orders"]
        unitsPassedPerDay[i] = sum(int(out.quantity or 0) for out in chartOutputs if _safeEventDate(out.inspectionDate) == dayDate)

    peak = max(ordersPerDay + unitsPassedPerDay)
    if peak <= 3:
        step, chartMax = 1, 3
    elif peak <= 4:
        step, chartMax = 1, 4
    elif peak <= 6:
        step, chartMax = 2, 6
    elif peak <= 10:
        step, chartMax = 5, 10
    elif peak <= 15:
        step, chartMax = 5, 15
    elif peak <= 20:
        step, chartMax = 5, 20
    elif peak <= 30:
        step, chartMax = 10, 30
    elif peak <= 40:
        step, chartMax = 10, 40
    elif peak <= 50:
        step, chartMax = 10, 50
    elif peak <= 75:
        step, chartMax = 25, 75
    elif peak <= 100:
        step, chartMax = 25, 100
    else:
        roughStep = peak / 4.0
        mag = 10 ** math.floor(math.log10(roughStep))
        norm = roughStep / mag
        if norm <= 1.5:
            step = int(1 * mag)
        elif norm <= 3.5:
            step = int(2.5 * mag) if mag >= 10 and int(2.5 * mag) == 2.5 * mag else int(2 * mag)
        elif norm <= 7.5:
            step = int(5 * mag)
        else:
            step = int(10 * mag)
        chartMax = int(math.ceil(peak / step) * step)
    tickVals = list(range(0, chartMax + step, step))
    chartLeft, chartRight, chartTop, chartBottom = 40.0, 580.0, 18.0, 190.0
    plotH = chartBottom - chartTop
    stepX = (chartRight - chartLeft) / 6.0

    def _chartPoint(i, v):
        x = round(chartLeft + i * stepX, 1)
        y = round(chartBottom - (v / chartMax) * plotH, 1)
        return x, y

    unitPts = [_chartPoint(i, unitsPassedPerDay[i]) for i in range(7)]
    orderPts = [_chartPoint(i, ordersPerDay[i]) for i in range(7)]
    unitLine = " ".join(f"{x},{y}" for x, y in unitPts)
    orderLine = " ".join(f"{x},{y}" for x, y in orderPts)
    unitArea = f"{chartLeft},{chartBottom} {unitLine} {chartRight},{chartBottom}"

    daysData = []
    labels = []
    for i in range(7):
        d = monday + timedelta(days=i)
        isToday = (d == today)
        tooltipText = f"{dayNames[i]}, {d.strftime('%b %d')}: {unitsPassedPerDay[i]} units passed QC · {ordersPerDay[i]} orders created"
        x = unitPts[i][0]
        if i == 0:
            rectX = 0.0
            rectW = round(x + stepX / 2, 1)
        elif i == 6:
            rectX = round(x - stepX / 2, 1)
            rectW = round(620.0 - rectX, 1)
        else:
            rectX = round(x - stepX / 2, 1)
            rectW = round(stepX, 1)
        daysData.append({
            "rectX": rectX,
            "rectW": rectW,
            "unitX": unitPts[i][0],
            "unitY": unitPts[i][1],
            "orderX": orderPts[i][0],
            "orderY": orderPts[i][1],
            "unitsPassed": unitsPassedPerDay[i],
            "ordersCreated": ordersPerDay[i],
            "tooltip": tooltipText,
            "isToday": isToday
        })
        labels.append({
            "x": round(chartLeft + i * stepX, 1),
            "text": f"{dayNames[i]} {d.strftime('%d')}",
            "isToday": isToday
        })

    lineChart = {
        "hasError": chartError,
        "hasData": True,
        "unitLine": unitLine,
        "orderLine": orderLine,
        "unitArea": unitArea,
        "daysData": daysData,
        "labels": labels,
        "ticks": [{"v": v, "y": round(chartBottom - (v / chartMax) * plotH, 1)} for v in tickVals],
        "totalUnits": sum(unitsPassedPerDay),
        "totalOrders": sum(ordersPerDay)
    }

    statusSegmentsRaw = [
        ("Draft", draftOrders, "#D5C7AA"),
        ("Released", releasedOrders, "#A9B689"),
        ("In Progress", inProgressOrders, "#8E9B6D"),
        ("Completed", completedOrders, "#66754C")
    ]
    statusTotal = sum(s[1] for s in statusSegmentsRaw)
    donutSegments = []
    cumulative = 0.0
    for label, count, color in statusSegmentsRaw:
        pct = (count / statusTotal * 100) if statusTotal > 0 else 0
        donutSegments.append({
            "label": label,
            "count": count,
            "color": color,
            "dash": f"{round(pct, 2)} {round(100 - pct, 2)}",
            "offset": round((25 - cumulative) % 100, 2),
            "show": count > 0
        })
        cumulative += pct

    timelineScope = uncompletedOrders if isMgr else [o for o in uncompletedOrders if currentEmpID and o.assignedTo == currentEmpID]
    overdueTimeline = sum(1 for o in timelineScope if o.dueDate and o.dueDate < today)
    dueThisWeekTimeline = sum(1 for o in timelineScope if o.dueDate and today <= o.dueDate <= today + timedelta(days=7))
    upcomingTimeline = sum(1 for o in timelineScope if o.dueDate and o.dueDate > today + timedelta(days=7))
    unscheduledTimeline = sum(1 for o in timelineScope if not o.dueDate)

    timelineSegmentsRaw = [
        ("Overdue", overdueTimeline, "#9A4A3A"),
        ("Due This Week", dueThisWeekTimeline, "#C28B38"),
        ("Upcoming", upcomingTimeline, "#66754C"),
        ("Unscheduled", unscheduledTimeline, "#D5C7AA")
    ]
    timelineTotal = sum(s[1] for s in timelineSegmentsRaw)
    timelineSegments = []
    cumulativeTimeline = 0.0
    for label, count, color in timelineSegmentsRaw:
        pct = (count / timelineTotal * 100) if timelineTotal > 0 else 0
        timelineSegments.append({
            "label": label,
            "count": count,
            "color": color,
            "dash": f"{round(pct, 2)} {round(100 - pct, 2)}",
            "offset": round((25 - cumulativeTimeline) % 100, 2),
            "show": count > 0
        })
        cumulativeTimeline += pct

    activeOrdersList = []
    for o in uncompletedOrders:
        mon = monitoringMap.get(o.orderID)
        prog = int(round(float(mon.progress))) if (mon and mon.progress is not None) else 0
        isMine = bool(currentEmpID and o.assignedTo == currentEmpID)
        if o.status == "In Progress":
            if prog >= 90:
                stageText = "Stage 4: Ready for QC"
                actionText = "Inspect QC" if isMgr else "View Order"
                actionUrl = url_for("production.finishedGoodsList") if isMgr else url_for("production.orderDetail", orderID=o.orderID)
            elif prog >= 75:
                stageText = "Stage 3: Sanding & Finishing"
                actionText = "Update Progress"
                actionUrl = url_for("production.monitoringList")
            elif prog >= 50:
                stageText = "Stage 2: Joinery & Assembly"
                actionText = "Update Progress"
                actionUrl = url_for("production.monitoringList")
            elif prog >= 25:
                stageText = "Stage 1: Cutting & Sizing"
                actionText = "Update Progress"
                actionUrl = url_for("production.monitoringList")
            else:
                stageText = "Not Started"
                actionText = "Start Assembly"
                actionUrl = url_for("production.monitoringList")
        elif o.status == "Released":
            stageText = "Released to Floor"
            actionText = "Issue Materials" if isMgr else "View Order"
            actionUrl = url_for("production.issuanceList") if isMgr else url_for("production.orderDetail", orderID=o.orderID)
        else:
            stageText = "Draft Intake" if not o.dueDate else "Planned"
            actionText = "Plan Order" if isMgr else "View Order"
            actionUrl = url_for("production.planningList") if isMgr else url_for("production.orderDetail", orderID=o.orderID)
        activeOrdersList.append({
            "orderID": o.orderID,
            "furnitureName": o.furnitureName,
            "furnitureType": o.furnitureType or "",
            "plannedQuantity": o.plannedQuantity,
            "status": o.status,
            "statusClass": "inProgress" if o.status == "In Progress" else ("released" if o.status == "Released" else "draft"),
            "progress": prog,
            "stageText": stageText,
            "staffName": o.assignedStaffName or "Unassigned",
            "isAssignedToMe": isMine,
            "dueDate": o.dueDate,
            "dueDateStr": o.dueDate.strftime("%b. %d, %Y") if o.dueDate else "Not set",
            "isOverdue": bool(o.dueDate and o.dueDate < today),
            "actionText": actionText,
            "actionUrl": actionUrl
        })

    if not isMgr:
        activeOrdersList.sort(key=lambda item: (0 if item["isAssignedToMe"] else 1, -int(item["orderID"] or 0)))

    def _fmtQty(val):
        txt = f"{val:f}".rstrip("0").rstrip(".") if "." in f"{val:f}" else f"{val:f}"
        return txt or "0"

    lowStockList = [
        {
            "materialID": m.materialID,
            "itemCode": getattr(m, "itemCode", "") or str(m.materialID),
            "name": m.materialName,
            "onHand": f"{_fmtQty(m.currentStock)} {m.unit or ''}".strip(),
            "unitCost": m.unitCost
        }
        for m in materials if m.currentStock <= Decimal("0.000")
    ][:5]

    activeOrderSummary = {
        "total": len(activeOrdersList),
        "mine": sum(1 for a in activeOrdersList if a["isAssignedToMe"]),
        "draft": sum(1 for a in activeOrdersList if a["status"] == "Draft"),
        "released": sum(1 for a in activeOrdersList if a["status"] == "Released"),
        "inProgress": sum(1 for a in activeOrdersList if a["status"] == "In Progress"),
        "totalUnits": sum(int(a["plannedQuantity"] or 0) for a in activeOrdersList)
    }

    stockoutSummary = {
        "total": len(stockouts),
        "needsBom": sum(1 for s in stockouts if not s.get("active_order_id") and int(s.get("bom_item_count") or 0) == 0),
        "ready": sum(1 for s in stockouts if not s.get("active_order_id") and int(s.get("bom_item_count") or 0) > 0),
        "restocking": sum(1 for s in stockouts if s.get("active_order_id")),
        "totalIncomingUnits": totalIncomingUnits
    }

    now = datetime.now()
    hour = now.hour
    if 5 <= hour < 12:
        greetingText = "Good morning"
    elif 12 <= hour < 18:
        greetingText = "Good afternoon"
    else:
        greetingText = "Good evening"

    empName = session.get("employee_name", "Operator")
    firstName = empName.split()[0] if empName else "Operator"
    lastUpdatedTime = now.strftime("%I:%M %p").lstrip("0")

    return render_template(
        "production/dashboard/dashboard.html",
        activeTab="dashboard",
        databaseStatus=databaseStatusMessage,
        metrics=metricsData,
        recentOrders=recentOrdersList,
        integrationEvents=integrationEventsList,
        activityTimeline=activityTimeline,
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
        scheduleTracker=scheduleTracker,
        greetingText=greetingText,
        firstName=firstName,
        lastUpdatedTime=lastUpdatedTime,
        dashRings=dashRings,
        lineChart=lineChart,
        donutSegments=donutSegments,
        timelineSegments=timelineSegments,
        timelineTotal=timelineTotal,
        activeOrdersList=activeOrdersList,
        activeOrderSummary=activeOrderSummary,
        stockoutSummary=stockoutSummary,
        lowStockList=lowStockList,
        warehouseStockouts=stockouts
    )

@productionBlueprint.route("/furniture")
@manager_required
def furnitureList():
    searchQuery = request.args.get("q", "").strip()
    selectedCategory = request.args.get("category", "").strip()
    try:
        furnitureItemList = Furniture.getAll()
        categoriesList = Furniture.getCategories()
        categoryCounts = {}
        for item in furnitureItemList:
            c = item.furnitureType
            if c:
                categoryCounts[c] = categoryCounts.get(c, 0) + 1
    except Exception as err:
        flash(f"Failed to load products from database: {str(err)}", "alert")
        furnitureItemList = []
        categoriesList = []
        categoryCounts = {}

    return render_template(
        "production/products/furniture_list.html",
        activeTab="furniture",
        furnitureItems=furnitureItemList,
        categories=categoriesList,
        categoryCounts=categoryCounts,
        searchQuery=searchQuery,
        selectedCategory=selectedCategory
    )

@productionBlueprint.route("/furniture/add", methods=["POST"])
@manager_required
def addFurniture():
    furnitureName = request.form.get("furnitureName", "").strip()
    furnitureType = request.form.get("furnitureType", "").strip()

    if not furnitureName or not furnitureType:
        flash("Product name and category are required.", "error")
        return redirect(url_for("production.furnitureList"))

    try:
        if Furniture.existsByName(furnitureName):
            flash(f"A product named '{furnitureName}' already exists in the catalog.", "warning")
            return redirect(url_for("production.furnitureList"))

        Furniture.addFurniture(furnitureName, furnitureType)
        flash(f"Product '{furnitureName}' registered successfully.", "success")
    except UniqueViolation:
        flash(f"A product named '{furnitureName}' already exists in the catalog.", "warning")
    except Exception as err:
        flash(f"DB error while adding product: {str(err)}", "error")

    return redirect(url_for("production.furnitureList"))

@productionBlueprint.route("/furniture/edit/<int:furnitureID>", methods=["POST"])
@manager_required
def editFurniture(furnitureID):
    furnitureName = request.form.get("furnitureName", "").strip()
    furnitureType = request.form.get("furnitureType", "").strip()

    if not furnitureName or not furnitureType:
        flash("Product name and category are required.", "error")
        return redirect(url_for("production.furnitureList"))

    try:
        if Furniture.existsByName(furnitureName, excludeID=furnitureID):
            flash(f"Another product with the name '{furnitureName}' already exists.", "warning")
            return redirect(url_for("production.furnitureList"))

        updated = Furniture.updateFurniture(furnitureID, furnitureName, furnitureType)
        if updated:
            flash(f"Product '{furnitureName}' updated successfully.", "success")
        else:
            flash("Product not found.", "error")
    except UniqueViolation:
        flash(f"Another product with the name '{furnitureName}' already exists.", "warning")
    except Exception as err:
        flash(f"DB error while updating product: {str(err)}", "error")

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
        flash(f"DB error while deleting product: {str(err)}", "error")

    return redirect(url_for("production.furnitureList"))

@productionBlueprint.route("/materials")
@manager_required
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
@manager_required
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
            flash(f"Failed to load BOM: {str(err)}", "error")
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
        flash(f"DB error while saving BOM item: {str(err)}", "error")

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
        flash("Component removed from BOM.", "success")
    except Exception as err:
        flash(f"DB error while removing component: {str(err)}", "error")

    return redirect(url_for("production.bomList", furniture_id=furnitureID))

@productionBlueprint.route("/bom/update-price", methods=["POST"])
@manager_required
def updateFurniturePriceFromBom():
    furnitureID = request.form.get("furnitureID", "").strip()
    return redirect(url_for("production.bomList", furniture_id=furnitureID if furnitureID.isdigit() else None))

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

    currentEmpID = session.get("employee_id")
    if not is_manager_session():
        productionOrderList = [o for o in productionOrderList if currentEmpID and getattr(o, "assignedTo", None) == currentEmpID]
        summary = {
            "total": len(productionOrderList),
            "draft": sum(1 for o in productionOrderList if o.status == "Draft"),
            "released": sum(1 for o in productionOrderList if o.status == "Released"),
            "inProgress": sum(1 for o in productionOrderList if o.status == "In Progress"),
            "completed": sum(1 for o in productionOrderList if o.status == "Completed")
        }
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

        currentEmpID = session.get("employee_id")
        if not is_manager_session() and (not currentEmpID or getattr(order, "assignedTo", None) != currentEmpID):
            flash("You can only view production orders assigned to you.", "warning")
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
        flash("Cannot create production order: Selected product does not have a configured Bill of Materials. Please configure its BOM first.", "error")
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
        flash(f"DB error while creating production order: {str(err)}", "error")

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
        flash(f"DB error while deleting order: {str(err)}", "error")

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
        flash(f"DB error while updating schedule: {str(err)}", "error")

    return redirect(targetRedirect)

@productionBlueprint.route("/requirements")
@productionBlueprint.route("/requirement")
@manager_required
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
            flash(f"Cannot release order: No BOM components defined for '{order.furnitureName}'.", "warning")
            return redirect(url_for("production.requirementList", order_id=orderID))

        matsMap = {m.materialID: m for m in Material.getAll(useCache=False)}
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
        invalidateKeys("orders_all", "orders_summary", "materials_all", "furniture_all")
        flash(f"Order #PO-{orderID} released to production successfully. Ready for Material Issuance.", "success")
    except Exception as err:
        flash(f"Failed to release order: {str(err)}", "error")

    return redirect(url_for("production.requirementList", order_id=orderID))

@productionBlueprint.route("/issuance")
@manager_required
def issuanceList():
    try:
        allOrders = ProductionOrder.getAll(useCache=False)
        releasedOrders = [o for o in allOrders if o.status == "Released"]
        matsMap = {m.materialID: m for m in Material.getAll(useCache=False)}
        bomCache = {}
        totalReadyUnits = 0
        totalBatchValue = Decimal("0.00")
        shortageOrderCount = 0
        for o in releasedOrders:
            if o.furnitureID not in bomCache:
                bomCache[o.furnitureID] = BillOfMaterials.getByFurnitureID(o.furnitureID, autoCreate=False)
            bom = bomCache[o.furnitureID]
            if bom:
                reqs = bom.calculateRequirements(Decimal(str(o.plannedQuantity)))
            else:
                reqs = []
            orderShortage = False
            orderCost = Decimal("0.00")
            for r in reqs:
                mat = matsMap.get(r["materialID"])
                onHand = mat.currentStock if mat else Decimal("0.000")
                deficit = max(Decimal("0.000"), r["batchQuantity"] - onHand)
                r["onHand"] = onHand
                r["deficit"] = deficit
                r["sufficient"] = (deficit == Decimal("0.000"))
                orderCost += Decimal(str(r.get("batchCost") or 0))
                if deficit > Decimal("0.000"):
                    orderShortage = True
            o.requirements = reqs
            o.estimatedMaterialCost = orderCost
            o.hasShortage = orderShortage or (len(reqs) == 0)
            o.shortageCount = sum(1 for r in reqs if r["deficit"] > Decimal("0.000"))
            totalReadyUnits += int(o.plannedQuantity or 0)
            totalBatchValue += orderCost
            if o.hasShortage:
                shortageOrderCount += 1
        materialIssuanceList = MaterialIssuance.getAll()
    except Exception as err:
        flash(f"Failed to load issuance records: {str(err)}", "error")
        releasedOrders = []
        materialIssuanceList = []
        totalReadyUnits = 0
        totalBatchValue = Decimal("0.00")
        shortageOrderCount = 0

    issuanceSummary = {
        "queueCount": len(releasedOrders),
        "readyCount": sum(1 for o in releasedOrders if not getattr(o, "hasShortage", False)),
        "shortageCount": shortageOrderCount,
        "totalUnits": totalReadyUnits,
        "totalBatchValue": totalBatchValue,
        "historyCount": len(materialIssuanceList)
    }

    return render_template(
        "production/materials/issuance_list.html",
        activeTab="issuance",
        releasedOrders=releasedOrders,
        issuances=materialIssuanceList,
        issuanceSummary=issuanceSummary
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

            execute("""
                INSERT INTO prod_productionmonitoring (order_id, progress, start_date)
                VALUES (%s, 0.0, CURRENT_DATE)
                ON CONFLICT (order_id) DO NOTHING
            """, (orderID,), conn=conn)

            ProductionOrder.updateStatus(orderID, "In Progress", conn=conn)

        invalidateKeys("materials_all", "orders_all", "orders_summary", "furniture_all")
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
        90: "Stage 4: Ready for QC",
        100: "QC Passed & Completed"
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
            flash("A proof is required when submitting Stage 4 (Ready for QC).", "error")
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
@manager_required
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
            orderRow = fetchOne("""
                SELECT po.order_id, po.furniture_id, po.planned_quantity, po.status, po.assigned_to, f.furniture_name
                FROM prod_productionorder po
                JOIN prod_furniture f ON po.furniture_id = f.furniture_id
                WHERE po.order_id = %s
                FOR UPDATE
            """, (orderID,), conn=conn)

            if not orderRow:
                flash("Production order not found.", "error")
                return redirect(url_for("production.finishedGoodsList"))

            if orderRow["status"] != "In Progress":
                flash(f"Order #PO-{orderID} is '{orderRow['status']}'. Quality inspection is only allowed for 'In Progress' orders.", "warning")
                return redirect(url_for("production.finishedGoodsList"))

            monitoringRow = fetchOne("""
                SELECT monitoring_id, progress, COALESCE(rework_count, 0) AS rework_count
                FROM prod_productionmonitoring
                WHERE order_id = %s
                FOR UPDATE
            """, (orderID,), conn=conn)

            if not monitoringRow or float(monitoringRow["progress"]) < 90.0:
                currentProg = int(round(float(monitoringRow["progress"]))) if monitoringRow else 0
                flash(f"Order #PO-{orderID} assembly is at {currentProg}%. Workshop assembly must reach at least 90% before inspection.", "warning")
                return redirect(url_for("production.finishedGoodsList"))

            countsRow = fetchOne("""
                SELECT 
                    COALESCE(SUM(CASE WHEN quality_status = 'Passed' THEN quantity ELSE 0 END), 0) AS total_passed,
                    COALESCE(SUM(CASE WHEN quality_status = 'Failed' THEN quantity ELSE 0 END), 0) AS total_failed
                FROM prod_productionoutput
                WHERE order_id = %s
            """, (orderID,), conn=conn)
            alreadyPassed = int(countsRow["total_passed"]) if countsRow else 0
            alreadyFailed = int(countsRow["total_failed"]) if countsRow else 0
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
                msg = f"Order #PO-{orderID} QC submitted: {passedQty} passed, {reworkQty} returned to workshop (Rework #{currentReworks + 1}/2 at {int(ProductionMonitoring.REWORK_STAGE_PROGRESS)}%)"
                if failedQty > 0:
                    msg += f", {failedQty} {unitWord} scrapped"
                flash(msg + ".", "warning")

    except ValueError as valErr:
        flash(str(valErr), "warning")
    except Exception as err:
        flash(f"DB error during quality inspection: {str(err)}", "error")

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
                o.overheadCost = Decimal("0.00")
                o.totalCost = (savedCost.materialCost + savedCost.laborCost).quantize(Decimal("0.01"))
                o.unitCost = (o.totalCost / Decimal(str(o.plannedQuantity))).quantize(Decimal("0.01")) if o.plannedQuantity else Decimal("0.00")
                o.costDate = savedCost.costDate
                o.formattedCostDate = savedCost.formattedCostDate
            else:
                o.hasCostSheet = False
                o.costID = None
                o.materialCost = ProductionCost.calculateActualMaterialCost(o.orderID)
                o.laborCost = Decimal("0.00")
                o.overheadCost = Decimal("0.00")
                o.totalCost = (o.materialCost + o.laborCost).quantize(Decimal("0.01"))
                o.unitCost = (o.totalCost / Decimal(str(o.plannedQuantity))).quantize(Decimal("0.01")) if o.plannedQuantity else Decimal("0.00")
                o.costDate = None
                o.formattedCostDate = "-"

            goodCost, passedUnits = ProductionCost.calculateCostPerGoodUnit(o.orderID, o.totalCost)
            o.costPerGoodUnit = goodCost
            o.passedUnits = passedUnits

        allCostRecords = ProductionCost.getAll()
        totalRecordedCost = sum((c.materialCost + c.laborCost) for c in allCostRecords)
        summary = {
            "totalCost": totalRecordedCost,
            "costedOrders": len(allCostRecords),
            "pendingCosting": sum(1 for o in costOrders if not o.hasCostSheet),
            "activeOrders": len(costOrders)
        }
    except Exception as err:
        flash(f"Failed to load production costing records: {str(err)}", "error")
        costOrders = []
        allCostRecords = []
        summary = {"totalCost": Decimal("0.00"), "costedOrders": 0, "pendingCosting": 0, "activeOrders": 0}

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
            overheadCost=Decimal("0.00")
        )
        flash(f"Cost sheet saved for Order #PO-{orderID} (Total: ₱{saved.totalCost:,.2f})! Available for Team 5 Finance.", "success")
    except ValueError as valErr:
        flash(str(valErr), "warning")
    except Exception as err:
        flash(f"DB error while saving production cost: {str(err)}", "error")

    return redirect(url_for("production.costingList"))

@productionBlueprint.route("/report")
@productionBlueprint.route("/reports")
@manager_required
def reportView():
    statusFilter = request.args.get("status", "All").strip()

    try:
        rawOrders = fetchAll("""
            SELECT po.order_id,
                   po.planned_quantity,
                   po.status,
                   po.order_date,
                   po.planned_start_date,
                   po.due_date,
                   f.furniture_name,
                   f.furniture_type,
                   COALESCE(pm.progress, 0.00) AS progress,
                   pm.start_date AS actual_start_date,
                   pm.completion_date,
                   pc.cost_id,
                   pc.material_cost,
                   pc.labor_cost,
                   pc.overhead_cost,
                   pc.total_cost,
                   pc.cost_date,
                   COALESCE(iss.issued_material_cost, 0.00) AS issued_material_cost
            FROM prod_productionorder po
            JOIN prod_furniture f ON po.furniture_id = f.furniture_id
            LEFT JOIN prod_productionmonitoring pm ON po.order_id = pm.order_id
            LEFT JOIN prod_productioncost pc ON po.order_id = pc.order_id
            LEFT JOIN (
                SELECT mi.order_id,
                       SUM(mi.quantity_issued * rm.unit_cost) AS issued_material_cost
                FROM prod_materialissuance mi
                JOIN raw_material rm ON mi.material_id = rm.raw_material_id
                GROUP BY mi.order_id
            ) iss ON po.order_id = iss.order_id
            ORDER BY po.order_id DESC
        """)

        materialUsageRows = fetchAll("""
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

        allOrders = []
        for r in rawOrders:
            item = dict(r)
            item["formattedOrderDate"] = item["order_date"].strftime("%b. %d, %Y") if item.get("order_date") else "-"
            item["formattedDueDate"] = item["due_date"].strftime("%b. %d, %Y") if item.get("due_date") else "-"
            item["formattedStartDate"] = item["actual_start_date"].strftime("%b. %d, %Y") if item.get("actual_start_date") else (item["planned_start_date"].strftime("%b. %d, %Y") if item.get("planned_start_date") else "-")
            item["formattedCompletionDate"] = item["completion_date"].strftime("%b. %d, %Y") if item.get("completion_date") else ("In Progress" if item["status"] == "In Progress" else "-")
            qty = Decimal(str(item.get("planned_quantity") or 0))
            item["estimatedValue"] = Decimal("0.00")
            issuedMatCost = Decimal(str(item.get("issued_material_cost") or 0)).quantize(Decimal("0.01"))
            if item.get("total_cost") is not None:
                item["hasCostSheet"] = True
                mat = Decimal(str(item.get("material_cost") or 0))
                lab = Decimal(str(item.get("labor_cost") or 0))
                item["effectiveCost"] = (mat + lab).quantize(Decimal("0.01"))
            elif issuedMatCost > Decimal("0.00"):
                item["hasCostSheet"] = False
                item["effectiveCost"] = issuedMatCost
            else:
                item["hasCostSheet"] = False
                item["effectiveCost"] = Decimal("0.00")
            allOrders.append(item)

        issuances = MaterialIssuance.getAll()
        outputRecords = ProductionOutput.getAll()

        totalOrders = len(allOrders)
        completedOrders = sum(1 for o in allOrders if o["status"] == "Completed")
        inProgressOrders = sum(1 for o in allOrders if o["status"] == "In Progress")
        releasedOrders = sum(1 for o in allOrders if o["status"] == "Released")
        draftOrders = sum(1 for o in allOrders if o["status"] == "Draft")

        totalPlannedUnits = sum(int(o["planned_quantity"]) for o in allOrders)
        passedQAUnits = sum(int(o.quantity) for o in outputRecords if o.qualityStatus == "Passed")
        completedBatchUnits = sum(int(o["planned_quantity"]) for o in allOrders if o["status"] == "Completed")
        totalCompletedUnits = passedQAUnits if passedQAUnits > 0 else completedBatchUnits
        completionRate = int(round((completedOrders / totalOrders * 100))) if totalOrders > 0 else 0

        totalRecordedCost = sum(Decimal(str(o["total_cost"])) for o in allOrders if o.get("total_cost") is not None)
        totalIncurredCost = sum(o["effectiveCost"] for o in allOrders)
        costedOrdersCount = sum(1 for o in allOrders if o.get("hasCostSheet"))
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
            "totalIncurredCost": totalIncurredCost,
            "costedOrdersCount": costedOrdersCount,
            "totalMaterialExpense": totalMaterialExpense,
            "totalPlannedValue": totalPlannedValue
        }

        if statusFilter in ("Completed", "In Progress", "Released", "Draft"):
            filteredOrders = [o for o in allOrders if o["status"] == statusFilter]
        else:
            statusFilter = "All"
            filteredOrders = allOrders

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
            "totalIncurredCost": Decimal("0.00"),
            "costedOrdersCount": 0,
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
        lastActivity=lastActivity,
        reportDate=date.today().strftime("%B %d, %Y")
    )

@productionBlueprint.route("/logs")
@manager_required
def logsView():
    return redirect(url_for("production.reportView", tab="audit"))



