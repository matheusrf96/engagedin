# Test Infrastructure — Tasks

> Implementation order: test restructure → integration fixtures & tests →
> docker-compose.test.yml → Makefile → pytest-xdist → CI → verification.

## Spec

- [x] Write `specs/test-infrastructure/requirements.md`
- [x] Write `specs/test-infrastructure/design.md`
- [x] Link the spec from `specs/README.md`

## REQ-TI-001 — Unit/integration split

- [x] `git mv tests/test_*.py tests/unit/` (add `tests/unit/__init__.py`)
- [x] `git mv tests/api tests/unit/api`
- [x] Confirm pytest collects both trees (`testpaths = ["tests"]`)

## REQ-TI-002 — Unit tests behavior parity

- [x] Run `uv run pytest tests/unit/ -q` — all previously passing tests pass
- [x] Run `uv run pytest tests/unit/ --cov=engagedin --cov=cli --cov=api
      --cov-fail-under=100 -q` — gate holds from unit tests alone

## REQ-TI-003 — Test database service

- [x] Create `docker-compose.test.yml` (postgres:16-alpine, port 5433,
      `engagedin_test`, healthcheck, named volume)
- [x] Confirm dev `docker-compose.yml` untouched

## REQ-TI-004 — Session-scoped integration engine

- [x] Add `_get_test_db_url()` helper (`POSTGRES_PORT` default 5433) to
      `tests/conftest.py`
- [x] Add session-scoped `integration_db_engine` fixture: unique
      `engagedin_test_<hex>` DB via maintenance connection
      (AUTOCOMMIT + NullPool), `Base.metadata.create_all`, teardown
      (drop_all → terminate connections → DROP DATABASE → dispose)
- [x] Confirm `pytest.skip` path on `OSError`

## REQ-TI-005 — Integration session and sessionmaker

- [x] Add `integration_db_session` fixture (function-scoped,
      `expire_on_commit=False`)
- [x] Add session-scoped `integration_sessionmaker` fixture

## REQ-TI-006 — Per-test table cleanup

- [x] Create `tests/integration/conftest.py` with autouse
      `cleanup_integration_tables` (rollback → `TRUNCATE posts RESTART
      IDENTITY CASCADE` → commit)

## REQ-TI-007 — Integration HTTP client

- [x] Add `async_client` fixture overriding `get_session` with per-request
      sessions from `integration_sessionmaker`; clear overrides afterwards

## REQ-TI-008 — Service-level integration coverage

- [x] Write `tests/integration/test_service_db.py`: create draft
      (patched Engine), headliner source, get/round-trip + 404, list filters,
      update content (count recomputed) + published conflict, publish success
      (URN + `published_at`, durable), publish failure (`status=failed` +
      `error` durable), retry after failure, delete + re-delete 404
- [x] Mock only at the `Engine` boundary with `@patch` decorators

## REQ-TI-009 — API-flow integration coverage

- [x] Write `tests/integration/test_api_flow.py`: healthz reachable, full
      post lifecycle (201 → list → PATCH → publish 200 → 409 → DELETE 204 →
      GET 404), publish failure (502 + failed record via GET), pagination and
      filters

## REQ-TI-010 — Graceful skip without database

- [x] Verify `make test`-style run (`uv run pytest tests/`) completes with
      integration tests skipped when Postgres is stopped

## REQ-TI-011 — Help target

- [x] Create `Makefile` with `help` target listing all commands

## REQ-TI-012 — Quality targets

- [x] Add `format` (`ruff check --fix .`), `lint` (`ruff check .`),
      `typecheck` (`mypy engagedin cli api`) with failure guards

## REQ-TI-013 — Unit test targets

- [x] Add `unit-test` (`pytest tests/unit/ -vv -n auto`)
- [x] Add `coverage` (`pytest tests/unit/ --cov=engagedin --cov=cli --cov=api
      --cov-fail-under=100 -n auto`)
- [x] Add `test` (full suite, serial, `--tb=short`)

## REQ-TI-014 — Integration database up target

- [x] Add `integration-test-up`: compose up → `pg_isready` retry loop (10×2s)
      → `alembic upgrade head` against `…:5433/engagedin_test`

## REQ-TI-015 — Integration database down target

- [x] Add `integration-test-down` (`docker compose -f
      docker-compose.test.yml down -v`)

## REQ-TI-016 — Integration test target

- [x] Add `_NPROC` / `INTEGRATION_WORKERS` (capped at 8) variables
- [x] Add `integration-test` target: up → `pytest tests/integration/ -v -n
      $(INTEGRATION_WORKERS) --dist loadscope` → down; down also on failure

## REQ-TI-017 — Run target

- [x] Add `run`: dev compose up + readiness loop +
      `uvicorn api.main:app --reload`

## REQ-TI-018 — pytest-xdist dependency

- [x] Add `pytest-xdist (>=3.6)` to the `dev` dependency group
- [x] `uv lock` / `uv sync` and confirm resolution

## REQ-TI-019 — Session-scoped event loop

- [x] Add `asyncio_default_fixture_loop_scope = "session"` and
      `asyncio_default_test_loop_scope = "session"` to
      `[tool.pytest.ini_options]`
- [x] Confirm session-scoped async fixtures work under `-n auto`

## REQ-TI-020 — Parallel CI gates

- [x] Update CI: unit step (`tests/unit/` with coverage gate, `-n auto`, no
      DB dependency) and integration step (`tests/integration/ -n 4 --dist
      loadscope`)
- [x] Point the Postgres service at host port `5433` with database
      `engagedin_test`; update `DATABASE_URL` env accordingly
- [x] Confirm Python matrix and 100% coverage gate preserved

## Verification

- [x] `make format && make lint && make typecheck` pass
- [x] `make unit-test` passes (parallel, no DB running)
- [x] `make integration-test` — integration tests skip gracefully without DB
- [x] `make coverage` passes with 100% gate (no DB running)
- [x] `uv run pytest tests/` with Docker stopped: integration skipped, exit 0
- [ ] CI passes on a pull request against `main` for all three Python versions
      (pending PR)
