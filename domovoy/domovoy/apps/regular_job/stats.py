from datetime import timedelta, datetime
from typing import List, Tuple

import pydantic
from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.db.models.functions import TruncDate
from django.utils import timezone
from domovoy.apps.dmv_home.models import Home

from domovoy.apps.regular_job.models import RegularJobInstance

User = get_user_model()


class UserStatistics(pydantic.BaseModel):
    id: int
    name: str
    relative_score: int
    daily_scores: List[int]


class HomeStatistics(pydantic.BaseModel):
    base_date: datetime
    base_score: int
    self: int
    users: List[UserStatistics]
    dates: List[datetime]


def get_statistics(user: User, home: Home, days: int = 30):
    now = timezone.now().replace(minute=0, hour=0, second=0, microsecond=0)
    start_date = now - timedelta(days=days)
    completed = RegularJobInstance.objects.filter(
        job__home=home, completed_at__gte=start_date
    )
    daily_scores = (
        completed.annotate(day=TruncDate("completed_at"))
        .values("completed_by", "day")
        .annotate(total_points=Sum("value"))
        .order_by("completed_by", "day")
    )
    lookup = {}
    for entry in daily_scores:
        lookup[(entry["completed_by"], entry["day"])] = entry["total_points"]

    all_memberships = home.memberships.all().prefetch_related("user")
    dates = [(now.date() - timedelta(days=_)) for _ in range(days)][::-1]

    users_scores = sorted(
        [
            UserStatistics(
                id=membership.user.id,
                name=membership.user.name_full,
                relative_score=membership.score,
                daily_scores=[lookup.get((membership.user.id, d), 0) for d in dates],
            )
            for membership in all_memberships
        ],
        key=lambda _: -_.relative_score,
    )

    return HomeStatistics(
        base_date=now,
        base_score=home.base_score,
        users=users_scores,
        self=user.id,
        dates=[datetime.combine(_, datetime.min.time()) for _ in dates],
    )
