from datetime import datetime, date, timezone, timedelta

try:
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
except ImportError:
    ZoneInfo = None
    ZoneInfoNotFoundError = Exception


def _resolveManilaTz():
    """Return the Asia/Manila timezone, falling back to fixed UTC+8."""
    if ZoneInfo is not None:
        try:
            return ZoneInfo("Asia/Manila")
        except ZoneInfoNotFoundError:
            pass
    return timezone(timedelta(hours=8))


MANILA_TZ = _resolveManilaTz()


def manilaNow():
    """Return the current timezone-aware datetime in Asia/Manila."""
    return datetime.now(MANILA_TZ)


def manilaToday():
    """Return today's calendar date in Asia/Manila."""
    return manilaNow().date()


def parseTemporal(val):
    """Normalize a date, datetime, or ISO string into a Manila datetime or date."""
    if not val:
        return None
    if isinstance(val, datetime):
        if val.tzinfo is None:
            return val.replace(tzinfo=MANILA_TZ)
        return val.astimezone(MANILA_TZ)
    if isinstance(val, date):
        return val
    if isinstance(val, str):
        s = val.strip()
        if not s:
            return None
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        try:
            if len(s) > 10 or "T" in s or " " in s or ":" in s:
                dt = datetime.fromisoformat(s)
                if dt.tzinfo is None:
                    return dt.replace(tzinfo=MANILA_TZ)
                return dt.astimezone(MANILA_TZ)
            return date.fromisoformat(s)
        except ValueError:
            return None
    return None


def toManilaDatetime(val, fallback=None):
    """Convert any date/datetime value into a timezone-aware Asia/Manila datetime."""
    parsed = parseTemporal(val)
    if isinstance(parsed, datetime):
        return parsed
    if isinstance(parsed, date):
        return datetime(parsed.year, parsed.month, parsed.day, tzinfo=MANILA_TZ)
    return fallback


def toManilaDate(val, fallback=None):
    """Convert any date/datetime value into a calendar date in Asia/Manila."""
    parsed = parseTemporal(val)
    if isinstance(parsed, datetime):
        return parsed.date()
    if isinstance(parsed, date):
        return parsed
    return fallback


def toManilaIsoDate(val):
    """Return YYYY-MM-DD in Asia/Manila for client-side date filters."""
    d = toManilaDate(val)
    return d.isoformat() if d else ""


def hasManilaTime(dt):
    """Return True when dt carries a non-midnight time component in Asia/Manila."""
    return isinstance(dt, datetime) and (
        dt.hour != 0 or dt.minute != 0 or dt.second != 0 or dt.microsecond != 0
    )


def formatTime12h(dt):
    """Format a datetime's wall-clock time as 12-hour AM/PM without leading zero."""
    return dt.strftime("%I:%M %p").lstrip("0")


def formatManilaDateOnly(val, fallback="-", includeYear=True):
    """Format a planning or calendar date strictly without a time component."""
    d = toManilaDate(val)
    if d is None:
        return fallback if (val is None or val == "") else str(val)
    dateFmt = "%b. %d, %Y" if includeYear else "%b. %d"
    return d.strftime(dateFmt)


def formatManilaDateTime(val, fallback="-", includeYear=True, sep=" · "):
    """Format a timestamp in Asia/Manila, appending time when non-midnight."""
    parsed = parseTemporal(val)
    if parsed is None:
        return fallback if (val is None or val == "") else str(val)
    dateFmt = "%b. %d, %Y" if includeYear else "%b. %d"
    datePart = parsed.strftime(dateFmt)
    if hasManilaTime(parsed):
        return f"{datePart}{sep}{formatTime12h(parsed)}"
    return datePart
