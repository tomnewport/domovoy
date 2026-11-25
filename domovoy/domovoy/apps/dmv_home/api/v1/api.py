from django.db import IntegrityError, transaction
from django.db.models import Manager
from django.http import HttpRequest
from django.utils import timezone
from ninja import Router
from domovoy.security.session_key import SessionHeader
from ninja.errors import HttpError
from domovoy.apps.dmv_home.models import Home, Membership, Holiday
from domovoy.apps.dmv_home.api.v1.schemas import (
    CreateHomeRequest,
    HomeSchema,
    UpdateHomeRequest,
    HolidaySchema,
    CreateHolidaySchema,
    UpdateHolidaySchema,
)

homes_v1_router = Router(tags=["Homes"], auth=[SessionHeader()])


def get_user_memberships(request: HttpRequest) -> Membership.objects.none():
    user = request.user
    if not user.is_authenticated:
        return (
            Membership.objects.none()
        )  # Return an empty queryset if not authenticated

    return user.memberships.prefetch_related("home", "user")


@homes_v1_router.post("homes")
def create_home(request: HttpRequest, data: CreateHomeRequest):
    memberships = get_user_memberships(request)
    if len(memberships) >= 5:
        raise HttpError(403, "Maximum number of memberships reached")

    try:
        # The home and its first membership are created together or not at all.
        with transaction.atomic():
            new_home = Home(name=data.name, description=data.description)
            new_home.save()
            new_membership = Membership(
                user=request.user,
                home=new_home,
            )
            new_membership.save()
    except IntegrityError:
        raise HttpError(409, "Home with that name already exists")


@homes_v1_router.get("homes", response={200: list[HomeSchema]})
def list_homes(request: HttpRequest):
    memberships = get_user_memberships(request)
    homes = Home.objects.filter(memberships__in=memberships)
    return homes


@homes_v1_router.patch("homes/{home_id}")
def update_home(request: HttpRequest, home_id: str, body: UpdateHomeRequest):
    memberships = get_user_memberships(request)
    try:
        home = Home.objects.get(memberships__in=memberships, id=home_id)
    except Home.DoesNotExist:
        raise HttpError(403, "Forbidden")
    if body.name:
        home.name = body.name
    if body.description:
        home.description = body.description
    home.save()


@homes_v1_router.get("holidays", response={200: list[HolidaySchema]})
def list_upcoming_holidays(
    request: HttpRequest, include_past: bool = False
) -> Manager[Holiday]:
    """Your holidays, earliest first: those that haven't ended yet (a holiday
    runs to the end of its last day), or all of them with `include_past`."""
    memberships = get_user_memberships(request)
    holidays = Holiday.objects.filter(membership__in=memberships)
    if not include_past:
        holidays = holidays.filter(to_date__date__gte=timezone.now().date())
    return holidays.order_by("from_date")


@homes_v1_router.delete("holidays/{holiday_id}", response={200: None})
def delete_holiday(request: HttpRequest, holiday_id: str):
    try:
        holiday = Holiday.objects.get(membership__user=request.user, id=holiday_id)
    except Holiday.DoesNotExist:
        raise HttpError(404, "Not found")
    holiday.delete()


@homes_v1_router.patch("holidays/{holiday_id}", response={200: HolidaySchema})
def update_holiday(request: HttpRequest, holiday_id: str, data: UpdateHolidaySchema):
    try:
        holiday = Holiday.objects.get(membership__user=request.user, id=holiday_id)
    except Holiday.DoesNotExist:
        raise HttpError(404, "Not found")
    if data.from_date > data.to_date:
        raise HttpError(400, "From date must be before to date")
    if data.to_date.date() < timezone.now().date():
        raise HttpError(400, "Must end in the future")
    holiday.from_date = data.from_date
    holiday.to_date = data.to_date
    holiday.note = data.note
    holiday.save()
    return holiday


@homes_v1_router.post("holidays/", response={200: None})
def create_holiday(request: HttpRequest, data: CreateHolidaySchema):
    try:
        membership = Membership.objects.get(user=request.user, home__id=data.home_id)
    except Membership.DoesNotExist:
        raise HttpError(404, "Not found")
    if data.from_date > data.to_date:
        raise HttpError(400, "From date must be before to date")
    if data.to_date.date() < timezone.now().date():
        raise HttpError(400, "Must end in the future")

    Holiday(
        membership=membership,
        note=data.note,
        from_date=data.from_date,
        to_date=data.to_date,
    ).save()
