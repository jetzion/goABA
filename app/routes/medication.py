"""Medication page: schemas, routes and completion."""

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, model_validator
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.completion import CHECKERS, PageError, PageStatusResponse, month_after_birth, required, result
from app.models import Client, Medication, TreatmentPlan
from app.routes.common import apply_patch, get_owned
from app.routes.plan import SessionDep, load_plan, load_plan_for_write
from app.rules import Body, PastMonth, Text, at_least_one_field

router = APIRouter(prefix="/api/v2/treatment_plans/{plan_id}/pages/medications")


class MedicationPatchRequest(Body):
    medication_name: Text(4, 255) | None = None
    dosage: Text(2, 255) | None = None
    start_date: PastMonth | None = None
    physician_name: Text(8, 255) | None = None
    reason: Text(8, 255) | None = None


class MedicationCreateRequest(MedicationPatchRequest):
    @model_validator(mode="after")
    def has_a_field(self) -> "MedicationCreateRequest":
        at_least_one_field(self)
        return self


FIELDS = list(MedicationPatchRequest.model_fields)


class MedicationResponse(MedicationPatchRequest):
    model_config = ConfigDict(extra="ignore", from_attributes=True)

    id: int


class NoMedicationPatch(Body):
    no_medication: bool


class MedicationPageResponse(BaseModel):
    no_medication: bool | None
    medications: list[MedicationResponse]


def plan_medications(session: Session, plan_id: int) -> list[Medication]:
    return list(session.scalars(select(Medication).where(Medication.treatment_plan_id == plan_id).order_by(Medication.id)))


def page_response(session: Session, plan: TreatmentPlan) -> MedicationPageResponse:
    return MedicationPageResponse(
        no_medication=None if plan.has_medication is None else not plan.has_medication,
        medications=[MedicationResponse.model_validate(m) for m in plan_medications(session, plan.id)],
    )


@router.get("/")
def get_medications(plan_id: int, session: SessionDep) -> MedicationPageResponse:
    return page_response(session, load_plan(session, plan_id))


@router.patch("/")
def patch_no_medication(plan_id: int, body: NoMedicationPatch, session: SessionDep) -> MedicationPageResponse:
    plan = load_plan_for_write(session, plan_id)
    plan.has_medication = not body.no_medication
    session.commit()
    return page_response(session, plan)


@router.post("/", status_code=201)
def create_medication(plan_id: int, body: MedicationCreateRequest, session: SessionDep) -> MedicationResponse:
    load_plan_for_write(session, plan_id)
    medication = Medication(treatment_plan_id=plan_id, **body.model_dump())
    session.add(medication)
    session.commit()
    return MedicationResponse.model_validate(medication)


@router.delete("/all/", status_code=204)
def delete_all_medications(plan_id: int, session: SessionDep) -> None:
    load_plan_for_write(session, plan_id)
    session.execute(delete(Medication).where(Medication.treatment_plan_id == plan_id))
    session.commit()


@router.patch("/{medication_id}/")
def patch_medication(plan_id: int, medication_id: int, body: MedicationPatchRequest, session: SessionDep) -> MedicationResponse:
    load_plan_for_write(session, plan_id)
    medication = get_owned(session, Medication, medication_id, "treatment_plan_id", plan_id)
    apply_patch(medication, body)
    session.commit()
    return MedicationResponse.model_validate(medication)


@router.delete("/{medication_id}/", status_code=204)
def delete_medication(plan_id: int, medication_id: int, session: SessionDep) -> None:
    load_plan_for_write(session, plan_id)
    session.delete(get_owned(session, Medication, medication_id, "treatment_plan_id", plan_id))
    session.commit()


def medication_status(session: Session, plan: TreatmentPlan) -> PageStatusResponse:
    rows = plan_medications(session, plan.id)
    if plan.has_medication is None:
        if not rows:
            return PageStatusResponse(page="medication", status="empty")
        return result("medication", [PageError(field="no_medication", message="Select whether the client takes medication")])
    if plan.has_medication is False:
        errors = [PageError(field="no_medication", message="Delete the medications or clear the no medication box")] if rows else []
        return result("medication", errors)
    if not rows:
        return result("medication", [PageError(field="no_medication", message="Add a medication or check no medication")])
    dob = session.get_one(Client, plan.client_id).date_of_birth
    errors = []
    for row in rows:
        errors += required(row, FIELDS, row.id)
        errors += month_after_birth(dob, row.start_date, "start_date", row.id)
    return result("medication", errors)


CHECKERS["medication"] = medication_status
