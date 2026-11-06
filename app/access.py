"""The current user, access keys, their allowed levels, and route access checks.

Two layers: the role decides what a user may do on each page; the client rules decide for which plans.
"""

import hashlib
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.enums import PAGES
from app.models import AppUser, ClientAssignment, RolePermission, TreatmentPlan, UserSession

COOKIE = "tp_session"
OPEN_WHILE_MUST_CHANGE = {"/api/v2/session/", "/api/v2/session/password/"}
OPEN_WHILE_MFA_SETUP = OPEN_WHILE_MUST_CHANGE | {"/api/v2/session/mfa/setup/", "/api/v2/session/mfa/enable/"}

NONE, VIEW, EDIT = "none", "view", "edit"
LEVELS = (NONE, VIEW, EDIT)

ACTIONS = ("create_plan", "sign_plan", "all_clients")
ADMIN_PAGES = ("admin_roles", "admin_users", "admin_goal_names", "admin_clients", "admin_providers", "admin_assignments", "admin_history")

ALLOWED_LEVELS: dict[str, tuple[str, ...]] = {
    **{page: LEVELS for page in PAGES},
    "information": (NONE, VIEW),
    **{action: (NONE, EDIT) for action in ACTIONS},
    **{page: LEVELS for page in ADMIN_PAGES},
    "admin_history": (NONE, VIEW),
}


def token_hash(token: str) -> str:
    """Only this hash of a session token is stored."""
    return hashlib.sha256(token.encode()).hexdigest()


def find_session(session: Session, token: str | None) -> UserSession | None:
    """The unexpired session for a cookie token, if any."""
    if not token:
        return None
    return session.scalar(select(UserSession).where(
        UserSession.token_hash == token_hash(token), UserSession.expires_at > datetime.now(UTC)))


def mfa_setup_required(user: AppUser) -> bool:
    """Admin users must use authenticator codes."""
    return user.role.locked and not user.mfa_enabled


def current_user(request: Request, session: Annotated[Session, Depends(get_session)],
                 tp_session: Annotated[str | None, Cookie()] = None) -> AppUser:
    """The signed-in user, or 401 (also while the authenticator code is still owed).

    Until a temporary password is changed, and then until an Admin sets up authenticator codes,
    only sign-in routes work (403). The user is also kept on the request's session for the change history.
    """
    found = find_session(session, tp_session)
    if found is None:
        raise HTTPException(401, "Sign in first")
    if found.mfa_pending:
        raise HTTPException(401, "Enter your authenticator code first")
    user = session.get_one(AppUser, found.user_id)
    if user.must_change_password and request.url.path not in OPEN_WHILE_MUST_CHANGE:
        raise HTTPException(403, "Change your password first")
    if mfa_setup_required(user) and request.url.path not in OPEN_WHILE_MFA_SETUP:
        raise HTTPException(403, "Set up authenticator codes first")
    session.info["user"] = user
    return user


CurrentUser = Annotated[AppUser, Depends(current_user)]


def user_access(session: Session, user: AppUser) -> dict[str, str]:
    """The user's level for every key."""
    return {key: user_level(session, user, key) for key in ALLOWED_LEVELS}


def user_level(session: Session, user: AppUser, key: str) -> str:
    """A locked role has the highest level for every key. Others default to none."""
    if user.role.locked:
        return ALLOWED_LEVELS[key][-1]
    stored = session.scalar(
        select(RolePermission.level).where(RolePermission.role_id == user.role_id, RolePermission.key == key)
    )
    return stored or NONE


def allows(level: str, needed: str) -> bool:
    """Edit includes view."""
    return LEVELS.index(level) >= LEVELS.index(needed)


def assigned(session: Session, user: AppUser, client_id: int) -> bool:
    """The user's provider is clinically assigned to the client."""
    if user.provider_id is None:
        return False
    return session.scalar(select(ClientAssignment.id).where(
        ClientAssignment.client_id == client_id, ClientAssignment.provider_id == user.provider_id)) is not None


def sees_all_clients(session: Session, user: AppUser) -> bool:
    """Admin, or a role with the All clients action."""
    return user.role.locked or allows(user_level(session, user, "all_clients"), EDIT)


def sees_client(session: Session, user: AppUser, client_id: int) -> bool:
    return sees_all_clients(session, user) or assigned(session, user, client_id)


def edits_plan(session: Session, user: AppUser, plan: TreatmentPlan) -> bool:
    """Admin, the plan's owner, or a provider assigned to its client. All clients alone does not edit."""
    owner = user.provider_id is not None and plan.provider_id == user.provider_id
    return user.role.locked or owner or assigned(session, user, plan.client_id)


def sees_plan(session: Session, user: AppUser, plan: TreatmentPlan) -> bool:
    return edits_plan(session, user, plan) or sees_all_clients(session, user)


def check_plan(session: Session, user: AppUser, plan_id: int, write: bool) -> None:
    """403 unless the user may read (or, for a write, edit) the plan. A missing plan is left to the route's 404."""
    plan = session.get(TreatmentPlan, plan_id)
    if plan is None:
        return
    if not (edits_plan if write else sees_plan)(session, user, plan):
        raise HTTPException(403, "You are not assigned to this client" if write and sees_plan(session, user, plan)
                            else "You do not have access to this client")


def page_access(key: str):
    """Route dependency: GET needs view, other methods need edit. Routes under a plan also check the client rules."""

    def check(request: Request, user: CurrentUser, session: Annotated[Session, Depends(get_session)]) -> None:
        write = request.method != "GET"
        needed = EDIT if write else VIEW
        if not allows(user_level(session, user, key), needed):
            raise HTTPException(403, f"Your role cannot {needed} {key}")
        if "plan_id" in request.path_params:
            check_plan(session, user, int(request.path_params["plan_id"]), write)

    return Depends(check)


def plan_reader(request: Request, user: CurrentUser, session: Annotated[Session, Depends(get_session)]) -> None:
    """Route dependency for plan-level reads: the user must see the plan's client."""
    check_plan(session, user, int(request.path_params["plan_id"]), write=False)


def plan_editor(request: Request, user: CurrentUser, session: Annotated[Session, Depends(get_session)]) -> None:
    """Route dependency for plan-level writes such as signing: the user must be able to edit the plan."""
    check_plan(session, user, int(request.path_params["plan_id"]), write=True)


def action_access(key: str):
    """Route dependency for an action such as signing: the role must allow it."""

    def check(user: CurrentUser, session: Annotated[Session, Depends(get_session)]) -> None:
        if not allows(user_level(session, user, key), EDIT):
            raise HTTPException(403, f"Your role cannot {key.replace('_', ' ')}")

    return Depends(check)
