from datetime import datetime
from typing import Optional

from ninja import Schema, ModelSchema
from pydantic import constr

from domovoy.apps.dmv_home.models import Home, Membership, Holiday

from domovoy.apps.dmv_user.api.v1.schemas import UserSchema


class CreateHomeRequest(Schema):
    name: constr(min_length=3, max_length=100)
    description: constr(max_length=1000)


class UpdateHomeRequest(Schema):
    name: Optional[constr(min_length=3, max_length=100)] = None
    description: Optional[constr(max_length=1000)] = None


class MembershipSchema(ModelSchema):
    user: UserSchema

    class Config:
        model = Membership
        model_fields = ["score"]


class HomeSchema(ModelSchema):
    memberships: list[MembershipSchema]

    class Config:
        model = Home
        model_fields = ["id", "name", "description"]


class HomeOnlySchema(ModelSchema):
    class Config:
        model = Home
        model_fields = ["id", "name", "description"]


class MembershipWithHomeSchema(MembershipSchema):
    home: HomeOnlySchema


class HolidaySchema(ModelSchema):
    membership: MembershipWithHomeSchema

    class Config:
        model = Holiday
        model_fields = ["id", "note", "membership", "from_date", "to_date"]


class UpdateHolidaySchema(Schema):
    from_date: datetime
    to_date: datetime
    note: constr(max_length=256)


class CreateHolidaySchema(Schema):
    home_id: int
    from_date: datetime
    to_date: datetime
    note: constr(max_length=256)
