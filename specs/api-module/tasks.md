# API Module — Tasks

> Implementation order: CLI isolation → packaging → infrastructure → data
> model/migrations → service → routers → tests → CI → docs. The checklist
> below is grouped by requirement ID; phases reference the REQ sections.

## Spec

- [x] Write `specs/api-module/requirements.md`
- [x] Write `specs/api-module/design.md`
- [x] Link the spec from `specs/README.md`

## REQ-AM-001 — CLI package relocation

- [x] `git mv engagedin/cli cli` (top-level package with `__init__.py`)
- [x] Confirm `cli/main.py` still imports shared logic from `engagedin.*`
- [x] Delete the now-empty `engagedin/cli/` directory
- [x] Confirm `engagedin/core`, `engagedin/linkedin`, `engagedin/llm`,
      `engagedin/news`, `engagedin/rules` are untouched

## REQ-AM-002 — Entry points

- [x] Add `cli/__main__.py` delegating to `cli.main:cli`
- [x] Delete `engagedin/__main__.py`
- [x] Update `[project.scripts]` to `engagedin = "cli.main:cli"`
- [x] Verify `uv run engagedin --help` and `uv run python -m cli --help`

## REQ-AM-003 — CLI behavior parity

- [x] Verify `draft`, `post`, `headliner`, `auth login`, `auth status`,
      `rules show`, `config show` subcommands and options are unchanged
- [x] Diff CLI output of `--help` against pre-migration (no flag changes)

## REQ-AM-004 — CLI tests migration

- [x] Update `tests/test_cli.py` imports to `from cli.main import cli`
- [x] Update patch targets `engagedin.cli.main.*` → `cli.main.*`
- [x] Update `tests/test_main.py` imports/patch targets likewise
- [x] Run the CLI test subset and confirm all pass unchanged

## REQ-AM-005 — Application bootstrap and health

- [ ] Create `api/main.py` with `create_app()` factory, lifespan (engine
      disposal on shutdown), and router wiring
- [ ] Create `api/routers/health.py` with `GET /healthz` (DB ping;
      200/`reachable` vs 503/`unreachable`)

## REQ-AM-006 — API configuration

- [ ] Create `api/config.py` with `ApiSettings` (`DATABASE_URL`, `API_HOST`,
      `API_PORT`) and defaults per design §4
- [ ] Confirm `engagedin.core.config.settings` remains unchanged

## REQ-AM-007 — Async engine lifecycle

- [ ] Create `api/database.py`: `Base`, `create_async_engine(pool_pre_ping)`,
      `async_sessionmaker`, `get_session` dependency
- [ ] Wire engine disposal into the app lifespan

## REQ-AM-008 — Non-blocking execution of shared logic

- [ ] Wrap `Engine.generate_draft`, `Engine.generate_headliner_draft`,
      `Engine.publish_draft`, and `LinkedInClient.get_user_info` calls in
      `asyncio.to_thread`
- [ ] Keep all handler functions `async def`

## REQ-AM-009 — Standard draft generation

- [ ] Create `api/services/posts.py` with `PostService.create_draft` (persist
      `status=draft`, `source=standard`, commit, return record)
- [ ] Create `api/routers/generation.py` with `POST /api/v1/drafts` → 201

## REQ-AM-010 — Headliner draft generation

- [ ] Add `source="headliner"` path calling
      `Engine.generate_headliner_draft(days=…)` (days default 1, range 1–7)

## REQ-AM-011 — Generation error mapping

- [ ] Map `LLMConfigError` → 400, `NewsError` → 502, unexpected → 500, each
      with `{"detail": ...}`
- [ ] Confirm no record is persisted when generation fails

## REQ-AM-012 — List posts

- [ ] Implement `PostService.list` (filters `status`/`topic`, `limit` max 100
      default 20, `offset`, newest-first) and `GET /api/v1/posts` with
      `PostListResponse` (`items`, `total`)

## REQ-AM-013 — Get post

- [ ] Implement `PostService.get` (raises `NotFoundError`) and
      `GET /api/v1/posts/{id}` (200 / 404)

## REQ-AM-014 — Update draft content

- [ ] Implement `PostService.update_content` (recompute `character_count`,
      409 when `published`) and `PATCH /api/v1/posts/{id}`
- [ ] Create `api/schemas.py` (`DraftCreateRequest`, `PostUpdateRequest`,
      `PostOut`, `PostListResponse`, `AuthStatusResponse`)

## REQ-AM-015 — Publish a draft

- [ ] Implement `PostService.publish` (allowed for `draft`/`failed`; 409 when
      `published`; rebuilds `GeneratedDraft` from stored content)
- [ ] Success path: store `linkedin_post_urn`, `status=published`,
      `published_at=now`, commit → 200
- [ ] Failure path: catch `LinkedInError` → `status=failed`, `error` message,
      commit → 502
- [ ] Create `api/routers/posts.py` with `POST /api/v1/posts/{id}/publish`

## REQ-AM-016 — Delete post

- [ ] Implement `PostService.delete` and `DELETE /api/v1/posts/{id}`
      (204 / 404, any status)

## REQ-AM-017 — LinkedIn auth status

- [ ] Create `api/routers/auth.py` with `GET /api/v1/auth/status`
      (200 `AuthStatusResponse` / 502 on `LinkedInError`)

## REQ-AM-018 — PostRecord table

- [ ] Create `api/models.py` with `PostStatus`, `DraftSource`, `PostRecord`
      (columns, string-backed enums, unique URN, indexes on `status` and
      `created_at`, server-default timestamps)

## REQ-AM-019 — Alembic migrations

- [ ] Add root `alembic.ini` (`script_location = migrations`, no hardcoded URL)
- [ ] Initialize `migrations/` with async `env.py` resolving `DATABASE_URL`
      and `target_metadata = api.models.Base.metadata`
- [ ] Generate revision `0001_posts`
- [ ] Verify `uv run alembic upgrade head` on a fresh database
- [ ] Verify `alembic revision --autogenerate` yields an empty diff afterwards

## REQ-AM-020 — Docker Compose Postgres

- [ ] Create `docker-compose.yml` with `postgres:16-alpine`, healthcheck,
      named volume, port 5432, default `engagedin` credentials
- [ ] Verify `docker compose up -d` then `pg_isready` passes and the default
      `DATABASE_URL` connects

## REQ-AM-021 — Environment example

- [ ] Add `DATABASE_URL`, `API_HOST`, `API_PORT` to `.env.example` with
      defaults; keep existing entries unchanged

## REQ-AM-022 — Optional `api` extra

- [ ] Add `[project.optional-dependencies] api` (fastapi, uvicorn[standard],
      sqlalchemy[asyncio], asyncpg, alembic)
- [ ] Add `pytest-asyncio` to the `dev` group and set `asyncio_mode = "auto"`
- [ ] Verify `uv sync` (no extras) keeps the CLI runnable; `uv sync --extra
      api` installs the API stack

## REQ-AM-023 — Distribution contents

- [ ] Update `[tool.setuptools.packages.find]` to
      `include = ["engagedin*", "cli*", "api*"]`
- [ ] Verify `uv build` produces a wheel containing all three packages
- [ ] Verify the console script resolves to `cli.main:cli`

## REQ-AM-024 — CI gates over new packages

- [ ] Update `.github/workflows/ci.yml`: `uv sync --frozen --extra api`,
      `uv run mypy engagedin cli api`, coverage
      `--cov=engagedin --cov=cli --cov=api --cov-fail-under=100`
- [ ] Confirm the `3.12`/`3.13`/`3.14` matrix is preserved

## REQ-AM-025 — CI Postgres service

- [ ] Add the `postgres:16-alpine` service (`engagedin_test` database,
      healthcheck) and export the test `DATABASE_URL`
- [ ] Add the `uv run alembic upgrade head` step before pytest

## REQ-AM-026 — README API section

- [ ] Add the repository-layout section (`cli/`, `api/`, `engagedin/`)
- [ ] Add the API quickstart (compose, sync --extra api, alembic, uvicorn)
      with curl examples for `/healthz`, draft generation, publish
- [ ] Note `engagedin[api]` for API installs; keep CLI sections accurate

## REQ-AM-027 — Changelog

- [ ] Record Added (API module, docker-compose, Alembic), Changed (CLI
      relocated; console script `cli.main:cli`), and the breaking
      `python -m engagedin` → `python -m cli` removal

## Verification

- [ ] `uv run ruff check .` passes
- [ ] `uv run mypy engagedin cli api` passes
- [ ] `uv run pytest --cov=engagedin --cov=cli --cov=api --cov-fail-under=100
      -q` passes
- [ ] `uv run engagedin --help` and `uv run python -m cli --help` render
- [ ] `docker compose up -d` + `uv run alembic upgrade head` + smoke
      `GET /healthz` → 200
- [ ] `uv build` wheel contains `engagedin`, `cli`, `api`
- [ ] CI passes on a pull request against `main` for all three Python versions
