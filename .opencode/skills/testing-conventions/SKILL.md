---
name: testing-conventions
description: >
  Use when writing, debugging, or modifying tests for engagedin.
  Documents test file conventions, mock patterns, fixture usage, and coverage
  expectations. Trigger on "test", "pytest", "coverage", "mock", "spec".
---

# engagedin — Testing Conventions

## Test runner

```bash
poetry run pytest                          # all tests
poetry run pytest --cov=engagedin          # with coverage report
poetry run pytest -k "test_foo" -v --tb=short  # single test, verbose
poetry run pytest --cov=engagedin --cov-report=term-missing  # show missed lines
```

## File layout

Each source module gets a corresponding test file:

| Source | Test file |
|--------|-----------|
| `engagedin/cli/main.py` | `tests/test_cli.py` |
| `engagedin/core/engine.py` | `tests/test_engine.py` |
| `engagedin/core/config.py` | `tests/test_main.py` |
| `engagedin/core/models.py` | `tests/test_models.py` |
| `engagedin/linkedin/auth.py` | `tests/test_auth.py` |
| `engagedin/linkedin/client.py` | `tests/test_linkedin.py` |
| `engagedin/llm/client.py` | `tests/test_llm.py` |
| `engagedin/rules/loader.py` | `tests/test_rules.py` |

## Test style

- Use pytest function-style (not classes) unless a class is needed for shared setup.
- Fixtures defined at module level in each test file; conftest.py for project-wide fixtures.
- Test function names: `test_<unit>_<scenario>` or `test_<unit>_<condition>_<expected>`.

## Mocking

| Dependency | Mock strategy |
|------------|---------------|
| HTTP calls (`httpx`) | `respx` or `httpx.MockTransport` / `pytest-httpx` |
| LLM (`litellm`) | Patch `litellm.completion` or the wrapper at `engagedin.llm.client` |
| File I/O | `monkeypatch` / `tmp_path` fixture |
| Environment | `monkeypatch.setenv` |
| OAuth / Authlib | Patch `authlib.integrations.httpx_client.OAuth2Client` or the auth module |
| Click CLI | `CliRunner` from `click.testing` |

## Coverage

- Target: 100% on all source code.
- Use `--cov-report=term-missing` to see uncovered lines after a run.
- New features require new tests.

## Review checklist

- [ ] Every public function tested (happy + error path)
- [ ] Mocks reset between tests (use `autouse` fixtures if needed)
- [ ] No real network calls in unit tests
- [ ] No real env / file dependencies (use monkeypatch / tmp_path)
- [ ] Coverage does not decrease
