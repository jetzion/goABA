"""Treatment page: schemas, routes and completion."""

from datetime import date

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.completion import CHECKERS, PageError, PageStatusResponse, required, result
from app.enums import SERVICE_PER, SERVICES
from app.models import ClientAssignment, Provider, Treatment, TreatmentPlan
from app.routes.common import apply_patch
from app.routes.plan import SessionDep, load_plan, load_plan_for_write
from app.rules import Body, IntRange, OneOf, RichText, visible_length

router = APIRouter(prefix="/api/v2/treatment_plans/{plan_id}/pages/treatment")

ASSESSMENT_CODES = ("assessment_97151", "assessment_97152")
ASSESSMENT_COMBINED_MAX = 8
Per = OneOf(SERVICE_PER)
AssessmentHours = IntRange(0, 8)
Hours = IntRange(0, 99)

TECHNICIAN_SUPERVISED = (
    "A trained behavioral technician administers the treatment protocol under the supervision of a BCBA."
)
BCBA_ADMINISTERED = "A BCBA administers the treatment protocol."


class TreatmentPatchRequest(Body):
    recommendations_explanation: RichText() | None = None
    proposed_start_date: date | None = None
    duration_in_months: IntRange(1, 99) | None = None
    assessment_97151_hours: AssessmentHours | None = None
    assessment_97151_per: Per | None = None
    assessment_97152_hours: AssessmentHours | None = None
    assessment_97152_per: Per | None = None
    direct_therapy_97153_hours: Hours | None = None
    direct_therapy_97153_per: Per | None = None
    protocol_modification_97155_hours: Hours | None = None
    protocol_modification_97155_per: Per | None = None
    parent_training_97156_hours: Hours | None = None
    parent_training_97156_per: Per | None = None
    group_parent_training_97157_hours: Hours | None = None
    group_parent_training_97157_per: Per | None = None
    care_coordination_99366_hours: Hours | None = None
    care_coordination_99366_per: Per | None = None


class Service(BaseModel):
    hours: int | None
    units: int | None
    per: str | None


class TreatmentPageResponse(BaseModel):
    recommendations_explanation: str | None
    proposed_start_date: date | None
    duration_in_months: int | None
    services: dict[str, Service]
    therapy_provisioning_description: str | None


def find_treatment(session: Session, plan_id: int) -> Treatment | None:
    return session.scalar(select(Treatment).where(Treatment.treatment_plan_id == plan_id))


def provisioning_description(session: Session, plan: TreatmentPlan) -> str | None:
    """Fixed text by bay. Bay 3 names the assigned behavior technicians and is blank without one."""
    if plan.bay in ("2.6", "7"):
        return TECHNICIAN_SUPERVISED
    if plan.bay == "6":
        return BCBA_ADMINISTERED
    if plan.bay == "3":
        names = session.scalars(
            select(Provider.display_name)
            .join(ClientAssignment, ClientAssignment.provider_id == Provider.id)
            .where(ClientAssignment.client_id == plan.client_id, ClientAssignment.role == "bt")
            .order_by(Provider.display_name)
        ).all()
        if not names:
            return None
        return (
            f"Treatment is provided by {', '.join(names)}, behavior technician. "
            "The therapist is the parent of the recipient and is supervised by a BCBA."
        )
    return None


def page_response(session: Session, plan: TreatmentPlan, treatment: Treatment | None) -> TreatmentPageResponse:
    services = {}
    if treatment is not None:
        for prefix in SERVICES:
            hours = getattr(treatment, f"{prefix}_hours")
            services[prefix] = Service(hours=hours, units=None if hours is None else hours * 4, per=getattr(treatment, f"{prefix}_per"))
    return TreatmentPageResponse(
        recommendations_explanation=treatment.recommendations_explanation if treatment else None,
        proposed_start_date=treatment.proposed_start_date if treatment else None,
        duration_in_months=treatment.duration_in_months if treatment else None,
        services=services,
        therapy_provisioning_description=provisioning_description(session, plan),
    )


@router.get("/")
def get_treatment(plan_id: int, session: SessionDep) -> TreatmentPageResponse:
    plan = load_plan(session, plan_id)
    return page_response(session, plan, find_treatment(session, plan_id))


@router.patch("/")
def patch_treatment(plan_id: int, body: TreatmentPatchRequest, session: SessionDep) -> TreatmentPageResponse:
    plan = load_plan_for_write(session, plan_id)
    treatment = find_treatment(session, plan_id)
    if treatment is None:
        treatment = Treatment(treatment_plan_id=plan_id)
        session.add(treatment)
    apply_patch(treatment, body)
    combined = sum(getattr(treatment, f"{code}_hours") or 0 for code in ASSESSMENT_CODES)
    if combined > ASSESSMENT_COMBINED_MAX:
        raise HTTPException(422, "97151 and 97152 hours together cannot be more than 8")
    session.commit()
    return page_response(session, plan, treatment)


def treatment_status(session: Session, plan: TreatmentPlan) -> PageStatusResponse:
    treatment = find_treatment(session, plan.id)
    if treatment is None:
        return PageStatusResponse(page="treatment", status="empty")
    errors = required(treatment, ["proposed_start_date", "duration_in_months"])
    if visible_length(treatment.recommendations_explanation) == 0:
        errors.append(PageError(field="recommendations_explanation", message="This field is required"))
    active = [prefix for prefix in SERVICES if (getattr(treatment, f"{prefix}_hours") or 0) > 0]
    if not active:
        errors.append(PageError(field="services", message="At least one service needs hours"))
    for prefix in active:
        if getattr(treatment, f"{prefix}_per") is None:
            errors.append(PageError(field=f"{prefix}_per", message="Choose how often"))
    return result("treatment", errors)


CHECKERS["treatment"] = treatment_status
