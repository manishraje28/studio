# Studio API

FastAPI service for projects, briefs, the agent job queue and the live event stream.

## Run locally

```bash
docker compose up -d db          # from the repo root: Postgres on localhost:54322
cp .env.example .env
uv run python -m app.migrate     # create tables (adds RLS policies on Supabase)
uv run uvicorn app.main:app --reload --port 8000
uv run python -m app.worker      # in a second terminal
```

API docs: http://localhost:8000/docs

## Test

```bash
uv run pytest
uv run ruff check .
```

Tests use the `studio_test` database created by `db/init/01-test-db.sql`.

## How it fits together

- `POST /projects` stores the brief and enqueues a `project.kickoff` job.
- `app/queue.py` is a Postgres job queue (`FOR UPDATE SKIP LOCKED`), with retries and exponential backoff.
- `app/worker.py` claims jobs and runs the handler registered for each job kind.
- Agents write `agent_events`; clients read them at `GET /projects/{id}/events` or live over SSE at `/events/stream`.
- Auth: Supabase access tokens, verified through the project's JWKS (`SUPABASE_URL`) or the legacy HS256 secret.
- Free-tier guardrail: `DAILY_PROJECT_LIMIT` new projects per user per day.
