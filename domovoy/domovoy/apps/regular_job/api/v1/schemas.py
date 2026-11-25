from datetime import datetime
from typing import Optional

from ninja import ModelSchema, Schema

from domovoy.apps.regular_job.models import RegularJobDefinition, CriticalityLevel, RegularJobInstance
from pydantic import constr

from domovoy.apps.regular_job.rules import Ruleset, RuleComputeResult
from domovoy.apps.regular_job.stats import HomeStatistics


class JobCompletionSchema(Schema):
    """One completed job, for activity feeds."""

    id: int
    job_id: int
    job_name: str
    home_id: int
    value: int  # points earned, including any overdue bonus
    completed_by_id: int
    completed_at: datetime
    due_at: Optional[datetime]
    on_time: Optional[bool]  # completed by the end of its due date; None if it had none


class RegularJobInstanceSchema(ModelSchema):
    class Meta:
        model = RegularJobInstance
        fields = [
            "id",
            "job",
            "value",
            "completed_by",
            "assigned_at",
            "can_start_at",
            "due_at",
            "completed_at"
        ]

class RegularJobDefinitionSchema(ModelSchema):
    rules: Ruleset
    bonus: int

    @staticmethod
    def resolve_bonus(obj):
        return obj.bonus

    class Meta:
        model = RegularJobDefinition
        fields = [
            "id",
            "home",
            "name",
            "description",
            "open_for_days",
            "criticality",
            "value_min",
            "value_max",
            "value_default",
            "next_assigned_to",
            "next_assigned_date",
            "next_assigned_start_date",
            "next_assigned_due_date",
        ]


class ClaimResponse(Schema):
    value: int
    statistics: HomeStatistics
    result: Optional[RuleComputeResult]
    # The job after the claim (next assignee and dates), so the client can
    # show it straight away instead of the occurrence just done.
    definition: RegularJobDefinitionSchema


class CreateRegularJobDefinitionRequest(Schema):
    name: constr(min_length=5, max_length=100)
    description: constr(max_length=1000)
    value_max: int
    value_min: int
    value_default: int


class CreateRegularJobInstanceRequest(Schema):
    value: Optional[int] = None
    # Which occurrence is being completed: the job's `next_assigned_date` as
    # the client last saw it. Every claim, snooze or reassignment sets a new
    # one (the due date can stay the same: a daily job done early is due
    # "tomorrow" again), so if it has changed the occurrence was already dealt
    # with and the claim is refused with 409. A repeated or retried claim
    # can't count twice. Omitted: complete whatever occurrence is current.
    assigned_at: Optional[datetime] = None


class RegularJobDefinitionEditSchema(Schema):
    name: Optional[str] = None
    description: Optional[str] = None
    open_for_days: Optional[int] = None
    criticality: Optional[CriticalityLevel] = None
    rules: Optional[Ruleset] = None
    value_min: Optional[int] = None
    value_max: Optional[int] = None
    value_default: Optional[int] = None
