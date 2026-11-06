"""Medication page table. The no-medication flag lives on treatment_plan.has_medication."""

from datetime import date

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Medication(Base):
    """A medication row. Many per plan."""

    __tablename__ = "treatment_plan_v3_medication"

    id: Mapped[int] = mapped_column(primary_key=True)
    treatment_plan_id: Mapped[int] = mapped_column(ForeignKey("treatment_plan.id", ondelete="CASCADE"), index=True)
    medication_name: Mapped[str | None]
    dosage: Mapped[str | None]
    start_date: Mapped[date | None]
    physician_name: Mapped[str | None]
    reason: Mapped[str | None]
