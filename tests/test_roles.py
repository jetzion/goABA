"""Admin roles API: list, create, rename, delete, matrix cells and the Admin lock."""

from sqlalchemy import select

from app.db import SessionLocal
from app.models import AppUser, Role
from tests.test_enforcement import sign_in_with

ROLES = "/api/v2/admin/roles"


def admin_role_id() -> int:
    with SessionLocal() as session:
        return session.scalar(select(Role.id).where(Role.name == "Admin"))


def create(client, name: str) -> dict:
    response = client.post(f"{ROLES}/", json={"name": name})
    assert response.status_code == 201
    return response.json()


def test_list_has_matrix_keys_and_full_admin(client):
    data = client.get(f"{ROLES}/").json()
    keys = {k["key"]: k for k in data["keys"]}
    assert keys["information"]["allowed"] == ["none", "view"]
    assert keys["sign_plan"] == {"key": "sign_plan", "group": "action", "allowed": ["none", "edit"]}
    assert keys["admin_roles"]["group"] == "admin"
    admin = data["roles"][0]
    assert admin["name"] == "Admin" and admin["locked"] and admin["user_count"] >= 1
    assert admin["permissions"]["medical"] == "edit" and admin["permissions"]["information"] == "view"


def test_create_starts_with_no_access(client):
    role = create(client, "BCBA roles test")
    assert not role["locked"] and role["user_count"] == 0
    assert set(role["permissions"].values()) == {"none"}


def test_names_unique_ignoring_case(client):
    create(client, "Biller roles test")
    assert client.post(f"{ROLES}/", json={"name": "biller ROLES test"}).status_code == 409
    assert client.post(f"{ROLES}/", json={"name": "admin"}).status_code == 409
    assert client.post(f"{ROLES}/", json={"name": "  "}).status_code == 422


def test_rename(client):
    role = create(client, "Rename me")
    renamed = client.patch(f"{ROLES}/{role['id']}/", json={"name": "Renamed role"}).json()
    assert renamed["name"] == "Renamed role"
    assert client.patch(f"{ROLES}/{role['id']}/", json={"name": "Admin"}).status_code == 409


def test_set_cells(client):
    role = create(client, "Cells test")
    url = f"{ROLES}/{role['id']}/permissions"
    assert client.put(f"{url}/medical/", json={"level": "view"}).json()["permissions"]["medical"] == "view"
    assert client.put(f"{url}/medical/", json={"level": "edit"}).json()["permissions"]["medical"] == "edit"
    assert client.put(f"{url}/sign_plan/", json={"level": "edit"}).json()["permissions"]["sign_plan"] == "edit"
    assert client.put(f"{url}/information/", json={"level": "edit"}).status_code == 422
    assert client.put(f"{url}/sign_plan/", json={"level": "view"}).status_code == 422
    assert client.put(f"{url}/medical/", json={"level": "owner"}).status_code == 422
    assert client.put(f"{url}/nope/", json={"level": "view"}).status_code == 404


def test_admin_is_locked(client):
    admin = admin_role_id()
    assert client.patch(f"{ROLES}/{admin}/", json={"name": "Boss"}).status_code == 409
    assert client.put(f"{ROLES}/{admin}/permissions/medical/", json={"level": "view"}).status_code == 409
    assert client.delete(f"{ROLES}/{admin}/").status_code == 409
    assert client.get(f"{ROLES}/").json()["roles"][0]["permissions"]["medical"] == "edit"


def test_delete(client):
    role = create(client, "Delete me")
    assert client.delete(f"{ROLES}/{role['id']}/").status_code == 204
    assert client.delete(f"{ROLES}/{role['id']}/").status_code == 404


def test_cannot_delete_role_in_use(client):
    role = create(client, "In use")
    with SessionLocal() as session:
        session.add(AppUser(display_name="Uma User", role_id=role["id"]))
        session.commit()
    response = client.delete(f"{ROLES}/{role['id']}/")
    assert response.status_code == 409 and "1 user" in response.json()["detail"]


def test_view_only_admin_can_read_not_change(client):
    viewer = sign_in_with({"admin_roles": "view"}, "Roles viewer")
    assert viewer.get(f"{ROLES}/").status_code == 200
    assert viewer.post(f"{ROLES}/", json={"name": "Sneaky"}).status_code == 403
