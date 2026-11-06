"""A real plan filled through the API reaches all-complete and can be signed."""

from app.enums import DSM5_SYMPTOMS

BASE = "/api/v2/treatment_plans"
LONG = "<p>" + "Detailed clinical narrative text. " * 3 + "</p>"
INSTRUCTIONS = "Present the instruction, wait three seconds, prompt as needed, then reinforce."
SYMPTOM = DSM5_SYMPTOMS[0]


def fill_medical(c, url):
    c.patch(url("medical/"), json={
        "allergies": "Peanuts", "special_diets": "Gluten free",
        "hearing_difficulty": "No hearing issues", "hearing_screening_date": "2024-02-10",
        "vision_difficulty": "No vision issues", "vision_screening_date": "2024-02-10",
        "trauma_history": "<p>None reported</p>", "hospitalization_history": "<p>None reported</p>",
        "asd_severity_level": "Level-2", "asd_diagnosis_provider_name": "Dr. Jane Smith",
        "asd_diagnosis_city": "Austin", "asd_diagnosis_state": "TX", "asd_diagnosis_year": 2022,
        "child_delivery_type": "Spontaneous", "child_gestational_age_weeks": 39,
        "child_weight_at_birth_pounds": 7, "child_weight_at_birth_ounces": 4,
        "child_sitting_up_age_months": 6, "child_crawling_age_months": 8,
        "child_walking_age_years": 1, "child_walking_age_months": 2,
        "child_standing_age_years": 1, "child_standing_age_months": 0,
        "child_babbling_age_months": 7, "child_first_word": "mama", "child_second_word": "ball",
        "child_first_words_age_months": 14,
    })
    for selection_type in ("EARLY_INTERVENTION", "PREGNANCY_ISSUE", "REGRESSION"):
        c.post(url("medical/selections/"), json={"selection_type": selection_type, "value": "None"})


def fill_family(c, url):
    c.post(url("family/members/"), json={
        "full_name": "Ana Rivera", "member_role": "Parent and a caregiver", "caregiver_type": "Primary caregiver",
        "relationship_to_client": "Parent (Mother / Father)", "custody_type": "Joint custody",
        "marital_status": "Married", "job_title": "Nurse", "email": "ana@example.com", "phone": "5125550111",
        "street_address_line_one": "123 Oak Street", "street_address_city": "Austin",
        "street_address_state": "TX", "street_address_zip": "78701",
    })
    for info_type in ("MATERNAL_MEDICAL_HISTORY", "PATERNAL_MEDICAL_HISTORY", "COMMUNITY_SUPPORT"):
        c.post(url("family/additional_info/"), json={"info_type": info_type, "value": "None"})
    c.patch(url("family/"), json={"cultural_consideration": "<p>Bilingual home</p>"})


def fill_child(c, url):
    for background_type, value in (("COMMUNICATION_STYLE", "Sign language"), ("GOALS_FOR_THERAPY", "Improve play skills"), ("BEHAVIOR_ISSUE", "None")):
        c.post(url("child/backgrounds/"), json={"background_type": background_type, "background_description": value})
    for background_type in ("STRENGTH", "WEAKNESS", "INTEREST", "DISLIKES"):
        for n in (1, 2):
            c.post(url("child/backgrounds/"), json={"background_type": background_type, "background_description": f"{background_type} {n}"})
    c.post(url("child/schedule/"), json={
        "day_of_week": "MONDAY", "schedule_activity_type": "FORTA_THERAPY",
        "schedule_start_date": "2026-11-02T09:00:00-06:00", "schedule_end_date": "2026-11-02T12:00:00-06:00",
        "utc_offset": -21600,
    })


def fill_assessment(c, url):
    c.patch(url("assessment/"), json={
        "initial_assessment_date": "2026-01-10", "diagnostic_report_reviewed": True, "reassessment_date": "2026-07-10",
        "parent_interview_summary": LONG, "assessment_results": LONG, "priorities": LONG,
        "observations": "<p>Calm and engaged</p>",
    })
    c.post(url("assessment/methods/"), json={
        "tool": "VB-MAPP", "assessment_date": "2026-01-12", "rationale": LONG,
        "selection_rationale": LONG, "tool_description": LONG, "client_score": LONG,
    })
    return c.post(url("assessment/behaviors/"), json={
        "behavior": "<p>Hits peers when toys are taken</p>", "dsm5_symptom": SYMPTOM,
        "parent_concerns": "<p>Hurts siblings at home</p>",
    }).json()["id"]


def goal_name(c, url, section, prefix):
    data = c.get(url(f"{section}/")).json()
    options = data["available_goals"] if section == "pcg" else [g for a in data["focus_areas"] for g in a["goals"]]
    return next(g["id"] for g in options if g["prefix"] == prefix)


def fill_goals(c, url):
    common = {"baseline_date": "2026-01-10", "expected_mastery_date": "06-2026"}
    c.post(url("pcg/goals/"), json={
        **common, "goal_name_id": goal_name(c, url, "pcg", "PT-1"), "data_collection_method": "Instances",
        "baseline_level": 10, "current_level": 10, "mastery_to": 40, "goal_description": "<p>Caregiver reinforces</p>",
    })
    sag = c.post(url("sag/goals/"), json={
        **common, "goal_name_id": goal_name(c, url, "sag", "COM-1"), "data_collection_method": "Percentage",
        "opportunities": 10, "baseline_level": 2, "current_level": 2, "frequency": "Once a week",
        "goal_description": "<p>Requests items with words</p>",
        "acquisition_responses": 8, "generalization_responses": 8, "maintenance_responses": 9,
    }).json()
    sag_target = c.post(url(f"sag/goals/{sag['id']}/targets/"), json={
        "target_name": "Requests juice with a word", "timeframe": "Short-Term", "baseline_date": "2026-01-10",
        "baseline_level": 2, "opportunities": 10, "description": LONG, "instructions": INSTRUCTIONS,
    })
    assert sag_target.status_code == 201
    brg = c.post(url("brg/goals/"), json={
        **common, "goal_name_id": goal_name(c, url, "brg", "BC-1"), "dsm5_symptom": SYMPTOM,
        "data_collection_method": "Instances", "baseline_level": 12, "current_level": 12, "frequency": "Twice a week",
        "mastery_direction": "decrease", "mastery_to": 2, "linked_sag_goal_ids": [sag["id"]],
        **{f: LONG for f in ("operational_definition", "objective", "antecedent_modifications", "consequence_modifications", "goal_description")},
    }).json()
    c.post(url(f"brg/goals/{brg['id']}/hypothesized-functions/"), json={"function_date": "2026-01-10", "functions": ["Attention"]})


def fill_full_plan(client, plan_id):
    """Fill every page through the API so the plan is all complete."""
    def url(path):
        return f"{BASE}/{plan_id}/pages/{path}"

    fill_medical(client, url)
    client.post(url("referrals/"), json={
        "referral_date": "2024-05-01", "provider_name": "Dr. Jane Smith",
        "diagnosis_tool": "ADOS-2 (Autism Diagnostic Observation Schedule)", "city": "Austin", "state": "TX",
    })
    client.patch(url("medications/"), json={"no_medication": True})
    client.patch(url("therapy/"), json={"no_historical_therapy": True})
    client.patch(url("education/"), json={"not_attending_school": True})
    fill_family(client, url)
    fill_child(client, url)
    behavior_id = fill_assessment(client, url)
    client.post(url("crisis/"), json={
        "assessment_behavior_id": behavior_id, "crisis_creation_date": "2027-03-01", "functional_behavior": ["Escape-Maintained"],
        **{f: LONG for f in ("operational_definition", "antecedent_interventions", "precursors_action_steps",
                             "escalation_intervention_plan", "follow_up_steps", "consequence_strategies")},
    })
    fill_goals(client, url)
    client.patch(url("discharge/"), json={f: LONG for f in ("mastery_of_program_goals", "titration_plan", "readiness_to_step_down", "care_coordination")})
    client.post(url("discharge/reasons/"), json={"reason": "No new behaviors have emerged"})
    client.patch(url("treatment/"), json={
        "recommendations_explanation": "<p>Begin at 20 hours</p>", "proposed_start_date": "2026-12-01",
        "duration_in_months": 6, "direct_therapy_97153_hours": 20, "direct_therapy_97153_per": "Weekly",
    })


def test_full_plan_completes_and_signs(client, plan_id):
    def url(path):
        return f"{BASE}/{plan_id}/pages/{path}"

    fill_full_plan(client, plan_id)
    statuses = client.get(f"{BASE}/{plan_id}/pages/").json()
    assert [s for s in statuses if s["status"] != "completed"] == []

    signed = client.post(f"{BASE}/{plan_id}/sign/", json={"signature": "Dana Lee, BCBA"})
    assert signed.status_code == 200 and signed.json()["status"] == "signed"
    assert client.patch(url("treatment/"), json={"duration_in_months": 7}).status_code == 409
