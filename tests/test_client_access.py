"""Client rules: who sees a client's plans and who may edit them, on top of the role."""

import itertools
import re

import pytest

from app.access import ALLOWED_LEVELS, ADMIN_PAGES
from app.main import app
from tests.test_enforcement import sign_in_with

PLANS = "/api/v2/treatment_plans"
FULL = {k: levels[-1] for k, levels in ALLOWED_LEVELS.items() if k != "all_clients" and k not in ADMIN_PAGES}
_n = itertools.count(1)


@pytest.fixture
def world(client):
    """A client with one assigned provider and a plan owned by the Admin (Dana)."""
    n = next(_n)
    person = client.post("/api/v2/admin/clients/", json={"first_name": f"Cora{n}", "last_name": "Access"}).json()
    providers = {name: client.post("/api/v2/admin/providers/", json={"display_name": f"{name} {n}"}).json()["id"]
                 for name in ("Assigned", "Outsider", "Owner")}
    client.post("/api/v2/admin/assignments/", json={"client_id": person["id"], "provider_id": providers["Assigned"], "role": "bt"})
    plan = client.post(f"{PLANS}/", json={"client_id": person["id"], "bay": "3"}).json()
    return {"client_id": person["id"], "plan_id": plan["id"], "providers": providers, "n": n}


def user(world, name, cells=None, provider=None):
    return sign_in_with(cells or FULL, f"{name} {world['n']}", world["providers"].get(provider))


def test_assigned_provider_reads_and_edits(world):
    assigned = user(world, "Assigned user", provider="Assigned")
    plan_id = world["plan_id"]
    assert assigned.get(f"{PLANS}/{plan_id}/pages/medical/").status_code == 200
    assert assigned.patch(f"{PLANS}/{plan_id}/pages/medical/", json={"allergies": "None"}).status_code == 200
    assert assigned.get(f"{PLANS}/{plan_id}/").json()["can_edit"] is True
    listing = assigned.get(f"{PLANS}/").json()
    assert [p["id"] for p in listing["plans"]] == [plan_id]
    assert [c["id"] for c in listing["clients"]] == [world["client_id"]]


def test_unassigned_sees_nothing(world):
    outsider = user(world, "Outsider user", provider="Outsider")
    plan_id = world["plan_id"]
    assert outsider.get(f"{PLANS}/{plan_id}/").status_code == 403
    assert outsider.get(f"{PLANS}/{plan_id}/pages/medical/").status_code == 403
    assert outsider.patch(f"{PLANS}/{plan_id}/pages/medical/", json={"allergies": "x"}).status_code == 403
    listing = outsider.get(f"{PLANS}/").json()
    assert all(p["client_id"] != world["client_id"] for p in listing["plans"])
    assert all(c["id"] != world["client_id"] for c in listing["clients"])
    assert outsider.post(f"{PLANS}/", json={"client_id": world["client_id"], "bay": "3"}).status_code == 403


def test_all_clients_reads_but_does_not_edit(world):
    reader = user(world, "All clients user", {**FULL, "all_clients": "edit"}, provider="Outsider")
    plan_id = world["plan_id"]
    assert reader.get(f"{PLANS}/{plan_id}/pages/medical/").status_code == 200
    assert reader.get(f"{PLANS}/{plan_id}/").json()["can_edit"] is False
    refused = reader.patch(f"{PLANS}/{plan_id}/pages/medical/", json={"allergies": "x"})
    assert refused.status_code == 403 and refused.json()["detail"] == "You are not assigned to this client"
    assert reader.post(f"{PLANS}/{plan_id}/sign/", json={"signature": "Someone"}).status_code == 403
    assert any(p["id"] == plan_id for p in reader.get(f"{PLANS}/").json()["plans"])


def test_owner_keeps_editing_after_unassignment(client, world):
    owner_assignment = client.post("/api/v2/admin/assignments/", json={
        "client_id": world["client_id"], "provider_id": world["providers"]["Owner"], "role": "substitute_bcba"}).json()
    owner = user(world, "Owner user", provider="Owner")
    plan = owner.post(f"{PLANS}/", json={"client_id": world["client_id"], "bay": "6"}).json()
    client.delete(f"/api/v2/admin/assignments/{owner_assignment['id']}/")
    assert owner.patch(f"{PLANS}/{plan['id']}/pages/medical/", json={"allergies": "None"}).status_code == 200
    assert owner.get(f"{PLANS}/{world['plan_id']}/").status_code == 403


def test_clone_needs_to_see_the_source(world):
    outsider = user(world, "Clone outsider", provider="Outsider")
    assert outsider.post(f"{PLANS}/{world['plan_id']}/clone/").status_code == 403
    assigned = user(world, "Clone assigned", provider="Assigned")
    assert assigned.post(f"{PLANS}/{world['plan_id']}/clone/").status_code == 201


def test_visual_files_follow_the_client_rules(client, world):
    plan_id = world["plan_id"]
    method = client.post(f"{PLANS}/{plan_id}/pages/assessment/methods/", json={}).json()
    files = [("files", ("chart.png", b"png", "image/png"))]
    url = client.post(f"{PLANS}/{plan_id}/pages/assessment/methods/{method['id']}/visuals/", files=files).json()[0]["url"]
    assert client.get(url).content == b"png"
    assert user(world, "File assigned", provider="Assigned").get(url).status_code == 200
    assert user(world, "File outsider", provider="Outsider").get(url).status_code == 403
    assert user(world, "File no role", {"all_clients": "edit"}).get(url).status_code == 403
    assert client.get("/uploads/nope.png").status_code == 404


def test_every_plan_route_refuses_an_unassigned_user(world):
    """A role that may do everything still gets 403 on every plan route without access to the client."""
    outsider = user(world, "Sweep outsider", provider="Outsider")
    routes = [(m.upper(), p) for p, ops in app.openapi()["paths"].items() if "{plan_id}" in p for m in ops]
    assert len(routes) > 80
    for method, path in routes:
        url = re.sub(r"\{(\w+)\}", lambda m: str(world["plan_id"]) if m[1] == "plan_id" else ("x" if m[1] == "item" else "1"), path)
        response = outsider.request(method, url, json={})
        assert response.status_code == 403, f"{method} {path} returned {response.status_code}"
