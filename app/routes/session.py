"""Sign in with email and password, sign out, who am I, and change your own password.

A session lasts 8 hours. The cookie holds a random token; the database keeps only its SHA-256.
Five wrong passwords in a row lock the account for 15 minutes.
"""

import os
import secrets
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict, field_validator
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.access import COOKIE, CurrentUser, find_session, token_hash, user_access
from app.db import get_session
from app.models import AppUser, UserSession
from app.passwords import check_new_password, hash_password, normal_email, verify_password

router = APIRouter(prefix="/api/v2/session")

SESSION_LENGTH = timedelta(hours=8)
MAX_FAILED = 5
LOCKOUT = timedelta(minutes=15)
WRONG = "Email or password is incorrect"
SECURE_COOKIE = os.environ.get("TP_SECURE_COOKIE") == "1"
_DUMMY_HASH = hash_password("timing equalizer, never a real password")

SessionDep = Annotated[Session, Depends(get_session)]


class UserResponse(BaseModel):
    id: int
    display_name: str
    email: str | None
    role: str
    provider_id: int | None
    must_change_password: bool


class SessionResponse(BaseModel):
    user: UserResponse | None
    access: dict[str, str]


class SignInRequest(BaseModel):
    """Passwords are taken exactly as typed; only the email is trimmed and lowercased."""

    model_config = ConfigDict(extra="forbid")

    email: str
    password: str


class ChangePasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def rule(cls, value: str) -> str:
        check_new_password(value)
        return value


def user_response(user: AppUser) -> UserResponse:
    return UserResponse(
        id=user.id, display_name=user.display_name, email=user.email, role=user.role.name,
        provider_id=user.provider_id, must_change_password=user.must_change_password,
    )


def as_utc(value: datetime) -> datetime:
    """SQLite gives back naive datetimes; they are stored as UTC."""
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def start_session(session: Session, response: Response, user: AppUser) -> None:
    token = secrets.token_urlsafe(32)
    now = datetime.now(UTC)
    session.add(UserSession(token_hash=token_hash(token), user_id=user.id, created_at=now, expires_at=now + SESSION_LENGTH))
    response.set_cookie(COOKIE, token, max_age=int(SESSION_LENGTH.total_seconds()), httponly=True, samesite="strict", secure=SECURE_COOKIE)


def end_other_sessions(session: Session, user_id: int, keep_token: str | None = None) -> None:
    """Delete the user's sessions, except the one with keep_token."""
    query = delete(UserSession).where(UserSession.user_id == user_id)
    if keep_token:
        query = query.where(UserSession.token_hash != token_hash(keep_token))
    session.execute(query)


@router.get("/")
def who_am_i(session: SessionDep, tp_session: Annotated[str | None, Cookie()] = None) -> SessionResponse:
    """The signed-in user (or null) and their level for every access key."""
    found = find_session(session, tp_session)
    if found is None:
        return SessionResponse(user=None, access={})
    user = session.get_one(AppUser, found.user_id)
    return SessionResponse(user=user_response(user), access=user_access(session, user))


@router.post("/")
def sign_in(body: SignInRequest, response: Response, session: SessionDep) -> UserResponse:
    """Check the password and start an 8-hour session. Unknown email and wrong password look the same."""
    user = session.scalar(select(AppUser).where(func.lower(AppUser.email) == normal_email(body.email)))
    if user is None:
        verify_password(_DUMMY_HASH, body.password)
        raise HTTPException(401, WRONG)
    now = datetime.now(UTC)
    if user.locked_until and as_utc(user.locked_until) > now:
        raise HTTPException(429, "Too many wrong passwords. Try again in 15 minutes.")
    if not verify_password(user.password_hash, body.password):
        user.failed_logins += 1
        if user.failed_logins >= MAX_FAILED:
            user.failed_logins, user.locked_until = 0, now + LOCKOUT
        session.commit()
        raise HTTPException(401, WRONG)
    user.failed_logins, user.locked_until = 0, None
    start_session(session, response, user)
    session.commit()
    return user_response(user)


@router.delete("/", status_code=204)
def sign_out(response: Response, session: SessionDep, tp_session: Annotated[str | None, Cookie()] = None) -> None:
    """End this session on the server and clear the cookie."""
    if tp_session:
        session.execute(delete(UserSession).where(UserSession.token_hash == token_hash(tp_session)))
        session.commit()
    response.delete_cookie(COOKIE, httponly=True, samesite="strict", secure=SECURE_COOKIE)


@router.post("/password/", status_code=204)
def change_password(body: ChangePasswordRequest, user: CurrentUser, session: SessionDep,
                    tp_session: Annotated[str | None, Cookie()] = None) -> None:
    """Change your own password. Ends your other sessions and clears a forced change."""
    if not verify_password(user.password_hash, body.current_password):
        raise HTTPException(422, "Your current password is incorrect")
    if body.new_password == body.current_password:
        raise HTTPException(422, "Choose a password different from the current one")
    user.password_hash = hash_password(body.new_password)
    user.must_change_password = False
    end_other_sessions(session, user.id, keep_token=tp_session)
    session.commit()
