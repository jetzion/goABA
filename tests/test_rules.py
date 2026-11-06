"""Shared value rules."""

from datetime import date

import pytest
from pydantic import ValidationError

from app.rules import (
    Body,
    Email,
    FirstOfMonth,
    GoalMonth,
    Phone,
    RichText,
    StateCode,
    StateCodeCZ,
    visible_length,
)


class Sample(Body):
    phone: Phone | None = None
    email: Email | None = None
    state: StateCode | None = None
    state_cz: StateCodeCZ | None = None
    month: FirstOfMonth | None = None
    goal_month: GoalMonth | None = None
    notes: RichText(max_length=40, min_visible=4) | None = None


def test_unknown_field_rejected():
    with pytest.raises(ValidationError):
        Sample(other=1)


def test_blank_becomes_null_and_spaces_stripped():
    sample = Sample(phone="   ", email="  a@b.co  ")
    assert sample.phone is None
    assert sample.email == "a@b.co"


@pytest.mark.parametrize("value", ["123456789", "12345678901", "123-456-7890"])
def test_phone_rejects(value):
    with pytest.raises(ValidationError):
        Sample(phone=value)


def test_phone_accepts_ten_digits():
    assert Sample(phone="5125550100").phone == "5125550100"


def test_email():
    with pytest.raises(ValidationError):
        Sample(email="not-an-email")


def test_state_uppercased_and_checked():
    assert Sample(state="tx").state == "TX"
    with pytest.raises(ValidationError):
        Sample(state="CZ")
    assert Sample(state_cz="cz").state_cz == "CZ"


def test_first_of_month():
    assert Sample(month="2024-03-01").month == date(2024, 3, 1)
    with pytest.raises(ValidationError):
        Sample(month="2024-03-02")


def test_goal_month_stored_as_yyyy_mm():
    assert Sample(goal_month="03-2027").goal_month == "2027-03"
    with pytest.raises(ValidationError):
        Sample(goal_month="2027-03")


def test_rich_text_sanitized():
    assert Sample(notes="<p>hello<script>x</script></p>").notes == "<p>hello</p>"


def test_rich_text_visible_minimum():
    with pytest.raises(ValidationError):
        Sample(notes="<p> a&nbsp;b ​</p>")


def test_rich_text_stored_max():
    with pytest.raises(ValidationError):
        Sample(notes="x" * 41)


def test_visible_length():
    assert visible_length("<p>ab <b>c</b>&nbsp;</p>") == 3
    assert visible_length(None) == 0
