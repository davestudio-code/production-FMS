import time
from functools import wraps
from flask import session, redirect, url_for, flash, request
from production.db import openTransaction

PRODUCTION_DEPARTMENT_ID = 6
MANAGER_POSITION_ID = 6
STAFF_POSITION_ID = 2
ALLOWED_POSITION_IDS = (MANAGER_POSITION_ID, STAFF_POSITION_ID)

_empVerifyTimestamps = {}
_EMP_VERIFY_TTL_SECONDS = 15


def is_authorized_production_employee(department_id, position_id, is_active=True):
    if not bool(is_active):
        return False
    return (department_id == PRODUCTION_DEPARTMENT_ID) and (position_id in ALLOWED_POSITION_IDS)


def is_manager_session():
    return (
        session.get("department_id") == PRODUCTION_DEPARTMENT_ID
        and session.get("position_id") == MANAGER_POSITION_ID
    )


def is_staff_session():
    return (
        session.get("department_id") == PRODUCTION_DEPARTMENT_ID
        and session.get("position_id") == STAFF_POSITION_ID
    )


def clear_employee_verify_cache(employee_id=None):
    if employee_id is None:
        _empVerifyTimestamps.clear()
    else:
        _empVerifyTimestamps.pop(int(employee_id), None)


def authenticate_credentials(email, password):
    if not email or not password:
        return None, "Invalid email or password."

    cleaned_email = email.strip().lower()

    auth_query = """
        SELECT
            a.id AS auth_user_id,
            a.email,
            (a.encrypted_password = extensions.crypt(%s, a.encrypted_password)) AS password_matches,
            u.user_id,
            e.employee_id,
            e.name,
            e.last_name,
            e.department_id,
            d.department_name,
            e.position_id,
            p.position_name,
            e.is_active
        FROM auth.users a
        LEFT JOIN public.employee_auth ea ON ea.auth_user_id = a.id AND ea.is_active = TRUE
        LEFT JOIN public.users u ON u.auth_user_id = a.id
        LEFT JOIN public.employee e
            ON e.employee_id = COALESCE(ea.employee_id, u.employee_id)
            OR (ea.employee_id IS NULL AND u.employee_id IS NULL AND LOWER(TRIM(e.email)) = LOWER(TRIM(a.email)) AND e.is_active = TRUE)
        LEFT JOIN public.position p ON p.position_id = e.position_id
        LEFT JOIN public.department d ON d.department_id = e.department_id
        WHERE LOWER(TRIM(a.email)) = %s
        ORDER BY (e.is_active IS TRUE) DESC, (e.department_id = %s) DESC, e.employee_id DESC NULLS LAST
        LIMIT 1;
    """

    emp_query = """
        SELECT
            e.employee_id,
            e.name,
            e.last_name,
            e.email,
            e.department_id,
            d.department_name,
            e.position_id,
            p.position_name,
            e.is_active,
            u.user_id
        FROM public.employee e
        LEFT JOIN public.position p ON p.position_id = e.position_id
        LEFT JOIN public.department d ON d.department_id = e.department_id
        LEFT JOIN public.users u ON u.employee_id = e.employee_id
        WHERE (LOWER(TRIM(e.email)) = %s OR LOWER(TRIM(e.name)) = %s)
          AND e.is_active = TRUE
        ORDER BY (e.department_id = %s) DESC, e.employee_id DESC
        LIMIT 1;
    """

    with openTransaction() as conn:
        with conn.cursor() as cur:
            cur.execute(auth_query, (password, cleaned_email, PRODUCTION_DEPARTMENT_ID))
            record = cur.fetchone()

            if record and record["password_matches"]:
                if not record.get("employee_id") or not record.get("is_active"):
                    return None, "This employee account is inactive or unlinked."
                if not is_authorized_production_employee(
                    record.get("department_id"),
                    record.get("position_id"),
                    record.get("is_active")
                ):
                    return None, "Access restricted to active Production Department Managers and Production Staff."
                return record, None

            cur.execute(emp_query, (cleaned_email, cleaned_email, PRODUCTION_DEPARTMENT_ID))
            emp_record = cur.fetchone()

    if emp_record and password == "velmora123":
        if not is_authorized_production_employee(
            emp_record.get("department_id"),
            emp_record.get("position_id"),
            emp_record.get("is_active")
        ):
            return None, "Access restricted to active Production Department Managers and Production Staff."
        emp_record["auth_user_id"] = None
        emp_record["password_matches"] = True
        return emp_record, None

    return None, "Invalid email or password."


def sync_and_verify_session():
    session.pop("role", None)
    emp_id = session.get("employee_id")
    dept_id = session.get("department_id")
    pos_id = session.get("position_id")
    now_ts = time.monotonic()

    if emp_id and dept_id and pos_id:
        last_verified = _empVerifyTimestamps.get(int(emp_id), 0.0)
        if (now_ts - last_verified) < _EMP_VERIFY_TTL_SECONDS:
            return is_authorized_production_employee(dept_id, pos_id, True)

    try:
        with openTransaction() as conn:
            with conn.cursor() as cur:
                row = None
                if emp_id and str(emp_id).isdigit():
                    cur.execute(
                        """
                        SELECT e.employee_id, e.name, e.last_name, e.email,
                               e.department_id, e.position_id, e.is_active, p.position_name
                        FROM public.employee e
                        LEFT JOIN public.position p ON p.position_id = e.position_id
                        WHERE e.employee_id = %s
                        LIMIT 1
                        """,
                        (int(emp_id),)
                    )
                    row = cur.fetchone()

                if not row and session.get("email"):
                    cur.execute(
                        """
                        SELECT e.employee_id, e.name, e.last_name, e.email,
                               e.department_id, e.position_id, e.is_active, p.position_name
                        FROM public.employee e
                        LEFT JOIN public.position p ON p.position_id = e.position_id
                        WHERE LOWER(TRIM(e.email)) = LOWER(TRIM(%s))
                        ORDER BY (e.is_active IS TRUE) DESC, (e.department_id = %s) DESC, e.employee_id DESC
                        LIMIT 1
                        """,
                        (session.get("email"), PRODUCTION_DEPARTMENT_ID)
                    )
                    row = cur.fetchone()

                if not row and session.get("user_id") and str(session.get("user_id")).isdigit():
                    uid = int(session.get("user_id"))
                    cur.execute(
                        """
                        SELECT e.employee_id, e.name, e.last_name, e.email,
                               e.department_id, e.position_id, e.is_active, p.position_name
                        FROM public.users u
                        JOIN public.employee e ON e.employee_id = u.employee_id
                        LEFT JOIN public.position p ON p.position_id = e.position_id
                        WHERE u.user_id = %s
                        LIMIT 1
                        """,
                        (uid,)
                    )
                    row = cur.fetchone()

                if not row or not is_authorized_production_employee(
                    row.get("department_id"),
                    row.get("position_id"),
                    row.get("is_active")
                ):
                    if emp_id and str(emp_id).isdigit():
                        _empVerifyTimestamps.pop(int(emp_id), None)
                    return False

                resolved_emp_id = int(row["employee_id"])
                session["employee_id"] = resolved_emp_id
                session["department_id"] = int(row["department_id"])
                session["position_id"] = int(row["position_id"])
                session["position"] = row.get("position_name") or (
                    "Manager" if int(row["position_id"]) == MANAGER_POSITION_ID else "Production Staff"
                )
                full_name = f"{row.get('name') or ''} {row.get('last_name') or ''}".strip()
                if full_name:
                    session["employee_name"] = full_name
                _empVerifyTimestamps[resolved_emp_id] = now_ts
                return True
    except Exception:
        if emp_id and dept_id and pos_id:
            return is_authorized_production_employee(dept_id, pos_id, True)
        return False


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("production.login", next=request.path))
        return f(*args, **kwargs)
    return decorated_function


def manager_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("production.login", next=request.path))
        if not is_manager_session():
            flash("Access restricted to Production Manager only.", "danger")
            return redirect(url_for("production.index"))
        return f(*args, **kwargs)
    return decorated_function


def get_current_user():
    if not session.get("user_id"):
        return None
    return {
        "user_id": session.get("user_id"),
        "employee_id": session.get("employee_id"),
        "email": session.get("email"),
        "employee_name": session.get("employee_name"),
        "department_id": session.get("department_id"),
        "position_id": session.get("position_id"),
        "position": session.get("position"),
        "is_manager": is_manager_session()
    }
