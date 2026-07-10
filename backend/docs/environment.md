# Development Environment

This project's environment is **frozen**: local machines, Docker, and CI all run the
same Python interpreter and the same dependency versions, resolved once and recorded in
`uv.lock`. If it works on one machine, it works on all of them.

## Supported Python version

**Python 3.12** — specifically `3.12.13`, recorded in `.python-version`.

`pyproject.toml` declares `requires-python = ">=3.12,<3.13"`. That is an upper *and*
lower bound on purpose:

- **3.11 and below are not supported.** The test suite uses `datetime.UTC`, added in
  3.11, and the pinned toolchain was resolved and validated only on 3.12. 3.11 has never
  been exercised.
- **3.13+ is not supported yet.** It removes the stdlib `crypt` module. `passlib` tolerates
  its absence, but the combination is unvalidated, and the bound keeps every environment
  on one interpreter rather than letting each pick its own.

Docker uses `python:3.12.13-slim`. CI uses `3.12.13`. They are the same interpreter.

## Dependency management

`uv` is the resolver and installer. There are three generated files, and **one** source of
truth:

| File | Role | Edit by hand? |
|---|---|---|
| `pyproject.toml` | Direct dependencies, each pinned to an exact `==` version | **Yes** |
| `uv.lock` | Full transitive graph with hashes; the source of truth for installs | No — `make lock` |
| `requirements.txt` | Runtime deps exported from the lock, hash-pinned, pip-installable | No — `make lock` |
| `requirements-dev.txt` | Runtime + dev deps, same format | No — `make lock` |

`requirements*.txt` exist so Docker and any pip-only consumer get a byte-for-byte
reproducible install without needing `uv`.

### Install

```bash
make install        # uv sync --locked --extra dev --python 3.12
```

`--locked` asserts that `uv.lock` is still consistent with `pyproject.toml` and **fails**
if it is not, so an installed environment always matches the lockfile.

> Do not substitute `--frozen` here. `--frozen` means "skip the check and install the
> lock as-is": if someone edits `pyproject.toml` without relocking, `--frozen` installs
> the *stale* graph and reports success. `--locked` fails loudly instead.

### Change a dependency

```bash
# 1. Edit the pinned version in pyproject.toml
# 2. Regenerate the lock and both exports
make lock
# 3. Reinstall and run the suite
make install && make test
# 4. Commit pyproject.toml, uv.lock, requirements.txt, requirements-dev.txt together
```

`make lock-check` verifies the lock and the exports are in sync with `pyproject.toml`.
CI runs it, so a hand-edited `pyproject.toml` without a regenerated lock fails the build.

## Pinned versions of note

Two pins encode hard-won constraints. Do not relax them without reading the comment in
`pyproject.toml`:

- **`bcrypt==4.0.1`** — `passlib` 1.7.4 probes its bcrypt backend by hashing a 73-byte
  password. `bcrypt >= 5` raises `ValueError` instead of truncating, which makes *every*
  `hash_password()` call fail; login and user creation break entirely. `bcrypt >= 4.1`
  also removed `__about__`, which passlib logs as a trapped error on import.
- **`passlib==1.7.4`** — the last release; the pin above is what makes it usable.

## Common commands

```bash
make install     # frozen install into ./.venv
make test        # pytest (834 tests)
make run         # uvicorn with --reload on :8000
make lint        # ruff + mypy
make format      # black + ruff --fix
make migrate     # alembic upgrade head
make lock        # regenerate uv.lock + requirements*.txt
make lock-check  # fail if the lock is stale
```

All `make` targets invoke `./.venv/bin/python` explicitly, so they never depend on which
interpreter happens to be first on your `PATH`.

## Docker

```bash
docker compose up --build          # db + redis + api on :8000
docker compose --profile worker up # additionally start the background worker
```

The image is multi-stage: a builder stage creates `/opt/venv` from `requirements.txt`
with `pip install --require-hashes`, and the runtime stage copies that venv and the
application, running as the unprivileged `hrms` user.

`docker-compose.yml` reads `.env` if present but does not require it — a fresh clone
comes up on the defaults declared in the file. Copy `.env.example` to `.env` to override.

The `worker` service sits behind a Compose profile and does not start by default, because
`app/jobs/worker.py` is still a placeholder with no entrypoint.

## Environment variables

Copy `.env.example` to `.env`. `.env` is gitignored and must never be committed.

In production, `Settings` refuses to load with placeholder secrets: `ENVIRONMENT=production`
requires real `SECRET_KEY`, `JWT_SECRET`, `ALLOWED_ORIGINS`, and `ALLOWED_HOSTS`, and
rejects `DEBUG=true`. The application fails at startup rather than serving traffic with a
publicly known JWT signing key.
