"""Therapy page: schemas, routes and completion."""

from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field, PlainSerializer, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.completion import CHECKERS, PageError, PageStatusResponse, month_after_birth, required, result
from app.enums import RECORD_SHARED, THERAPY_FREQUENCIES, THERAPY_PROGRESS, THERAPY_SERVICE_TYPES
from app.models import Client, Therapy, TherapyRow, TreatmentPlan
from app.routes.common import apply_patch, get_owned
from app.routes.plan import SessionDep, load_plan, load_plan_for_write
from app.rules import Body, Email, OneOf, PastMonth, Phone, Text, at_least_one_field

router = APIRouter(prefix="/api/v2/treatment_plans/{plan_id}/pages/therapy")

Hours = Annotated[Decimal, Field(ge=0, max_digits=4, decimal_places=1), PlainSerializer(float, return_type=float)]

CLINICAL_FIELDS = [
    "provider_name", "service_type", "phone_number", "email", "start_date",
    "end_date", "hours", "frequency", "progress", "is_record_shared",
]
REQUIRED_FIELDS = ["provider_name", "service_type", "phone_number", "email", "start_date", "hours", "frequency", "progress"]


class TherapyPatchRequest(Body):
    provider_name: Text(8, 255) | None = None
    service_type: OneOf(THERAPY_SERVICE_TYPES) | None = None
    phone_number: Phone | None = None
    email: Email | None = None
    start_date: PastMonth | None = None
    end_date: PastMonth | None = None
    hours: Hours | None = None
    frequency: OneOf(THERAPY_FREQUENCIES) | None = None
    progress: OneOf(THERAPY_PROGRESS) | None = None
    do_not_share_info_with_provider: bool = False
    is_record_shared: OneOf(RECORD_SHARED) | None = None


class TherapyCreateRequest(TherapyPatchRequest):
    @model_validator(mode="after")
    def has_clinical_field(self) -> "TherapyCreateRequest":
        if all(getattr(self, f) is None for f in CLINICAL_FIELDS):
            raise ValueError("Provide at least one therapy field")
        return self


class TherapyResponse(TherapyPatchRequest):
    model_config = ConfigDict(extra="ignore", from_attributes=True)

    id: int


class NoHistoricalTherapyPatch(Body):
    no_historical_therapy: bool


class TherapyPageResponse(BaseModel):
    no_historical_therapy: bool | None
    therapies: list[TherapyResponse]


def find_page(session: Session, plan_id: int) -> Therapy | None:
    return session.scalar(select(Therapy).where(Therapy.treatment_plan_id == plan_id))


def get_or_create_page(session: Session, plan_id: int) -> Therapy:
    page = find_page(session, plan_id)
    if page is None:
        page = Therapy(treatment_plan_id=plan_id)
        session.add(page)
        session.flush()
    return page


def page_response(page: Therapy | None) -> TherapyPageResponse:
    if page is None:
        return TherapyPageResponse(no_historical_therapy=None, therapies=[])
    return TherapyPageResponse(
        no_historical_therapy=page.no_historical_therapy,
        therapies=[TherapyResponse.model_validate(r) for r in page.rows],
    )


def load_row(session: Session, plan_id: int, therapy_id: int) -> TherapyRow:
    page = find_page(session, plan_id)
    return get_owned(session, TherapyRow, therapy_id, "therapy_id", page.id if page else None)


@router.get("/")
def get_therapy(plan_id: int, session: SessionDep) -> TherapyPageResponse:
    load_plan(session, plan_id)
    return page_response(find_page(session, plan_id))


@router.patch("/")
def patch_therapy(plan_id: int, body: NoHistoricalTherapyPatch, session: SessionDep) -> TherapyPageResponse:
    load_plan_for_write(session, plan_id)
    page = get_or_create_page(session, plan_id)
    page.no_historical_therapy = body.no_historical_therapy
    session.commit()
    return page_response(page)


@router.post("/", status_code=201)
def create_therapy(plan_id: int, body: TherapyCreateRequest, session: SessionDep) -> TherapyResponse:
    load_plan_for_write(session, plan_id)
    page = get_or_create_page(session, plan_id)
    row = TherapyRow(therapy_id=page.id, **body.model_dump())
    session.add(row)
    session.commit()
    return TherapyResponse.model_validate(row)


@router.patch("/{therapy_id}/")
def patch_therapy_row(plan_id: int, therapy_id: int, body: TherapyPatchRequest, session: SessionDep) -> TherapyResponse:
    load_plan_for_write(session, plan_id)
    row = load_row(session, plan_id, therapy_id)
    apply_patch(row, body)
    session.commit()
    return TherapyResponse.model_validate(row)


@router.delete("/{therapy_id}/", status_code=204)
def delete_therapy_row(plan_id: int, therapy_id: int, session: SessionDep) -> None:
    load_plan_for_write(session, plan_id)
    session.delete(load_row(session, plan_id, therapy_id))
    session.commit()


def row_errors(row: TherapyRow, client_dob) -> list[PageError]:
    """Required fields, the record-shared rule, and date order."""
    errors = required(row, REQUIRED_FIELDS, row.id)
    if row.do_not_share_info_with_provider and row.is_record_shared is not None:
        errors.append(PageError(field="is_record_shared", row_id=row.id, message="Must be empty when info is not shared"))
    if not row.do_not_share_info_with_provider and row.is_record_shared is None:
        errors.append(PageError(field="is_record_shared", row_id=row.id, message="This field is required"))
    if row.start_date and row.end_date and row.end_date < row.start_date:
        errors.append(PageError(field="end_date", row_id=row.id, message="Must be on or after the start month"))
    errors += month_after_birth(client_dob, row.start_date, "start_date", row.id)
    errors += month_after_birth(client_dob, row.end_date, "end_date", row.id)
    return errors


def therapy_status(session: Session, plan: TreatmentPlan) -> PageStatusResponse:
    page = find_page(session, plan.id)
    rows = page.rows if page else []
    flag = page.no_historical_therapy if page else None
    if flag is None:
        if not rows:
            return PageStatusResponse(page="therapy", status="empty")
        return result("therapy", [PageError(field="no_historical_therapy", message="Select whether the client had historical therapy")])
    if flag:
        errors = [PageError(field="no_historical_therapy", message="Delete the therapies or clear the no historical therapy box")] if rows else []
        return result("therapy", errors)
    if not rows:
        return result("therapy", [PageError(field="no_historical_therapy", message="Add a therapy or check no historical therapy")])
    dob = session.get_one(Client, plan.client_id).date_of_birth
    errors = []
    for row in rows:
        errors += row_errors(row, dob)
    return result("therapy", errors)


CHECKERS["therapy"] = therapy_status
