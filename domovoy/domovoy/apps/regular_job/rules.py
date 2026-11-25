"""
Rules:

Deadline type: Hard deadline
Open for: 3 days

When
[four] [days] have passed since the job was last done
{"rule": "delay", "days": 4}

and the [day of the week] is [Wednesday]
and the [day of the week] is one of [Wednesday, Thursday, Friday]
and the [date] is [July 3rd]
and the [month] is [June 4th]
{"rule": "calendar", "query": "DDD", "match": ["Wednesday"]}
"""

import enum
from datetime import timedelta, date
from typing import Literal, Optional, Union, Annotated
from dateutil.relativedelta import relativedelta
from pydantic import BaseModel, ConfigDict, Field
from django.db import models
from django.utils import timezone


class CriticalityLevel(models.TextChoices):
    HIGH = "H", "Hard - job must be done before deadline. Priority in app."
    MEDIUM = "M", "Medium - job should be done before going away"
    LOW = "L", "Low - job can be skipped occasionally"


class CalendarQuery(enum.Enum):
    MONTH_NAME = "%B"
    WEEK_NUMBER = "%W"
    WEEKDAY_NAME = "%A"
    MONTH_AND_DAY = "%m-%d"


class RuleDelay(BaseModel):
    rule: Literal["delay:v1"] = "delay:v1"
    days: Optional[int] = None
    weeks: Optional[int] = None
    months: Optional[int] = None

    def evaluate(self, candidates):
        limit = None
        for option in candidates:
            if limit is None:
                limit = option
                if self.days:
                    limit += timedelta(days=self.days)
                if self.weeks:
                    limit += relativedelta(weeks=self.weeks)
                if self.months:
                    limit += relativedelta(months=self.months)
            if option >= limit:
                yield option


class RuleCalendar(BaseModel):
    rule: Literal["calendar:v1"] = "calendar:v1"
    query: CalendarQuery
    match: list[str]

    model_config = ConfigDict(use_enum_values=True)

    def evaluate(self, candidates):
        for option in candidates:
            if option.strftime(self.query) in self.match:
                yield option


Rule = Annotated[Union[RuleDelay, RuleCalendar], Field(discriminator="rule")]


def generate_dates(from_date: date):
    for increment in range(0, 365 * 100):
        yield from_date + timedelta(days=increment)


class Ruleset(BaseModel):
    # A plain [] default: Pydantic copies it per instance, and unlike
    # default_factory it stays in the OpenAPI schema, so the generated TS type
    # keeps `rules` required.
    rules: list[Rule] = []

    def find(self, start_date=None):
        candidates = generate_dates(start_date or timezone.now().date())
        for rule in self.rules:
            candidates = rule.evaluate(candidates)
        return candidates


class RuleComputeResultParticipant(BaseModel):
    user_id: int
    user_name: str
    score: int
    # Dice values; a single 0 means the current assignee was kept
    # (assign(preserve_member=True)).
    rolls: list[Literal[0, 1, 2, 3, 4, 5, 6]]
    tiebreak: float
    first_available: date


class RuleComputeResult(BaseModel):
    criticality: CriticalityLevel = Field(default=CriticalityLevel.LOW)
    participants: list[RuleComputeResultParticipant] = Field(default=[])  # see Ruleset.rules
    ideal_date: date = Field(default=date(1970, 1, 1))
    remark: str = Field(default="")
    assignee: int = Field(default=-1)
    selected_date: date = Field(default=date(1970, 1, 1))


class SnoozeOption(BaseModel):
    label: str
    date: date
