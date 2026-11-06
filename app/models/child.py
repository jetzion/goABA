"""Child page tables."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Child(Base):
    """One child row per plan."""

    __tablename__ = "treatment_plan_v3_child"

    id: Mapped[int] = mapped_column(primary_key=True)
    treatment_plan_id: Mapped[int] = mapped_column(ForeignKey("treatment_plan.id", ondelete="CASCADE"), unique=True)
    child_behavior_issues: Mapped[str | None] = mapped_column(Text)

    backgrounds: Mapped[list["ChildBackground"]] = relationship(cascade="all, delete-orphan", order_by="ChildBackground.id")
    schedule: Mapped[list["ChildSchedule"]] = relationship(cascade="all, delete-orphan", order_by="ChildSchedule.id")


class ChildBackground(Base):
    """One item in a background list. A description cannot repeat inside its type."""

    __tablename__ = "treatment_plan_v3_child_background"
    __table_args__ = (UniqueConstraint("child_id", "background_type", "background_description"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    child_id: Mapped[int] = mapped_column(ForeignKey(Child.id, ondelete="CASCADE"), index=True)
    background_type: Mapped[str]
    background_description: Mapped[str]


class ChildSchedule(Base):
    """A weekly availability slot. Times are stored as naive UTC; utc_offset restores local time."""

    __tablename__ = "treatment_plan_v3_child_schedule"

    id: Mapped[int] = mapped_column(primary_key=True)
    child_id: Mapped[int] = mapped_column(ForeignKey(Child.id, ondelete="CASCADE"), index=True)
    day_of_week: Mapped[str]
    schedule_activity_type: Mapped[str]
    schedule_start_date: Mapped[datetime] = mapped_column(DateTime())
    schedule_end_date: Mapped[datetime] = mapped_column(DateTime())
    utc_offset: Mapped[int]
