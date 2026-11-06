"""Child page: schemas, routes and completion."""

from datetime import UTC, datetime, time, timedelta, timezone
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException
from pydantic import AwareDatetime, BaseModel, BeforeValidator, Field, model_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.completion import CHECKERS, PageError, PageStatusResponse, result
from app.enums import CHILD_FREE_TEXT_TYPES, CHILD_OPTION_TYPES, DAYS_OF_WEEK, SCHEDULE_ACTIVITIES
from app.models import Child, ChildBackground, ChildSchedule, Therapy, TreatmentPlan
from app.routes.common import apply_patch, get_owned
from app.routes.education import attends_school
from app.routes.plan import SessionDep, load_plan, load_plan_for_write
from app.rules import Body, OneOf, RichText

router = APIRouter(prefix="/api/v2/treatment_plans/{plan_id}/pages/child")

TYPO = "Verbal a ggression"
MIN_ITEMS = {"COMMUNICATION_STYLE": 1, "GOALS_FOR_THERAPY": 1, "BEHAVIOR_ISSUE": 1} | {t: 2 for t in CHILD_FREE_TEXT_TYPES}
MIN_OFFSET, MAX_OFFSET = -12 * 3600, 14 * 3600


def _fix_typo(value: object) -> object:
    return value.replace(TYPO, "Verbal aggression") if isinstance(value, str) else value


class ChildPatch(Body):
    child_behavior_issues: RichText(800) | None = None


class ChildBackgroundCreateRequest(Body):
    background_type: Literal["COMMUNICATION_STYLE", "GOALS_FOR_THERAPY", "STRENGTH", "WEAKNESS", "INTEREST", "DISLIKES", "BEHAVIOR_ISSUE"]
    background_description: Annotated[str, BeforeValidator(_fix_typo), Field(min_length=1, max_length=2000)]

    @model_validator(mode="after")
    def listed_label(self) -> "ChildBackgroundCreateRequest":
        """Dropdown types must use one of their listed labels."""
        options = CHILD_OPTION_TYPES.get(self.background_type)
        if options and self.background_description not in options:
            raise ValueError(f"background_description is not an option for {self.background_type}")
        return self


class ChildBackgroundResponse(BaseModel):
    id: int
    background_type: str
    background_description: str


class ChildScheduleCreateRequest(Body):
    day_of_week: OneOf(DAYS_OF_WEEK)
    schedule_activity_type: OneOf(tuple(SCHEDULE_ACTIVITIES))
    schedule_start_date: AwareDatetime
    schedule_end_date: AwareDatetime
    utc_offset: Annotated[int, Field(ge=MIN_OFFSET, le=MAX_OFFSET)]

    @model_validator(mode="after")
    def valid_interval(self) -> "ChildScheduleCreateRequest":
        """Both times use the given offset, fall on the same local day, and end after start."""
        offset = timedelta(seconds=self.utc_offset)
        if self.schedule_start_date.utcoffset() != offset or self.schedule_end_date.utcoffset() != offset:
            raise ValueError("Times must use the given UTC offset")
        if self.schedule_end_date <= self.schedule_start_date:
            raise ValueError("End time must be after start time")
        if self.schedule_end_date.date() != self.schedule_start_date.date():
            raise ValueError("Start and end must be on the same day")
        return self


class ChildScheduleResponse(BaseModel):
    id: int
    day_of_week: str
    schedule_activity_type: str
    schedule_start_date: datetime
    schedule_end_date: datetime
    utc_offset: int


class ChildPageResponse(BaseModel):
    child_behavior_issues: str | None
    backgrounds: list[ChildBackgroundResponse]
    schedule: list[ChildScheduleResponse]


def local(value: datetime, offset: int) -> datetime:
    """Stored naive UTC to an aware datetime in the slot's offset."""
    return value.replace(tzinfo=UTC).astimezone(timezone(timedelta(seconds=offset)))


def local_span(slot: ChildSchedule) -> tuple[time, time]:
    return local(slot.schedule_start_date, slot.utc_offset).time(), local(slot.schedule_end_date, slot.utc_offset).time()


def to_naive_utc(value: datetime) -> datetime:
    return value.astimezone(UTC).replace(tzinfo=None)


def schedule_response(slot: ChildSchedule) -> ChildScheduleResponse:
    return ChildScheduleResponse(
        id=slot.id,
        day_of_week=slot.day_of_week,
        schedule_activity_type=slot.schedule_activity_type,
        schedule_start_date=local(slot.schedule_start_date, slot.utc_offset),
        schedule_end_date=local(slot.schedule_end_date, slot.utc_offset),
        utc_offset=slot.utc_offset,
    )


def sorted_schedule(child: Child) -> list[ChildSchedule]:
    return sorted(child.schedule, key=lambda s: (DAYS_OF_WEEK.index(s.day_of_week), local_span(s)[0]))


def page_response(child: Child | None) -> ChildPageResponse:
    if child is None:
        return ChildPageResponse(child_behavior_issues=None, backgrounds=[], schedule=[])
    return ChildPageResponse(
        child_behavior_issues=child.child_behavior_issues,
        backgrounds=[
            ChildBackgroundResponse(id=b.id, background_type=b.background_type, background_description=b.background_description)
            for b in child.backgrounds
        ],
        schedule=[schedule_response(s) for s in sorted_schedule(child)],
    )


def find_child(session: Session, plan_id: int) -> Child | None:
    return session.scalar(select(Child).where(Child.treatment_plan_id == plan_id))


def get_or_create_child(session: Session, plan_id: int) -> Child:
    child = find_child(session, plan_id)
    if child is None:
        child = Child(treatment_plan_id=plan_id)
        session.add(child)
        session.flush()
    return child


def child_id_of(session: Session, plan_id: int) -> int | None:
    child = find_child(session, plan_id)
    return child.id if child else None


def overlaps(a: tuple[time, time], b: tuple[time, time]) -> bool:
    return a[0] < b[1] and b[0] < a[1]


@router.get("/")
def get_child(plan_id: int, session: SessionDep) -> ChildPageResponse:
    load_plan(session, plan_id)
    return page_response(find_child(session, plan_id))


@router.patch("/")
def patch_child(plan_id: int, body: ChildPatch, session: SessionDep) -> ChildPageResponse:
    load_plan_for_write(session, plan_id)
    child = get_or_create_child(session, plan_id)
    apply_patch(child, body)
    session.commit()
    return page_response(child)


@router.post("/backgrounds/", status_code=201)
def create_background(plan_id: int, body: ChildBackgroundCreateRequest, session: SessionDep) -> ChildBackgroundResponse:
    load_plan_for_write(session, plan_id)
    item = ChildBackground(child_id=get_or_create_child(session, plan_id).id, **body.model_dump())
    session.add(item)
    try:
        session.commit()
    except IntegrityError:
        raise HTTPException(409, "This item is already in the list")
    return ChildBackgroundResponse(id=item.id, **body.model_dump())


@router.delete("/backgrounds/{background_id}/", status_code=204)
def delete_background(plan_id: int, background_id: int, session: SessionDep) -> None:
    load_plan_for_write(session, plan_id)
    session.delete(get_owned(session, ChildBackground, background_id, "child_id", child_id_of(session, plan_id)))
    session.commit()


@router.post("/schedule/", status_code=201)
def create_schedule(plan_id: int, body: ChildScheduleCreateRequest, session: SessionDep) -> ChildScheduleResponse:
    load_plan_for_write(session, plan_id)
    child = get_or_create_child(session, plan_id)
    span = (body.schedule_start_date.time(), body.schedule_end_date.time())
    if any(s.day_of_week == body.day_of_week and overlaps(span, local_span(s)) for s in child.schedule):
        raise HTTPException(409, "This time overlaps another slot on the same day")
    slot = ChildSchedule(
        child_id=child.id,
        day_of_week=body.day_of_week,
        schedule_activity_type=body.schedule_activity_type,
        schedule_start_date=to_naive_utc(body.schedule_start_date),
        schedule_end_date=to_naive_utc(body.schedule_end_date),
        utc_offset=body.utc_offset,
    )
    session.add(slot)
    session.commit()
    return schedule_response(slot)


@router.delete("/schedule/{schedule_id}/", status_code=204)
def delete_schedule(plan_id: int, schedule_id: int, session: SessionDep) -> None:
    load_plan_for_write(session, plan_id)
    session.delete(get_owned(session, ChildSchedule, schedule_id, "child_id", child_id_of(session, plan_id)))
    session.commit()


def had_historical_therapy(session: Session, plan_id: int) -> bool:
    """True when Therapy says the client had historical therapy."""
    flag = session.scalar(select(Therapy.no_historical_therapy).where(Therapy.treatment_plan_id == plan_id))
    return flag is False


def schedule_errors(session: Session, plan_id: int, slots: list[ChildSchedule]) -> list[PageError]:
    """Slots the page needs, based on this page and on Education and Therapy."""
    activities = {s.schedule_activity_type for s in slots}
    needed = [("FORTA_THERAPY", "Add at least one slot available for Forta therapy")]
    if attends_school(session, plan_id):
        needed.append(("SCHOOL", "The child attends school, so add a School slot"))
    if had_historical_therapy(session, plan_id):
        needed.append(("OTHER_THERAPY", "The client has historical therapy, so add an Other therapies slot"))
    return [PageError(field="schedule", message=message) for activity, message in needed if activity not in activities]


def child_status(session: Session, plan: TreatmentPlan) -> PageStatusResponse:
    child = find_child(session, plan.id)
    if child is None:
        return PageStatusResponse(page="child", status="empty")
    errors = []
    for background_type, minimum in MIN_ITEMS.items():
        count = sum(b.background_type == background_type for b in child.backgrounds)
        if count < minimum:
            errors.append(PageError(field=background_type, message=f"Add at least {minimum}"))
    errors += schedule_errors(session, plan.id, child.schedule)
    return result("child", errors)


CHECKERS["child"] = child_status
