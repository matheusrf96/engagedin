# API Module — Requirements

Feature ID: `AM`

## Context

engagedin is a CLI-only Python application (Click) that generates and publishes
LinkedIn posts using LLMs via LiteLLM. This feature introduces a FastAPI +
PostgreSQL API module so the same generation/publishing capabilities become
available over HTTP with persistent post history, while the existing CLI stays
fully functional. The CLI is isolated into a top-level `cli/` package, the API
lives in a top-level `api/` package, and shared business logic remains in the
`engagedin/` package (`core`, `linkedin`, `llm`, `news`, `rules`).

Decisions locked during planning:

- **Repository layout**: monorepo split — top-level `cli/` + `api/`; shared
  logic stays in the `engagedin/` package.
- **Database**: real PostgreSQL 16 instantiated via Docker, accessed through
  async SQLAlchemy (`asyncpg`) and managed by Alembic migrations.
- **Persistence scope**: the posts/drafts lifecycle only (no rulesets, no
  scheduling queue in this feature).
- **Packaging**: API dependencies ship as the optional extra `api`.
- **Authentication**: none — this is an open-source tool users run locally.

## Requirements

### CLI isolation

### REQ-AM-001 — CLI package relocation

WHEN the repository is checked out after this feature
THE SYSTEM SHALL expose the Click CLI from the top-level `cli` package
(`cli/__init__.py`, `cli/main.py`)
AND SHALL remove the `engagedin/cli/` directory
WHILE `cli/main.py` continues to import shared logic exclusively from
`engagedin.*` (`engagedin.core`, `engagedin.linkedin`, `engagedin.llm`,
`engagedin.news`, `engagedin.rules`).

### REQ-AM-002 — Entry points

WHEN a user runs the installed `engagedin` console script or `python -m cli`
THE SYSTEM SHALL start the CLI
AND `engagedin/__main__.py` SHALL be deleted
AND `cli/__main__.py` SHALL delegate to `cli.main:cli`
WHILE any Python 3.12+ interpreter in the project virtual environment is used.

### REQ-AM-003 — CLI behavior parity

WHEN the CLI is invoked with any existing command (`draft`, `post`,
`headliner`, `auth login`, `auth status`, `rules show`, `config show`) and any
of their options (`--rules`, `--yes`, `--days`, `--topic`)
THE SYSTEM SHALL behave identically to the pre-migration CLI
WHILE command signatures, flags, and outputs are not changed.

### REQ-AM-004 — CLI tests migration

WHEN the test suite runs
THE SYSTEM SHALL import the CLI from `cli.main`
AND SHALL patch `cli.main` attributes (e.g. `cli.main.LinkedInClient`,
`cli.main.Engine`) instead of `engagedin.cli.main`
AND all existing CLI tests SHALL keep passing without behavioral changes
WHILE only import paths and patch targets are edited.

### API application

### REQ-AM-005 — Application bootstrap and health

WHEN the application is started with `uvicorn api.main:app`
THE SYSTEM SHALL expose `GET /healthz` returning
`{"status": "ok", "database": "reachable"}` with HTTP 200 when the database is
reachable
AND SHALL return HTTP 503 with `"database": "unreachable"` when the ping fails
WHILE the application is served under `api.main:app`.

### REQ-AM-006 — API configuration

WHEN the API process starts
THE SYSTEM SHALL read `DATABASE_URL`, `API_HOST`, and `API_PORT` from
environment variables (and the `.env` file) through a dedicated
pydantic-settings model in `api/config.py`
AND SHALL default `DATABASE_URL` to
`postgresql+asyncpg://engagedin:engagedin@localhost:5432/engagedin`
AND SHALL default `API_HOST` to `127.0.0.1` and `API_PORT` to `8000`
WHILE the existing `engagedin.core.config.settings` remains the single source
of shared (LinkedIn, LLM, news, rules) configuration.

### REQ-AM-007 — Async engine lifecycle

WHEN the application starts or shuts down
THE SYSTEM SHALL create an async SQLAlchemy engine and sessionmaker once and
dispose of the engine on shutdown
AND request handlers SHALL obtain `AsyncSession` objects through a
`get_session` FastAPI dependency that closes the session after each request
AND commits SHALL be performed by the service layer
WHILE connection pooling uses `pool_pre_ping` to survive Postgres restarts.

### REQ-AM-008 — Non-blocking execution of shared logic

WHEN an endpoint handler invokes blocking shared logic (LLM generation, news
fetching, LinkedIn HTTP calls, ruleset loading)
THE SYSTEM SHALL execute it off the event loop (via `asyncio.to_thread` or
equivalent)
WHILE handlers remain `async def` and the shared `engagedin` code stays
synchronous.

### Draft generation

### REQ-AM-009 — Standard draft generation

WHEN `POST /api/v1/drafts` receives `{"topic": "<text>"}`
THE SYSTEM SHALL generate a draft through `Engine.generate_draft`, persist a
`PostRecord` with `status=draft` and `source=standard`, and return HTTP 201
with the persisted record
AND SHALL reject an empty or missing `topic` with HTTP 422
WHILE the LLM configuration is valid.

### REQ-AM-010 — Headliner draft generation

WHEN `POST /api/v1/drafts` receives
`{"topic": "<text>", "source": "headliner", "days": <1..7>}`
THE SYSTEM SHALL generate the draft through
`Engine.generate_headliner_draft(days=days)` and persist it with
`source=headliner`
AND `days` SHALL default to `1` and SHALL be restricted to `1..7`
WHILE news articles exist for the requested topic and window.

### REQ-AM-011 — Generation error mapping

WHEN draft generation raises `LLMConfigError`, `NewsError`, or an unexpected
exception
THE SYSTEM SHALL return HTTP 400, HTTP 502, and HTTP 500 respectively with a
JSON `{"detail": "<message>"}`
AND SHALL NOT persist a record when generation fails before content exists
WHILE the response body always carries a human-readable detail message.

### Posts lifecycle

### REQ-AM-012 — List posts

WHEN `GET /api/v1/posts` is called with optional `status`, `topic`, `limit`
(default `20`, maximum `100`), and `offset` (default `0`) query parameters
THE SYSTEM SHALL return HTTP 200 with `{"items": [...], "total": <int>}`
ordered newest-first (`created_at DESC, id DESC`)
AND SHALL ignore unknown statuses with HTTP 422
WHILE the database is reachable.

### REQ-AM-013 — Get post

WHEN `GET /api/v1/posts/{id}` is called
THE SYSTEM SHALL return HTTP 200 with the record, or HTTP 404 with a JSON
detail when the record does not exist
WHILE the identifier is a positive integer.

### REQ-AM-014 — Update draft content

WHEN `PATCH /api/v1/posts/{id}` receives `{"content": "<text>"}` (1..3000
characters)
THE SYSTEM SHALL update `content`, recompute `character_count`, and return
HTTP 200 with the updated record
AND SHALL return HTTP 409 when `status` is `published`
AND SHALL return HTTP 404 when the record does not exist
WHILE `updated_at` is refreshed.

### REQ-AM-015 — Publish a draft

WHEN `POST /api/v1/posts/{id}/publish` is called for a record with
`status=draft` or `status=failed`
THE SYSTEM SHALL publish the stored content through `Engine.publish_draft`,
store `linkedin_post_urn`, set `status=published` and `published_at` to now,
and return HTTP 200 with the updated record
AND SHALL return HTTP 409 when `status` is `published`
AND SHALL return HTTP 404 when the record does not exist
AND WHEN publishing raises `LinkedInError` THE SYSTEM SHALL set
`status=failed` with the error message in `error`, keep the stored content
untouched, commit the failure, and return HTTP 502.

### REQ-AM-016 — Delete post

WHEN `DELETE /api/v1/posts/{id}` is called
THE SYSTEM SHALL delete the record and return HTTP 204
AND SHALL return HTTP 404 when the record does not exist
WHILE any status is accepted for deletion.

### REQ-AM-017 — LinkedIn auth status

WHEN `GET /api/v1/auth/status` is called
THE SYSTEM SHALL return HTTP 200 with `{"name": ..., "sub": ...}` from the
LinkedIn userinfo endpoint
AND SHALL return HTTP 502 with a JSON detail when the LinkedIn call fails
WHILE no tokens are written and no publish action is performed.

### Data model and migrations

### REQ-AM-018 — PostRecord table

THE SYSTEM SHALL persist posts in a `posts` table with columns `id`
(autoincrement integer primary key), `topic` (`varchar(500)`), `source`
(`standard` | `headliner`), `status` (`draft` | `published` | `failed`),
`content` (`text`), `character_count` (integer), `linkedin_post_urn`
(`varchar(120)`, nullable, unique), `error` (`text`, nullable), `created_at`,
`updated_at`, and `published_at` (nullable timestamp)
AND SHALL store `source` and `status` as string-backed enums (native enum
disabled) validated at the application boundary
AND SHALL index `status` and `created_at`
WHILE `created_at` and `updated_at` default to the database clock and
`updated_at` refreshes on update.

### REQ-AM-019 — Alembic migrations

WHEN `uv run alembic upgrade head` runs against a fresh database
THE SYSTEM SHALL create the `posts` table with all constraints and indexes
(revision `0001`)
AND `alembic revision --autogenerate` SHALL produce no diff after the upgrade
WHILE `alembic.ini` and `migrations/` live at the repository root and the
Alembic environment uses the async engine configured from `DATABASE_URL`.

### Infrastructure

### REQ-AM-020 — Docker Compose Postgres

WHEN `docker compose up -d` runs at the repository root
THE SYSTEM SHALL start a PostgreSQL 16 service with a healthcheck, a named
volume for data, port `5432` published to the host, and default credentials
`engagedin`/`engagedin` with database `engagedin`
AND the default `DATABASE_URL` SHALL connect to this service
WHILE the credentials are overridable through compose environment variables.

### REQ-AM-021 — Environment example

WHEN `.env.example` is inspected
THE SYSTEM SHALL document `DATABASE_URL`, `API_HOST`, and `API_PORT` with
sensible defaults
WHILE the existing LinkedIn, LLM, news, and rules variables remain documented
unchanged.

### Packaging

### REQ-AM-022 — Optional `api` extra

WHEN `uv sync --extra api` (or `pip install engagedin[api]`) runs
THE SYSTEM SHALL install `fastapi`, `uvicorn[standard]`,
`sqlalchemy[asyncio]`, `asyncpg`, and `alembic`
AND WHEN `uv sync` runs without extras the CLI SHALL install and run without
any API dependency
WHILE the `dev` dependency group additionally gains a pytest async plugin
needed by API tests.

### REQ-AM-023 — Distribution contents

WHEN `uv build` runs
THE SYSTEM SHALL produce a wheel containing the `engagedin`, `cli`, and `api`
packages
AND the console script `engagedin` SHALL point to `cli.main:cli`
WHILE the PyPI distribution name remains `engagedin`.

### CI

### REQ-AM-024 — CI gates over new packages

WHEN the CI workflow runs on a push to `main` or a pull request
THE SYSTEM SHALL install dependencies with `uv sync --frozen --extra api`
AND SHALL run `ruff check .` over the whole repository
AND SHALL run `mypy` over `engagedin`, `cli`, and `api`
AND SHALL run pytest with coverage over `engagedin`, `cli`, and `api`
enforcing the 100% coverage gate
WHILE the Python `3.12` / `3.13` / `3.14` matrix is preserved.

### REQ-AM-025 — CI Postgres service

WHEN the CI test job runs
THE SYSTEM SHALL start a PostgreSQL 16 service container with a healthcheck,
export a `DATABASE_URL` pointing at a dedicated test database
(`engagedin_test`), and apply migrations before pytest
WHILE tests that do not need a database remain unaffected.

### Documentation

### REQ-AM-026 — README API section

WHEN the README is read
THE SYSTEM SHALL document how to start Postgres with Docker Compose, apply
migrations, and run the API with uvicorn
AND SHALL show example requests against the endpoints
AND SHALL reflect the new repository layout with the top-level `cli/` and
`api/` packages
WHILE the CLI installation and usage sections stay accurate.

### REQ-AM-027 — Changelog

WHEN the CHANGELOG is updated
THE SYSTEM SHALL record the API module and infrastructure as added
AND SHALL record the CLI relocation to the top-level `cli` package as changed
AND SHALL record the removal of `python -m engagedin` as a breaking change
WHILE following the existing CHANGELOG format.

## Constraints

### CON-AM-001 — Shared logic placement

Business logic SHALL remain in the `engagedin/` package. `cli/` SHALL contain
only command definitions and presentation; `api/` SHALL contain only transport,
persistence, and orchestration concerns. Neither application SHALL duplicate
business logic implemented in `engagedin/core`, `engagedin/linkedin`,
`engagedin/llm`, `engagedin/news`, or `engagedin/rules`.

### CON-AM-002 — No API authentication

API endpoints SHALL NOT require credentials. The API is intended to run on the
user's machine (bound to `127.0.0.1` by default).

### CON-AM-003 — Postgres-only persistence

The API storage layer SHALL target PostgreSQL through `asyncpg`. SQLite SHALL
NOT be used for API storage.

### CON-AM-004 — Versioned API prefix

All domain endpoints SHALL be mounted under the `/api/v1` prefix; only the
health endpoint lives at the root path level.

### CON-AM-005 — Type and style gates

All new code SHALL pass the existing ruff configuration (line length 100; rule
sets E, F, I, N, W, UP) and the existing mypy configuration
(`disallow_untyped_defs`).

### CON-AM-006 — Coverage gate

The 100% coverage requirement SHALL extend to the `cli` and `api` packages in
addition to `engagedin`.

### CON-AM-007 — Distribution name

The PyPI distribution SHALL remain `engagedin`. No new distributions are
introduced by this feature.

### CON-AM-008 — Alembic location

`alembic.ini` and the `migrations/` directory SHALL live at the repository
root, decoupled from the `api/` application package.

### CON-AM-009 — Generic top-level package names accepted

The top-level package names `cli` and `api` are intentionally generic. Name
shadowing is only possible when this distribution is installed into an
environment that already contains another distribution exporting a top-level
`cli` or `api` package. This risk is accepted for a locally-run, open-source
tool.
