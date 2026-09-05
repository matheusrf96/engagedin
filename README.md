# engagedin

AI-powered LinkedIn content generator. Write and publish LinkedIn posts using an LLM of your choice, with a configurable ruleset for tone, length, hashtags, and structure.

## Features

- **AI post generation** — provider-agnostic (DeepSeek, OpenAI, Anthropic, etc.) via LiteLLM
- **Direct LinkedIn publishing** — uses the official LinkedIn REST API (`POST /rest/posts`)
- **Headliner mode** — generates opinionated posts from recent tech news (Hacker News or NewsAPI)
- **Configurable ruleset** — YAML-based rules defining tone, length, hashtags, schedule, and post templates
- **OAuth 2.0 authentication** — built-in auth flow via `engagedin auth login`; credentials saved to `.env` automatically
- **Preview before posting** — review drafts, confirm, or cancel
- **Schedule advisory** — warns when you're about to post outside your configured best-time windows
- **Friendly errors** — clear messages when configuration is missing (no raw tracebacks)
- **Secrets safe** — all credentials go in `.env`, never in code

## Installation

```bash
# Requirements: Python 3.14+ and uv
pip install uv
git clone git@github.com:matheusrf96/engagedin.git
cd engagedin
uv sync
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

### Quick auth setup

```bash
engagedin auth login
# Opens browser → authorizes → token and user URN are saved to .env automatically
```

## Usage

```bash
# Generate a draft and preview it
engagedin draft "Why Python is great for automation"

# Generate, preview, confirm, and publish
engagedin post "Remote work trends in 2025"

# Skip confirmation with --yes
engagedin post "AI in business" --yes

# Opinionated post from the last 3 days of AI news
engagedin headliner --days 3 --topic AI --yes

# Use a custom ruleset
engagedin post "Topic" --rules my-rules.yaml

# Check authentication
engagedin auth status

# View current ruleset
engagedin rules show

# View configuration (secrets masked)
engagedin config show
```

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
├── tests/
│   ├── api/                 # API endpoint tests
│   └── ...                  # CLI, engine, service tests
├── docker-compose.yml       # PostgreSQL for local dev
├── alembic.ini              # Alembic config
├── .env.example
└── pyproject.toml
```

## Development

```bash
uv sync --extra api
uv run pytest --cov=engagedin --cov=cli --cov=api
uv run ruff check .
uv run mypy engagedin cli api
```

## API Module

engagedin includes an optional FastAPI API for HTTP-based post generation and management, backed by PostgreSQL.

### Setup

```bash
# Install with API extras
uv sync --extra api

# Start PostgreSQL
docker compose up -d

# Apply migrations
uv run alembic upgrade head

# Run the API server
uv run uvicorn api.main:app --reload
```

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/health` | Health check (DB ping) |
| `POST` | `/api/v1/drafts` | Generate a draft post |
| `GET` | `/api/v1/posts` | List posts (filter by `status`, `topic`) |
| `GET` | `/api/v1/posts/{id}` | Get a post |
| `PATCH` | `/api/v1/posts/{id}` | Update draft content |
| `POST` | `/api/v1/posts/{id}/publish` | Publish to LinkedIn |
| `DELETE` | `/api/v1/posts/{id}` | Delete a post |
| `GET` | `/api/v1/auth/status` | Check LinkedIn auth |

### Example: generate a draft

```bash
curl -X POST http://localhost:8000/api/v1/drafts \
  -H "Content-Type: application/json" \
  -d '{"topic": "Python async patterns"}'
```

## License

MIT
