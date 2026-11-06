"""Set a user's email and password from the command line, e.g. for the first Admin.

Run: `uv run python -m app.set_password --user-id 1 --email you@example.com`
The password is asked for twice and never shown. The user can use it right away (no forced change).
"""

import argparse
from getpass import getpass

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app import models  # noqa: F401
from app.db import Base, SessionLocal, engine
from app.migrate import add_missing_columns
from app.models import AppUser, UserSession
from app.passwords import check_new_password, hash_password, normal_email


def set_credentials(session: Session, user_id: int, email: str, password: str) -> AppUser:
    """Store the email and password hash, clear any lockout and end the user's sessions."""
    check_new_password(password)
    user = session.get(AppUser, user_id)
    if user is None:
        raise ValueError(f"No user with id {user_id}")
    user.email = normal_email(email)
    user.password_hash = hash_password(password)
    user.must_change_password = False
    user.failed_logins = 0
    user.locked_until = None
    session.execute(delete(UserSession).where(UserSession.user_id == user.id))
    session.commit()
    return user


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--user-id", type=int, required=True)
    parser.add_argument("--email", required=True)
    args = parser.parse_args()
    Base.metadata.create_all(engine)
    add_missing_columns(engine)
    password = getpass("New password: ")
    if getpass("Repeat it: ") != password:
        raise SystemExit("The passwords do not match")
    with SessionLocal() as session:
        user = set_credentials(session, args.user_id, args.email, password)
        print(f"{user.display_name} can now sign in as {user.email}")


if __name__ == "__main__":
    main()
