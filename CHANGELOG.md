# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- FastAPI API module (`api/`) with endpoints for draft generation, post CRUD,
  publish, and LinkedIn auth status.
- PostgreSQL persistence for posts/drafts lifecycle (`PostRecord` model).
- Alembic async migrations (`migrations/`).
- Docker Compose for local PostgreSQL (`docker-compose.yml`).
- Optional `api` extra: `pip install engagedin[api]` or `uv sync --extra api`.
- `AGENTS.md` with code best practices (imports, early returns, service-layer
  exceptions, decorator-based mocking).
- 164 tests with 100% coverage across `engagedin`, `cli`, and `api`.

### Changed

- CLI relocated to top-level `cli/` package (was `engagedin/cli/`).
- Console script now points to `cli.main:cli` (was `engagedin.cli.main:cli`).
- CI installs with `--extra api`, runs mypy over `engagedin cli api`, coverage
  over all three packages, and uses a PostgreSQL service container.
- All test files use `@patch` decorators instead of `with patch(...)` blocks.
- Domain exceptions (`NotFoundError`, `ConflictError`, `ExternalServiceError`)
  live in the service layer; routers only catch service exceptions.
- CI matrix reduced to Python 3.14 only; the publish workflow builds on 3.14.

### Breaking Changes

- Minimum supported Python is now 3.14 (`requires-python = ">=3.14"`); pip
  installs on older interpreters must stay on 0.3.x.
- `python -m engagedin` no longer works; use `python -m cli` instead.
- `engagedin/__main__.py` removed.

### Added (earlier, unreleased)

- Retry with exponential backoff for LinkedIn and news HTTP calls (tenacity).
- `mypy` type checking enforced in development and CI (with `types-PyYAML` stubs).
- `run_oauth_login()` service that encapsulates the OAuth browser flow.

### Changed (earlier, unreleased)

- HTTP status codes now use the `HTTPStatus` enum instead of raw ints.
- OAuth login flow moved out of the CLI layer into `linkedin/auth.py`.

### Fixed

- Publishing retries only pre-send connection failures; mid-response errors no
  longer risk publishing the same post twice.
- LinkedIn transport errors are wrapped in `LinkedInError` after retries are
  exhausted, so the CLI shows a friendly message instead of a traceback.
- OAuth exchange and profile-fetch failures are wrapped in `OAuthError`.
- `.env` files written by `auth login` are restricted to the current user (0600).
- Empty news results raise `NewsError` instead of a bare `RuntimeError`.

## [0.3.0] - 2026-08-03

### Added

- Schedule advisory: `post` and `headliner` warn when the current time is
  outside the `schedule.best_times` windows from the ruleset
  (`engagedin/core/schedule.py`).
- Pre-flight checks with friendly error messages when `LLM_API_KEY` is missing
  for remote providers (local providers like Ollama need no key).
- Friendly error handling for generation and publishing failures in the CLI
  (no more raw tracebacks for missing config or API errors).
- `auth login` now saves `LINKEDIN_ACCESS_TOKEN` and `LINKEDIN_USER_URN`
  directly to `.env` automatically (`engagedin/core/env.py`).
- CI workflows: lint + tests with 100% coverage gate on Python 3.12-3.14, and
  PyPI publishing on version tags.
- Project metadata: keywords, classifiers, project URLs, CHANGELOG.

### Fixed

- `draft` no longer requires a LinkedIn token — the LinkedIn client is now
  created lazily, only when publishing.
- Removed unused `keyring` dependency.

## [0.2.0] - 2026-07-XX

### Added

- `headliner` command: generates opinionated posts from recent tech news
  (Hacker News or NewsAPI).
- `opinionated` tone option.
- News source configuration (`news_source`, `news_api_key`).

## [0.1.0] - 2026-06-XX

### Added

- Initial release: `draft`, `post`, `auth login/status`, `rules show`,
  `config show`.
- YAML rulesets with tone, length, hashtags, schedule, and templates.
- Provider-agnostic LLM support via LiteLLM.
