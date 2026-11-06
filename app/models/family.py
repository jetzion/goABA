"""Family page tables."""

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Family(Base):
    """One family row per plan."""

    __tablename__ = "treatment_plan_v3_family"

    id: Mapped[int] = mapped_column(primary_key=True)
    treatment_plan_id: Mapped[int] = mapped_column(ForeignKey("treatment_plan.id", ondelete="CASCADE"), unique=True)
    cultural_consideration: Mapped[str | None] = mapped_column(Text)

    members: Mapped[list["FamilyMember"]] = relationship(cascade="all, delete-orphan", order_by="FamilyMember.id")
    siblings: Mapped[list["FamilySibling"]] = relationship(cascade="all, delete-orphan", order_by="FamilySibling.id")
    additional_info: Mapped[list["FamilyAdditionalInfo"]] = relationship(
        cascade="all, delete-orphan", order_by="FamilyAdditionalInfo.id"
    )


class FamilyMember(Base):
    """A parent or caregiver."""

    __tablename__ = "treatment_plan_v3_family_member"

    id: Mapped[int] = mapped_column(primary_key=True)
    family_id: Mapped[int] = mapped_column(ForeignKey(Family.id, ondelete="CASCADE"), index=True)
    full_name: Mapped[str | None]
    member_role: Mapped[str | None]
    caregiver_type: Mapped[str | None]
    relationship_to_client: Mapped[str | None]
    custody_type: Mapped[str | None]
    marital_status: Mapped[str | None]
    job_title: Mapped[str | None]
    email: Mapped[str | None]
    phone: Mapped[str | None] = mapped_column(String(10))
    street_address_line_one: Mapped[str | None]
    street_address_line_two: Mapped[str | None]
    street_address_city: Mapped[str | None]
    street_address_state: Mapped[str | None] = mapped_column(String(2))
    street_address_zip: Mapped[str | None] = mapped_column(String(5))


class FamilySibling(Base):
    """A sibling of the client."""

    __tablename__ = "treatment_plan_v3_family_sibling"

    id: Mapped[int] = mapped_column(primary_key=True)
    family_id: Mapped[int] = mapped_column(ForeignKey(Family.id, ondelete="CASCADE"), index=True)
    sibling_relationship: Mapped[str | None]
    sibling_age: Mapped[int | None]
    sibling_diagnosis: Mapped[str | None]


class FamilyAdditionalInfo(Base):
    """One value in a family selection list. The API calls `description` `value`."""

    __tablename__ = "treatment_plan_v3_family_additional_info"
    __table_args__ = (UniqueConstraint("family_id", "info_type", "description"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    family_id: Mapped[int] = mapped_column(ForeignKey(Family.id, ondelete="CASCADE"), index=True)
    info_type: Mapped[str]
    description: Mapped[str]
