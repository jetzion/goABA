"""Admin: providers, the clinicians who own plans and are assigned to clients."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import AppUser, ClientAssignment, Provider, TreatmentPlan
from app.routes.plan import SessionDep
from app.rules import Body, Text

router = APIRouter(prefix="/api/v2/admin/providers")


class ProviderPatchRequest(Body):
    display_name: Text(1, 255) = None  # type: ignore[assignment]  # omitted is allowed, null is not
    active: bool = None  # type: ignore[assignment]


class ProviderCreateRequest(ProviderPatchRequest):
    display_name: Text(1, 255)
    active: bool = True


class ProviderRow(BaseModel):
    id: int
    display_name: str
    active: bool
    user: str | None
    assignments: int
    plans: int


def count(session: Session, column, provider_id: int) -> int:
    return session.scalar(select(func.count()).where(column == provider_id))


def row(session: Session, provider: Provider) -> ProviderRow:
    user = session.scalar(select(AppUser.display_name).where(AppUser.provider_id == provider.id))
    return ProviderRow(
        id=provider.id, display_name=provider.display_name, active=provider.active, user=user,
        assignments=count(session, ClientAssignment.provider_id, provider.id),
        plans=count(session, TreatmentPlan.provider_id, provider.id),
    )


def load(session: Session, provider_id: int) -> Provider:
    provider = session.get(Provider, provider_id)
    if provider is None:
        raise HTTPException(404, "Provider not found")
    return provider


@router.get("/")
def list_providers(session: SessionDep) -> list[ProviderRow]:
    providers = session.scalars(select(Provider).order_by(Provider.active.desc(), Provider.display_name)).all()
    return [row(session, p) for p in providers]


@router.post("/", status_code=201)
def create_provider(body: ProviderCreateRequest, session: SessionDep) -> ProviderRow:
    provider = Provider(**body.model_dump())
    session.add(provider)
    session.commit()
    return row(session, provider)


@router.patch("/{provider_id}/")
def patch_provider(provider_id: int, body: ProviderPatchRequest, session: SessionDep) -> ProviderRow:
    provider = load(session, provider_id)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(provider, field, value)
    session.commit()
    return row(session, provider)


@router.delete("/{provider_id}/", status_code=204)
def delete_provider(provider_id: int, session: SessionDep) -> None:
    """Only a provider with no user, assignments or plans can be deleted. Otherwise turn it off."""
    provider = load(session, provider_id)
    used = row(session, provider)
    if used.user or used.assignments or used.plans:
        raise HTTPException(409, "This provider is linked to a user, assigned to clients or owns plans. Turn it off instead.")
    session.delete(provider)
    session.commit()
