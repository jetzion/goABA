"""Crisis page: schemas, routes and completion."""

import html
import re
from typing import Annotated

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.completion import CHECKERS, PageError, PageStatusResponse, required, result
from app.enums import FUNCTIONAL_BEHAVIORS
from app.models import AssessmentBehavior, Crisis, CrisisPlan, TreatmentPlan
from app.routes.assessment import LONG_TEXT_MIN, UniqueList, find_assessment, min_visible
from app.routes.common import apply_patch, get_owned
from app.routes.plan import SessionDep, load_plan, load_plan_for_write
from app.rules import Body, FirstOfMonth, RichText

router = APIRouter(prefix="/api/v2/treatment_plans/{plan_id}/pages/crisis")

TEXT_FIELDS = [
    "operational_definition",
    "antecedent_interventions",
    "precursors_action_steps",
    "escalation_intervention_plan",
    "follow_up_steps",
    "consequence_strategies",
]
BehaviorId = Annotated[int, Field(gt=0)]


class CrisisPlanPatchRequest(Body):
    assessment_behavior_id: BehaviorId = None  # type: ignore[assignment]  # omitted is allowed, null is not
    crisis_creation_date: FirstOfMonth | None = None
    operational_definition: RichText() | None = None
    antecedent_interventions: RichText() | None = None
    precursors_action_steps: RichText() | None = None
    escalation_intervention_plan: RichText() | None = None
    follow_up_steps: RichText() | None = None
    functional_behavior: UniqueList(FUNCTIONAL_BEHAVIORS, 5) = []
    consequence_strategies: RichText() | None = None


class CrisisPlanCreateRequest(CrisisPlanPatchRequest):
    assessment_behavior_id: BehaviorId


class CrisisPlanResponse(CrisisPlanPatchRequest):
    model_config = ConfigDict(extra="ignore", from_attributes=True)

    id: int
    assessment_behavior_id: int


class BehaviorChoice(BaseModel):
    id: int
    label: str
    dsm5_symptom: str | None


class NoCrisisPlanPatch(Body):
    no_crisis_plan_needed: bool


class CrisisPageResponse(BaseModel):
    no_crisis_plan_needed: bool
    plans: list[CrisisPlanResponse]
    available_behaviors: list[BehaviorChoice]


class CrisisTemplateCatalogResponse(BaseModel):
    operational_definition: str
    antecedent_interventions: str
    precursors_action_steps: str
    escalation_intervention_plan: str
    follow_up_steps: str
    consequence_strategies: str


def plain_label(behavior: AssessmentBehavior) -> str:
    """Behavior rich text as a short plain label for a dropdown."""
    text = html.unescape(re.sub(r"<[^>]+>", " ", behavior.behavior or "")).strip()
    text = re.sub(r"\s+", " ", text) or f"Behavior {behavior.id}"
    return text if len(text) <= 80 else text[:77] + "..."


def find_crisis(session: Session, plan_id: int) -> Crisis | None:
    return session.scalar(select(Crisis).where(Crisis.treatment_plan_id == plan_id))


def get_or_create_crisis(session: Session, plan_id: int) -> Crisis:
    crisis = find_crisis(session, plan_id)
    if crisis is None:
        crisis = Crisis(treatment_plan_id=plan_id)
        session.add(crisis)
        session.flush()
    return crisis


def plan_behaviors(session: Session, plan_id: int) -> list[AssessmentBehavior]:
    assessment = find_assessment(session, plan_id)
    return list(assessment.behaviors) if assessment else []


def check_behavior(session: Session, plan_id: int, behavior_id: int) -> None:
    if behavior_id not in {b.id for b in plan_behaviors(session, plan_id)}:
        raise HTTPException(422, "assessment_behavior_id must be a maladaptive behavior on this plan")


def page_response(session: Session, plan_id: int) -> CrisisPageResponse:
    crisis = find_crisis(session, plan_id)
    return CrisisPageResponse(
        no_crisis_plan_needed=crisis.no_crisis_plan_needed if crisis else False,
        plans=[CrisisPlanResponse.model_validate(p) for p in crisis.plans] if crisis else [],
        available_behaviors=[
            BehaviorChoice(id=b.id, label=plain_label(b), dsm5_symptom=b.dsm5_symptom) for b in plan_behaviors(session, plan_id)
        ],
    )


def commit_unique(session: Session) -> None:
    try:
        session.commit()
    except IntegrityError:
        raise HTTPException(409, "This behavior already has a crisis plan")


@router.get("/")
def get_crisis(plan_id: int, session: SessionDep) -> CrisisPageResponse:
    load_plan(session, plan_id)
    return page_response(session, plan_id)


@router.patch("/")
def patch_crisis(plan_id: int, body: NoCrisisPlanPatch, session: SessionDep) -> CrisisPageResponse:
    load_plan_for_write(session, plan_id)
    get_or_create_crisis(session, plan_id).no_crisis_plan_needed = body.no_crisis_plan_needed
    session.commit()
    return page_response(session, plan_id)


@router.get("/templates/")
def get_templates(plan_id: int, session: SessionDep) -> CrisisTemplateCatalogResponse:
    load_plan(session, plan_id)
    return CrisisTemplateCatalogResponse(
        operational_definition="<p>The behavior is defined as any instance in which the client:</p>",
        antecedent_interventions="<p>Before the behavior is likely, staff and caregivers will:</p>",
        precursors_action_steps="<p>Precursors include the following. When one is seen, staff will:</p>",
        escalation_intervention_plan="<p>If the behavior escalates, staff will take these steps in order:</p>",
        follow_up_steps="<p>After the crisis, staff will document the event and:</p>",
        consequence_strategies="<p>Before escalation, staff will respond to the behavior by:</p>",
    )


@router.post("/", status_code=201)
def create_plan(plan_id: int, body: CrisisPlanCreateRequest, session: SessionDep) -> CrisisPlanResponse:
    load_plan_for_write(session, plan_id)
    check_behavior(session, plan_id, body.assessment_behavior_id)
    plan = CrisisPlan(crisis_id=get_or_create_crisis(session, plan_id).id, **body.model_dump())
    session.add(plan)
    commit_unique(session)
    return CrisisPlanResponse.model_validate(plan)


@router.patch("/{crisis_plan_id}/")
def patch_plan(plan_id: int, crisis_plan_id: int, body: CrisisPlanPatchRequest, session: SessionDep) -> CrisisPlanResponse:
    load_plan_for_write(session, plan_id)
    crisis = find_crisis(session, plan_id)
    plan = get_owned(session, CrisisPlan, crisis_plan_id, "crisis_id", crisis.id if crisis else None)
    if "assessment_behavior_id" in body.model_fields_set:
        check_behavior(session, plan_id, body.assessment_behavior_id)
    apply_patch(plan, body)
    commit_unique(session)
    return CrisisPlanResponse.model_validate(plan)


@router.delete("/{crisis_plan_id}/", status_code=204)
def delete_plan(plan_id: int, crisis_plan_id: int, session: SessionDep) -> None:
    load_plan_for_write(session, plan_id)
    crisis = find_crisis(session, plan_id)
    session.delete(get_owned(session, CrisisPlan, crisis_plan_id, "crisis_id", crisis.id if crisis else None))
    session.commit()


def plan_errors(plan: CrisisPlan) -> list[PageError]:
    errors = required(plan, ["crisis_creation_date"], plan.id)
    for field in TEXT_FIELDS:
        errors += min_visible(plan, field, LONG_TEXT_MIN, plan.id)
    if not plan.functional_behavior:
        errors.append(PageError(field="functional_behavior", row_id=plan.id, message="Pick at least one"))
    return errors


def crisis_status(session: Session, plan: TreatmentPlan) -> PageStatusResponse:
    crisis = find_crisis(session, plan.id)
    if crisis is not None and crisis.no_crisis_plan_needed:
        return PageStatusResponse(page="crisis", status="completed")
    if crisis is None or not crisis.plans:
        return PageStatusResponse(page="crisis", status="empty")
    errors = []
    for crisis_plan in crisis.plans:
        errors += plan_errors(crisis_plan)
    return result("crisis", errors)


CHECKERS["crisis"] = crisis_status
