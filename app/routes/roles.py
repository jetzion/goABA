"""Admin: roles and the access matrix."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.access import ACTIONS, ADMIN_PAGES, ALLOWED_LEVELS, LEVELS
from app.enums import PAGES
from app.models import AppUser, Role, RolePermission
from app.routes.plan import SessionDep
from app.rules import Body, OneOf, Text

router = APIRouter(prefix="/api/v2/admin/roles")

GROUPS = {**{k: "page" for k in PAGES}, **{k: "action" for k in ACTIONS}, **{k: "admin" for k in ADMIN_PAGES}}


class RoleRequest(Body):
    name: Text(1, 100)


class LevelRequest(Body):
    level: OneOf(LEVELS)


class MatrixKey(BaseModel):
    key: str
    group: str
    allowed: list[str]


class RoleResponse(BaseModel):
    id: int
    name: str
    locked: bool
    user_count: int
    permissions: dict[str, str]


class RolesResponse(BaseModel):
    keys: list[MatrixKey]
    roles: list[RoleResponse]


def role_response(session: Session, role: Role) -> RoleResponse:
    """A locked role shows the highest level for every key; others show stored cells, none by default."""
    stored = {p.key: p.level for p in role.permissions}
    permissions = {k: allowed[-1] if role.locked else stored.get(k, "none") for k, allowed in ALLOWED_LEVELS.items()}
    users = session.scalar(select(func.count()).where(AppUser.role_id == role.id))
    return RoleResponse(id=role.id, name=role.name, locked=role.locked, user_count=users, permissions=permissions)


def load_role(session: Session, role_id: int) -> Role:
    role = session.get(Role, role_id)
    if role is None:
        raise HTTPException(404, "Role not found")
    return role


def load_unlocked(session: Session, role_id: int) -> Role:
    role = load_role(session, role_id)
    if role.locked:
        raise HTTPException(409, f"The {role.name} role is locked and cannot be changed")
    return role


def check_name_free(session: Session, name: str, role_id: int | None = None) -> None:
    """Names are unique ignoring case, so "admin" cannot sit beside "Admin"."""
    clash = session.scalar(select(Role).where(func.lower(Role.name) == name.lower(), Role.id != role_id))
    if clash:
        raise HTTPException(409, f"A role named {clash.name} already exists")


@router.get("/")
def list_roles(session: SessionDep) -> RolesResponse:
    """The matrix rows and every role with its cells."""
    keys = [MatrixKey(key=k, group=GROUPS[k], allowed=list(allowed)) for k, allowed in ALLOWED_LEVELS.items()]
    roles = session.scalars(select(Role).order_by(Role.locked.desc(), Role.name)).all()
    return RolesResponse(keys=keys, roles=[role_response(session, r) for r in roles])


@router.post("/", status_code=201)
def create_role(body: RoleRequest, session: SessionDep) -> RoleResponse:
    """A new role starts with no access."""
    check_name_free(session, body.name)
    role = Role(name=body.name)
    session.add(role)
    session.commit()
    return role_response(session, role)


@router.patch("/{role_id}/")
def rename_role(role_id: int, body: RoleRequest, session: SessionDep) -> RoleResponse:
    role = load_unlocked(session, role_id)
    check_name_free(session, body.name, role.id)
    role.name = body.name
    session.commit()
    return role_response(session, role)


@router.delete("/{role_id}/", status_code=204)
def delete_role(role_id: int, session: SessionDep) -> None:
    role = load_unlocked(session, role_id)
    users = session.scalar(select(func.count()).where(AppUser.role_id == role.id))
    if users:
        raise HTTPException(409, f"{users} user(s) have the {role.name} role. Give them another role first.")
    session.delete(role)
    session.commit()


@router.put("/{role_id}/permissions/{key}/")
def set_permission(role_id: int, key: str, body: LevelRequest, session: SessionDep) -> RoleResponse:
    """Set one matrix cell."""
    role = load_unlocked(session, role_id)
    if key not in ALLOWED_LEVELS:
        raise HTTPException(404, "Unknown access key")
    if body.level not in ALLOWED_LEVELS[key]:
        raise HTTPException(422, f"{key} allows only: {', '.join(ALLOWED_LEVELS[key])}")
    cell = next((p for p in role.permissions if p.key == key), None)
    if cell is None:
        role.permissions.append(RolePermission(key=key, level=body.level))
    else:
        cell.level = body.level
    session.commit()
    return role_response(session, role)
