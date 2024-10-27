from datetime import datetime
from typing import Union, Literal, Annotated

from ninja import Schema
from pydantic import constr, EmailStr, Field


class UserRegistrationRequest(Schema):
    name_short: constr(min_length=1, max_length=16) = Field(examples=["Herb"])
    name_full: constr(min_length=1, max_length=128) = Field(
        examples=["Herberto Berherbo"]
    )
    email: EmailStr
    username: constr(min_length=3, max_length=32) = Field(examples=["HBerherbo"])
    password: constr(
        min_length=8,
        max_length=128,
    ) = Field(examples=["Pa$$w0rd", "A good password is easy to remember"])


class FactorPassword(Schema):
    factor_type: Literal["password"]
    password: str


class FactorEmailCode(Schema):
    factor_type: Literal["email_code"]
    email_code: str


AuthenticationFactor = Annotated[
    Union[FactorPassword, FactorEmailCode], Field(discriminator="factor_type")
]


class CreateSessionRequest(Schema):
    email: EmailStr
    factors: list[AuthenticationFactor]


class UserSchema(Schema):
    id: int
    email: str
    username: str
    name_full: str
    name_short: str


class ActiveSessionResponse(UserSchema):
    session_expires: datetime
