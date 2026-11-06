"""Plans list: every plan with its client and owner, plus the choices a new plan needs."""

from fastapi.testclient import TestClient

from app.main import app
from tests.test_enforcement import sign_in_with

PLANS = "/api/v2/treatment_plans"


def test_list_shows_new_plan_first_with_client_and_owner(client, plan_id):
    data = client.get(f"{PLANS}/").json()
    first = data["plans"][0]
    assert first["id"] == plan_id
    assert first["client_name"] == "Sam Rivera" and first["owner"] == "Dana Lee, BCBA"
    assert first["status"] == "draft" and first["bay"] == "3" and first["signature"] is None


def test_list_has_clients_and_bays(client):
    data = client.get(f"{PLANS}/").json()
    assert {"id": 1, "name": "Sam Rivera"} in data["clients"]
    assert data["bays"] == ["2.5", "2.6", "2.7", "3", "6", "7"]


def test_list_needs_sign_in_only(client):
    assert TestClient(app).get(f"{PLANS}/").status_code == 401
    nobody = sign_in_with({}, "Plans list nobody")
    assert nobody.get(f"{PLANS}/").status_code == 200
    assert nobody.post(f"{PLANS}/", json={"client_id": 1, "bay": "3"}).status_code == 403
