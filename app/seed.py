"""Seed one client and one blank plan. Run with `uv run python -m app.seed`."""

from datetime import date

from app import models  # noqa: F401
from app.db import Base, SessionLocal, engine
from app.migrate import add_missing_columns
from app.models import AppUser, Role, Client, GoalName, ClientAssignment, ClientGuardian, ClientInsurance, Provider, TreatmentPlan


GOAL_NAMES = [
    ("Parent training", "PT-1", "Uses reinforcement after target behavior"),
    ("Parent training", "PT-2", "Follows the prompting hierarchy"),
    ("Parent training", "PT-3", "Records behavior data accurately"),
    ("Communication", "COM-1", "Requests preferred items (mands)"),
    ("Communication", "COM-2", "Follows one-step directions"),
    ("Communication", "COM-9", "Retired communication goal"),
    ("Social skills", "SOC-1", "Takes turns in play"),
    ("Daily living", "DL-1", "Washes hands independently"),
    ("Behavior change", "BC-1", "Reduce aggression"),
    ("Behavior change", "BC-2", "Reduce elopement"),
    ("Behavior change", "BC-3", "Reduce self-injury"),
]


def seed_goal_names() -> None:
    """Add the goal name catalog once. COM-9 is inactive."""
    with SessionLocal() as session:
        if session.query(GoalName).first():
            return
        session.add_all(GoalName(focus_area=a, prefix=p, label=l, active=p != "COM-9") for a, p, l in GOAL_NAMES)
        session.commit()


def seed_admin() -> None:
    """Add the locked Admin role and make provider 1 an Admin user, once."""
    with SessionLocal() as session:
        if session.query(Role).first():
            return
        admin = Role(name="Admin", locked=True)
        session.add(admin)
        session.flush()
        session.add(AppUser(display_name="Dana Lee, BCBA", role_id=admin.id, provider_id=1))
        session.commit()


def seed() -> None:
    """Create tables, a demo client and a plan if the database is empty."""
    Base.metadata.create_all(engine)
    add_missing_columns(engine)
    seed_goal_names()
    with SessionLocal() as session:
        if session.get(Client, 1):
            print("Already seeded")
            seed_admin()
            return
        session.add(Client(id=1, first_name="Sam", last_name="Rivera", date_of_birth=date(2019, 4, 12), sex="Male"))
        session.add_all([
            Provider(id=1, display_name="Dana Lee, BCBA"),
            Provider(id=2, display_name="Chris Park"),
            Provider(id=3, display_name="Morgan Diaz, BCBA"),
        ])
        session.flush()
        session.add_all([
            ClientAssignment(client_id=1, provider_id=1, role="home_bcba"),
            ClientAssignment(client_id=1, provider_id=2, role="bt"),
            ClientAssignment(client_id=1, provider_id=3, role="substitute_bcba"),
            ClientGuardian(client_id=1, display_name="Ana Rivera", role="Mother"),
            ClientInsurance(client_id=1, rank="primary", payor_name="Blue Cross Blue Shield of Texas",
                            member_id="XJH123456789", date_start=date(2025, 1, 1)),
            TreatmentPlan(client_id=1, bay="3", version=3, provider_id=1),
        ])
        session.commit()
        seed_admin()
        print("Seeded client 1, providers, Admin user and plan 1")


if __name__ == "__main__":
    seed()
