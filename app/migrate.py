"""Columns and indexes added after a table first shipped. `create_all` makes new tables but never alters old ones."""

from sqlalchemy import Engine, inspect, text

ADDED_COLUMNS = [
    ("provider", "active", "BOOLEAN NOT NULL DEFAULT 1"),
    ("app_user", "email", "VARCHAR"),
    ("app_user", "password_hash", "VARCHAR"),
    ("app_user", "must_change_password", "BOOLEAN NOT NULL DEFAULT 0"),
    ("app_user", "failed_logins", "INTEGER NOT NULL DEFAULT 0"),
    ("app_user", "locked_until", "DATETIME"),
]

ADDED_INDEXES = [
    "CREATE UNIQUE INDEX IF NOT EXISTS ix_app_user_email ON app_user (email)",
]


def add_missing_columns(engine: Engine) -> None:
    """Add each listed column to its table if the table lacks it, then the listed indexes."""
    with engine.begin() as connection:
        for table, column, ddl in ADDED_COLUMNS:
            if column not in {c["name"] for c in inspect(connection).get_columns(table)}:
                connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}"))
        for statement in ADDED_INDEXES:
            connection.execute(text(statement))
