"""Information page."""

BASE = "/api/v2/treatment_plans"


def test_information(client, plan_id):
    data = client.get(f"{BASE}/{plan_id}/pages/information/").json()
    assert data["client"]["first_name"] == "Sam"
    assert data["home_bcba"]["display_name"] == "Dana Lee, BCBA"
    assert "bobbing_bcba" not in data
    assert [p["display_name"] for p in data["assigned_bts"]] == ["Chris Park"]
    assert [p["display_name"] for p in data["substitute_bcbas"]] == ["Morgan Diaz, BCBA"]
    assert data["parents_guardians"] == [{"display_name": "Ana Rivera", "role": "Mother"}]
    assert data["insurance"]["primary"]["payor_name"] == "Blue Cross Blue Shield of Texas"
    assert data["insurance"]["secondary"] is None
    assert set(data["insurance"]) == {"primary", "secondary"}
