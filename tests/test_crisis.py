"""Crisis page."""

from app.enums import DSM5_SYMPTOMS

BASE = "/api/v2/treatment_plans"
LONG = "<p>" + "Detailed clinical narrative text. " * 3 + "</p>"
COMPLETE = {
    "crisis_creation_date": "2027-03-01",
    "operational_definition": LONG,
    "antecedent_interventions": LONG,
    "precursors_action_steps": LONG,
    "escalation_intervention_plan": LONG,
    "follow_up_steps": LONG,
    "functional_behavior": ["Escape-Maintained"],
    "consequence_strategies": LONG,
}


def url(plan_id, path=""):
    return f"{BASE}/{plan_id}/pages/crisis/{path}"


def status(client, plan_id):
    return next(s for s in client.get(f"{BASE}/{plan_id}/pages/").json() if s["page"] == "crisis")


def behavior(client, plan_id, text="<p>Hits peers when toys are taken</p>"):
    body = {"behavior": text, "dsm5_symptom": DSM5_SYMPTOMS[0], "parent_concerns": "<p>Hurts siblings at home</p>"}
    return client.post(f"{BASE}/{plan_id}/pages/assessment/behaviors/", json=body).json()["id"]


def test_empty(client, plan_id):
    assert status(client, plan_id)["status"] == "empty"
    assert client.get(url(plan_id)).json() == {"no_crisis_plan_needed": False, "plans": [], "available_behaviors": []}


def test_not_needed_is_complete(client, plan_id):
    client.patch(url(plan_id), json={"no_crisis_plan_needed": True})
    assert status(client, plan_id)["status"] == "completed"


def test_complete_plan_with_future_date(client, plan_id):
    behavior_id = behavior(client, plan_id)
    response = client.post(url(plan_id), json={"assessment_behavior_id": behavior_id, **COMPLETE})
    assert response.status_code == 201
    assert status(client, plan_id)["status"] == "completed"
    choices = client.get(url(plan_id)).json()["available_behaviors"]
    assert choices == [{"id": behavior_id, "label": "Hits peers when toys are taken", "dsm5_symptom": DSM5_SYMPTOMS[0]}]


def test_create_requires_behavior(client, plan_id):
    assert client.post(url(plan_id), json=COMPLETE).status_code == 422


def test_behavior_must_be_on_this_plan(client, plan_id):
    other = client.post(f"{BASE}/", json={"client_id": 1, "bay": "3"}).json()["id"]
    assert client.post(url(plan_id), json={"assessment_behavior_id": behavior(client, other)}).status_code == 422


def test_one_plan_per_behavior(client, plan_id):
    behavior_id = behavior(client, plan_id)
    assert client.post(url(plan_id), json={"assessment_behavior_id": behavior_id}).status_code == 201
    assert client.post(url(plan_id), json={"assessment_behavior_id": behavior_id}).status_code == 409


def test_behavior_cannot_be_cleared(client, plan_id):
    created = client.post(url(plan_id), json={"assessment_behavior_id": behavior(client, plan_id)}).json()
    assert client.patch(url(plan_id, f"{created['id']}/"), json={"assessment_behavior_id": None}).status_code == 422


def test_partial_plan_is_error(client, plan_id):
    created = client.post(url(plan_id), json={"assessment_behavior_id": behavior(client, plan_id)}).json()
    fields = {e["field"] for e in status(client, plan_id)["errors"]}
    assert fields == set(COMPLETE)
    client.patch(url(plan_id, f"{created['id']}/"), json=COMPLETE)
    assert status(client, plan_id)["status"] == "completed"


def test_save_rules(client, plan_id):
    behavior_id = behavior(client, plan_id)
    assert client.post(url(plan_id), json={"assessment_behavior_id": behavior_id, "crisis_creation_date": "2027-03-02"}).status_code == 422
    assert client.post(url(plan_id), json={"assessment_behavior_id": behavior_id, "functional_behavior": ["Boredom"]}).status_code == 422
    assert client.post(url(plan_id), json={"assessment_behavior_id": behavior_id, "functional_behavior": ["Escape-Maintained"] * 2}).status_code == 422


def test_behavior_with_crisis_plan_cannot_be_deleted(client, plan_id):
    behavior_id = behavior(client, plan_id)
    created = client.post(url(plan_id), json={"assessment_behavior_id": behavior_id}).json()
    behavior_url = f"{BASE}/{plan_id}/pages/assessment/behaviors/{behavior_id}/"
    assert client.delete(behavior_url).status_code == 409
    client.delete(url(plan_id, f"{created['id']}/"))
    assert client.delete(behavior_url).status_code == 204


def test_templates(client, plan_id):
    assert len(client.get(url(plan_id, "templates/")).json()) == 6
