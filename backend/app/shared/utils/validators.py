"""Reusable validation helpers (email, phone, password, uuid, pagination).

Pure boolean/normalization helpers usable from Pydantic validators or services.
They do not raise; callers decide how to surface a failure (typically by raising
:class:`~app.core.exceptions.base.ValidationException`).
"""

from __future__ import annotations

import re

from app.core.constants.enums import MAX_PAGE_SIZE, MIN_PAGE_SIZE
from app.shared.utils.ids import is_valid_uuid

__all__ = [
    "is_valid_email",
    "is_valid_phone",
    "normalize_phone",
    "password_issues",
    "is_strong_password",
    "is_valid_uuid",
    "is_valid_pagination",
]

_EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")
_PHONE_RE = re.compile(r"^\+?[0-9]{7,15}$")


def is_valid_email(value: str) -> bool:
    """Return ``True`` if ``value`` looks like a valid email address."""
    return bool(value) and bool(_EMAIL_RE.match(value.strip()))


def normalize_phone(value: str) -> str:
    """Strip spaces, dashes, and parentheses from a phone number."""
    return re.sub(r"[\s()\-]", "", value or "")


def is_valid_phone(value: str) -> bool:
    """Return ``True`` if ``value`` is a plausible phone number (7–15 digits, opt +)."""
    return bool(_PHONE_RE.match(normalize_phone(value)))


def password_issues(
    value: str,
    *,
    min_length: int = 8,
    require_upper: bool = True,
    require_lower: bool = True,
    require_digit: bool = True,
) -> list[str]:
    """Return a list of policy violations for ``value`` (empty list = strong).

    The concrete password policy is a project decision (see the Authentication API
    Contract open question); these are sensible defaults callers may override.
    """
    issues: list[str] = []
    if len(value) < min_length:
        issues.append(f"must be at least {min_length} characters")
    if require_upper and not any(c.isupper() for c in value):
        issues.append("must contain an uppercase letter")
    if require_lower and not any(c.islower() for c in value):
        issues.append("must contain a lowercase letter")
    if require_digit and not any(c.isdigit() for c in value):
        issues.append("must contain a digit")
    return issues


def is_strong_password(value: str, **kwargs: object) -> bool:
    """Return ``True`` if ``value`` satisfies :func:`password_issues` with no issues."""
    return not password_issues(value, **kwargs)  # type: ignore[arg-type]


def is_valid_pagination(page: int, page_size: int) -> bool:
    """Return ``True`` if ``page``/``page_size`` are within allowed bounds."""
    return page >= 1 and MIN_PAGE_SIZE <= page_size <= MAX_PAGE_SIZE
