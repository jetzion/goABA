"""Discharge page."""

import pytest

from app.enums import DISCHARGE_REASONS

BASE = "/api/v2/treatment_plans"
LONG = "<p>" + "Detailed clinical narrative text. " * 3 + "</p>"
INFO = {f: LONG for f in ("mastery_of_program_goals", "titration_plan", "readiness_to_step_down", "care_coordination")}


def url(plan_id, path=""):
    return f"{BASE}/{plan_id}/pages/discharge/{path}"


def status(client, plan_id):
    return next(s for s in client.get(f"{BASE}/{plan_id}/pages/").json() if s["page"] == "discharge")


def test_empty(client, plan_id):
    assert status(client, plan_id)["status"] == "empty"


def test_complete(client, plan_id):
    client.patch(url(plan_id), json=INFO)
    assert {e["field"] for e in status(client, plan_id)["errors"]} == {"reasons"}
    client.post(url(plan_id, "reasons/"), json={"reason": DISCHARGE_REASONS[0]})
    assert status(client, plan_id)["status"] == "completed"


def test_reason_alone_is_error(client, plan_id):
    client.post(url(plan_id, "reasons/"), json={"reason": DISCHARGE_REASONS[1]})
    assert {e["field"] for e in status(client, plan_id)["errors"]} == set(INFO)


@pytest.mark.parametrize(
    "body",
    [
        {"reason": "Other"},
        {"reason": "Other", "explanation": "abc"},
        {"reason": DISCHARGE_REASONS[0], "explanation": "Not allowed here"},
        {"reason": "Moved away"},
        {},
    ],
)
def test_reason_rules(client, plan_id, body):
    assert client.post(url(plan_id, "reasons/"), json=body).status_code == 422


def test_other_with_explanation(client, plan_id):
    reason = client.post(url(plan_id, "reasons/"), json={"reason": "Other", "explanation": "Family relocating"}).json()
    assert reason["explanation"] == "Family relocating"
    assert client.delete(url(plan_id, f"reasons/{reason['id']}/")).status_code == 204


def test_duplicate_reason(client, plan_id):
    body = {"reason": DISCHARGE_REASONS[2]}
    assert client.post(url(plan_id, "reasons/"), json=body).status_code == 201
    assert client.post(url(plan_id, "reasons/"), json=body).status_code == 409
