"""Alembic migration environment.

Loads the database URL from the environment (DATABASE_URL) and the SQLAlchemy
metadata from the application's declarative Base. Model modules are imported so
their tables register on Base.metadata for autogenerate and offline rendering.

Alembic runs synchronously; if DATABASE_URL uses the async driver
(postgresql+asyncpg) it is transparently switched to a sync driver
(postgresql+psycopg2) for migrations.
"""

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.database.base import Base

# --- Register model metadata -------------------------------------------------
# Import model packages so their tables attach to Base.metadata.
import app.modules.approvals.models  # noqa: F401,E402
import app.modules.audit.models  # noqa: F401,E402
import app.modules.employee.models  # noqa: F401,E402
import app.modules.hardware.models  # noqa: F401,E402
import app.modules.leave.models  # noqa: F401,E402
import app.modules.notifications.models  # noqa: F401,E402
import app.modules.payroll.models  # noqa: F401,E402
import app.modules.rbac.models  # noqa: F401,E402
import app.modules.settings.models  # noqa: F401,E402
import app.modules.settlements.models  # noqa: F401,E402
import app.modules.shift.models  # noqa: F401,E402

target_metadata = Base.metadata

# --- Alembic config ----------------------------------------------------------
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def _sync_database_url() -> str:
    """Return a synchronous SQLAlchemy URL for Alembic to use."""
    url = os.getenv("DATABASE_URL", "")
    return url.replace("+asyncpg", "+psycopg2")


_url = _sync_database_url()
if _url:
    config.set_main_option("sqlalchemy.url", _url)


def run_migrations_offline() -> None:
    """Run migrations without a DB connection (emits SQL)."""
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live DB connection."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
