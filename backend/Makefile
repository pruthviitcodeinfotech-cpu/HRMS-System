.PHONY: install lock lock-check run worker migrate revision test lint format

# Python 3.12 is the only supported interpreter (see docs/environment.md).
PYTHON_VERSION := 3.12
VENV := .venv
PY := $(VENV)/bin/python

# Install the exact dependency graph recorded in uv.lock, then the project itself.
# `--locked` asserts uv.lock is still consistent with pyproject.toml and fails otherwise.
# (`--frozen` would install the stale lock silently — it skips the check rather than
# performing it.) An installed environment therefore always matches the lockfile.
install:
	uv sync --locked --extra dev --python $(PYTHON_VERSION)

# Regenerate uv.lock and the pip-installable exports after editing pyproject.toml.
lock:
	uv lock --python $(PYTHON_VERSION)
	uv export --frozen --no-emit-project --format requirements.txt -o requirements.txt
	uv export --frozen --no-emit-project --extra dev --format requirements.txt -o requirements-dev.txt

# CI guard: proves uv.lock and requirements*.txt are in sync with pyproject.toml.
# The exports are regenerated with the same `-o` path they were created with, because
# uv records the invoking command in the file header.
lock-check:
	uv lock --check --python $(PYTHON_VERSION)
	@tmp=$$(mktemp -d); cp requirements.txt requirements-dev.txt $$tmp/; \
	 uv export --frozen --no-emit-project --format requirements.txt -o requirements.txt >/dev/null 2>&1; \
	 uv export --frozen --no-emit-project --extra dev --format requirements.txt -o requirements-dev.txt >/dev/null 2>&1; \
	 rc=0; \
	 diff -u $$tmp/requirements.txt requirements.txt || rc=1; \
	 diff -u $$tmp/requirements-dev.txt requirements-dev.txt || rc=1; \
	 rm -rf $$tmp; \
	 if [ $$rc -ne 0 ]; then echo "requirements*.txt are stale — run 'make lock'"; exit 1; fi; \
	 echo "lock and exports are in sync"

run:
	$(PY) -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

worker:
	$(PY) -m app.jobs.worker

migrate:
	$(PY) -m alembic upgrade head

revision:
	$(PY) -m alembic revision --autogenerate -m "$(m)"

test:
	$(PY) -m pytest

lint:
	$(PY) -m ruff check app tests
	$(PY) -m mypy app

format:
	$(PY) -m black app tests
	$(PY) -m ruff check --fix app tests
