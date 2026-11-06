"""Change history: who changed what and when, recorded automatically and read-only."""

from app.db import SessionLocal
from app.models import Client
from tests.test_enforcement import sign_in_with
from tests.test_full_plan import fill_full_plan

HISTORY = "/api/v2/admin/history"
PLANS = "/api/v2/treatment_plans"


def latest(client, record_type: str) -> dict:
    return client.get(f"{HISTORY}/", params={"record_type": record_type}).json()["events"][0]


def test_role_create_rename_cell_delete(client):
    role = client.post("/api/v2/admin/roles/", json={"name": "History role"}).json()
    created = latest(client, "role")
    assert created["action"] == "created" and created["label"] == "History role" and created["user_name"] == "Dana Lee, BCBA"
    assert created["changes"]["name"] == [None, "History role"]
    client.patch(f"/api/v2/admin/roles/{role['id']}/", json={"name": "History role 2"})
    assert latest(client, "role")["changes"] == {"name": ["History role", "History role 2"]}
    client.put(f"/api/v2/admin/roles/{role['id']}/permissions/medical/", json={"level": "view"})
    client.put(f"/api/v2/admin/roles/{role['id']}/permissions/medical/", json={"level": "edit"})
    cell = latest(client, "access")
    assert cell["action"] == "changed" and cell["label"] == "History role 2: medical" and cell["changes"] == {"level": ["view", "edit"]}
    client.delete(f"/api/v2/admin/roles/{role['id']}/")
    deleted = latest(client, "role")
    assert deleted["action"] == "deleted" and deleted["changes"]["name"] == ["History role 2", None]


def test_user_provider_client_assignment_goal_name(client):
    provider = client.post("/api/v2/admin/providers/", json={"display_name": "Hal History"}).json()
    assert latest(client, "provider")["label"] == "Hal History"
    person = client.post("/api/v2/admin/clients/", json={"first_name": "Hana", "last_name": "History"}).json()
    client.patch(f"/api/v2/admin/clients/{person['id']}/", json={"date_of_birth": "2020-05-06"})
    assert latest(client, "client")["changes"] == {"date_of_birth": [None, "2020-05-06"]}
    client.post("/api/v2/admin/assignments/", json={"client_id": person["id"], "provider_id": provider["id"], "role": "bt"})
    assert latest(client, "assignment")["label"] == "Hal History for Hana History"
    roles = client.get("/api/v2/admin/users/").json()["roles"]
    user = client.post("/api/v2/admin/users/", json={"display_name": "Hugo", "role_id": roles[-1]["id"]}).json()
    client.patch(f"/api/v2/admin/users/{user['id']}/", json={"provider_id": provider["id"]})
    assert latest(client, "user")["changes"] == {"provider_id": [None, provider["id"]]}
    name = client.post("/api/v2/admin/goal_names/", json={"focus_area": "Communication", "label": "Greets peers", "prefix": "HIS-1"}).json()
    client.patch(f"/api/v2/admin/goal_names/{name['id']}/", json={"active": False})
    assert latest(client, "goal name")["changes"] == {"active": [True, False]}


def test_plan_created_cloned_signed_but_not_page_edits(client, plan_id):
    created = latest(client, "plan")
    assert created["action"] == "created" and created["record_id"] == plan_id
    fill_full_plan(client, plan_id)
    client.patch(f"{PLANS}/{plan_id}/pages/medications/", json={"no_medication": True})
    assert latest(client, "plan")["record_id"] == plan_id and latest(client, "plan")["action"] == "created"
    client.post(f"{PLANS}/{plan_id}/sign/", json={"signature": "Dana Lee, BCBA"})
    signed = latest(client, "plan")
    assert signed["action"] == "signed" and signed["changes"]["status"] == ["draft", "signed"]
    copy = client.post(f"{PLANS}/{plan_id}/clone/").json()
    cloned = latest(client, "plan")
    assert cloned["action"] == "cloned" and cloned["record_id"] == copy["id"] and cloned["changes"]["parent_treatment_plan_id"] == [None, plan_id]


def test_writes_without_a_user_are_not_recorded(client):
    before = client.get(f"{HISTORY}/", params={"record_type": "client"}).json()["events"][0]["id"]
    with SessionLocal() as session:
        session.add(Client(first_name="Quiet", last_name="Seed"))
        session.commit()
    assert client.get(f"{HISTORY}/", params={"record_type": "client"}).json()["events"][0]["id"] == before


def test_paging_and_filter(client):
    for n in range(3):
        client.post("/api/v2/admin/providers/", json={"display_name": f"Page {n}"})
    first = client.get(f"{HISTORY}/", params={"record_type": "provider", "limit": 2}).json()
    assert len(first["events"]) == 2 and first["more"] is True
    assert {e["record_type"] for e in first["events"]} == {"provider"}
    older = client.get(f"{HISTORY}/", params={"record_type": "provider", "limit": 2, "before": first["events"][-1]["id"]}).json()
    assert older["events"][0]["id"] < first["events"][-1]["id"]
    assert "assignment" in first["record_types"]


def test_read_only_and_view_access(client):
    assert client.post(f"{HISTORY}/", json={}).status_code == 405
    assert sign_in_with({}, "History nobody").get(f"{HISTORY}/").status_code == 403
    viewer = sign_in_with({"admin_history": "view"}, "History viewer")
    assert viewer.get(f"{HISTORY}/").status_code == 200
    assert client.put("/api/v2/admin/roles/1/permissions/admin_history/", json={"level": "edit"}).status_code in (409, 422)
