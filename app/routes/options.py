"""Option lists for the UI, so dropdowns use the same values the API validates."""

from fastapi import APIRouter

from app import enums

router = APIRouter(prefix="/api/v2")


@router.get("/options/")
def get_options() -> dict[str, list[str] | dict[str, list[str] | str]]:
    """Every uppercase tuple or dict of tuples in app.enums."""
    options = {}
    for name, value in vars(enums).items():
        if name.isupper() and isinstance(value, tuple):
            options[name] = list(value)
        elif name.isupper() and isinstance(value, dict):
            options[name] = {k: v if isinstance(v, str) else list(v) for k, v in value.items()}
    return options
