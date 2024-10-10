from typing import Union, Literal, Annotated

from ninja import Schema
from pydantic import constr, EmailStr, Field


class UserRegistrationRequest(Schema):
    name_short: constr(min_length=1, max_length=16) = Field(examples=["Herb"])
    name_full: constr(min_length=1, max_length=128) = Field(examples=["Herberto Berherbo"])
    email: EmailStr
    password: constr(
        min_length=8,
        max_length=128,
    ) = Field(examples=["Pa$$w0rd", "A good password is easy to remember"])


class FactorPassword(Schema):
    factor_type: Literal["password"]
    password: str


class FactorEmailLink(Schema):
    factor_type: Literal["email_link"]
    email_link: str


AuthenticationFactor = Annotated[
    Union[FactorPassword, FactorEmailLink],
    Field(discriminator="factor_type")]


class CreateSessionRequest(Schema):
    email: EmailStr
    factors: list[AuthenticationFactor]
