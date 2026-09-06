# engagedin

AI-powered LinkedIn content generator. Write and publish LinkedIn posts using an LLM of your choice, with a configurable ruleset for tone, length, hashtags, and structure.

Engaged in ships as two applications over one shared core:

- **CLI** — generate and publish posts straight from your terminal
- **API** — an optional FastAPI + PostgreSQL service for HTTP-based generation, draft management, and publishing

## Features

- **AI post generation** — provider-agnostic (DeepSeek, OpenAI, Anthropic, local models, etc.) via LiteLLM
- **Direct LinkedIn publishing** — uses the official versioned LinkedIn REST API (`POST /rest/posts`)
- **Headliner mode** — generates opinionated posts from recent tech news (Hacker News or NewsAPI)
- **News reference card** — the source article the post is about is attached to the LinkedIn post as a native link preview card (title + description), not a plain-text URL
- **Configurable ruleset** — YAML-based rules defining tone, length, hashtags, schedule, and post templates
- **Draft lifecycle (API)** — drafts are persisted in PostgreSQL; edit content, publish when ready, and keep a full post history
- **OAuth 2.0 authentication** — built-in auth flow via `engagedin auth login`; credentials saved to `.env` automatically
- **Preview before posting** — review drafts (and the reference article) before confirming
- **Schedule advisory** — warns when you're about to post outside your configured best-time windows
- **Friendly errors** — clear messages when configuration is missing (no raw tracebacks)
- **Secrets safe** — all credentials go in `.env`, never in code

## Installation

Requirements: Python 3.14+ and [uv](https://docs.astral.sh/uv/).

```bash
pip install uv
git clone git@github.com:matheusrf96/engagedin.git
cd engagedin

# CLI only
uv sync

# CLI + API module
uv sync --extra api
```

## Configuration

Copy the template and fill in your credentials:

```bash
cp .env.example .env
```

Required variables in `.env`:

| Variable | Description |
|---|---|
| `LINKEDIN_CLIENT_ID` | LinkedIn App client ID |
| `LINKEDIN_CLIENT_SECRET` | LinkedIn App client secret |
| `LINKEDIN_ACCESS_TOKEN` | OAuth 2.0 access token (or run `auth login`) |
| `LINKEDIN_USER_URN` | Your LinkedIn URN (e.g. `urn:li:person:abc123`) |
| `LLM_PROVIDER` | LLM provider name (`deepseek`, `openai`, `anthropic`, etc.) |
| `LLM_API_KEY` | API key for the LLM provider |
| `LLM_MODEL` | Model name (e.g. `deepseek-chat`, `gpt-4o`) |

Optional variables:

| Variable | Description |
|---|---|
| `NEWS_SOURCE` | News source for `headliner`: `hackernews` (default, no key) or `newsapi` |
| `NEWS_API_KEY` | Required when `NEWS_SOURCE=newsapi` |
| `RULES_PATH` | Path to a custom ruleset YAML (also via `--rules`) |
| `DATABASE_URL` | API only: Postgres URL (default `postgresql+asyncpg://engagedin:engagedin@localhost:5432/engagedin`) |
| `API_HOST` / `API_PORT` | API only: bind address (default `127.0.0.1:8000`) |

### Quick auth setup

```bash
engagedin auth login
# Opens browser → authorizes → token and user URN are saved to .env automatically

engagedin auth status   # verify the token works
```

## CLI usage

The console script is `engagedin` (or `python -m cli`):

```bash
# Generate a draft and preview it (not published)
engagedin draft "Why Python is great for automation"

# Generate, preview, confirm, and publish
engagedin post "Remote work trends in 2025"

# Skip the confirmation prompt
engagedin post "AI in business" --yes

# Opinionated post from the last 3 days of AI news
engagedin headliner --days 3 --topic AI --yes

# Use a custom ruleset
engagedin post "Topic" --rules my-rules.yaml

# View current ruleset
engagedin rules show

# View configuration (secrets masked)
engagedin config show
```

### Headliner and the news reference card

`engagedin headliner` fetches the latest news for a topic, picks the most significant story, and writes an opinionated post about it. The source article travels with the draft:

- Before publishing, the preview shows a **Reference article** panel with the article title and URL — cancel if it doesn't match the story you expected.
- On publish, LinkedIn renders the article as a **native link preview card** (source URL, title, description) below the post text.
- If the AI fails to identify its source story, the top-ranked article of the fetched list is used as the reference.

| Command | Purpose |
|---|---|
| `engagedin draft <topic>` | Generate a draft, preview only |
| `engagedin post <topic>` | Generate, preview, confirm, publish |
| `engagedin headliner` | News-based opinion post with reference card (`--days` 1–7, `--topic`) |
| `engagedin auth login` / `auth status` | Manage LinkedIn authentication |
| `engagedin rules show` | View the active ruleset |
| `engagedin config show` | View configuration with secrets masked |

## API usage

The API module (optional extra `api`) exposes the same generation/publishing capabilities over HTTP, with persistent drafts in PostgreSQL.

### Setup

```bash
uv sync --extra api

# Start PostgreSQL (docker compose service on localhost:5432)
docker compose up -d

# Apply database migrations
uv run alembic upgrade head

# Run the API server (interactive docs at http://127.0.0.1:8000/docs)
uv run uvicorn api.main:app --reload
```

The server binds to `127.0.0.1:8000` by default; override with `API_HOST`/`API_PORT` in `.env`. Connection settings come from `DATABASE_URL`.

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/health` | Health check (DB ping) |
| `POST` | `/api/v1/drafts` | Generate and store a draft post |
| `GET` | `/api/v1/posts` | List posts (filter by `status`, `topic`; paginated) |
| `GET` | `/api/v1/posts/{id}` | Get a post |
| `PATCH` | `/api/v1/posts/{id}` | Update draft content |
| `POST` | `/api/v1/posts/{id}/publish` | Publish the draft to LinkedIn |
| `DELETE` | `/api/v1/posts/{id}` | Delete a post |
| `GET` | `/api/v1/auth/status` | Check LinkedIn auth |

### Workflow: draft → review → publish

1. **Generate a draft.** Standard drafts generate from a topic; headliner drafts generate from recent news and carry the source article:

```bash
curl -X POST http://localhost:8000/api/v1/drafts \
  -H "Content-Type: application/json" \
  -d '{"topic": "AI", "source": "headliner", "days": 1}'
```

Response (201) — the reference fields describe the news article the post is about:

```json
{
  "id": 1,
  "topic": "AI",
  "source": "headliner",
  "status": "draft",
  "content": "Every headline misses the point about ...",
  "character_count": 234,
  "reference_url": "https://example.com/news",
  "reference_title": "Groundbreaking AI news",
  "reference_description": "News description",
  "linkedin_post_urn": null,
  "error": null,
  "created_at": "2026-09-06T12:00:00",
  "updated_at": "2026-09-06T12:00:00",
  "published_at": null
}
```

2. **Review and edit** the content before publishing (blocked once published):

```bash
curl -X PATCH http://localhost:8000/api/v1/posts/1 \
  -H "Content-Type: application/json" \
  -d '{"content": "Tuned copy of the draft"}'
```

3. **Publish.** The stored content and reference are sent to LinkedIn — posts with a reference render the article card:

```bash
curl -X POST http://localhost:8000/api/v1/posts/1/publish
```

Response (200) sets `status: "published"`, `linkedin_post_urn`, and `published_at`. On LinkedIn API failure the record is kept as `status: "failed"` with the error message in `error` — fix the issue and publish again.

4. **Manage history.** Filter, page, and clean up:

```bash
curl "http://localhost:8000/api/v1/posts?status=draft&topic=AI&limit=10&offset=0"
curl http://localhost:8000/api/v1/posts/1
curl -X DELETE http://localhost:8000/api/v1/posts/1
```

> Standard drafts (`"source": "standard"`, the default) have all `reference_*` fields `null` and publish as text-only posts — exactly like `engagedin post`.

## Ruleset

The default ruleset lives at `engagedin/rules/defaults.yaml`. You can override any field with a custom YAML file:

```yaml
tone: educational          # professional | provocative | educational | storytelling | opinionated
min_length: 200
max_length: 2000
hashtags:
  count: 5
  style: camelcase         # lowercase | camelcase | uppercase
schedule:
  best_times:              # inclusive hour ranges; "22-2" wraps midnight
    - "7-9"
    - "12-13"
  cooldown_hours: 6        # reserved for future use
templates:
  hooks: [question, statistic, story]
  outros: [cta_question, reflection]
```

## Project Structure

```
engagedin/
├── cli/                     # CLI package (Click)
│   ├── __main__.py
│   └── main.py
├── api/                     # FastAPI API package
│   ├── main.py              # App factory + lifespan
│   ├── config.py            # API settings (DATABASE_URL, etc.)
│   ├── database.py          # Async engine, session, Base
│   ├── models.py            # SQLAlchemy ORM (PostRecord)
│   ├── schemas.py           # Pydantic request/response models
│   ├── dependencies.py      # FastAPI dependency providers
│   ├── services/
│   │   └── posts.py         # PostService (business logic)
│   └── routers/
│       ├── health.py        # GET /api/v1/health
│       ├── generation.py    # POST /api/v1/drafts
│       ├── posts.py         # CRUD + publish
│       └── auth.py          # GET /api/v1/auth/status
├── engagedin/               # Shared core logic
│   ├── core/                # Config, engine, models, schedule, env
│   ├── linkedin/            # LinkedIn API client + OAuth
│   ├── llm/                 # LiteLLM wrapper + prompts
│   ├── news/                # Hacker News / NewsAPI client
│   └── rules/               # YAML rules loader
├── migrations/              # Alembic async migrations
├── specs/                   # Spec-driven feature contracts
├── tests/
│   ├── unit/                # CLI, engine, service, API tests
│   └── integration/         # API flow tests against Postgres
├── docker-compose.yml       # PostgreSQL for local dev
├── alembic.ini              # Alembic config
├── .env.example
└── pyproject.toml
```

## Development

```bash
uv sync --extra api --group dev
uv run pytest tests/unit --cov=engagedin --cov=cli --cov=api --cov-fail-under=100 -q
uv run pytest tests/integration -q          # requires docker compose up -d
uv run ruff check .
uv run mypy engagedin cli api migrations
```

Feature changes follow a spec-first workflow: contracts live in `specs/<feature>/` (`requirements.md`, `design.md`, `tasks.md`).

## License

MIT
