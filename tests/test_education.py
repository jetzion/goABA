"""Education page."""

import pytest

BASE = "/api/v2/treatment_plans"

COMPLETE = {
    "education_setting": "In-person public/private",
    "number_of_hours_per_week": 30.5,
    "school_name": "Oak Hill Elementary",
    "school_phone_number": "5125550199",
    "education_description": "<p>Kindergarten, general class</p>",
    "focus_area_description": "<p>Social skills and transitions</p>",
    "iep_or_504_in_place": "IEP",
    "education_support": "Speech pull-out twice weekly",
    "classroom_setting": "General education classroom",
    "attitude_towards_school": "Positive (Generally Enjoys School)",
}


def url(plan_id):
    return f"{BASE}/{plan_id}/pages/education/"


def status(client, plan_id):
    return next(s for s in client.get(f"{BASE}/{plan_id}/pages/").json() if s["page"] == "education")


def test_empty(client, plan_id):
    assert status(client, plan_id)["status"] == "empty"
    assert client.get(url(plan_id)).json()["not_attending_school"] is False


def test_complete_without_evaluation_fields(client, plan_id):
    response = client.patch(url(plan_id), json=COMPLETE)
    assert response.json()["number_of_hours_per_week"] == 30.5
    assert status(client, plan_id)["status"] == "completed"


def test_partial_is_error(client, plan_id):
    client.patch(url(plan_id), json={"school_name": "Oak Hill Elementary"})
    assert status(client, plan_id)["status"] == "error"


def test_not_attending_alone_is_complete(client, plan_id):
    client.patch(url(plan_id), json={"not_attending_school": True})
    assert status(client, plan_id)["status"] == "completed"


def test_not_attending_with_fields_is_error(client, plan_id):
    client.patch(url(plan_id), json={"not_attending_school": True, "school_name": "Oak Hill Elementary"})
    assert status(client, plan_id)["errors"] == [
        {"field": "school_name", "row_id": None, "message": "Must be empty when the child is not attending school"}
    ]


def test_omitted_not_attending_keeps_value(client, plan_id):
    client.patch(url(plan_id), json={"not_attending_school": True})
    response = client.patch(url(plan_id), json={"evaluation_status": "EVALUATED"})
    assert response.json()["not_attending_school"] is True


def test_homeschool_needs_no_school_name_or_phone(client, plan_id):
    body = {**COMPLETE, "education_setting": "Homeschool", "school_name": None, "school_phone_number": None}
    client.patch(url(plan_id), json=body)
    assert status(client, plan_id)["status"] == "completed"


@pytest.mark.parametrize(
    "field,value",
    [
        ("number_of_hours_per_week", 0),
        ("number_of_hours_per_week", 40.5),
        ("number_of_hours_per_week", 10.25),
        ("education_description", "<p>short</p>"),
        ("education_description", "<p>" + "x" * 800 + "</p>"),
        ("evaluation_status", "DONE"),
        ("not_attending_school", None),
    ],
)
def test_save_rules_reject(client, plan_id, field, value):
    assert client.patch(url(plan_id), json={field: value}).status_code == 422
