# goABA

A web app for writing ABA treatment plans: a FastAPI JSON API and a browser UI for the 13 plan pages, with an Admin area for roles and page access.

- Spec: `TREATMENT-PLAN.md`
- Build plan, layout and decisions: `PLAN.md`

## Requirements

- [uv](https://docs.astral.sh/uv/) (`brew install uv`)
- Python 3.15 (uv installs it if missing)

## Setup

```bash
uv sync
uv run python -m app.seed
```

The seed adds a demo client, plan 1, the goal-name catalog and the locked Admin role with one Admin user (Dana Lee). It is safe to run again.

If the project folder was moved or `uv run` says "Failed to spawn", rebuild the environment with `rm -rf .venv && uv sync`, and `unset VIRTUAL_ENV` if it points elsewhere.

## Run

```bash
uv run uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000 and sign in. Run from the project folder, since the UI is served from `static/`.

## First sign-in

Users sign in with email and password. Give the first Admin a login from the command line (the password is asked for twice and not shown):

```bash
uv run python -m app.set_password --user-id 1 --email you@example.com
```

Run it again to reset a forgotten Admin password. Everyone else gets a temporary password from an Admin on Admin - Users and chooses their own at first sign-in. Sign-ins last 8 hours; five wrong passwords lock an account for 15 minutes. Behind HTTPS, set `TP_SECURE_COOKIE=1`.

## Test

```bash
uv run pytest
```

Tests use their own temporary database and upload folder.

## Settings

| Variable | Default | Purpose |
| --- | --- | --- |
| `TP_DATABASE_URL` | `sqlite:///tp.db` | Database |
| `TP_UPLOAD_DIR` | `uploads` | Assessment visual files |
| `TP_SECURE_COOKIE` | off | `1` marks the sign-in cookie Secure (HTTPS only) |

## Roles and access

Admin has full access and cannot be changed. Other roles are made on Admin - Roles: None, View or Edit per page, plus the Create plan, Sign plan and All clients (read) actions. A user sees a client's plans when their provider is assigned to the client (Admin - Client assignment) or their role has All clients; editing needs an assignment or plan ownership. Admin - Change history lists who changed what.
