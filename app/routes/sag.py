"""Skill acquisition goals (SAG)."""

from fastapi import APIRouter
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.completion import PageError
from app.enums import BEHAVIOR_CHANGE, GOAL_FREQUENCIES, PARENT_TRAINING
from app.models import BrgGoal, BrgGoalSagLink, GoalName, SagGoal, SagTarget, SagTargetStage, TreatmentPlan
from app.routes.goals_common import (
    GoalBase,
    GoalKind,
    Opportunities,
    TargetKind,
    TargetPatchWithOpportunities,
    add_goal_routes,
    add_target_routes,
    base_goal_response,
    err,
    goal_measurement_errors,
    goal_patch_model,
    missing,
    target_errors,
)
from app.routes.plan import SessionDep, load_plan
from app.rules import OneOf

router = APIRouter(prefix="/api/v2/treatment_plans/{plan_id}/pages/sag")

KIND = GoalKind(
    page="sag",
    blocks=("acquisition", "generalization", "maintenance"),
    default_sessions={"acquisition": 3, "generalization": 3, "maintenance": 10},
)
TARGETS = TargetKind(
    page="sag",
    name_min=16,
    transitions={
        "New": ("Probe", "On-hold", "Discontinued"),
        "Probe": ("Acquisition", "On-hold", "Discontinued"),
        "Acquisition": ("Generalization", "On-hold", "Discontinued"),
        "Generalization": ("Acquisition", "Maintenance", "On-hold", "Discontinued"),
        "Maintenance": ("Generalization", "Mastered", "On-hold", "Discontinued"),
        "Mastered": ("Maintenance", "Generalization"),
    },
    same_day=("New", "Probe"),
    system_only={("Probe", "Acquisition")},
    target_model=SagTarget,
    stage_model=SagTargetStage,
    patch_model=TargetPatchWithOpportunities,
)
MIN_SUCCESS_RATE = 0.8
MIN_SESSIONS = {"acquisition": 3, "generalization": 3, "maintenance": 8}


def is_skill_area(area: str) -> bool:
    return area not in (PARENT_TRAINING, BEHAVIOR_CHANGE)


class SagGoalBase(GoalBase):
    opportunities: Opportunities | None = None
    frequency: OneOf(GOAL_FREQUENCIES) | None = None


SagGoalPatchRequest = goal_patch_model("SagGoalPatchRequest", SagGoalBase, KIND)


def respond(session: Session, goal: SagGoal) -> dict:
    linked = session.scalars(
        select(BrgGoal).join(BrgGoalSagLink, BrgGoalSagLink.brg_goal_id == BrgGoal.id).where(BrgGoalSagLink.sag_goal_id == goal.id)
    )
    return {**base_goal_response(goal, SagGoalPatchRequest, TARGETS), "linked_brg_goals": [{"id": b.id, "goal_name": b.goal_name.label} for b in linked]}


def plan_goals(session: Session, plan_id: int) -> list[SagGoal]:
    return list(session.scalars(select(SagGoal).where(SagGoal.treatment_plan_id == plan_id).order_by(SagGoal.id)))


@router.get("/")
def get_sag(plan_id: int, session: SessionDep) -> dict:
    load_plan(session, plan_id)
    names = [n for n in session.scalars(select(GoalName).where(GoalName.active).order_by(GoalName.prefix)) if is_skill_area(n.focus_area)]
    areas = sorted({n.focus_area for n in names})
    return {
        "focus_areas": [
            {"name": area, "goals": [{"id": n.id, "label": n.label, "prefix": n.prefix} for n in names if n.focus_area == area]}
            for area in areas
        ],
        "goals": [respond(session, g) for g in plan_goals(session, plan_id)],
    }


@router.get("/templates/")
def get_templates(plan_id: int, session: SessionDep) -> dict:
    load_plan(session, plan_id)
    return {
        "goal_description": "<p>Given [materials and setting], the client will [skill] with [prompt level] across [sessions].</p>",
        "target_description": "<p>The target is met when the client [observable response] following [discriminative stimulus].</p>",
        "target_instructions": "Present the instruction, wait 3 seconds, prompt as needed, and reinforce correct responses.",
    }


load_goal = add_goal_routes(
    router,
    model=SagGoal,
    kind=KIND,
    patch_model=SagGoalPatchRequest,
    name_allowed=is_skill_area,
    respond=respond,
)
add_target_routes(router, TARGETS, load_goal)


def percentage_errors(goal: SagGoal) -> list[PageError]:
    """Percentage goals: baseline below opportunities, at least 80 percent success, enough sessions."""
    if goal.data_collection_method != "Percentage" or goal.opportunities is None:
        return []
    errors = []
    if goal.baseline_level is not None and goal.baseline_level >= goal.opportunities:
        errors.append(err("sag", "goal", "baseline_level", goal.id, "Must be lower than the opportunity count"))
    for block in KIND.blocks:
        responses, sessions = getattr(goal, f"{block}_responses"), getattr(goal, f"{block}_sessions")
        if responses is not None and responses / goal.opportunities < MIN_SUCCESS_RATE:
            errors.append(err("sag", "goal", f"{block}_responses", goal.id, "Success rate must be at least 80 percent"))
        if sessions is not None and sessions < MIN_SESSIONS[block]:
            errors.append(err("sag", "goal", f"{block}_sessions", goal.id, f"Needs at least {MIN_SESSIONS[block]} consecutive sessions"))
    return errors


def sag_errors(session: Session, plan: TreatmentPlan) -> tuple[bool, list[PageError]]:
    """(is_empty, errors) for the SAG section."""
    goals = plan_goals(session, plan.id)
    errors = []
    for goal in goals:
        errors += goal_measurement_errors(goal, KIND) + missing("sag", "goal", goal, ["frequency"]) + percentage_errors(goal)
        for target in goal.targets:
            errors += target_errors(TARGETS, goal.data_collection_method, target)
    return not goals, errors
