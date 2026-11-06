"""Medical page."""

import pytest

BASE = "/api/v2/treatment_plans"

COMPLETE_INFO = {
    "allergies": "Peanuts",
    "special_diets": "Gluten free",
    "hearing_difficulty": "No hearing issues",
    "hearing_screening_date": "2024-02-10",
    "vision_difficulty": "No vision issues",
    "vision_screening_date": "2024-02-10",
    "trauma_history": "<p>None reported</p>",
    "hospitalization_history": "<p>None reported</p>",
    "asd_severity_level": "Level-2",
    "asd_diagnosis_provider_name": "Dr. Jane Smith",
    "asd_diagnosis_city": "Austin",
    "asd_diagnosis_state": "tx",
    "asd_diagnosis_year": 2022,
    "child_delivery_type": "Spontaneous",
    "child_gestational_age_weeks": 39,
    "child_weight_at_birth_pounds": 7,
    "child_weight_at_birth_ounces": 4,
    "child_sitting_up_age_months": 6,
    "child_crawling_age_months": 8,
    "child_walking_age_years": 1,
    "child_walking_age_months": 2,
    "child_standing_age_years": 1,
    "child_standing_age_months": 0,
    "child_babbling_age_months": 7,
    "child_first_word": "mama",
    "child_second_word": "ball",
    "child_first_words_age_months": 14,
}

SELECTIONS = [("EARLY_INTERVENTION", "Speech Therapy"), ("PREGNANCY_ISSUE", "None"), ("REGRESSION", "None")]


def url(plan_id, path=""):
    return f"{BASE}/{plan_id}/pages/medical/{path}"


def status(client, plan_id):
    return next(s for s in client.get(f"{BASE}/{plan_id}/pages/").json() if s["page"] == "medical")


def fill(client, plan_id):
    client.patch(url(plan_id), json=COMPLETE_INFO)
    for selection_type, value in SELECTIONS:
        client.post(url(plan_id, "selections/"), json={"selection_type": selection_type, "value": value})


def test_empty_until_saved(client, plan_id):
    assert status(client, plan_id)["status"] == "empty"
    assert client.get(url(plan_id)).json() == {"medical_info": None, "diagnoses": [], "selections": []}


@pytest.mark.parametrize(
    "field,value",
    [
        ("allergies", "abc"),
        ("hearing_difficulty", "Deaf"),
        ("asd_diagnosis_year", 1899),
        ("child_weight_at_birth_ounces", 16),
        ("child_standing_age_years", 10),
        ("child_first_word", "two words"),
        ("trauma_history", "<p>a b</p>"),
        ("unknown_field", "x"),
    ],
)
def test_save_rules_reject(client, plan_id, field, value):
    assert client.patch(url(plan_id), json={field: value}).status_code == 422


def test_partial_save_is_error_with_missing_fields(client, plan_id):
    response = client.patch(url(plan_id), json={"allergies": "  Peanuts  "})
    assert response.status_code == 200
    assert response.json()["allergies"] == "Peanuts"
    page = status(client, plan_id)
    assert page["status"] == "error"
    assert "special_diets" in {e["field"] for e in page["errors"]}


def test_omitted_field_keeps_value_and_null_clears(client, plan_id):
    client.patch(url(plan_id), json={"allergies": "Peanuts", "special_diets": "None given"})
    response = client.patch(url(plan_id), json={"special_diets": None})
    assert response.json()["allergies"] == "Peanuts"
    assert response.json()["special_diets"] is None


def test_complete_page(client, plan_id):
    fill(client, plan_id)
    assert status(client, plan_id) == {"page": "medical", "status": "completed", "errors": []}
    assert client.get(url(plan_id)).json()["medical_info"]["asd_diagnosis_state"] == "TX"


def test_incomplete_diagnosis_row_is_error(client, plan_id):
    fill(client, plan_id)
    row = client.post(url(plan_id, "diagnoses/"), json={"diagnosis_name": "Anxiety (F41.9)"}).json()
    page = status(client, plan_id)
    assert page["status"] == "error"
    assert {e["row_id"] for e in page["errors"]} == {row["id"]}
    client.patch(url(plan_id, f"diagnoses/{row['id']}/"), json={"provider_name": "Dr. Alan Grant", "city": "Austin", "state": "TX", "year": 2023})
    assert status(client, plan_id)["status"] == "completed"
    assert client.delete(url(plan_id, f"diagnoses/{row['id']}/")).status_code == 204


def test_selection_value_must_match_type(client, plan_id):
    response = client.post(url(plan_id, "selections/"), json={"selection_type": "REGRESSION", "value": "Speech Therapy"})
    assert response.status_code == 422


def test_duplicate_selection_rejected(client, plan_id):
    body = {"selection_type": "REGRESSION", "value": "Fine motor"}
    assert client.post(url(plan_id, "selections/"), json=body).status_code == 201
    assert client.post(url(plan_id, "selections/"), json=body).status_code == 409


def test_none_combined_is_error(client, plan_id):
    fill(client, plan_id)
    selection = client.post(url(plan_id, "selections/"), json={"selection_type": "REGRESSION", "value": "Gross motor"}).json()
    page = status(client, plan_id)
    assert page["errors"][0]["field"] == "REGRESSION"
    assert client.delete(url(plan_id, f"selections/REGRESSION/{selection['id']}/")).status_code == 204
    assert status(client, plan_id)["status"] == "completed"

