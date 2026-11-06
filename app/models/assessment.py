"""Assessment page tables. String-array columns are JSON lists in SQLite."""

from datetime import date

from sqlalchemy import JSON, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Assessment(Base):
    """One assessment row per plan."""

    __tablename__ = "treatment_plan_v3_assessment"

    id: Mapped[int] = mapped_column(primary_key=True)
    treatment_plan_id: Mapped[int] = mapped_column(ForeignKey("treatment_plan.id", ondelete="CASCADE"), unique=True)
    initial_assessment_date: Mapped[date | None]
    reassessment_date: Mapped[date | None]
    diagnostic_report_reviewed: Mapped[bool | None]
    parent_interview_summary: Mapped[str | None] = mapped_column(Text)
    assessment_results: Mapped[str | None] = mapped_column(Text)
    priorities: Mapped[str | None] = mapped_column(Text)
    additional_files_viewed: Mapped[list[str]] = mapped_column(JSON, default=list)
    no_maladaptive_behavior: Mapped[bool] = mapped_column(default=False)
    telehealth_readiness_assessment_needed: Mapped[bool] = mapped_column(default=False)
    telehealth_assessment_date: Mapped[date | None]
    barriers: Mapped[list[str]] = mapped_column(JSON, default=list)
    observations: Mapped[str | None] = mapped_column(Text)

    behaviors: Mapped[list["AssessmentBehavior"]] = relationship(cascade="all, delete-orphan", order_by="AssessmentBehavior.id")
    methods: Mapped[list["AssessmentMethod"]] = relationship(cascade="all, delete-orphan", order_by="AssessmentMethod.id")
    readiness: Mapped[list["AssessmentReadiness"]] = relationship(cascade="all, delete-orphan")


class AssessmentBehavior(Base):
    """A maladaptive behavior."""

    __tablename__ = "treatment_plan_v3_assessment_behavior"

    id: Mapped[int] = mapped_column(primary_key=True)
    assessment_id: Mapped[int] = mapped_column(ForeignKey(Assessment.id, ondelete="CASCADE"), index=True)
    behavior: Mapped[str | None] = mapped_column(Text)
    dsm5_symptom: Mapped[str | None] = mapped_column(Text)
    parent_concerns: Mapped[str | None] = mapped_column(Text)


class AssessmentMethod(Base):
    """An assessment tool and its write-up."""

    __tablename__ = "treatment_plan_v3_assessment_method"

    id: Mapped[int] = mapped_column(primary_key=True)
    assessment_id: Mapped[int] = mapped_column(ForeignKey(Assessment.id, ondelete="CASCADE"), index=True)
    tool: Mapped[str | None]
    assessment_date: Mapped[date | None]
    rationale: Mapped[str | None] = mapped_column(Text)
    selection_rationale: Mapped[str | None] = mapped_column(Text)
    tool_description: Mapped[str | None] = mapped_column(Text)
    client_score: Mapped[str | None] = mapped_column(Text)

    visuals: Mapped[list["AssessmentVisual"]] = relationship(cascade="all, delete-orphan", order_by="AssessmentVisual.id")


class AssessmentVisual(Base):
    """An uploaded chart or image for a method. The file lives in local storage under its key."""

    __tablename__ = "treatment_plan_v3_assessment_visual"

    id: Mapped[int] = mapped_column(primary_key=True)
    method_id: Mapped[int] = mapped_column(ForeignKey(AssessmentMethod.id, ondelete="CASCADE"), index=True)
    file_storage_key: Mapped[str]
    title: Mapped[str | None] = mapped_column(String(255))
    analysis: Mapped[str | None] = mapped_column(Text)


class AssessmentReadiness(Base):
    """A telehealth readiness rating for one item."""

    __tablename__ = "treatment_plan_v3_assessment_readiness"
    __table_args__ = (UniqueConstraint("assessment_id", "item"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    assessment_id: Mapped[int] = mapped_column(ForeignKey(Assessment.id, ondelete="CASCADE"))
    item: Mapped[str]
    readiness: Mapped[str | None]
    notes: Mapped[str | None] = mapped_column(Text)
