"""Roles, role access cells, app users and their sign-in sessions."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, false
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Role(Base):
    """A role. A locked role (Admin) has full access and cannot be changed or deleted."""

    __tablename__ = "role"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)
    locked: Mapped[bool] = mapped_column(default=False)
    permissions: Mapped[list["RolePermission"]] = relationship(cascade="all, delete-orphan", passive_deletes=True)


class RolePermission(Base):
    """One matrix cell: the access level a role has to a page, action or admin page."""

    __tablename__ = "role_permission"
    __table_args__ = (UniqueConstraint("role_id", "key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("role.id", ondelete="CASCADE"))
    key: Mapped[str]
    level: Mapped[str]


class AppUser(Base):
    """A person who signs in. Each user has one role and may be a provider."""

    __tablename__ = "app_user"

    id: Mapped[int] = mapped_column(primary_key=True)
    display_name: Mapped[str]
    role_id: Mapped[int] = mapped_column(ForeignKey("role.id"))
    provider_id: Mapped[int | None] = mapped_column(ForeignKey("provider.id"), unique=True)
    email: Mapped[str | None] = mapped_column(unique=True, index=True)
    password_hash: Mapped[str | None]
    must_change_password: Mapped[bool] = mapped_column(default=False, server_default=false())
    failed_logins: Mapped[int] = mapped_column(default=0, server_default="0")
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    role: Mapped[Role] = relationship()


class UserSession(Base):
    """A signed-in session. Only the SHA-256 of the cookie token is stored."""

    __tablename__ = "user_session"

    id: Mapped[int] = mapped_column(primary_key=True)
    token_hash: Mapped[str] = mapped_column(unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("app_user.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
