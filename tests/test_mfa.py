"""Authenticator codes: checking a code, clock drift, replay, and the key kept out of the history."""

from datetime import UTC, datetime, timedelta

import pyotp
from sqlalchemy import select

from app.db import SessionLocal
from app.mfa import matching_step, new_secret, qr_svg, setup_uri
from app.models import AppUser, AuditEvent
from tests.test_passwords import make_user

NOW = datetime(2026, 11, 6, 12, 0, 0, tzinfo=UTC)


def code_at(secret: str, when: datetime) -> str:
    return pyotp.TOTP(secret).at(when)


def test_current_code_matches_its_step():
    secret = new_secret()
    step = matching_step(secret, code_at(secret, NOW), None, NOW)
    assert step == pyotp.TOTP(secret).timecode(NOW)


def test_one_step_of_drift_either_way():
    secret = new_secret()
    assert matching_step(secret, code_at(secret, NOW - timedelta(seconds=30)), None, NOW) is not None
    assert matching_step(secret, code_at(secret, NOW + timedelta(seconds=30)), None, NOW) is not None
    assert matching_step(secret, code_at(secret, NOW - timedelta(seconds=90)), None, NOW) is None


def test_wrong_code_and_spaces():
    secret = new_secret()
    code = code_at(secret, NOW)
    assert matching_step(secret, f" {code} ", None, NOW) is not None
    assert matching_step(secret, "000000" if code != "000000" else "111111", None, NOW) is None


def test_used_code_does_not_match_again():
    secret = new_secret()
    code = code_at(secret, NOW)
    step = matching_step(secret, code, None, NOW)
    assert matching_step(secret, code, step, NOW) is None
    assert matching_step(secret, code_at(secret, NOW - timedelta(seconds=30)), step, NOW) is None
    assert matching_step(secret, code_at(secret, NOW + timedelta(seconds=30)), step, NOW) == step + 1


def test_setup_uri_and_qr():
    uri = setup_uri("JBSWY3DPEHPK3PXP", "dana@example.com")
    assert uri.startswith("otpauth://totp/goABA:dana%40example.com?secret=JBSWY3DPEHPK3PXP")
    assert qr_svg(uri).startswith("<svg")


def test_history_never_holds_the_mfa_key(client):
    with SessionLocal() as session:
        session.info["user"] = session.get(AppUser, 1)
        user = make_user(session, "Mfa History User")
        session.commit()
        user.mfa_secret = "JBSWY3DPEHPK3PXP"
        user.mfa_last_step = 123
        user.mfa_enabled = True
        session.commit()
        event = session.scalars(select(AuditEvent).where(AuditEvent.record_type == "user").order_by(AuditEvent.id.desc())).first()
        assert event.label == "Mfa History User" and event.changes == {"mfa_enabled": [False, True]}
        everything = " ".join(str(e.changes) for e in session.scalars(select(AuditEvent)))
        assert "JBSWY3DPEHPK3PXP" not in everything and "mfa_last_step" not in everything
