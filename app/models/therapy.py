"""Therapy page tables."""

from datetime import date
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Therapy(Base):
    """One therapy page row per plan, holding the no-historical-therapy flag."""

    __tablename__ = "treatment_plan_v3_therapy"

    id: Mapped[int] = mapped_column(primary_key=True)
    treatment_plan_id: Mapped[int] = mapped_column(ForeignKey("treatment_plan.id", ondelete="CASCADE"), unique=True)
    no_historical_therapy: Mapped[bool | None]

    rows: Mapped[list["TherapyRow"]] = relationship(cascade="all, delete-orphan", order_by="TherapyRow.id")


class TherapyRow(Base):
    """A historical therapy row."""

    __tablename__ = "treatment_plan_v3_therapy_row"

    id: Mapped[int] = mapped_column(primary_key=True)
    therapy_id: Mapped[int] = mapped_column(ForeignKey(Therapy.id, ondelete="CASCADE"), index=True)
    provider_name: Mapped[str | None]
    service_type: Mapped[str | None]
    phone_number: Mapped[str | None] = mapped_column(String(10))
    email: Mapped[str | None]
    start_date: Mapped[date | None]
    end_date: Mapped[date | None]
    hours: Mapped[Decimal | None] = mapped_column(Numeric(4, 1, asdecimal=True))
    frequency: Mapped[str | None]
    progress: Mapped[str | None]
    do_not_share_info_with_provider: Mapped[bool] = mapped_column(default=False)
    is_record_shared: Mapped[str | None]
