# UV Migration — Tasks

> Tooling migration: the "test" phase is replaced by the verification command
> suite (no unit tests are written).

## Spec

- [x] Write `specs/uv-migration/requirements.md`
- [x] Write `specs/uv-migration/design.md`
- [x] Link the spec from `specs/README.md`

## REQ-UV-001 — Environment sync

- [x] Run `uv lock` to generate `uv.lock`
- [x] Delete `poetry.lock`
- [x] Run `uv sync --frozen` and confirm `.venv` + project + dev group install

## REQ-UV-002 — CLI execution

- [x] Run `uv run engagedin --help` and confirm the CLI help renders without Poetry

## REQ-UV-003 — CI lint and test

- [x] Rewrite `.github/workflows/ci.yml` to use `astral-sh/setup-uv@v6`
- [x] Replace `poetry install --with dev` with `uv sync --frozen`
- [x] Replace `poetry run` with `uv run` for ruff, mypy, pytest steps
- [x] Confirm the Python `3.12`/`3.13`/`3.14` matrix is preserved

## REQ-UV-004 — PyPI publishing

- [x] Rewrite `.github/workflows/publish.yml` to use `astral-sh/setup-uv@v6`
- [x] Replace `poetry build` with `uv build`
- [x] Confirm trusted publishing step is unchanged

## REQ-UV-005 — Documentation consistency

- [x] Update `README.md` installation and development sections
- [x] Update `.opencode/agents/test.md`
- [x] Update `.opencode/agents/code-review.md`
- [x] Update `.opencode/skills/ruff-style/SKILL.md`
- [x] Update `.opencode/skills/testing-conventions/SKILL.md`

## CON-UV-001 — Lockfile

- [x] Confirm `uv.lock` is present and committed
- [x] Confirm `poetry.lock` is absent

## CON-UV-002 — pyproject.toml stability

- [x] Confirm setuptools build backend unchanged
- [x] Confirm `[project]` and `[dependency-groups]` tables unchanged

## CON-UV-003 — No behavior change

- [x] Confirm no application code or test files were modified
- [x] Confirm no dependency versions changed

## Verification

- [x] `uv run ruff check .` passes
- [x] `uv run mypy engagedin` passes
- [x] `uv run pytest --cov=engagedin --cov-fail-under=100` passes
- [x] `grep -ri "poetry" . --exclude-dir=.git` returns no matches
- [x] CI on a pull request against `main` passes all three Python versions