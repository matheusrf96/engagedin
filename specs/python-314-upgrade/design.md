# Python 3.14 Upgrade — Design

## 1. Current state

- `.venv` already runs CPython 3.14.2; uv has `cpython-3.14.2` installed and it
  is the system default `python3`. The runtime migration is effectively done —
  this change makes 3.14 the declared, enforced minimum.
- CI (`.github/workflows/ci.yml`) already includes `3.14` in its matrix and is
  green; publish (`.github/workflows/publish.yml`) builds on `3.12`.
- Metadata and tooling lag: `requires-python = ">=3.12"`, ruff
  `target-version = "py312"`, mypy `python_version = "3.12"`, no
  `.python-version` pin.
- No usage of stdlib modules removed in recent Python versions was found in
  `engagedin/`, `cli/`, `api/`, or `tests/`.

## 2. `pyproject.toml`

| Setting | Before | After |
|---------|--------|-------|
| `project.version` | `0.3.0` | `0.4.0` |
| `project.requires-python` | `>=3.12` | `>=3.14` |
| classifiers | 3.12, 3.13, 3.14 | 3.14 only |
| `[tool.ruff] target-version` | `py312` | `py314` |
| `[tool.mypy] python_version` | `3.12` | `3.14` |

The setuptools build backend, the `[project]` dependency floors, and
`[dependency-groups] dev` are unchanged. The pinned dev tool versions (pytest
9.x, ruff 0.15.x, mypy 1.20.x) all support Python 3.14 and the `py314` target.

## 3. Interpreter pin

Create `.python-version` with the single line `3.14`. uv reads it for `uv sync`,
`uv run`, and `uv python install`, making the development interpreter
deterministic. uv resolves the loose `3.14` pin to the newest installed or
downloadable CPython 3.14.x patch release.

## 4. Lockfile

Run `uv lock` after the metadata change. The `requires-python` bump rewrites the
lockfile's `resolution-markers`, so `uv.lock` is regenerated and committed.
Existing dependency floors are kept: the currently locked versions already
resolve and run under 3.14 (the live `.venv` is 3.14.2 installed from the same
lock). If `uv lock` surfaces a conflict, raise the affected floor to the nearest
3.14-compatible release and record it in the CHANGELOG entry.

## 5. CI workflow — `.github/workflows/ci.yml`

| Before | After |
|--------|-------|
| `python-version: ["3.12", "3.13", "3.14"]` | `python-version: ["3.14"]` |

All steps are unchanged: `uv sync --frozen --extra api`, ruff, mypy
(`engagedin cli api`), unit tests with the 100% coverage gate, `alembic upgrade
head` against the Postgres service, and integration tests. `fail-fast: false`
becomes a no-op for a single-element matrix and is kept to avoid gratuitous
diffs.

## 6. Publish workflow — `.github/workflows/publish.yml`

| Before | After |
|--------|-------|
| `python-version: "3.12"` | `python-version: "3.14"` |

`uv build` and trusted publishing (`pypa/gh-action-pypi-publish@release/v1`)
are unchanged.

## 7. Code changes

None expected. If `ruff check` or `mypy` surface new findings under the 3.14
targets, fix only what they require:

- `from __future__ import annotations` stays in all files that have it (ADR
  below).
- No adoption of new 3.14 syntax (t-strings, etc.) — modernization beyond
  linter/type-checker findings is out of scope.

## 8. Documentation updates

| File | Change |
|------|--------|
| `README.md` | "Requirements: Python 3.12+ and uv" → "Python 3.14+ and uv". |
| `AGENTS.md` | Style bullet "Python 3.12+" → "Python 3.14+" (convention list unchanged). |
| `.opencode/agents/code-review.md` | "target is 3.12+" → "target is 3.14+". |
| `.opencode/skills/ruff-style/SKILL.md` | "Python 3.12" descriptor, "pyupgrade (Python 3.12+ idioms)", and the "Python 3.12 conventions" heading → 3.14. |
| `.opencode/skills/engagedin-context/SKILL.md` | "Language: Python 3.12+" → "Language: Python 3.14+". |
| `.opencode/skills/testing-conventions/SKILL.md` | "Python 3.12+" mention → "Python 3.14+". |
| `CHANGELOG.md` | New `0.4.0` entry: minimum supported Python is now 3.14 (breaking), package version bump, CI matrix reduced to `3.14`. |

Historical records — the completed specs (`specs/uv-migration/`,
`specs/api-module/`, `specs/test-infrastructure/`) and past CHANGELOG entries —
are not edited.

## 9. ADR — keep `from __future__ import annotations`

Under PEP 649/749 (deferred evaluation of annotations, default in 3.14), the
import is redundant. It is retained because (a) AGENTS.md mandates it as a
convention, (b) it is harmless under lazy annotation evaluation, and (c)
removing it changes annotation-evaluation timing across pydantic/FastAPI-heavy
modules for zero benefit. If ruff's `UP` rules flag the imports under
`target-version = "py314"`, add the minimal per-rule ignore instead of removing
the imports.

## 10. Verification

```bash
uv lock
uv sync --frozen --extra api
uv run ruff check .
uv run mypy engagedin cli api
uv run pytest tests/unit/ --cov=engagedin --cov=cli --cov=api --cov-fail-under=100 -n auto -q
POSTGRES_PORT=5433 uv run pytest tests/integration/ -n 4 --dist loadscope -q   # requires local Postgres
uv build
uv run engagedin --help
```

Manual checks:

- `uv run python --version` prints `Python 3.14.x`.
- A grep sweep for `3.12` / `3.13` returns no matches outside historical
  records (past CHANGELOG entries, `specs/` history, `uv.lock` internals).
- CI on a pull request against `main` passes on the `3.14`-only matrix.

## 11. ADR references

- ADR (this spec): `from __future__ import annotations` retained under 3.14 —
  section 9.
- Supersedes: the CI `3.12`/`3.13`/`3.14` matrix requirements in
  `specs/uv-migration` (REQ-UV-003), `specs/api-module`, and
  `specs/test-infrastructure`. Historical spec files are left unchanged per
  CON-P314-004.
