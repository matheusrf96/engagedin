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
# Requirements: Python 3.12+
pip install poetry
git clone git@github.com:matheusrf96/engagedin.git
cd engagedin
poetry install
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
├── engagedin/
│   ├── cli/main.py        # Click CLI (7 commands)
│   ├── core/
│   │   ├── config.py      # pydantic-settings
│   │   ├── engine.py      # Orchestrator
│   │   ├── env.py         # .env read/write helpers
│   │   ├── models.py      # Pydantic models
│   │   └── schedule.py    # Best-time posting logic
│   ├── linkedin/
│   │   ├── auth.py        # OAuth 2.0 flow + callback handler
│   │   └── client.py      # httpx API client
│   ├── llm/
│   │   ├── client.py      # LiteLLM wrapper
│   │   └── prompts.py     # Prompt templates
│   ├── news/
│   │   ├── client.py      # Hacker News / NewsAPI client
│   │   └── models.py      # NewsArticle model
│   └── rules/
│       ├── loader.py      # YAML rules loader
│       └── defaults.yaml  # Default ruleset
├── tests/                 # 100+ tests, 100% coverage
├── .env.example
└── pyproject.toml
```

## Development

```bash
poetry install --with dev
poetry run pytest --cov=engagedin
poetry run ruff check .
```

## License

MIT
