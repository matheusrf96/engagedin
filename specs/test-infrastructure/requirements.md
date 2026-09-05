# Test Infrastructure — Requirements

Feature ID: `TI`

## Context

engagedin currently has all 164 tests in a flat `tests/` directory, all
mock-based (no real database), executed serially, with no Makefile. The
sibling project `~/dev/py/devotion` established three behaviors worth
replicating:

1. **Integration tests against a real PostgreSQL database** — `tests/` is
   split into `tests/unit/` (mocks) and `tests/integration/` (real DB). A
   session-scoped fixture creates a unique database per test session
   (`<name>_test_<uuid8>`) with `CREATE DATABASE` (AUTOCOMMIT + NullPool),
   builds the schema with `Base.metadata.create_all`, and tears everything
   down afterwards. Tests skip gracefully when Postgres is unavailable. A
   per-test cleanup fixture truncates mutable tables so the full suite stays
   isolated. Integration tests run against a dedicated Postgres on **port
   5433** (dev DB stays on 5432) managed by a dedicated Docker Compose file.
2. **A Makefile** exposing common commands (`help`, `format`, `lint`,
   `typecheck`, `test`, `unit-test`, `coverage`, `integration-test-up/down`,
   `integration-test`, `run`) via `uv run`, with `pg_isready` readiness
   loops, Alembic migration application, and `|| exit 1` failure guards.
3. **Parallel test execution with pytest-xdist** — unit tests run with
   `-n auto`; integration tests run with `-n $(INTEGRATION_WORKERS)
   --dist loadscope` (workers capped at 8 via `nproc`). Session-scoped async
   fixtures require session-scoped event loops
   (`asyncio_default_fixture_loop_scope = session`), which also gives each
   xdist worker its own unique test database.

## Requirements

### Test layout

### REQ-TI-001 — Unit/integration split

WHEN the repository is checked out after this feature
THE SYSTEM SHALL have all existing mock-based tests under `tests/unit/`
(`tests/unit/api/` for the current `tests/api/` files)
AND SHALL have new integration tests under `tests/integration/`
WHILE `pytest` collects both trees through `testpaths = ["tests"]`.

### REQ-TI-002 — Unit tests behavior parity

WHEN the relocated unit tests run
THE SYSTEM SHALL keep every existing test passing without behavioral changes
AND SHALL pass ruff, mypy, and the 100% coverage gate from unit tests alone
WHILE only file paths and imports are adjusted.

### Integration tests (real PostgreSQL)

### REQ-TI-003 — Test database service

WHEN `docker compose -f docker-compose.test.yml up -d postgres` runs at the
repository root
THE SYSTEM SHALL start a PostgreSQL 16 container publishing host port `5433`,
with credentials `engagedin`/`engagedin`, database `engagedin_test`, a
`pg_isready` healthcheck, and a named volume
WHILE the existing dev `docker-compose.yml` on port 5432 remains unchanged.

### REQ-TI-004 — Session-scoped integration engine

WHEN an integration test session starts
THE SYSTEM SHALL create a unique database named `engagedin_test_<8-char-hex>`
by connecting to the `postgres` maintenance database with
`isolation_level="AUTOCOMMIT"` and `NullPool`
AND SHALL create the schema with `Base.metadata.create_all`
AND SHALL yield an async engine bound to the unique database
AND on teardown SHALL drop all tables, terminate remaining connections, and
drop the unique database
WHILE each xdist worker process gets its own unique database.

### REQ-TI-005 — Integration session and sessionmaker

WHEN an integration test requests a database session
THE SYSTEM SHALL provide `integration_db_session` (function-scoped
`AsyncSession`, `expire_on_commit=False`) bound to the integration engine
AND SHALL provide `integration_sessionmaker` (session-scoped factory) for
per-request sessions in API tests.

### REQ-TI-006 — Per-test table cleanup

WHEN an integration test finishes
THE SYSTEM SHALL execute `TRUNCATE TABLE posts RESTART IDENTITY CASCADE;`
against the integration database
WHILE the truncation runs automatically (autouse fixture) after every test.

### REQ-TI-007 — Integration HTTP client

WHEN an integration test needs the API over HTTP
THE SYSTEM SHALL provide an `async_client` fixture built on
`httpx.AsyncClient` + `ASGITransport`
AND SHALL override the `get_session` dependency so each request receives a
fresh session from `integration_sessionmaker`
AND SHALL clear dependency overrides after each test.

### REQ-TI-008 — Service-level integration coverage

WHEN the integration suite runs
THE SYSTEM SHALL exercise `PostService` against the real database: create
draft (with `Engine` patched via `@patch`), get by id, list with status and
topic filters, update content (character count recomputed), publish success
(URN + `published_at` persisted), publish failure (`status=failed` + `error`
persisted and durable), and delete
WHILE external calls (LLM, LinkedIn) are mocked at the `Engine` boundary.

### REQ-TI-009 — API-flow integration coverage

WHEN the integration suite runs
THE SYSTEM SHALL exercise the HTTP surface end-to-end against the real
database: `GET /healthz` returns `database: reachable`, `POST /api/v1/drafts`
persists and the record appears in `GET /api/v1/posts`, `PATCH` updates the
stored content, publish returns the URN and a second publish returns 409, and
`DELETE` removes the record (subsequent `GET` returns 404)
WHILE the same `async_client` fixture is used.

### REQ-TI-010 — Graceful skip without database

WHEN integration tests run without PostgreSQL available on the test port
THE SYSTEM SHALL skip the integration tests with a clear message pointing to
`make integration-test-up`
AND `make test` SHALL complete successfully using unit tests alone
WHILE Postgres is not running.

### Makefile

### REQ-TI-011 — Help target

WHEN `make help` (or bare `make`) runs
THE SYSTEM SHALL print the list of available targets with descriptions.

### REQ-TI-012 — Quality targets

WHEN `make format`, `make lint`, or `make typecheck` runs
THE SYSTEM SHALL run `uv run ruff check --fix .`, `uv run ruff check .`, and
`uv run mypy engagedin cli api` respectively
AND each SHALL fail the make invocation when its command fails.

### REQ-TI-013 — Unit test targets

WHEN `make unit-test` or `make coverage` runs
THE SYSTEM SHALL run `uv run pytest tests/unit/ -vv -n auto` and
`uv run pytest tests/unit/ --cov=engagedin --cov=cli --cov=api
--cov-fail-under=100 -n auto` respectively
WHILE neither requires a running PostgreSQL (coverage gate is satisfied by
unit mocks alone, as today).

### REQ-TI-014 — Integration database up target

WHEN `make integration-test-up` runs
THE SYSTEM SHALL start the test Postgres via
`docker compose -f docker-compose.test.yml up -d postgres`
AND SHALL wait for readiness by retrying `pg_isready` up to 10 times (2s
interval)
AND SHALL run `uv run alembic upgrade head` against the test database
AND SHALL fail the target when any step fails.

### REQ-TI-015 — Integration database down target

WHEN `make integration-test-down` runs
THE SYSTEM SHALL run
`docker compose -f docker-compose.test.yml down -v`
removing containers and volumes.

### REQ-TI-016 — Integration test target

WHEN `make integration-test` runs
THE SYSTEM SHALL start the test database (REQ-TI-014), run
`uv run pytest tests/integration/ -v -n $(INTEGRATION_WORKERS) --dist
loadscope`, and stop the database (REQ-TI-015) afterwards
AND SHALL stop the database even when the test run fails
AND `INTEGRATION_WORKERS` SHALL default to the machine core count capped at 8.

### REQ-TI-017 — Run target

WHEN `make run` executes
THE SYSTEM SHALL start the dev Postgres (port 5432) with a readiness wait
loop and run `uv run uvicorn api.main:app --reload` against it.

### Parallel execution

### REQ-TI-018 — pytest-xdist dependency

WHEN the dev dependency group is installed
THE SYSTEM SHALL include `pytest-xdist (>=3.6)`
WHILE `uv sync` resolves it into the lockfile.

### REQ-TI-019 — Session-scoped event loop

WHEN pytest collects async tests
THE SYSTEM SHALL use session-scoped event loops via
`asyncio_default_fixture_loop_scope = "session"` and
`asyncio_default_test_loop_scope = "session"` in the pytest configuration
WHILE session-scoped async fixtures (integration engine, sessionmaker) are
required by the xdist execution model.

### REQ-TI-020 — Parallel CI gates

WHEN CI runs
THE SYSTEM SHALL execute unit tests with coverage as one step (no database
required, `-n auto`)
AND SHALL execute integration tests as a separate step against the Postgres
service container with `--dist loadscope`
AND SHALL keep the Python `3.12` / `3.13` / `3.14` matrix and the 100%
coverage gate
WHILE the Postgres service in CI is reachable on the port the integration
fixtures expect.

## Constraints

### CON-TI-001 — No application-code changes

The feature SHALL NOT modify files under `engagedin/`, `cli/`, or `api/`
except where a fix is strictly required to make integration tests pass.

### CON-TI-002 — Coverage gate preserved

The 100% coverage gate SHALL hold over `engagedin`, `cli`, and `api` from
unit tests alone, matching today's gate.

### CON-TI-003 — Test database port

Integration tests SHALL target host port `5433` by default (overridable via
`POSTGRES_PORT`), never the dev port `5432`.

### CON-TI-004 — Mock conventions

New integration tests SHALL mock external services with `@patch` decorators
(no `with patch(...)` blocks) at the `Engine`/`LinkedInClient` boundary, per
`AGENTS.md`.

### CON-TI-005 — Schema source of truth

Alembic migrations SHALL remain the schema source of truth for
`make integration-test-up`; the per-session unique databases created by
fixtures SHALL be built with `Base.metadata.create_all` (same as devotion).

### CON-TI-006 — Dev Compose untouched

The existing `docker-compose.yml` (dev database, port 5432) SHALL remain
unchanged; the test database gets its own `docker-compose.test.yml`.

### CON-TI-007 — Spec-first

This feature SHALL follow the repo's spec-first workflow; `tasks.md` tracks
implementation order and verification.
