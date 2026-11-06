"""Turn a user's authenticator codes off from the command line, e.g. for the last Admin after a lost phone.

Run: `uv run python -m app.reset_mfa --user-id 1`
The user's sessions end. An Admin sets codes up again at the next sign-in.
"""

import argparse

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app import models  # noqa: F401
from app.db import Base, SessionLocal, engine
from app.mfa import turn_off
from app.migrate import add_missing_columns
from app.models import AppUser, UserSession


def reset_mfa(session: Session, user_id: int) -> AppUser:
    user = session.get(AppUser, user_id)
    if user is None:
        raise ValueError(f"No user with id {user_id}")
    turn_off(user)
    session.execute(delete(UserSession).where(UserSession.user_id == user.id))
    session.commit()
    return user


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--user-id", type=int, required=True)
    args = parser.parse_args()
    Base.metadata.create_all(engine)
    add_missing_columns(engine)
    with SessionLocal() as session:
        user = reset_mfa(session, args.user_id)
        print(f"Authenticator codes are off for {user.display_name}")


if __name__ == "__main__":
    main()
