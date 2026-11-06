"""Assessment page."""

import pytest

from app.enums import DSM5_SYMPTOMS, READINESS_ITEMS
from app.routes.assessment import UPLOAD_DIR

BASE = "/api/v2/treatment_plans"
LONG = "<p>" + "Detailed clinical narrative text. " * 3 + "</p>"
SYMPTOM = DSM5_SYMPTOMS[3]

INFO = {
    "initial_assessment_date": "2026-01-10",
    "diagnostic_report_reviewed": True,
    "reassessment_date": "2026-07-10",
    "parent_interview_summary": LONG,
    "assessment_results": LONG,
    "priorities": LONG,
    "observations": "<p>Calm and engaged</p>",
}
METHOD = {
    "tool": "VB-MAPP",
    "assessment_date": "2026-01-12",
    "rationale": LONG,
    "selection_rationale": LONG,
    "tool_description": LONG,
    "client_score": LONG,
}
BEHAVIOR = {
    "behavior": "<p>Lines up toys for long periods</p>",
    "dsm5_symptom": SYMPTOM,
    "parent_concerns": "<p>Upset when the line is moved</p>",
}


def url(plan_id, path=""):
    return f"{BASE}/{plan_id}/pages/assessment/{path}"


def status(client, plan_id):
    return next(s for s in client.get(f"{BASE}/{plan_id}/pages/").json() if s["page"] == "assessment")


def fields(client, plan_id):
    return {e["field"] for e in status(client, plan_id)["errors"]}


def fill(client, plan_id):
    client.patch(url(plan_id), json=INFO)
    client.post(url(plan_id, "methods/"), json=METHOD)
    return client.post(url(plan_id, "behaviors/"), json=BEHAVIOR).json()


def test_empty(client, plan_id):
    assert status(client, plan_id)["status"] == "empty"
    data = client.get(url(plan_id)).json()
    assert len(data["readiness_items"]) == 19
    assert data["readiness_scores"] == {"child": 0, "caregiver": 0, "environment": 0, "overall": 0}


def test_complete(client, plan_id):
    fill(client, plan_id)
    assert status(client, plan_id) == {"page": "assessment", "status": "completed", "errors": []}
    assert client.get(url(plan_id)).json()["dsm5_symptoms"] == [SYMPTOM]


def test_long_text_needs_60_visible(client, plan_id):
    fill(client, plan_id)
    client.patch(url(plan_id), json={"priorities": "<p>Short</p>"})
    assert fields(client, plan_id) == {"priorities"}


def test_reassessment_after_initial(client, plan_id):
    fill(client, plan_id)
    client.patch(url(plan_id), json={"reassessment_date": "2026-01-01"})
    assert fields(client, plan_id) == {"reassessment_date"}


@pytest.mark.parametrize(
    "body",
    [
        {"additional_files_viewed": ["School reports", "School reports"]},
        {"additional_files_viewed": ["Tax returns"]},
        {"barriers": ["Rain"]},
        {"observations": "<p>ok</p>"},
    ],
)
def test_save_rules_reject(client, plan_id, body):
    assert client.patch(url(plan_id), json=body).status_code == 422


def test_maladaptive_rules(client, plan_id):
    behavior = fill(client, plan_id)
    client.patch(url(plan_id), json={"no_maladaptive_behavior": True})
    assert fields(client, plan_id) == {"no_maladaptive_behavior"}
    client.delete(url(plan_id, f"behaviors/{behavior['id']}/"))
    assert status(client, plan_id)["status"] == "completed"
    client.patch(url(plan_id), json={"no_maladaptive_behavior": False})
    assert fields(client, plan_id) == {"no_maladaptive_behavior"}


def test_behavior_save_rules(client, plan_id):
    assert client.post(url(plan_id, "behaviors/"), json={"behavior": "<p>Short</p>"}).status_code == 422
    assert client.post(url(plan_id, "behaviors/"), json={"dsm5_symptom": "Other"}).status_code == 422


def test_needs_a_method(client, plan_id):
    client.patch(url(plan_id), json=INFO)
    client.post(url(plan_id, "behaviors/"), json=BEHAVIOR)
    assert fields(client, plan_id) == {"methods"}


def test_partial_method_is_error(client, plan_id):
    fill(client, plan_id)
    method = client.post(url(plan_id, "methods/"), json={"tool": "AFLS"}).json()
    page = status(client, plan_id)
    assert {e["row_id"] for e in page["errors"]} == {method["id"]}


def test_visual_upload_and_completion(client, plan_id):
    fill(client, plan_id)
    method_id = client.get(url(plan_id)).json()["methods"][0]["id"]
    files = [("files", ("chart.png", b"\x89PNG fake", "image/png"))]
    visual = client.post(url(plan_id, f"methods/{method_id}/visuals/"), files=files).json()[0]
    assert visual["url"].startswith("/uploads/") and visual["url"].endswith(".png")
    assert client.get(visual["url"]).content == b"\x89PNG fake"
    assert fields(client, plan_id) == {"title", "analysis"}
    client.patch(url(plan_id, f"methods/{method_id}/visuals/{visual['id']}/"), json={"title": "Mand progress chart", "analysis": "<p>Mands rose steadily over 6 weeks</p>"})
    assert status(client, plan_id)["status"] == "completed"
    replaced = client.patch(url(plan_id, f"methods/{method_id}/visuals/{visual['id']}/file/"), files={"file": ("new.jpg", b"jpg", "image/jpeg")}).json()
    assert replaced["url"].endswith(".jpg")
    assert client.delete(url(plan_id, f"methods/{method_id}/visuals/{visual['id']}/")).status_code == 204


def test_visual_rejects_other_files(client, plan_id):
    fill(client, plan_id)
    method_id = client.get(url(plan_id)).json()["methods"][0]["id"]
    files = [("files", ("notes.txt", b"hi", "text/plain"))]
    assert client.post(url(plan_id, f"methods/{method_id}/visuals/"), files=files).status_code == 422


@pytest.mark.parametrize("name", ["x.html", "x.svg", "x", "x.png.html"])
def test_visual_rejects_unsafe_extensions(client, plan_id, name):
    fill(client, plan_id)
    method_id = client.get(url(plan_id)).json()["methods"][0]["id"]
    files = [("files", (name, b"<script>alert(1)</script>", "image/png"))]
    assert client.post(url(plan_id, f"methods/{method_id}/visuals/"), files=files).status_code == 422


def test_visual_files_removed_from_disk(client, plan_id):
    fill(client, plan_id)
    method_id = client.get(url(plan_id)).json()["methods"][0]["id"]
    files = [("files", ("chart.png", b"png", "image/png"))]
    visual = client.post(url(plan_id, f"methods/{method_id}/visuals/"), files=files).json()[0]
    first = UPLOAD_DIR / visual["url"].removeprefix("/uploads/")
    replaced = client.patch(url(plan_id, f"methods/{method_id}/visuals/{visual['id']}/file/"), files={"file": ("new.pdf", b"pdf", "application/pdf")}).json()
    second = UPLOAD_DIR / replaced["url"].removeprefix("/uploads/")
    assert not first.exists() and second.exists()
    client.delete(url(plan_id, f"methods/{method_id}/visuals/{visual['id']}/"))
    assert not second.exists()


def test_method_delete_removes_visual_files(client, plan_id):
    fill(client, plan_id)
    method_id = client.get(url(plan_id)).json()["methods"][0]["id"]
    files = [("files", ("chart.png", b"png", "image/png"))]
    visual = client.post(url(plan_id, f"methods/{method_id}/visuals/"), files=files).json()[0]
    client.delete(url(plan_id, f"methods/{method_id}/"))
    assert not (UPLOAD_DIR / visual["url"].removeprefix("/uploads/")).exists()


def test_telehealth(client, plan_id):
    fill(client, plan_id)
    client.patch(url(plan_id), json={"telehealth_readiness_assessment_needed": True})
    missing = fields(client, plan_id)
    assert "telehealth_assessment_date" in missing and "readiness_attends_to_screen" in missing
    client.patch(url(plan_id), json={"telehealth_assessment_date": "2026-01-15"})
    for items in READINESS_ITEMS.values():
        for item in items:
            response = client.patch(url(plan_id, f"readiness/{item}/"), json={"readiness": "Somewhat", "notes": "Observed in session"})
            assert response.status_code == 200
    assert status(client, plan_id)["status"] == "completed"
    assert client.get(url(plan_id)).json()["readiness_scores"] == {"child": 6, "caregiver": 7, "environment": 6, "overall": 19}
    data = client.patch(url(plan_id), json={"telehealth_readiness_assessment_needed": False}).json()
    assert data["telehealth_assessment_date"] is None
    assert {i["readiness"] for i in data["readiness_items"]} == {None}
    assert status(client, plan_id)["status"] == "completed"


def test_readiness_rules(client, plan_id):
    assert client.patch(url(plan_id, "readiness/flying/"), json={"readiness": "Ready"}).status_code == 404
    assert client.patch(url(plan_id, "readiness/lighting/"), json={"notes": "dim"}).status_code == 422


def test_templates(client, plan_id):
    data = client.get(url(plan_id, "templates/")).json()
    assert set(data["page"]) == {"parent_interview_summary", "assessment_results", "priorities"}
    assert set(data["methods"]["VB-MAPP"]) == {"rationale", "selection_rationale", "tool_description", "client_score"}
