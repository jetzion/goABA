"""Clone a plan: a new draft for the same client with a copy of every page row.

The copy is generic: every table whose foreign keys lead back to `treatment_plan` is a page table.
Tables are walked parent first, and each foreign key to a copied row is pointed at its copy, which
also re-links crisis plans to the copied behaviors and BRG goals to the copied SAG goals.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import Table, insert, select
from sqlalchemy.orm import Session

from app.access import CurrentUser, action_access, plan_reader
from app.db import Base
from app.models import AssessmentVisual, TreatmentPlan
from app.routes.assessment import copy_upload
from app.routes.plan import SessionDep, TreatmentPlanResponse, load_plan

PLAN_TABLE = TreatmentPlan.__tablename__

router = APIRouter(prefix="/api/v2/treatment_plans")


def page_tables() -> list[Table]:
    """Tables owned by a plan, parents before children."""
    owned = {PLAN_TABLE}
    tables = []
    for table in Base.metadata.sorted_tables:
        if table.name != PLAN_TABLE and any(fk.column.table.name in owned for fk in table.foreign_keys):
            owned.add(table.name)
            tables.append(table)
    return tables


def copy_pages(session: Session, source_id: int, target_id: int) -> dict[str, dict[int, int]]:
    """Copy every page row of the source plan to the target plan. Returns old id to new id per table.

    Link tables keyed by their foreign keys (no `id` column) are copied with both links re-pointed.
    """
    id_maps: dict[str, dict[int, int]] = {PLAN_TABLE: {source_id: target_id}}
    for table in page_tables():
        owned_fks = [fk for fk in table.foreign_keys if fk.column.table.name in id_maps]
        anchor = owned_fks[0]
        rows = session.execute(
            select(table).where(anchor.parent.in_(id_maps[anchor.column.table.name])).order_by(*table.primary_key)
        ).mappings().all()
        has_id = "id" in table.c
        id_maps[table.name] = {}
        for row in rows:
            values = {name: value for name, value in row.items() if name != "id"}
            for fk in owned_fks:
                if values[fk.parent.name] is not None:
                    values[fk.parent.name] = id_maps[fk.column.table.name][values[fk.parent.name]]
            result = session.execute(insert(table).values(values))
            if has_id:
                id_maps[table.name][row["id"]] = result.inserted_primary_key[0]
    return id_maps


def copy_visual_files(session: Session, new_visual_ids: list[int]) -> None:
    """Give each copied visual its own file, so deleting it never removes the source's file."""
    for visual in session.scalars(select(AssessmentVisual).where(AssessmentVisual.id.in_(new_visual_ids))):
        visual.file_storage_key = copy_upload(visual.file_storage_key)


@router.post("/{plan_id}/clone/", status_code=201, dependencies=[action_access("create_plan"), Depends(plan_reader)])
def clone_plan(plan_id: int, session: SessionDep, user: CurrentUser) -> TreatmentPlanResponse:
    """A new draft plan for the same client and bay, owned by the signed-in provider, with every page copied."""
    source = load_plan(session, plan_id)
    if user.provider_id is None:
        raise HTTPException(422, "Only a provider can own a treatment plan")
    plan = TreatmentPlan(
        client_id=source.client_id, bay=source.bay, version=3, provider_id=user.provider_id,
        has_medication=source.has_medication, parent_treatment_plan_id=source.id,
    )
    session.add(plan)
    session.flush()
    id_maps = copy_pages(session, source.id, plan.id)
    copy_visual_files(session, list(id_maps[AssessmentVisual.__tablename__].values()))
    session.commit()
    return TreatmentPlanResponse.model_validate(plan)
