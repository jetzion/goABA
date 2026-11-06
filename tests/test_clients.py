"""Admin clients API: list, create, edit, delete, and a new client getting a plan."""

from datetime import date, timedelta

from app.db import SessionLocal
from app.models import ClientGuardian
from tests.test_enforcement import sign_in_with

CLIENTS = "/api/v2/admin/clients"
PLANS = "/api/v2/treatment_plans"


def create(client, **extra) -> dict:
    response = client.post(f"{CLIENTS}/", json={"first_name": "Lena", "last_name": "Ortiz", **extra})
    assert response.status_code == 201, response.text
    return response.json()


def test_list_has_seeded_client(client):
    sam = next(c for c in client.get(f"{CLIENTS}/").json() if c["id"] == 1)
    assert sam["first_name"] == "Sam" and sam["date_of_birth"] == "2019-04-12" and sam["plan_count"] >= 1


def test_new_client_gets_a_plan(client):
    new = create(client, date_of_birth="2020-02-03", sex="Female")
    assert new["plan_count"] == 0
    plan = client.post(f"{PLANS}/", json={"client_id": new["id"], "bay": "3"}).json()
    info = client.get(f"{PLANS}/{plan['id']}/pages/information/").json()["client"]
    assert info["first_name"] == "Lena" and info["date_of_birth"] == "2020-02-03" and info["sex"] == "Female"
    listed = next(c for c in client.get(f"{CLIENTS}/").json() if c["id"] == new["id"])
    assert listed["plan_count"] == 1


def test_edit_and_clear_optional_fields(client):
    new = create(client, sex="Male")
    edited = client.patch(f"{CLIENTS}/{new['id']}/", json={"last_name": "Ortiz-Reyes", "date_of_birth": "2018-07-01"}).json()
    assert edited["last_name"] == "Ortiz-Reyes" and edited["date_of_birth"] == "2018-07-01" and edited["sex"] == "Male"
    cleared = client.patch(f"{CLIENTS}/{new['id']}/", json={"sex": "", "date_of_birth": None}).json()
    assert cleared["sex"] is None and cleared["date_of_birth"] is None


def test_save_rules(client):
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    assert client.post(f"{CLIENTS}/", json={"first_name": "", "last_name": "X"}).status_code == 422
    assert client.post(f"{CLIENTS}/", json={"first_name": "X"}).status_code == 422
    assert client.post(f"{CLIENTS}/", json={"first_name": "X", "last_name": "Y", "date_of_birth": tomorrow}).status_code == 422
    assert client.patch(f"{CLIENTS}/1/", json={"first_name": None}).status_code == 422
    assert client.patch(f"{CLIENTS}/99999/", json={"sex": "Male"}).status_code == 404


def test_client_with_plans_cannot_be_deleted(client):
    response = client.delete(f"{CLIENTS}/1/")
    assert response.status_code == 409 and "treatment plan" in response.json()["detail"]


def test_delete_removes_client_records(client):
    new = create(client)
    with SessionLocal() as session:
        session.add(ClientGuardian(client_id=new["id"], display_name="Gus Ortiz", role="Father"))
        session.commit()
    assert client.delete(f"{CLIENTS}/{new['id']}/").status_code == 204
    assert all(c["id"] != new["id"] for c in client.get(f"{CLIENTS}/").json())


def test_view_only_can_read_not_change(client):
    viewer = sign_in_with({"admin_clients": "view"}, "Clients viewer")
    assert viewer.get(f"{CLIENTS}/").status_code == 200
    assert viewer.post(f"{CLIENTS}/", json={"first_name": "X", "last_name": "Y"}).status_code == 403
