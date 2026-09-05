.PHONY: help format lint typecheck test unit-test coverage \
        integration-test integration-test-up integration-test-down run

help:
	@echo "Available commands:"
	@echo "  make format               - Auto-fix lint (ruff check --fix)"
	@echo "  make lint                 - Lint (ruff check)"
	@echo "  make typecheck            - Type check (mypy: engagedin cli api)"
	@echo "  make test                 - Run all tests (integration skipped w/o DB)"
	@echo "  make unit-test            - Run unit tests in parallel (-n auto)"
	@echo "  make coverage             - Unit tests with 100% coverage gate (-n auto)"
	@echo "  make integration-test-up  - Start PostgreSQL (5433) + apply migrations"
	@echo "  make integration-test-down - Stop PostgreSQL (5433) and remove volume"
	@echo "  make integration-test     - Run integration tests (starts/stops DB)"
	@echo "  make run                  - Start dev DB + run the API locally"

format:
	uv run ruff check --fix .

lint:
	uv run ruff check . || exit 1

typecheck:
	uv run mypy engagedin cli api || exit 1

unit-test:
	uv run pytest tests/unit/ -vv -n auto || exit 1

test:
	uv run pytest tests/ -v --tb=short || exit 1

integration-test-up:
	@echo ""
	@echo "Starting PostgreSQL for integration tests (port 5433)..."
	docker compose -f docker-compose.test.yml up -d postgres
	@echo "Waiting for PostgreSQL to be ready..."
	@i=1; while [ $$i -le 10 ]; do \
		docker compose -f docker-compose.test.yml exec -T postgres \
			pg_isready -U engagedin -d engagedin_test > /dev/null 2>&1 \
			&& echo "PostgreSQL is ready!" \
			&& DATABASE_URL=postgresql+asyncpg://engagedin:engagedin@localhost:5433/engagedin_test \
				uv run alembic upgrade head \
			&& echo "Migrations applied" && exit 0; \
		echo "Waiting... (attempt $$i/10)"; sleep 2; i=$$(($$i + 1)); \
	done; \
	echo "PostgreSQL failed to start"; exit 1

integration-test-down:
	@echo ""
	@echo "Stopping integration test database..."
	docker compose -f docker-compose.test.yml down -v
	@echo "Done"

_NPROC := $(shell nproc 2>/dev/null || echo 1)
INTEGRATION_WORKERS ?= $(shell if [ "$(_NPROC)" -le 8 ]; then echo "$(_NPROC)"; else echo 8; fi)

integration-test: integration-test-up
	@echo ""
	@echo "Running integration tests with port 5433..."
	@echo ""
	DB_USER=engagedin DB_PASS=engagedin DB_HOST=localhost DB_PORT=5433 DB_NAME=engagedin_test POSTGRES_PORT=5433 uv run pytest tests/integration/ -v -n $(INTEGRATION_WORKERS) --dist loadscope || ($(MAKE) integration-test-down && exit 1)
	@echo ""
	$(MAKE) integration-test-down

coverage:
	uv run pytest tests/unit/ --cov=engagedin --cov=cli --cov=api --cov-fail-under=100 -n auto || exit 1

run:
	@echo "Starting PostgreSQL..."
	docker compose up -d
	@echo "Waiting for PostgreSQL to be ready..."
	@i=1; while [ $$i -le 10 ]; do \
		docker compose exec -T db pg_isready -U engagedin -d engagedin > /dev/null 2>&1 \
			&& echo "PostgreSQL is ready!" && break; \
		echo "Waiting... (attempt $$i/10)"; sleep 2; i=$$(($$i + 1)); \
	done
	DATABASE_URL=postgresql+asyncpg://engagedin:engagedin@localhost:5432/engagedin uv run uvicorn api.main:app --reload
