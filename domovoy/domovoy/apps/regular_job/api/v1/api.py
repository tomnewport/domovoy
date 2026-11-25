from typing import Optional, Union, Literal

from django.contrib.auth import get_user_model
from django.http import HttpRequest
from ninja import Router
from datetime import date, timedelta
from django.utils import timezone

from domovoy.apps.regular_job.rules import SnoozeOption
from domovoy.apps.regular_job.utils import before_midnight
from domovoy.security.session_key import SessionHeader
from ninja.errors import HttpError
from domovoy.apps.regular_job.api.v1.schemas import (
    RegularJobDefinitionSchema,
    CreateRegularJobDefinitionRequest,
    CreateRegularJobInstanceRequest, RegularJobDefinitionEditSchema, RegularJobInstanceSchema, ClaimResponse
)
from domovoy.apps.regular_job.models import RegularJobDefinition

from domovoy.apps.regular_job.stats import HomeStatistics, get_statistics

regular_jobs_v1_router = Router(tags=["Regular Jobs"], auth=[SessionHeader()])

User = get_user_model()


@regular_jobs_v1_router.get(
    "/definitions", response={200: list[RegularJobDefinitionSchema]}
)
def list_all_regular_job_definition(
    request: HttpRequest,
    home_id: Optional[int] = None,
    assignee: Union[Literal["*"], int, None] = None,
):
    user_homes = request.user.home_set.all()
    shortlist = RegularJobDefinition.objects.filter(home__in=user_homes)
    if home_id:
        shortlist = shortlist.filter(home__id=home_id)

    if assignee == "*":
        shortlist = shortlist.exclude(next_assigned_to=None)

    if isinstance(assignee, int):
        shortlist = shortlist.filter(next_assigned_to_id=assignee)

    return shortlist


@regular_jobs_v1_router.patch(
    "/definitions/{definition_id}", response={200: RegularJobDefinitionSchema}
)
def edit_regular_job_definition(
    request: HttpRequest,
    definition_id: int,
    changes: RegularJobDefinitionEditSchema
):
    user_homes = request.user.home_set.all()
    try:
        job = RegularJobDefinition.objects.get(home__in=user_homes, id=definition_id)
    except RegularJobDefinition.DoesNotExist:
        raise HttpError(404, "Not found")
    for k, v in changes.dict(exclude_none=True).items():
        setattr(job, k, v)
    job.save()
    if changes.rules:
        job.adjust()
    return job


@regular_jobs_v1_router.post("/definitions")
def create_regular_job_definition(
    request: HttpRequest, home_id: int, data: CreateRegularJobDefinitionRequest
):
    home = request.user.home_set.get(id=home_id)
    if home.regular_jobs.count() >= 500:
        raise HttpError(403, "Job definition limit exceeded")

    new_job = RegularJobDefinition(home=home, **data.dict())
    new_job.save()
    new_job.adjust()


@regular_jobs_v1_router.get(
    "/definitions/{definition_id}/instances", response={200: list[RegularJobInstanceSchema]}
)
def list_instances(
    request: HttpRequest, definition_id: int
) -> HomeStatistics:
    user_homes = request.user.home_set.all()
    try:
        definition = RegularJobDefinition.objects.get(
            id=definition_id, home__in=user_homes
        )
    except RegularJobDefinition.DoesNotExist:
        raise HttpError(404, "Job definition not found")
    return definition.instances.all()


@regular_jobs_v1_router.post(
    "/definitions/{definition_id}/instances", response={200: ClaimResponse}
)
def create_instance(
    request: HttpRequest, definition_id: int, data: CreateRegularJobInstanceRequest
) -> ClaimResponse:
    user_homes = request.user.home_set.all()
    try:
        definition = RegularJobDefinition.objects.get(
            id=definition_id, home__in=user_homes
        )
    except RegularJobDefinition.DoesNotExist:
        raise HttpError(404, "Job definition not found")

    value = definition.claim(request.user, data.value)

    return ClaimResponse(
        value=value,
        statistics=get_statistics(request.user, definition.home, 30),
        result=definition.assignment_notes
    )


@regular_jobs_v1_router.get(
    "/definitions/{definition_id}/snooze", response={200: list[SnoozeOption]}
)
def get_snooze_options(request: HttpRequest, definition_id: int) -> HomeStatistics:
    user_homes = request.user.home_set.all()
    try:
        definition = RegularJobDefinition.objects.get(
            id=definition_id, home__in=user_homes
        )
    except RegularJobDefinition.DoesNotExist:
        raise HttpError(404, "Job definition not found")

    return definition.snooze_options()


@regular_jobs_v1_router.post(
    "/definitions/{definition_id}/snooze", response={200: None}
)
def snooze(request: HttpRequest, definition_id: int, new_date: date):
    user_homes = request.user.home_set.all()
    try:
        definition = RegularJobDefinition.objects.get(
            id=definition_id, home__in=user_homes
        )
    except RegularJobDefinition.DoesNotExist:
        raise HttpError(404, "Job definition not found")

    definition.next_assigned_date = timezone.now()
    definition.next_assigned_due_date = before_midnight(new_date)
    definition.next_assigned_start_date = definition.next_assigned_due_date - timedelta(
        days=definition.open_for_days
    )
    definition.save()
