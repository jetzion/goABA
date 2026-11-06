"""Family page: schemas, routes and completion."""

from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, model_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.completion import CHECKERS, PageError, PageStatusResponse, required, result
from app.enums import (
    CAREGIVER_TYPES,
    CUSTODY_TYPES,
    FAMILY_INFO_TYPES,
    MARITAL_STATUSES,
    MEMBER_ROLES,
    RELATIONSHIPS,
    SIBLING_RELATIONSHIPS,
)
from app.models import Family, FamilyAdditionalInfo, FamilyMember, FamilySibling, TreatmentPlan
from app.routes.common import apply_patch, get_owned
from app.routes.plan import SessionDep, load_plan, load_plan_for_write
from app.rules import Body, Email, IntRange, OneOf, Phone, RichText, StateCodeCZ, Text, visible_length

router = APIRouter(prefix="/api/v2/treatment_plans/{plan_id}/pages/family")

ALIASES = {
    "Adoptive Siblings": "Adoptive-siblings",
    "Church (or other religious organization)": "Church (or other religion organization)",
}
NOT_CAREGIVER = "Parent not a caregiver"


def _alias(value: object) -> object:
    return ALIASES.get(value, value) if isinstance(value, str) else value


Zip = Annotated[str, Field(pattern=r"^\d{5}$")]


class FamilyMemberPatchRequest(Body):
    full_name: Text(6, 255) | None = None
    member_role: OneOf(MEMBER_ROLES) | None = None
    caregiver_type: OneOf(CAREGIVER_TYPES) | None = None
    relationship_to_client: OneOf(RELATIONSHIPS) | None = None
    custody_type: OneOf(CUSTODY_TYPES) | None = None
    marital_status: OneOf(MARITAL_STATUSES) | None = None
    job_title: Text(4, 255) | None = None
    email: Email | None = None
    phone: Phone | None = None
    street_address_line_one: Text(8, 255) | None = None
    street_address_line_two: Text(0, 255) | None = None
    street_address_city: Text(2, 255) | None = None
    street_address_state: StateCodeCZ | None = None
    street_address_zip: Zip | None = None


FamilyMemberCreateRequest = FamilyMemberPatchRequest
MEMBER_REQUIRED = [f for f in FamilyMemberPatchRequest.model_fields if f not in ("caregiver_type", "street_address_line_two")]


class FamilyMemberResponse(FamilyMemberPatchRequest):
    model_config = ConfigDict(extra="ignore", from_attributes=True)

    id: int


class FamilySiblingPatchRequest(Body):
    sibling_relationship: Annotated[OneOf(SIBLING_RELATIONSHIPS), BeforeValidator(_alias)] | None = None
    sibling_age: IntRange(0, 99) | None = None
    sibling_diagnosis: Text(4, 255) | None = None


FamilySiblingCreateRequest = FamilySiblingPatchRequest
SIBLING_FIELDS = list(FamilySiblingPatchRequest.model_fields)


class FamilySiblingResponse(FamilySiblingPatchRequest):
    model_config = ConfigDict(extra="ignore", from_attributes=True)

    id: int


class FamilyTaggedItemCreate(Body):
    info_type: Literal["MATERNAL_MEDICAL_HISTORY", "PATERNAL_MEDICAL_HISTORY", "COMMUNITY_SUPPORT"]
    value: Annotated[str, BeforeValidator(_alias), Field(min_length=1, max_length=500)]

    @model_validator(mode="after")
    def value_in_type(self) -> "FamilyTaggedItemCreate":
        if self.value not in FAMILY_INFO_TYPES[self.info_type]:
            raise ValueError(f"value is not an option for {self.info_type}")
        return self


class FamilyTaggedItemResponse(BaseModel):
    id: int
    info_type: str
    value: str


class FamilyPatch(Body):
    cultural_consideration: RichText(800) | None = None


class FamilyPageResponse(BaseModel):
    cultural_consideration: str | None
    members: list[FamilyMemberResponse]
    siblings: list[FamilySiblingResponse]
    maternal_medical_history: list[FamilyTaggedItemResponse]
    paternal_medical_history: list[FamilyTaggedItemResponse]
    community_support: list[FamilyTaggedItemResponse]
    additional_info: list[FamilyTaggedItemResponse]


def find_family(session: Session, plan_id: int) -> Family | None:
    return session.scalar(select(Family).where(Family.treatment_plan_id == plan_id))


def get_or_create_family(session: Session, plan_id: int) -> Family:
    family = find_family(session, plan_id)
    if family is None:
        family = Family(treatment_plan_id=plan_id)
        session.add(family)
        session.flush()
    return family


def tagged(item: FamilyAdditionalInfo) -> FamilyTaggedItemResponse:
    return FamilyTaggedItemResponse(id=item.id, info_type=item.info_type, value=item.description)


def page_response(family: Family | None) -> FamilyPageResponse:
    items = family.additional_info if family else []

    def of_type(info_type: str) -> list[FamilyTaggedItemResponse]:
        return [tagged(i) for i in items if i.info_type == info_type]

    return FamilyPageResponse(
        cultural_consideration=family.cultural_consideration if family else None,
        members=[FamilyMemberResponse.model_validate(m) for m in family.members] if family else [],
        siblings=[FamilySiblingResponse.model_validate(s) for s in family.siblings] if family else [],
        maternal_medical_history=of_type("MATERNAL_MEDICAL_HISTORY"),
        paternal_medical_history=of_type("PATERNAL_MEDICAL_HISTORY"),
        community_support=of_type("COMMUNITY_SUPPORT"),
        additional_info=[tagged(i) for i in items if i.info_type not in FAMILY_INFO_TYPES],
    )


def family_id_of(session: Session, plan_id: int) -> int | None:
    family = find_family(session, plan_id)
    return family.id if family else None


def check_single_primary(session: Session, member: FamilyMember) -> None:
    """Only one member may be the primary caregiver."""
    if member.caregiver_type != "Primary caregiver":
        return
    others = select(FamilyMember.id).where(
        FamilyMember.family_id == member.family_id,
        FamilyMember.caregiver_type == "Primary caregiver",
        FamilyMember.id != member.id,
    )
    if session.scalar(others) is not None:
        raise HTTPException(409, "Another member is already the primary caregiver")


@router.get("/")
def get_family(plan_id: int, session: SessionDep) -> FamilyPageResponse:
    load_plan(session, plan_id)
    return page_response(find_family(session, plan_id))


@router.patch("/")
def patch_family(plan_id: int, body: FamilyPatch, session: SessionDep) -> FamilyPageResponse:
    load_plan_for_write(session, plan_id)
    family = get_or_create_family(session, plan_id)
    apply_patch(family, body)
    session.commit()
    return page_response(family)


@router.post("/members/", status_code=201)
def create_member(plan_id: int, body: FamilyMemberCreateRequest, session: SessionDep) -> FamilyMemberResponse:
    load_plan_for_write(session, plan_id)
    member = FamilyMember(family_id=get_or_create_family(session, plan_id).id, **body.model_dump())
    session.add(member)
    session.flush()
    check_single_primary(session, member)
    session.commit()
    return FamilyMemberResponse.model_validate(member)


@router.patch("/members/{member_id}/")
def patch_member(plan_id: int, member_id: int, body: FamilyMemberPatchRequest, session: SessionDep) -> FamilyMemberResponse:
    load_plan_for_write(session, plan_id)
    member = get_owned(session, FamilyMember, member_id, "family_id", family_id_of(session, plan_id))
    apply_patch(member, body)
    check_single_primary(session, member)
    session.commit()
    return FamilyMemberResponse.model_validate(member)


@router.delete("/members/{member_id}/", status_code=204)
def delete_member(plan_id: int, member_id: int, session: SessionDep) -> None:
    load_plan_for_write(session, plan_id)
    session.delete(get_owned(session, FamilyMember, member_id, "family_id", family_id_of(session, plan_id)))
    session.commit()


@router.post("/siblings/", status_code=201)
def create_sibling(plan_id: int, body: FamilySiblingCreateRequest, session: SessionDep) -> FamilySiblingResponse:
    load_plan_for_write(session, plan_id)
    sibling = FamilySibling(family_id=get_or_create_family(session, plan_id).id, **body.model_dump())
    session.add(sibling)
    session.commit()
    return FamilySiblingResponse.model_validate(sibling)


@router.patch("/siblings/{sibling_id}/")
def patch_sibling(plan_id: int, sibling_id: int, body: FamilySiblingPatchRequest, session: SessionDep) -> FamilySiblingResponse:
    load_plan_for_write(session, plan_id)
    sibling = get_owned(session, FamilySibling, sibling_id, "family_id", family_id_of(session, plan_id))
    apply_patch(sibling, body)
    session.commit()
    return FamilySiblingResponse.model_validate(sibling)


@router.delete("/siblings/{sibling_id}/", status_code=204)
def delete_sibling(plan_id: int, sibling_id: int, session: SessionDep) -> None:
    load_plan_for_write(session, plan_id)
    session.delete(get_owned(session, FamilySibling, sibling_id, "family_id", family_id_of(session, plan_id)))
    session.commit()


@router.post("/additional_info/", status_code=201)
def create_tagged_item(plan_id: int, body: FamilyTaggedItemCreate, session: SessionDep) -> FamilyTaggedItemResponse:
    load_plan_for_write(session, plan_id)
    item = FamilyAdditionalInfo(
        family_id=get_or_create_family(session, plan_id).id, info_type=body.info_type, description=body.value
    )
    session.add(item)
    try:
        session.commit()
    except IntegrityError:
        raise HTTPException(409, "This value is already in the list")
    return tagged(item)


@router.delete("/additional_info/{item_id}/", status_code=204)
def delete_tagged_item(plan_id: int, item_id: int, session: SessionDep) -> None:
    load_plan_for_write(session, plan_id)
    session.delete(get_owned(session, FamilyAdditionalInfo, item_id, "family_id", family_id_of(session, plan_id)))
    session.commit()


def member_errors(member: FamilyMember) -> list[PageError]:
    """Required fields, plus the caregiver type rule for the member's role."""
    errors = required(member, MEMBER_REQUIRED, member.id)
    if member.member_role == NOT_CAREGIVER and member.caregiver_type is not None:
        errors.append(PageError(field="caregiver_type", row_id=member.id, message="Must be empty for a parent who is not a caregiver"))
    if member.member_role not in (None, NOT_CAREGIVER) and member.caregiver_type is None:
        errors.append(PageError(field="caregiver_type", row_id=member.id, message="This field is required"))
    return errors


def family_status(session: Session, plan: TreatmentPlan) -> PageStatusResponse:
    family = find_family(session, plan.id)
    if family is None:
        return PageStatusResponse(page="family", status="empty")
    errors = []
    if not family.members:
        errors.append(PageError(field="members", message="Add at least one family member"))
    for member in family.members:
        errors += member_errors(member)
    for sibling in family.siblings:
        errors += required(sibling, SIBLING_FIELDS, sibling.id)
    for info_type in FAMILY_INFO_TYPES:
        if not any(i.info_type == info_type for i in family.additional_info):
            errors.append(PageError(field=info_type, message="Select at least one value"))
    if visible_length(family.cultural_consideration) < 4:
        errors.append(PageError(field="cultural_consideration", message="Enter at least 4 characters"))
    return result("family", errors)


CHECKERS["family"] = family_status
