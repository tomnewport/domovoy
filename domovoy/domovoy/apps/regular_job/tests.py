"""Tests for the rules engine (``apps/regular_job/rules.py``).

This is the highest-risk, previously-untested logic in the project: the
composable ruleset that decides when a job is next due. These cover the two
rule types, their composition, and discriminated-union parsing. They use
``SimpleTestCase`` because the rules engine is pure Python and needs no DB.
"""

from datetime import date
from itertools import islice

from django.test import SimpleTestCase

from domovoy.apps.regular_job.rules import (
    CalendarQuery,
    RuleCalendar,
    RuleDelay,
    Ruleset,
    generate_dates,
)

# 2024-01-01 is a Monday, which makes the expected weekdays easy to reason about.
START = date(2024, 1, 1)


def first(iterable):
    return next(iter(iterable))


def take(iterable, n):
    return list(islice(iterable, n))


class RuleDelayTests(SimpleTestCase):
    def test_days_skips_the_delay_window(self):
        # With a 4-day delay the first eligible date is start + 4 days.
        self.assertEqual(first(RuleDelay(days=4).evaluate(generate_dates(START))), date(2024, 1, 5))

    def test_weeks(self):
        self.assertEqual(first(RuleDelay(weeks=2).evaluate(generate_dates(START))), date(2024, 1, 15))

    def test_months(self):
        self.assertEqual(first(RuleDelay(months=3).evaluate(generate_dates(START))), date(2024, 4, 1))

    def test_yields_contiguous_dates_after_the_window(self):
        self.assertEqual(
            take(RuleDelay(days=4).evaluate(generate_dates(START)), 3),
            [date(2024, 1, 5), date(2024, 1, 6), date(2024, 1, 7)],
        )


class RuleCalendarTests(SimpleTestCase):
    def test_weekday_predicate(self):
        rule = RuleCalendar(query=CalendarQuery.WEEKDAY_NAME, match=["Wednesday"])
        # First Wednesday on/after 2024-01-01 is the 3rd, then weekly.
        self.assertEqual(
            take(rule.evaluate(generate_dates(START)), 2),
            [date(2024, 1, 3), date(2024, 1, 10)],
        )

    def test_month_predicate(self):
        rule = RuleCalendar(query=CalendarQuery.MONTH_NAME, match=["January"])
        results = take(rule.evaluate(generate_dates(date(2024, 1, 29))), 3)
        self.assertEqual(results, [date(2024, 1, 29), date(2024, 1, 30), date(2024, 1, 31)])

    def test_use_enum_values_stores_the_strftime_token(self):
        rule = RuleCalendar(query=CalendarQuery.WEEKDAY_NAME, match=["Wednesday"])
        self.assertEqual(rule.query, "%A")


class RulesetTests(SimpleTestCase):
    def test_rules_compose_in_order(self):
        # Delay 4 days, then only Wednesdays: first Wednesday on/after 2024-01-05.
        ruleset = Ruleset(
            rules=[
                RuleDelay(days=4),
                RuleCalendar(query=CalendarQuery.WEEKDAY_NAME, match=["Wednesday"]),
            ]
        )
        self.assertEqual(first(ruleset.find(START)), date(2024, 1, 10))

    def test_discriminated_union_parsing(self):
        ruleset = Ruleset.model_validate(
            {
                "rules": [
                    {"rule": "delay:v1", "days": 4},
                    {"rule": "calendar:v1", "query": "%A", "match": ["Wednesday"]},
                ]
            }
        )
        self.assertIsInstance(ruleset.rules[0], RuleDelay)
        self.assertIsInstance(ruleset.rules[1], RuleCalendar)
        self.assertEqual(ruleset.rules[0].days, 4)
        self.assertEqual(ruleset.rules[1].match, ["Wednesday"])
