from typing import Optional

from ninja import ModelSchema, Schema

from domovoy.apps.regular_job.models import RegularJobDefinition, CriticalityLevel, RegularJobInstance
from pydantic import constr

from domovoy.apps.regular_job.rules import Ruleset, RuleComputeResult
from domovoy.apps.regular_job.stats import HomeStatistics


class ClaimResponse(Schema):
    value: int
    statistics: HomeStatistics
    result: Optional[RuleComputeResult]


class RegularJobInstanceSchema(ModelSchema):
    class Config:
        model = RegularJobInstance
        model_fields = [
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

    class Config:
        model = RegularJobDefinition
        model_fields = [
            "id",
            "home",
            "name",
            "description",
            "open_for_days",
            "criticality",
            "rules",
            "value_min",
            "value_max",
            "value_default",
            "next_assigned_to",
            "next_assigned_date",
            "next_assigned_start_date",
            "next_assigned_due_date",
        ]


class RegularJobDefinitionEditSchema(Schema):
    name: Optional[str]
    description: Optional[str]
    open_for_days: Optional[int]
    criticality: Optional[CriticalityLevel]
    rules: Optional[Ruleset]
    value_min: Optional[int]
    value_max: Optional[int]
    value_default: Optional[int]


class CreateRegularJobDefinitionRequest(Schema):
    name: constr(min_length=5, max_length=100)
    description: constr(max_length=1000)
    value_max: int
    value_min: int
    value_default: int


class CreateRegularJobInstanceRequest(Schema):
    value: Optional[int] = None


class RegularJobDefinitionEditSchema(Schema):
    name: Optional[str] = None
    description: Optional[str] = None
    open_for_days: Optional[int] = None
    criticality: Optional[CriticalityLevel] = None
    rules: Optional[Ruleset] = None
    value_min: Optional[int] = None
    value_max: Optional[int] = None
    value_default: Optional[int] = None
