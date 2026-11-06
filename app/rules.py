"""Shared value rules from the spec, as reusable Pydantic types."""

import html
import re
from datetime import date
from typing import Annotated

import nh3
from app.enums import US_STATES
from pydantic import AfterValidator, BaseModel, BeforeValidator, ConfigDict, Field, model_validator

US_STATE_SET = frozenset(US_STATES)

INVISIBLE = re.compile(r"[\s​-‏⁠﻿]")
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class Body(BaseModel):
    """Base for request bodies: unknown fields rejected, spaces stripped, blanks become null."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @model_validator(mode="before")
    @classmethod
    def blank_to_null(cls, data: object) -> object:
        """Turn blank strings into None."""
        if isinstance(data, dict):
            return {k: None if isinstance(v, str) and not v.strip() else v for k, v in data.items()}
        return data


def _state_validator(allowed: frozenset[str]):
    def check(value: str) -> str:
        if value not in allowed:
            raise ValueError("must be a two-letter US state or territory code")
        return value

    return check


def _email(value: str) -> str:
    if not EMAIL.match(value):
        raise ValueError("must be a valid email address")
    return value


def _first_of_month(value: date) -> date:
    if value.day != 1:
        raise ValueError("must be the first day of a month")
    return value


def _goal_month(value: str) -> str:
    match = re.fullmatch(r"(0[1-9]|1[0-2])-(\d{4})", value)
    if not match:
        raise ValueError("must be mm-yyyy")
    return f"{match[2]}-{match[1]}"


def sanitize_html(value: str) -> str:
    """Remove unsafe HTML."""
    return nh3.clean(value)


def visible_length(value: str | None) -> int:
    """Count visible characters after removing tags, spaces and invisible characters."""
    if not value:
        return 0
    text = html.unescape(nh3.clean(value, tags=set()))
    return len(INVISIBLE.sub("", text))


def Text(min_length: int = 0, max_length: int = 255):
    """Plain text with length limits."""
    return Annotated[str, Field(min_length=min_length, max_length=max_length)]


def RichText(max_length: int = 50_000, min_visible: int = 0):
    """Sanitized HTML with a stored max length and optional visible-character minimum."""

    def check(value: str) -> str:
        clean = sanitize_html(value)
        if len(clean) > max_length:
            raise ValueError(f"must be at most {max_length} characters")
        if visible_length(clean) < min_visible:
            raise ValueError(f"must have at least {min_visible} visible characters")
        return clean

    return Annotated[str, AfterValidator(check)]


Phone = Annotated[str, Field(pattern=r"^\d{10}$")]
Email = Annotated[str, Field(max_length=255), AfterValidator(_email)]
StateCode = Annotated[str, BeforeValidator(str.upper), AfterValidator(_state_validator(US_STATE_SET))]
StateCodeCZ = Annotated[str, BeforeValidator(str.upper), AfterValidator(_state_validator(US_STATE_SET | {"CZ"}))]
FirstOfMonth = Annotated[date, AfterValidator(_first_of_month)]
GoalMonth = Annotated[str, AfterValidator(_goal_month)]


def OneOf(options: tuple[str, ...]):
    """A string that must be one of the listed options."""

    def check(value: str) -> str:
        if value not in options:
            raise ValueError("must be one of the listed options")
        return value

    return Annotated[str, AfterValidator(check)]


def IntRange(low: int, high: int):
    """An integer within an inclusive range."""
    return Annotated[int, Field(ge=low, le=high)]


def _not_future_month(value: date) -> date:
    if value > date.today().replace(day=1):
        raise ValueError("cannot be in the future")
    return value


PastMonth = Annotated[date, AfterValidator(_first_of_month), AfterValidator(_not_future_month)]


def at_least_one_field(body: BaseModel) -> None:
    """Raise when a create body has no non-null field."""
    if all(value is None for value in body.model_dump().values()):
        raise ValueError("Provide at least one field")
