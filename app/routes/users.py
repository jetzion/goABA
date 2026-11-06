"""Admin: users, their sign-in email, role and optional provider link, temporary passwords and MFA resets."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, field_validator
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.access import CurrentUser
from app.mfa import turn_off
from app.models import AppUser, Provider, Role, UserSession
from app.passwords import check_new_password, hash_password, normal_email
from app.routes.plan import SessionDep
from app.rules import Body, Email, Text

router = APIRouter(prefix="/api/v2/admin/users")


class UserPatchRequest(Body):
    display_name: Text(1, 255) = None  # type: ignore[assignment]  # omitted is allowed, null is not
    role_id: int = None  # type: ignore[assignment]
    provider_id: int | None = None
    email: Email | None = None


class UserCreateRequest(UserPatchRequest):
    display_name: Text(1, 255)
    role_id: int


class UserRow(BaseModel):
    id: int
    display_name: str
    role_id: int
    role: str
    provider_id: int | None
    email: str | None
    has_password: bool
    must_change_password: bool
    mfa_enabled: bool


class TemporaryPasswordRequest(BaseModel):
    """The password is taken exactly as typed."""

    model_config = ConfigDict(extra="forbid")

    password: str

    @field_validator("password")
    @classmethod
    def rule(cls, value: str) -> str:
        check_new_password(value)
        return value


class Choice(BaseModel):
    id: int
    name: str


class UsersResponse(BaseModel):
    users: list[UserRow]
    roles: list[Choice]
    providers: list[Choice]


def user_row(user: AppUser) -> UserRow:
    return UserRow(
        id=user.id, display_name=user.display_name, role_id=user.role_id, role=user.role.name, provider_id=user.provider_id,
        email=user.email, has_password=user.password_hash is not None, must_change_password=user.must_change_password,
        mfa_enabled=user.mfa_enabled,
    )


def load_user(session: Session, user_id: int) -> AppUser:
    user = session.get(AppUser, user_id)
    if user is None:
        raise HTTPException(404, "User not found")
    return user


def check_refs(session: Session, body: UserPatchRequest, current_provider_id: int | None = None) -> None:
    """The role must exist. A newly linked provider must exist and be active; a kept link may be inactive."""
    if "role_id" in body.model_fields_set and session.get(Role, body.role_id) is None:
        raise HTTPException(422, "Unknown role")
    if body.provider_id is None or body.provider_id == current_provider_id:
        return
    provider = session.get(Provider, body.provider_id)
    if provider is None:
        raise HTTPException(422, "Unknown provider")
    if not provider.active:
        raise HTTPException(422, "That provider is turned off")


def user_values(session: Session, body: UserPatchRequest, user_id: int | None = None) -> dict:
    """The fields sent, with the email lowercased and checked to be free (ignoring case)."""
    data = body.model_dump(exclude_unset=True)
    if data.get("email"):
        data["email"] = normal_email(data["email"])
        clash = session.scalar(select(AppUser).where(func.lower(AppUser.email) == data["email"], AppUser.id != user_id))
        if clash:
            raise HTTPException(409, f"{clash.display_name} already signs in with that email")
    return data


def admin_count(session: Session) -> int:
    return session.scalar(select(func.count()).select_from(AppUser).join(Role).where(Role.locked))


def check_keeps_an_admin(session: Session, user: AppUser) -> None:
    """Refuse a change that would leave no Admin user."""
    if user.role.locked and admin_count(session) <= 1:
        raise HTTPException(409, "This is the last Admin user. Give another user the Admin role first.")


def commit_unique(session: Session) -> None:
    try:
        session.commit()
    except IntegrityError:
        raise HTTPException(409, "That provider is already linked to another user")


@router.get("/")
def list_users(session: SessionDep) -> UsersResponse:
    """Users with the roles and providers to choose from."""
    users = session.scalars(select(AppUser).order_by(AppUser.display_name)).all()
    roles = session.scalars(select(Role).order_by(Role.locked.desc(), Role.name)).all()
    linked = select(AppUser.provider_id).where(AppUser.provider_id.is_not(None))
    providers = session.scalars(select(Provider).where(Provider.active | Provider.id.in_(linked)).order_by(Provider.display_name)).all()
    return UsersResponse(
        users=[user_row(u) for u in users],
        roles=[Choice(id=r.id, name=r.name) for r in roles],
        providers=[Choice(id=p.id, name=p.display_name) for p in providers],
    )


@router.post("/", status_code=201)
def create_user(body: UserCreateRequest, session: SessionDep) -> UserRow:
    check_refs(session, body)
    user = AppUser(**user_values(session, body))
    session.add(user)
    commit_unique(session)
    return user_row(user)


@router.patch("/{user_id}/")
def patch_user(user_id: int, body: UserPatchRequest, session: SessionDep) -> UserRow:
    user = load_user(session, user_id)
    check_refs(session, body, user.provider_id)
    if "role_id" in body.model_fields_set and body.role_id != user.role_id:
        check_keeps_an_admin(session, user)
    for field, value in user_values(session, body, user.id).items():
        setattr(user, field, value)
    commit_unique(session)
    session.refresh(user)
    return user_row(user)


@router.delete("/{user_id}/", status_code=204)
def delete_user(user_id: int, session: SessionDep, me: CurrentUser) -> None:
    user = load_user(session, user_id)
    if user.id == me.id:
        raise HTTPException(409, "You cannot delete yourself")
    check_keeps_an_admin(session, user)
    session.delete(user)
    session.commit()


@router.post("/{user_id}/password/", status_code=204)
def set_temporary_password(user_id: int, body: TemporaryPasswordRequest, session: SessionDep, me: CurrentUser) -> None:
    """Give a user a one-time password. They must change it at next sign-in; their sessions end and any lockout clears."""
    user = load_user(session, user_id)
    if user.id == me.id:
        raise HTTPException(409, "Use Change password for your own account")
    if not user.email:
        raise HTTPException(422, "Give the user an email first; it is how they sign in")
    user.password_hash = hash_password(body.password)
    user.must_change_password = True
    user.failed_logins, user.locked_until = 0, None
    session.execute(delete(UserSession).where(UserSession.user_id == user.id))
    session.commit()


@router.post("/{user_id}/mfa/reset/", status_code=204)
def reset_mfa(user_id: int, session: SessionDep, me: CurrentUser) -> None:
    """Turn a user's authenticator codes off, e.g. after a lost phone, and end their sessions."""
    user = load_user(session, user_id)
    if user.id == me.id:
        raise HTTPException(409, "You cannot reset your own authenticator codes here")
    turn_off(user)
    session.execute(delete(UserSession).where(UserSession.user_id == user.id))
    session.commit()
