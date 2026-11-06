"""Admin: the goal-name catalog that goal pickers offer.

The focus area decides the section: Parent training is PCG, Behavior change is BRG, any other area is a skill area (SAG).
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.enums import BEHAVIOR_CHANGE, PARENT_TRAINING
from app.models import BrgGoal, GoalName, PcgGoal, SagGoal
from app.routes.plan import SessionDep
from app.rules import Body, Text

router = APIRouter(prefix="/api/v2/admin/goal_names")


class GoalNamePatchRequest(Body):
    focus_area: Text(1, 100) = None  # type: ignore[assignment]  # omitted is allowed, null is not
    label: Text(1, 255) = None  # type: ignore[assignment]
    prefix: Text(1, 20) = None  # type: ignore[assignment]
    active: bool = None  # type: ignore[assignment]


class GoalNameCreateRequest(GoalNamePatchRequest):
    focus_area: Text(1, 100)
    label: Text(1, 255)
    prefix: Text(1, 20)
    active: bool = True


class GoalNameRow(BaseModel):
    id: int
    focus_area: str
    label: str
    prefix: str
    active: bool
    in_use: int


class GoalNamesResponse(BaseModel):
    goal_names: list[GoalNameRow]
    focus_areas: list[str]


def uses(session: Session, goal_name_id: int) -> int:
    """How many plan goals use this name."""
    return sum(session.scalar(select(func.count()).where(m.goal_name_id == goal_name_id)) for m in (PcgGoal, SagGoal, BrgGoal))


def row(session: Session, name: GoalName) -> GoalNameRow:
    return GoalNameRow(id=name.id, focus_area=name.focus_area, label=name.label, prefix=name.prefix, active=name.active, in_use=uses(session, name.id))


def load(session: Session, goal_name_id: int) -> GoalName:
    name = session.get(GoalName, goal_name_id)
    if name is None:
        raise HTTPException(404, "Goal name not found")
    return name


def check_prefix_free(session: Session, prefix: str, goal_name_id: int | None = None) -> None:
    """Prefixes are unique ignoring case."""
    clash = session.scalar(select(GoalName).where(func.lower(GoalName.prefix) == prefix.lower(), GoalName.id != goal_name_id))
    if clash:
        raise HTTPException(409, f"Prefix {clash.prefix} is already used by {clash.label}")


@router.get("/")
def list_goal_names(session: SessionDep) -> GoalNamesResponse:
    """Every goal name, and the focus areas to suggest."""
    names = session.scalars(select(GoalName).order_by(GoalName.focus_area, GoalName.prefix)).all()
    areas = sorted({PARENT_TRAINING, BEHAVIOR_CHANGE, *(n.focus_area for n in names)})
    return GoalNamesResponse(goal_names=[row(session, n) for n in names], focus_areas=areas)


@router.post("/", status_code=201)
def create_goal_name(body: GoalNameCreateRequest, session: SessionDep) -> GoalNameRow:
    check_prefix_free(session, body.prefix)
    name = GoalName(**body.model_dump())
    session.add(name)
    session.commit()
    return row(session, name)


@router.patch("/{goal_name_id}/")
def patch_goal_name(goal_name_id: int, body: GoalNamePatchRequest, session: SessionDep) -> GoalNameRow:
    name = load(session, goal_name_id)
    data = body.model_dump(exclude_unset=True)
    if "prefix" in data:
        check_prefix_free(session, data["prefix"], name.id)
    if data.get("focus_area", name.focus_area) != name.focus_area and uses(session, name.id):
        raise HTTPException(409, "This goal name is used on a plan, so its focus area cannot change")
    for field, value in data.items():
        setattr(name, field, value)
    session.commit()
    return row(session, name)


@router.delete("/{goal_name_id}/", status_code=204)
def delete_goal_name(goal_name_id: int, session: SessionDep) -> None:
    name = load(session, goal_name_id)
    count = uses(session, name.id)
    if count:
        raise HTTPException(409, f"Used by {count} goal(s) on plans. Turn it off instead.")
    session.delete(name)
    session.commit()
