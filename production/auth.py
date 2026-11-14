import time
import uuid
import json
import re
from functools import wraps
from flask import session, redirect, url_for, flash, request
from production.db import openTransaction

PRODUCTION_DEPARTMENT_ID = 6
MANAGER_POSITION_ID = 6
STAFF_POSITION_ID = 2
ALLOWED_POSITION_IDS = (MANAGER_POSITION_ID, STAFF_POSITION_ID)
PRODUCTION_MODULE_CODE = "production"

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


def _sync_employee_auth_links(cur, emp_id, auth_uid, pos_id):
    access_lvl = "manager" if int(pos_id) == MANAGER_POSITION_ID else "staff"
    cur.execute(
        """
        INSERT INTO public.employee_auth (auth_user_id, employee_id, is_active, created_at)
        VALUES (%s, %s, TRUE, NOW())
        ON CONFLICT (employee_id) DO UPDATE
        SET auth_user_id = EXCLUDED.auth_user_id, is_active = TRUE
        """,
        (str(auth_uid), int(emp_id)),
    )
    cur.execute("SELECT user_id, auth_user_id FROM public.users WHERE employee_id = %s LIMIT 1", (int(emp_id),))
    u_row = cur.fetchone()
    if u_row:
        if str(u_row.get("auth_user_id") or "") != str(auth_uid):
            cur.execute("UPDATE public.users SET auth_user_id = %s WHERE employee_id = %s", (str(auth_uid), int(emp_id)))
    else:
        cur.execute(
            "INSERT INTO public.users (employee_id, role, auth_user_id) VALUES (%s, %s, %s)",
            (int(emp_id), "employee", str(auth_uid)),
        )
    cur.execute(
        """
        SELECT access_id, access_level, is_active
        FROM public.employee_module_access
        WHERE auth_user_id = %s AND module_code = %s
        LIMIT 1
        """,
        (str(auth_uid), PRODUCTION_MODULE_CODE),
    )
    ma_row = cur.fetchone()
    if ma_row:
        if ma_row.get("access_level") != access_lvl or not ma_row.get("is_active"):
            cur.execute(
                "UPDATE public.employee_module_access SET access_level = %s, is_active = TRUE WHERE access_id = %s",
                (access_lvl, ma_row["access_id"]),
            )
    else:
        cur.execute(
            """
            INSERT INTO public.employee_module_access (auth_user_id, module_code, access_level, is_active, created_at)
            VALUES (%s, %s, %s, TRUE, NOW())
            """,
            (str(auth_uid), PRODUCTION_MODULE_CODE, access_lvl),
        )
    return access_lvl


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
            e.phone,
            e.department_id,
            d.department_name,
            e.position_id,
            p.position_name,
            e.is_active,
            ema.module_code,
            ema.access_level,
            ema.is_active AS module_active
        FROM auth.users a
        LEFT JOIN public.employee_auth ea ON ea.auth_user_id = a.id AND ea.is_active = TRUE
        LEFT JOIN public.users u ON u.auth_user_id = a.id
        LEFT JOIN public.employee e
            ON e.employee_id = COALESCE(ea.employee_id, u.employee_id)
            OR (ea.employee_id IS NULL AND u.employee_id IS NULL AND LOWER(TRIM(e.email)) = LOWER(TRIM(a.email)) AND e.is_active = TRUE)
        LEFT JOIN public.position p ON p.position_id = e.position_id
        LEFT JOIN public.department d ON d.department_id = e.department_id
        LEFT JOIN public.employee_module_access ema
            ON ema.auth_user_id = a.id AND ema.module_code = %s
        WHERE LOWER(TRIM(a.email)) = %s
        ORDER BY (e.is_active IS TRUE) DESC, (e.department_id = %s) DESC, e.employee_id DESC NULLS LAST
        LIMIT 1;
    """

    unprovisioned_emp_query = """
        SELECT
            e.employee_id,
            e.name,
            e.last_name,
            e.email,
            e.phone,
            e.department_id,
            d.department_name,
            e.position_id,
            p.position_name,
            e.is_active,
            u.user_id,
            COALESCE(ea.auth_user_id, u.auth_user_id) AS existing_auth_user_id
        FROM public.employee e
        LEFT JOIN public.position p ON p.position_id = e.position_id
        LEFT JOIN public.department d ON d.department_id = e.department_id
        LEFT JOIN public.users u ON u.employee_id = e.employee_id
        LEFT JOIN public.employee_auth ea ON ea.employee_id = e.employee_id
        WHERE LOWER(TRIM(e.email)) = %s
          AND e.is_active = TRUE
        ORDER BY (e.department_id = %s) DESC, e.employee_id DESC
        LIMIT 1;
    """

    try:
        with openTransaction() as conn:
            with conn.cursor() as cur:
                cur.execute(auth_query, (password, PRODUCTION_MODULE_CODE, cleaned_email, PRODUCTION_DEPARTMENT_ID))
                record = cur.fetchone()

                if record:
                    if not record["password_matches"]:
                        return None, "Invalid email or password."
                    if not record.get("employee_id") or not record.get("is_active"):
                        return None, "Your account has been disabled. Please contact hr suppot."
                    if not is_authorized_production_employee(
                        record.get("department_id"),
                        record.get("position_id"),
                        record.get("is_active")
                    ):
                        return None, "[403] Forbidden Access."
                    if record.get("module_active") is False:
                        return None, "Your account has been disabled. Please contact hr support."
                    access_lvl = _sync_employee_auth_links(
                        cur,
                        record["employee_id"],
                        record["auth_user_id"],
                        record["position_id"],
                    )
                    record["access_level"] = access_lvl
                    return record, None

                cur.execute(unprovisioned_emp_query, (cleaned_email, PRODUCTION_DEPARTMENT_ID))
                emp_record = cur.fetchone()

                if emp_record and not emp_record.get("existing_auth_user_id") and password == "velmora123":
                    if not is_authorized_production_employee(
                        emp_record.get("department_id"),
                        emp_record.get("position_id"),
                        emp_record.get("is_active")
                    ):
                        return None, "[403] Forbidden Access."
                    new_auth_uid = str(uuid.uuid4())
                    app_meta = json.dumps({"provider": "email", "providers": ["email"]})
                    user_meta = json.dumps({"email_verified": True})
                    cur.execute(
                        """
                        INSERT INTO auth.users (
                            instance_id, id, aud, role, email, encrypted_password,
                            email_confirmed_at, confirmation_token, recovery_token,
                            email_change_token_new, email_change, raw_app_meta_data,
                            raw_user_meta_data, created_at, updated_at, phone_change,
                            phone_change_token, email_change_token_current,
                            email_change_confirm_status, reauthentication_token,
                            is_sso_user, is_anonymous
                        ) VALUES (
                            '00000000-0000-0000-0000-000000000000', %s, 'authenticated', 'authenticated', %s,
                            extensions.crypt(%s, extensions.gen_salt('bf')),
                            NOW() - INTERVAL '31 days', '', '', '', '',
                            %s::jsonb, %s::jsonb,
                            NOW() - INTERVAL '31 days', NOW() - INTERVAL '31 days',
                            '', '', '', 0, '', FALSE, FALSE
                        )
                        """,
                        (new_auth_uid, cleaned_email, password, app_meta, user_meta),
                    )
                    access_lvl = _sync_employee_auth_links(
                        cur,
                        emp_record["employee_id"],
                        new_auth_uid,
                        emp_record["position_id"],
                    )
                    emp_record["auth_user_id"] = new_auth_uid
                    emp_record["access_level"] = access_lvl
                    emp_record["password_matches"] = True
                    return emp_record, None

        return None, "Invalid email or password."
    except Exception as err:
        return None, f"DB error during authentication: {str(err)}"


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
                        SELECT e.employee_id, e.name, e.last_name, e.email, e.phone,
                               e.department_id, e.position_id, e.is_active, p.position_name,
                               COALESCE(ea.auth_user_id, u.auth_user_id) AS auth_user_id,
                               ema.access_level, ema.is_active AS module_active
                        FROM public.employee e
                        LEFT JOIN public.position p ON p.position_id = e.position_id
                        LEFT JOIN public.employee_auth ea ON ea.employee_id = e.employee_id AND ea.is_active = TRUE
                        LEFT JOIN public.users u ON u.employee_id = e.employee_id
                        LEFT JOIN public.employee_module_access ema
                            ON ema.auth_user_id = COALESCE(ea.auth_user_id, u.auth_user_id)
                           AND ema.module_code = %s
                        WHERE e.employee_id = %s
                        LIMIT 1
                        """,
                        (PRODUCTION_MODULE_CODE, int(emp_id))
                    )
                    row = cur.fetchone()

                if not row and session.get("email"):
                    cur.execute(
                        """
                        SELECT e.employee_id, e.name, e.last_name, e.email, e.phone,
                               e.department_id, e.position_id, e.is_active, p.position_name,
                               COALESCE(ea.auth_user_id, u.auth_user_id) AS auth_user_id,
                               ema.access_level, ema.is_active AS module_active
                        FROM public.employee e
                        LEFT JOIN public.position p ON p.position_id = e.position_id
                        LEFT JOIN public.employee_auth ea ON ea.employee_id = e.employee_id AND ea.is_active = TRUE
                        LEFT JOIN public.users u ON u.employee_id = e.employee_id
                        LEFT JOIN public.employee_module_access ema
                            ON ema.auth_user_id = COALESCE(ea.auth_user_id, u.auth_user_id)
                           AND ema.module_code = %s
                        WHERE LOWER(TRIM(e.email)) = LOWER(TRIM(%s))
                        ORDER BY (e.is_active IS TRUE) DESC, (e.department_id = %s) DESC, e.employee_id DESC
                        LIMIT 1
                        """,
                        (PRODUCTION_MODULE_CODE, session.get("email"), PRODUCTION_DEPARTMENT_ID)
                    )
                    row = cur.fetchone()

                if not row and session.get("user_id") and str(session.get("user_id")).isdigit():
                    uid = int(session.get("user_id"))
                    cur.execute(
                        """
                        SELECT e.employee_id, e.name, e.last_name, e.email, e.phone,
                               e.department_id, e.position_id, e.is_active, p.position_name,
                               COALESCE(ea.auth_user_id, u.auth_user_id) AS auth_user_id,
                               ema.access_level, ema.is_active AS module_active
                        FROM public.users u
                        JOIN public.employee e ON e.employee_id = u.employee_id
                        LEFT JOIN public.position p ON p.position_id = e.position_id
                        LEFT JOIN public.employee_auth ea ON ea.employee_id = e.employee_id AND ea.is_active = TRUE
                        LEFT JOIN public.employee_module_access ema
                            ON ema.auth_user_id = COALESCE(ea.auth_user_id, u.auth_user_id)
                           AND ema.module_code = %s
                        WHERE u.user_id = %s
                        LIMIT 1
                        """,
                        (PRODUCTION_MODULE_CODE, uid)
                    )
                    row = cur.fetchone()

                if (
                    not row
                    or row.get("module_active") is False
                    or not is_authorized_production_employee(
                        row.get("department_id"),
                        row.get("position_id"),
                        row.get("is_active")
                    )
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
                session["first_name"] = (row.get("name") or "").strip()
                session["last_name"] = (row.get("last_name") or "").strip()
                session["phone"] = (row.get("phone") or "").strip()
                if row.get("auth_user_id"):
                    session["auth_user_id"] = str(row["auth_user_id"])
                session["access_level"] = row.get("access_level") or (
                    "manager" if int(row["position_id"]) == MANAGER_POSITION_ID else "staff"
                )
                full_name = f"{session['first_name']} {session['last_name']}".strip()
                if full_name:
                    session["employee_name"] = full_name
                _empVerifyTimestamps[resolved_emp_id] = now_ts
                return True
    except Exception:
        if emp_id and dept_id and pos_id:
            return is_authorized_production_employee(dept_id, pos_id, True)
        return False


def update_employee_profile(employee_id, first_name, last_name, phone):
    if not employee_id:
        return None, "Employee session is invalid."
    clean_first = (first_name or "").strip()
    clean_last = (last_name or "").strip()
    clean_phone = (phone or "").strip()

    if not clean_first or not clean_last:
        return None, "First Name and Last Name are required."
    if len(clean_first) > 60 or len(clean_last) > 60:
        return None, "Name fields must not exceed 60 characters."
    if clean_phone and (len(clean_phone) > 25 or not re.match(r"^[0-9+\-\s()]{7,25}$", clean_phone)):
        return None, "Please enter a valid phone number (7 to 25 digits)."

    try:
        with openTransaction() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE public.employee
                    SET name = %s,
                        last_name = %s,
                        phone = %s
                    WHERE employee_id = %s
                    RETURNING employee_id, name, last_name, email, phone
                    """,
                    (clean_first, clean_last, clean_phone or None, int(employee_id)),
                )
                updated = cur.fetchone()
                if not updated:
                    return None, "Employee record not found."
        clear_employee_verify_cache(employee_id)
        return updated, None
    except Exception as err:
        return None, f"Failed to update profile: {str(err)}"


def change_employee_password(employee_id, current_password, new_password):
    if not employee_id:
        return False, "Employee session is invalid."
    if not current_password or not new_password:
        return False, "Current password and new password are required."
    if len(new_password) < 8:
        return False, "New password must be at least 8 characters long."
    if current_password == new_password:
        return False, "New password must be different from your current password."

    try:
        with openTransaction() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        a.id AS auth_user_id,
                        (a.encrypted_password = extensions.crypt(%s, a.encrypted_password)) AS current_matches,
                        (a.updated_at > a.created_at + INTERVAL '1 minute') AS has_changed_before,
                        EXTRACT(EPOCH FROM (NOW() - a.updated_at)) AS seconds_since_update
                    FROM public.employee e
                    LEFT JOIN public.employee_auth ea ON ea.employee_id = e.employee_id AND ea.is_active = TRUE
                    LEFT JOIN public.users u ON u.employee_id = e.employee_id
                    JOIN auth.users a
                        ON a.id = COALESCE(ea.auth_user_id, u.auth_user_id)
                        OR LOWER(TRIM(a.email)) = LOWER(TRIM(e.email))
                    WHERE e.employee_id = %s
                    LIMIT 1
                    """,
                    (current_password, int(employee_id)),
                )
                row = cur.fetchone()
                if not row or not row.get("auth_user_id"):
                    return False, "Authentication account is not linked for this employee."
                if not row.get("current_matches"):
                    return False, "Current password is incorrect."

                cooldown_seconds = 30 * 86400
                seconds_since = float(row.get("seconds_since_update") or 0)
                if row.get("has_changed_before") and seconds_since < cooldown_seconds:
                    remaining_days = max(1, int((cooldown_seconds - seconds_since + 86399) // 86400))
                    return False, f"Password can only be changed once every 30 days. Please wait {remaining_days} more day(s)."

                cur.execute(
                    """
                    UPDATE auth.users
                    SET encrypted_password = extensions.crypt(%s, extensions.gen_salt('bf')),
                        updated_at = NOW()
                    WHERE id = %s
                    """,
                    (new_password, row["auth_user_id"]),
                )
        clear_employee_verify_cache(employee_id)
        return True, None
    except Exception as err:
        return False, f"Failed to change password: {str(err)}"


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
            flash("[403] Forbidden Access.", "danger")
            return redirect(url_for("production.index"))
        return f(*args, **kwargs)
    return decorated_function


def get_current_user():
    if not session.get("user_id"):
        return None
    return {
        "user_id": session.get("user_id"),
        "auth_user_id": session.get("auth_user_id"),
        "employee_id": session.get("employee_id"),
        "email": session.get("email"),
        "first_name": session.get("first_name"),
        "last_name": session.get("last_name"),
        "phone": session.get("phone"),
        "employee_name": session.get("employee_name"),
        "department_id": session.get("department_id"),
        "position_id": session.get("position_id"),
        "position": session.get("position"),
        "access_level": session.get("access_level"),
        "is_manager": is_manager_session()
    }
