"""File-handling utilities: safe names, unique keys, extension checks."""

from __future__ import annotations

import os
import re

from app.shared.utils.ids import new_uuid_hex

_UNSAFE = re.compile(r"[^A-Za-z0-9._-]+")


def get_extension(filename: str) -> str:
    """Return the lowercase file extension (without the dot), or ``""``."""
    return os.path.splitext(filename)[1].lstrip(".").lower()


def sanitize_filename(filename: str) -> str:
    """Return a filesystem-safe version of ``filename`` (path components stripped)."""
    base = os.path.basename(filename).strip()
    safe = _UNSAFE.sub("_", base).strip("._")
    return safe or "file"


def unique_filename(original: str) -> str:
    """Return a collision-resistant name preserving the original extension."""
    ext = get_extension(original)
    stem = new_uuid_hex()
    return f"{stem}.{ext}" if ext else stem


def build_storage_key(*parts: str) -> str:
    """Join sanitized path parts into a normalized storage key (forward slashes)."""
    cleaned = [sanitize_filename(p) if "/" not in p else p.strip("/") for p in parts if p]
    return "/".join(segment for segment in cleaned if segment)


def has_allowed_extension(filename: str, allowed: set[str]) -> bool:
    """Return whether ``filename``'s extension is in the ``allowed`` set (lowercased)."""
    return get_extension(filename) in {ext.lower().lstrip(".") for ext in allowed}
