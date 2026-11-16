import threading
import time

_lock = threading.Lock()
_CACHE = {}
DEFAULT_TTL_SECONDS = 300.0

_DERIVED_KEYS = (
    "warehouse_stockouts",
    "monitoring_all",
    "issuances_all",
    "outputs_all",
    "costs_all",
    "bom_items_by_furniture",
    "staff_roster",
    "db_status_ok",
    "reports_data"
)
_DERIVED_PREFIXES = (
    "live_notifs:",
    "activity_recent:",
    "bom_by_furn:",
    "bom_items:",
    "attachments_latest:"
)

def getCached(key, ttl=DEFAULT_TTL_SECONDS):
    with _lock:
        entry = _CACHE.get(key)
        if not entry:
            return None
        storedAt, value = entry
        if ttl is not None and (time.monotonic() - storedAt) > ttl:
            _CACHE.pop(key, None)
            return None
        return value

def setCached(key, value):
    with _lock:
        _CACHE[key] = (time.monotonic(), value)
        return value

def invalidateKeys(*keys):
    with _lock:
        for k in keys:
            _CACHE.pop(k, None)
        for dk in _DERIVED_KEYS:
            _CACHE.pop(dk, None)
        if keys:
            prefixed = [ck for ck in list(_CACHE.keys()) if isinstance(ck, str) and ck.startswith(_DERIVED_PREFIXES)]
            for ck in prefixed:
                _CACHE.pop(ck, None)

def clearAllCache():
    with _lock:
        _CACHE.clear()
