---
name: engagedin-context
description: >
  Use when exploring, modifying, or understanding the engagedin project.
  Provides project structure, CLI commands, ruleset format, LLM provider setup,
  OAuth flow, and architecture conventions.
---

# engagedin — Project Context

## What it does

AI-powered LinkedIn content generator. Write and publish LinkedIn posts using an LLM of your choice (DeepSeek, OpenAI, Anthropic, etc.) via LiteLLM.

## Stack

- **Language**: Python 3.12+
- **Package manager**: Poetry
- **CLI framework**: Click
- **Terminal output**: Rich
- **Config / env**: pydantic-settings
- **HTTP client**: httpx
- **LLM abstraction**: LiteLLM
- **OAuth 2.0**: Authlib
- **Testing**: pytest + pytest-cov
- **Linting**: ruff

## Project structure

```
engagedin/
├── engagedin/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli/
│   │   ├── main.py        # Click CLI (6 commands)
│   ├── core/
│   │   ├── config.py      # pydantic-settings (Settings model)
│   │   ├── engine.py      # Orchestrator (generates + posts)
│   │   └── models.py      # Pydantic models
│   ├── linkedin/
│   │   ├── auth.py        # OAuth 2.0 flow + local callback server
│   │   └── client.py      # httpx-based LinkedIn API client
│   ├── llm/
│   │   ├── client.py      # LiteLLM wrapper
│   │   └── prompts.py     # Prompt templates
│   └── rules/
│       ├── loader.py      # YAML rules loader
│       └── defaults.yaml  # Default ruleset
├── tests/               # 55+ tests
├── .env.example
└── pyproject.toml
```

## CLI commands

| Command | Description |
|---------|-------------|
| `engagedin draft <topic>` | Generate a draft post and preview it |
| `engagedin post <topic>` | Generate, preview, confirm, and publish |
| `engagedin auth login` | OAuth 2.0 browser flow |
| `engagedin auth status` | Check authentication |
| `engagedin rules show` | View current ruleset |
| `engagedin config show` | View config (secrets masked) |

Options: `--rules <file>` for custom ruleset, `--yes` to skip confirmation.

## Ruleset format

YAML file in `engagedin/rules/defaults.yaml`:

```yaml
tone: professional
min_length: 150
max_length: 3000
hashtags:
  count: 3
  style: lowercase
schedule:
  best_times: ["7-9", "12-13", "17-18"]
  cooldown_hours: 4
templates:
  hooks: [question, statistic, story, bold_statement]
  outros: [cta_question, cta_discuss, reflection]
```

## Environment variables (`.env`)

| Variable | Description |
|----------|-------------|
| `LINKEDIN_CLIENT_ID` | LinkedIn App client ID |
| `LINKEDIN_CLIENT_SECRET` | LinkedIn App client secret |
| `LINKEDIN_ACCESS_TOKEN` | OAuth 2.0 access token |
| `LINKEDIN_USER_URN` | e.g. `urn:li:person:abc123` |
| `LLM_PROVIDER` | deepseek, openai, anthropic, etc. |
| `LLM_API_KEY` | API key for the provider |
| `LLM_MODEL` | e.g. deepseek-chat, gpt-4o |

## Key architecture rules

- `cli/` — only Click command definitions; delegate logic to `core/`.
- `core/engine.py` — orchestrator: generate draft → preview → confirm → post.
- `linkedin/auth.py` — runs a local HTTP server for OAuth callback.
- All secrets go in `.env`, never in code.
