from django.db import transaction
from django.db.models import Q
from django.http import HttpRequest, HttpResponse
from ninja import Router
from ninja.errors import HttpError
from domovoy.apps.dmv_user.api.v1.schemas import (
    ActiveSessionResponse,
    UserRegistrationRequest,
    CreateSessionRequest,
    FactorPassword,
    FactorEmailCode,
)
from domovoy.security.hashcash import (
    Hashcash,
    get_hashcash_config,
    HashcashConfig,
)

from django.contrib.auth import get_user_model, login
from pydantic import EmailStr

from domovoy.security.session_key import SessionHeader

users_v1_router = Router(tags=["Users"])
User = get_user_model()


@users_v1_router.get(
    "session", auth=[SessionHeader()], response={200: ActiveSessionResponse}
)
def active_user(request: HttpRequest):
    session_expiration_time = request.session.get_expiry_date()

    return ActiveSessionResponse(
        id=request.user.id,
        username=request.user.username,
        email=request.user.email,
        name_short=request.user.name_short,
        name_full=request.user.name_full,
        session_expires=session_expiration_time,
    )


@users_v1_router.post("email_code", auth=[Hashcash()], response={200: None})
def send_email_code(request: HttpRequest, email: EmailStr):
    allowed_subject = request.auth
    if email != allowed_subject:
        raise HttpError(401, "Hashcash subject must match requested email")
    try:
        user = User.objects.get(Q(username=email) | Q(email=email))
    except User.DoesNotExist as exc:
        raise HttpError(401, "Unauthorized") from exc

    user.send_email_code()


@users_v1_router.post("session", response={200: str})
def create_session(
    request: HttpRequest, body: CreateSessionRequest, response: HttpResponse
):
    try:
        user = User.objects.get(Q(username=body.email) | Q(email=body.email))
    except User.DoesNotExist as exc:
        raise HttpError(401, "Unauthorized") from exc

    verified_factors = set()
    for factor in body.factors:
        if isinstance(factor, FactorPassword):
            if user.check_password(factor.password):
                verified_factors.add(factor.factor_type)
            else:
                raise HttpError(401, "Unauthorized")
        if isinstance(factor, FactorEmailCode):
            if user.verify_email_code(factor.email_code):
                verified_factors.add(factor.factor_type)
            else:
                raise HttpError(401, "Unauthorized")

    required_factors = 1
    if len(verified_factors) < required_factors:
        raise HttpError(401, "Unauthorized")

    user.refresh_from_db()
    if not user.email_verified:
        raise HttpError(401, "Unauthorized")

    if not request.session.session_key:
        request.session.create()

    login(request, user)
    request.session.save()
    response["x-session-key"] = request.session.session_key
    return request.session.session_key


@users_v1_router.delete("session", auth=[SessionHeader()], response={200: None})
def logout(request: HttpRequest):
    session = SessionHeader().SessionStore(
        session_key=request.headers.get("X-Session-Key")
    )
    session.delete()


@users_v1_router.post("new", auth=[Hashcash()], response={200: None})
def register(request: HttpRequest, body: UserRegistrationRequest):
    allowed_subject = request.auth
    if body.email != allowed_subject:
        raise HttpError(401, "Hashcash subject must match requested email")

    with_username = User.objects.filter(username=body.username)
    with_email = User.objects.filter(email=body.email)
    if with_username.exists():
        raise HttpError(400, "Username already in use")
    if with_email.exists():
        raise HttpError(400, "Email already in use")

    with transaction.atomic():
        new_user = User(
            username=body.username,
            email=body.email,
            name_short=body.name_short,
            name_full=body.name_full,
        )
        new_user.save()
        new_user.set_password(body.password)
        new_user.save()
        new_user.send_email_code()


@users_v1_router.get("hashcash", auth=None, response={200: HashcashConfig})
def hashcash_config(request: HttpRequest) -> HashcashConfig:
    return get_hashcash_config()
