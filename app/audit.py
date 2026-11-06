"""Record changes to admin records and plans in the change history.

A flush listener compares each changed record's columns before and after, and writes one AuditEvent per
record in the same transaction. The signed-in user comes from `session.info["user"]`, set by
`current_user`; writes without a signed-in user (seed, tests writing directly) are not recorded.
"""

from datetime import UTC, datetime

from fastapi.encoders import jsonable_encoder
from sqlalchemy import event, insert, inspect
from sqlalchemy.orm import Session

from app.models import AppUser, AuditEvent, Client, ClientAssignment, GoalName, Provider, Role, RolePermission, TreatmentPlan

RECORD_TYPES = {
    Role: "role",
    RolePermission: "access",
    AppUser: "user",
    GoalName: "goal name",
    Client: "client",
    Provider: "provider",
    ClientAssignment: "assignment",
    TreatmentPlan: "plan",
}
PLAN_FIELDS = {"status", "signature"}
SECRET_FIELDS = {"password_hash", "failed_logins", "locked_until"}


def label(session: Session, obj: object) -> str:
    """A readable name for the record."""
    match obj:
        case Role() | AppUser() | Provider():
            return getattr(obj, "name", None) or obj.display_name
        case RolePermission():
            role = session.get(Role, obj.role_id)
            return f"{role.name if role else f'Role {obj.role_id}'}: {obj.key}"
        case GoalName():
            return f"{obj.prefix} {obj.label}"
        case Client():
            return f"{obj.first_name} {obj.last_name}"
        case ClientAssignment():
            provider, client = session.get(Provider, obj.provider_id), session.get(Client, obj.client_id)
            return f"{provider.display_name if provider else obj.provider_id} for {f'{client.first_name} {client.last_name}' if client else obj.client_id}"
        case TreatmentPlan():
            return f"Plan {obj.id}"


def values(obj: object, before: bool) -> dict[str, list]:
    """Every non-empty column, as [value, None] (deleted) or [None, value] (created)."""
    state = inspect(obj)
    found = {}
    for attr in state.mapper.column_attrs:
        value = state.attrs[attr.key].value
        if attr.key not in ("id", *SECRET_FIELDS) and value is not None:
            found[attr.key] = [value, None] if before else [None, value]
    return found


def changed(obj: object) -> dict[str, list]:
    """Columns whose value changed in this flush, as [old, new]."""
    state = inspect(obj)
    found = {}
    for attr in state.mapper.column_attrs:
        history = state.attrs[attr.key].history
        if attr.key not in SECRET_FIELDS and history.has_changes() and history.added:
            old = history.deleted[0] if history.deleted else None
            if old != history.added[0]:
                found[attr.key] = [old, history.added[0]]
    return found


def plan_action(obj: TreatmentPlan, kind: str, changes: dict[str, list]) -> tuple[str, dict[str, list]] | None:
    """Plans: record creation (or cloning) and signing, not page edits."""
    if kind == "created":
        return ("cloned" if obj.parent_treatment_plan_id else "created"), changes
    if kind == "changed":
        changes = {k: v for k, v in changes.items() if k in PLAN_FIELDS}
        if not changes:
            return None
        return ("signed" if changes.get("status", [None, None])[1] == "signed" else "changed"), changes
    return kind, changes


@event.listens_for(Session, "after_flush")
def record_changes(session: Session, _flush_context) -> None:
    user = session.info.get("user")
    if user is None:
        return
    rows = []
    with session.no_autoflush:
        for kind, objects in (("created", session.new), ("changed", session.dirty), ("deleted", session.deleted)):
            for obj in objects:
                record_type = RECORD_TYPES.get(type(obj))
                if record_type is None:
                    continue
                changes = {"created": lambda: values(obj, before=False), "changed": lambda: changed(obj),
                           "deleted": lambda: values(obj, before=True)}[kind]()
                action = kind
                if isinstance(obj, TreatmentPlan):
                    result = plan_action(obj, kind, changes)
                    if result is None:
                        continue
                    action, changes = result
                if kind == "changed" and not changes:
                    continue
                rows.append({
                    "at": datetime.now(UTC), "user_id": user.id, "user_name": user.display_name, "action": action,
                    "record_type": record_type, "record_id": getattr(obj, "id", None), "label": label(session, obj),
                    "changes": jsonable_encoder(changes),
                })
    if rows:
        session.connection().execute(insert(AuditEvent), rows)
