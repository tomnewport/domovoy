from datetime import datetime, timedelta, timezone as dt_timezone
from unittest import mock

from django.test import SimpleTestCase

from domovoy.security import hashcash
from domovoy.security.hashcash import (
    HASHCASH_DIFFICULTY,
    Hashcash,
    get_hashcash_config,
    make_header,
    trailing_zeros,
    verify_header,
)

NOON = datetime(2030, 1, 7, 12, 0, tzinfo=dt_timezone.utc)


def at(moment):
    """Run hashcash code as if it were `moment`."""
    return mock.patch.object(hashcash.timezone, "now", return_value=moment)


class HashcashTests(SimpleTestCase):
    def stamp(self, subject="me@example.com", difficulty=HASHCASH_DIFFICULTY, nonce=None, when=NOON):
        with at(when):
            nonce = nonce or get_hashcash_config()["nonces"][0]
            return make_header(subject, difficulty, nonce)

    def verify(self, header, when=NOON):
        with at(when):
            return verify_header(header)

    def test_trailing_zeros(self):
        self.assertEqual([trailing_zeros(n) for n in (0, 1, 2, 8, 12)], [0, 0, 1, 3, 2])

    def test_a_solved_stamp_is_accepted_and_names_its_subject(self):
        header = self.stamp("me@example.com")
        self.assertEqual(self.verify(header), "me@example.com")
        self.assertGreaterEqual(trailing_zeros(hashcash.hash(header.encode())), HASHCASH_DIFFICULTY)

    def test_stamp_stays_valid_for_an_hour(self):
        header = self.stamp()
        self.assertEqual(self.verify(header, NOON + timedelta(minutes=59)), "me@example.com")

    def assertRejected(self, header, reason, when=NOON):
        with self.assertRaisesRegex(ValueError, reason):
            self.verify(header, when)

    def test_rejects_a_stale_stamp(self):
        self.assertRejected(self.stamp(), "Time does not match", NOON + timedelta(minutes=61))

    def test_rejects_a_stamp_from_the_future(self):
        self.assertRejected(self.stamp(), "Time does not match", NOON - timedelta(minutes=61))

    def test_rejects_a_wrong_version(self):
        header = self.stamp()
        self.assertRejected("9" + header[1:], "Version does not match")

    def test_rejects_a_lower_difficulty(self):
        self.assertRejected(self.stamp(difficulty=4), "Difficulty does not match")

    def test_rejects_an_unknown_nonce(self):
        self.assertRejected(self.stamp(nonce="not-a-nonce"), "Unsupported nonce")

    def test_rejects_yesterdays_nonce(self):
        yesterday = NOON - timedelta(days=1)
        with at(yesterday):
            old_nonce = get_hashcash_config()["nonces"][0]
        self.assertRejected(self.stamp(nonce=old_nonce), "Unsupported nonce")

    def test_accepts_the_previous_hours_nonce_just_after_midnight(self):
        just_after_midnight = datetime(2030, 1, 8, 0, 10, tzinfo=dt_timezone.utc)
        with at(just_after_midnight):
            nonces = get_hashcash_config()["nonces"]
        self.assertEqual(len(nonces), 2)  # today's and yesterday's
        header = self.stamp(nonce=nonces[1], when=just_after_midnight)
        self.assertEqual(self.verify(header, just_after_midnight), "me@example.com")

    def test_rejects_an_unsolved_stamp(self):
        header = self.stamp()
        prefix, counter = header.rsplit(":", 1)
        unsolved = next(
            f"{prefix}:{c}"
            for c in ("x", "y", "z", "xx", "xy")
            if trailing_zeros(hashcash.hash(f"{prefix}:{c}".encode())) < HASHCASH_DIFFICULTY
        )
        self.assertRejected(unsolved, "Hashcash not solved")

    def test_rejects_a_stamp_made_with_another_secret(self):
        with at(NOON):
            foreign_nonce = get_hashcash_config(secret="someone-else")["nonces"][0]
        self.assertRejected(self.stamp(nonce=foreign_nonce), "Unsupported nonce")

    def test_authenticate_returns_false_for_garbage(self):
        auth = Hashcash()
        for header in ("", "nonsense", "1:2:3"):
            self.assertIs(auth.authenticate(None, header), False)
