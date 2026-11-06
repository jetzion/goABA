"""Treatment page."""

import pytest

BASE = "/api/v2/treatment_plans"
HEADER = {"recommendations_explanation": "<p>Begin at 20 hours</p>", "proposed_start_date": "2026-12-01", "duration_in_months": 6}


def url(plan_id):
    return f"{BASE}/{plan_id}/pages/treatment/"


def status(client, plan_id):
    return next(s for s in client.get(f"{BASE}/{plan_id}/pages/").json() if s["page"] == "treatment")


def fields(client, plan_id):
    return {e["field"] for e in status(client, plan_id)["errors"]}


def new_plan(client, bay):
    return client.post(f"{BASE}/", json={"client_id": 1, "bay": bay}).json()["id"]


def test_empty(client, plan_id):
    assert status(client, plan_id)["status"] == "empty"
    data = client.get(url(plan_id)).json()
    assert data["services"] == {} and data["recommendations_explanation"] is None


def test_complete(client, plan_id):
    data = client.patch(url(plan_id), json={**HEADER, "direct_therapy_97153_hours": 20, "direct_therapy_97153_per": "Weekly"}).json()
    assert data["services"]["direct_therapy_97153"] == {"hours": 20, "units": 80, "per": "Weekly"}
    assert data["services"]["assessment_97151"] == {"hours": None, "units": None, "per": None}
    assert status(client, plan_id)["status"] == "completed"


def test_needs_one_service_with_hours(client, plan_id):
    client.patch(url(plan_id), json={**HEADER, "direct_therapy_97153_hours": 0})
    assert fields(client, plan_id) == {"services"}


def test_per_required_only_with_hours(client, plan_id):
    client.patch(url(plan_id), json={**HEADER, "direct_therapy_97153_hours": 20, "care_coordination_99366_hours": 0})
    assert fields(client, plan_id) == {"direct_therapy_97153_per"}


def test_assessment_hours_combined_cap(client, plan_id):
    assert client.patch(url(plan_id), json={"assessment_97151_hours": 5}).status_code == 200
    assert client.patch(url(plan_id), json={"assessment_97152_hours": 4}).status_code == 422
    assert client.patch(url(plan_id), json={"assessment_97152_hours": 3}).status_code == 200


@pytest.mark.parametrize(
    "body",
    [
        {"assessment_97151_hours": 9},
        {"direct_therapy_97153_hours": 100},
        {"duration_in_months": 0},
        {"direct_therapy_97153_per": "Daily"},
        {"therapy_provisioning_description": "Custom"},
    ],
)
def test_save_rules_reject(client, plan_id, body):
    assert client.patch(url(plan_id), json=body).status_code == 422


@pytest.mark.parametrize(
    "bay,expected",
    [
        ("2.6", "A trained behavioral technician"),
        ("7", "A trained behavioral technician"),
        ("6", "A BCBA administers"),
        ("3", "Treatment is provided by Chris Park"),
        ("2.5", None),
        ("2.7", None),
    ],
)
def test_provisioning_by_bay(client, bay, expected):
    text = client.get(url(new_plan(client, bay))).json()["therapy_provisioning_description"]
    assert (text is None) if expected is None else text.startswith(expected)
