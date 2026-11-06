# Copilot instructions for this repository

## Project shape
This repository is a Flask-based school management system with a backend application under `backend-app/` and a root entry point at `run.py`. The backend remains the source of truth for authentication, authorization, database access, and role-based school scoping; React is introduced incrementally and should not bypass server-side permission checks.

Key repo references:
- `README.md` for local setup and deployment expectations
- `AGENTS.md` for repo-specific workflow expectations and guardrails
- `docs/react-migration-plan.md` for the staged frontend migration boundaries
- `docs/meetings-api.md` and `docs/meeting-schema.md` for meeting-related API and DB expectations
- `MEETING_PANEL_IMPLEMENTATION.md` for the meeting panel workflow and constraints

## Local setup and runtime
Use a virtual environment before installing dependencies:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run.py
```

For local SQLite-based development on Windows, the repo also includes `run-local.cmd`, which preserves the local SQLite database for that process without replacing `.env` or the configured PostgreSQL connection. If a PostgreSQL deployment is needed, configure `DATABASE_URL` in `.env` and keep the URL private.

If the React frontend package exists, build it before starting the Flask app:

```powershell
npm.cmd install --prefix react-frontend
npm.cmd run build --prefix react-frontend
python run.py
```

If the `react-frontend` directory is not present, fall back to the backend-only routes and keep the staged migration plan in `docs/react-migration-plan.md` in mind.

## Build, test, and validation commands
The repository does not appear to define a dedicated lint step or a project-wide front-end test suite. Use the commands below for the repo’s actual validation flow.

### Python backend tests
Run the full backend suite:

```powershell
python -m pytest
```

Run a single test module or file:

```powershell
python -m pytest backend-app/tests/test_attendance.py -q
python -m pytest backend-app/tests/test_meetings.py -q
```

### Frontend build (when React code is present)
```powershell
npm.cmd run build --prefix react-frontend
```

## Architecture and module boundaries
- `backend-app/app/models/`: SQLAlchemy data models for schools, users, attendance, academies, meetings, notifications, and school workflows
- `backend-app/app/routes/`: HTTP/UI route handlers; keep request validation and response shaping here
- `backend-app/app/services/`: business-logic seams for workflows such as RFID, attendance, notifications, and other reusable logic
- `backend-app/app/templates/`: Flask/Jinja templates for the non-React screens
- `backend-app/app/static/`: static assets used by the Flask app
- `backend-app/tests/`: pytest coverage for route and permission behavior
- `backend-app/migrations/versions/`: migration scripts used to evolve the database schema without manual DB editing

The app initializes through `backend-app/app/__init__.py` and upgrades legacy SQLite schema variants on startup when needed; preserve that migration-first pattern when changing the schema.

## Project conventions to follow
- Keep route handlers thin and focused on request validation, auth checks, and response shaping. Move reusable workflow logic into services/utilities.
- Preserve the existing role-based access model and school/guardian scope checks; do not move critical permissions into React-only code.
- Use SQLAlchemy models and migration-friendly patterns instead of editing a live database directly.
- If a schema change is needed, add or update migration files rather than hand-editing tables in production or local dev databases.
- Prefer targeted testing around route behavior, permissions, and data boundaries; the repo has focused pytest modules under `backend-app/tests/`.
- Follow Python conventions already used in the codebase: four-space indentation, `snake_case` for functions and variables, and `PascalCase` for classes.
- For meeting-related work, consult the meeting API and schema docs before changing endpoints or security assumptions.

## Security and configuration notes
- Keep secrets and local environment values in `backend-app/.env`; use `backend-app/.env.example` as the template.
- Do not commit credentials, local SQLite databases, or virtual environments.
- Treat bootstrap admin credentials in the docs as development-only values and rotate or replace them immediately in deployments.
- The app uses school-scoped access control and role checks in the backend; ensure changes respect those boundaries.

## Meeting and migration guardrails
The repository includes specific guidance for meeting workflows and database compatibility:
- Follow `docs/meeting-schema.md` before making schema changes that affect meeting records.
- Follow `docs/meetings-api.md` before changing meeting endpoints or payload contracts.
- Keep the migration approach in `docs/react-migration-plan.md` in mind: add React screens incrementally without breaking the backend flows.
