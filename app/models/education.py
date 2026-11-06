"""Education page table."""

from datetime import date
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Education(Base):
    """One education row per plan."""

    __tablename__ = "treatment_plan_v3_education"

    id: Mapped[int] = mapped_column(primary_key=True)
    treatment_plan_id: Mapped[int] = mapped_column(ForeignKey("treatment_plan.id", ondelete="CASCADE"), unique=True)
    not_attending_school: Mapped[bool] = mapped_column(default=False)
    education_setting: Mapped[str | None]
    number_of_hours_per_week: Mapped[Decimal | None] = mapped_column(Numeric(4, 1))
    school_name: Mapped[str | None]
    school_phone_number: Mapped[str | None] = mapped_column(String(10))
    education_description: Mapped[str | None] = mapped_column(Text)
    focus_area_description: Mapped[str | None] = mapped_column(Text)
    evaluation_status: Mapped[str | None]
    evaluation_date: Mapped[date | None]
    iep_or_504_in_place: Mapped[str | None]
    education_support: Mapped[str | None] = mapped_column(Text)
    classroom_setting: Mapped[str | None]
    attitude_towards_school: Mapped[str | None]
