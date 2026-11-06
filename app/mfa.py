"""Authenticator codes (TOTP): new keys, the setup QR code, and checking a code once."""

import hmac
from datetime import UTC, datetime

import pyotp
import segno

ISSUER = "Treatment Plan"
DRIFT_STEPS = 1


def new_secret() -> str:
    return pyotp.random_base32()


def setup_uri(secret: str, email: str) -> str:
    """The otpauth:// link an authenticator app reads from the QR code."""
    return pyotp.TOTP(secret).provisioning_uri(name=email, issuer_name=ISSUER)


def qr_svg(uri: str) -> str:
    return segno.make(uri, error="m").svg_inline(scale=5, border=2)


def matching_step(secret: str, code: str, last_step: int | None, now: datetime | None = None) -> int | None:
    """The time step the code belongs to, within one step of drift, or None.

    A step at or before last_step was already used and never matches, so a code works once.
    """
    totp = pyotp.TOTP(secret)
    current = totp.timecode(now or datetime.now(UTC))
    for step in range(current - DRIFT_STEPS, current + DRIFT_STEPS + 1):
        if last_step is not None and step <= last_step:
            continue
        if hmac.compare_digest(totp.generate_otp(step), code.strip()):
            return step
    return None
