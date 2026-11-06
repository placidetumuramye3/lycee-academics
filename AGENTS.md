# Repository Guidelines for Coding Agents

## Project shape

This project is a Flask application with a React/Vite frontend layer that is being introduced incrementally. The root entrypoint is [run.py](run.py), which loads the backend application from the `backend-app/` package. The repo is organized around the existing Flask app, not a static frontend-only build.

Key references:
- [README.md](README.md) for setup and workspace expectations
- [docs/react-migration-plan.md](docs/react-migration-plan.md) for the frontend migration boundaries
- [docs/meetings-api.md](docs/meetings-api.md) for API contract expectations
- [docs/meeting-schema.md](docs/meeting-schema.md) for database/schema migration behavior
- [MEETING_PANEL_IMPLEMENTATION.md](MEETING_PANEL_IMPLEMENTATION.md) for workflow-specific conventions

When changing application logic, prefer the existing Flask patterns and keep the server-side authorization model intact. The app uses role checks and school-scoped access control in the backend; do not move critical permissions into React-only code.

## Local setup

Use a virtual environment and install dependencies before running the app locally:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
npm.cmd install --prefix react-frontend
npm.cmd run build --prefix react-frontend
python run.py
```

If the frontend package is not present or not yet built, fall back to the existing backend-only routes and keep the migration plan in [docs/react-migration-plan.md](docs/react-migration-plan.md) in mind.

## Working conventions

- Keep route handlers focused on request validation and response shaping; move reusable business rules into services or utilities.
- Preserve the existing role-based access patterns and school/guardian scope checks.
- Use SQLAlchemy models and Flask migration patterns rather than editing a live database directly.
- Keep database changes idempotent and migration-friendly; if a schema change is necessary, add or update migration files instead of manual DB edits.
- Prefer small, focused tests under `backend-app/tests/` when changing routes, permissions, or data boundaries.
- Follow the existing Python conventions: four-space indentation, `snake_case` for functions/variables, and `PascalCase` for classes.

## Testing

Run the test suite with:

```powershell
python -m pytest
```

If you change frontend behavior, validate the build with:

```powershell
npm.cmd run build --prefix react-frontend
```

## Security and config

- Keep secrets and local environment values in `backend-app/.env`; use `backend-app/.env.example` as the documented template.
- Do not commit credentials, local sqlite files, or virtual environments.
- Treat the bootstrap admin credentials in the documentation as local development values only and rotate or replace them immediately in real deployments.

## Useful guardrails for agents

- Do not rewrite architecture boundaries just to make a small fix; follow the existing Flask + server-side auth model.
- Before making schema or migration changes, inspect [docs/meeting-schema.md](docs/meeting-schema.md) and the migration history to maintain compatibility.
- For meeting-related work, consult [docs/meetings-api.md](docs/meetings-api.md) and [docs/meeting-security-and-deployment.md](docs/meeting-security-and-deployment.md) before changing endpoints or security assumptions.
- Keep changes aligned with the migration approach in [docs/react-migration-plan.md](docs/react-migration-plan.md): incremental front-end adoption without breaking the backend flows.

## Commit and PR expectations

Use concise, imperative commit subjects such as "Fix teacher class assignment scope". Pull requests should explain the user-visible change, call out any migration/configuration impact, list verification performed, and include screenshots for UI changes when relevant.
