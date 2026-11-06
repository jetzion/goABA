"""Admin users API: list, create, edit, delete and the safety rules."""

import pytest

from tests.test_enforcement import sign_in_with

USERS = "/api/v2/admin/users"


@pytest.fixture
def role_id(client) -> int:
    """A plain role to put users in."""
    roles = client.get("/api/v2/admin/roles/").json()["roles"]
    found = next((r for r in roles if r["name"] == "Users test role"), None)
    return found["id"] if found else client.post("/api/v2/admin/roles/", json={"name": "Users test role"}).json()["id"]


def admin_role_id(client) -> int:
    return client.get(f"{USERS}/").json()["roles"][0]["id"]


def test_list_has_users_roles_and_providers(client):
    data = client.get(f"{USERS}/").json()
    dana = next(u for u in data["users"] if u["id"] == 1)
    assert dana["role"] == "Admin" and dana["provider_id"] == 1
    assert data["roles"][0]["name"] == "Admin"
    assert {"id": 2, "name": "Chris Park"} in data["providers"]


def test_create_and_edit(client, role_id):
    user = client.post(f"{USERS}/", json={"display_name": "Casey Clerk", "role_id": role_id}).json()
    assert user["role_id"] == role_id and user["provider_id"] is None
    edited = client.patch(f"{USERS}/{user['id']}/", json={"display_name": "Casey C.", "provider_id": 2}).json()
    assert edited["display_name"] == "Casey C." and edited["provider_id"] == 2 and edited["role_id"] == role_id
    assert client.patch(f"{USERS}/{user['id']}/", json={"provider_id": None}).json()["provider_id"] is None
    assert client.delete(f"{USERS}/{user['id']}/").status_code == 204


def test_save_rules(client, role_id):
    assert client.post(f"{USERS}/", json={"display_name": "", "role_id": role_id}).status_code == 422
    assert client.post(f"{USERS}/", json={"display_name": "No Role"}).status_code == 422
    assert client.post(f"{USERS}/", json={"display_name": "Bad Role", "role_id": 9999}).status_code == 422
    assert client.post(f"{USERS}/", json={"display_name": "Bad Provider", "role_id": role_id, "provider_id": 9999}).status_code == 422
    assert client.patch(f"{USERS}/1/", json={"display_name": None}).status_code == 422


def test_one_user_per_provider(client, role_id):
    response = client.post(f"{USERS}/", json={"display_name": "Second Dana", "role_id": role_id, "provider_id": 1})
    assert response.status_code == 409 and "already linked" in response.json()["detail"]


def test_last_admin_cannot_lose_the_role(client, role_id):
    response = client.patch(f"{USERS}/1/", json={"role_id": role_id})
    assert response.status_code == 409 and "last Admin" in response.json()["detail"]


def test_two_admins_then_one_can_step_down(client, role_id):
    second = client.post(f"{USERS}/", json={"display_name": "Ada Admin", "role_id": admin_role_id(client)}).json()
    assert client.patch(f"{USERS}/{second['id']}/", json={"role_id": role_id}).status_code == 200
    client.delete(f"{USERS}/{second['id']}/")


def test_cannot_delete_yourself(client):
    response = client.delete(f"{USERS}/1/")
    assert response.status_code == 409 and "yourself" in response.json()["detail"]


def test_cannot_delete_last_admin(client):
    manager = sign_in_with({"admin_users": "edit"}, "User manager")
    response = manager.delete(f"{USERS}/1/")
    assert response.status_code == 409 and "last Admin" in response.json()["detail"]


def test_view_only_can_read_not_change(client):
    viewer = sign_in_with({"admin_users": "view"}, "User viewer")
    assert viewer.get(f"{USERS}/").status_code == 200
    assert viewer.patch(f"{USERS}/1/", json={"display_name": "Hacked"}).status_code == 403
