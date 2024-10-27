from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

from domovoy.apps.regular_job.rules import generate_dates

User = get_user_model()


class Home(models.Model):
    name = models.CharField(max_length=128, unique=True)
    description = models.TextField(blank=True, null=True)
    members = models.ManyToManyField(to=User, through="Membership")

    base_score = models.PositiveIntegerField(default=0)

    d6_cost = models.PositiveSmallIntegerField(default=60)
    d6_min = models.PositiveSmallIntegerField(default=1)
    d6_max = models.PositiveSmallIntegerField(default=6)

    # bonus = job_value * (days_overdue / open_for_days) * (overdue_bounty / 100)
    overdue_bounty = models.PositiveSmallIntegerField(default=50)

    def __str__(self):
        return self.name


class Membership(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="memberships")
    home = models.ForeignKey(Home, on_delete=models.CASCADE, related_name="memberships")
    score = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.user} in {self.home}"

    def filter_available_dates(self, candidate_dates):
        holidays = None
        for candidate in candidate_dates:
            if holidays is None:
                holidays = self.holiday_set.filter(to_date__gte=candidate)
            valid = True
            for holiday in holidays:
                if holiday.from_date.date() <= candidate <= holiday.to_date.date():
                    valid = False
            if valid:
                yield candidate


class Holiday(models.Model):
    membership = models.ForeignKey(to=Membership, on_delete=models.CASCADE)
    note = models.CharField(max_length=256)
    from_date = models.DateTimeField()
    to_date = models.DateTimeField()
