# Python 3.14 Upgrade — Requirements

Feature ID: `P314`

## Context

The project currently declares `requires-python = ">=3.12"` while already running
CPython 3.14.2 in the development virtual environment, and CI already includes
`3.14` in its version matrix. Tooling and metadata lag behind: ruff targets
`py312`, mypy checks against `3.12`, the publish workflow builds on `3.12`, and
no `.python-version` pin exists. This upgrade standardizes the project on Python
3.14 — the latest stable release — by raising the minimum supported version,
retargeting static analysis, shrinking CI to a single `3.14` job, and updating
all documentation that references the old floor. Raising `requires-python` is a
breaking metadata change for the PyPI package, so the package version bumps to
`0.4.0`.

## Requirements

### REQ-P314-001 — Interpreter pin

WHEN a developer runs `uv sync`, `uv run`, or any uv-managed command in the
repository root
THE SYSTEM SHALL use CPython 3.14 resolved from a committed `.python-version`
file
WHILE uv is installed and `.python-version` contains `3.14`.

### REQ-P314-002 — Package metadata

WHEN the package metadata is read from `pyproject.toml`
THE SYSTEM SHALL declare `requires-python = ">=3.14"`, version `0.4.0`, and
classifiers listing only `Programming Language :: Python :: 3.14`
WHILE the setuptools build backend and the PEP 621 `[project]` table are
preserved.

### REQ-P314-003 — Static analysis targets

WHEN ruff or mypy run against the codebase
THE SYSTEM SHALL target Python 3.14 (ruff `target-version = "py314"`, mypy
`python_version = "3.14"`)
AND SHALL pass with zero errors
WHILE code modifications are limited to linter- or type-checker-driven changes.

### REQ-P314-004 — Lockfile

WHEN a developer or CI runs `uv sync --frozen`
THE SYSTEM SHALL install the environment resolved from a `uv.lock` regenerated
for the `>=3.14` requirement marker
WHILE the runtime and `dev` dependency groups resolve without conflicts.

### REQ-P314-005 — CI

WHEN the CI workflow runs on a push to `main` or a pull request
THE SYSTEM SHALL run the lint, type-check, unit-test (with the 100% coverage
gate), migration, and integration-test steps on Python `3.14` only
WHILE the repository is checked out and `uv.lock` is committed.

### REQ-P314-006 — Publishing

WHEN a `v*` tag is pushed
THE SYSTEM SHALL build the sdist and wheel with `uv build` on Python `3.14` and
publish them to PyPI via trusted publishing
WHILE an OIDC trust relationship with PyPI exists.

### REQ-P314-007 — Documentation consistency

WHEN the README, AGENTS.md, or `.opencode` agent/skill files state the project's
Python version or conventions
THE SYSTEM SHALL reference Python 3.14+
AND SHALL NOT reference Python 3.12 or 3.13 as the supported floor
WHILE historical records (completed spec folders and past CHANGELOG entries)
are left unchanged.

## Constraints

### CON-P314-001 — No behavior change

The upgrade SHALL NOT change application behavior
AND code modifications SHALL be limited to what ruff or mypy require under the
new targets.

### CON-P314-002 — Future annotations retained

The `from __future__ import annotations` imports SHALL be retained across the
codebase
AND SHALL NOT be mass-removed, because AGENTS.md mandates them and they remain
harmless under PEP 649 deferred annotation evaluation.

### CON-P314-003 — Build backend stability

`pyproject.toml` SHALL keep the setuptools build backend, the PEP 621
`[project]` dependency floors, and the PEP 735 `[dependency-groups]` table
unchanged.

### CON-P314-004 — Historical spec records

The completed spec folders under `specs/` SHALL NOT be edited; the CI matrix
requirements they contain are superseded by this spec.
