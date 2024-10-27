from datetime import datetime, date, time
from django.utils import timezone
import pytz


def before_midnight(input_date: datetime | date, timezone_str: str = "Europe/London") -> datetime:
    """Returns one minute before midnight in the specified timezone, as a UTC time."""

    # Ensure input_date is a datetime object; if it's a date, add time
    if isinstance(input_date, date) and not isinstance(input_date, datetime):
        input_date = datetime.combine(input_date, time.min)

    # Get the specified timezone object
    local_tz = pytz.timezone(timezone_str)

    # If datetime is naive, localize it; if aware, convert it to the specified timezone
    if timezone.is_naive(input_date):
        local_date = local_tz.localize(input_date)
    else:
        local_date = input_date.astimezone(local_tz)

    # Set to one minute before midnight in the local timezone
    one_minute_before_midnight = local_date.replace(hour=23, minute=59, second=0, microsecond=0)

    # Convert to UTC
    utc_date = one_minute_before_midnight.astimezone(pytz.utc)

    return utc_date
