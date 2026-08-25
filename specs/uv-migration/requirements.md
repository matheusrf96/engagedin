# UV Migration — Requirements

Feature ID: `UV`

## Context

The project currently uses Poetry as its dependency manager. `pyproject.toml`
already follows PEP 621 (`[project]`) and PEP 735 (`[dependency-groups]`), so it
is directly consumable by uv without structural changes. The migration swaps the
dependency manager while keeping the setuptools build backend, dependency set,
application code, and tests unchanged.

## Requirements

### REQ-UV-001 — Environment sync

WHEN a developer runs `uv sync` in the repository root
THE SYSTEM SHALL create a virtual environment at `.venv` and install the project
plus its runtime and `dev` dependency groups resolved from `uv.lock`
WHILE uv is installed and `pyproject.toml` declares the dependencies.

### REQ-UV-002 — CLI execution

WHEN a developer runs `uv run engagedin <command>`
THE SYSTEM SHALL execute the Click CLI within the uv-managed virtual environment
WITHOUT requiring Poetry to be installed
WHILE the environment has been synchronized.

### REQ-UV-003 — CI lint and test

WHEN the CI workflow runs on a push to `main` or a pull request
THE SYSTEM SHALL install uv and Python via `astral-sh/setup-uv@v6` for the
`3.12` / `3.13` / `3.14` matrix, install dependencies with `uv sync --frozen`,
and run ruff, mypy, and pytest (with the 100% coverage gate) through `uv run`
WHILE the repository is checked out and `uv.lock` is committed.

### REQ-UV-004 — PyPI publishing

WHEN a `v*` tag is pushed
THE SYSTEM SHALL build the sdist and wheel with `uv build` and publish them to
PyPI via the trusted-publishing action
WHILE an OIDC trust relationship with PyPI exists.

### REQ-UV-005 — Documentation consistency

WHEN the README and the `.opencode` agent/skill files present installation or
development commands
THE SYSTEM SHALL reference `uv` commands
AND SHALL NOT reference `poetry`
WHILE those documents are maintained.

## Constraints

### CON-UV-001 — Lockfile

The repository SHALL contain a committed `uv.lock`
AND SHALL NOT contain `poetry.lock`.

### CON-UV-002 — pyproject.toml stability

`pyproject.toml` SHALL keep the setuptools build backend and the PEP 621
`[project]` and PEP 735 `[dependency-groups]` tables unchanged.

### CON-UV-003 — No behavior change

The migration SHALL NOT change application code, tests, or dependency versions.