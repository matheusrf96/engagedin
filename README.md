# engagedin

AI-powered LinkedIn content generator. Write and publish LinkedIn posts using an LLM of your choice, with a configurable ruleset for tone, length, hashtags, and structure.

## Features

- **AI post generation** — provider-agnostic (DeepSeek, OpenAI, Anthropic, etc.) via LiteLLM
- **Direct LinkedIn publishing** — uses the official LinkedIn REST API (`POST /rest/posts`)
- **Configurable ruleset** — YAML-based rules defining tone, length, hashtags, schedule, and post templates
- **OAuth 2.0 authentication** — built-in auth flow via `engagedin auth login`
- **Preview before posting** — review drafts, confirm, or cancel
- **Secrets safe** — all credentials go in `.env`, never in code

## Installation

```bash
# Requirements: Python 3.12+
pip install poetry
git clone <repo-url>
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

### Quick auth setup

```bash
engagedin auth login
# Opens browser → authorizes → saves token to .env
```

## Usage

```bash
# Generate a draft and preview it
engagedin draft "Why Python is great for automation"

# Generate, preview, confirm, and publish
engagedin post "Remote work trends in 2025"

# Skip confirmation with --yes
engagedin post "AI in business" --yes

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
tone: educational
min_length: 200
max_length: 2000
hashtags:
  count: 5
  style: camelcase
schedule:
  best_times: ["7-9", "12-13"]
  cooldown_hours: 6
templates:
  hooks: [question, statistic, story]
  outros: [cta_question, reflection]
```

## Project Structure

```
engagedin/
├── engagedin/
│   ├── cli/main.py        # Click CLI (6 commands)
│   ├── core/
│   │   ├── config.py      # pydantic-settings
│   │   ├── engine.py      # Orchestrator
│   │   └── models.py      # Pydantic models
│   ├── linkedin/
│   │   ├── auth.py        # OAuth 2.0 flow + callback handler
│   │   └── client.py      # httpx API client
│   ├── llm/
│   │   ├── client.py      # LiteLLM wrapper
│   │   └── prompts.py     # Prompt templates
│   └── rules/
│       ├── loader.py      # YAML rules loader
│       └── defaults.yaml  # Default ruleset
├── tests/                 # 55 tests, 100% coverage
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
