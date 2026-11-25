from typing import Optional, Union, Literal

from django.contrib.auth import get_user_model
from django.db import transaction
from django.http import HttpRequest
from ninja import Query, Router
from datetime import date, datetime, timedelta
from django.utils import timezone

from domovoy.apps.regular_job.rules import SnoozeOption
from domovoy.apps.regular_job.utils import before_midnight
from domovoy.security.session_key import SessionHeader
from ninja.errors import HttpError
from domovoy.apps.regular_job.api.v1.schemas import (
    RegularJobDefinitionSchema,
    CreateRegularJobDefinitionRequest,
    CreateRegularJobInstanceRequest, RegularJobDefinitionEditSchema, RegularJobInstanceSchema, ClaimResponse,
    JobCompletionSchema,
)
from domovoy.apps.dmv_home.models import Home
from domovoy.apps.regular_job.models import RegularJobDefinition, RegularJobInstance

from domovoy.apps.regular_job.stats import HomeStatistics, get_statistics
from domovoy.apps.regular_job.upkeep import HomeUpkeep, get_upkeep

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
    for k, v in changes.model_dump(exclude_none=True).items():
        setattr(job, k, v)
    job.save()
    if changes.rules:
        job.adjust()
    return job


@regular_jobs_v1_router.post("/definitions")
def create_regular_job_definition(
    request: HttpRequest, home_id: int, data: CreateRegularJobDefinitionRequest
):
    try:
        home = request.user.home_set.get(id=home_id)
    except Home.DoesNotExist:
        raise HttpError(404, "Home not found")
    if home.regular_jobs.count() >= 500:
        raise HttpError(403, "Job definition limit exceeded")

    new_job = RegularJobDefinition(home=home, **data.model_dump())
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


def same_occurrence(current: Optional[datetime], seen: Optional[datetime]) -> bool:
    """Whether the occurrence the client saw (its `next_assigned_date`) is still current."""
    # Each claim, snooze or reassignment sets a new timestamp. The API sends
    # it to the millisecond (Django's JSON encoder), so compare at that
    # precision: claims even a moment apart still differ.
    if current is None or seen is None:
        return current is seen
    return current.replace(microsecond=current.microsecond // 1000 * 1000) == seen.replace(
        microsecond=seen.microsecond // 1000 * 1000
    )


def locked_definition(request: HttpRequest, definition_id: int) -> RegularJobDefinition:
    """The job, row-locked for the rest of the transaction, if it's in your homes."""
    try:
        return RegularJobDefinition.objects.select_for_update().get(
            id=definition_id, home__in=request.user.home_set.all()
        )
    except RegularJobDefinition.DoesNotExist:
        raise HttpError(404, "Job definition not found")


ALREADY_DONE = "Already done: this job has moved on since you opened it."


@regular_jobs_v1_router.post(
    "/definitions/{definition_id}/instances", response={200: ClaimResponse}
)
@transaction.atomic
def create_instance(
    request: HttpRequest, definition_id: int, data: CreateRegularJobInstanceRequest
) -> ClaimResponse:
    # Locked, so two claims for the same occurrence can't both pass the check.
    definition = locked_definition(request, definition_id)
    if data.assigned_at is not None and not same_occurrence(
        definition.next_assigned_date, data.assigned_at
    ):
        raise HttpError(409, ALREADY_DONE)

    value = definition.claim(request.user, data.value)

    return ClaimResponse(
        value=value,
        statistics=get_statistics(request.user, definition.home, 30),
        result=definition.assignment_notes,
        definition=definition,
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
    "/definitions/{definition_id}/snooze", response={200: RegularJobDefinitionSchema}
)
@transaction.atomic
def snooze(
    request: HttpRequest,
    definition_id: int,
    new_date: date,
    assigned_at: Optional[datetime] = None,
):
    """Move the current occurrence to `new_date`. With `assigned_at` (the
    job's `next_assigned_date` as you saw it), refused with 409 if that
    occurrence has since been dealt with, so a stale snooze can't move the
    next one instead."""
    definition = locked_definition(request, definition_id)
    if assigned_at is not None and not same_occurrence(definition.next_assigned_date, assigned_at):
        raise HttpError(409, ALREADY_DONE)

    definition.next_assigned_date = timezone.now()
    definition.next_assigned_due_date = before_midnight(new_date)
    definition.next_assigned_start_date = definition.next_assigned_due_date - timedelta(
        days=definition.open_for_days
    )
    definition.save()
    return definition


@regular_jobs_v1_router.get("/statistics", response={200: HomeStatistics})
def home_statistics(
    request: HttpRequest, home_id: int, days: int = Query(30, ge=1, le=365)
):
    """Each member's points per day over the last `days` days, for one of your homes."""
    try:
        home = request.user.home_set.get(id=home_id)
    except Home.DoesNotExist:
        raise HttpError(404, "Home not found")
    return get_statistics(request.user, home, days)


@regular_jobs_v1_router.get("/instances", response={200: list[JobCompletionSchema]})
def list_completions(
    request: HttpRequest,
    home_id: Optional[int] = None,
    user_id: Optional[int] = None,
    since: Optional[datetime] = None,
    before: Optional[datetime] = None,
    limit: int = Query(30, ge=1, le=100),
):
    """Jobs completed in your homes, newest first.

    Narrow it to one home (`home_id`) or one member (`user_id`), to completions
    from `since` onwards, and page back with `before` (the `completed_at` of
    the last item you have).
    """
    completions = RegularJobInstance.objects.filter(
        job__home__in=request.user.home_set.all(), completed_at__isnull=False
    ).select_related("job")
    if home_id is not None:
        completions = completions.filter(job__home_id=home_id)
    if user_id is not None:
        completions = completions.filter(completed_by_id=user_id)
    if since is not None:
        completions = completions.filter(completed_at__gte=since)
    if before is not None:
        completions = completions.filter(completed_at__lt=before)
    return [
        JobCompletionSchema(
            id=completion.id,
            job_id=completion.job_id,
            job_name=completion.job.name,
            home_id=completion.job.home_id,
            value=completion.value,
            completed_by_id=completion.completed_by_id,
            completed_at=completion.completed_at,
            due_at=completion.due_at,
            on_time=None if completion.due_at is None else completion.completed_at <= completion.due_at,
        )
        for completion in completions.order_by("-completed_at", "-id")[:limit]
    ]


@regular_jobs_v1_router.get("/upkeep", response={200: HomeUpkeep})
def home_upkeep(request: HttpRequest, home_id: int, days: int = Query(56, ge=7, le=365)):
    """How well one of your homes is keeping up with its jobs.

    `ideal_per_week`: the points a week of every job done on schedule would
    earn (each job's occurrences per week, from its rules over a year, times
    its default value). `daily_points`: points actually earned each day of
    the last `days`, without overdue bonuses. `daily_jobs`, `daily_on_time`
    and `daily_late`: jobs completed each day, and how many of those met or
    missed a due date. `jobs`: each job's share of the ideal.
    """
    try:
        home = request.user.home_set.get(id=home_id)
    except Home.DoesNotExist:
        raise HttpError(404, "Home not found")
    return get_upkeep(home, days)
