"""Clone: a new draft with every page row copied and every link pointing inside the copy."""

from sqlalchemy import func, select

from app.db import SessionLocal
from app.models import AssessmentBehavior, AssessmentMethod, AssessmentVisual, BrgGoal, BrgGoalSagLink, Crisis, CrisisPlan, SagGoal
from app.routes.assessment import UPLOAD_DIR, find_assessment
from app.routes.clone import page_tables
from tests.test_enforcement import sign_in_with
from tests.test_full_plan import fill_full_plan

PLANS = "/api/v2/treatment_plans"


def clone(client, plan_id: int) -> dict:
    response = client.post(f"{PLANS}/{plan_id}/clone/")
    assert response.status_code == 201, response.text
    return response.json()


def statuses(client, plan_id: int) -> list[tuple[str, str]]:
    return [(s["page"], s["status"]) for s in client.get(f"{PLANS}/{plan_id}/pages/").json()]


def row_counts(plan_id: int) -> dict[str, int]:
    """Rows per page table that belong to the plan, found by walking the same parent links as the clone."""
    counts, ids = {}, {"treatment_plan": {plan_id}}
    with SessionLocal() as session:
        for table in page_tables():
            fk = next(fk for fk in table.foreign_keys if fk.column.table.name in ids)
            where = fk.parent.in_(ids[fk.column.table.name])
            counts[table.name] = session.scalar(select(func.count()).select_from(table).where(where))
            if "id" in table.c:
                ids[table.name] = set(session.scalars(select(table.c.id).where(where)))
    return counts


def test_full_plan_clone_matches_source(client, plan_id):
    fill_full_plan(client, plan_id)
    copy = clone(client, plan_id)
    assert copy["status"] == "draft" and copy["signature"] is None and copy["client_id"] == 1 and copy["bay"] == "3"
    assert statuses(client, copy["id"]) == statuses(client, plan_id)
    assert all(status == "completed" for _, status in statuses(client, copy["id"]))
    source_counts = row_counts(plan_id)
    assert row_counts(copy["id"]) == source_counts
    assert sum(source_counts.values()) >= 40


def test_links_point_inside_the_copy(client, plan_id):
    fill_full_plan(client, plan_id)
    copy = clone(client, plan_id)
    with SessionLocal() as session:
        crisis = session.scalar(select(Crisis).where(Crisis.treatment_plan_id == copy["id"]))
        behaviors = {b.id for b in find_assessment(session, copy["id"]).behaviors}
        assert crisis.plans and all(p.assessment_behavior_id in behaviors for p in crisis.plans)
        source_behaviors = {b.id for b in find_assessment(session, plan_id).behaviors}
        assert not behaviors & source_behaviors
        brg_ids = set(session.scalars(select(BrgGoal.id).where(BrgGoal.treatment_plan_id == copy["id"])))
        sag_ids = set(session.scalars(select(SagGoal.id).where(SagGoal.treatment_plan_id == copy["id"])))
        links = session.scalars(select(BrgGoalSagLink).where(BrgGoalSagLink.brg_goal_id.in_(brg_ids))).all()
        assert links and all(link.sag_goal_id in sag_ids for link in links)


def test_partial_plan_keeps_its_statuses(client, plan_id):
    client.patch(f"{PLANS}/{plan_id}/pages/medications/", json={"no_medication": True})
    client.post(f"{PLANS}/{plan_id}/pages/referrals/", json={"provider_name": "Dr. Only Name"})
    copy = clone(client, plan_id)
    assert statuses(client, copy["id"]) == statuses(client, plan_id)
    assert {"completed", "error", "empty"} <= {s for _, s in statuses(client, copy["id"])}


def test_signed_source_gives_editable_copy(client, plan_id):
    fill_full_plan(client, plan_id)
    client.post(f"{PLANS}/{plan_id}/sign/", json={"signature": "Dana Lee, BCBA"})
    copy = clone(client, plan_id)
    assert copy["status"] == "draft"
    assert client.patch(f"{PLANS}/{copy['id']}/pages/treatment/", json={"duration_in_months": 9}).status_code == 200
    assert client.get(f"{PLANS}/{plan_id}/pages/treatment/").json()["duration_in_months"] == 6


def test_copy_records_its_source_and_owner(client, plan_id):
    copy = clone(client, plan_id)
    listed = next(p for p in client.get(f"{PLANS}/").json()["plans"] if p["id"] == copy["id"])
    assert listed["owner"] == "Dana Lee, BCBA"
    with SessionLocal() as session:
        from app.models import TreatmentPlan
        assert session.get(TreatmentPlan, copy["id"]).parent_treatment_plan_id == plan_id


def test_visual_files_are_copied(client, plan_id):
    method = client.post(f"{PLANS}/{plan_id}/pages/assessment/methods/", json={}).json()
    files = [("files", ("chart.png", b"png bytes", "image/png"))]
    client.post(f"{PLANS}/{plan_id}/pages/assessment/methods/{method['id']}/visuals/", files=files)
    copy = clone(client, plan_id)
    with SessionLocal() as session:
        keys = {
            plan: session.scalar(
                select(AssessmentVisual.file_storage_key)
                .join(AssessmentMethod, AssessmentMethod.id == AssessmentVisual.method_id)
                .where(AssessmentMethod.assessment_id == find_assessment(session, plan).id))
            for plan in (plan_id, copy["id"])
        }
    assert keys[plan_id] != keys[copy["id"]]
    assert (UPLOAD_DIR / keys[copy["id"]]).read_bytes() == b"png bytes"
    copy_method = client.get(f"{PLANS}/{copy['id']}/pages/assessment/").json()["methods"][0]
    client.delete(f"{PLANS}/{copy['id']}/pages/assessment/methods/{copy_method['id']}/")
    assert (UPLOAD_DIR / keys[plan_id]).exists() and not (UPLOAD_DIR / keys[copy["id"]]).exists()


def test_clone_needs_permission_and_provider(client, plan_id):
    nobody = sign_in_with({}, "Clone nobody")
    assert nobody.post(f"{PLANS}/{plan_id}/clone/").status_code == 403
    assert sign_in_with({"create_plan": "edit"}, "Clone outsider").post(f"{PLANS}/{plan_id}/clone/").status_code == 403
    clerk = sign_in_with({"create_plan": "edit", "all_clients": "edit"}, "Clone clerk")
    assert clerk.post(f"{PLANS}/{plan_id}/clone/").status_code == 422
    assert client.post(f"{PLANS}/99999/clone/").status_code == 404


def test_no_rows_left_behind(client, plan_id):
    """Every crisis plan and behavior on the source stays on the source."""
    fill_full_plan(client, plan_id)
    with SessionLocal() as session:
        before = session.scalar(select(func.count()).select_from(CrisisPlan))
        behaviors_before = session.scalar(select(func.count()).select_from(AssessmentBehavior))
    clone(client, plan_id)
    with SessionLocal() as session:
        assert session.scalar(select(func.count()).select_from(CrisisPlan)) == before + 1
        assert session.scalar(select(func.count()).select_from(AssessmentBehavior)) == behaviors_before + 1
