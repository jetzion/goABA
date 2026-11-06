"""Discharge page: schemas, routes and completion."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, model_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.completion import CHECKERS, PageError, PageStatusResponse, result
from app.enums import DISCHARGE_REASONS
from app.models import Discharge, DischargeReason, TreatmentPlan
from app.routes.assessment import LONG_TEXT_MIN, min_visible
from app.routes.common import apply_patch, get_owned
from app.routes.plan import SessionDep, load_plan, load_plan_for_write
from app.rules import Body, OneOf, RichText, Text

router = APIRouter(prefix="/api/v2/treatment_plans/{plan_id}/pages/discharge")

OTHER = "Other"


class DischargeInfoPatch(Body):
    mastery_of_program_goals: RichText() | None = None
    titration_plan: RichText() | None = None
    readiness_to_step_down: RichText() | None = None
    care_coordination: RichText() | None = None


TEXT_FIELDS = list(DischargeInfoPatch.model_fields)


class DischargeReasonCreate(Body):
    reason: OneOf(DISCHARGE_REASONS)
    explanation: Text(4, 255) | None = None

    @model_validator(mode="after")
    def explanation_only_for_other(self) -> "DischargeReasonCreate":
        """Other needs an explanation; other reasons take none."""
        if self.reason == OTHER and self.explanation is None:
            raise ValueError("Explain the other reason in at least 4 characters")
        if self.reason != OTHER and self.explanation is not None:
            raise ValueError("Only the Other reason takes an explanation")
        return self


class DischargeReasonResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    reason: str
    explanation: str | None


class DischargePageResponse(DischargeInfoPatch):
    model_config = ConfigDict(extra="ignore")

    reasons: list[DischargeReasonResponse]


def find_discharge(session: Session, plan_id: int) -> Discharge | None:
    return session.scalar(select(Discharge).where(Discharge.treatment_plan_id == plan_id))


def get_or_create_discharge(session: Session, plan_id: int) -> Discharge:
    discharge = find_discharge(session, plan_id)
    if discharge is None:
        discharge = Discharge(treatment_plan_id=plan_id)
        session.add(discharge)
        session.flush()
    return discharge


def page_response(discharge: Discharge | None) -> DischargePageResponse:
    if discharge is None:
        return DischargePageResponse(reasons=[])
    return DischargePageResponse(
        **{f: getattr(discharge, f) for f in TEXT_FIELDS},
        reasons=[DischargeReasonResponse.model_validate(r) for r in discharge.reasons],
    )


@router.get("/")
def get_discharge(plan_id: int, session: SessionDep) -> DischargePageResponse:
    load_plan(session, plan_id)
    return page_response(find_discharge(session, plan_id))


@router.patch("/")
def patch_discharge(plan_id: int, body: DischargeInfoPatch, session: SessionDep) -> DischargePageResponse:
    load_plan_for_write(session, plan_id)
    discharge = get_or_create_discharge(session, plan_id)
    apply_patch(discharge, body)
    session.commit()
    return page_response(discharge)


@router.post("/reasons/", status_code=201)
def create_reason(plan_id: int, body: DischargeReasonCreate, session: SessionDep) -> DischargeReasonResponse:
    load_plan_for_write(session, plan_id)
    reason = DischargeReason(discharge_id=get_or_create_discharge(session, plan_id).id, **body.model_dump())
    session.add(reason)
    try:
        session.commit()
    except IntegrityError:
        raise HTTPException(409, "This reason is already selected")
    return DischargeReasonResponse.model_validate(reason)


@router.delete("/reasons/{reason_id}/", status_code=204)
def delete_reason(plan_id: int, reason_id: int, session: SessionDep) -> None:
    load_plan_for_write(session, plan_id)
    discharge = find_discharge(session, plan_id)
    session.delete(get_owned(session, DischargeReason, reason_id, "discharge_id", discharge.id if discharge else None))
    session.commit()


def discharge_status(session: Session, plan: TreatmentPlan) -> PageStatusResponse:
    discharge = find_discharge(session, plan.id)
    if discharge is None:
        return PageStatusResponse(page="discharge", status="empty")
    errors = []
    for field in TEXT_FIELDS:
        errors += min_visible(discharge, field, LONG_TEXT_MIN)
    if not discharge.reasons:
        errors.append(PageError(field="reasons", message="Pick at least one reason"))
    return result("discharge", errors)


CHECKERS["discharge"] = discharge_status
