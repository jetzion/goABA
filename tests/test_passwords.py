"""Password hashing, the password rule, the set-password command, and secrets kept out of the history."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select

from app.db import SessionLocal
from app.models import AppUser, AuditEvent, Role, UserSession
from app.passwords import check_new_password, hash_password, verify_password
from app.set_password import set_credentials


def test_hash_and_verify():
    stored = hash_password("correct horse battery")
    assert stored.startswith("$argon2") and "correct horse" not in stored
    assert verify_password(stored, "correct horse battery")
    assert not verify_password(stored, "correct horse battery!")
    assert not verify_password(None, "anything at all")


def test_password_rule():
    check_new_password("8 chars!")
    with pytest.raises(ValueError):
        check_new_password("7 chars")


def make_user(session, name: str) -> AppUser:
    user = AppUser(display_name=name, role=Role(name=f"{name} role"))
    session.add(user)
    session.flush()
    return user


def test_set_credentials(client):
    with SessionLocal() as session:
        user = make_user(session, "Cli User")
        user.must_change_password, user.failed_logins = True, 4
        user.locked_until = datetime.now(UTC) + timedelta(minutes=5)
        now = datetime.now(UTC)
        session.add(UserSession(token_hash="abc", user_id=user.id, created_at=now, expires_at=now + timedelta(hours=8)))
        session.commit()
        set_credentials(session, user.id, "  Cli.User@Example.COM ", "a long enough password")
        session.refresh(user)
        assert user.email == "cli.user@example.com"
        assert verify_password(user.password_hash, "a long enough password")
        assert not user.must_change_password and user.failed_logins == 0 and user.locked_until is None
        assert session.scalar(select(func.count()).select_from(UserSession).where(UserSession.user_id == user.id)) == 0


def test_set_credentials_rules(client):
    with SessionLocal() as session:
        user = make_user(session, "Cli Rules")
        session.commit()
        with pytest.raises(ValueError):
            set_credentials(session, user.id, "rules@example.com", "short")
        with pytest.raises(ValueError):
            set_credentials(session, 99999, "nobody@example.com", "a long enough password")


def test_history_never_holds_secrets(client):
    with SessionLocal() as session:
        session.info["user"] = session.get(AppUser, 1)
        user = make_user(session, "Secret User")
        session.commit()
        user.password_hash = hash_password("temporary password 1")
        user.must_change_password = True
        user.failed_logins = 3
        session.commit()
        event = session.scalars(select(AuditEvent).where(AuditEvent.record_type == "user").order_by(AuditEvent.id.desc())).first()
        assert event.label == "Secret User" and event.changes == {"must_change_password": [False, True]}
        everything = " ".join(str(e.changes) for e in session.scalars(select(AuditEvent)))
        assert "argon2" not in everything and "password_hash" not in everything and "failed_logins" not in everything
