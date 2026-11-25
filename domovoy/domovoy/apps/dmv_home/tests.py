from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from domovoy.apps.dmv_home.models import Holiday, Home, Membership
from domovoy.testing import ApiClient, make_user


class HomeApiPermissionTests(TestCase):
    """A member only ever sees and changes their own homes and holidays."""

    @classmethod
    def setUpTestData(cls):
        cls.alice, cls.bob = make_user("alice"), make_user("bob")
        cls.home_a = Home.objects.create(name="Alice's home")
        cls.home_b = Home.objects.create(name="Bob's home")
        cls.alice_m = Membership.objects.create(user=cls.alice, home=cls.home_a)
        cls.bob_m = Membership.objects.create(user=cls.bob, home=cls.home_b)
        now = timezone.now()
        cls.bobs_holiday = Holiday.objects.create(
            membership=cls.bob_m, note="Bob away", from_date=now, to_date=now + timedelta(days=3)
        )

    def setUp(self):
        self.api = ApiClient(self.alice)

    def holiday(self, home, days_from, days_to):
        now = timezone.now()
        return self.api.post_json(
            "/api/homes/v1/holidays/",
            {
                "home_id": home.id,
                "note": "Away",
                "from_date": (now + timedelta(days=days_from)).isoformat(),
                "to_date": (now + timedelta(days=days_to)).isoformat(),
            },
        )

    def test_list_only_shows_own_homes(self):
        names = [h["name"] for h in self.api.get("/api/homes/v1/homes").json()]
        self.assertEqual(names, ["Alice's home"])

    def test_edit_own_home_but_not_anothers(self):
        own = self.api.patch_json(f"/api/homes/v1/homes/{self.home_a.id}", {"name": "Renamed"})
        other = self.api.patch_json(f"/api/homes/v1/homes/{self.home_b.id}", {"name": "Mine now"})
        self.assertEqual((own.status_code, other.status_code), (200, 403))
        self.home_a.refresh_from_db()
        self.home_b.refresh_from_db()
        self.assertEqual((self.home_a.name, self.home_b.name), ("Renamed", "Bob's home"))

    def test_holidays_are_private(self):
        self.assertEqual(self.api.get("/api/homes/v1/holidays").json(), [])
        response = self.api.delete(f"/api/homes/v1/holidays/{self.bobs_holiday.id}")
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Holiday.objects.filter(pk=self.bobs_holiday.pk).exists())

    def test_cannot_add_a_holiday_to_another_home(self):
        self.assertEqual(self.holiday(self.home_b, 1, 2).status_code, 404)
        self.assertFalse(self.bob_m.holiday_set.exclude(pk=self.bobs_holiday.pk).exists())

    def test_finished_holidays_are_not_listed(self):
        now = timezone.now()
        for days_ago in (10, 1):  # ended 10 days ago; ends 1 day from now
            Holiday.objects.create(
                membership=self.alice_m,
                note=f"{days_ago}",
                from_date=now - timedelta(days=days_ago + 3),
                to_date=now + timedelta(days=1) if days_ago == 1 else now - timedelta(days=days_ago),
            )
        notes = [h["note"] for h in self.api.get("/api/homes/v1/holidays").json()]
        self.assertEqual(notes, ["1"])

    def test_holiday_dates_are_validated(self):
        self.assertEqual(self.holiday(self.home_a, 3, 1).status_code, 400)
        self.assertEqual(self.holiday(self.home_a, -5, -2).status_code, 400)
        self.assertEqual(self.holiday(self.home_a, 1, 2).status_code, 200)
        self.assertEqual(len(self.api.get("/api/homes/v1/holidays").json()), 1)

    def test_create_home_limits(self):
        create = lambda name: self.api.post_json(  # noqa: E731
            "/api/homes/v1/homes", {"name": name, "description": ""}
        )
        self.assertEqual(create("Bob's home").status_code, 409)
        for i in range(4):
            self.assertEqual(create(f"Home {i}").status_code, 200)
        self.assertEqual(create("One too many").status_code, 403)
        self.assertEqual(self.alice.memberships.count(), 5)


class HolidayBrowsingTests(TestCase):
    """Past holidays on request, a holiday shown through its last day, and edits."""

    @classmethod
    def setUpTestData(cls):
        cls.alice, cls.bob = make_user("alice"), make_user("bob")
        home = Home.objects.create(name="Flat")
        cls.alice_m = Membership.objects.create(user=cls.alice, home=home)
        cls.bob_m = Membership.objects.create(user=cls.bob, home=home)
        today = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        cls.past = Holiday.objects.create(
            membership=cls.alice_m, note="Past",
            from_date=today - timedelta(days=20), to_date=today - timedelta(days=15),
        )
        # Stored as midnight at the start of its last day, as the date picker sends it.
        cls.ends_today = Holiday.objects.create(
            membership=cls.alice_m, note="Ends today",
            from_date=today - timedelta(days=2), to_date=today,
        )
        cls.bobs = Holiday.objects.create(
            membership=cls.bob_m, note="Bob's",
            from_date=today + timedelta(days=1), to_date=today + timedelta(days=2),
        )

    def setUp(self):
        self.api = ApiClient(self.alice)

    def notes(self, query=""):
        return [h["note"] for h in self.api.get(f"/api/homes/v1/holidays{query}").json()]

    def test_a_holiday_is_listed_through_its_last_day(self):
        self.assertEqual(self.notes(), ["Ends today"])

    def test_include_past(self):
        self.assertEqual(self.notes("?include_past=true"), ["Past", "Ends today"])

    def edit(self, holiday, days_from, days_to, note="Edited"):
        today = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        return self.api.patch_json(
            f"/api/homes/v1/holidays/{holiday.id}",
            {
                "note": note,
                "from_date": (today + timedelta(days=days_from)).isoformat(),
                "to_date": (today + timedelta(days=days_to)).isoformat(),
            },
        )

    def test_edit_own_holiday(self):
        response = self.edit(self.ends_today, 0, 3)
        self.assertEqual(response.status_code, 200, response.content[:300])
        self.assertEqual(response.json()["note"], "Edited")
        self.ends_today.refresh_from_db()
        self.assertEqual(self.ends_today.note, "Edited")

    def test_edits_are_validated_and_private(self):
        self.assertEqual(self.edit(self.ends_today, 3, 1).status_code, 400)
        self.assertEqual(self.edit(self.past, -20, -15).status_code, 400)
        self.assertEqual(self.edit(self.bobs, 1, 2).status_code, 404)
        self.bobs.refresh_from_db()
        self.assertEqual(self.bobs.note, "Bob's")
