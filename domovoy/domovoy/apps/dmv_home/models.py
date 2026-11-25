from django.db import models
from django.contrib.auth import get_user_model


User = get_user_model()


class Home(models.Model):
    name = models.CharField(max_length=128, unique=True)
    description = models.TextField(blank=True, null=True)
    members = models.ManyToManyField(to=User, through="Membership")

    base_score = models.PositiveIntegerField(default=0)

    d6_cost = models.PositiveSmallIntegerField(default=60)
    d6_min = models.PositiveSmallIntegerField(default=1)
    d6_max = models.PositiveSmallIntegerField(default=6)

    # Percentage that scales the bonus for doing someone else's overdue job;
    # see RegularJobDefinition.bonus.
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
        """Yield the candidate dates that don't fall in one of this member's holidays.

        Reads `holiday_set.all()`, so prefetching `holiday_set` saves a query.
        """
        holidays = [(h.from_date.date(), h.to_date.date()) for h in self.holiday_set.all()]
        for candidate in candidate_dates:
            if not any(first <= candidate <= last for first, last in holidays):
                yield candidate


class Holiday(models.Model):
    membership = models.ForeignKey(to=Membership, on_delete=models.CASCADE)
    note = models.CharField(max_length=256)
    from_date = models.DateTimeField()
    to_date = models.DateTimeField()
