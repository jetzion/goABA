"""Medical page: schemas, routes and completion."""

from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.completion import CHECKERS, PageError, PageStatusResponse, required, result
from app.enums import ASD_SEVERITY, DELIVERY_TYPES, DIAGNOSES, HEARING, MEDICAL_SELECTIONS, VISION
from app.models import MedicalDiagnosis, MedicalInfo, MedicalSelection, TreatmentPlan
from app.routes.plan import SessionDep, load_plan, load_plan_for_write
from app.rules import Body, IntRange, OneOf, RichText, StateCode, Text

router = APIRouter(prefix="/api/v2/treatment_plans/{plan_id}/pages/medical")

OneWord = Annotated[str, Field(pattern=r"^\S{2,16}$")]
Age = IntRange(0, 99)
Year = IntRange(1900, 2100)


class MedicalInfoPatch(Body):
    allergies: Text(4, 255) | None = None
    special_diets: Text(4, 255) | None = None
    hearing_difficulty: OneOf(HEARING) | None = None
    hearing_screening_date: date | None = None
    vision_difficulty: OneOf(VISION) | None = None
    vision_screening_date: date | None = None
    trauma_history: RichText(50_000, 4) | None = None
    hospitalization_history: RichText(50_000, 4) | None = None
    asd_severity_level: OneOf(ASD_SEVERITY) | None = None
    asd_diagnosis_provider_name: Text(8, 255) | None = None
    asd_diagnosis_city: Text(2, 255) | None = None
    asd_diagnosis_state: StateCode | None = None
    asd_diagnosis_year: Year | None = None
    child_delivery_type: OneOf(DELIVERY_TYPES) | None = None
    child_gestational_age_weeks: Age | None = None
    child_weight_at_birth_pounds: Age | None = None
    child_weight_at_birth_ounces: IntRange(0, 15) | None = None
    child_sitting_up_age_months: Age | None = None
    child_crawling_age_months: Age | None = None
    child_walking_age_years: Age | None = None
    child_walking_age_months: Age | None = None
    child_standing_age_years: IntRange(0, 9) | None = None
    child_standing_age_months: Age | None = None
    child_babbling_age_months: Age | None = None
    child_first_word: OneWord | None = None
    child_second_word: OneWord | None = None
    child_first_words_age_months: Age | None = None


INFO_FIELDS = list(MedicalInfoPatch.model_fields)


class MedicalInfoResponse(MedicalInfoPatch):
    model_config = ConfigDict(extra="ignore", from_attributes=True)

    id: int


class MedicalDiagnosisBody(Body):
    diagnosis_name: OneOf(DIAGNOSES) | None = None
    provider_name: Text(8, 255) | None = None
    city: Text(2, 255) | None = None
    state: StateCode | None = None
    year: Year | None = None


DIAGNOSIS_FIELDS = list(MedicalDiagnosisBody.model_fields)


class MedicalDiagnosisResponse(MedicalDiagnosisBody):
    model_config = ConfigDict(extra="ignore", from_attributes=True)

    id: int


class MedicalSelectionCreate(Body):
    selection_type: Literal["EARLY_INTERVENTION", "PREGNANCY_ISSUE", "REGRESSION"]
    value: str

    @model_validator(mode="after")
    def value_in_type(self) -> "MedicalSelectionCreate":
        """The value must belong to its selection type."""
        if self.value not in MEDICAL_SELECTIONS[self.selection_type]:
            raise ValueError(f"value is not an option for {self.selection_type}")
        return self


class MedicalSelectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    selection_type: str
    value: str


class MedicalPageResponse(BaseModel):
    medical_info: MedicalInfoResponse | None
    diagnoses: list[MedicalDiagnosisResponse]
    selections: list[MedicalSelectionResponse]


def find_info(session: Session, plan_id: int) -> MedicalInfo | None:
    return session.scalar(select(MedicalInfo).where(MedicalInfo.treatment_plan_id == plan_id))


def get_or_create_info(session: Session, plan_id: int) -> MedicalInfo:
    info = find_info(session, plan_id)
    if info is None:
        info = MedicalInfo(treatment_plan_id=plan_id)
        session.add(info)
        session.flush()
    return info


def load_diagnosis(session: Session, plan_id: int, diagnosis_id: int) -> MedicalDiagnosis:
    info = find_info(session, plan_id)
    diagnosis = session.get(MedicalDiagnosis, diagnosis_id)
    if info is None or diagnosis is None or diagnosis.medical_info_id != info.id:
        raise HTTPException(404, "Diagnosis not found")
    return diagnosis


@router.get("/")
def get_medical(plan_id: int, session: SessionDep) -> MedicalPageResponse:
    load_plan(session, plan_id)
    info = find_info(session, plan_id)
    return MedicalPageResponse(
        medical_info=MedicalInfoResponse.model_validate(info) if info else None,
        diagnoses=[MedicalDiagnosisResponse.model_validate(d) for d in info.diagnoses] if info else [],
        selections=[MedicalSelectionResponse.model_validate(s) for s in info.selections] if info else [],
    )


@router.patch("/")
def patch_medical(plan_id: int, body: MedicalInfoPatch, session: SessionDep) -> MedicalInfoResponse:
    load_plan_for_write(session, plan_id)
    info = get_or_create_info(session, plan_id)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(info, field, value)
    session.commit()
    return MedicalInfoResponse.model_validate(info)


@router.post("/diagnoses/", status_code=201)
def create_diagnosis(plan_id: int, body: MedicalDiagnosisBody, session: SessionDep) -> MedicalDiagnosisResponse:
    load_plan_for_write(session, plan_id)
    info = get_or_create_info(session, plan_id)
    diagnosis = MedicalDiagnosis(medical_info_id=info.id, **body.model_dump())
    session.add(diagnosis)
    session.commit()
    return MedicalDiagnosisResponse.model_validate(diagnosis)


@router.patch("/diagnoses/{diagnosis_id}/")
def patch_diagnosis(plan_id: int, diagnosis_id: int, body: MedicalDiagnosisBody, session: SessionDep) -> MedicalDiagnosisResponse:
    load_plan_for_write(session, plan_id)
    diagnosis = load_diagnosis(session, plan_id, diagnosis_id)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(diagnosis, field, value)
    session.commit()
    return MedicalDiagnosisResponse.model_validate(diagnosis)


@router.delete("/diagnoses/{diagnosis_id}/", status_code=204)
def delete_diagnosis(plan_id: int, diagnosis_id: int, session: SessionDep) -> None:
    load_plan_for_write(session, plan_id)
    session.delete(load_diagnosis(session, plan_id, diagnosis_id))
    session.commit()


@router.post("/selections/", status_code=201)
def create_selection(plan_id: int, body: MedicalSelectionCreate, session: SessionDep) -> MedicalSelectionResponse:
    load_plan_for_write(session, plan_id)
    info = get_or_create_info(session, plan_id)
    selection = MedicalSelection(medical_info_id=info.id, selection_type=body.selection_type, value=body.value)
    session.add(selection)
    try:
        session.commit()
    except IntegrityError:
        raise HTTPException(409, "This value is already selected")
    return MedicalSelectionResponse.model_validate(selection)


@router.delete("/selections/{selection_type}/{selection_id}/", status_code=204)
def delete_selection(plan_id: int, selection_type: str, selection_id: int, session: SessionDep) -> None:
    load_plan_for_write(session, plan_id)
    info = find_info(session, plan_id)
    selection = session.get(MedicalSelection, selection_id)
    if info is None or selection is None or selection.medical_info_id != info.id or selection.selection_type != selection_type:
        raise HTTPException(404, "Selection not found")
    session.delete(selection)
    session.commit()


def selection_errors(selections: list[MedicalSelection]) -> list[PageError]:
    """Each group needs a value, and None cannot be combined with another value."""
    errors = []
    for selection_type in MEDICAL_SELECTIONS:
        values = [s.value for s in selections if s.selection_type == selection_type]
        if not values:
            errors.append(PageError(field=selection_type, message="Select at least one value"))
        elif "None" in values and len(values) > 1:
            errors.append(PageError(field=selection_type, message="None cannot be combined with another value"))
    return errors


def medical_status(session: Session, plan: TreatmentPlan) -> PageStatusResponse:
    info = find_info(session, plan.id)
    if info is None:
        return PageStatusResponse(page="medical", status="empty")
    errors = required(info, INFO_FIELDS)
    for diagnosis in info.diagnoses:
        errors += required(diagnosis, DIAGNOSIS_FIELDS, diagnosis.id)
    errors += selection_errors(info.selections)
    return result("medical", errors)


CHECKERS["medical"] = medical_status
