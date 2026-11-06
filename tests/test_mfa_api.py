"""Authenticator codes over the API: setup, the code step at sign-in, the Admin gate, turning off and resets."""

import itertools
from datetime import UTC, datetime, timedelta

import pyotp
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import SessionLocal
from app.main import app
from app.models import AppUser, AuditEvent, Role, RolePermission, UserSession
from app.passwords import hash_password
from app.reset_mfa import reset_mfa

SESSION = "/api/v2/session/"
MFA = "/api/v2/session/mfa"
USERS = "/api/v2/admin/users"
PLANS = "/api/v2/treatment_plans/"
PASSWORD = "mfa user password"
_n = itertools.count(1)


def code(secret: str, steps_ahead: int = 0) -> str:
    """The code for now, or for a later 30-second step (still inside the allowed drift when 1)."""
    return pyotp.TOTP(secret).at(datetime.now(UTC) + timedelta(seconds=30 * steps_ahead))


def make_person(admin: bool = False, secret: str | None = None) -> dict:
    """A user with a password whose role may view Information, or an Admin. With a secret, codes are on."""
    n = next(_n)
    email = f"mfa{n}@example.com"
    with SessionLocal() as session:
        if admin:
            role = session.scalar(select(Role).where(Role.locked))
        else:
            role = Role(name=f"Mfa role {n}", permissions=[RolePermission(key="information", level="view")])
        user = AppUser(display_name=f"Mfa {n}", role=role, email=email, password_hash=hash_password(PASSWORD),
                       mfa_secret=secret, mfa_enabled=secret is not None)
        session.add(user)
        session.commit()
        return {"id": user.id, "email": email, "secret": secret}


def password_step(person: dict) -> tuple[TestClient, object]:
    browser = TestClient(app)
    return browser, browser.post(SESSION, json={"email": person["email"], "password": PASSWORD})


@pytest.fixture
def person(client) -> dict:
    return make_person()


@pytest.fixture
def mfa_person(client) -> dict:
    return make_person(secret=pyotp.random_base32())


def test_password_alone_without_codes(person):
    browser, response = password_step(person)
    assert response.json()["mfa_enabled"] is False and response.json()["mfa_pending"] is False
    assert browser.get(PLANS).status_code == 200


def test_setup_and_enable(person):
    browser, _ = password_step(person)
    other, _ = password_step(person)
    setup = browser.post(f"{MFA}/setup/").json()
    assert setup["uri"].startswith("otpauth://totp/") and setup["qr_svg"].startswith("<svg")
    assert browser.post(f"{MFA}/enable/", json={"code": "abc"}).status_code == 422
    enabled = browser.post(f"{MFA}/enable/", json={"code": code(setup["secret"])})
    assert enabled.status_code == 200 and enabled.json()["mfa_enabled"] is True
    assert other.get(SESSION).json()["user"] is None
    assert browser.get(SESSION).json()["user"]["mfa_enabled"] is True
    assert browser.post(f"{MFA}/setup/").status_code == 409
    assert browser.post(f"{MFA}/enable/", json={"code": code(setup["secret"], 1)}).status_code == 409


def test_enable_needs_setup_first(person):
    browser, _ = password_step(person)
    assert browser.post(f"{MFA}/enable/", json={"code": "123456"}).status_code == 409


def test_sign_in_with_a_code(mfa_person):
    browser, response = password_step(mfa_person)
    assert response.status_code == 200 and response.json()["mfa_pending"] is True
    me = browser.get(SESSION).json()
    assert me["user"]["mfa_pending"] is True and me["access"] == {}
    assert browser.get(PLANS).json() == {"detail": "Enter your authenticator code first"}
    assert browser.post(f"{SESSION}password/", json={"current_password": PASSWORD, "new_password": "x" * 9}).status_code == 401
    assert browser.post(f"{MFA}/", json={"code": "000000"}).status_code == 401
    done = browser.post(f"{MFA}/", json={"code": code(mfa_person["secret"])})
    assert done.status_code == 200 and done.json()["mfa_pending"] is False
    assert browser.get(PLANS).status_code == 200 and browser.get(SESSION).json()["access"]["information"] == "view"
    with SessionLocal() as session:
        row = session.scalar(select(UserSession).where(UserSession.user_id == mfa_person["id"]))
        assert row.expires_at.replace(tzinfo=UTC) > datetime.now(UTC) + timedelta(hours=7)


def test_pending_session_is_short(mfa_person):
    password_step(mfa_person)
    with SessionLocal() as session:
        row = session.scalar(select(UserSession).where(UserSession.user_id == mfa_person["id"]))
        assert row.mfa_pending and row.expires_at.replace(tzinfo=UTC) < datetime.now(UTC) + timedelta(minutes=6)


def test_a_code_works_once(mfa_person):
    first, _ = password_step(mfa_person)
    used = code(mfa_person["secret"])
    assert first.post(f"{MFA}/", json={"code": used}).status_code == 200
    second, _ = password_step(mfa_person)
    assert second.post(f"{MFA}/", json={"code": used}).status_code == 401


def test_code_step_needs_a_pending_session(mfa_person):
    assert TestClient(app).post(f"{MFA}/", json={"code": code(mfa_person["secret"])}).status_code == 401
    browser, _ = password_step(mfa_person)
    browser.post(f"{MFA}/", json={"code": code(mfa_person["secret"])})
    assert browser.post(f"{MFA}/", json={"code": code(mfa_person["secret"], 1)}).status_code == 401


def test_wrong_codes_lock_the_account(mfa_person):
    browser, _ = password_step(mfa_person)
    for _ in range(5):
        assert browser.post(f"{MFA}/", json={"code": "000000"}).status_code == 401
    assert browser.post(f"{MFA}/", json={"code": code(mfa_person["secret"])}).status_code == 429
    assert password_step(mfa_person)[1].status_code == 429


def test_admin_must_set_up_codes(client):
    admin = make_person(admin=True)
    browser, response = password_step(admin)
    assert response.json()["mfa_setup_required"] is True and response.json()["mfa_pending"] is False
    assert browser.get(PLANS).json() == {"detail": "Set up authenticator codes first"}
    assert browser.get(SESSION).json()["user"]["mfa_setup_required"] is True
    secret = browser.post(f"{MFA}/setup/").json()["secret"]
    assert browser.post(f"{MFA}/enable/", json={"code": code(secret)}).json()["mfa_setup_required"] is False
    assert browser.get(PLANS).status_code == 200


def test_turn_off(mfa_person):
    browser, _ = password_step(mfa_person)
    browser.post(f"{MFA}/", json={"code": code(mfa_person["secret"])})
    assert browser.post(f"{MFA}/disable/", json={"code": "000000"}).status_code == 422
    off = browser.post(f"{MFA}/disable/", json={"code": code(mfa_person["secret"], 1)})
    assert off.status_code == 200 and off.json()["mfa_enabled"] is False
    assert browser.post(f"{MFA}/disable/", json={"code": "000000"}).status_code == 409
    assert password_step(mfa_person)[1].json()["mfa_pending"] is False


def test_admin_cannot_turn_off(client):
    assert client.post(f"{MFA}/disable/", json={"code": "000000"}).json() == {"detail": "Admin users must keep authenticator codes on"}


def test_admin_reset(client, mfa_person):
    browser, _ = password_step(mfa_person)
    row = next(u for u in client.get(f"{USERS}/").json()["users"] if u["id"] == mfa_person["id"])
    assert row["mfa_enabled"] is True
    assert client.post(f"{USERS}/{mfa_person['id']}/mfa/reset/").status_code == 204
    assert browser.get(SESSION).json()["user"] is None
    assert password_step(mfa_person)[1].json()["mfa_pending"] is False
    assert client.post(f"{USERS}/1/mfa/reset/").status_code == 409
    with SessionLocal() as session:
        event = session.scalars(select(AuditEvent).where(AuditEvent.record_type == "user").order_by(AuditEvent.id.desc())).first()
        assert event.changes == {"mfa_enabled": [True, False]}


def test_reset_command(mfa_person):
    with SessionLocal() as session:
        user = reset_mfa(session, mfa_person["id"])
        assert user.mfa_enabled is False and user.mfa_secret is None
        with pytest.raises(ValueError):
            reset_mfa(session, 99999)
