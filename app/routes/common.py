"""Helpers shared by page route modules."""

from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import Base


def apply_patch(target: Base, body: BaseModel) -> None:
    """Copy the fields the client sent onto the row. Omitted fields keep their value."""
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(target, field, value)


def get_owned[T: Base](session: Session, model: type[T], row_id: int, owner_field: str, owner_id: int | None) -> T:
    """Load a row that belongs to the given owner, or raise 404."""
    row = session.get(model, row_id)
    if row is None or owner_id is None or getattr(row, owner_field) != owner_id:
        raise HTTPException(404, f"{model.__name__} not found")
    return row
