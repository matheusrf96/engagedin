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

## Patch decorator rule

Do NOT use `with patch(...)` blocks inside test functions or `@unittest.mock.patch` decorators. Instead, define `@pytest.fixture` fixtures that wrap `with patch(...)` and yield the mock, then request the fixture in the test function signature.

```python
# ✅ Correct
@pytest.fixture
def mock_settings():
    with patch("engagedin.module.settings") as m:
        yield m

def test_something(mock_settings: MagicMock) -> None:
    mock_settings.some_attr = "value"
    # ... test logic

# ❌ Wrong — with patch inside test body
def test_something() -> None:
    with patch("engagedin.module.settings") as mock_settings:
        ...

# ❌ Wrong — @unittest.mock.patch decorator
@patch("engagedin.module.settings")
def test_something(mock_settings):
    ...
```

This keeps test bodies free of indentation for patching and avoids signature issues with `@patch` in Python 3.12+.

## Mocking

| Dependency | Mock strategy |
|------------|---------------|
| HTTP calls (`httpx`) | `pytest.fixture` wrapping `patch("httpx.get")` / `patch("httpx.post")` |
| LLM (`litellm`) | `pytest.fixture` wrapping `patch("engagedin.llm.client.completion")` |
| File I/O | `monkeypatch` / `tmp_path` fixture |
| Environment | `monkeypatch.setenv` |
| OAuth / Authlib | `pytest.fixture` wrapping `patch("engagedin.linkedin.auth.OAuth2Client")` / `patch("httpx.get")` |
| Click CLI | `CliRunner` from `click.testing` |

## Coverage

- Target: 100% on all source code.
- Use `--cov-report=term-missing` to see uncovered lines after a run.
- New features require new tests.

## Review checklist

- [ ] Every public function tested (happy + error path)
- [ ] No `with patch(...)` blocks in test bodies — use `@pytest.fixture` wrapping `with patch(...)` instead
- [ ] No `@unittest.mock.patch` decorators on test functions — use fixtures that yield mocks
- [ ] Mocks reset between tests (use `autouse` fixtures if needed)
- [ ] No real network calls in unit tests
- [ ] No real env / file dependencies (use monkeypatch / tmp_path)
- [ ] Coverage does not decrease
