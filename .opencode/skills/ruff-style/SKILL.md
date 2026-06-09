---
name: ruff-style
description: >
  Use when linting, formatting, or fixing code style in engagedin.
  Documents the ruff configuration, enabled rule sets, and Python 3.12
  conventions. Trigger on "ruff", "lint", "format", "style", "line length".
---

# engagedin — Ruff & Code Style

## Configuration

Defined in `pyproject.toml`:

```toml
[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP"]
```

## Rules enabled

| Code | Category |
|------|----------|
| `E` | pycodestyle errors |
| `F` | pyflakes (logic errors) |
| `I` | isort (import order) |
| `N` | pep8-naming |
| `W` | pycodestyle warnings |
| `UP` | pyupgrade (Python 3.12+ idioms) |

## Running

```bash
poetry run ruff check .              # check all files
poetry run ruff check --fix .        # auto-fix safe violations
poetry run ruff check tests/         # check only tests
```

ruff is configured as a linter only — no formatter is active.

## Python 3.12 conventions

- Type union syntax: `str | None` instead of `Optional[str]`.
- Use `Path.read_text()` / `Path.write_text()` over `open()` where concise.
- Use `str.removeprefix()` / `str.removesuffix()` over manual slicing.
- Prefer `list[str]` over `List[str]` (PEP 585).
- Use `type` statements for type aliases where appropriate.
- Use `Self` return type from `typing` for classmethod return types.

## Import order (isort)

1. `from __future__` annotations
2. Standard library
3. Third-party
4. First-party (`engagedin`)
5. Local imports

Groups separated by a blank line. Within groups: alphabetical by module, then by symbol.

## Naming (pep8-naming)

- Classes: `PascalCase`
- Functions / methods: `snake_case`
- Constants: `UPPER_CASE`
- Private: `_leading_underscore`
- Modules: `snake_case` (short, no hyphens)

## What not to do

- No wildcard imports (`from foo import *`).
- No bare `except:` (use `except Exception:` at minimum).
- No mutable default arguments.
- No `print()` in production code (use `rich.print` or `click.echo`).
- No hardcoded secrets or tokens.
