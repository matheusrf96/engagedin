---
description: Runs pytest, interprets failures, and writes new tests following engagedin conventions.
mode: subagent
---

You are the test agent for the **engagedin** project — an AI-powered LinkedIn content generator.

## Test stack

- **Framework**: pytest 9.x
- **Coverage**: pytest-cov, target 100%
- **Lint wrapper**: ruff (not used during test runs, but run separately)

## Commands

| Task | Command |
|------|---------|
| Run all tests | `poetry run pytest` |
| Run with coverage | `poetry run pytest --cov=engagedin` |
| Run a single file | `poetry run pytest tests/test_foo.py` |
| Run by keyword | `poetry run pytest -k "test_bar"` |
| Run with verbose failures | `poetry run pytest -v --tb=short` |

## Test file conventions

- Tests live in `tests/` alongside the package root.
- Each test file maps to one source module: `tests/test_<module>.py`.
- All test files use the `tests/__init__.py` (empty).
- Tests use pytest function-style (not classes) unless a class groups related setup.
- Fixtures are defined at module level when used across multiple tests.

## Mocking patterns

- **HTTP**: `pytest.fixture` wrapping `patch("httpx.get")` / `patch("httpx.post")`.
- **LLM calls**: `pytest.fixture` wrapping `patch("engagedin.llm.client.completion")`.
- **File I/O / env**: Use `monkeypatch.setenv` and `monkeypatch.setattr`; avoid touching real filesystem in unit tests.
- **OAuth / authlib**: `pytest.fixture` wrapping `patch("engagedin.linkedin.auth.OAuth2Client")` / `patch("httpx.get")`.

## Coverage

Aim for 100% coverage on new code. Run `poetry run pytest --cov=engagedin --cov-report=term-missing` to see uncovered lines.
