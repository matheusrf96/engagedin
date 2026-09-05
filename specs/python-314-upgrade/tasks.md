# Python 3.14 Upgrade — Tasks

> Tooling/metadata upgrade: no new unit tests are written; verification uses the
> existing quality suite under the new interpreter and tool targets.

## Spec

- [ ] Write `specs/python-314-upgrade/requirements.md`
- [ ] Write `specs/python-314-upgrade/design.md`
- [ ] Link the spec from `specs/README.md`

## REQ-P314-001 — Interpreter pin

- [ ] Create `.python-version` containing `3.14`
- [ ] Confirm `uv run python --version` reports `Python 3.14.x`

## REQ-P314-002 — Package metadata

- [ ] Bump `project.version` to `0.4.0` in `pyproject.toml`
- [ ] Change `requires-python` to `>=3.14`
- [ ] Trim classifiers to `Programming Language :: Python :: 3.14` only
- [ ] Set `[tool.ruff] target-version = "py314"`
- [ ] Set `[tool.mypy] python_version = "3.14"`

## REQ-P314-003 — Static analysis targets

- [ ] Run `uv run ruff check .` and fix any findings introduced by the `py314` target (retain `from __future__ import annotations`; add minimal per-rule ignores per design section 9 if needed)
- [ ] Run `uv run mypy engagedin cli api` and fix any findings introduced by the `3.14` target

## REQ-P314-004 — Lockfile

- [ ] Run `uv lock` and confirm `uv.lock` resolves for the `>=3.14` marker
- [ ] Run `uv sync --frozen --extra api` and confirm a clean install

## REQ-P314-005 — CI

- [ ] Update `.github/workflows/ci.yml` matrix to `python-version: ["3.14"]`
- [ ] Confirm all other CI steps are unchanged

## REQ-P314-006 — Publishing

- [ ] Update `.github/workflows/publish.yml` to `python-version: "3.14"`
- [ ] Run `uv build` and confirm the sdist and wheel build with the new metadata

## REQ-P314-007 — Documentation consistency

- [ ] Update `README.md` requirements line to Python 3.14+
- [ ] Update `AGENTS.md` style bullet to Python 3.14+
- [ ] Update `.opencode/agents/code-review.md`
- [ ] Update `.opencode/skills/ruff-style/SKILL.md`
- [ ] Update `.opencode/skills/engagedin-context/SKILL.md`
- [ ] Update `.opencode/skills/testing-conventions/SKILL.md`
- [ ] Add a `0.4.0` entry to `CHANGELOG.md` documenting the breaking `requires-python` change

## CON-P314-001 — No behavior change

- [ ] Confirm no application or test logic changes beyond lint/type-checker-driven edits

## CON-P314-002 — Future annotations retained

- [ ] Confirm `from __future__ import annotations` remains in place (no mass removal)

## CON-P314-003 — Build backend stability

- [ ] Confirm the setuptools backend, dependency floors, and `[dependency-groups]` are unchanged

## CON-P314-004 — Historical spec records

- [ ] Confirm no files under `specs/uv-migration/`, `specs/api-module/`, or `specs/test-infrastructure/` were modified

## Verification

- [ ] `uv run ruff check .` passes
- [ ] `uv run mypy engagedin cli api` passes
- [ ] `uv run pytest tests/unit/ --cov=engagedin --cov=cli --cov=api --cov-fail-under=100 -n auto -q` passes
- [ ] Integration tests pass against local Postgres (when available)
- [ ] `uv run engagedin --help` renders the CLI help
- [ ] Grep sweep: no `3.12`/`3.13` references outside historical records
- [ ] CI on a pull request against `main` passes the `3.14`-only matrix
