"""Admin: client records shown on the Information page."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, HTTPException
from pydantic import AfterValidator, BaseModel
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models import Client, ClientAssignment, ClientGuardian, ClientInsurance, TreatmentPlan
from app.routes.plan import SessionDep
from app.rules import Body, Text

router = APIRouter(prefix="/api/v2/admin/clients")


def _not_future(value: date) -> date:
    if value > date.today():
        raise ValueError("cannot be in the future")
    return value


BirthDate = Annotated[date, AfterValidator(_not_future)]


class ClientPatchRequest(Body):
    first_name: Text(1, 100) = None  # type: ignore[assignment]  # omitted is allowed, null is not
    last_name: Text(1, 100) = None  # type: ignore[assignment]
    date_of_birth: BirthDate | None = None
    sex: Text(1, 50) | None = None


class ClientCreateRequest(ClientPatchRequest):
    first_name: Text(1, 100)
    last_name: Text(1, 100)


class ClientRow(BaseModel):
    id: int
    first_name: str
    last_name: str
    date_of_birth: date | None
    sex: str | None
    plan_count: int


def plan_count(session: Session, client_id: int) -> int:
    return session.scalar(select(func.count()).where(TreatmentPlan.client_id == client_id))


def row(session: Session, client: Client) -> ClientRow:
    return ClientRow(
        id=client.id, first_name=client.first_name, last_name=client.last_name,
        date_of_birth=client.date_of_birth, sex=client.sex, plan_count=plan_count(session, client.id),
    )


def load(session: Session, client_id: int) -> Client:
    client = session.get(Client, client_id)
    if client is None:
        raise HTTPException(404, "Client not found")
    return client


@router.get("/")
def list_clients(session: SessionDep) -> list[ClientRow]:
    clients = session.scalars(select(Client).order_by(Client.last_name, Client.first_name)).all()
    return [row(session, c) for c in clients]


@router.post("/", status_code=201)
def create_client(body: ClientCreateRequest, session: SessionDep) -> ClientRow:
    client = Client(**body.model_dump())
    session.add(client)
    session.commit()
    return row(session, client)


@router.patch("/{client_id}/")
def patch_client(client_id: int, body: ClientPatchRequest, session: SessionDep) -> ClientRow:
    client = load(session, client_id)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(client, field, value)
    session.commit()
    return row(session, client)


@router.delete("/{client_id}/", status_code=204)
def delete_client(client_id: int, session: SessionDep) -> None:
    """A client with plans is kept. Otherwise the client goes with their guardians, insurance and assignments."""
    client = load(session, client_id)
    count = plan_count(session, client.id)
    if count:
        raise HTTPException(409, f"This client has {count} treatment plan(s) and cannot be deleted")
    for model in (ClientGuardian, ClientInsurance, ClientAssignment):
        session.execute(delete(model).where(model.client_id == client.id))
    session.delete(client)
    session.commit()
