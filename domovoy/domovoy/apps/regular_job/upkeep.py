"""How well a home is keeping up with its jobs.

The ideal is what the home would earn in a week if every job were done
exactly as its rules schedule it, at its default value. The actual is the
points really earned, without overdue bonuses (those reward rescuing a late
job, not extra work). Comparing the two says whether the housework is
keeping pace, whoever did it.
"""

from datetime import date, datetime, timedelta
from typing import Optional

import pydantic
from django.db.models import Count, F, Q, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone

from domovoy.apps.dmv_home.models import Home
from domovoy.apps.regular_job.models import RegularJobDefinition, RegularJobInstance
from domovoy.apps.regular_job.rules import Ruleset

# Rules are simulated over two years, so monthly and seasonal jobs average
# out and a yearly job happens at least twice.
SIMULATED_DAYS = 2 * 364


def occurrences_per_week(rules: Ruleset, start: Optional[date] = None) -> float:
    """How often the rules schedule a job, on average, if each occurrence is
    done on its due date (as the next one is then counted from it)."""
    if not rules.rules:
        return 0.0
    start = start or timezone.now().date()
    end = start + timedelta(days=SIMULATED_DAYS)

    def after(day: date) -> Optional[date]:
        # The next date the rules allow after `day`. A calendar-only rule
        # ("every Monday") matches the day itself again, so skip that.
        return next((d for d in rules.find(day) if d > day), None)

    occurrences = []
    occurrence = after(start)
    while occurrence is not None and occurrence <= end:
        occurrences.append(occurrence)
        occurrence = after(occurrence)
    if len(occurrences) < 2:
        return len(occurrences) / (SIMULATED_DAYS / 7)
    # The average gap between occurrences, which doesn't depend on where the
    # window happens to cut a monthly or yearly cycle.
    gap_days = (occurrences[-1] - occurrences[0]).days / (len(occurrences) - 1)
    return 7 / gap_days


class UpkeepJob(pydantic.BaseModel):
    id: int
    name: str
    per_week: float  # scheduled occurrences per week
    value: int  # default points per occurrence
    points_per_week: float


class HomeUpkeep(pydantic.BaseModel):
    home_id: int
    ideal_per_week: float  # sum of points_per_week over the jobs
    dates: list[datetime]  # one per day, oldest first
    daily_points: list[int]  # points earned each day, without bonuses
    daily_jobs: list[int]  # jobs completed each day
    daily_on_time: list[int]  # of those, ones that had a due date and met it
    daily_late: list[int]  # and ones completed after their due date
    jobs: list[UpkeepJob]  # largest contribution first


def get_upkeep(home: Home, days: int) -> HomeUpkeep:
    jobs = []
    for job in RegularJobDefinition.objects.filter(home=home):
        per_week = occurrences_per_week(Ruleset.model_validate(job.rules))
        if per_week:
            jobs.append(
                UpkeepJob(
                    id=job.id,
                    name=job.name,
                    per_week=per_week,
                    value=job.value_default,
                    points_per_week=per_week * job.value_default,
                )
            )
    jobs.sort(key=lambda j: -j.points_per_week)

    today = timezone.now().date()
    dates = [today - timedelta(days=n) for n in range(days)][::-1]
    start = datetime.combine(dates[0], datetime.min.time(), tzinfo=timezone.get_current_timezone())
    per_day = (
        RegularJobInstance.objects.filter(job__home=home, completed_at__gte=start)
        .annotate(day=TruncDate("completed_at"))
        .values("day")
        .annotate(
            points=Sum(F("value") - F("bonus")),
            jobs=Count("id"),
            # The same test as a completion's `on_time` in the activity feed.
            on_time=Count("id", filter=Q(due_at__isnull=False, completed_at__lte=F("due_at"))),
            late=Count("id", filter=Q(due_at__isnull=False, completed_at__gt=F("due_at"))),
        )
    )
    lookup = {row["day"]: row for row in per_day}

    def daily(field: str) -> list[int]:
        return [lookup[d][field] if d in lookup else 0 for d in dates]

    return HomeUpkeep(
        home_id=home.id,
        ideal_per_week=sum(j.points_per_week for j in jobs),
        dates=[datetime.combine(d, datetime.min.time()) for d in dates],
        daily_points=daily("points"),
        daily_jobs=daily("jobs"),
        daily_on_time=daily("on_time"),
        daily_late=daily("late"),
        jobs=jobs,
    )
