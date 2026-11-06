import os
import json
import time
import threading
from flask import request

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")
STORAGE_FILE = os.path.join(INSTANCE_DIR, "login_ratelimit.json")

ATTEMPTS_BEFORE_BLOCK = 5
BLOCK_DURATION_SECONDS = 60
BLOCKS_BEFORE_BAN = 3
BAN_DURATION_SECONDS = 86400

_lock = threading.Lock()
_ip_records = {}

def _ensure_storage_dir():
    try:
        if not os.path.exists(INSTANCE_DIR):
            os.makedirs(INSTANCE_DIR, exist_ok=True)
    except Exception:
        pass

def _load_records():
    global _ip_records
    _ensure_storage_dir()
    if not os.path.exists(STORAGE_FILE):
        _ip_records = {}
        return
    try:
        with open(STORAGE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            now = time.time()
            clean = {}
            for ip, rec in data.items():
                banned_until = rec.get("banned_until", 0)
                blocked_until = rec.get("blocked_until", 0)
                if banned_until > now or blocked_until > now or rec.get("block_count", 0) > 0:
                    clean[ip] = rec
            _ip_records = clean
    except Exception:
        _ip_records = {}

def _save_records():
    _ensure_storage_dir()
    try:
        with open(STORAGE_FILE, "w", encoding="utf-8") as f:
            json.dump(_ip_records, f, indent=2)
    except Exception:
        pass

_load_records()

def format_remaining_time(seconds_remaining):
    sec = max(0, int(round(seconds_remaining)))
    if sec <= 0:
        return "0 seconds"
    if sec < 60:
        return f"{sec} second{'s' if sec != 1 else ''}"
    minutes = sec // 60
    rem_sec = sec % 60
    if sec < 3600:
        if rem_sec > 0:
            return f"{minutes} min{'s' if minutes != 1 else ''}, {rem_sec} sec{'s' if rem_sec != 1 else ''}"
        return f"{minutes} minute{'s' if minutes != 1 else ''}"
    hours = sec // 3600
    rem_min = (sec % 3600) // 60
    if rem_min > 0:
        return f"{hours} hour{'s' if hours != 1 else ''}, {rem_min} min{'s' if rem_min != 1 else ''}"
    return f"{hours} hour{'s' if hours != 1 else ''}"

def get_client_ip():
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    cf_ip = request.headers.get("CF-Connecting-IP")
    if cf_ip:
        return cf_ip.strip()
    return (request.remote_addr or "127.0.0.1").strip()

def check_ip_security(ip=None):
    if not ip:
        ip = get_client_ip()
    now = time.time()
    with _lock:
        rec = _ip_records.get(ip)
        if not rec:
            return True, None
        banned_until = rec.get("banned_until", 0)
        if banned_until > now:
            rem = banned_until - now
            time_str = format_remaining_time(rem)
            return False, {
                "status": "banned",
                "remaining_seconds": int(rem),
                "remaining_formatted": time_str,
                "message": f"Your IP address is banned for 1 day due to repeated security blocks. Access will be restored in {time_str}."
            }
        blocked_until = rec.get("blocked_until", 0)
        if blocked_until > now:
            rem = blocked_until - now
            time_str = format_remaining_time(rem)
            block_count = rec.get("block_count", 1)
            warn = " Warning: 1 more block will trigger a 24-hour IP ban." if block_count == (BLOCKS_BEFORE_BAN - 1) else ""
            return False, {
                "status": "blocked",
                "remaining_seconds": int(rem),
                "remaining_formatted": time_str,
                "block_count": block_count,
                "blocks_max": BLOCKS_BEFORE_BAN,
                "message": f"Too many failed login attempts. You are temporarily blocked for 60 seconds ({time_str} remaining).{warn}"
            }
        return True, None

def record_failed_login(ip=None):
    if not ip:
        ip = get_client_ip()
    now = time.time()
    with _lock:
        rec = _ip_records.get(ip)
        if not rec:
            rec = {
                "failed_attempts": 0,
                "block_count": 0,
                "blocked_until": 0,
                "banned_until": 0,
                "last_attempt": now
            }
            _ip_records[ip] = rec

        if rec.get("banned_until", 0) > now:
            rem = rec["banned_until"] - now
            time_str = format_remaining_time(rem)
            return {
                "action": "banned",
                "remaining_seconds": int(rem),
                "remaining_formatted": time_str,
                "message": f"Your IP address is banned for 1 day. Access restored in {time_str}."
            }

        rec["failed_attempts"] = rec.get("failed_attempts", 0) + 1
        rec["last_attempt"] = now

        if rec["failed_attempts"] >= ATTEMPTS_BEFORE_BLOCK:
            rec["failed_attempts"] = 0
            rec["block_count"] = rec.get("block_count", 0) + 1

            if rec["block_count"] >= BLOCKS_BEFORE_BAN:
                rec["banned_until"] = now + BAN_DURATION_SECONDS
                rec["blocked_until"] = 0
                _save_records()
                time_str = format_remaining_time(BAN_DURATION_SECONDS)
                return {
                    "action": "banned",
                    "remaining_seconds": BAN_DURATION_SECONDS,
                    "remaining_formatted": time_str,
                    "message": f"Your IP address has been banned for 1 day after reaching 3 security blocks. Access will be restored in {time_str}."
                }
            else:
                rec["blocked_until"] = now + BLOCK_DURATION_SECONDS
                _save_records()
                b_count = rec["block_count"]
                warn = " Final warning before a 1-day IP ban." if b_count == (BLOCKS_BEFORE_BAN - 1) else ""
                return {
                    "action": "blocked",
                    "remaining_seconds": BLOCK_DURATION_SECONDS,
                    "remaining_formatted": "60 seconds",
                    "block_count": b_count,
                    "blocks_max": BLOCKS_BEFORE_BAN,
                    "message": f"Rate limit reached. Access temporarily blocked for 60 seconds (Block {b_count}/{BLOCKS_BEFORE_BAN}).{warn}"
                }

        attempts_left = ATTEMPTS_BEFORE_BLOCK - rec["failed_attempts"]
        _save_records()
        return {
            "action": "failed",
            "attempts_left": attempts_left,
            "message": f"Invalid email or password. ({attempts_left} attempt{'s' if attempts_left != 1 else ''} remaining before temporary block)"
        }

def record_successful_login(ip=None):
    if not ip:
        ip = get_client_ip()
    with _lock:
        rec = _ip_records.get(ip)
        if rec:
            rec["failed_attempts"] = 0
            _save_records()

