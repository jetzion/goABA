"""Behavior reduction goals (BRG)."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, HTTPException
from pydantic import AfterValidator, BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.completion import PageError
from app.enums import BEHAVIOR_CHANGE, DSM5_SYMPTOMS, GOAL_FREQUENCIES, HYPOTHESIZED_FUNCTIONS
from app.models import BrgGoal, BrgGoalSagLink, BrgHypothesizedFunction, BrgTarget, BrgTargetStage, GoalName, SagGoal, TreatmentPlan
from app.routes.assessment import UniqueList, dsm5_symptoms, find_assessment
from app.routes.common import get_owned
from app.routes.goals_common import (
    GoalBase,
    GoalKind,
    TargetKind,
    TargetPatch,
    add_goal_routes,
    add_target_routes,
    base_goal_response,
    err,
    goal_measurement_errors,
    goal_patch_model,
    missing,
    target_errors,
)
from app.routes.plan import SessionDep, load_plan, load_plan_for_write
from app.rules import Body, OneOf, RichText, visible_length

router = APIRouter(prefix="/api/v2/treatment_plans/{plan_id}/pages/brg")

BRG_METHODS = ("Duration", "Instances", "Rate")
TEXT_FIELDS = ["operational_definition", "objective", "antecedent_modifications", "consequence_modifications"]
KIND = GoalKind(page="brg", blocks=("mastery",), default_sessions={"mastery": 3}, has_opportunities=False, has_responses=False)
TARGETS = TargetKind(
    page="brg",
    name_min=16,
    transitions={
        "New": ("In progress", "On-hold", "Discontinued"),
        "In progress": ("Mastered", "On-hold", "Discontinued"),
        "Mastered": ("In progress",),
    },
    same_day=("New", "In progress"),
    target_model=BrgTarget,
    stage_model=BrgTargetStage,
    patch_model=TargetPatch,
)


def _unique_ids(values: list[int]) -> list[int]:
    if len(set(values)) != len(values):
        raise ValueError("Each SAG goal can be linked once")
    return values


class BrgGoalBase(GoalBase):
    data_collection_method: OneOf(BRG_METHODS) = None  # type: ignore[assignment]
    dsm5_symptom: OneOf(DSM5_SYMPTOMS) | None = None
    linked_sag_goal_ids: Annotated[list[int], Field(max_length=100), AfterValidator(_unique_ids)] = []
    frequency: OneOf(GOAL_FREQUENCIES) | None = None
    operational_definition: RichText() | None = None
    objective: RichText() | None = None
    antecedent_modifications: RichText() | None = None
    consequence_modifications: RichText() | None = None


BrgGoalPatchRequest = goal_patch_model("BrgGoalPatchRequest", BrgGoalBase, KIND)


class HypothesizedFunctionCreate(Body):
    function_date: date
    functions: Annotated[UniqueList(HYPOTHESIZED_FUNCTIONS, 4), Field(min_length=1)]


def plan_symptoms(session: Session, plan_id: int) -> list[str]:
    return dsm5_symptoms(find_assessment(session, plan_id))


def respond(session: Session, goal: BrgGoal) -> dict:
    return {
        **base_goal_response(goal, BrgGoalPatchRequest, TARGETS),
        "linked_sag_goal_ids": [link.sag_goal_id for link in goal.sag_links],
        "hypothesized_functions": [{"id": f.id, "function_date": f.function_date.isoformat(), "functions": f.functions} for f in goal.functions],
    }


def before_save(session: Session, plan_id: int, goal: BrgGoal, body: BaseModel) -> None:
    """The symptom must be on this plan's Assessment page; linked goals must be SAG goals on this plan."""
    if body.model_fields_set & {"dsm5_symptom"} and goal.dsm5_symptom and goal.dsm5_symptom not in plan_symptoms(session, plan_id):
        raise HTTPException(422, "dsm5_symptom must be a symptom recorded on this plan's Assessment page")
    if "linked_sag_goal_ids" in body.model_fields_set:
        own = set(session.scalars(select(SagGoal.id).where(SagGoal.treatment_plan_id == plan_id)))
        if not set(body.linked_sag_goal_ids) <= own:
            raise HTTPException(422, "linked_sag_goal_ids must be SAG goals on this plan")
        goal.sag_links = [BrgGoalSagLink(sag_goal_id=i) for i in body.linked_sag_goal_ids]


def plan_goals(session: Session, plan_id: int) -> list[BrgGoal]:
    return list(session.scalars(select(BrgGoal).where(BrgGoal.treatment_plan_id == plan_id).order_by(BrgGoal.id)))


@router.get("/")
def get_brg(plan_id: int, session: SessionDep) -> dict:
    load_plan(session, plan_id)
    names = session.scalars(select(GoalName).where(GoalName.focus_area == BEHAVIOR_CHANGE, GoalName.active).order_by(GoalName.prefix))
    sag_goals = session.scalars(select(SagGoal).where(SagGoal.treatment_plan_id == plan_id).order_by(SagGoal.id))
    return {
        "focus_areas": [{"name": BEHAVIOR_CHANGE, "goals": [{"id": n.id, "label": n.label, "prefix": n.prefix} for n in names]}],
        "dsm5_symptoms": plan_symptoms(session, plan_id),
        "sag_goals": [{"id": g.id, "goal_name": g.goal_name.label} for g in sag_goals],
        "goals": [respond(session, g) for g in plan_goals(session, plan_id)],
    }


@router.get("/templates/")
def get_templates(plan_id: int, session: SessionDep) -> dict:
    load_plan(session, plan_id)
    return {
        "operational_definition": "<p>The behavior is any instance in which the client:</p>",
        "objective": "<p>The client will reduce the behavior to [level] across [sessions].</p>",
        "antecedent_modifications": "<p>Before the behavior is likely, staff will:</p>",
        "consequence_modifications": "<p>When the behavior occurs, staff will:</p>",
        "goal_description": "<p>Reduce [behavior] from [baseline] to [target] by [date].</p>",
    }


load_goal = add_goal_routes(
    router,
    model=BrgGoal,
    kind=KIND,
    patch_model=BrgGoalPatchRequest,
    name_allowed=lambda area: area == BEHAVIOR_CHANGE,
    respond=respond,
    before_save=before_save,
)
add_target_routes(router, TARGETS, load_goal)


@router.post("/goals/{goal_id}/hypothesized-functions/", status_code=201)
def add_functions(plan_id: int, goal_id: int, body: HypothesizedFunctionCreate, session: SessionDep) -> dict:
    load_plan_for_write(session, plan_id)
    goal = load_goal(session, plan_id, goal_id)
    goal.functions.append(BrgHypothesizedFunction(function_date=body.function_date, functions=body.functions))
    try:
        session.commit()
    except IntegrityError:
        raise HTTPException(409, "There is already an entry for this date")
    return respond(session, goal)


@router.delete("/goals/{goal_id}/hypothesized-functions/{entry_id}/", status_code=204)
def delete_functions(plan_id: int, goal_id: int, entry_id: int, session: SessionDep) -> None:
    load_plan_for_write(session, plan_id)
    load_goal(session, plan_id, goal_id)
    session.delete(get_owned(session, BrgHypothesizedFunction, entry_id, "goal_id", goal_id))
    session.commit()


def brg_errors(session: Session, plan: TreatmentPlan) -> tuple[bool, list[PageError]]:
    """(is_empty, errors) for the BRG section."""
    goals = plan_goals(session, plan.id)
    symptoms = plan_symptoms(session, plan.id)
    errors = []
    for goal in goals:
        errors += goal_measurement_errors(goal, KIND) + missing("brg", "goal", goal, ["frequency", "dsm5_symptom"])
        if goal.dsm5_symptom and goal.dsm5_symptom not in symptoms:
            errors.append(err("brg", "goal", "dsm5_symptom", goal.id, "This symptom is no longer on the Assessment page"))
        errors += [err("brg", "goal", f, goal.id, "This field is required") for f in TEXT_FIELDS if visible_length(getattr(goal, f)) == 0]
        if not goal.functions:
            errors.append(err("brg", "goal", "hypothesized_functions", goal.id, "Add at least one hypothesized function entry"))
        for target in goal.targets:
            errors += target_errors(TARGETS, goal.data_collection_method, target)
    return not goals, errors
