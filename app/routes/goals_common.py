"""Rules shared by PCG, SAG and BRG goals: methods, criteria, targets and stage history."""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from typing import Annotated

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field, create_model
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.completion import PageError
from app.enums import DATA_COLLECTION_METHODS, DURATION_AGGREGATIONS, MASTERY_DIRECTIONS, MEASUREMENT_UNITS, TARGET_TIMEFRAMES
from app.models import GoalName
from app.routes.common import apply_patch, get_owned
from app.routes.plan import SessionDep, load_plan_for_write
from app.rules import Body, GoalMonth, OneOf, RichText, Text, visible_length

METHOD_FIELDS = {
    "Duration": ("duration_unit",),
    "Instances": (),
    "Percentage": ("opportunities",),
    "Rate": ("rate_interval", "rate_unit"),
}
CRITERIA_PARTS = {
    "Duration": ("direction", "aggregation", "to", "sessions"),
    "Instances": ("direction", "to", "sessions"),
    "Percentage": ("responses", "sessions"),
    "Rate": ("direction", "to", "sessions"),
}
TARGET_METHOD_FIELDS = ("duration_unit", "opportunities", "rate_interval", "rate_unit")
PAUSED = ("On-hold", "Discontinued")
LONG_TEXT_MIN = 60

Level = Annotated[float, Field(ge=0, le=100)]
Opportunities = Annotated[int, Field(ge=1, le=99)]
RateInterval = Annotated[int, Field(ge=1, le=60)]
Sessions = Annotated[int, Field(ge=1, le=100)]
Responses = Annotated[int, Field(ge=1, le=99)]
NonNegative = Annotated[float, Field(ge=0)]
GoalNameId = Annotated[int, Field(gt=0)]


@dataclass
class GoalKind:
    """What differs between goal sections."""

    page: str
    blocks: tuple[str, ...]
    default_sessions: dict[str, int]
    has_opportunities: bool = True
    has_responses: bool = True

    def owned_fields(self, method: str | None) -> set[str]:
        """Method and criteria columns that belong to a method."""
        if method is None:
            return set()
        owned = {f for f in METHOD_FIELDS[method] if f != "opportunities" or self.has_opportunities}
        for block in self.blocks:
            owned |= {f"{block}_{part}" for part in CRITERIA_PARTS[method] if part != "responses" or self.has_responses}
        return owned

    def all_method_fields(self) -> set[str]:
        return set().union(*(self.owned_fields(m) for m in METHOD_FIELDS))


def check_goal_name(session: Session, goal_name_id: int, allowed: Callable[[str], bool]) -> GoalName:
    """The goal name must be active and in an allowed focus area."""
    goal_name = session.get(GoalName, goal_name_id)
    if goal_name is None or not goal_name.active or not allowed(goal_name.focus_area):
        raise HTTPException(422, "goal_name_id must be an active goal in this section's focus area")
    return goal_name


def apply_goal_patch(goal: object, body: BaseModel, kind: GoalKind) -> None:
    """Apply a goal patch with method rules: foreign fields rejected, defaults on method change.

    Only columns are copied; section-specific fields such as linked goal ids are handled by the caller.
    """
    data = body.model_dump(exclude_unset=True)
    method = data.get("data_collection_method", goal.data_collection_method)
    owned = kind.owned_fields(method)
    foreign = [f for f, v in data.items() if f in kind.all_method_fields() and v is not None and f not in owned]
    if foreign:
        raise HTTPException(422, f"{foreign[0]} does not belong to the {method or 'unselected'} method")
    changed = "data_collection_method" in data and data["data_collection_method"] != goal.data_collection_method
    for name, value in data.items():
        if hasattr(type(goal), name):
            setattr(goal, name, value)
    if changed:
        for name in kind.all_method_fields() - owned:
            setattr(goal, name, None)
        apply_defaults(goal, kind)
    check_cross_fields(goal, kind)


def apply_defaults(goal: object, kind: GoalKind) -> None:
    """Defaults when a method is chosen: sessions per block, increase, average, interval 1."""
    method = goal.data_collection_method
    parts = CRITERIA_PARTS[method]
    for block in kind.blocks:
        if getattr(goal, f"{block}_sessions") is None:
            setattr(goal, f"{block}_sessions", kind.default_sessions[block])
        if "direction" in parts and getattr(goal, f"{block}_direction") is None:
            setattr(goal, f"{block}_direction", "increase")
        if "aggregation" in parts and getattr(goal, f"{block}_aggregation") is None:
            setattr(goal, f"{block}_aggregation", "average")
    if method == "Rate" and goal.rate_interval is None:
        goal.rate_interval = 1


def check_cross_fields(row: object, kind: GoalKind | None = None) -> None:
    """Rate interval fits its unit; responses fit the opportunity count."""
    if row.rate_unit == "Hours" and (row.rate_interval or 0) > 4:
        raise HTTPException(422, "rate_interval must be 1 to 4 for Hours")
    if kind is None or not kind.has_responses:
        return
    for block in kind.blocks:
        responses = getattr(row, f"{block}_responses")
        if responses is not None and row.opportunities is not None and responses > row.opportunities:
            raise HTTPException(422, f"{block}_responses cannot be more than opportunities")


def err(kind_page: str, row: str, field_name: str, row_id: int, message: str) -> PageError:
    return PageError(field=f"{kind_page}.{row}.{field_name}", row_id=row_id, message=message)


def missing(page: str, row: str, obj: object, fields: list[str] | set[str]) -> list[PageError]:
    return [err(page, row, f, obj.id, "This field is required") for f in sorted(fields) if getattr(obj, f) is None]


def goal_measurement_errors(goal: object, kind: GoalKind) -> list[PageError]:
    """Method, method fields, criteria, and mastery target versus baseline."""
    errors = missing(kind.page, "goal", goal, ["data_collection_method", "baseline_date", "baseline_level", "current_level", "expected_mastery_date"])
    if visible_length(goal.goal_description) == 0:
        errors.append(err(kind.page, "goal", "goal_description", goal.id, "This field is required"))
    method = goal.data_collection_method
    if method is None:
        return errors
    errors += missing(kind.page, "goal", goal, kind.owned_fields(method))
    if method == "Percentage" or goal.baseline_level is None:
        return errors
    for block in kind.blocks:
        direction, target = getattr(goal, f"{block}_direction"), getattr(goal, f"{block}_to")
        if target is None or direction is None:
            continue
        if direction == "increase" and target <= goal.baseline_level:
            errors.append(err(kind.page, "goal", f"{block}_to", goal.id, "Must be above the baseline to increase"))
        if direction == "decrease" and target >= goal.baseline_level:
            errors.append(err(kind.page, "goal", f"{block}_to", goal.id, "Must be below the baseline to decrease"))
    return errors


# Targets and stage history


@dataclass
class TargetKind:
    """What differs between target sections."""

    page: str
    name_min: int
    transitions: dict[str, tuple[str, ...]]
    same_day: tuple[str, str]
    target_model: type
    stage_model: type
    patch_model: type[BaseModel]
    system_only: set[tuple[str, str]] = field(default_factory=set)


class TargetPatch(Body):
    target_name: Text(0, 500) | None = None
    timeframe: OneOf(TARGET_TIMEFRAMES) | None = None
    baseline_date: date | None = None
    baseline_level: Level | None = None
    duration_unit: OneOf(MEASUREMENT_UNITS) | None = None
    rate_interval: RateInterval | None = None
    rate_unit: OneOf(MEASUREMENT_UNITS) | None = None
    description: RichText() | None = None
    instructions: Text(0, 50_000) | None = None


class TargetPatchWithOpportunities(TargetPatch):
    opportunities: Opportunities | None = None


class StageCreate(Body):
    stage: str
    stage_date: date
    reason: Text(0, 500) | None = None


class StageDatePatch(Body):
    stage_date: date


class StageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    stage: str
    stage_date: date
    reason: str | None
    order: int


class TargetResponse(TargetPatchWithOpportunities):
    model_config = ConfigDict(extra="ignore")

    id: int
    current_stage: str
    allowed_next_stages: list[str]
    stage_history: list[StageResponse]


def target_response(target: object, kind: "TargetKind") -> TargetResponse:
    values = {f: getattr(target, f, None) for f in TargetPatchWithOpportunities.model_fields}
    return TargetResponse(
        id=target.id,
        current_stage=target.stages[-1].stage,
        allowed_next_stages=sorted(allowed_next(kind, target.stages)),
        stage_history=[StageResponse.model_validate(s) for s in target.stages],
        **values,
    )


def prior_active(stages: list) -> str:
    return next(s.stage for s in reversed(stages) if s.stage not in PAUSED)


def allowed_next(kind: TargetKind, stages: list) -> set[str]:
    """Stages a user may move to from the current one."""
    last = stages[-1].stage
    if last == "On-hold":
        return {prior_active(stages), "Discontinued"}
    if last == "Discontinued":
        return {prior_active(stages)}
    return {s for s in kind.transitions.get(last, ()) if (last, s) not in kind.system_only}


def check_dates(kind: TargetKind, history: list[tuple[str, date]]) -> None:
    """Dates never move backward. A same-day step is allowed only for the first listed step out of New."""
    for i in range(1, len(history)):
        (prev_stage, prev_date), (stage, stage_date) = history[i - 1], history[i]
        if stage_date < prev_date:
            raise HTTPException(422, "Stage dates cannot move backward")
        if stage_date == prev_date and not (i == 1 and (prev_stage, stage) == kind.same_day):
            raise HTTPException(422, "This stage change cannot happen on the same day as the previous one")


def target_errors(kind: TargetKind, goal_method: str | None, target: object) -> list[PageError]:
    errors = missing(kind.page, "target", target, ["timeframe", "baseline_date", "baseline_level"])
    if len(target.target_name or "") < kind.name_min:
        errors.append(err(kind.page, "target", "target_name", target.id, f"Enter at least {kind.name_min} characters"))
    if goal_method:
        errors += missing(kind.page, "target", target, [f for f in METHOD_FIELDS[goal_method] if hasattr(target, f)])
    if visible_length(target.description) < LONG_TEXT_MIN:
        errors.append(err(kind.page, "target", "description", target.id, f"Enter at least {LONG_TEXT_MIN} characters"))
    if len(target.instructions or "") < LONG_TEXT_MIN:
        errors.append(err(kind.page, "target", "instructions", target.id, f"Enter at least {LONG_TEXT_MIN} characters"))
    if not target.stages or target.stages[0].stage != "New":
        errors.append(err(kind.page, "target", "stage_history", target.id, "Stage history must start at New"))
    return errors


def add_target_routes(router: APIRouter, kind: TargetKind, load_goal: Callable) -> None:
    """Target and stage-history routes under /goals/{goal_id}/targets/."""
    Patch = kind.patch_model

    def load_target(session: Session, plan_id: int, goal_id: int, target_id: int):
        load_goal(session, plan_id, goal_id)
        return get_owned(session, kind.target_model, target_id, "goal_id", goal_id)

    def check_method_fields(goal, body: BaseModel) -> None:
        owned = set(METHOD_FIELDS[goal.data_collection_method]) if goal.data_collection_method else set()
        sent = {f for f, v in body.model_dump(exclude_unset=True).items() if f in TARGET_METHOD_FIELDS and v is not None}
        if sent - owned:
            raise HTTPException(422, f"{sorted(sent - owned)[0]} does not match the goal's method")

    @router.post("/goals/{goal_id}/targets/", status_code=201)
    def create_target(plan_id: int, goal_id: int, body: Patch, session: SessionDep) -> TargetResponse:
        load_plan_for_write(session, plan_id)
        goal = load_goal(session, plan_id, goal_id)
        check_method_fields(goal, body)
        target = kind.target_model(goal_id=goal.id, **body.model_dump())
        target.stages.append(kind.stage_model(stage="New", stage_date=date.today(), order=0))
        check_cross_fields(target)
        session.add(target)
        session.commit()
        return target_response(target, kind)

    @router.patch("/goals/{goal_id}/targets/{target_id}/")
    def patch_target(plan_id: int, goal_id: int, target_id: int, body: Patch, session: SessionDep) -> TargetResponse:
        load_plan_for_write(session, plan_id)
        target = load_target(session, plan_id, goal_id, target_id)
        check_method_fields(load_goal(session, plan_id, goal_id), body)
        apply_patch(target, body)
        check_cross_fields(target)
        session.commit()
        return target_response(target, kind)

    @router.delete("/goals/{goal_id}/targets/{target_id}/", status_code=204)
    def delete_target(plan_id: int, goal_id: int, target_id: int, session: SessionDep) -> None:
        load_plan_for_write(session, plan_id)
        session.delete(load_target(session, plan_id, goal_id, target_id))
        session.commit()

    @router.post("/goals/{goal_id}/targets/{target_id}/stage-history/", status_code=201)
    def add_stage(plan_id: int, goal_id: int, target_id: int, body: StageCreate, session: SessionDep) -> TargetResponse:
        load_plan_for_write(session, plan_id)
        target = load_target(session, plan_id, goal_id, target_id)
        last = target.stages[-1].stage
        if (last, body.stage) in kind.system_only:
            raise HTTPException(422, f"{last} to {body.stage} happens automatically and cannot be requested")
        if body.stage not in allowed_next(kind, target.stages):
            raise HTTPException(422, f"A target cannot move from {last} to {body.stage}")
        check_dates(kind, [(s.stage, s.stage_date) for s in target.stages] + [(body.stage, body.stage_date)])
        target.stages.append(kind.stage_model(stage=body.stage, stage_date=body.stage_date, reason=body.reason, order=len(target.stages)))
        session.commit()
        return target_response(target, kind)

    @router.patch("/goals/{goal_id}/targets/{target_id}/stage-history/{stage_id}/")
    def patch_stage(plan_id: int, goal_id: int, target_id: int, stage_id: int, body: StageDatePatch, session: SessionDep) -> TargetResponse:
        load_plan_for_write(session, plan_id)
        target = load_target(session, plan_id, goal_id, target_id)
        stage = get_owned(session, kind.stage_model, stage_id, "target_id", target.id)
        check_dates(kind, [(s.stage, body.stage_date if s.id == stage.id else s.stage_date) for s in target.stages])
        stage.stage_date = body.stage_date
        session.commit()
        return target_response(target, kind)

    @router.delete("/goals/{goal_id}/targets/{target_id}/stage-history/{stage_id}/", status_code=204)
    def delete_stage(plan_id: int, goal_id: int, target_id: int, stage_id: int, session: SessionDep) -> None:
        load_plan_for_write(session, plan_id)
        target = load_target(session, plan_id, goal_id, target_id)
        stage = get_owned(session, kind.stage_model, stage_id, "target_id", target.id)
        if stage is not target.stages[-1] or stage.order == 0:
            raise HTTPException(422, "Only the latest stage can be removed, and never the first New stage")
        session.delete(stage)
        session.commit()


def goal_criteria_fields(kind: GoalKind) -> dict[str, object]:
    """Pydantic field definitions for every criteria column of a goal kind."""
    types = {"direction": OneOf(MASTERY_DIRECTIONS), "aggregation": OneOf(DURATION_AGGREGATIONS), "to": NonNegative, "responses": Responses, "sessions": Sessions}
    fields = {}
    for block in kind.blocks:
        for part, annotation in types.items():
            if part == "responses" and not kind.has_responses:
                continue
            fields[f"{block}_{part}"] = (annotation | None, None)
    return fields


class GoalBase(Body):
    """Fields every goal accepts. goal_name_id and the method can be omitted but never set to null."""

    goal_name_id: GoalNameId = None  # type: ignore[assignment]
    data_collection_method: OneOf(DATA_COLLECTION_METHODS) = None  # type: ignore[assignment]
    duration_unit: OneOf(MEASUREMENT_UNITS) | None = None
    baseline_date: date | None = None
    baseline_level: Level | None = None
    rate_interval: RateInterval | None = None
    rate_unit: OneOf(MEASUREMENT_UNITS) | None = None
    current_level: Level | None = None
    expected_mastery_date: GoalMonth | None = None
    goal_description: RichText() | None = None


def goal_patch_model(name: str, base: type[BaseModel], kind: GoalKind) -> type[BaseModel]:
    """The goal patch body: the base fields plus the kind's criteria columns."""
    return create_model(name, __base__=base, **goal_criteria_fields(kind))


def goal_values(goal: object, patch_model: type[BaseModel]) -> dict[str, object]:
    """Stored goal columns named in the patch model."""
    return {f: getattr(goal, f) for f in patch_model.model_fields if hasattr(type(goal), f)}


def base_goal_response(goal: object, patch_model: type[BaseModel], target_kind: TargetKind) -> dict[str, object]:
    return {
        "id": goal.id,
        **goal_values(goal, patch_model),
        "goal_name": goal.goal_name.label,
        "prefix": goal.goal_name.prefix,
        "targets": [target_response(t, target_kind).model_dump(mode="json") for t in goal.targets],
    }


def add_goal_routes(
    router: APIRouter,
    *,
    model: type,
    kind: GoalKind,
    patch_model: type[BaseModel],
    name_allowed: Callable[[str], bool],
    respond: Callable[[Session, object], dict],
    before_save: Callable[[Session, int, object, BaseModel], None] | None = None,
) -> Callable:
    """Goal create, patch and delete routes. Returns the goal loader for target routes."""
    create_body = create_model(f"{model.__name__}CreateRequest", __base__=patch_model, goal_name_id=(GoalNameId, ...))

    def load_goal(session: Session, plan_id: int, goal_id: int):
        return get_owned(session, model, goal_id, "treatment_plan_id", plan_id)

    def save(session: Session, plan_id: int, goal: object, body: BaseModel) -> dict:
        if "goal_name_id" in body.model_fields_set:
            check_goal_name(session, body.goal_name_id, name_allowed)
        apply_goal_patch(goal, body, kind)
        if before_save:
            before_save(session, plan_id, goal, body)
        session.add(goal)
        try:
            session.commit()
        except IntegrityError:
            raise HTTPException(409, "This goal is already on the plan")
        return respond(session, goal)

    @router.post("/goals/", status_code=201)
    def create_goal(plan_id: int, body: create_body, session: SessionDep) -> dict:
        load_plan_for_write(session, plan_id)
        return save(session, plan_id, model(treatment_plan_id=plan_id), body)

    @router.patch("/goals/{goal_id}/")
    def patch_goal(plan_id: int, goal_id: int, body: patch_model, session: SessionDep) -> dict:
        load_plan_for_write(session, plan_id)
        return save(session, plan_id, load_goal(session, plan_id, goal_id), body)

    @router.delete("/goals/{goal_id}/", status_code=204)
    def delete_goal(plan_id: int, goal_id: int, session: SessionDep) -> None:
        load_plan_for_write(session, plan_id)
        session.delete(load_goal(session, plan_id, goal_id))
        session.commit()

    return load_goal
