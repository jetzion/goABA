"""Email and password sign-in: sessions, expiry, lockout, sign-out, password changes and resets."""

import itertools
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update

from app.access import token_hash
from app.db import SessionLocal
from app.main import app
from app.models import AppUser, Role, RolePermission, UserSession
from app.passwords import hash_password

SESSION = "/api/v2/session/"
PASSWORD = "first password 1"
_n = itertools.count(1)


@pytest.fixture
def person(client) -> dict:
    """A user with an email and password, whose role may view Information."""
    n = next(_n)
    email = f"pat{n}@example.com"
    with SessionLocal() as session:
        role = Role(name=f"Login role {n}", permissions=[RolePermission(key="information", level="view")])
        user = AppUser(display_name=f"Pat {n}", role=role, email=email, password_hash=hash_password(PASSWORD))
        session.add(user)
        session.commit()
        return {"id": user.id, "email": email}


def sign_in(person: dict, password: str = PASSWORD, email: str | None = None) -> tuple[TestClient, object]:
    browser = TestClient(app)
    return browser, browser.post(SESSION, json={"email": email or person["email"], "password": password})


def test_signed_out(client):
    browser = TestClient(app)
    assert browser.get(SESSION).json() == {"user": None, "access": {}}
    assert browser.get("/api/v2/treatment_plans/").status_code == 401


def test_sign_in_and_who_am_i(person):
    browser, response = sign_in(person, email=person["email"].upper())
    assert response.status_code == 200 and response.json()["email"] == person["email"]
    me = browser.get(SESSION).json()
    assert me["user"]["id"] == person["id"] and me["access"]["information"] == "view"
    cookie = browser.cookies["tp_session"]
    with SessionLocal() as session:
        stored = session.scalar(select(UserSession.token_hash).where(UserSession.user_id == person["id"]))
    assert stored == token_hash(cookie) and cookie not in stored


def test_wrong_password_and_unknown_email_look_the_same(person):
    _, wrong = sign_in(person, password="not the password")
    _, unknown = sign_in(person, email="nobody@example.com")
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json() == {"detail": "Email or password is incorrect"}


def test_lockout_after_five_wrong(person):
    for _ in range(5):
        assert sign_in(person, password="wrong guess")[1].status_code == 401
    assert sign_in(person)[1].status_code == 429
    with SessionLocal() as session:
        session.execute(update(AppUser).where(AppUser.id == person["id"]).values(locked_until=datetime.now(UTC) - timedelta(seconds=1)))
        session.commit()
    assert sign_in(person)[1].status_code == 200


def test_session_expires(person):
    browser, _ = sign_in(person)
    with SessionLocal() as session:
        session.execute(update(UserSession).where(UserSession.user_id == person["id"]).values(expires_at=datetime.now(UTC) - timedelta(seconds=1)))
        session.commit()
    assert browser.get(SESSION).json()["user"] is None
    assert browser.get("/api/v2/treatment_plans/").status_code == 401


def test_sign_out_ends_the_session_on_the_server(person):
    browser, _ = sign_in(person)
    token = browser.cookies["tp_session"]
    assert browser.delete(SESSION).status_code == 204
    replay = TestClient(app, cookies={"tp_session": token})
    assert replay.get("/api/v2/treatment_plans/").status_code == 401


def test_change_password(person):
    browser, _ = sign_in(person)
    other_device, _ = sign_in(person)
    assert browser.post(f"{SESSION}password/", json={"current_password": "wrong", "new_password": "second password 2"}).status_code == 422
    assert browser.post(f"{SESSION}password/", json={"current_password": PASSWORD, "new_password": "short"}).status_code == 422
    assert browser.post(f"{SESSION}password/", json={"current_password": PASSWORD, "new_password": PASSWORD}).status_code == 422
    assert browser.post(f"{SESSION}password/", json={"current_password": PASSWORD, "new_password": "second password 2"}).status_code == 204
    assert browser.get("/api/v2/treatment_plans/").status_code == 200
    assert other_device.get("/api/v2/treatment_plans/").status_code == 401
    assert sign_in(person, password="second password 2")[1].status_code == 200


def test_admin_temporary_password_forces_a_change(client, person):
    old_browser, _ = sign_in(person)
    assert client.post(f"/api/v2/admin/users/{person['id']}/password/", json={"password": "temp password 9"}).status_code == 204
    assert old_browser.get("/api/v2/treatment_plans/").status_code == 401
    assert sign_in(person)[1].status_code == 401
    browser, response = sign_in(person, password="temp password 9")
    assert response.json()["must_change_password"] is True
    blocked = browser.get("/api/v2/treatment_plans/")
    assert blocked.status_code == 403 and blocked.json()["detail"] == "Change your password first"
    assert browser.get(SESSION).json()["user"]["must_change_password"] is True
    browser.post(f"{SESSION}password/", json={"current_password": "temp password 9", "new_password": "my own password"})
    assert browser.get("/api/v2/treatment_plans/").status_code == 200


def test_admin_reset_rules(client, person):
    assert client.post("/api/v2/admin/users/1/password/", json={"password": "temp password 9"}).status_code == 409
    assert client.post(f"/api/v2/admin/users/{person['id']}/password/", json={"password": "short"}).status_code == 422
    with SessionLocal() as session:
        no_email = AppUser(display_name="No Email", role_id=session.get(AppUser, person["id"]).role_id)
        session.add(no_email)
        session.commit()
        no_email_id = no_email.id
    assert client.post(f"/api/v2/admin/users/{no_email_id}/password/", json={"password": "temp password 9"}).status_code == 422


def test_user_emails_are_unique_and_lowercased(client, person):
    roles = client.get("/api/v2/admin/users/").json()["roles"]
    made = client.post("/api/v2/admin/users/", json={"display_name": "Eve", "role_id": roles[-1]["id"], "email": "Eve.Example@Clinic.org"}).json()
    assert made["email"] == "eve.example@clinic.org" and made["has_password"] is False
    clash = client.post("/api/v2/admin/users/", json={"display_name": "Eve 2", "role_id": roles[-1]["id"], "email": person["email"].upper()})
    assert clash.status_code == 409 and "already signs in" in clash.json()["detail"]
    assert client.post("/api/v2/admin/users/", json={"display_name": "Bad", "role_id": roles[-1]["id"], "email": "not-an-email"}).status_code == 422


def test_picker_is_gone(client):
    assert client.put(SESSION, json={"user_id": 1}).status_code == 405
    assert "users" not in client.get(SESSION).json()
