# HRMS Backend image — Python 3.12 (the only supported interpreter; see docs/environment.md).
#
# Dependencies are installed from requirements.txt, which is exported from uv.lock and
# carries a sha256 for every artifact. `--require-hashes` makes the build fail rather
# than silently pull a different wheel, so the image content is reproducible.

# --------------------------------------------------------------------------------------
# Stage 1: build a self-contained virtualenv
# --------------------------------------------------------------------------------------
FROM python:3.12.13-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Only the lockfile export is needed to build the venv, so this layer is cached until a
# dependency actually changes.
COPY requirements.txt ./
RUN pip install --require-hashes --no-deps -r requirements.txt

# --------------------------------------------------------------------------------------
# Stage 2: runtime
# --------------------------------------------------------------------------------------
FROM python:3.12.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

# Run as an unprivileged user.
RUN useradd --create-home --uid 10001 hrms

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app

# Only what the application needs at runtime; see .dockerignore for exclusions.
COPY --chown=hrms:hrms app ./app
COPY --chown=hrms:hrms alembic ./alembic
COPY --chown=hrms:hrms alembic.ini pyproject.toml README.md ./

USER hrms

EXPOSE 8000

# `/health` touches no external dependency, so it is a liveness probe, not a readiness one.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3).status == 200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
