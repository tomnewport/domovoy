"""Component tests that drive the public HTTP API.

These exercise the API the way a client (the SPA) does: real requests through
the full Django/ninja stack, real sessions, real JSON. Two areas are covered:

* ``AuthAndPermissionTests`` — the public auth flow (register -> email link ->
  session) and the cross-home permission boundaries.
* ``MultiWeekSimulationTests`` — a couple of users sharing a home and completing
  recurring jobs over several simulated weeks, asserting the scoring/assignment
  invariants (score normalisation, base-score accumulation, value clamping, the
  overdue bonus) that ``RegularJobDefinition.claim``/``assign`` are responsible
  for.

Notes on the test harness:

* There is currently no public endpoint to join an *existing* home (``create_home``
  only enrols the creator), so multi-member homes are seeded via the ORM. Job
  creation, claiming, stats, etc. all go through HTTP.
* ``timezone.now`` is patched to a movable clock so "weeks" can pass between
  requests; ``SESSION_COOKIE_AGE`` is widened so the login sessions created at
  the start survive the simulated time travel.
* The assignment lottery uses ``random``; it is seeded for reproducibility and
  the tests assert *invariants* rather than which specific member is picked.
"""

import json
import random
from datetime import datetime, timedelta
from datetime import timezone as dt_timezone
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings

User = get_user_model()

PASSWORD = "Sup3rSecretPassword"


class _Clock:
    """A movable stand-in for ``timezone.now`` so tests can let time pass."""

    def __init__(self, start):
        self.current = start

    def now(self):
        return self.current

    def advance(self, **kwargs):
        self.current += timedelta(**kwargs)


class ApiMixin:
    """HTTP helpers shared across the component tests.

    Each logged-in user gets its own ``Client`` so their cookie jars don't
    collide (``login`` cycles the session key, which would otherwise evict an
    earlier user's session when two users share one client). Authenticated
    requests are routed to the matching client by session key; everything else
    falls back to ``self.client``.
    """

    def setUp(self):
        super().setUp()
        self._clients = {}

    def create_verified_user(self, email, username):
        user = User.objects.create(
            username=username,
            email=email,
            name_short=username[:16],
            name_full=f"{username} Lastname",
            email_verified=True,
        )
        user.set_password(PASSWORD)
        user.save()
        return user

    def login(self, email, password=PASSWORD):
        client = Client()
        resp = client.post(
            "/api/users/v1/session",
            data=json.dumps(
                {"email": email, "factors": [{"factor_type": "password", "password": password}]}
            ),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        key = resp.json()
        self._clients[key] = client
        return key

    # --- thin verb wrappers that attach the session key header ---------------

    def _client_for(self, key):
        return self._clients.get(key, self.client)

    @staticmethod
    def _headers(key):
        return {"x-session-key": key} if key else {}

    def get(self, path, key=None):
        return self._client_for(key).get(path, headers=self._headers(key))

    def post(self, path, body, key=None):
        return self._client_for(key).post(
            path,
            data=json.dumps(body),
            content_type="application/json",
            headers=self._headers(key),
        )

    def patch(self, path, body, key=None):
        return self._client_for(key).patch(
            path,
            data=json.dumps(body),
            content_type="application/json",
            headers=self._headers(key),
        )


class AuthAndPermissionTests(ApiMixin, TestCase):
    def test_full_registration_and_login_via_email_link(self):
        """Register through the API, 'receive' the email link, then log in with it."""
        email = "newcomer@example.com"
        body = {
            "name_short": "New",
            "name_full": "New Comer",
            "email": email,
            "username": "newcomer",
            "password": PASSWORD,
        }

        captured = []
        # Lower the hashcash difficulty so the proof-of-work solves quickly, and
        # capture the "email" so we can read the login code out of it.
        with mock.patch("domovoy.security.hashcash.HASHCASH_DIFFICULTY", 8), mock.patch(
            "domovoy.apps.dmv_user.models.send_formatted_email",
            side_effect=lambda **kwargs: captured.append(kwargs),
        ):
            from domovoy.security.hashcash import make_header

            config = self.get("/api/users/v1/hashcash").json()
            header = make_header(email, config["difficulty"], config["nonces"][0])

            register = self.client.post(
                "/api/users/v1/new",
                data=json.dumps(body),
                content_type="application/json",
                headers={"x-hashcash": header},
            )
            self.assertEqual(register.status_code, 200, register.content)

        # The login link looks like ".../auth_link/<user>/<code>"; the code is the
        # final path segment.
        code = captured[-1]["message"].strip().split("/")[-1]

        session = self.post(
            "/api/users/v1/session",
            {"email": email, "factors": [{"factor_type": "email_code", "email_code": code}]},
        )
        self.assertEqual(session.status_code, 200, session.content)
        key = session.json()

        active = self.get("/api/users/v1/session", key)
        self.assertEqual(active.status_code, 200)
        self.assertEqual(active.json()["email"], email)

    def test_login_rejects_wrong_password(self):
        self.create_verified_user("a@example.com", "aaa")
        resp = self.post(
            "/api/users/v1/session",
            {"email": "a@example.com", "factors": [{"factor_type": "password", "password": "wrong"}]},
        )
        self.assertEqual(resp.status_code, 401)

    def test_login_rejects_unverified_email(self):
        user = self.create_verified_user("b@example.com", "bbb")
        user.email_verified = False
        user.save()
        resp = self.post(
            "/api/users/v1/session",
            {"email": "b@example.com", "factors": [{"factor_type": "password", "password": PASSWORD}]},
        )
        self.assertEqual(resp.status_code, 401)

    def test_endpoints_require_authentication(self):
        self.assertEqual(self.client.get("/api/homes/v1/homes").status_code, 401)
        self.assertEqual(self.client.get("/api/regular_jobs/v1/definitions").status_code, 401)

    def test_users_cannot_reach_another_users_home_or_jobs(self):
        self.create_verified_user("owner@example.com", "owner")
        self.create_verified_user("intruder@example.com", "intruder")
        owner_key = self.login("owner@example.com")
        intruder_key = self.login("intruder@example.com")

        # Owner creates a home (and is its only member) and a job in it.
        self.assertEqual(
            self.post("/api/homes/v1/homes", {"name": "Owner House", "description": "ours"}, owner_key).status_code,
            200,
        )
        home_id = self.get("/api/homes/v1/homes", owner_key).json()[0]["id"]
        self.post(
            f"/api/regular_jobs/v1/definitions?home_id={home_id}",
            {"name": "Vacuum", "description": "the floors", "value_max": 20, "value_min": 5, "value_default": 10},
            owner_key,
        )
        job_id = self.get("/api/regular_jobs/v1/definitions", owner_key).json()[0]["id"]

        # The intruder is in no home and must not see or touch the owner's data.
        self.assertEqual(self.get("/api/homes/v1/homes", intruder_key).json(), [])
        self.assertEqual(self.get("/api/regular_jobs/v1/definitions", intruder_key).json(), [])
        self.assertEqual(
            self.get(f"/api/regular_jobs/v1/definitions/{job_id}/instances", intruder_key).status_code, 404
        )
        self.assertEqual(
            self.get(f"/api/regular_jobs/v1/definitions/{job_id}/snooze", intruder_key).status_code, 404
        )
        self.assertEqual(
            self.patch(f"/api/homes/v1/homes/{home_id}", {"name": "Hijacked"}, intruder_key).status_code, 403
        )


@override_settings(SESSION_COOKIE_AGE=60 * 60 * 24 * 400)
class MultiWeekSimulationTests(ApiMixin, TestCase):
    """Two housemates sharing a home, completing a recurring job over weeks."""

    def setUp(self):
        super().setUp()
        random.seed(20240101)
        self.clock = _Clock(datetime(2024, 1, 1, 9, 0, tzinfo=dt_timezone.utc))
        patcher = mock.patch("django.utils.timezone.now", self.clock.now)
        patcher.start()
        self.addCleanup(patcher.stop)

        from domovoy.apps.dmv_home.models import Home, Membership

        self.alice = self.create_verified_user("alice@example.com", "alice")
        self.bob = self.create_verified_user("bob@example.com", "bob")
        # No public "join home" endpoint exists, so seed the shared home directly.
        self.home = Home.objects.create(name="Shared Flat", description="shared")
        Membership.objects.create(user=self.alice, home=self.home)
        Membership.objects.create(user=self.bob, home=self.home)

        self.keys = {
            self.alice.id: self.login("alice@example.com"),
            self.bob.id: self.login("bob@example.com"),
        }

    def _create_weekly_job(self, value_default=10, value_min=5, value_max=20, open_for_days=3):
        owner_key = self.keys[self.alice.id]
        self.post(
            f"/api/regular_jobs/v1/definitions?home_id={self.home.id}",
            {
                "name": "Take out the bins",
                "description": "kerbside collection",
                "value_max": value_max,
                "value_min": value_min,
                "value_default": value_default,
            },
            owner_key,
        )
        job = self.get("/api/regular_jobs/v1/definitions", owner_key).json()[0]
        # Give it a weekly schedule + open-for window via the edit endpoint.
        edited = self.patch(
            f"/api/regular_jobs/v1/definitions/{job['id']}",
            {"open_for_days": open_for_days, "rules": {"rules": [{"rule": "delay:v1", "days": 7}]}},
            owner_key,
        )
        self.assertEqual(edited.status_code, 200, edited.content)
        return edited.json()

    def _home_scores(self):
        home = self.get("/api/homes/v1/homes", self.keys[self.alice.id]).json()[0]
        return [m["score"] for m in home["memberships"]]

    def test_recurring_job_assigns_and_scores_fairly_over_a_month(self):
        job = self._create_weekly_job()
        self.assertIsNotNone(job["next_assigned_to"], "a weekly job should be assigned on creation")

        base_scores = []
        for _ in range(4):
            self.clock.advance(days=7)
            # Whoever currently holds the job completes it on time.
            current = self.get(
                f"/api/regular_jobs/v1/definitions?home_id={self.home.id}", self.keys[self.alice.id]
            ).json()[0]
            assignee_id = current["next_assigned_to"]
            self.assertIn(assignee_id, self.keys)

            claim = self.post(
                f"/api/regular_jobs/v1/definitions/{job['id']}/instances", {}, self.keys[assignee_id]
            )
            self.assertEqual(claim.status_code, 200, claim.content)
            # On-time completion by the assignee earns exactly the default value.
            self.assertEqual(claim.json()["value"], 10)

            base_scores.append(claim.json()["statistics"]["base_score"])
            # After every claim the lowest score is renormalised to zero.
            self.assertEqual(min(self._home_scores()), 0)

        # base_score only ever absorbs the offset, so it never decreases.
        self.assertEqual(base_scores, sorted(base_scores))

        instances = self.get(
            f"/api/regular_jobs/v1/definitions/{job['id']}/instances", self.keys[self.alice.id]
        ).json()
        self.assertEqual(len(instances), 4)
        self.assertEqual(sum(i["value"] for i in instances), 40)

    def test_value_is_clamped_to_the_configured_bounds(self):
        job = self._create_weekly_job(value_default=10, value_min=5, value_max=20)
        self.clock.advance(days=7)
        assignee_id = self.get(
            f"/api/regular_jobs/v1/definitions?home_id={self.home.id}", self.keys[self.alice.id]
        ).json()[0]["next_assigned_to"]

        # Above the maximum is clamped down to value_max...
        high = self.post(
            f"/api/regular_jobs/v1/definitions/{job['id']}/instances", {"value": 999}, self.keys[assignee_id]
        )
        self.assertEqual(high.json()["value"], 20)

        # ...and below the minimum is clamped up to value_min.
        self.clock.advance(days=7)
        assignee_id = self.get(
            f"/api/regular_jobs/v1/definitions?home_id={self.home.id}", self.keys[self.alice.id]
        ).json()[0]["next_assigned_to"]
        low = self.post(
            f"/api/regular_jobs/v1/definitions/{job['id']}/instances", {"value": 1}, self.keys[assignee_id]
        )
        self.assertEqual(low.json()["value"], 5)

    def test_overdue_job_picked_up_by_the_other_member_earns_a_bonus(self):
        job = self._create_weekly_job(value_default=10, open_for_days=3)
        assignee_id = job["next_assigned_to"]
        other_id = next(uid for uid in self.keys if uid != assignee_id)

        # Let the job become badly overdue, then the *other* member rescues it.
        self.clock.advance(days=21)
        claim = self.post(
            f"/api/regular_jobs/v1/definitions/{job['id']}/instances", {}, self.keys[other_id]
        )
        self.assertEqual(claim.status_code, 200, claim.content)

        value = claim.json()["value"]
        # Default value plus a positive overdue bonus, capped at value_default * 10.
        self.assertGreater(value, 10)
        self.assertLessEqual(value, 10 + 10 * 10)

        instances = self.get(
            f"/api/regular_jobs/v1/definitions/{job['id']}/instances", self.keys[self.alice.id]
        ).json()
        self.assertEqual(len(instances), 1)
        self.assertEqual(instances[0]["completed_by"], other_id)
        self.assertEqual(instances[0]["value"], value)
