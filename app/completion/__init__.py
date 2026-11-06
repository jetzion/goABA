"""Page status: empty, completed or error, with field errors."""

from collections.abc import Callable
from datetime import date
from typing import Literal

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.enums import PAGES
from app.models import TreatmentPlan


class PageError(BaseModel):
    """One completion error."""

    field: str
    row_id: int | None = None
    message: str


class PageStatusResponse(BaseModel):
    """Status of one page."""

    page: str
    status: Literal["empty", "completed", "error"]
    errors: list[PageError] = []


Checker = Callable[[Session, TreatmentPlan], PageStatusResponse]

CHECKERS: dict[str, Checker] = {}


def page_status(session: Session, plan: TreatmentPlan, page: str) -> PageStatusResponse:
    """Run the page's checker, or report empty when none is registered yet."""
    checker = CHECKERS.get(page)
    if checker is None:
        return PageStatusResponse(page=page, status="empty")
    return checker(session, plan)


def all_statuses(session: Session, plan: TreatmentPlan) -> list[PageStatusResponse]:
    """Status of every page in navigation order."""
    return [page_status(session, plan, page) for page in PAGES]


def required(obj: object, fields: list[str], row_id: int | None = None) -> list[PageError]:
    """An error for each listed attribute that is None."""
    return [
        PageError(field=f, row_id=row_id, message="This field is required")
        for f in fields
        if getattr(obj, f) is None
    ]


def result(page: str, errors: list[PageError]) -> PageStatusResponse:
    """Completed when there are no errors, otherwise error."""
    return PageStatusResponse(page=page, status="error" if errors else "completed", errors=errors)


def month_after_birth(client_dob: date | None, value: date | None, field: str, row_id: int) -> list[PageError]:
    """A month/year date cannot fall in a month before the client's birth month."""
    if client_dob is None or value is None or value >= client_dob.replace(day=1):
        return []
    return [PageError(field=field, row_id=row_id, message="Must be after the client's date of birth")]
