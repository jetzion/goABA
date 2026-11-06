"""Assessment visual files, served only to users who may view that plan's Assessment page."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select

from app.access import VIEW, CurrentUser, allows, check_plan, user_level
from app.models import Assessment, AssessmentMethod, AssessmentVisual
from app.routes.assessment import UPLOAD_DIR
from app.routes.plan import SessionDep

router = APIRouter(prefix="/uploads")


@router.get("/{key}")
def get_upload(key: str, session: SessionDep, user: CurrentUser) -> FileResponse:
    """The file behind a visual. 403 without the Assessment page or the plan's client, 404 for unknown keys."""
    if not allows(user_level(session, user, "assessment"), VIEW):
        raise HTTPException(403, "Your role cannot view assessment")
    plan_id = session.scalar(
        select(Assessment.treatment_plan_id)
        .join(AssessmentMethod, AssessmentMethod.assessment_id == Assessment.id)
        .join(AssessmentVisual, AssessmentVisual.method_id == AssessmentMethod.id)
        .where(AssessmentVisual.file_storage_key == key)
    )
    if plan_id is None:
        raise HTTPException(404, "File not found")
    check_plan(session, user, plan_id, write=False)
    return FileResponse(UPLOAD_DIR / key, headers={"X-Content-Type-Options": "nosniff"})
