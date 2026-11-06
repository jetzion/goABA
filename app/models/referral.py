"""Referral page table."""

from datetime import date

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Referral(Base):
    """A referral row. Many per plan."""

    __tablename__ = "treatment_plan_v3_referral"

    id: Mapped[int] = mapped_column(primary_key=True)
    treatment_plan_id: Mapped[int] = mapped_column(ForeignKey("treatment_plan.id", ondelete="CASCADE"), index=True)
    referral_date: Mapped[date | None]
    provider_name: Mapped[str | None]
    diagnosis_tool: Mapped[str | None]
    city: Mapped[str | None]
    state: Mapped[str | None] = mapped_column(String(2))
