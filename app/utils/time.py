from datetime import datetime, timezone, timedelta


def utcnow():
    return datetime.now(timezone.utc)


def format_iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def local_now(tz_str: str = "Asia/Ho_Chi_Minh"):
    from zoneinfo import ZoneInfo
    return datetime.now(ZoneInfo(tz_str))


def days_between(d1: datetime, d2: datetime) -> int:
    return abs((d1 - d2).days)
