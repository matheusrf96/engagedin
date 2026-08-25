# UV Migration — Tasks

> Tooling migration: the "test" phase is replaced by the verification command
> suite (no unit tests are written).

## Spec

- [ ] Write `specs/uv-migration/requirements.md`
- [ ] Write `specs/uv-migration/design.md`
- [ ] Link the spec from `specs/README.md`

## REQ-UV-001 — Environment sync

- [ ] Run `uv lock` to generate `uv.lock`
- [ ] Delete `poetry.lock`
- [ ] Run `uv sync --frozen` and confirm `.venv` + project + dev group install

## REQ-UV-002 — CLI execution

- [ ] Run `uv run engagedin --help` and confirm the CLI help renders without Poetry

## REQ-UV-003 — CI lint and test

- [ ] Rewrite `.github/workflows/ci.yml` to use `astral-sh/setup-uv@v6`
- [ ] Replace `poetry install --with dev` with `uv sync --frozen`
- [ ] Replace `poetry run` with `uv run` for ruff, mypy, pytest steps
- [ ] Confirm the Python `3.12`/`3.13`/`3.14` matrix is preserved

## REQ-UV-004 — PyPI publishing

- [ ] Rewrite `.github/workflows/publish.yml` to use `astral-sh/setup-uv@v6`
- [ ] Replace `poetry build` with `uv build`
- [ ] Confirm trusted publishing step is unchanged

## REQ-UV-005 — Documentation consistency

- [ ] Update `README.md` installation and development sections
- [ ] Update `.opencode/agents/test.md`
- [ ] Update `.opencode/agents/code-review.md`
- [ ] Update `.opencode/skills/ruff-style/SKILL.md`
- [ ] Update `.opencode/skills/testing-conventions/SKILL.md`

## CON-UV-001 — Lockfile

- [ ] Confirm `uv.lock` is present and committed
- [ ] Confirm `poetry.lock` is absent

## CON-UV-002 — pyproject.toml stability

- [ ] Confirm setuptools build backend unchanged
- [ ] Confirm `[project]` and `[dependency-groups]` tables unchanged

## CON-UV-003 — No behavior change

- [ ] Confirm no application code or test files were modified
- [ ] Confirm no dependency versions changed

## Verification

- [ ] `uv run ruff check .` passes
- [ ] `uv run mypy engagedin` passes
- [ ] `uv run pytest --cov=engagedin --cov-fail-under=100` passes
- [ ] `grep -ri "poetry" . --exclude-dir=.git` returns no matches
- [ ] CI on a pull request against `main` passes all three Python versions