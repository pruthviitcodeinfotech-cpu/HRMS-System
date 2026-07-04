"""SQLAlchemy declarative Base and shared metadata.

Foundation object required by every ORM model. A metadata naming convention is
applied so that constraint/index names are deterministic across models and
Alembic migrations. No business models are defined here.
"""

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# Deterministic naming for indexes / constraints (enterprise best practice).
NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Declarative base class for all HRMS ORM models."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)
