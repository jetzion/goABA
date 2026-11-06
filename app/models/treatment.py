"""Treatment page table. Units are hours times 4 and are not stored."""

from datetime import date

from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Treatment(Base):
    """One treatment row per plan."""

    __tablename__ = "treatment_plan_v3_treatment"

    id: Mapped[int] = mapped_column(primary_key=True)
    treatment_plan_id: Mapped[int] = mapped_column(ForeignKey("treatment_plan.id", ondelete="CASCADE"), unique=True)
    recommendations_explanation: Mapped[str | None] = mapped_column(Text)
    proposed_start_date: Mapped[date | None]
    duration_in_months: Mapped[int | None]
    assessment_97151_hours: Mapped[int | None]
    assessment_97151_per: Mapped[str | None]
    assessment_97152_hours: Mapped[int | None]
    assessment_97152_per: Mapped[str | None]
    direct_therapy_97153_hours: Mapped[int | None]
    direct_therapy_97153_per: Mapped[str | None]
    protocol_modification_97155_hours: Mapped[int | None]
    protocol_modification_97155_per: Mapped[str | None]
    parent_training_97156_hours: Mapped[int | None]
    parent_training_97156_per: Mapped[str | None]
    group_parent_training_97157_hours: Mapped[int | None]
    group_parent_training_97157_per: Mapped[str | None]
    care_coordination_99366_hours: Mapped[int | None]
    care_coordination_99366_per: Mapped[str | None]
