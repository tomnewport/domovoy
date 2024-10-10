from django.contrib.auth import login, SESSION_KEY
from django.contrib.auth.hashers import check_password
from django.core.exceptions import BadRequest
from django.http import HttpRequest, HttpResponse
from ninja import Router

from domovoy.apps.dmv_user.api.v1.schemas import UserRegistrationRequest, CreateSessionRequest, FactorPassword, FactorEmailLink
from domovoy.security.hashcash import Hashcash, get_hashcash_config, make_header, HashcashConfig

from domovoy.apps.dmv_user.models import DmvUser

users_v1_router = Router()


@users_v1_router.get("session")
def active_user(request: HttpRequest):
    pass


@users_v1_router.post("session")
def create_session(request: HttpRequest, body: CreateSessionRequest, response: HttpResponse):
    user = DmvUser.objects.get(username=body.email)

    verified_factors = set()
    for factor in body.factors:
        if isinstance(factor, FactorPassword):
            if not user.check_password(factor.password):
                return HttpResponse(status=403)
        if isinstance(factor, FactorEmailLink):
            print(factor.email_link)

    #login(request, user)
    #response["X-Session-Key"] = request.session.session_key


@users_v1_router.delete("session")
def logout(request: HttpRequest):
    pass


@users_v1_router.post("new", auth=[Hashcash()])
def register(request: HttpRequest, body: UserRegistrationRequest):
    allowed_subject = request.auth
    if body.email != allowed_subject:
        return HttpResponse({"detail": "Hashcash subject must match requested email"}, status=401)


@users_v1_router.get("hashcash", auth=None, response={200: HashcashConfig})
def hashcash_config(request: HttpRequest) -> HashcashConfig:
    return get_hashcash_config()


@users_v1_router.post("hashcash")
def hashcash_maker_dev(request: HttpRequest, subject: str):
    config = get_hashcash_config()
    return make_header(subject, config["difficulty"], config["nonces"][0])
