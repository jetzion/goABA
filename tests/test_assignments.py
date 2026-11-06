"""Admin client assignments: add, change role, remove, and the care team they feed."""

import itertools

import pytest

from tests.test_enforcement import sign_in_with

ASSIGN = "/api/v2/admin/assignments"
PLANS = "/api/v2/treatment_plans"
_names = itertools.count(1)


@pytest.fixture
def setup(client):
    """A fresh client with a bay 3 plan, and three active providers."""
    n = next(_names)
    person = client.post("/api/v2/admin/clients/", json={"first_name": f"Ava{n}", "last_name": "Assign"}).json()
    providers = [client.post("/api/v2/admin/providers/", json={"display_name": f"{who} {n}"}).json()["id"] for who in ("Bea BCBA", "Cal BCBA", "Tia Tech")]
    plan = client.post(f"{PLANS}/", json={"client_id": person["id"], "bay": "3"}).json()
    return person["id"], providers, plan["id"]


def assign(client, client_id, provider_id, role):
    return client.post(f"{ASSIGN}/", json={"client_id": client_id, "provider_id": provider_id, "role": role})


def test_list_has_seeded_care_team_and_roles(client):
    data = client.get(f"{ASSIGN}/").json()
    sam = next(c for c in data["clients"] if c["id"] == 1)
    assert [(a["provider"], a["role"]) for a in sam["assignments"]] == [
        ("Dana Lee, BCBA", "home_bcba"), ("Morgan Diaz, BCBA", "substitute_bcba"), ("Chris Park", "bt")]
    assert [r["value"] for r in data["roles"]] == ["home_bcba", "substitute_bcba", "bt"]


def test_assignments_feed_information_and_treatment(client, setup):
    client_id, (bea, cal, tia), plan_id = setup
    assert client.get(f"{PLANS}/{plan_id}/pages/treatment/").json()["therapy_provisioning_description"] is None
    assert assign(client, client_id, bea, "home_bcba").status_code == 201
    assert assign(client, client_id, cal, "substitute_bcba").status_code == 201
    assert assign(client, client_id, tia, "bt").status_code == 201
    info = client.get(f"{PLANS}/{plan_id}/pages/information/").json()
    assert info["home_bcba"]["provider_id"] == bea
    assert [p["provider_id"] for p in info["substitute_bcbas"]] == [cal]
    assert [p["provider_id"] for p in info["assigned_bts"]] == [tia]
    assert "Tia Tech" in client.get(f"{PLANS}/{plan_id}/pages/treatment/").json()["therapy_provisioning_description"]


def test_one_home_bcba(client, setup):
    client_id, (bea, cal, _), _ = setup
    assign(client, client_id, bea, "home_bcba")
    second = assign(client, client_id, cal, "home_bcba")
    assert second.status_code == 409 and "already the Home BCBA" in second.json()["detail"]
    sub = assign(client, client_id, cal, "substitute_bcba").json()
    assert client.patch(f"{ASSIGN}/{sub['id']}/", json={"role": "home_bcba"}).status_code == 409
    home = next(a for a in client.get(f"{ASSIGN}/").json()["clients"] if a["id"] == client_id)["assignments"][0]
    assert client.patch(f"{ASSIGN}/{home['id']}/", json={"role": "home_bcba"}).status_code == 200


def test_provider_once_per_client(client, setup):
    client_id, (bea, _, _), _ = setup
    assign(client, client_id, bea, "substitute_bcba")
    again = assign(client, client_id, bea, "bt")
    assert again.status_code == 409 and "already assigned" in again.json()["detail"]


def test_change_role_and_remove(client, setup):
    client_id, (_, cal, _), plan_id = setup
    row = assign(client, client_id, cal, "substitute_bcba").json()
    assert client.patch(f"{ASSIGN}/{row['id']}/", json={"role": "home_bcba"}).json()["role"] == "home_bcba"
    assert client.get(f"{PLANS}/{plan_id}/pages/information/").json()["home_bcba"]["provider_id"] == cal
    assert client.delete(f"{ASSIGN}/{row['id']}/").status_code == 204
    assert client.get(f"{PLANS}/{plan_id}/pages/information/").json()["home_bcba"] is None


def test_save_rules(client, setup):
    client_id, (bea, _, tia), _ = setup
    assert assign(client, client_id, bea, "bobbing_bcba").status_code == 422
    assert assign(client, 99999, bea, "bt").status_code == 422
    assert assign(client, client_id, 99999, "bt").status_code == 422
    client.patch(f"/api/v2/admin/providers/{tia}/", json={"active": False})
    off = assign(client, client_id, tia, "bt")
    assert off.status_code == 422 and "turned off" in off.json()["detail"]
    assert all(p["id"] != tia for p in client.get(f"{ASSIGN}/").json()["providers"])
    assert client.patch(f"{ASSIGN}/99999/", json={"role": "bt"}).status_code == 404


def test_turned_off_provider_keeps_assignment(client, setup):
    client_id, (bea, _, _), _ = setup
    assign(client, client_id, bea, "home_bcba")
    client.patch(f"/api/v2/admin/providers/{bea}/", json={"active": False})
    rows = next(c for c in client.get(f"{ASSIGN}/").json()["clients"] if c["id"] == client_id)["assignments"]
    assert rows[0]["provider_id"] == bea and rows[0]["provider_active"] is False


def test_view_only_can_read_not_change(client):
    viewer = sign_in_with({"admin_assignments": "view"}, "Assignments viewer")
    assert viewer.get(f"{ASSIGN}/").status_code == 200
    assert viewer.post(f"{ASSIGN}/", json={"client_id": 1, "provider_id": 1, "role": "bt"}).status_code == 403
