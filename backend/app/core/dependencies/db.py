"""FastAPI dependency: request-scoped database session.

Yields one :class:`~sqlalchemy.ext.asyncio.AsyncSession` per request. The session
is committed if the request handler returns normally and rolled back on any
exception, then always closed. Inject it with::

    async def handler(db: AsyncSession = Depends(get_db)) -> ...:
"""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.session import get_session_factory


async def get_db() -> AsyncIterator[AsyncSession]:
    """Provide a transactional database session for the lifetime of a request."""
    session = get_session_factory()()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()
