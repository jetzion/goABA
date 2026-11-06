"""The change history (audit log)."""

from datetime import datetime

from sqlalchemy import JSON, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class AuditEvent(Base):
    """One change to one record. User and record are copied as plain values so the log outlives them."""

    __tablename__ = "audit_event"

    id: Mapped[int] = mapped_column(primary_key=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    user_id: Mapped[int | None]
    user_name: Mapped[str]
    action: Mapped[str]
    record_type: Mapped[str] = mapped_column(index=True)
    record_id: Mapped[int | None]
    label: Mapped[str]
    changes: Mapped[dict] = mapped_column(JSON, default=dict)
