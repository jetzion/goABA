"""Admin providers API: list, create, rename, active flag, delete, and links from Users."""

from tests.test_enforcement import sign_in_with

PROVIDERS = "/api/v2/admin/providers"
USERS = "/api/v2/admin/users"


def create(client, name: str) -> dict:
    response = client.post(f"{PROVIDERS}/", json={"display_name": name})
    assert response.status_code == 201, response.text
    return response.json()


def any_role_id(client) -> int:
    return client.get(f"{USERS}/").json()["roles"][-1]["id"]


def test_list_shows_usage(client):
    dana = next(p for p in client.get(f"{PROVIDERS}/").json() if p["id"] == 1)
    assert dana["active"] and dana["user"] == "Dana Lee, BCBA" and dana["assignments"] >= 1 and dana["plans"] >= 1


def test_create_rename_and_link_on_users(client):
    provider = create(client, "Riley Tech, RBT")
    assert provider == {"id": provider["id"], "display_name": "Riley Tech, RBT", "active": True, "user": None, "assignments": 0, "plans": 0}
    renamed = client.patch(f"{PROVIDERS}/{provider['id']}/", json={"display_name": "Riley Tran, RBT"}).json()
    assert renamed["display_name"] == "Riley Tran, RBT"
    assert any(p["id"] == provider["id"] for p in client.get(f"{USERS}/").json()["providers"])
    user = client.post(f"{USERS}/", json={"display_name": "Riley Tran", "role_id": any_role_id(client), "provider_id": provider["id"]})
    assert user.status_code == 201
    assert next(p for p in client.get(f"{PROVIDERS}/").json() if p["id"] == provider["id"])["user"] == "Riley Tran"


def test_inactive_not_offered_or_newly_linked(client):
    provider = create(client, "Off Provider")
    client.patch(f"{PROVIDERS}/{provider['id']}/", json={"active": False})
    assert all(p["id"] != provider["id"] for p in client.get(f"{USERS}/").json()["providers"])
    response = client.post(f"{USERS}/", json={"display_name": "Late Link", "role_id": any_role_id(client), "provider_id": provider["id"]})
    assert response.status_code == 422 and "turned off" in response.json()["detail"]


def test_linked_provider_turned_off_stays_linked(client):
    provider = create(client, "Kept Provider")
    user = client.post(f"{USERS}/", json={"display_name": "Kept User", "role_id": any_role_id(client), "provider_id": provider["id"]}).json()
    client.patch(f"{PROVIDERS}/{provider['id']}/", json={"active": False})
    assert any(p["id"] == provider["id"] for p in client.get(f"{USERS}/").json()["providers"])
    assert client.patch(f"{USERS}/{user['id']}/", json={"display_name": "Kept User 2", "provider_id": provider["id"]}).status_code == 200


def test_delete_rules(client):
    unused = create(client, "Unused Provider")
    assert client.delete(f"{PROVIDERS}/{unused['id']}/").status_code == 204
    in_use = client.delete(f"{PROVIDERS}/1/")
    assert in_use.status_code == 409 and "Turn it off" in in_use.json()["detail"]


def test_save_rules(client):
    assert client.post(f"{PROVIDERS}/", json={"display_name": ""}).status_code == 422
    assert client.patch(f"{PROVIDERS}/1/", json={"display_name": None}).status_code == 422
    assert client.patch(f"{PROVIDERS}/99999/", json={"active": False}).status_code == 404


def test_view_only_can_read_not_change(client):
    viewer = sign_in_with({"admin_providers": "view"}, "Providers viewer")
    assert viewer.get(f"{PROVIDERS}/").status_code == 200
    assert viewer.post(f"{PROVIDERS}/", json={"display_name": "X"}).status_code == 403
