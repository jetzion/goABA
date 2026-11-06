"""Family page."""

import pytest

BASE = "/api/v2/treatment_plans"

MEMBER = {
    "full_name": "Ana Rivera",
    "member_role": "Parent and a caregiver",
    "caregiver_type": "Primary caregiver",
    "relationship_to_client": "Parent (Mother / Father)",
    "custody_type": "Joint custody",
    "marital_status": "Married",
    "job_title": "Nurse",
    "email": "ana@example.com",
    "phone": "5125550111",
    "street_address_line_one": "123 Oak Street",
    "street_address_city": "Austin",
    "street_address_state": "TX",
    "street_address_zip": "78701",
}
LISTS = [
    ("MATERNAL_MEDICAL_HISTORY", "None"),
    ("PATERNAL_MEDICAL_HISTORY", "ADHD"),
    ("COMMUNITY_SUPPORT", "Extended family"),
]


def url(plan_id, path=""):
    return f"{BASE}/{plan_id}/pages/family/{path}"


def status(client, plan_id):
    return next(s for s in client.get(f"{BASE}/{plan_id}/pages/").json() if s["page"] == "family")


def fill(client, plan_id):
    client.post(url(plan_id, "members/"), json=MEMBER)
    for info_type, value in LISTS:
        client.post(url(plan_id, "additional_info/"), json={"info_type": info_type, "value": value})
    client.patch(url(plan_id), json={"cultural_consideration": "<p>Bilingual home</p>"})


def fields(page):
    return {e["field"] for e in page["errors"]}


def test_empty(client, plan_id):
    assert status(client, plan_id)["status"] == "empty"


def test_complete(client, plan_id):
    fill(client, plan_id)
    assert status(client, plan_id) == {"page": "family", "status": "completed", "errors": []}


def test_cultural_consideration_only_lists_what_is_missing(client, plan_id):
    client.patch(url(plan_id), json={"cultural_consideration": "<p>Bilingual home</p>"})
    page = status(client, plan_id)
    assert fields(page) == {"members", "MATERNAL_MEDICAL_HISTORY", "PATERNAL_MEDICAL_HISTORY", "COMMUNITY_SUPPORT"}


@pytest.mark.parametrize(
    "field,value",
    [
        ("full_name", "Ana R"),
        ("street_address_line_one", "1 Elm"),
        ("street_address_zip", "7870"),
        ("street_address_state", "ZZ"),
        ("relationship_to_client", "Neighbor"),
        ("phone", "51255501"),
    ],
)
def test_member_save_rules_reject(client, plan_id, field, value):
    assert client.post(url(plan_id, "members/"), json={field: value}).status_code == 422


def test_member_state_accepts_cz(client, plan_id):
    response = client.post(url(plan_id, "members/"), json={"street_address_state": "cz"})
    assert response.json()["street_address_state"] == "CZ"


def test_only_one_primary_caregiver(client, plan_id):
    client.post(url(plan_id, "members/"), json=MEMBER)
    response = client.post(url(plan_id, "members/"), json={"caregiver_type": "Primary caregiver"})
    assert response.status_code == 409
    second = client.post(url(plan_id, "members/"), json={"caregiver_type": "Secondary caregiver"}).json()
    assert client.patch(url(plan_id, f"members/{second['id']}/"), json={"caregiver_type": "Primary caregiver"}).status_code == 409


def test_caregiver_type_rules(client, plan_id):
    fill(client, plan_id)
    member_id = client.get(url(plan_id)).json()["members"][0]["id"]
    client.patch(url(plan_id, f"members/{member_id}/"), json={"member_role": "Parent not a caregiver"})
    assert status(client, plan_id)["errors"][0]["message"] == "Must be empty for a parent who is not a caregiver"
    client.patch(url(plan_id, f"members/{member_id}/"), json={"caregiver_type": None})
    assert status(client, plan_id)["status"] == "completed"
    client.patch(url(plan_id, f"members/{member_id}/"), json={"member_role": "Caregiver"})
    assert fields(status(client, plan_id)) == {"caregiver_type"}


def test_incomplete_sibling_is_error(client, plan_id):
    fill(client, plan_id)
    sibling = client.post(url(plan_id, "siblings/"), json={"sibling_relationship": "Adoptive Siblings"}).json()
    assert sibling["sibling_relationship"] == "Adoptive-siblings"
    assert fields(status(client, plan_id)) == {"sibling_age", "sibling_diagnosis"}
    client.patch(url(plan_id, f"siblings/{sibling['id']}/"), json={"sibling_age": 9, "sibling_diagnosis": "ADHD"})
    assert status(client, plan_id)["status"] == "completed"


def test_list_value_must_match_type(client, plan_id):
    body = {"info_type": "COMMUNITY_SUPPORT", "value": "ADHD"}
    assert client.post(url(plan_id, "additional_info/"), json=body).status_code == 422


def test_community_alias(client, plan_id):
    body = {"info_type": "COMMUNITY_SUPPORT", "value": "Church (or other religious organization)"}
    assert client.post(url(plan_id, "additional_info/"), json=body).json()["value"] == "Church (or other religion organization)"


def test_duplicate_list_value_rejected(client, plan_id):
    body = {"info_type": "PATERNAL_MEDICAL_HISTORY", "value": "ASD"}
    assert client.post(url(plan_id, "additional_info/"), json=body).status_code == 201
    assert client.post(url(plan_id, "additional_info/"), json=body).status_code == 409


def test_page_response_splits_lists(client, plan_id):
    fill(client, plan_id)
    data = client.get(url(plan_id)).json()
    assert [i["value"] for i in data["paternal_medical_history"]] == ["ADHD"]
    assert data["additional_info"] == []


def test_cultural_consideration_limits(client, plan_id):
    assert client.patch(url(plan_id), json={"cultural_consideration": "<p>" + "x" * 800 + "</p>"}).status_code == 422
    fill(client, plan_id)
    client.patch(url(plan_id), json={"cultural_consideration": "<p>abc</p>"})
    assert fields(status(client, plan_id)) == {"cultural_consideration"}


def test_delete_rows(client, plan_id):
    fill(client, plan_id)
    data = client.get(url(plan_id)).json()
    assert client.delete(url(plan_id, f"members/{data['members'][0]['id']}/")).status_code == 204
    assert client.delete(url(plan_id, f"additional_info/{data['community_support'][0]['id']}/")).status_code == 204
    assert fields(status(client, plan_id)) == {"members", "COMMUNITY_SUPPORT"}
