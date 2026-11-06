"""Goal tables for PCG, SAG and BRG, plus the goal name catalog."""

from datetime import date

from sqlalchemy import JSON, Float, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class GoalName(Base):
    """A goal that can be chosen, grouped by focus area."""

    __tablename__ = "goal_name"

    id: Mapped[int] = mapped_column(primary_key=True)
    focus_area: Mapped[str]
    label: Mapped[str]
    prefix: Mapped[str]
    active: Mapped[bool] = mapped_column(default=True)


class MeasurementColumns:
    """Columns shared by every goal and target."""

    baseline_date: Mapped[date | None]
    baseline_level: Mapped[float | None] = mapped_column(Float)
    duration_unit: Mapped[str | None]
    rate_interval: Mapped[int | None]
    rate_unit: Mapped[str | None]


class GoalColumns(MeasurementColumns):
    """Columns shared by every goal."""

    goal_name_id: Mapped[int] = mapped_column(ForeignKey("goal_name.id"))
    data_collection_method: Mapped[str | None]
    current_level: Mapped[float | None] = mapped_column(Float)
    expected_mastery_date: Mapped[str | None] = mapped_column(String(7))
    goal_description: Mapped[str | None] = mapped_column(Text)


class TargetColumns(MeasurementColumns):
    """Columns shared by every target."""

    target_name: Mapped[str | None] = mapped_column(String(500))
    timeframe: Mapped[str | None]
    description: Mapped[str | None] = mapped_column(Text)
    instructions: Mapped[str | None] = mapped_column(Text)


class StageColumns:
    """Columns shared by every stage history row."""

    stage: Mapped[str]
    reason: Mapped[str | None] = mapped_column(String(500))
    stage_date: Mapped[date]
    order: Mapped[int]


# PCG


class PcgGoal(GoalColumns, Base):
    __tablename__ = "treatment_plan_v3_pcg_goal"
    __table_args__ = (UniqueConstraint("treatment_plan_id", "goal_name_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    treatment_plan_id: Mapped[int] = mapped_column(ForeignKey("treatment_plan.id", ondelete="CASCADE"))
    opportunities: Mapped[int | None]
    mastery_direction: Mapped[str | None]
    mastery_aggregation: Mapped[str | None]
    mastery_to: Mapped[float | None] = mapped_column(Float)
    mastery_responses: Mapped[int | None]
    mastery_sessions: Mapped[int | None]

    goal_name: Mapped[GoalName] = relationship()
    targets: Mapped[list["PcgTarget"]] = relationship(cascade="all, delete-orphan", order_by="PcgTarget.id")


class PcgTarget(TargetColumns, Base):
    __tablename__ = "treatment_plan_v3_pcg_target"

    id: Mapped[int] = mapped_column(primary_key=True)
    goal_id: Mapped[int] = mapped_column(ForeignKey(PcgGoal.id, ondelete="CASCADE"), index=True)
    opportunities: Mapped[int | None]

    stages: Mapped[list["PcgTargetStage"]] = relationship(cascade="all, delete-orphan", order_by="PcgTargetStage.order")


class PcgTargetStage(StageColumns, Base):
    __tablename__ = "treatment_plan_v3_pcg_target_stage"
    __table_args__ = (UniqueConstraint("target_id", "order"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    target_id: Mapped[int] = mapped_column(ForeignKey(PcgTarget.id, ondelete="CASCADE"))


# SAG


class SagGoal(GoalColumns, Base):
    __tablename__ = "treatment_plan_v3_sag_goal"
    __table_args__ = (UniqueConstraint("treatment_plan_id", "goal_name_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    treatment_plan_id: Mapped[int] = mapped_column(ForeignKey("treatment_plan.id", ondelete="CASCADE"))
    opportunities: Mapped[int | None]
    frequency: Mapped[str | None]
    acquisition_direction: Mapped[str | None]
    acquisition_aggregation: Mapped[str | None]
    acquisition_to: Mapped[float | None] = mapped_column(Float)
    acquisition_responses: Mapped[int | None]
    acquisition_sessions: Mapped[int | None]
    generalization_direction: Mapped[str | None]
    generalization_aggregation: Mapped[str | None]
    generalization_to: Mapped[float | None] = mapped_column(Float)
    generalization_responses: Mapped[int | None]
    generalization_sessions: Mapped[int | None]
    maintenance_direction: Mapped[str | None]
    maintenance_aggregation: Mapped[str | None]
    maintenance_to: Mapped[float | None] = mapped_column(Float)
    maintenance_responses: Mapped[int | None]
    maintenance_sessions: Mapped[int | None]

    goal_name: Mapped[GoalName] = relationship()
    targets: Mapped[list["SagTarget"]] = relationship(cascade="all, delete-orphan", order_by="SagTarget.id")


class SagTarget(TargetColumns, Base):
    __tablename__ = "treatment_plan_v3_sag_target"

    id: Mapped[int] = mapped_column(primary_key=True)
    goal_id: Mapped[int] = mapped_column(ForeignKey(SagGoal.id, ondelete="CASCADE"), index=True)
    opportunities: Mapped[int | None]

    stages: Mapped[list["SagTargetStage"]] = relationship(cascade="all, delete-orphan", order_by="SagTargetStage.order")


class SagTargetStage(StageColumns, Base):
    __tablename__ = "treatment_plan_v3_sag_target_stage"
    __table_args__ = (UniqueConstraint("target_id", "order"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    target_id: Mapped[int] = mapped_column(ForeignKey(SagTarget.id, ondelete="CASCADE"))


# BRG


class BrgGoal(GoalColumns, Base):
    __tablename__ = "treatment_plan_v3_brg_goal"
    __table_args__ = (UniqueConstraint("treatment_plan_id", "goal_name_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    treatment_plan_id: Mapped[int] = mapped_column(ForeignKey("treatment_plan.id", ondelete="CASCADE"))
    related_to_maladaptive_behavior: Mapped[bool] = mapped_column(default=False)
    dsm5_symptom: Mapped[str | None] = mapped_column(Text)
    frequency: Mapped[str | None]
    mastery_direction: Mapped[str | None]
    mastery_aggregation: Mapped[str | None]
    mastery_to: Mapped[float | None] = mapped_column(Float)
    mastery_sessions: Mapped[int | None]
    operational_definition: Mapped[str | None] = mapped_column(Text)
    objective: Mapped[str | None] = mapped_column(Text)
    antecedent_modifications: Mapped[str | None] = mapped_column(Text)
    consequence_modifications: Mapped[str | None] = mapped_column(Text)

    goal_name: Mapped[GoalName] = relationship()
    targets: Mapped[list["BrgTarget"]] = relationship(cascade="all, delete-orphan", order_by="BrgTarget.id")
    sag_links: Mapped[list["BrgGoalSagLink"]] = relationship(cascade="all, delete-orphan")
    functions: Mapped[list["BrgHypothesizedFunction"]] = relationship(
        cascade="all, delete-orphan", order_by="BrgHypothesizedFunction.function_date"
    )


class BrgGoalSagLink(Base):
    __tablename__ = "treatment_plan_v3_brg_goal_sag_link"

    brg_goal_id: Mapped[int] = mapped_column(ForeignKey(BrgGoal.id, ondelete="CASCADE"), primary_key=True)
    sag_goal_id: Mapped[int] = mapped_column(ForeignKey(SagGoal.id, ondelete="CASCADE"), primary_key=True, index=True)


class BrgHypothesizedFunction(Base):
    __tablename__ = "treatment_plan_v3_brg_hypothesized_function"
    __table_args__ = (UniqueConstraint("goal_id", "function_date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    goal_id: Mapped[int] = mapped_column(ForeignKey(BrgGoal.id, ondelete="CASCADE"))
    function_date: Mapped[date]
    functions: Mapped[list[str]] = mapped_column(JSON)


class BrgTarget(TargetColumns, Base):
    __tablename__ = "treatment_plan_v3_brg_target"

    id: Mapped[int] = mapped_column(primary_key=True)
    goal_id: Mapped[int] = mapped_column(ForeignKey(BrgGoal.id, ondelete="CASCADE"), index=True)

    stages: Mapped[list["BrgTargetStage"]] = relationship(cascade="all, delete-orphan", order_by="BrgTargetStage.order")


class BrgTargetStage(StageColumns, Base):
    __tablename__ = "treatment_plan_v3_brg_target_stage"
    __table_args__ = (UniqueConstraint("target_id", "order"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    target_id: Mapped[int] = mapped_column(ForeignKey(BrgTarget.id, ondelete="CASCADE"))
