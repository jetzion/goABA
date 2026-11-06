"""Signing a plan and the read-only state after it."""

import pytest

from app.completion import PageStatusResponse
from app.enums import PAGES

BASE = "/api/v2/treatment_plans"


@pytest.fixture
def all_complete(monkeypatch):
    """Report every page as complete, so signing logic is tested apart from page rules."""
    monkeypatch.setattr(
        "app.routes.plan.all_statuses",
        lambda session, plan: [PageStatusResponse(page=p, status="completed") for p in PAGES],
    )


def sign(client, plan_id, signature="Dana Lee, BCBA"):
    return client.post(f"{BASE}/{plan_id}/sign/", json={"signature": signature})


def test_incomplete_plan_cannot_be_signed(client, plan_id):
    response = sign(client, plan_id)
    assert response.status_code == 422
    assert response.json()["detail"].startswith("Complete every page before signing. Not complete: medical, referral")
    assert client.get(f"{BASE}/{plan_id}/").json()["status"] == "draft"


def test_complete_plan_is_signed(client, plan_id, all_complete):
    plan = sign(client, plan_id).json()
    assert plan["status"] == "signed"
    assert plan["signature"] == "Dana Lee, BCBA"
    assert client.get(f"{BASE}/{plan_id}/").json()["signature"] == "Dana Lee, BCBA"


@pytest.mark.parametrize("signature", ["", " ", "D"])
def test_signature_required(client, plan_id, all_complete, signature):
    assert sign(client, plan_id, signature).status_code == 422


def test_signed_plan_cannot_be_signed_again(client, plan_id, all_complete):
    sign(client, plan_id)
    assert sign(client, plan_id, "Someone Else").status_code == 409


@pytest.mark.parametrize(
    "method,path,body",
    [
        ("patch", "medical/", {"allergies": "Peanuts"}),
        ("post", "referrals/", {"city": "Austin"}),
        ("patch", "medications/", {"no_medication": True}),
        ("patch", "therapy/", {"no_historical_therapy": True}),
        ("patch", "education/", {"not_attending_school": True}),
        ("post", "family/members/", {"full_name": "Ana Rivera"}),
        ("post", "child/backgrounds/", {"background_type": "STRENGTH", "background_description": "Puzzles"}),
        ("patch", "assessment/", {"observations": "<p>Calm and engaged</p>"}),
        ("patch", "crisis/", {"no_crisis_plan_needed": True}),
        ("post", "pcg/goals/", {"goal_name_id": 1}),
        ("patch", "discharge/", {"titration_plan": "<p>Step down</p>"}),
        ("patch", "treatment/", {"duration_in_months": 6}),
    ],
)
def test_signed_plan_rejects_writes(client, plan_id, all_complete, method, path, body):
    sign(client, plan_id)
    response = getattr(client, method)(f"{BASE}/{plan_id}/pages/{path}", json=body)
    assert response.status_code == 409
    assert response.json()["detail"] == "Treatment plan is signed and read-only"


def test_signed_plan_still_reads(client, plan_id, all_complete):
    sign(client, plan_id)
    assert client.get(f"{BASE}/{plan_id}/pages/medical/").status_code == 200
    assert client.get(f"{BASE}/{plan_id}/pages/").status_code == 200
