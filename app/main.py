"""FastAPI app: API routes plus the static UI."""

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.staticfiles import StaticFiles

from app import audit, models  # noqa: F401  registers tables and the change-history listener
from app.access import current_user, page_access
from app.db import Base, engine
from app.migrate import add_missing_columns
from app.routes import assessment, assignments, brg, child, clients, clone, crisis, discharge, goal_names, goals, history, pcg, sag, education, family, information, medical, medication, mfa, options, plan, providers, referral, roles, session, therapy, treatment, uploads, users


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Create tables on startup."""
    Base.metadata.create_all(engine)
    add_missing_columns(engine)
    yield


app = FastAPI(title="Treatment Plan v3", lifespan=lifespan)
PAGE_ROUTERS = [
    (information.router, "information"),
    (medical.router, "medical"),
    (referral.router, "referral"),
    (medication.router, "medication"),
    (therapy.router, "therapy"),
    (education.router, "education"),
    (family.router, "family"),
    (child.router, "child"),
    (assessment.router, "assessment"),
    (crisis.router, "crisis"),
    (pcg.router, "goals"),
    (sag.router, "goals"),
    (brg.router, "goals"),
    (discharge.router, "discharge"),
    (treatment.router, "treatment"),
]

app.include_router(session.router)
app.include_router(mfa.router)
app.include_router(plan.router)
app.include_router(clone.router)
app.include_router(uploads.router)
app.include_router(options.router, dependencies=[Depends(current_user)])
app.include_router(roles.router, dependencies=[page_access("admin_roles")])
app.include_router(users.router, dependencies=[page_access("admin_users")])
app.include_router(goal_names.router, dependencies=[page_access("admin_goal_names")])
app.include_router(clients.router, dependencies=[page_access("admin_clients")])
app.include_router(providers.router, dependencies=[page_access("admin_providers")])
app.include_router(assignments.router, dependencies=[page_access("admin_assignments")])
app.include_router(history.router, dependencies=[page_access("admin_history")])
for router, key in PAGE_ROUTERS:
    app.include_router(router, dependencies=[page_access(key)])


@app.middleware("http")
async def revalidate_static(request: Request, call_next):
    """Make browsers revalidate UI files so updates show up without a hard refresh."""
    response = await call_next(request)
    if not request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-cache"
    return response


assessment.UPLOAD_DIR.mkdir(exist_ok=True)
app.mount("/", StaticFiles(directory="static", html=True), name="static")
