import threading

_lock = threading.Lock()
_CACHE = {}

def getCached(key):
    with _lock:
        return _CACHE.get(key)

def setCached(key, value):
    with _lock:
        _CACHE[key] = value
        return value

def invalidateKeys(*keys):
    with _lock:
        for k in keys:
            _CACHE.pop(k, None)

def clearAllCache():
    with _lock:
        _CACHE.clear()
