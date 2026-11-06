"""Information page: read-only client, assignment and insurance data."""

from datetime import date

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.completion import CHECKERS, PageStatusResponse
from app.models import Client, ClientAssignment, ClientGuardian, ClientInsurance, Provider, TreatmentPlan
from app.routes.plan import SessionDep, load_plan

router = APIRouter(prefix="/api/v2/treatment_plans")


class ClientInfo(BaseModel):
    id: int
    first_name: str
    last_name: str
    date_of_birth: date | None
    sex: str | None


class ProviderInfo(BaseModel):
    provider_id: int
    display_name: str


class GuardianInfo(BaseModel):
    display_name: str
    role: str


class InsuranceInfo(BaseModel):
    payor_name: str
    member_id: str | None
    date_start: date | None
    date_end: date | None


class InsuranceSet(BaseModel):
    primary: InsuranceInfo | None = None
    secondary: InsuranceInfo | None = None
    tertiary: InsuranceInfo | None = None


class TreatmentPlanV3InformationResponse(BaseModel):
    client: ClientInfo
    parents_guardians: list[GuardianInfo]
    home_bcba: ProviderInfo | None
    substitute_bcbas: list[ProviderInfo]
    assigned_bts: list[ProviderInfo]
    insurance: InsuranceSet


def _providers(session: Session, client_id: int, role: str) -> list[ProviderInfo]:
    rows = session.execute(
        select(Provider.id, Provider.display_name)
        .join(ClientAssignment, ClientAssignment.provider_id == Provider.id)
        .where(ClientAssignment.client_id == client_id, ClientAssignment.role == role)
        .order_by(Provider.display_name)
    )
    return [ProviderInfo(provider_id=pid, display_name=name) for pid, name in rows]


@router.get("/{plan_id}/pages/information/")
def get_information(plan_id: int, session: SessionDep) -> TreatmentPlanV3InformationResponse:
    """Assemble the Information page."""
    plan = load_plan(session, plan_id)
    client = session.get_one(Client, plan.client_id)
    guardians = session.scalars(select(ClientGuardian).where(ClientGuardian.client_id == client.id))
    policies = session.scalars(select(ClientInsurance).where(ClientInsurance.client_id == client.id))
    home = _providers(session, client.id, "home_bcba")
    return TreatmentPlanV3InformationResponse(
        client=ClientInfo.model_validate(client, from_attributes=True),
        parents_guardians=[GuardianInfo.model_validate(g, from_attributes=True) for g in guardians],
        home_bcba=home[0] if home else None,
        substitute_bcbas=_providers(session, client.id, "substitute_bcba"),
        assigned_bts=_providers(session, client.id, "bt"),
        insurance=InsuranceSet(**{p.rank: InsuranceInfo.model_validate(p, from_attributes=True) for p in policies}),
    )


def information_status(session: Session, plan: TreatmentPlan) -> PageStatusResponse:
    """Information has no inputs, so it is always complete."""
    return PageStatusResponse(page="information", status="completed")


CHECKERS["information"] = information_status
