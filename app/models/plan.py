"""Client and treatment plan tables."""

from datetime import date, datetime

from sqlalchemy import ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Client(Base):
    """A client receiving treatment."""

    __tablename__ = "client"

    id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str]
    last_name: Mapped[str]
    date_of_birth: Mapped[date | None]
    sex: Mapped[str | None]


class TreatmentPlan(Base):
    """A treatment plan. Version 3 plans own the page tables."""

    __tablename__ = "treatment_plan"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("client.id"))
    provider_id: Mapped[int]
    status: Mapped[str] = mapped_column(default="draft")
    bay: Mapped[str | None]
    version: Mapped[int]
    has_medication: Mapped[bool | None]
    parent_treatment_plan_id: Mapped[int | None] = mapped_column(
        ForeignKey("treatment_plan.id", ondelete="SET NULL")
    )
    date_treatment_plan_started: Mapped[datetime] = mapped_column(server_default=func.now())
    signature: Mapped[str | None]
