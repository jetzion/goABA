"""Password hashing with Argon2, and the password rule."""

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

MIN_LENGTH = 8

_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str | None, password: str) -> bool:
    """True when the password matches. A user without a password never matches."""
    if password_hash is None:
        return False
    try:
        return _hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def check_new_password(password: str) -> None:
    """Raise ValueError when a new password breaks the rule."""
    if len(password) < MIN_LENGTH:
        raise ValueError(f"must be at least {MIN_LENGTH} characters")


def normal_email(email: str) -> str:
    return email.strip().lower()
