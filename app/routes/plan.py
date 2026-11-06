"""Plan list, create, read, page status and sign routes."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.completion import PageStatusResponse, all_statuses
from app.db import get_session
from app.enums import Bay
from app.models import Client, Provider, TreatmentPlan
from app.access import CurrentUser, action_access, edits_plan, plan_editor, plan_reader, sees_client, sees_plan
from app.rules import Body, Text

SIGNED = "signed"

router = APIRouter(prefix="/api/v2/treatment_plans")

SessionDep = Annotated[Session, Depends(get_session)]


class TreatmentPlanV3Create(BaseModel):
    """Body for creating a blank v3 plan."""

    model_config = ConfigDict(extra="forbid")

    client_id: int
    bay: Bay


class TreatmentPlanResponse(BaseModel):
    """A plan."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    client_id: int
    provider_id: int
    status: str
    bay: str | None
    version: int
    date_treatment_plan_started: datetime
    signature: str | None


class PlanReadResponse(TreatmentPlanResponse):
    """A plan as read by one user."""

    can_edit: bool


class SignRequest(Body):
    """The signer types their full name."""

    signature: Text(2, 255)


def load_plan(session: Session, plan_id: int) -> TreatmentPlan:
    """Load a v3 plan or raise 404/409."""
    plan = session.get(TreatmentPlan, plan_id)
    if plan is None:
        raise HTTPException(404, "Treatment plan not found")
    if plan.version != 3:
        raise HTTPException(409, "Treatment plan is not version 3")
    return plan


def load_plan_for_write(session: Session, plan_id: int) -> TreatmentPlan:
    """Load a v3 plan that can still be edited, or raise 404/409."""
    plan = load_plan(session, plan_id)
    if plan.status == SIGNED:
        raise HTTPException(409, "Treatment plan is signed and read-only")
    return plan


class PlanListItem(BaseModel):
    """One row of the plans list."""

    id: int
    client_id: int
    client_name: str
    bay: str | None
    status: str
    owner: str | None
    date_treatment_plan_started: datetime
    signature: str | None


class ClientChoice(BaseModel):
    id: int
    name: str


class PlanListResponse(BaseModel):
    plans: list[PlanListItem]
    clients: list[ClientChoice]
    bays: list[str]


@router.get("/")
def list_plans(session: SessionDep, user: CurrentUser) -> PlanListResponse:
    """The v3 plans the user can see, newest first, with the clients and bays a new plan can use."""
    rows = session.execute(
        select(TreatmentPlan, Client, Provider.display_name)
        .join(Client, Client.id == TreatmentPlan.client_id)
        .outerjoin(Provider, Provider.id == TreatmentPlan.provider_id)
        .where(TreatmentPlan.version == 3)
        .order_by(TreatmentPlan.id.desc())
    ).all()
    plans = [
        PlanListItem(
            id=plan.id, client_id=client.id, client_name=f"{client.first_name} {client.last_name}", bay=plan.bay,
            status=plan.status, owner=owner, date_treatment_plan_started=plan.date_treatment_plan_started, signature=plan.signature,
        )
        for plan, client, owner in rows
        if sees_plan(session, user, plan)
    ]
    clients = [c for c in session.scalars(select(Client).order_by(Client.last_name, Client.first_name)) if sees_client(session, user, c.id)]
    return PlanListResponse(
        plans=plans,
        clients=[ClientChoice(id=c.id, name=f"{c.first_name} {c.last_name}") for c in clients],
        bays=[b.value for b in Bay],
    )


@router.post("/", status_code=201, dependencies=[action_access("create_plan")])
def create_plan(body: TreatmentPlanV3Create, session: SessionDep, user: CurrentUser) -> TreatmentPlanResponse:
    """Create a blank v3 plan owned by the signed-in provider."""
    if session.get(Client, body.client_id) is None:
        raise HTTPException(404, "Client not found")
    if user.provider_id is None:
        raise HTTPException(422, "Only a provider can own a treatment plan")
    if not sees_client(session, user, body.client_id):
        raise HTTPException(403, "You do not have access to this client")
    plan = TreatmentPlan(
        client_id=body.client_id, bay=body.bay, version=3, provider_id=user.provider_id
    )
    session.add(plan)
    session.commit()
    return TreatmentPlanResponse.model_validate(plan)


@router.get("/{plan_id}/", dependencies=[Depends(plan_reader)])
def get_plan(plan_id: int, session: SessionDep, user: CurrentUser) -> PlanReadResponse:
    """Read one plan, and whether the caller may edit it."""
    plan = load_plan(session, plan_id)
    return PlanReadResponse(**TreatmentPlanResponse.model_validate(plan).model_dump(), can_edit=edits_plan(session, user, plan))


@router.get("/{plan_id}/pages/", dependencies=[Depends(plan_reader)])
def get_page_statuses(plan_id: int, session: SessionDep) -> list[PageStatusResponse]:
    """Status of all 13 pages."""
    return all_statuses(session, load_plan(session, plan_id))


@router.post("/{plan_id}/sign/", dependencies=[action_access("sign_plan"), Depends(plan_editor)])
def sign_plan(plan_id: int, body: SignRequest, session: SessionDep) -> TreatmentPlanResponse:
    """Sign a plan whose pages are all complete. A signed plan is read-only."""
    plan = load_plan_for_write(session, plan_id)
    unfinished = [s.page for s in all_statuses(session, plan) if s.status != "completed"]
    if unfinished:
        raise HTTPException(422, f"Complete every page before signing. Not complete: {', '.join(unfinished)}")
    plan.status = SIGNED
    plan.signature = body.signature
    session.commit()
    return TreatmentPlanResponse.model_validate(plan)
