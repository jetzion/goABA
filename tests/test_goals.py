"""Goals page: PCG, SAG and BRG."""

import pytest

from app.enums import DSM5_SYMPTOMS

BASE = "/api/v2/treatment_plans"
LONG = "<p>" + "Detailed clinical narrative text. " * 3 + "</p>"
INSTRUCTIONS = "Present the instruction, wait three seconds, prompt as needed, then reinforce."


def url(plan_id, section, path=""):
    return f"{BASE}/{plan_id}/pages/{section}/{path}"


def goals_status(client, plan_id):
    return next(s for s in client.get(f"{BASE}/{plan_id}/pages/").json() if s["page"] == "goals")


def fields(client, plan_id):
    return {e["field"] for e in goals_status(client, plan_id)["errors"]}


def goal_name(client, plan_id, section, prefix):
    data = client.get(url(plan_id, section)).json()
    options = data["available_goals"] if section == "pcg" else [g for a in data["focus_areas"] for g in a["goals"]]
    return next(g["id"] for g in options if g["prefix"] == prefix)


def pcg_goal(client, plan_id, **extra):
    body = {
        "goal_name_id": goal_name(client, plan_id, "pcg", "PT-1"),
        "data_collection_method": "Instances",
        "baseline_date": "2026-01-10",
        "baseline_level": 10,
        "current_level": 10,
        "expected_mastery_date": "06-2026",
        "goal_description": "<p>Caregiver reinforces target behavior</p>",
        "mastery_to": 40,
        **extra,
    }
    return client.post(url(plan_id, "pcg", "goals/"), json=body)


def target_body(name="Praises within 3 seconds", **extra):
    return {"target_name": name, "timeframe": "Short-Term", "baseline_date": "2026-01-10", "baseline_level": 5,
            "description": LONG, "instructions": INSTRUCTIONS, **extra}


# PCG


def test_goals_empty(client, plan_id):
    assert goals_status(client, plan_id)["status"] == "empty"


def test_pcg_goal_complete_with_defaults(client, plan_id):
    goal = pcg_goal(client, plan_id).json()
    assert goal["expected_mastery_date"] == "2026-06"
    assert (goal["mastery_sessions"], goal["mastery_direction"], goal["prefix"]) == (3, "increase", "PT-1")
    assert goals_status(client, plan_id)["status"] == "completed"


def test_goal_name_must_be_in_focus_area(client, plan_id):
    behavior_name = goal_name(client, plan_id, "brg", "BC-1")
    body = {"goal_name_id": behavior_name, "data_collection_method": "Instances"}
    assert client.post(url(plan_id, "pcg", "goals/"), json=body).status_code == 422


def test_inactive_goal_name_rejected(client, plan_id):
    from app.db import SessionLocal
    from app.models import GoalName

    with SessionLocal() as session:
        inactive = session.query(GoalName).filter_by(prefix="COM-9").one().id
    assert client.post(url(plan_id, "sag", "goals/"), json={"goal_name_id": inactive}).status_code == 422


def test_duplicate_goal_name_on_plan(client, plan_id):
    assert pcg_goal(client, plan_id).status_code == 201
    assert pcg_goal(client, plan_id).status_code == 409


def test_goal_name_and_method_cannot_be_cleared(client, plan_id):
    goal = pcg_goal(client, plan_id).json()
    for field in ("goal_name_id", "data_collection_method"):
        assert client.patch(url(plan_id, "pcg", f"goals/{goal['id']}/"), json={field: None}).status_code == 422


def test_field_of_other_method_rejected(client, plan_id):
    assert pcg_goal(client, plan_id, opportunities=10).status_code == 422


def test_method_change_clears_and_defaults(client, plan_id):
    goal = pcg_goal(client, plan_id).json()
    changed = client.patch(url(plan_id, "pcg", f"goals/{goal['id']}/"), json={"data_collection_method": "Percentage"}).json()
    assert changed["mastery_direction"] is None and changed["mastery_to"] is None
    assert changed["mastery_sessions"] == 3
    assert {"pcg.goal.opportunities", "pcg.goal.mastery_responses"} <= fields(client, plan_id)


def test_rate_interval_for_hours(client, plan_id):
    body = {"data_collection_method": "Rate", "rate_unit": "Hours", "rate_interval": 5}
    assert pcg_goal(client, plan_id, **body).status_code == 422
    assert pcg_goal(client, plan_id, **{**body, "rate_interval": 4}).status_code == 201


def test_responses_cannot_exceed_opportunities(client, plan_id):
    body = {"data_collection_method": "Percentage", "mastery_to": None, "opportunities": 5, "mastery_responses": 6}
    assert pcg_goal(client, plan_id, **body).status_code == 422


def test_mastery_target_vs_baseline(client, plan_id):
    goal = pcg_goal(client, plan_id, mastery_to=5).json()
    assert fields(client, plan_id) == {"pcg.goal.mastery_to"}
    client.patch(url(plan_id, "pcg", f"goals/{goal['id']}/"), json={"mastery_direction": "decrease"})
    assert goals_status(client, plan_id)["status"] == "completed"


@pytest.mark.parametrize("body", [{"baseline_level": 101}, {"expected_mastery_date": "2026-06"}, {"mastery_sessions": 0}])
def test_goal_save_rules(client, plan_id, body):
    assert pcg_goal(client, plan_id, **body).status_code == 422


# Targets and stages


def make_target(client, plan_id, **extra):
    goal = pcg_goal(client, plan_id).json()
    target = client.post(url(plan_id, "pcg", f"goals/{goal['id']}/targets/"), json=target_body(**extra)).json()
    return goal["id"], target


def stage_url(plan_id, goal_id, target_id, path=""):
    return url(plan_id, "pcg", f"goals/{goal_id}/targets/{target_id}/stage-history/{path}")


def test_target_starts_new_and_completes(client, plan_id):
    _, target = make_target(client, plan_id)
    assert target["current_stage"] == "New" and len(target["stage_history"]) == 1
    assert goals_status(client, plan_id)["status"] == "completed"


def test_target_name_minimum(client, plan_id):
    make_target(client, plan_id, target_name="Short")
    assert fields(client, plan_id) == {"pcg.target.target_name"}


def test_target_method_fields_must_match_goal(client, plan_id):
    goal = pcg_goal(client, plan_id).json()
    response = client.post(url(plan_id, "pcg", f"goals/{goal['id']}/targets/"), json=target_body(opportunities=10))
    assert response.status_code == 422


def test_stage_transitions(client, plan_id):
    goal_id, target = make_target(client, plan_id)
    new_date = target["stage_history"][0]["stage_date"]
    add = lambda stage, day: client.post(stage_url(plan_id, goal_id, target["id"]), json={"stage": stage, "stage_date": day})  # noqa: E731
    assert add("Mastered", "2099-01-01").status_code == 422
    assert add("Acquisition", new_date).status_code == 201
    assert add("On-hold", new_date).status_code == 422
    assert add("On-hold", "2099-01-01").status_code == 201
    assert add("Mastered", "2099-01-02").status_code == 422
    assert add("Acquisition", "2099-01-02").status_code == 201
    assert add("Discontinued", "2099-01-01").status_code == 422
    history = add("Discontinued", "2099-01-03").json()["stage_history"]
    assert [s["stage"] for s in history] == ["New", "Acquisition", "On-hold", "Acquisition", "Discontinued"]


def test_stage_edit_and_delete(client, plan_id):
    goal_id, target = make_target(client, plan_id)
    first = target["stage_history"][0]
    moved = client.post(stage_url(plan_id, goal_id, target["id"]), json={"stage": "Acquisition", "stage_date": "2099-02-01"}).json()
    second = moved["stage_history"][1]
    assert client.patch(stage_url(plan_id, goal_id, target["id"], f"{second['id']}/"), json={"stage_date": "2000-01-01"}).status_code == 422
    assert client.patch(stage_url(plan_id, goal_id, target["id"], f"{second['id']}/"), json={"stage_date": "2099-03-01"}).status_code == 200
    assert client.delete(stage_url(plan_id, goal_id, target["id"], f"{first['id']}/")).status_code == 422
    assert client.delete(stage_url(plan_id, goal_id, target["id"], f"{second['id']}/")).status_code == 204


# SAG


def sag_goal(client, plan_id, **extra):
    body = {
        "goal_name_id": goal_name(client, plan_id, "sag", "COM-1"),
        "data_collection_method": "Percentage",
        "opportunities": 10,
        "baseline_date": "2026-01-10",
        "baseline_level": 2,
        "current_level": 2,
        "frequency": "Once a week",
        "expected_mastery_date": "06-2026",
        "goal_description": "<p>Requests items with words</p>",
        "acquisition_responses": 8,
        "generalization_responses": 8,
        "maintenance_responses": 9,
        **extra,
    }
    return client.post(url(plan_id, "sag", "goals/"), json=body)


def test_sag_defaults_and_complete(client, plan_id):
    goal = sag_goal(client, plan_id).json()
    assert (goal["acquisition_sessions"], goal["generalization_sessions"], goal["maintenance_sessions"]) == (3, 3, 10)
    assert goals_status(client, plan_id)["status"] == "completed"


def test_sag_percentage_rules(client, plan_id):
    sag_goal(client, plan_id, baseline_level=10, acquisition_responses=7, maintenance_sessions=7)
    assert fields(client, plan_id) == {"sag.goal.baseline_level", "sag.goal.acquisition_responses", "sag.goal.maintenance_sessions"}


def test_sag_probe_to_acquisition_is_automatic(client, plan_id):
    goal = sag_goal(client, plan_id).json()
    target = client.post(url(plan_id, "sag", f"goals/{goal['id']}/targets/"), json=target_body(name="Requests juice with a word", opportunities=10)).json()
    stages = url(plan_id, "sag", f"goals/{goal['id']}/targets/{target['id']}/stage-history/")
    assert client.post(stages, json={"stage": "Probe", "stage_date": target["stage_history"][0]["stage_date"]}).status_code == 201
    response = client.post(stages, json={"stage": "Acquisition", "stage_date": "2099-01-01"})
    assert response.status_code == 422 and "automatically" in response.json()["detail"]


def test_sag_rejects_parent_training_goal(client, plan_id):
    assert sag_goal(client, plan_id, goal_name_id=goal_name(client, plan_id, "pcg", "PT-1")).status_code == 422


# BRG


def add_behavior(client, plan_id, symptom=DSM5_SYMPTOMS[0]):
    body = {"behavior": "<p>Hits peers when toys are taken</p>", "dsm5_symptom": symptom, "parent_concerns": "<p>Hurts siblings at home</p>"}
    return client.post(f"{BASE}/{plan_id}/pages/assessment/behaviors/", json=body).json()["id"]


def brg_goal(client, plan_id, **extra):
    body = {
        "goal_name_id": goal_name(client, plan_id, "brg", "BC-1"),
        "dsm5_symptom": DSM5_SYMPTOMS[0],
        "data_collection_method": "Instances",
        "baseline_date": "2026-01-10",
        "baseline_level": 12,
        "current_level": 12,
        "frequency": "Twice a week",
        "expected_mastery_date": "09-2026",
        "mastery_direction": "decrease",
        "mastery_to": 2,
        **{f: LONG for f in ("operational_definition", "objective", "antecedent_modifications", "consequence_modifications", "goal_description")},
        **extra,
    }
    return client.post(url(plan_id, "brg", "goals/"), json=body)


def test_brg_symptom_must_be_on_assessment(client, plan_id):
    assert brg_goal(client, plan_id).status_code == 422
    add_behavior(client, plan_id)
    assert brg_goal(client, plan_id).status_code == 201


def test_brg_needs_hypothesized_functions(client, plan_id):
    add_behavior(client, plan_id)
    goal = brg_goal(client, plan_id).json()
    assert fields(client, plan_id) == {"brg.goal.hypothesized_functions"}
    functions = url(plan_id, "brg", f"goals/{goal['id']}/hypothesized-functions/")
    assert client.post(functions, json={"function_date": "2026-01-10", "functions": ["Attention", "Attention"]}).status_code == 422
    assert client.post(functions, json={"function_date": "2026-01-10", "functions": []}).status_code == 422
    saved = client.post(functions, json={"function_date": "2026-01-10", "functions": ["Attention", "Tangible"]})
    assert saved.status_code == 201
    assert client.post(functions, json={"function_date": "2026-01-10", "functions": ["Sensory"]}).status_code == 409
    assert goals_status(client, plan_id)["status"] == "completed"
    entry = saved.json()["hypothesized_functions"][0]["id"]
    assert client.delete(url(plan_id, "brg", f"goals/{goal['id']}/hypothesized-functions/{entry}/")).status_code == 204


def test_brg_rejects_percentage(client, plan_id):
    add_behavior(client, plan_id)
    assert brg_goal(client, plan_id, data_collection_method="Percentage", mastery_direction=None, mastery_to=None).status_code == 422


def test_brg_links_sag_goals(client, plan_id):
    add_behavior(client, plan_id)
    sag = sag_goal(client, plan_id).json()
    other_plan = client.post(f"{BASE}/", json={"client_id": 1, "bay": "3"}).json()["id"]
    other_sag = sag_goal(client, other_plan).json()
    assert brg_goal(client, plan_id, linked_sag_goal_ids=[other_sag["id"]]).status_code == 422
    assert brg_goal(client, plan_id, linked_sag_goal_ids=[sag["id"], sag["id"]]).status_code == 422
    goal = brg_goal(client, plan_id, linked_sag_goal_ids=[sag["id"]]).json()
    assert goal["linked_sag_goal_ids"] == [sag["id"]]
    linked = client.get(url(plan_id, "sag")).json()["goals"][0]["linked_brg_goals"]
    assert linked == [{"id": goal["id"], "goal_name": "Reduce aggression"}]


def test_brg_symptom_removed_from_assessment_is_error(client, plan_id):
    behavior_id = add_behavior(client, plan_id)
    goal = brg_goal(client, plan_id).json()
    client.post(url(plan_id, "brg", f"goals/{goal['id']}/hypothesized-functions/"), json={"function_date": "2026-01-10", "functions": ["Attention"]})
    client.delete(f"{BASE}/{plan_id}/pages/assessment/behaviors/{behavior_id}/")
    assert fields(client, plan_id) == {"brg.goal.dsm5_symptom"}


def test_any_section_error_marks_goals(client, plan_id):
    sag_goal(client, plan_id)
    pcg_goal(client, plan_id, mastery_to=1)
    assert goals_status(client, plan_id)["status"] == "error"
