"""Roles, access cells and user access levels."""

from sqlalchemy import select

from app.access import ALLOWED_LEVELS, EDIT, NONE, VIEW, allows, user_level
from app.db import SessionLocal
from app.models import AppUser, Role, RolePermission


def test_seed_has_admin_role_and_user(client):
    with SessionLocal() as session:
        admin = session.scalar(select(Role).where(Role.name == "Admin"))
        user = session.get(AppUser, 1)
        assert admin.locked and user.role_id == admin.id and user.provider_id == 1


def test_admin_has_highest_level_for_every_key(client):
    with SessionLocal() as session:
        user = session.get(AppUser, 1)
        for key, allowed in ALLOWED_LEVELS.items():
            assert user_level(session, user, key) == allowed[-1]
        assert user_level(session, user, "information") == VIEW


def test_other_role_uses_stored_cells_and_defaults_to_none(client):
    with SessionLocal() as session:
        role = Role(name="Biller test", permissions=[RolePermission(key="medical", level=VIEW)])
        user = AppUser(display_name="Bea Biller", role=role)
        session.add(user)
        session.flush()
        assert user_level(session, user, "medical") == VIEW
        assert user_level(session, user, "goals") == NONE
        session.rollback()


def test_edit_includes_view():
    assert allows(EDIT, VIEW) and allows(VIEW, VIEW) and not allows(VIEW, EDIT) and not allows(NONE, VIEW)
