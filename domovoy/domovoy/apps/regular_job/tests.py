from datetime import datetime, timedelta, timezone as dt_timezone

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from domovoy.apps.dmv_home.models import Home, Membership
from domovoy.apps.regular_job.models import RegularJobDefinition, RegularJobInstance
from domovoy.apps.regular_job.rules import (
    CalendarQuery,
    RuleCalendar,
    RuleDelay,
    Ruleset,
)
from domovoy.apps.regular_job.stats import get_statistics

User = get_user_model()


class DatabaseCompatibilityTests(TestCase):
    """Behaviour that must match on SQLite and Postgres (see issue #10)."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="a@example.com", email="a@example.com", name_full="A"
        )
        cls.home = Home.objects.create(name="Home")
        Membership.objects.create(user=cls.user, home=cls.home)

    def make_job(self, **kwargs):
        return RegularJobDefinition.objects.create(
            home=self.home,
            name="Bins",
            value_max=10,
            value_min=1,
            value_default=5,
            **kwargs,
        )

    def test_json_fields_round_trip(self):
        ruleset = Ruleset(
            rules=[
                RuleDelay(weeks=1),
                RuleCalendar(query=CalendarQuery.WEEKDAY_NAME, match=["Mon"]),
            ]
        )
        job = self.make_job(rules=ruleset.model_dump(mode="json"))
        job.refresh_from_db()
        self.assertEqual(Ruleset.model_validate(job.rules), ruleset)
        self.assertIsNone(job.assignment_notes)

        # An empty dict must stay distinct from SQL NULL.
        job.assignment_notes = {}
        job.save()
        job.refresh_from_db()
        self.assertEqual(job.assignment_notes, {})

    def test_statistics_bucket_completions_by_utc_day(self):
        job = self.make_job()
        today = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday = today - timedelta(days=1)
        for completed_at, value in [
            (yesterday + timedelta(minutes=1), 2),
            (yesterday + timedelta(hours=23, minutes=59), 3),
            (today + timedelta(minutes=1), 7),
        ]:
            RegularJobInstance.objects.create(
                job=job, value=value, completed_by=self.user, completed_at=completed_at
            )

        stats = get_statistics(self.user, self.home, days=3)

        self.assertEqual(stats.users[0].daily_scores, [0, 5, 7])
        self.assertEqual(
            stats.dates[-1],
            datetime.combine(today.astimezone(dt_timezone.utc).date(), datetime.min.time()),
        )
