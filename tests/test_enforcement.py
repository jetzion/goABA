"""Role access is enforced on every route."""

import re

import pytest
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models import AppUser, Role, RolePermission
from app.passwords import hash_password

TEST_PASSWORD = "test user password"
TEST_HASH = hash_password(TEST_PASSWORD)

PLANS = "/api/v2/treatment_plans"
SIGNED_IN_ONLY = {
    ("GET", "/api/v2/treatment_plans/"),
    ("GET", "/api/v2/treatment_plans/{plan_id}/"),
    ("GET", "/api/v2/treatment_plans/{plan_id}/pages/"),
    ("GET", "/api/v2/options/"),
}


def sign_in_with(cells: dict[str, str], name: str, provider_id: int | None = None) -> TestClient:
    """A client signed in with a password as a new user whose role has these cells."""
    email = f"{re.sub(r"\W+", ".", name.lower())}@test.example"
    with SessionLocal() as session:
        role = Role(name=name, permissions=[RolePermission(key=k, level=v) for k, v in cells.items()])
        session.add(AppUser(display_name=name, role=role, provider_id=provider_id, email=email, password_hash=TEST_HASH))
        session.commit()
    other = TestClient(app)
    assert other.post("/api/v2/session/", json={"email": email, "password": TEST_PASSWORD}).status_code == 200
    return other


@pytest.fixture(scope="module")
def viewer(client) -> TestClient:
    return sign_in_with({"medical": "view", "goals": "view", "information": "view", "all_clients": "edit"}, "Viewer role")


@pytest.fixture(scope="module")
def nobody(client) -> TestClient:
    return sign_in_with({}, "No access role")


def test_view_can_read_not_write(viewer, plan_id):
    assert viewer.get(f"{PLANS}/{plan_id}/pages/medical/").status_code == 200
    assert viewer.patch(f"{PLANS}/{plan_id}/pages/medical/", json={}).status_code == 403
    assert viewer.get(f"{PLANS}/{plan_id}/pages/information/").status_code == 200


def test_goals_key_covers_pcg_sag_brg(viewer, plan_id):
    for section in ("pcg", "sag", "brg"):
        assert viewer.get(f"{PLANS}/{plan_id}/pages/{section}/").status_code == 200
        assert viewer.post(f"{PLANS}/{plan_id}/pages/{section}/goals/", json={"goal_name_id": 1}).status_code == 403


def test_none_cannot_read(nobody, plan_id):
    assert nobody.get(f"{PLANS}/{plan_id}/pages/medical/").status_code == 403
    assert nobody.get(f"{PLANS}/{plan_id}/").status_code == 403


def test_actions_need_permission(client, nobody, plan_id):
    assert nobody.post(f"{PLANS}/", json={"client_id": 1, "bay": "3"}).status_code == 403
    assert nobody.post(f"{PLANS}/{plan_id}/sign/", json={"signature": "No Access"}).status_code == 403


def test_signed_out_gets_401(client, plan_id):
    signed_out = TestClient(app)
    assert signed_out.get(f"{PLANS}/{plan_id}/pages/medical/").status_code == 401
    assert signed_out.get("/api/v2/options/").status_code == 401


def guarded_routes() -> list[tuple[str, str]]:
    """Every API method and path from the OpenAPI schema, except sign-in and the signed-in-only reads."""
    return [
        (method.upper(), path)
        for path, operations in app.openapi()["paths"].items()
        if not path.startswith("/api/v2/session")
        for method in operations
        if (method.upper(), path) not in SIGNED_IN_ONLY
    ]


def test_every_api_route_is_protected(nobody, plan_id):
    """A role with no access is refused on every route except the signed-in-only reads and sign-in itself."""
    routes = guarded_routes()
    assert len(routes) > 80
    for method, path in routes:
        url = re.sub(r"\{(\w+)\}", lambda m: str(plan_id) if m[1] == "plan_id" else ("x" if m[1] == "item" else "1"), path)
        response = nobody.request(method, url, json={})
        assert response.status_code == 403, f"{method} {path} returned {response.status_code}"
