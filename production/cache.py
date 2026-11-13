import threading
import time

_lock = threading.Lock()
_CACHE = {}
DEFAULT_TTL_SECONDS = 15.0

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

def clearAllCache():
    with _lock:
        _CACHE.clear()
