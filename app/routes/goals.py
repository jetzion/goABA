"""Goals page status: PCG, SAG and BRG combined."""

from sqlalchemy.orm import Session

from app.completion import CHECKERS, PageStatusResponse, result
from app.models import TreatmentPlan
from app.routes.brg import brg_errors
from app.routes.pcg import pcg_errors
from app.routes.sag import sag_errors


def goals_status(session: Session, plan: TreatmentPlan) -> PageStatusResponse:
    """Empty only when all three sections are empty. Any section error marks Goals in error."""
    sections = [pcg_errors(session, plan), sag_errors(session, plan), brg_errors(session, plan)]
    if all(empty for empty, _ in sections):
        return PageStatusResponse(page="goals", status="empty")
    return result("goals", [e for _, errors in sections for e in errors])


CHECKERS["goals"] = goals_status
