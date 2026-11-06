"""Plan create, read and page status."""

from app.enums import PAGES

BASE = "/api/v2/treatment_plans"


def test_create_plan(client):
    response = client.post(f"{BASE}/", json={"client_id": 1, "bay": "2.6"})
    assert response.status_code == 201
    assert response.json()["version"] == 3
    assert response.json()["bay"] == "2.6"


def test_create_rejects_unknown_field(client):
    response = client.post(f"{BASE}/", json={"client_id": 1, "bay": "3", "extra": 1})
    assert response.status_code == 422


def test_create_rejects_unknown_bay(client):
    response = client.post(f"{BASE}/", json={"client_id": 1, "bay": "9"})
    assert response.status_code == 422


def test_get_missing_plan(client):
    assert client.get(f"{BASE}/999999/").status_code == 404


def test_new_plan_pages_are_empty_except_information(client, plan_id):
    statuses = client.get(f"{BASE}/{plan_id}/pages/").json()
    assert [s["page"] for s in statuses] == PAGES
    assert statuses[0]["status"] == "completed"
    assert {s["status"] for s in statuses[1:]} == {"empty"}
