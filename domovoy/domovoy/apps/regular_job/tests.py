from datetime import date, datetime, timedelta, timezone as dt_timezone
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import Client, SimpleTestCase, TestCase
from django.utils import timezone

from pydantic import ValidationError

from domovoy.apps.dmv_home.models import Holiday, Home, Membership
from domovoy.apps.regular_job.models import RegularJobDefinition, RegularJobInstance
from domovoy.apps.regular_job.rules import (
    CalendarQuery,
    CriticalityLevel,
    RuleCalendar,
    RuleDelay,
    Ruleset,
)
from domovoy.apps.regular_job.stats import get_statistics
from domovoy.apps.regular_job.utils import before_midnight
from domovoy.testing import ApiClient, make_user

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


def first(dates):
    return next(iter(dates))


class RuleEngineTests(SimpleTestCase):
    """Ruleset.find(start) yields the dates a job may next be scheduled on."""

    START = date(2030, 1, 7)  # a Monday

    def find(self, *rules, start=START):
        return first(Ruleset(rules=list(rules)).find(start))

    def test_no_rules_allows_the_start_date(self):
        self.assertEqual(self.find(), self.START)

    def test_delay_in_days_weeks_and_months(self):
        self.assertEqual(self.find(RuleDelay(days=3)), date(2030, 1, 10))
        self.assertEqual(self.find(RuleDelay(weeks=2)), date(2030, 1, 21))
        self.assertEqual(self.find(RuleDelay(months=1)), date(2030, 2, 7))
        self.assertEqual(
            self.find(RuleDelay(days=1, weeks=1, months=1)), date(2030, 2, 15)
        )

    def test_month_delay_clamps_to_the_end_of_a_shorter_month(self):
        self.assertEqual(
            self.find(RuleDelay(months=1), start=date(2030, 1, 31)), date(2030, 2, 28)
        )

    def test_delay_yields_every_later_date(self):
        dates = Ruleset(rules=[RuleDelay(days=2)]).find(self.START)
        self.assertEqual(
            [next(dates) for _ in range(3)],
            [date(2030, 1, 9), date(2030, 1, 10), date(2030, 1, 11)],
        )

    def test_calendar_queries(self):
        def calendar(query, *match):
            return RuleCalendar(query=query, match=list(match))

        # The start date itself matches if it qualifies.
        self.assertEqual(self.find(calendar(CalendarQuery.WEEKDAY_NAME, "Monday")), self.START)
        self.assertEqual(
            self.find(calendar(CalendarQuery.WEEKDAY_NAME, "Saturday", "Sunday")),
            date(2030, 1, 12),
        )
        self.assertEqual(
            self.find(calendar(CalendarQuery.MONTH_NAME, "March")), date(2030, 3, 1)
        )
        self.assertEqual(
            self.find(calendar(CalendarQuery.MONTH_AND_DAY, "12-25")), date(2030, 12, 25)
        )
        self.assertEqual(
            self.find(calendar(CalendarQuery.WEEK_NUMBER, "03")), date(2030, 1, 21)
        )

    def test_rules_compose_in_order(self):
        delay = RuleDelay(weeks=1)
        friday = RuleCalendar(query=CalendarQuery.WEEKDAY_NAME, match=["Friday"])
        # A week later, then the next Friday.
        self.assertEqual(self.find(delay, friday), date(2030, 1, 18))
        # The first Friday is the 11th; a week after that.
        self.assertEqual(self.find(friday, delay), date(2030, 1, 18))
        # Order matters when the delay doesn't land on a match.
        three_days = RuleDelay(days=3)
        self.assertEqual(self.find(three_days, friday), date(2030, 1, 11))
        self.assertEqual(self.find(friday, three_days), date(2030, 1, 18))

    def test_rules_parse_from_stored_json(self):
        ruleset = Ruleset.model_validate(
            {
                "rules": [
                    {"rule": "delay:v1", "days": 2},
                    {"rule": "calendar:v1", "query": "%A", "match": ["Friday"]},
                ]
            }
        )
        self.assertIsInstance(ruleset.rules[0], RuleDelay)
        self.assertIsInstance(ruleset.rules[1], RuleCalendar)
        self.assertEqual(first(ruleset.find(self.START)), date(2030, 1, 11))

    def test_unknown_rule_is_rejected(self):
        with self.assertRaises(ValidationError):
            Ruleset.model_validate({"rules": [{"rule": "lunar:v1"}]})


@mock.patch("domovoy.apps.regular_job.models.random", return_value=0.5)
@mock.patch("domovoy.apps.regular_job.models.randrange", return_value=3)
class AssignmentTests(TestCase):
    """RegularJobDefinition.assign(), with every die rolling 3.

    With equal dice, fewer dice means a lower total, so a member's score (more
    score, more dice) decides who is picked.
    """

    D = date(2030, 1, 7)  # baseline; the weekly rule makes the ideal date D+7

    @classmethod
    def setUpTestData(cls):
        cls.home = Home.objects.create(name="Home", d6_cost=60, d6_min=1, d6_max=4)
        cls.alice, cls.bob = make_user("alice"), make_user("bob")
        cls.alice_m = Membership.objects.create(user=cls.alice, home=cls.home, score=0)
        cls.bob_m = Membership.objects.create(user=cls.bob, home=cls.home, score=180)

    def make_job(self, criticality=CriticalityLevel.LOW, rules=(RuleDelay(days=7),)):
        return RegularJobDefinition.objects.create(
            home=self.home,
            name="Bins",
            value_max=10,
            value_min=1,
            value_default=5,
            criticality=criticality,
            rules=Ruleset(rules=list(rules)).model_dump(mode="json"),
        )

    def away(self, membership, first_day, last_day):
        Holiday.objects.create(
            membership=membership,
            note="Away",
            from_date=before_midnight(self.D + timedelta(days=first_day)),
            to_date=before_midnight(self.D + timedelta(days=last_day)),
        )

    def assign(self, job):
        return job.assign(override_date=self.D)

    def day(self, n):
        return self.D + timedelta(days=n)

    def test_dice_count_follows_score(self, *_):
        carol = make_user("carol")
        Membership.objects.create(user=carol, home=self.home, score=600)
        result = self.assign(self.make_job())
        dice = {p.user_id: len(p.rolls) for p in result.participants}
        # 0 // 60 = 0 -> d6_min 1; 180 // 60 = 3; 600 // 60 = 10 -> d6_max 4
        self.assertEqual(dice, {self.alice.id: 1, self.bob.id: 3, carol.id: 4})

    def test_lowest_total_gets_the_job(self, *_):
        result = self.assign(self.make_job())
        self.assertEqual(result.ideal_date, self.day(7))
        self.assertEqual(result.assignee, self.alice.id)
        self.assertEqual(result.selected_date, self.day(7))
        self.assertEqual(result.remark, "Perfect")
        self.assertEqual([p.user_id for p in result.participants], [self.alice.id, self.bob.id])

    def test_no_rules_means_no_assignment(self, *_):
        self.assertIsNone(self.assign(self.make_job(rules=())))

    def test_low_criticality_waits_for_the_assignee(self, *_):
        self.away(self.alice_m, 5, 10)
        result = self.assign(self.make_job(CriticalityLevel.LOW))
        self.assertEqual(result.assignee, self.alice.id)
        self.assertEqual(result.selected_date, self.day(11))
        self.assertEqual(result.remark, "Job can be delayed")

    def test_medium_criticality_switches_to_someone_available(self, *_):
        self.away(self.alice_m, 5, 10)
        result = self.assign(self.make_job(CriticalityLevel.MEDIUM))
        self.assertEqual(result.assignee, self.bob.id)
        self.assertEqual(result.selected_date, self.day(7))

    def test_medium_criticality_picks_the_earliest_return(self, *_):
        self.away(self.alice_m, 5, 12)
        self.away(self.bob_m, 5, 10)
        result = self.assign(self.make_job(CriticalityLevel.MEDIUM))
        self.assertEqual(result.assignee, self.bob.id)
        self.assertEqual(result.selected_date, self.day(11))
        self.assertEqual(result.remark, "Closest available")

    def test_high_criticality_schedules_before_the_holiday(self, *_):
        self.away(self.alice_m, 5, 12)
        self.away(self.bob_m, 5, 12)
        result = self.assign(self.make_job(CriticalityLevel.HIGH))
        self.assertEqual(result.selected_date, self.day(4))
        self.assertIn(result.assignee, (self.alice.id, self.bob.id))
        self.assertEqual(result.remark, "Scheduled before holiday")

    def test_high_criticality_with_nobody_free_before_the_ideal_date(self, *_):
        self.away(self.alice_m, -1, 12)
        self.away(self.bob_m, -1, 12)
        result = self.assign(self.make_job(CriticalityLevel.HIGH))
        self.assertEqual(result.assignee, self.alice.id)
        self.assertEqual(result.selected_date, self.day(13))
        self.assertEqual(result.remark, "Failed to find a good date")


class ClaimTests(TestCase):
    """RegularJobDefinition.claim(): scoring, normalisation and reassignment."""

    @classmethod
    def setUpTestData(cls):
        cls.home = Home.objects.create(name="Home", overdue_bounty=50)
        cls.alice, cls.bob = make_user("alice"), make_user("bob")
        Membership.objects.create(user=cls.alice, home=cls.home)
        Membership.objects.create(user=cls.bob, home=cls.home)

    def make_job(self, home=None, **kwargs):
        defaults = dict(
            home=home or self.home,
            name="Bins",
            value_max=20,
            value_min=2,
            value_default=10,
            rules=Ruleset(rules=[RuleDelay(weeks=1)]).model_dump(mode="json"),
        )
        defaults.update(kwargs)
        return RegularJobDefinition.objects.create(**defaults)

    def scores(self):
        return {
            m.user_id: m.score for m in Membership.objects.filter(home=self.home)
        }

    def test_value_is_clamped_to_the_job_range(self):
        job = self.make_job()
        self.assertEqual(job.validate_value(None), 10)
        self.assertEqual(job.validate_value(1), 2)
        self.assertEqual(job.validate_value(99), 20)
        self.assertEqual(job.validate_value(7), 7)

    def test_scores_are_normalised_so_the_lowest_is_zero(self):
        job = self.make_job()
        self.assertEqual(job.claim(self.alice, 5), 5)
        self.assertEqual(self.scores(), {self.alice.id: 5, self.bob.id: 0})

        self.assertEqual(job.claim(self.bob, 12), 12)
        # bob 12, alice 5 -> subtract 5 from everyone, carried into base_score
        self.assertEqual(self.scores(), {self.alice.id: 0, self.bob.id: 7})
        self.home.refresh_from_db()
        self.assertEqual(self.home.base_score, 5)

    def test_single_member_home(self):
        home = Home.objects.create(name="Solo")
        Membership.objects.create(user=self.alice, home=home)
        job = self.make_job(home=home)
        job.claim(self.alice, 6)
        home.refresh_from_db()
        self.assertEqual(home.memberships.get().score, 0)
        self.assertEqual(home.base_score, 6)

    def test_home_without_members(self):
        home = Home.objects.create(name="Empty")
        job = self.make_job(home=home)
        job.claim(self.alice, 6)
        home.refresh_from_db()
        self.assertEqual(home.base_score, 0)
        self.assertEqual(job.instances.get().value, 6)
        self.assertIsNone(job.next_assigned_to)  # nobody to hand it to

    def overdue_job(self):
        return self.make_job(
            next_assigned_to=self.alice,
            open_for_days=2,
            next_assigned_due_date=timezone.now() - timedelta(days=4, hours=1),
        )

    def test_helping_with_an_overdue_job_earns_a_bonus(self):
        job = self.overdue_job()
        # default 10 * (4 days overdue / 2 open days) * 50% bounty = 10
        self.assertEqual(job.bonus, 10)
        self.assertEqual(job.claim(self.bob), 20)

    def test_the_assignee_gets_no_bonus(self):
        self.assertEqual(self.overdue_job().claim(self.alice), 10)

    def test_bonus_is_capped_at_ten_times_the_default(self):
        job = self.overdue_job()
        job.next_assigned_due_date = timezone.now() - timedelta(days=400)
        self.assertEqual(job.bonus, 100)

    def test_claim_records_an_instance_and_reassigns(self):
        job = self.make_job(next_assigned_to=self.alice)
        job.claim(self.bob, 4)
        instance = job.instances.get()
        self.assertEqual((instance.value, instance.completed_by), (4, self.bob))
        self.assertIsNotNone(instance.completed_at)
        job.refresh_from_db()
        self.assertIn(job.next_assigned_to, (self.alice, self.bob))
        self.assertIsNotNone(job.next_assigned_due_date)
        self.assertEqual(job.assignment_notes["assignee"], job.next_assigned_to_id)


class JobApiPermissionTests(TestCase):
    """A member only ever sees and changes their own homes' jobs."""

    @classmethod
    def setUpTestData(cls):
        cls.alice, cls.bob = make_user("alice"), make_user("bob")
        cls.home_a = Home.objects.create(name="A")
        cls.home_b = Home.objects.create(name="B")
        Membership.objects.create(user=cls.alice, home=cls.home_a)
        Membership.objects.create(user=cls.bob, home=cls.home_b)
        rules = Ruleset(rules=[RuleDelay(weeks=1)]).model_dump(mode="json")
        job = dict(value_max=10, value_min=1, value_default=5, rules=rules)
        cls.job_a = RegularJobDefinition.objects.create(home=cls.home_a, name="A's", **job)
        cls.job_b = RegularJobDefinition.objects.create(home=cls.home_b, name="B's", **job)

    def setUp(self):
        self.api = ApiClient(self.alice)

    def url(self, job, suffix=""):
        return f"/api/regular_jobs/v1/definitions/{job.id}{suffix}"

    def test_list_only_shows_own_homes(self):
        names = [j["name"] for j in self.api.get("/api/regular_jobs/v1/definitions").json()]
        self.assertEqual(names, ["A's"])

    def test_other_homes_jobs_are_not_found(self):
        b = self.job_b
        responses = {
            "instances": self.api.get(self.url(b, "/instances")),
            "claim": self.api.post_json(self.url(b, "/instances"), {"value": 3}),
            "edit": self.api.patch_json(self.url(b), {"name": "Mine now"}),
            "snooze options": self.api.get(self.url(b, "/snooze")),
            "snooze": self.api.post(self.url(b, "/snooze") + "?new_date=2030-01-01"),
        }
        self.assertEqual({k: r.status_code for k, r in responses.items()}, dict.fromkeys(responses, 404))
        b.refresh_from_db()
        self.assertEqual((b.name, b.instances.count()), ("B's", 0))

    def create_job(self, home, name):
        return self.api.post_json(
            f"/api/regular_jobs/v1/definitions?home_id={home.id}",
            {"name": name, "description": "", "value_max": 5, "value_min": 1, "value_default": 2},
        )

    def test_create_a_job_in_own_home(self):
        self.assertEqual(self.create_job(self.home_a, "Hoover").status_code, 200)
        self.assertTrue(self.home_a.regular_jobs.filter(name="Hoover").exists())

    def test_cannot_create_a_job_in_another_home(self):
        self.assertEqual(self.create_job(self.home_b, "Sneaky").status_code, 404)
        self.assertFalse(self.home_b.regular_jobs.filter(name="Sneaky").exists())

    def test_claiming_own_job(self):
        response = self.api.post_json(self.url(self.job_a, "/instances"), {"value": 3})
        self.assertEqual(response.status_code, 200, response.content[:300])
        self.assertEqual(response.json()["value"], 3)

    def test_requires_a_session(self):
        self.assertEqual(Client().get("/api/regular_jobs/v1/definitions").status_code, 401)
