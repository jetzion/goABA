"""Admin: read the change history. There are no routes to change it."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import select

from app.audit import RECORD_TYPES
from app.models import AuditEvent
from app.routes.plan import SessionDep

router = APIRouter(prefix="/api/v2/admin/history")

PAGE_SIZE = 100


class EventRow(BaseModel):
    id: int
    at: datetime
    user_name: str
    action: str
    record_type: str
    record_id: int | None
    label: str
    changes: dict[str, list]


class HistoryResponse(BaseModel):
    events: list[EventRow]
    record_types: list[str]
    more: bool


@router.get("/")
def list_history(
    session: SessionDep,
    record_type: str | None = None,
    before: int | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = PAGE_SIZE,
) -> HistoryResponse:
    """Newest first. `before` (an event id) pages to older events."""
    query = select(AuditEvent).order_by(AuditEvent.id.desc()).limit(limit + 1)
    if record_type:
        query = query.where(AuditEvent.record_type == record_type)
    if before:
        query = query.where(AuditEvent.id < before)
    events = session.scalars(query).all()
    return HistoryResponse(
        events=[EventRow.model_validate(e, from_attributes=True) for e in events[:limit]],
        record_types=sorted(set(RECORD_TYPES.values())),
        more=len(events) > limit,
    )
