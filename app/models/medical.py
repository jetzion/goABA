"""Medical page tables."""

from datetime import date

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class MedicalInfo(Base):
    """One medical row per plan."""

    __tablename__ = "treatment_plan_v3_medical_info"

    id: Mapped[int] = mapped_column(primary_key=True)
    treatment_plan_id: Mapped[int] = mapped_column(ForeignKey("treatment_plan.id", ondelete="CASCADE"), unique=True)
    allergies: Mapped[str | None]
    special_diets: Mapped[str | None]
    hearing_difficulty: Mapped[str | None]
    hearing_screening_date: Mapped[date | None]
    vision_difficulty: Mapped[str | None]
    vision_screening_date: Mapped[date | None]
    trauma_history: Mapped[str | None] = mapped_column(Text)
    hospitalization_history: Mapped[str | None] = mapped_column(Text)
    asd_severity_level: Mapped[str | None]
    asd_diagnosis_provider_name: Mapped[str | None]
    asd_diagnosis_city: Mapped[str | None]
    asd_diagnosis_state: Mapped[str | None] = mapped_column(String(2))
    asd_diagnosis_year: Mapped[int | None]
    child_delivery_type: Mapped[str | None]
    child_gestational_age_weeks: Mapped[int | None]
    child_weight_at_birth_pounds: Mapped[int | None]
    child_weight_at_birth_ounces: Mapped[int | None]
    child_sitting_up_age_months: Mapped[int | None]
    child_crawling_age_months: Mapped[int | None]
    child_walking_age_years: Mapped[int | None]
    child_walking_age_months: Mapped[int | None]
    child_standing_age_years: Mapped[int | None]
    child_standing_age_months: Mapped[int | None]
    child_babbling_age_months: Mapped[int | None]
    child_first_word: Mapped[str | None]
    child_second_word: Mapped[str | None]
    child_first_words_age_months: Mapped[int | None]

    diagnoses: Mapped[list["MedicalDiagnosis"]] = relationship(cascade="all, delete-orphan", order_by="MedicalDiagnosis.id")
    selections: Mapped[list["MedicalSelection"]] = relationship(cascade="all, delete-orphan", order_by="MedicalSelection.id")


class MedicalDiagnosis(Base):
    """An additional diagnosis row."""

    __tablename__ = "treatment_plan_v3_medical_info_diagnosis"

    id: Mapped[int] = mapped_column(primary_key=True)
    medical_info_id: Mapped[int] = mapped_column(ForeignKey(MedicalInfo.id, ondelete="CASCADE"), index=True)
    diagnosis_name: Mapped[str | None]
    provider_name: Mapped[str | None]
    city: Mapped[str | None]
    state: Mapped[str | None] = mapped_column(String(2))
    year: Mapped[int | None]


class MedicalSelection(Base):
    """One value in a multi-select group."""

    __tablename__ = "treatment_plan_v3_medical_info_selection"
    __table_args__ = (UniqueConstraint("medical_info_id", "selection_type", "value"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    medical_info_id: Mapped[int] = mapped_column(ForeignKey(MedicalInfo.id, ondelete="CASCADE"))
    selection_type: Mapped[str]
    value: Mapped[str]
