# Test Infrastructure — Design

## 1. Target test layout

```
tests/
├── conftest.py                 # unit fixtures (existing) + integration fixtures (new)
├── unit/                       # ← existing tests moved here (git mv, history preserved)
│   ├── __init__.py
│   ├── test_cli.py
│   ├── test_main.py
│   ├── test_engine.py
│   ├── test_env.py
│   ├── test_linkedin.py
│   ├── test_llm.py
│   ├── test_models.py
│   ├── test_news.py
│   ├── test_rules.py
│   ├── test_schedule.py
│   └── api/
│       ├── __init__.py
│       ├── test_health.py
│       ├── test_generation.py
│       ├── test_posts.py
│       ├── test_auth.py
│       ├── test_service.py
│       └── test_infra.py
└── integration/
    ├── __init__.py
    ├── conftest.py             # per-test truncate cleanup + async_client
    ├── test_service_db.py      # PostService vs real Postgres
    └── test_api_flow.py        # HTTP flow vs real Postgres
```

The move is mechanical (`git mv tests/*.py tests/unit/`,
`git mv tests/api tests/unit/api`) — no test bodies change (REQ-TI-002).
Fixture resolution is unaffected: pytest merges the root `tests/conftest.py`
with directory-level conftests.

## 2. Test database lifecycle

Sequence for one test session (one xdist worker):

1. First integration test requests `integration_db_engine`.
2. Fixture computes `test_db_name = engagedin_test_<uuid4().hex[:8]>`.
3. Connects to the **maintenance database** `postgres`
   (`postgresql+asyncpg://engagedin:engagedin@localhost:<port>/postgres`) with
   `isolation_level="AUTOCOMMIT"`, `poolclass=NullPool`; runs
   `CREATE DATABASE engagedin_test_<hex> WITH ENCODING 'utf8';`.
   On `OSError` → `pytest.skip(...)` with instructions (REQ-TI-010).
4. Connects to the new database, runs `Base.metadata.create_all`.
5. Yields the engine for the whole session.
6. Teardown: `drop_all`, terminate foreign connections
   (`pg_terminate_backend`), `DROP DATABASE IF EXISTS`, dispose engines.

Because the fixture is session-scoped and every xdist worker process has its
own session scope, **each worker gets an isolated database** — no cross-worker
contention on tables or sequences.

`_get_test_db_url()` helper:

```python
def _get_test_db_url() -> str:
    postgres_port = os.getenv("POSTGRES_PORT", "5433")
    return (
        f"postgresql+asyncpg://engagedin:engagedin@localhost:"
        f"{postgres_port}/engagedin_test"
    )
```

`DATABASE_URL` is intentionally **not** used here so CI/local overrides of the
dev URL cannot silently redirect integration tests.

## 3. `docker-compose.test.yml` (new, repository root)

```yaml
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: engagedin
      POSTGRES_PASSWORD: engagedin
      POSTGRES_DB: engagedin_test
    ports:
      - "5433:5432"
    volumes:
      - engagedin_pgdata_test:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U engagedin -d engagedin_test"]
      interval: 5s
      timeout: 5s
      retries: 10

volumes:
  engagedin_pgdata_test:
```

Dev `docker-compose.yml` (port 5432, db `engagedin`) is untouched (CON-TI-006).

## 4. Fixtures

### Root `tests/conftest.py` — additions

Existing unit fixtures (`mock_session`, `app`, `client`) stay as-is. Appended
integration section (mirrors devotion's structure):

```python
def _get_test_db_url() -> str: ...          # §2

@pytest_asyncio.fixture(scope="session")
async def integration_db_engine():
    # unique DB per session; create_all; yield; teardown (§2)

@pytest_asyncio.fixture
async def integration_db_session(integration_db_engine) -> AsyncIterator[AsyncSession]:
    async with AsyncSession(integration_db_engine, expire_on_commit=False) as session:
        yield session

@pytest_asyncio.fixture(scope="session")
async def integration_sessionmaker(
    integration_db_engine,
) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(bind=integration_db_engine, expire_on_commit=False)
```

### `tests/integration/conftest.py` (new)

```python
_REFERENCE_TABLES: set[str] = set()   # engagedin has no seed/reference tables

@pytest_asyncio.fixture(autouse=True)
async def cleanup_integration_tables(integration_db_session):
    yield
    await integration_db_session.rollback()
    tables = [t.name for t in Base.metadata.sorted_tables
              if t.name not in _REFERENCE_TABLES]
    if tables:
        await integration_db_session.execute(
            text(f"TRUNCATE TABLE {', '.join(tables)} RESTART IDENTITY CASCADE;")
        )
    await integration_db_session.commit()

@pytest_asyncio.fixture
async def async_client(integration_sessionmaker) -> AsyncIterator[AsyncClient]:
    async def _override_get_session():
        async with integration_sessionmaker() as session:
            yield session

    app.dependency_overrides[get_session] = _override_get_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()
```

Note: `app` (unit fixture) and `get_session` import come from
`api.dependencies` — the same object the routers bind to
(`api/database.get_session` and `api/dependencies.get_session` are distinct;
the override targets the one routers import, as established in api-module).

## 5. Integration test cases

### `tests/integration/test_service_db.py` — PostService vs real DB

| Test | Asserts |
|------|---------|
| `test_create_draft_persists` (`@patch("api.services.posts.Engine")`) | row exists with `status=draft`, `source=standard`, content/count persisted |
| `test_create_draft_headliner_persists` | `source=headliner` persisted |
| `test_get_returns_record` | `get(id)` round-trips; unknown id raises `NotFoundError` |
| `test_list_filters_by_status_and_topic` | seeded rows filtered correctly; `total` matches |
| `test_update_content_recomputes_count` | `character_count == len(content)`, `updated_at` refreshed |
| `test_update_published_conflicts` | `ConflictError` raised, row unchanged |
| `test_publish_success_persists_urn` (patched Engine → URN) | `status=published`, URN + `published_at` stored, durable after fresh session read |
| `test_publish_failure_persists_failed` (Engine raises `LinkedInError`) | `status=failed`, `error` message stored; record still `failed` from a new session |
| `test_publish_after_failure_succeeds` | failed → published retry works |
| `test_delete_removes_record` | row gone; second delete raises `NotFoundError` |

### `tests/integration/test_api_flow.py` — HTTP vs real DB

| Test | Asserts |
|------|---------|
| `test_healthz_reports_reachable` | 200 + `database: reachable` |
| `test_full_post_lifecycle` | POST /drafts 201 → GET /posts contains it → PATCH 200 → POST publish 200 with URN → second publish 409 → DELETE 204 → GET 404 |
| `test_publish_linkedin_failure_marks_failed` (patched Engine raises) | 502; subsequent GET shows `status=failed` + error |
| `test_list_pagination_and_filters` | `limit`/`offset`/`status`/`topic` query params behave against real data |

Both files mock only the `Engine` boundary with `@patch` decorators
(CON-TI-004); everything below (session, models, HTTP) is real.

## 6. Makefile (new, repository root)

```make
.PHONY: help format lint typecheck test unit-test coverage \
        integration-test integration-test-up integration-test-down run

help:
	@echo "Available commands:"
	@echo "  make format               - Auto-fix lint (ruff)"
	@echo "  make lint                 - Lint (ruff)"
	@echo "  make typecheck            - Type check (mypy: engagedin cli api)"
	@echo "  make test                 - Run all tests (integration skipped w/o DB)"
	@echo "  make unit-test            - Run unit tests in parallel (-n auto)"
	@echo "  make coverage             - Unit tests with 100% coverage gate (-n auto)"
	@echo "  make integration-test-up  - Start PostgreSQL (5433) + apply migrations"
	@echo "  make integration-test-down - Stop PostgreSQL (5433) and remove volume"
	@echo "  make integration-test     - Run integration tests (starts/stops DB)"
	@echo "  make run                  - Start dev DB + run the API locally"

format:
	uv run ruff check --fix .

lint:
	uv run ruff check . || exit 1

typecheck:
	uv run mypy engagedin cli api || exit 1

unit-test:
	uv run pytest tests/unit/ -vv -n auto || exit 1

test:
	uv run pytest tests/ -v --tb=short || exit 1

integration-test-up:
	@echo "Starting PostgreSQL for integration tests (port 5433)..."
	docker compose -f docker-compose.test.yml up -d postgres
	@i=1; while [ $$i -le 10 ]; do \
		docker compose -f docker-compose.test.yml exec -T postgres \
			pg_isready -U engagedin -d engagedin_test > /dev/null 2>&1 \
			&& echo "PostgreSQL is ready" \
			&& DATABASE_URL=postgresql+asyncpg://engagedin:engagedin@localhost:5433/engagedin_test \
				uv run alembic upgrade head \
			&& echo "Migrations applied" && exit 0; \
		echo "Waiting... (attempt $$i/10)"; sleep 2; i=$$(($$i + 1)); \
	done; echo "PostgreSQL failed to start"; exit 1

integration-test-down:
	docker compose -f docker-compose.test.yml down -v

_NPROC := $(shell nproc 2>/dev/null || echo 1)
INTEGRATION_WORKERS ?= $(shell if [ "$(_NPROC)" -le 8 ]; then echo "$(_NPROC)"; else echo 8; fi)

integration-test: integration-test-up
	DB_... uv run pytest tests/integration/ -v -n $(INTEGRATION_WORKERS) \
		--dist loadscope || ($(MAKE) integration-test-down && exit 1)
	$(MAKE) integration-test-down

coverage:
	uv run pytest tests/unit/ --cov=engagedin --cov=cli --cov=api \
		--cov-fail-under=100 -n auto || exit 1

run:
	docker compose up -d
	@i=1; while [ $$i -le 10 ]; do \
		docker compose exec -T db pg_isready -U engagedin -d engagedin \
			> /dev/null 2>&1 && break; sleep 2; i=$$(($$i + 1)); done
	uv run uvicorn api.main:app --reload
```

(The integration pytest step needs no extra env: fixtures default to port
5433.)

## 7. Parallel execution configuration

- `pyproject.toml` dev group: add `"pytest-xdist (>=3.6)"`.
- `[tool.pytest.ini_options]` becomes:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "session"
asyncio_default_test_loop_scope = "session"
```

Session-scoped loops are what allow the session-scoped async engine fixture
to exist; under xdist each worker process owns its session scope and thus its
unique database (REQ-TI-004, REQ-TI-019).

## 8. CI changes — `.github/workflows/ci.yml`

| Step | Before | After |
|------|--------|-------|
| Install | `uv sync --frozen --extra api` | unchanged (xdist arrives via dev group) |
| Type check | `uv run mypy engagedin cli api` | unchanged |
| Migrations | `uv run alembic upgrade head` | unchanged (service DB on 5433, see below) |
| Unit tests | — | `uv run pytest tests/unit/ --cov=engagedin --cov=cli --cov=api --cov-fail-under=100 -n auto -q` |
| Integration tests | — | `uv run pytest tests/integration/ -n 4 --dist loadscope -q` |
| Postgres service | port `5432:5432` | port `5433:5432`, db `engagedin_test` |
| `DATABASE_URL` env | `…@localhost:5432/engagedin_test` | `…@localhost:5433/engagedin_test` |

Matrix (`3.12`/`3.13`/`3.14`) and `fail-fast: false` preserved. The coverage
gate stays satisfied by the unit step (CON-TI-002), matching today's totals.

## 9. Verification

```bash
make format && make lint && make typecheck
make unit-test                    # parallel, no DB required
make integration-test             # starts DB, runs integration, stops DB
make coverage                     # 100% gate from unit tests
make test                         # full suite, integration skips w/o DB
uv run pytest tests/integration/ -v   # against `make integration-test-up` DB
```

Manual checks:

- `make integration-test` twice in a row succeeds (volume lifecycle clean).
- `make test` with Docker stopped: integration tests SKIP, unit tests pass.
- Two xdist workers never collide: unique DB names visible via
  `\l` in psql during a run.
- CI passes on all three Python versions.

## 10. ADR references

- **ADR-TI-001 — Unique database per session.** Mirrors devotion: per-worker
  isolation for xdist, no TRUNCATE races, cheap disposable databases.
- **ADR-TI-002 — Port 5433 for tests.** Dev and test databases never share an
  instance; a developer running `make run` and `make integration-test`
  concurrently is safe.
- **ADR-TI-003 — `create_all` in fixtures, Alembic in Makefile.** Alembic
  remains the schema source of truth (Makefile applies it); per-session unique
  DBs use `create_all` for speed — same split as devotion.
- **ADR-TI-004 — Coverage from unit tests only.** All application code is
  already 100% covered by mocks; integration tests validate real-database
  behavior without adding coverage obligations, keeping the gate
  DB-independent.
- **ADR-TI-005 — Single flat `docker-compose.test.yml` at root.** engagedin
  has no `infrastructure/` tree; a sibling file to `docker-compose.yml`
  (CON-TI-006) is the minimal faithful adaptation.
