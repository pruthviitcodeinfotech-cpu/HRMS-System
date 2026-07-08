"""Password hashing and verification (bcrypt via passlib).

Reusable primitives only — no user lookup or login flow. The auth module composes
these with the ``users.password_hash`` column.
"""

from passlib.context import CryptContext

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """Return a bcrypt hash for ``plain_password``.

    Raises:
        ValueError: if the password is empty.
    """
    if not plain_password:
        raise ValueError("password must not be empty")
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Return ``True`` if ``plain_password`` matches ``password_hash``.

    Never raises on malformed hashes — returns ``False`` instead, so callers can
    treat verification failures uniformly.
    """
    if not plain_password or not password_hash:
        return False
    try:
        return _pwd_context.verify(plain_password, password_hash)
    except (ValueError, TypeError):
        return False


def needs_rehash(password_hash: str) -> bool:
    """Return ``True`` if ``password_hash`` should be upgraded to current params."""
    return _pwd_context.needs_update(password_hash)
