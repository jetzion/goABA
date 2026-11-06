"""Referral page: schemas, routes and completion."""

from datetime import date

from fastapi import APIRouter
from pydantic import ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.completion import CHECKERS, PageStatusResponse, required, result
from app.enums import DIAGNOSIS_TOOLS
from app.models import Referral, TreatmentPlan
from app.routes.common import apply_patch, get_owned
from app.routes.plan import SessionDep, load_plan, load_plan_for_write
from app.rules import Body, OneOf, StateCode, Text

router = APIRouter(prefix="/api/v2/treatment_plans/{plan_id}/pages/referrals")


class TreatmentPlanV3ReferralPatch(Body):
    referral_date: date | None = None
    provider_name: Text(8, 255) | None = None
    diagnosis_tool: OneOf(DIAGNOSIS_TOOLS) | None = None
    city: Text(2, 255) | None = None
    state: StateCode | None = None


TreatmentPlanV3ReferralCreate = TreatmentPlanV3ReferralPatch
FIELDS = list(TreatmentPlanV3ReferralPatch.model_fields)


class TreatmentPlanV3ReferralResponse(TreatmentPlanV3ReferralPatch):
    model_config = ConfigDict(extra="ignore", from_attributes=True)

    id: int


def plan_referrals(session: Session, plan_id: int) -> list[Referral]:
    return list(session.scalars(select(Referral).where(Referral.treatment_plan_id == plan_id).order_by(Referral.id)))


@router.get("/")
def list_referrals(plan_id: int, session: SessionDep) -> list[TreatmentPlanV3ReferralResponse]:
    load_plan(session, plan_id)
    return [TreatmentPlanV3ReferralResponse.model_validate(r) for r in plan_referrals(session, plan_id)]


@router.post("/", status_code=201)
def create_referral(plan_id: int, body: TreatmentPlanV3ReferralCreate, session: SessionDep) -> TreatmentPlanV3ReferralResponse:
    load_plan_for_write(session, plan_id)
    referral = Referral(treatment_plan_id=plan_id, **body.model_dump())
    session.add(referral)
    session.commit()
    return TreatmentPlanV3ReferralResponse.model_validate(referral)


@router.patch("/{referral_id}/")
def patch_referral(plan_id: int, referral_id: int, body: TreatmentPlanV3ReferralPatch, session: SessionDep) -> TreatmentPlanV3ReferralResponse:
    load_plan_for_write(session, plan_id)
    referral = get_owned(session, Referral, referral_id, "treatment_plan_id", plan_id)
    apply_patch(referral, body)
    session.commit()
    return TreatmentPlanV3ReferralResponse.model_validate(referral)


@router.delete("/{referral_id}/", status_code=204)
def delete_referral(plan_id: int, referral_id: int, session: SessionDep) -> None:
    load_plan_for_write(session, plan_id)
    session.delete(get_owned(session, Referral, referral_id, "treatment_plan_id", plan_id))
    session.commit()


def referral_status(session: Session, plan: TreatmentPlan) -> PageStatusResponse:
    referrals = plan_referrals(session, plan.id)
    if not referrals:
        return PageStatusResponse(page="referral", status="empty")
    errors = []
    for referral in referrals:
        errors += required(referral, FIELDS, referral.id)
    return result("referral", errors)


CHECKERS["referral"] = referral_status
