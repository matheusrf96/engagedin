# Python 3.14 Upgrade — Tasks

> Tooling/metadata upgrade: no new unit tests are written; verification uses the
> existing quality suite under the new interpreter and tool targets.

## Spec

- [x] Write `specs/python-314-upgrade/requirements.md`
- [x] Write `specs/python-314-upgrade/design.md`
- [x] Link the spec from `specs/README.md`

## REQ-P314-001 — Interpreter pin

- [x] Create `.python-version` containing `3.14`
- [x] Confirm `uv run python --version` reports `Python 3.14.x` (3.14.2)

## REQ-P314-002 — Package metadata

- [x] Bump `project.version` to `0.4.0` in `pyproject.toml`
- [x] Change `requires-python` to `>=3.14`
- [x] Trim classifiers to `Programming Language :: Python :: 3.14` only
- [x] Set `[tool.ruff] target-version = "py314"`
- [x] Set `[tool.mypy] python_version = "3.14"`

## REQ-P314-003 — Static analysis targets

- [x] Run `uv run ruff check .` and fix any findings introduced by the `py314` target (all checks passed, no code changes needed)
- [x] Run `uv run mypy engagedin cli api` and fix any findings introduced by the `3.14` target (no issues in 38 source files)

## REQ-P314-004 — Lockfile

- [x] Run `uv lock` and confirm `uv.lock` resolves for the `>=3.14` marker (94 packages, no conflicts)
- [x] Run `uv sync --frozen --extra api` and confirm a clean install

## REQ-P314-005 — CI

- [x] Update `.github/workflows/ci.yml` matrix to `python-version: ["3.14"]`
- [x] Confirm all other CI steps are unchanged

## REQ-P314-006 — Publishing

- [x] Update `.github/workflows/publish.yml` to `python-version: "3.14"`
- [x] Run `uv build` and confirm the sdist and wheel build with the new metadata (`engagedin-0.4.0.tar.gz`, `engagedin-0.4.0-py3-none-any.whl`)

## REQ-P314-007 — Documentation consistency

- [x] Update `README.md` requirements line to Python 3.14+
- [x] Update `AGENTS.md` style bullet to Python 3.14+
- [x] Update `.opencode/agents/code-review.md`
- [x] Update `.opencode/skills/ruff-style/SKILL.md`
- [x] Update `.opencode/skills/engagedin-context/SKILL.md`
- [x] Update `.opencode/skills/testing-conventions/SKILL.md`
- [x] Add a `0.4.0` entry to `CHANGELOG.md` documenting the breaking `requires-python` change (recorded under `[Unreleased]` Changed + Breaking Changes per the Keep a Changelog convention)

## CON-P314-001 — No behavior change

- [x] Confirm no application or test logic changes beyond lint/type-checker-driven edits (none were required)

## CON-P314-002 — Future annotations retained

- [x] Confirm `from __future__ import annotations` remains in place (no mass removal)

## CON-P314-003 — Build backend stability

- [x] Confirm the setuptools backend, dependency floors, and `[dependency-groups]` are unchanged

## CON-P314-004 — Historical spec records

- [x] Confirm no files under `specs/uv-migration/`, `specs/api-module/`, or `specs/test-infrastructure/` were modified

## Verification

- [x] `uv run ruff check .` passes
- [x] `uv run mypy engagedin cli api` passes
- [x] `uv run pytest tests/unit/ --cov=engagedin --cov=cli --cov=api --cov-fail-under=100 -n auto -q` passes (170 passed, 100.00%)
- [x] Integration tests pass against local Postgres (migrations applied; 15 passed)
- [x] `uv run engagedin --help` renders the CLI help
- [x] Grep sweep: no `3.12`/`3.13` references outside historical records
- [ ] CI on a pull request against `main` passes the `3.14`-only matrix
