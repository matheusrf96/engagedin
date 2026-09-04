# API Module — Design

## 1. Target repository layout

```
engagedin/                          (repository root)
├── cli/                            ← moved from engagedin/cli/
│   ├── __init__.py
│   ├── __main__.py                 (new: python -m cli)
│   └── main.py                     (Click app; imports shared logic from engagedin.*)
├── api/
│   ├── __init__.py
│   ├── main.py                     (app factory, lifespan, router wiring)
│   ├── config.py                   (ApiSettings: DATABASE_URL, API_HOST, API_PORT)
│   ├── database.py                 (async engine, sessionmaker, Base, get_session)
│   ├── models.py                   (ORM: PostRecord, PostStatus, DraftSource)
│   ├── schemas.py                  (Pydantic request/response models)
│   ├── dependencies.py             (get_db_session dependency override point)
│   ├── services/
│   │   ├── __init__.py
│   │   └── posts.py                (PostService + typed domain exceptions)
│   └── routers/
│       ├── __init__.py
│       ├── health.py               (GET /healthz)
│       ├── generation.py           (POST /api/v1/drafts)
│       ├── posts.py                (GET/PATCH/DELETE/publish on /api/v1/posts)
│       └── auth.py                 (GET /api/v1/auth/status)
├── engagedin/                      (shared core only — cli/ removed)
│   ├── core/                       (config, engine, models, schedule, env)
│   ├── linkedin/
│   ├── llm/
│   ├── news/
│   └── rules/
├── migrations/                     (Alembic)
│   ├── env.py                      (async engine from DATABASE_URL)
│   ├── script.py.mako
│   └── versions/
│       └── 0001_posts.py
├── alembic.ini                     (script_location = migrations)
├── docker-compose.yml              (postgres:16-alpine)
└── tests/
    ├── conftest.py                 (async DB + client fixtures)
    ├── test_cli.py                 (updated imports/patch targets)
    ├── test_main.py                (updated imports/patch targets)
    └── api/
        ├── test_health.py
        ├── test_generation.py
        ├── test_posts.py
        └── test_auth.py
```

## 2. CLI relocation map

| Element | Before | After |
|---------|--------|-------|
| CLI module | `engagedin/cli/main.py` | `cli/main.py` (via `git mv`) |
| CLI package init | `engagedin/cli/__init__.py` | `cli/__init__.py` |
| `python -m` entry | `engagedin/__main__.py` → `engagedin.cli.main` | deleted; replaced by `cli/__main__.py` → `cli.main` |
| Test imports | `from engagedin.cli.main import cli` | `from cli.main import cli` |
| Test patch targets | `patch("engagedin.cli.main.X")` | `patch("cli.main.X")` |
| Shared imports inside CLI | `from engagedin.core…` / `from engagedin.linkedin…` / `from engagedin.llm…` / `from engagedin.news…` / `from engagedin.rules…` | unchanged |

The relocation is mechanical: no command bodies are edited (REQ-AM-003). All
`engagedin.*` imports inside `cli/main.py` keep working because the shared
package is untouched.

## 3. `pyproject.toml` deltas

```toml
[project.scripts]
engagedin = "cli.main:cli"          # was "engagedin.cli.main:cli"

[project.optional-dependencies]
api = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.30",
    "sqlalchemy[asyncio]>=2.0",
    "asyncpg>=0.29",
    "alembic>=1.13",
]

[tool.setuptools.packages.find]
include = ["engagedin*", "cli*", "api*"]

[dependency-groups]
dev = [
    # existing entries kept, plus:
    "pytest-asyncio (>=0.24)",
]
```

- `greenlet` arrives transitively with `sqlalchemy[asyncio]`; not pinned.
- `[tool.pytest.ini_options]` gains `asyncio_mode = "auto"` so async fixtures
  and tests need no per-test decorators.
- Distribution name, build backend, ruff, mypy, and existing dependencies are
  unchanged.

## 4. API configuration — `api/config.py`

```python
class ApiSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore",
    )

    database_url: str = (
        "postgresql+asyncpg://engagedin:engagedin@localhost:5432/engagedin"
    )
    api_host: str = "127.0.0.1"
    api_port: int = 8000

api_settings = ApiSettings()
```

Environment variables: `DATABASE_URL`, `API_HOST`, `API_PORT`. The existing
`engagedin.core.config.settings` is untouched and remains the source for
LinkedIn / LLM / news / rules configuration.

## 5. Database layer — `api/database.py` and `docker-compose.yml`

```python
class Base(DeclarativeBase): ...

engine = create_async_engine(api_settings.database_url, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session
```

The engine is created at module import; the app lifespan disposes it on
shutdown (REQ-AM-007). Tests override the `get_session` dependency via
`app.dependency_overrides` to inject the test database session.

`docker-compose.yml`:

```yaml
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: engagedin
      POSTGRES_PASSWORD: engagedin
      POSTGRES_DB: engagedin
    ports:
      - "5432:5432"
    volumes:
      - engagedin_pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U engagedin -d engagedin"]
      interval: 5s
      timeout: 5s
      retries: 10

volumes:
  engagedin_pgdata:
```

## 6. Data model — `api/models.py`

```python
class PostStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    FAILED = "failed"

class DraftSource(StrEnum):
    STANDARD = "standard"
    HEADLINER = "headliner"

class PostRecord(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(primary_key=True)
    topic: Mapped[str] = mapped_column(String(500))
    source: Mapped[DraftSource] = mapped_column(
        Enum(DraftSource, native_enum=False, length=16)
    )
    status: Mapped[PostStatus] = mapped_column(
        Enum(PostStatus, native_enum=False, length=16),
        default=PostStatus.DRAFT,
    )
    content: Mapped[str] = mapped_column(Text)
    character_count: Mapped[int]
    linkedin_post_urn: Mapped[str | None] = mapped_column(
        String(120), unique=True
    )
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )
    published_at: Mapped[datetime | None]

    __table_args__ = (Index("ix_posts_status", "status"),)
```

Status state machine:

```
draft ──publish OK────▶ published   (terminal)
draft ──publish fail──▶ failed
failed ──publish OK───▶ published
failed ──publish fail▶ failed     (error message refreshed)
published              (no transitions; PATCH/DELETE-by-id rules below)
```

- PATCH content: allowed for `draft` and `failed`; 409 for `published`.
- Publish: allowed for `draft` and `failed`; 409 for `published`.
- DELETE: allowed for any status.

String-backed enums (`native_enum=False`) produce VARCHAR + CHECK constraints,
keeping migration 0001 simple and diffable (ADR-AM-006).

## 7. Alembic setup — `alembic.ini` and `migrations/`

- `alembic.ini` at the repository root with `script_location = migrations` and
  no hardcoded URL.
- `migrations/env.py` resolves the URL from the `DATABASE_URL` environment
  variable (falling back to `api_settings.database_url`) and runs migrations
  with `async_engine_from_config` + `connection.run_sync(target_metadata...)`
  where `target_metadata = api.models.Base.metadata`.
- Revision `0001_posts` creates the `posts` table per section 6.
- The `alembic` CLI runs with the `api` extra installed
  (`uv run alembic upgrade head`).

## 8. Service layer — `api/services/posts.py`

Typed exceptions raised by the service, mapped by routers:

```python
class NotFoundError(Exception): ...
class ConflictError(Exception): ...
```

```python
class PostService:
    def __init__(self, session: AsyncSession, engine: Engine | None = None):
        self.session = session
        self.engine = engine          # shared engagedin.core.engine.Engine

    async def create_draft(self, topic: str, source: DraftSource, days: int) -> PostRecord:
        # blocking work off the event loop (REQ-AM-008)
        if source is DraftSource.HEADLINER:
            draft = await asyncio.to_thread(
                self._engine().generate_headliner_draft, topic=topic, days=days
            )
        else:
            draft = await asyncio.to_thread(self._engine().generate_draft, topic)
        record = PostRecord(
            topic=topic, source=source, status=PostStatus.DRAFT,
            content=draft.content, character_count=draft.character_count,
        )
        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)
        return record

    async def get(self, post_id: int) -> PostRecord            # raises NotFoundError
    async def list(self, status, topic, limit, offset) -> tuple[list[PostRecord], int]
    async def update_content(self, post_id: int, content: str) -> PostRecord
    async def publish(self, post_id: int) -> PostRecord
    async def delete(self, post_id: int) -> None

    def _engine(self) -> Engine:
        # Lazy Engine construction keeps YAML ruleset loading off the event loop.
```

`publish` builds `GeneratedDraft(content=record.content,
character_count=record.character_count)` and calls
`Engine.publish_draft` inside `asyncio.to_thread`. On success it writes
`linkedin_post_urn`, `status=published`, `published_at=now` and commits. On
`LinkedInError` it writes `status=failed`, `error=str(e)` and commits, then the
router raises the mapped HTTP error — the failure state is durable
(REQ-AM-015).

## 9. API schemas — `api/schemas.py`

```python
class DraftCreateRequest(BaseModel):
    topic: str = Field(min_length=1, max_length=500)
    source: Literal["standard", "headliner"] = "standard"
    days: int = Field(default=1, ge=1, le=7)

class PostUpdateRequest(BaseModel):
    content: str = Field(min_length=1, max_length=3000)   # LinkedIn hard limit

class PostOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    topic: str
    source: DraftSource
    status: PostStatus
    content: str
    character_count: int
    linkedin_post_urn: str | None
    error: str | None
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None

class PostListResponse(BaseModel):
    items: list[PostOut]
    total: int

class AuthStatusResponse(BaseModel):
    name: str
    sub: str
```

## 10. Routers and endpoint contract

All domain routers are mounted with `prefix="/api/v1"` (CON-AM-004).

| Method | Path | Request | Success | Notes |
|--------|------|---------|---------|-------|
| GET | `/healthz` | — | 200 `{"status": "ok", "database": "reachable"}` | 503 with `"database": "unreachable"` when ping fails |
| POST | `/api/v1/drafts` | `DraftCreateRequest` | 201 `PostOut` | 422 invalid body; 400 `LLMConfigError`; 502 `NewsError`; 500 unexpected |
| GET | `/api/v1/posts` | query: `status?`, `topic?`, `limit=20`, `offset=0` | 200 `PostListResponse` | newest-first; `limit` capped at 100 |
| GET | `/api/v1/posts/{id}` | — | 200 `PostOut` | 404 unknown id |
| PATCH | `/api/v1/posts/{id}` | `PostUpdateRequest` | 200 `PostOut` | 404 unknown; 409 when `published` |
| POST | `/api/v1/posts/{id}/publish` | — | 200 `PostOut` | 404 unknown; 409 when `published`; 502 `LinkedInError` (record set to `failed`) |
| DELETE | `/api/v1/posts/{id}` | — | 204 | 404 unknown |
| GET | `/api/v1/auth/status` | — | 200 `AuthStatusResponse` | 502 `LinkedInError` |

`app/main.py` factory:

```python
def create_app() -> FastAPI:
    app = FastAPI(title="EngagedIn API", lifespan=lifespan)
    app.include_router(health.router)                          # /healthz
    for router in (generation, posts, auth):
        app.include_router(router, prefix="/api/v1")
    return app

app = create_app()
```

## 11. Error mapping

| Exception | HTTP | Raised when |
|-----------|------|-------------|
| `NotFoundError` (service) | 404 | post id absent |
| `ConflictError` (service) | 409 | PATCH/publish on a `published` record |
| `LLMConfigError` | 400 | LLM configuration missing/invalid |
| `NewsError` | 502 | news source failure (headliner) |
| `LinkedInError` | 502 | LinkedIn API failure (publish, auth status) |
| unexpected | 500 | unhandled failure; message logged, generic detail returned |

Routers catch `NotFoundError`/`ConflictError` from the service and map them to
`HTTPException`; library exceptions are caught around the `to_thread` call
sites. Every error response carries `{"detail": "<human-readable message>"}`.

## 12. Sequence flows

Draft generation (`POST /api/v1/drafts`, source=`headliner`):

1. Router resolves `AsyncSession` via `get_session`; builds `PostService`.
2. `PostService.create_draft` dispatches to
   `Engine.generate_headliner_draft(topic, news_context…, days)` inside
   `asyncio.to_thread` (news fetch + LLM completion are blocking).
3. On success: `PostRecord(status=draft, source=headliner)` inserted, commit,
   201 with `PostOut`.
4. On `LLMConfigError` → 400; on `NewsError` → 502. Nothing is persisted.

Publish (`POST /api/v1/posts/{id}/publish`):

1. Service loads the record → 404 if absent, 409 if `published`.
2. `GeneratedDraft` rebuilt from stored content; `Engine.publish_draft` runs
   inside `asyncio.to_thread`.
3. Success: `linkedin_post_urn` + `status=published` + `published_at`, commit,
   200.
4. `LinkedInError`: `status=failed`, `error` message, commit, 502.

## 13. Testing strategy

- **Fixtures (`tests/conftest.py`)**:
  - `database_url` — from the `DATABASE_URL` env var (CI injects
    `…@localhost:5432/engagedin_test`); local default is the Compose service.
  - `db_engine` (session-scoped) — creates/drops all tables via
    `Base.metadata` around the test session; faster than Alembic in tests.
  - `db_session` — per-test `AsyncSession`.
  - `client` — `httpx.AsyncClient(transport=ASGITransport(app=app),
    base_url="http://test")` with `app.dependency_overrides[get_session]`
    yielding the test session.
  - `mock_engine_cls` — `patch("api.services.posts.Engine")` mirroring the
    `test_cli.py` pattern; canned `GeneratedDraft` returns.
- **Async**: `pytest-asyncio` with `asyncio_mode = "auto"`.
- **Test files**: `tests/api/test_health.py`, `test_generation.py`
  (standard + headliner + error mapping), `test_posts.py` (CRUD, publish
  success/failure/409/404), `test_auth.py` (200/502).
- **CLI tests**: `tests/test_cli.py` and `tests/test_main.py` keep their
  behavior; only imports and patch targets move (REQ-AM-004).
- **Coverage**: every router branch (success, 404, 409, 400, 502), the service
  methods, config, database module, and lifespan are exercised so the 100%
  gate holds for `cli` and `api` (CON-AM-006).

## 14. CI changes — `.github/workflows/ci.yml`

| Step | Before | After |
|------|--------|-------|
| Install | `uv sync --frozen` | `uv sync --frozen --extra api` |
| Services | — | `postgres:16-alpine` (env `POSTGRES_DB: engagedin_test`, user/pass `engagedin`, port 5432, healthcheck) |
| Env | — | `DATABASE_URL: postgresql+asyncpg://engagedin:engagedin@localhost:5432/engagedin_test` |
| Migrate | — | `uv run alembic upgrade head` |
| Lint | `uv run ruff check .` | unchanged |
| Type check | `uv run mypy engagedin` | `uv run mypy engagedin cli api` |
| Test | `uv run pytest --cov=engagedin --cov-fail-under=100 -q` | `uv run pytest --cov=engagedin --cov=cli --cov=api --cov-fail-under=100 -q` |

The Python `3.12` / `3.13` / `3.14` matrix and `fail-fast: false` are
preserved. `.github/workflows/publish.yml` is unchanged — `uv build` picks up
the new packages through `packages.find`.

## 15. Documentation changes

| File | Change |
|------|--------|
| `README.md` | New "Repository layout" section (`cli/`, `api/`, `engagedin/`); new "API" section: `docker compose up -d`, `uv sync --extra api`, `uv run alembic upgrade head`, `uv run uvicorn api.main:app --reload`, curl examples for `/healthz`, draft generation, and publish; CLI install note: base install unchanged, `engagedin[api]` enables the API. |
| `.env.example` | Adds `DATABASE_URL`, `API_HOST`, `API_PORT` with defaults (REQ-AM-021). |
| `CHANGELOG.md` | Unreleased section: Added (API module, docker-compose, Alembic), Changed (CLI relocated to top-level `cli/`; console script now `cli.main:cli`), Removed/changed (breaking): `python -m engagedin` → `python -m cli` (REQ-AM-027). |

## 16. Verification

```bash
uv sync --extra api --group dev
docker compose up -d
uv run alembic upgrade head
uv run uvicorn api.main:app --reload          # smoke: GET /healthz → 200
uv run ruff check .
uv run mypy engagedin cli api
uv run pytest --cov=engagedin --cov=cli --cov=api --cov-fail-under=100 -q
uv run engagedin --help                        # CLI parity
python -m cli --help                           # module entry parity
```

Manual checks:

- `POST /api/v1/drafts` returns 201 and the row appears in `GET /api/v1/posts`.
- `POST /api/v1/posts/{id}/publish` on a real token returns 200 and the URN is
  stored; on a bad token the record becomes `failed` with 502.
- `alembic revision --autogenerate` after upgrade yields an empty migration.
- CI passes on all three Python versions with the Postgres service.

## 17. ADR references

- **ADR-AM-001 — Top-level `cli/` and `api/` packages.** Literal requirement
  (CLI isolated at `/cli` of the project root) and clean app separation.
  Tradeoff: generic top-level names can shadow foreign packages in polluted
  environments; accepted for a locally-run tool (CON-AM-009).
- **ADR-AM-002 — Async SQLAlchemy + asyncpg with an `asyncio.to_thread`
  bridge.** The shared engine (`engagedin.core.engine.Engine`, LiteLLM, httpx)
  is synchronous; instead of porting it, blocking calls run in threads.
  Alternatives rejected: sync psycopg (contradicts the async Postgres choice),
  full async rewrite of shared clients (out of scope, high risk).
- **ADR-AM-003 — No authentication.** Open-source tool run locally; default
  bind `127.0.0.1`; auth can be layered later without contract changes.
- **ADR-AM-004 — Persist every generated draft.** No opt-out flag; history is
  the DB's purpose and deletion is explicit (`DELETE`), keeping the request
  schema minimal.
- **ADR-AM-005 — Alembic at the repository root.** Migrations describe the
  database, not the app package; `script_location` stays independent of `api/`.
- **ADR-AM-006 — String-backed enums (`native_enum=False`).** VARCHAR + CHECK
  constraints instead of Postgres native enums, keeping migration 0001 simple
  and future status renames additive.
