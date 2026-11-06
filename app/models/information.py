"""Reference tables the Information page reads: providers, assignments, guardians, insurance."""

from datetime import date

from sqlalchemy import ForeignKey, true
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Provider(Base):
    """A clinician."""

    __tablename__ = "provider"

    id: Mapped[int] = mapped_column(primary_key=True)
    display_name: Mapped[str]
    active: Mapped[bool] = mapped_column(default=True, server_default=true())


class ClientAssignment(Base):
    """A provider assigned to a client. Role: home_bcba, substitute_bcba, bt."""

    __tablename__ = "client_assignment"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("client.id"), index=True)
    provider_id: Mapped[int] = mapped_column(ForeignKey("provider.id"))
    role: Mapped[str]


class ClientGuardian(Base):
    """A parent or guardian of a client."""

    __tablename__ = "client_guardian"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("client.id"), index=True)
    display_name: Mapped[str]
    role: Mapped[str]


class ClientInsurance(Base):
    """An insurance policy. Rank: primary, secondary, tertiary."""

    __tablename__ = "client_insurance"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("client.id"), index=True)
    rank: Mapped[str]
    payor_name: Mapped[str]
    member_id: Mapped[str | None]
    date_start: Mapped[date | None]
    date_end: Mapped[date | None]
