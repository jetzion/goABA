"""Education page: schemas, routes and completion."""

from datetime import date
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field, PlainSerializer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.completion import CHECKERS, PageError, PageStatusResponse, required, result
from app.enums import CLASSROOM_SETTINGS, EDUCATION_SETTINGS, EVALUATION_STATUSES, IEP_OR_504, SCHOOL_ATTITUDES
from app.models import Education, TreatmentPlan
from app.routes.common import apply_patch
from app.routes.plan import SessionDep, load_plan, load_plan_for_write
from app.rules import Body, OneOf, Phone, RichText, Text

router = APIRouter(prefix="/api/v2/treatment_plans/{plan_id}/pages/education")

WeeklyHours = Annotated[Decimal, Field(gt=0, le=40, decimal_places=1), PlainSerializer(float, return_type=float)]


class EducationPatchRequest(Body):
    not_attending_school: bool = False
    education_setting: OneOf(EDUCATION_SETTINGS) | None = None
    number_of_hours_per_week: WeeklyHours | None = None
    school_name: Text(4, 255) | None = None
    school_phone_number: Phone | None = None
    education_description: RichText(800, 8) | None = None
    focus_area_description: RichText(800, 8) | None = None
    evaluation_status: OneOf(EVALUATION_STATUSES) | None = None
    evaluation_date: date | None = None
    iep_or_504_in_place: OneOf(IEP_OR_504) | None = None
    education_support: Text(8, 255) | None = None
    classroom_setting: OneOf(CLASSROOM_SETTINGS) | None = None
    attitude_towards_school: OneOf(SCHOOL_ATTITUDES) | None = None


DETAIL_FIELDS = [f for f in EducationPatchRequest.model_fields if f != "not_attending_school"]
OPTIONAL_FIELDS = {"evaluation_status", "evaluation_date"}
HOMESCHOOL_OPTIONAL = {"school_name", "school_phone_number"}


class EducationPageResponse(EducationPatchRequest):
    model_config = ConfigDict(extra="ignore", from_attributes=True)


def find_page(session: Session, plan_id: int) -> Education | None:
    return session.scalar(select(Education).where(Education.treatment_plan_id == plan_id))


@router.get("/")
def get_education(plan_id: int, session: SessionDep) -> EducationPageResponse:
    load_plan(session, plan_id)
    page = find_page(session, plan_id)
    return EducationPageResponse.model_validate(page) if page else EducationPageResponse()


@router.patch("/")
def patch_education(plan_id: int, body: EducationPatchRequest, session: SessionDep) -> EducationPageResponse:
    load_plan_for_write(session, plan_id)
    page = find_page(session, plan_id)
    if page is None:
        page = Education(treatment_plan_id=plan_id)
        session.add(page)
    apply_patch(page, body)
    session.commit()
    return EducationPageResponse.model_validate(page)


def required_fields(page: Education) -> list[str]:
    """Fields a complete attending-school page needs. Homeschool needs no school name or phone."""
    skip = OPTIONAL_FIELDS | (HOMESCHOOL_OPTIONAL if page.education_setting == "Homeschool" else set())
    return [f for f in DETAIL_FIELDS if f not in skip]


def education_status(session: Session, plan: TreatmentPlan) -> PageStatusResponse:
    page = find_page(session, plan.id)
    if page is None:
        return PageStatusResponse(page="education", status="empty")
    if page.not_attending_school:
        filled = [f for f in DETAIL_FIELDS if getattr(page, f) is not None]
        return result("education", [PageError(field=f, message="Must be empty when the child is not attending school") for f in filled])
    return result("education", required(page, required_fields(page)))


def attends_school(session: Session, plan_id: int) -> bool:
    """True when the Education page says the child attends school."""
    page = find_page(session, plan_id)
    return page is not None and not page.not_attending_school


CHECKERS["education"] = education_status
