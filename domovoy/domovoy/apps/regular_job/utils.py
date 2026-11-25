from datetime import datetime, date, time, timezone as dt_timezone
from zoneinfo import ZoneInfo

from django.utils import timezone


def before_midnight(input_date: datetime | date, timezone_str: str = "Europe/London") -> datetime:
    """23:59 on `input_date`'s day in `timezone_str`, as a UTC datetime.

    A date or naive datetime is taken as already local to `timezone_str`; an
    aware datetime is converted to it first. The UTC offset is the one in force
    at 23:59, so days when the clocks change come out right.
    """
    local_tz = ZoneInfo(timezone_str)
    if isinstance(input_date, datetime):
        if timezone.is_aware(input_date):
            input_date = input_date.astimezone(local_tz)
        input_date = input_date.date()
    deadline = datetime.combine(input_date, time(23, 59), tzinfo=local_tz)
    return deadline.astimezone(dt_timezone.utc)
