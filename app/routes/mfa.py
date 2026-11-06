"""Authenticator codes for your own account: the code step at sign-in, setup, and turning them off."""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Cookie, HTTPException
from pydantic import BaseModel, ConfigDict

from app.access import CurrentUser, find_session
from app.mfa import matching_step, new_secret, qr_svg, setup_uri, turn_off
from app.models import AppUser
from app.routes.session import (
    SESSION_LENGTH, SessionDep, UserResponse, check_not_locked, count_failure, end_other_sessions, user_response,
)

router = APIRouter(prefix="/api/v2/session/mfa")

WRONG_CODE = "That code is incorrect"


class CodeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str


class SetupResponse(BaseModel):
    """The key as text, the otpauth link, and the same link as a QR code (inline SVG)."""

    secret: str
    uri: str
    qr_svg: str


def use_code(user: AppUser, code: str) -> bool:
    """True when the code is right and unused; it is then marked used."""
    step = matching_step(user.mfa_secret, code, user.mfa_last_step) if user.mfa_secret else None
    if step is None:
        return False
    user.mfa_last_step = step
    return True


@router.post("/")
def enter_code(body: CodeRequest, session: SessionDep, tp_session: Annotated[str | None, Cookie()] = None) -> UserResponse:
    """Finish signing in: a right code turns the pending session into a full 8-hour one."""
    found = find_session(session, tp_session)
    if found is None or not found.mfa_pending:
        raise HTTPException(401, "Sign in with your password first")
    user = session.get_one(AppUser, found.user_id)
    check_not_locked(user)
    if not use_code(user, body.code):
        count_failure(session, user)
        raise HTTPException(401, WRONG_CODE)
    user.failed_logins, user.locked_until = 0, None
    found.mfa_pending = False
    found.expires_at = datetime.now(UTC) + SESSION_LENGTH
    session.commit()
    return user_response(user)


@router.post("/setup/")
def start_setup(user: CurrentUser, session: SessionDep) -> SetupResponse:
    """Make a new key to scan. Codes stay off until one is confirmed; asking again replaces the key."""
    if user.mfa_enabled:
        raise HTTPException(409, "Authenticator codes are already on")
    user.mfa_secret, user.mfa_last_step = new_secret(), None
    session.commit()
    uri = setup_uri(user.mfa_secret, user.email or user.display_name)
    return SetupResponse(secret=user.mfa_secret, uri=uri, qr_svg=qr_svg(uri))


@router.post("/enable/")
def enable(body: CodeRequest, user: CurrentUser, session: SessionDep,
           tp_session: Annotated[str | None, Cookie()] = None) -> UserResponse:
    """Turn codes on with the first right code from the app. Ends your other sessions."""
    if user.mfa_enabled:
        raise HTTPException(409, "Authenticator codes are already on")
    if user.mfa_secret is None:
        raise HTTPException(409, "Start setup first")
    if not use_code(user, body.code):
        raise HTTPException(422, WRONG_CODE)
    user.mfa_enabled = True
    end_other_sessions(session, user.id, keep_token=tp_session)
    session.commit()
    return user_response(user)


@router.post("/disable/")
def disable(body: CodeRequest, user: CurrentUser, session: SessionDep) -> UserResponse:
    """Turn codes off with a current code. Admin users must keep them on."""
    if user.role.locked:
        raise HTTPException(409, "Admin users must keep authenticator codes on")
    if not user.mfa_enabled:
        raise HTTPException(409, "Authenticator codes are already off")
    if not use_code(user, body.code):
        raise HTTPException(422, WRONG_CODE)
    turn_off(user)
    session.commit()
    return user_response(user)
