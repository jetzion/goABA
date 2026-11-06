"""Admin: clinical assignments of providers to clients.

They feed the Information care team and the Treatment bay 3 text, and (step 20.3) decide who sees and edits a client's plans.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Client, ClientAssignment, Provider
from app.routes.plan import SessionDep
from app.rules import Body, OneOf

router = APIRouter(prefix="/api/v2/admin/assignments")

ROLES = {"home_bcba": "Home BCBA", "substitute_bcba": "Substitute BCBA", "bt": "BT"}
HOME = "home_bcba"


class AssignmentCreateRequest(Body):
    client_id: int
    provider_id: int
    role: OneOf(tuple(ROLES))


class AssignmentPatchRequest(Body):
    role: OneOf(tuple(ROLES))


class AssignmentRow(BaseModel):
    id: int
    provider_id: int
    provider: str
    provider_active: bool
    role: str


class ClientAssignments(BaseModel):
    id: int
    name: str
    assignments: list[AssignmentRow]


class Choice(BaseModel):
    id: int
    name: str


class RoleChoice(BaseModel):
    value: str
    label: str


class AssignmentsResponse(BaseModel):
    clients: list[ClientAssignments]
    providers: list[Choice]
    roles: list[RoleChoice]


def assignment_row(session: Session, assignment: ClientAssignment) -> AssignmentRow:
    provider = session.get_one(Provider, assignment.provider_id)
    return AssignmentRow(id=assignment.id, provider_id=provider.id, provider=provider.display_name, provider_active=provider.active, role=assignment.role)


def load(session: Session, assignment_id: int) -> ClientAssignment:
    assignment = session.get(ClientAssignment, assignment_id)
    if assignment is None:
        raise HTTPException(404, "Assignment not found")
    return assignment


def check_one_home(session: Session, client_id: int, role: str, assignment_id: int | None = None) -> None:
    """A client has at most one Home BCBA."""
    if role != HOME:
        return
    other = session.scalar(select(ClientAssignment).where(
        ClientAssignment.client_id == client_id, ClientAssignment.role == HOME, ClientAssignment.id != assignment_id))
    if other:
        name = session.get_one(Provider, other.provider_id).display_name
        raise HTTPException(409, f"{name} is already the Home BCBA. Change that assignment first.")


@router.get("/")
def list_assignments(session: SessionDep) -> AssignmentsResponse:
    """Every client with their assignments, the active providers to assign, and the roles."""
    clients = session.scalars(select(Client).order_by(Client.last_name, Client.first_name)).all()
    order = list(ROLES)
    result = []
    for client in clients:
        rows = [assignment_row(session, a) for a in session.scalars(select(ClientAssignment).where(ClientAssignment.client_id == client.id))]
        rows.sort(key=lambda r: (order.index(r.role) if r.role in order else len(order), r.provider))
        result.append(ClientAssignments(id=client.id, name=f"{client.first_name} {client.last_name}", assignments=rows))
    providers = session.scalars(select(Provider).where(Provider.active).order_by(Provider.display_name)).all()
    return AssignmentsResponse(
        clients=result,
        providers=[Choice(id=p.id, name=p.display_name) for p in providers],
        roles=[RoleChoice(value=v, label=label) for v, label in ROLES.items()],
    )


@router.post("/", status_code=201)
def create_assignment(body: AssignmentCreateRequest, session: SessionDep) -> AssignmentRow:
    """Assign an active provider to a client once, in one role."""
    if session.get(Client, body.client_id) is None:
        raise HTTPException(422, "Unknown client")
    provider = session.get(Provider, body.provider_id)
    if provider is None:
        raise HTTPException(422, "Unknown provider")
    if not provider.active:
        raise HTTPException(422, "That provider is turned off")
    if session.scalar(select(ClientAssignment).where(
            ClientAssignment.client_id == body.client_id, ClientAssignment.provider_id == body.provider_id)):
        raise HTTPException(409, f"{provider.display_name} is already assigned to this client")
    check_one_home(session, body.client_id, body.role)
    assignment = ClientAssignment(**body.model_dump())
    session.add(assignment)
    session.commit()
    return assignment_row(session, assignment)


@router.patch("/{assignment_id}/")
def change_role(assignment_id: int, body: AssignmentPatchRequest, session: SessionDep) -> AssignmentRow:
    assignment = load(session, assignment_id)
    check_one_home(session, assignment.client_id, body.role, assignment.id)
    assignment.role = body.role
    session.commit()
    return assignment_row(session, assignment)


@router.delete("/{assignment_id}/", status_code=204)
def delete_assignment(assignment_id: int, session: SessionDep) -> None:
    session.delete(load(session, assignment_id))
    session.commit()
