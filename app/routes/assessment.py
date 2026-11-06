"""Assessment page: schemas, routes and completion."""

import os
import shutil
import uuid
from datetime import date
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, HTTPException, UploadFile
from pydantic import AfterValidator, BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.completion import CHECKERS, PageError, PageStatusResponse, required, result
from app.enums import ADDITIONAL_FILES, ASSESSMENT_TOOLS, BARRIERS, DSM5_SYMPTOMS, READINESS_ITEMS, READINESS_LEVELS
from app.models import Assessment, AssessmentBehavior, AssessmentMethod, AssessmentReadiness, AssessmentVisual, CrisisPlan, TreatmentPlan
from app.routes.common import apply_patch, get_owned
from app.routes.plan import SessionDep, load_plan, load_plan_for_write
from app.rules import Body, OneOf, RichText, Text, visible_length

router = APIRouter(prefix="/api/v2/treatment_plans/{plan_id}/pages/assessment")

UPLOAD_DIR = Path(os.environ.get("TP_UPLOAD_DIR", "uploads"))
UPLOAD_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".pdf"}
ITEM_SECTIONS = {item: section for section, items in READINESS_ITEMS.items() for item in items}
ITEM_LABELS = {item: label for items in READINESS_ITEMS.values() for item, label in items.items()}
SCORES = {"Not ready": 0, "Somewhat": 1, "Ready": 2}
LONG_TEXT_MIN = 60


def _unique(values: list[str]) -> list[str]:
    if len(set(values)) != len(values):
        raise ValueError("values must be unique")
    return values


def UniqueList(options: tuple[str, ...], max_items: int):
    """A list of unique listed options."""
    return Annotated[list[OneOf(options)], Field(max_length=max_items), AfterValidator(_unique)]


class AssessmentPatchRequest(Body):
    initial_assessment_date: date | None = None
    diagnostic_report_reviewed: bool | None = None
    reassessment_date: date | None = None
    parent_interview_summary: RichText() | None = None
    assessment_results: RichText() | None = None
    priorities: RichText() | None = None
    additional_files_viewed: UniqueList(ADDITIONAL_FILES, 6) = []
    no_maladaptive_behavior: bool = False
    telehealth_readiness_assessment_needed: bool = False
    telehealth_assessment_date: date | None = None
    barriers: UniqueList(BARRIERS, 23) = []
    observations: RichText(50_000, 4) | None = None


class BehaviorPatchRequest(Body):
    behavior: RichText(50_000, 16) | None = None
    dsm5_symptom: OneOf(DSM5_SYMPTOMS) | None = None
    parent_concerns: RichText(50_000, 16) | None = None


BehaviorCreateRequest = BehaviorPatchRequest
BEHAVIOR_FIELDS = list(BehaviorPatchRequest.model_fields)


class BehaviorResponse(BehaviorPatchRequest):
    model_config = ConfigDict(extra="ignore", from_attributes=True)

    id: int


class MethodPatchRequest(Body):
    tool: OneOf(ASSESSMENT_TOOLS) | None = None
    assessment_date: date | None = None
    rationale: RichText() | None = None
    selection_rationale: RichText() | None = None
    tool_description: RichText() | None = None
    client_score: RichText() | None = None


MethodCreateRequest = MethodPatchRequest
METHOD_TEXT_FIELDS = ["rationale", "selection_rationale", "tool_description", "client_score"]


class VisualPatchRequest(Body):
    title: Text(8, 255) | None = None
    analysis: RichText(50_000, 16) | None = None


class VisualResponse(BaseModel):
    id: int
    title: str | None
    analysis: str | None
    url: str


class MethodResponse(MethodPatchRequest):
    model_config = ConfigDict(extra="ignore")

    id: int
    visuals: list[VisualResponse]


class ReadinessPatchRequest(Body):
    readiness: OneOf(READINESS_LEVELS) | None = None
    notes: Text(8, 50_000) | None = None


class ReadinessResponse(BaseModel):
    item: str
    section: str
    label: str
    readiness: str | None
    notes: str | None


class ReadinessScores(BaseModel):
    child: int
    caregiver: int
    environment: int
    overall: int


class AssessmentPageResponse(AssessmentPatchRequest):
    model_config = ConfigDict(extra="ignore")

    behaviors: list[BehaviorResponse]
    methods: list[MethodResponse]
    readiness_items: list[ReadinessResponse]
    dsm5_symptoms: list[str]
    readiness_scores: ReadinessScores


class AssessmentTemplateCatalogResponse(BaseModel):
    page: dict[str, str]
    methods: dict[str, dict[str, str]]


def find_assessment(session: Session, plan_id: int) -> Assessment | None:
    return session.scalar(select(Assessment).where(Assessment.treatment_plan_id == plan_id))


def get_or_create_assessment(session: Session, plan_id: int) -> Assessment:
    assessment = find_assessment(session, plan_id)
    if assessment is None:
        assessment = Assessment(treatment_plan_id=plan_id, additional_files_viewed=[], barriers=[])
        session.add(assessment)
        session.flush()
    return assessment


def assessment_id_of(session: Session, plan_id: int) -> int | None:
    assessment = find_assessment(session, plan_id)
    return assessment.id if assessment else None


def visual_response(visual: AssessmentVisual) -> VisualResponse:
    return VisualResponse(id=visual.id, title=visual.title, analysis=visual.analysis, url=f"/uploads/{visual.file_storage_key}")


def method_response(method: AssessmentMethod) -> MethodResponse:
    values = {f: getattr(method, f) for f in MethodPatchRequest.model_fields}
    return MethodResponse(id=method.id, visuals=[visual_response(v) for v in method.visuals], **values)


def readiness_items(assessment: Assessment | None) -> list[ReadinessResponse]:
    rows = {r.item: r for r in assessment.readiness} if assessment else {}
    return [
        ReadinessResponse(
            item=item,
            section=section.lower(),
            label=ITEM_LABELS[item],
            readiness=rows[item].readiness if item in rows else None,
            notes=rows[item].notes if item in rows else None,
        )
        for item, section in ITEM_SECTIONS.items()
    ]


def readiness_scores(items: list[ReadinessResponse]) -> ReadinessScores:
    """Not ready 0, Somewhat 1, Ready 2. A section score sums its items; overall sums all."""
    by_section = {"child": 0, "caregiver": 0, "environment": 0}
    for item in items:
        by_section[item.section] += SCORES.get(item.readiness, 0)
    return ReadinessScores(**by_section, overall=sum(by_section.values()))


def dsm5_symptoms(assessment: Assessment | None) -> list[str]:
    """Symptoms chosen on behavior rows, in list order, without repeats."""
    chosen = {b.dsm5_symptom for b in assessment.behaviors} if assessment else set()
    return [s for s in DSM5_SYMPTOMS if s in chosen]


def page_response(assessment: Assessment | None) -> AssessmentPageResponse:
    items = readiness_items(assessment)
    values = {f: getattr(assessment, f) for f in AssessmentPatchRequest.model_fields} if assessment else {}
    return AssessmentPageResponse(
        **values,
        behaviors=[BehaviorResponse.model_validate(b) for b in assessment.behaviors] if assessment else [],
        methods=[method_response(m) for m in assessment.methods] if assessment else [],
        readiness_items=items,
        dsm5_symptoms=dsm5_symptoms(assessment),
        readiness_scores=readiness_scores(items),
    )


def load_method(session: Session, plan_id: int, method_id: int) -> AssessmentMethod:
    return get_owned(session, AssessmentMethod, method_id, "assessment_id", assessment_id_of(session, plan_id))


def load_visual(session: Session, plan_id: int, method_id: int, visual_id: int) -> AssessmentVisual:
    load_method(session, plan_id, method_id)
    return get_owned(session, AssessmentVisual, visual_id, "method_id", method_id)


def store_upload(upload: UploadFile) -> str:
    """Save an uploaded image or PDF and return its storage key.

    The extension decides how the file is served, so only safe ones are allowed.
    """
    suffix = Path(upload.filename or "").suffix.lower()
    if suffix not in UPLOAD_SUFFIXES:
        raise HTTPException(422, "Upload a PNG, JPEG, GIF, WebP image or a PDF")
    UPLOAD_DIR.mkdir(exist_ok=True)
    key = f"{uuid.uuid4().hex}{suffix}"
    (UPLOAD_DIR / key).write_bytes(upload.file.read())
    return key


def remove_uploads(keys: list[str]) -> None:
    """Delete stored files once their rows are gone."""
    for key in keys:
        (UPLOAD_DIR / key).unlink(missing_ok=True)


def copy_upload(key: str) -> str:
    """Copy a stored file under a new key, so a cloned plan owns its own copy."""
    new_key = f"{uuid.uuid4().hex}{Path(key).suffix}"
    shutil.copyfile(UPLOAD_DIR / key, UPLOAD_DIR / new_key)
    return new_key


@router.get("/")
def get_assessment(plan_id: int, session: SessionDep) -> AssessmentPageResponse:
    load_plan(session, plan_id)
    return page_response(find_assessment(session, plan_id))


@router.patch("/")
def patch_assessment(plan_id: int, body: AssessmentPatchRequest, session: SessionDep) -> AssessmentPageResponse:
    load_plan_for_write(session, plan_id)
    assessment = get_or_create_assessment(session, plan_id)
    apply_patch(assessment, body)
    if "telehealth_readiness_assessment_needed" in body.model_fields_set and not assessment.telehealth_readiness_assessment_needed:
        assessment.telehealth_assessment_date = None
        assessment.readiness.clear()
    session.commit()
    return page_response(assessment)


@router.get("/templates/")
def get_templates(plan_id: int, session: SessionDep) -> AssessmentTemplateCatalogResponse:
    load_plan(session, plan_id)
    return AssessmentTemplateCatalogResponse(
        page={
            "parent_interview_summary": "<p>The caregiver reported the following concerns, history and priorities:</p>",
            "assessment_results": "<p>Areas of strength:</p><p>Areas of deficit:</p>",
            "priorities": "<p>Based on the results above, treatment will first focus on:</p>",
        },
        methods={
            tool: {
                "rationale": f"<p>The {tool} was used to identify:</p>",
                "selection_rationale": f"<p>The {tool} was selected because:</p>",
                "tool_description": f"<p>The {tool} measures the following domains and modules:</p>",
                "client_score": f"<p>On the {tool}, the client scored:</p>",
            }
            for tool in ASSESSMENT_TOOLS
        },
    )


@router.post("/behaviors/", status_code=201)
def create_behavior(plan_id: int, body: BehaviorCreateRequest, session: SessionDep) -> BehaviorResponse:
    load_plan_for_write(session, plan_id)
    behavior = AssessmentBehavior(assessment_id=get_or_create_assessment(session, plan_id).id, **body.model_dump())
    session.add(behavior)
    session.commit()
    return BehaviorResponse.model_validate(behavior)


@router.patch("/behaviors/{behavior_id}/")
def patch_behavior(plan_id: int, behavior_id: int, body: BehaviorPatchRequest, session: SessionDep) -> BehaviorResponse:
    load_plan_for_write(session, plan_id)
    behavior = get_owned(session, AssessmentBehavior, behavior_id, "assessment_id", assessment_id_of(session, plan_id))
    apply_patch(behavior, body)
    session.commit()
    return BehaviorResponse.model_validate(behavior)


@router.delete("/behaviors/{behavior_id}/", status_code=204)
def delete_behavior(plan_id: int, behavior_id: int, session: SessionDep) -> None:
    load_plan_for_write(session, plan_id)
    behavior = get_owned(session, AssessmentBehavior, behavior_id, "assessment_id", assessment_id_of(session, plan_id))
    if session.scalar(select(CrisisPlan.id).where(CrisisPlan.assessment_behavior_id == behavior.id)) is not None:
        raise HTTPException(409, "This behavior has a crisis plan. Delete the crisis plan first.")
    session.delete(behavior)
    session.commit()


@router.post("/methods/", status_code=201)
def create_method(plan_id: int, body: MethodCreateRequest, session: SessionDep) -> MethodResponse:
    load_plan_for_write(session, plan_id)
    method = AssessmentMethod(assessment_id=get_or_create_assessment(session, plan_id).id, **body.model_dump())
    session.add(method)
    session.commit()
    return method_response(method)


@router.patch("/methods/{method_id}/")
def patch_method(plan_id: int, method_id: int, body: MethodPatchRequest, session: SessionDep) -> MethodResponse:
    load_plan_for_write(session, plan_id)
    method = load_method(session, plan_id, method_id)
    apply_patch(method, body)
    session.commit()
    return method_response(method)


@router.delete("/methods/{method_id}/", status_code=204)
def delete_method(plan_id: int, method_id: int, session: SessionDep) -> None:
    load_plan_for_write(session, plan_id)
    method = load_method(session, plan_id, method_id)
    keys = [v.file_storage_key for v in method.visuals]
    session.delete(method)
    session.commit()
    remove_uploads(keys)


@router.patch("/readiness/{item}/")
def patch_readiness(plan_id: int, item: str, body: ReadinessPatchRequest, session: SessionDep) -> ReadinessResponse:
    load_plan_for_write(session, plan_id)
    if item not in ITEM_SECTIONS:
        raise HTTPException(404, "Readiness item not found")
    assessment = get_or_create_assessment(session, plan_id)
    row = next((r for r in assessment.readiness if r.item == item), None)
    if row is None:
        row = AssessmentReadiness(item=item)
        assessment.readiness.append(row)
    apply_patch(row, body)
    session.commit()
    return next(r for r in readiness_items(assessment) if r.item == item)


@router.post("/methods/{method_id}/visuals/", status_code=201)
def create_visuals(plan_id: int, method_id: int, files: list[UploadFile], session: SessionDep) -> list[VisualResponse]:
    load_plan_for_write(session, plan_id)
    method = load_method(session, plan_id, method_id)
    visuals = [AssessmentVisual(file_storage_key=store_upload(f)) for f in files]
    method.visuals.extend(visuals)
    session.commit()
    return [visual_response(v) for v in visuals]


@router.patch("/methods/{method_id}/visuals/{visual_id}/")
def patch_visual(plan_id: int, method_id: int, visual_id: int, body: VisualPatchRequest, session: SessionDep) -> VisualResponse:
    load_plan_for_write(session, plan_id)
    visual = load_visual(session, plan_id, method_id, visual_id)
    apply_patch(visual, body)
    session.commit()
    return visual_response(visual)


@router.patch("/methods/{method_id}/visuals/{visual_id}/file/")
def replace_visual_file(plan_id: int, method_id: int, visual_id: int, file: UploadFile, session: SessionDep) -> VisualResponse:
    load_plan_for_write(session, plan_id)
    visual = load_visual(session, plan_id, method_id, visual_id)
    old_key = visual.file_storage_key
    visual.file_storage_key = store_upload(file)
    session.commit()
    remove_uploads([old_key])
    return visual_response(visual)


@router.delete("/methods/{method_id}/visuals/{visual_id}/", status_code=204)
def delete_visual(plan_id: int, method_id: int, visual_id: int, session: SessionDep) -> None:
    load_plan_for_write(session, plan_id)
    visual = load_visual(session, plan_id, method_id, visual_id)
    session.delete(visual)
    session.commit()
    remove_uploads([visual.file_storage_key])


def min_visible(obj: object, field: str, minimum: int, row_id: int | None = None) -> list[PageError]:
    """An error when a rich text field has fewer visible characters than required."""
    if visible_length(getattr(obj, field)) >= minimum:
        return []
    message = "This field is required" if getattr(obj, field) is None else f"Enter at least {minimum} characters"
    return [PageError(field=field, row_id=row_id, message=message)]


def behavior_errors(assessment: Assessment) -> list[PageError]:
    if assessment.no_maladaptive_behavior:
        if assessment.behaviors:
            return [PageError(field="no_maladaptive_behavior", message="Delete the behaviors or clear the no maladaptive behavior box")]
        return []
    if not assessment.behaviors:
        return [PageError(field="no_maladaptive_behavior", message="Add at least one maladaptive behavior or check no maladaptive behavior")]
    errors = []
    for b in assessment.behaviors:
        errors += min_visible(b, "behavior", 16, b.id) + required(b, ["dsm5_symptom"], b.id) + min_visible(b, "parent_concerns", 16, b.id)
    return errors


def method_errors(assessment: Assessment) -> list[PageError]:
    if not assessment.methods:
        return [PageError(field="methods", message="Add at least one assessment method")]
    errors = []
    for m in assessment.methods:
        errors += required(m, ["tool", "assessment_date"], m.id)
        for field in METHOD_TEXT_FIELDS:
            errors += min_visible(m, field, LONG_TEXT_MIN, m.id)
        for v in m.visuals:
            errors += required(v, ["title"], v.id) + min_visible(v, "analysis", 16, v.id)
    return errors


def telehealth_errors(assessment: Assessment) -> list[PageError]:
    rated = [r for r in assessment.readiness if r.readiness is not None or r.notes is not None]
    if not assessment.telehealth_readiness_assessment_needed:
        if assessment.telehealth_assessment_date or rated:
            return [PageError(field="telehealth_readiness_assessment_needed", message="Clear the telehealth date and ratings, or check the box")]
        return []
    errors = required(assessment, ["telehealth_assessment_date"])
    rows = {r.item: r for r in assessment.readiness}
    for item in ITEM_SECTIONS:
        row = rows.get(item)
        if row is None or row.readiness is None:
            errors.append(PageError(field=f"readiness_{item}", message="Choose a rating"))
        if row is None or row.notes is None:
            errors.append(PageError(field=f"notes_{item}", message="Add notes"))
    return errors


def assessment_status(session: Session, plan: TreatmentPlan) -> PageStatusResponse:
    assessment = find_assessment(session, plan.id)
    if assessment is None:
        return PageStatusResponse(page="assessment", status="empty")
    errors = required(assessment, ["initial_assessment_date", "diagnostic_report_reviewed", "reassessment_date"])
    if assessment.initial_assessment_date and assessment.reassessment_date and assessment.reassessment_date <= assessment.initial_assessment_date:
        errors.append(PageError(field="reassessment_date", message="Must be after the initial assessment date"))
    for field in ("parent_interview_summary", "assessment_results", "priorities"):
        errors += min_visible(assessment, field, LONG_TEXT_MIN)
    errors += min_visible(assessment, "observations", 4)
    errors += behavior_errors(assessment) + method_errors(assessment) + telehealth_errors(assessment)
    return result("assessment", errors)


CHECKERS["assessment"] = assessment_status
