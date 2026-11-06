"""Child page."""

import pytest

BASE = "/api/v2/treatment_plans"
OFFSET = -6 * 3600


def url(plan_id, path=""):
    return f"{BASE}/{plan_id}/pages/child/{path}"


def status(client, plan_id):
    return next(s for s in client.get(f"{BASE}/{plan_id}/pages/").json() if s["page"] == "child")


def slot(day="MONDAY", activity="FORTA_THERAPY", start="09:00", end="12:00", offset="-06:00", utc_offset=OFFSET):
    return {
        "day_of_week": day,
        "schedule_activity_type": activity,
        "schedule_start_date": f"2026-11-02T{start}:00{offset}",
        "schedule_end_date": f"2026-11-02T{end}:00{offset}",
        "utc_offset": utc_offset,
    }


def add(client, plan_id, background_type, description):
    return client.post(url(plan_id, "backgrounds/"), json={"background_type": background_type, "background_description": description})


def fill(client, plan_id):
    add(client, plan_id, "COMMUNICATION_STYLE", "Sign language")
    add(client, plan_id, "GOALS_FOR_THERAPY", "Improve play skills")
    add(client, plan_id, "BEHAVIOR_ISSUE", "None")
    for t in ("STRENGTH", "WEAKNESS", "INTEREST", "DISLIKES"):
        add(client, plan_id, t, f"{t} one")
        add(client, plan_id, t, f"{t} two")
    client.post(url(plan_id, "schedule/"), json=slot())


def fields(client, plan_id):
    return {e["field"] for e in status(client, plan_id)["errors"]}


def test_empty(client, plan_id):
    assert status(client, plan_id)["status"] == "empty"


def test_complete(client, plan_id):
    fill(client, plan_id)
    assert status(client, plan_id)["status"] == "completed"


def test_free_text_needs_two(client, plan_id):
    add(client, plan_id, "STRENGTH", "Loves puzzles")
    assert "STRENGTH" in fields(client, plan_id)


def test_dropdown_type_needs_listed_label(client, plan_id):
    assert add(client, plan_id, "COMMUNICATION_STYLE", "Morse code").status_code == 422


def test_free_text_length(client, plan_id):
    assert add(client, plan_id, "STRENGTH", "x" * 2001).status_code == 422


def test_typo_is_rewritten(client, plan_id):
    item = add(client, plan_id, "BEHAVIOR_ISSUE", "Verbal a ggression (e.g., threats, name-calling)").json()
    assert item["background_description"] == "Verbal aggression (e.g., threats, name-calling)"


def test_duplicate_in_type_rejected(client, plan_id):
    assert add(client, plan_id, "INTEREST", "Trains").status_code == 201
    assert add(client, plan_id, "INTEREST", "Trains").status_code == 409
    assert add(client, plan_id, "DISLIKES", "Trains").status_code == 201


def test_schedule_keeps_local_time(client, plan_id):
    created = client.post(url(plan_id, "schedule/"), json=slot()).json()
    assert created["schedule_start_date"] == "2026-11-02T09:00:00-06:00"
    assert client.get(url(plan_id)).json()["schedule"][0]["schedule_end_date"] == "2026-11-02T12:00:00-06:00"


def test_schedule_sorted_by_day_then_time(client, plan_id):
    client.post(url(plan_id, "schedule/"), json=slot(day="TUESDAY"))
    client.post(url(plan_id, "schedule/"), json=slot(start="13:00", end="14:00"))
    client.post(url(plan_id, "schedule/"), json=slot(start="07:00", end="08:00"))
    days = [(s["day_of_week"], s["schedule_start_date"][11:16]) for s in client.get(url(plan_id)).json()["schedule"]]
    assert days == [("MONDAY", "07:00"), ("MONDAY", "13:00"), ("TUESDAY", "09:00")]


def test_overlap_same_day_rejected(client, plan_id):
    client.post(url(plan_id, "schedule/"), json=slot())
    assert client.post(url(plan_id, "schedule/"), json=slot(start="11:00", end="13:00")).status_code == 409
    assert client.post(url(plan_id, "schedule/"), json=slot(start="12:00", end="13:00")).status_code == 201
    assert client.post(url(plan_id, "schedule/"), json=slot(day="FRIDAY", start="11:00", end="13:00")).status_code == 201


@pytest.mark.parametrize(
    "body",
    [
        slot(start="12:00", end="09:00"),
        slot(offset="-05:00"),
        slot(utc_offset=-50000),
        {**slot(), "schedule_start_date": "2026-11-02T09:00:00"},
        slot(activity="NAP"),
    ],
)
def test_schedule_rejects(client, plan_id, body):
    assert client.post(url(plan_id, "schedule/"), json=body).status_code == 422


def test_needs_school_slot_when_attending(client, plan_id):
    fill(client, plan_id)
    client.patch(f"{BASE}/{plan_id}/pages/education/", json={"school_name": "Oak Hill Elementary"})
    assert fields(client, plan_id) == {"schedule"}
    client.post(url(plan_id, "schedule/"), json=slot(day="TUESDAY", activity="SCHOOL"))
    assert status(client, plan_id)["status"] == "completed"


def test_needs_other_therapy_slot_with_historical_therapy(client, plan_id):
    fill(client, plan_id)
    client.patch(f"{BASE}/{plan_id}/pages/therapy/", json={"no_historical_therapy": False})
    assert status(client, plan_id)["errors"][0]["message"].startswith("The client has historical therapy")
    client.patch(f"{BASE}/{plan_id}/pages/therapy/", json={"no_historical_therapy": True})
    assert status(client, plan_id)["status"] == "completed"


def test_behavior_issues_text_not_required_but_limited(client, plan_id):
    assert client.patch(url(plan_id), json={"child_behavior_issues": "<p>" + "x" * 800 + "</p>"}).status_code == 422
    assert client.patch(url(plan_id), json={"child_behavior_issues": "<p>Bites when tired</p>"}).status_code == 200


def test_delete(client, plan_id):
    item = add(client, plan_id, "INTEREST", "Trains").json()
    created = client.post(url(plan_id, "schedule/"), json=slot()).json()
    assert client.delete(url(plan_id, f"backgrounds/{item['id']}/")).status_code == 204
    assert client.delete(url(plan_id, f"schedule/{created['id']}/")).status_code == 204
    assert client.get(url(plan_id)).json()["backgrounds"] == []
