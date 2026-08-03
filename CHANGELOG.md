# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Retry with exponential backoff for LinkedIn and news HTTP calls (tenacity).
- `mypy` type checking enforced in development and CI (with `types-PyYAML` stubs).
- `run_oauth_login()` service that encapsulates the OAuth browser flow.

### Changed

- HTTP status codes now use the `HTTPStatus` enum instead of raw ints.
- OAuth login flow moved out of the CLI layer into `linkedin/auth.py`.
- Tests use fixture-based patching instead of inline `with patch(...)` blocks.

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
