"""Admin goal-name catalog: list, create, edit, active flag, delete, and what goal pickers offer."""

from tests.test_enforcement import sign_in_with

NAMES = "/api/v2/admin/goal_names"


def create(client, prefix: str, area: str = "Parent training", label: str = "Test goal") -> dict:
    response = client.post(f"{NAMES}/", json={"focus_area": area, "label": label, "prefix": prefix})
    assert response.status_code == 201, response.text
    return response.json()


def offered(client, plan_id: int, section: str = "pcg") -> set[str]:
    """Prefixes a section's goal picker offers. PCG lists them flat; SAG and BRG group them by focus area."""
    page = client.get(f"/api/v2/treatment_plans/{plan_id}/pages/{section}/").json()
    if "available_goals" in page:
        return {g["prefix"] for g in page["available_goals"]}
    return {g["prefix"] for area in page["focus_areas"] for g in area["goals"]}


def test_list_has_seeded_names_and_areas(client):
    data = client.get(f"{NAMES}/").json()
    prefixes = {n["prefix"]: n for n in data["goal_names"]}
    assert prefixes["PT-1"]["focus_area"] == "Parent training" and prefixes["PT-1"]["active"]
    assert not prefixes["COM-9"]["active"]
    assert {"Parent training", "Behavior change", "Communication"} <= set(data["focus_areas"])


def test_new_name_is_offered_then_hidden_when_off(client, plan_id):
    name = create(client, "PT-T1", label="Praises effort")
    assert name["active"] and name["in_use"] == 0
    assert "PT-T1" in offered(client, plan_id)
    assert client.patch(f"{NAMES}/{name['id']}/", json={"active": False}).json()["active"] is False
    assert "PT-T1" not in offered(client, plan_id)
    goal = client.post(f"/api/v2/treatment_plans/{plan_id}/pages/pcg/goals/", json={"goal_name_id": name["id"]})
    assert goal.status_code == 422


def test_inactive_keeps_existing_goals(client, plan_id):
    name = create(client, "PT-T2")
    goal = client.post(f"/api/v2/treatment_plans/{plan_id}/pages/pcg/goals/", json={"goal_name_id": name["id"]})
    assert goal.status_code == 201
    client.patch(f"{NAMES}/{name['id']}/", json={"active": False})
    goals = client.get(f"/api/v2/treatment_plans/{plan_id}/pages/pcg/").json()["goals"]
    assert [g["prefix"] for g in goals] == ["PT-T2"]


def test_skill_area_goes_to_sag(client, plan_id):
    create(client, "MOT-T1", area="Motor skills", label="Uses a pincer grasp")
    assert "MOT-T1" in offered(client, plan_id, "sag")
    assert "MOT-T1" not in offered(client, plan_id, "pcg")


def test_prefix_unique_ignoring_case(client):
    response = client.post(f"{NAMES}/", json={"focus_area": "Communication", "label": "Dup", "prefix": "com-1"})
    assert response.status_code == 409 and "COM-1" in response.json()["detail"]
    name = create(client, "PT-T3")
    assert client.patch(f"{NAMES}/{name['id']}/", json={"prefix": "PT-1"}).status_code == 409


def test_save_rules(client):
    assert client.post(f"{NAMES}/", json={"focus_area": "", "label": "x", "prefix": "X-1"}).status_code == 422
    assert client.post(f"{NAMES}/", json={"focus_area": "Communication", "label": "x"}).status_code == 422
    assert client.patch(f"{NAMES}/1/", json={"label": None}).status_code == 422
    assert client.patch(f"{NAMES}/99999/", json={"label": "x"}).status_code == 404


def test_in_use_cannot_change_area_or_be_deleted(client, plan_id):
    name = create(client, "PT-T4")
    client.post(f"/api/v2/treatment_plans/{plan_id}/pages/pcg/goals/", json={"goal_name_id": name["id"]})
    listed = next(n for n in client.get(f"{NAMES}/").json()["goal_names"] if n["id"] == name["id"])
    assert listed["in_use"] == 1
    moved = client.patch(f"{NAMES}/{name['id']}/", json={"focus_area": "Communication"})
    assert moved.status_code == 409
    assert client.patch(f"{NAMES}/{name['id']}/", json={"label": "Renamed in use"}).status_code == 200
    deleted = client.delete(f"{NAMES}/{name['id']}/")
    assert deleted.status_code == 409 and "Turn it off" in deleted.json()["detail"]


def test_unused_can_be_deleted_and_moved(client):
    name = create(client, "PT-T5")
    assert client.patch(f"{NAMES}/{name['id']}/", json={"focus_area": "Communication"}).json()["focus_area"] == "Communication"
    assert client.delete(f"{NAMES}/{name['id']}/").status_code == 204


def test_view_only_can_read_not_change(client):
    viewer = sign_in_with({"admin_goal_names": "view"}, "Goal names viewer")
    assert viewer.get(f"{NAMES}/").status_code == 200
    assert viewer.post(f"{NAMES}/", json={"focus_area": "Communication", "label": "x", "prefix": "V-1"}).status_code == 403
