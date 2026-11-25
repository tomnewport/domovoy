from datetime import datetime, timedelta, timezone as dt_timezone

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
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
from domovoy.apps.regular_job.utils import before_midnight

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


class AssignmentRegressionTests(TestCase):
    """Bugs fixed in #13 (and two found alongside them)."""

    @classmethod
    def setUpTestData(cls):
        cls.alice, cls.bob = (
            User.objects.create_user(
                username=f"{name}@example.com",
                email=f"{name}@example.com",
                name_short=name.title(),
                name_full=name.title(),
                email_verified=True,
            )
            for name in ("alice", "bob")
        )
        cls.home = Home.objects.create(name="Home")
        for user in (cls.alice, cls.bob):
            Membership.objects.create(user=user, home=cls.home)

    def make_job(self, name="Bins", rules=(RuleDelay(weeks=1),), **kwargs):
        return RegularJobDefinition.objects.create(
            home=self.home,
            name=name,
            value_max=10,
            value_min=1,
            value_default=5,
            rules=Ruleset(rules=list(rules)).model_dump(mode="json"),
            **kwargs,
        )

    def list_definitions(self, query=""):
        login = Client()
        login.force_login(self.alice)
        response = Client().get(
            f"/api/regular_jobs/v1/definitions{query}",
            HTTP_X_SESSION_KEY=login.session.session_key,
        )
        self.assertEqual(response.status_code, 200, response.content[:500])
        return sorted(job["name"] for job in response.json())

    def test_assignee_filter(self):
        self.make_job("Alice's", next_assigned_to=self.alice)
        self.make_job("Bob's", next_assigned_to=self.bob)
        self.make_job("Nobody's")

        self.assertEqual(self.list_definitions(), ["Alice's", "Bob's", "Nobody's"])
        self.assertEqual(self.list_definitions("?assignee=*"), ["Alice's", "Bob's"])
        self.assertEqual(self.list_definitions(f"?assignee={self.bob.id}"), ["Bob's"])

    def test_snooze_skips_count_from_the_due_date(self):
        due = timezone.now().date() + timedelta(days=3)
        job = self.make_job(next_assigned_due_date=before_midnight(due))
        job.refresh_from_db()
        due = job.next_assigned_due_date.date()

        skips = [o for o in job.snooze_options() if o.label.startswith("Skip")]

        self.assertEqual([o.label for o in skips], [f"Skip +{i}" for i in range(1, 8)])
        self.assertEqual(
            [o.date for o in skips], [due + timedelta(weeks=i) for i in range(1, 8)]
        )

    def test_snooze_options_without_rules_or_due_date(self):
        no_rules = self.make_job(
            rules=(), next_assigned_due_date=before_midnight(timezone.now().date())
        )
        self.assertEqual(no_rules.snooze_options(), [])
        self.assertEqual(self.make_job().snooze_options(), [])

    def test_adjust_keeps_the_current_assignee(self):
        job = self.make_job(next_assigned_to=self.bob)
        for _ in range(10):
            job.adjust()
            self.assertEqual(job.next_assigned_to, self.bob)
        rolls = {p["user_id"]: p["rolls"] for p in job.assignment_notes["participants"]}
        self.assertEqual(rolls[self.bob.id], [0])
        self.assertTrue(all(1 <= r <= 6 for r in rolls[self.alice.id]))

    def test_adjust_assigns_a_new_job(self):
        job = self.make_job()
        job.adjust()
        self.assertIn(job.next_assigned_to, (self.alice, self.bob))
