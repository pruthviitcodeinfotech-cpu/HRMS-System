"""String utilities: slugify, case conversion, truncation, masking."""

from __future__ import annotations

import re
import unicodedata

_SLUG_STRIP = re.compile(r"[^a-z0-9]+")
_CAMEL_BOUNDARY = re.compile(r"(?<!^)(?=[A-Z])")


def slugify(value: str, *, separator: str = "-") -> str:
    """Return a URL/identifier-safe slug of ``value`` (ASCII, lowercase)."""
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    slug = _SLUG_STRIP.sub(separator, normalized.lower()).strip(separator)
    return slug


def snake_to_camel(value: str) -> str:
    """Convert ``snake_case`` to ``camelCase``."""
    head, *tail = value.split("_")
    return head + "".join(word.capitalize() for word in tail)


def camel_to_snake(value: str) -> str:
    """Convert ``camelCase``/``PascalCase`` to ``snake_case``."""
    return _CAMEL_BOUNDARY.sub("_", value).lower()


def truncate(value: str, length: int, *, suffix: str = "…") -> str:
    """Truncate ``value`` to ``length`` characters, appending ``suffix`` if cut."""
    if len(value) <= length:
        return value
    return value[: max(0, length - len(suffix))].rstrip() + suffix


def mask(value: str, *, visible: int = 4, mask_char: str = "*") -> str:
    """Mask all but the last ``visible`` characters (e.g. for account numbers)."""
    if not value:
        return value
    if len(value) <= visible:
        return mask_char * len(value)
    return mask_char * (len(value) - visible) + value[-visible:]


def is_blank(value: str | None) -> bool:
    """Return ``True`` if ``value`` is ``None`` or whitespace-only."""
    return value is None or not value.strip()
