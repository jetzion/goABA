"""Crisis page tables."""

from datetime import date

from sqlalchemy import JSON, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Crisis(Base):
    """One crisis row per plan, holding the not-needed flag."""

    __tablename__ = "treatment_plan_v3_crisis"

    id: Mapped[int] = mapped_column(primary_key=True)
    treatment_plan_id: Mapped[int] = mapped_column(ForeignKey("treatment_plan.id", ondelete="CASCADE"), unique=True)
    no_crisis_plan_needed: Mapped[bool] = mapped_column(default=False)

    plans: Mapped[list["CrisisPlan"]] = relationship(cascade="all, delete-orphan", order_by="CrisisPlan.id")


class CrisisPlan(Base):
    """A crisis plan for one maladaptive behavior.

    The behavior foreign key has no ON DELETE action. The API refuses to delete a behavior
    that has a crisis plan, and plan deletes cascade through both parents without a
    RESTRICT check firing mid-cascade.
    """

    __tablename__ = "treatment_plan_v3_crisis_plan"

    id: Mapped[int] = mapped_column(primary_key=True)
    crisis_id: Mapped[int] = mapped_column(ForeignKey(Crisis.id, ondelete="CASCADE"))
    assessment_behavior_id: Mapped[int] = mapped_column(ForeignKey("treatment_plan_v3_assessment_behavior.id"), unique=True)
    crisis_creation_date: Mapped[date | None]
    operational_definition: Mapped[str | None] = mapped_column(Text)
    antecedent_interventions: Mapped[str | None] = mapped_column(Text)
    precursors_action_steps: Mapped[str | None] = mapped_column(Text)
    escalation_intervention_plan: Mapped[str | None] = mapped_column(Text)
    follow_up_steps: Mapped[str | None] = mapped_column(Text)
    functional_behavior: Mapped[list[str]] = mapped_column(JSON, default=list)
    consequence_strategies: Mapped[str | None] = mapped_column(Text)
