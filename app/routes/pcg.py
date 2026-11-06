"""Parent caregiver goals (PCG)."""

from fastapi import APIRouter
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.completion import PageError
from app.enums import PARENT_TRAINING
from app.models import GoalName, PcgGoal, PcgTarget, PcgTargetStage, TreatmentPlan
from app.routes.goals_common import (
    GoalBase,
    GoalKind,
    Opportunities,
    TargetKind,
    TargetPatchWithOpportunities,
    add_goal_routes,
    add_target_routes,
    base_goal_response,
    goal_measurement_errors,
    goal_patch_model,
    target_errors,
)
from app.routes.plan import SessionDep, load_plan

router = APIRouter(prefix="/api/v2/treatment_plans/{plan_id}/pages/pcg")

KIND = GoalKind(page="pcg", blocks=("mastery",), default_sessions={"mastery": 3})
TARGETS = TargetKind(
    page="pcg",
    name_min=8,
    transitions={
        "New": ("Acquisition", "On-hold", "Discontinued"),
        "Acquisition": ("Mastered", "On-hold", "Discontinued"),
        "Mastered": ("Acquisition",),
    },
    same_day=("New", "Acquisition"),
    target_model=PcgTarget,
    stage_model=PcgTargetStage,
    patch_model=TargetPatchWithOpportunities,
)


class PcgGoalBase(GoalBase):
    opportunities: Opportunities | None = None


PcgGoalPatchRequest = goal_patch_model("PcgGoalPatchRequest", PcgGoalBase, KIND)


def respond(session: Session, goal: PcgGoal) -> dict:
    return base_goal_response(goal, PcgGoalPatchRequest, TARGETS)


def plan_goals(session: Session, plan_id: int) -> list[PcgGoal]:
    return list(session.scalars(select(PcgGoal).where(PcgGoal.treatment_plan_id == plan_id).order_by(PcgGoal.id)))


@router.get("/")
def get_pcg(plan_id: int, session: SessionDep) -> dict:
    load_plan(session, plan_id)
    names = session.scalars(select(GoalName).where(GoalName.focus_area == PARENT_TRAINING, GoalName.active).order_by(GoalName.prefix))
    return {
        "focus_area": PARENT_TRAINING,
        "available_goals": [{"id": n.id, "label": n.label, "prefix": n.prefix} for n in names],
        "goals": [respond(session, g) for g in plan_goals(session, plan_id)],
    }


load_goal = add_goal_routes(
    router,
    model=PcgGoal,
    kind=KIND,
    patch_model=PcgGoalPatchRequest,
    name_allowed=lambda area: area == PARENT_TRAINING,
    respond=respond,
)
add_target_routes(router, TARGETS, load_goal)


def pcg_errors(session: Session, plan: TreatmentPlan) -> tuple[bool, list[PageError]]:
    """(is_empty, errors) for the PCG section."""
    goals = plan_goals(session, plan.id)
    errors = []
    for goal in goals:
        errors += goal_measurement_errors(goal, KIND)
        for target in goal.targets:
            errors += target_errors(TARGETS, goal.data_collection_method, target)
    return not goals, errors
