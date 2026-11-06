"""Discharge page tables."""

from sqlalchemy import ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Discharge(Base):
    """One discharge row per plan."""

    __tablename__ = "treatment_plan_v3_discharge"

    id: Mapped[int] = mapped_column(primary_key=True)
    treatment_plan_id: Mapped[int] = mapped_column(ForeignKey("treatment_plan.id", ondelete="CASCADE"), unique=True)
    mastery_of_program_goals: Mapped[str | None] = mapped_column(Text)
    titration_plan: Mapped[str | None] = mapped_column(Text)
    readiness_to_step_down: Mapped[str | None] = mapped_column(Text)
    care_coordination: Mapped[str | None] = mapped_column(Text)

    reasons: Mapped[list["DischargeReason"]] = relationship(cascade="all, delete-orphan", order_by="DischargeReason.id")


class DischargeReason(Base):
    """A reason to decrease hours or discharge. Each reason appears once per discharge."""

    __tablename__ = "treatment_plan_v3_discharge_reason"
    __table_args__ = (UniqueConstraint("discharge_id", "reason"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    discharge_id: Mapped[int] = mapped_column(ForeignKey(Discharge.id, ondelete="CASCADE"))
    reason: Mapped[str]
    explanation: Mapped[str | None]
