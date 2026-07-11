"""File-upload storage abstraction (local disk today, object storage later).

The storage layer owns **all** upload validation and every filesystem path the
application touches. Callers hand over a stream plus a *logical prefix*; they never
choose the stored path. That inversion is deliberate — a client-supplied path is a
path-traversal / arbitrary-write primitive, so:

* the storage **key is generated server-side** (``<prefix>/<uuid4hex><ext>``) and the
  client filename is kept as *metadata only*;
* every key (including keys read back out of the database) is re-resolved against the
  configured root and rejected unless it stays inside it (``Path.resolve()`` +
  ``is_relative_to``), which also kills absolute paths, ``..`` segments and NUL bytes;
* **size** (``MAX_UPLOAD_SIZE_MB``) and **extension/content-type** are validated against
  an allowlist *before* anything is written, streaming the body so an oversized upload
  is aborted instead of buffered whole;
* writes are **atomic** (temp file in the destination directory + ``os.replace``), so a
  failed upload never leaves a half-written document behind.

Failures raise :class:`~app.core.exceptions.base.ValidationException` (422) or
:class:`~app.core.exceptions.base.NotFoundException` (404) — never
``fastapi.HTTPException`` — so the global handlers render the standard error envelope.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Protocol

import anyio

from app.core.config.settings import get_settings
from app.core.constants.enums import StorageBackend
from app.core.exceptions.base import AppException, NotFoundException, ValidationException
from app.shared.utils.files import get_extension, sanitize_filename
from app.shared.utils.ids import new_uuid_hex

#: Upload allowlist: extension -> the content types accepted for it. Anything else is
#: rejected with ``422 UNSUPPORTED_FILE_TYPE`` (contract §7: "422 bad type / oversize /
#: unsupported extension"). Employee documents are scans or photos of ID papers, so the
#: set is deliberately narrow.
ALLOWED_UPLOAD_TYPES: dict[str, frozenset[str]] = {
    "pdf": frozenset({"application/pdf"}),
    "png": frozenset({"image/png"}),
    "jpg": frozenset({"image/jpeg", "image/jpg", "image/pjpeg"}),
    "jpeg": frozenset({"image/jpeg", "image/jpg", "image/pjpeg"}),
}

_FALLBACK_CONTENT_TYPE = "application/octet-stream"
_CHUNK_SIZE = 64 * 1024


@dataclass(frozen=True)
class StoredFile:
    """The result of a successful upload (persist this, never the client's input)."""

    key: str
    original_filename: str
    size_bytes: int
    content_type: str


class UploadedFile(Protocol):
    """Structural type for an incoming upload (satisfied by Starlette's ``UploadFile``)."""

    filename: str | None
    content_type: str | None

    async def read(self, size: int = -1) -> bytes:  # pragma: no cover - protocol
        ...


def content_type_for(name: str) -> str:
    """Return the canonical content type for ``name``'s extension (allowlist only)."""
    allowed = ALLOWED_UPLOAD_TYPES.get(get_extension(name))
    if not allowed:
        return _FALLBACK_CONTENT_TYPE
    return sorted(allowed)[0]


class LocalStorageClient:
    """Stores uploads on the local filesystem, rooted at ``settings.upload_dir``."""

    def __init__(
        self,
        *,
        base_dir: str | os.PathLike[str] | None = None,
        max_size_bytes: int | None = None,
        allowed_types: dict[str, frozenset[str]] | None = None,
    ) -> None:
        settings = get_settings()
        self._root = Path(base_dir or settings.upload_dir).resolve()
        self._max_size_bytes = (
            max_size_bytes if max_size_bytes is not None else settings.max_upload_size_bytes
        )
        self._allowed_types = allowed_types or ALLOWED_UPLOAD_TYPES

    @property
    def root(self) -> Path:
        """The resolved directory every stored object must live inside."""
        return self._root

    @property
    def max_size_bytes(self) -> int:
        """The configured upload ceiling (``MAX_UPLOAD_SIZE_MB``)."""
        return self._max_size_bytes

    # -- keys / paths -------------------------------------------------------
    def build_key(self, *, prefix: str, filename: str | None) -> str:
        """Return a server-generated key: ``<prefix>/<uuid4hex><ext>``.

        The client filename only contributes its (allow-listed) extension; the name
        itself is never used as a path component.
        """
        segments = [sanitize_filename(part) for part in prefix.split("/") if part.strip()]
        extension = get_extension(sanitize_filename(filename or ""))
        stem = new_uuid_hex()
        leaf = f"{stem}.{extension}" if extension else stem
        return "/".join([*segments, leaf])

    def resolve(self, key: str) -> Path:
        """Resolve ``key`` to an absolute path guaranteed to stay inside :attr:`root`.

        Rejects NUL bytes, absolute paths and ``..`` escapes with
        ``422 INVALID_STORAGE_KEY``.
        """
        if not key or not key.strip() or "\x00" in key:
            raise ValidationException("Invalid storage key.", code="INVALID_STORAGE_KEY")
        resolved = Path(os.path.normpath(str(self._root / key))).resolve()
        if resolved == self._root or not resolved.is_relative_to(self._root):
            raise ValidationException("Invalid storage key.", code="INVALID_STORAGE_KEY")
        return resolved

    def path_for(self, key: str) -> Path:
        """Return the on-disk path of an existing object (``404`` when it is missing)."""
        path = self.resolve(key)
        if not path.is_file():
            raise NotFoundException("The stored file is missing.", code="FILE_NOT_FOUND")
        return path

    # -- validation ---------------------------------------------------------
    def validate_type(self, filename: str | None, content_type: str | None) -> tuple[str, str]:
        """Validate extension + content type; return ``(extension, content_type)``."""
        safe_name = sanitize_filename(filename or "")
        extension = get_extension(safe_name)
        allowed = self._allowed_types.get(extension)
        if not allowed:
            raise ValidationException(
                "Unsupported file type. Allowed: " + ", ".join(sorted(self._allowed_types)) + ".",
                code="UNSUPPORTED_FILE_TYPE",
            )
        declared = (content_type or "").split(";")[0].strip().lower()
        if declared and declared not in allowed and declared != _FALLBACK_CONTENT_TYPE:
            raise ValidationException(
                f"Content type '{declared}' does not match a .{extension} file.",
                code="UNSUPPORTED_FILE_TYPE",
            )
        canonical = declared if declared in allowed else content_type_for(safe_name)
        return extension, canonical

    def validate_size(self, size_bytes: int) -> None:
        """Reject empty and oversized payloads (``settings.max_upload_size_bytes``)."""
        if size_bytes <= 0:
            raise ValidationException("The uploaded file is empty.", code="EMPTY_UPLOAD")
        if size_bytes > self._max_size_bytes:
            limit_mb = self._max_size_bytes / (1024 * 1024)
            raise ValidationException(
                f"The uploaded file exceeds the {limit_mb:g} MB limit.",
                code="FILE_TOO_LARGE",
            )

    # -- write / read / delete ---------------------------------------------
    async def save_upload(self, upload: UploadedFile, *, prefix: str) -> StoredFile:
        """Validate and store an incoming multipart upload; return its metadata.

        The body is streamed and abandoned as soon as it exceeds the configured limit,
        so an oversized upload is never fully buffered nor written to disk.
        """
        filename = upload.filename or ""
        _, content_type = self.validate_type(filename, upload.content_type)

        chunks: list[bytes] = []
        size = 0
        while True:
            chunk = await upload.read(_CHUNK_SIZE)
            if not chunk:
                break
            size += len(chunk)
            if size > self._max_size_bytes:
                self.validate_size(size)  # raises FILE_TOO_LARGE
            chunks.append(chunk)
        self.validate_size(size)

        return await self._store(b"".join(chunks), filename, content_type, prefix, size)

    async def save_bytes(
        self,
        content: bytes,
        *,
        filename: str,
        content_type: str | None = None,
        prefix: str,
    ) -> StoredFile:
        """Validate and store raw bytes (same rules as :meth:`save_upload`)."""
        _, resolved_type = self.validate_type(filename, content_type)
        self.validate_size(len(content))
        return await self._store(content, filename, resolved_type, prefix, len(content))

    async def read(self, key: str) -> bytes:
        """Return the stored object's bytes (``404`` when the key resolves to nothing)."""
        path = self.path_for(key)
        return await anyio.to_thread.run_sync(path.read_bytes)

    async def delete(self, key: str) -> bool:
        """Delete a stored object; ``False`` when it was already gone."""
        path = self.resolve(key)
        return await anyio.to_thread.run_sync(self._unlink, path)

    # -- internals ----------------------------------------------------------
    async def _store(
        self, content: bytes, filename: str, content_type: str, prefix: str, size: int
    ) -> StoredFile:
        key = self.build_key(prefix=prefix, filename=filename)
        await anyio.to_thread.run_sync(self._write_atomic, key, content)
        return StoredFile(
            key=key,
            original_filename=sanitize_filename(filename),
            size_bytes=size,
            content_type=content_type,
        )

    def _write_atomic(self, key: str, content: bytes) -> None:
        """Write ``content`` to ``key`` atomically (temp file + ``os.replace``)."""
        path = self.resolve(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_name(f".{path.name}.{new_uuid_hex()}.part")
        try:
            with open(tmp_path, "wb") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp_path, path)
        finally:
            tmp_path.unlink(missing_ok=True)

    @staticmethod
    def _unlink(path: Path) -> bool:
        if not path.is_file():
            return False
        path.unlink()
        return True


@lru_cache
def get_storage_client() -> LocalStorageClient:
    """Return the configured storage client (cached singleton)."""
    backend = get_settings().storage_backend
    if backend is StorageBackend.LOCAL:
        return LocalStorageClient()
    raise AppException(
        f"Storage backend '{backend.value}' is not implemented.",
        code="STORAGE_BACKEND_UNSUPPORTED",
    )


__all__ = [
    "ALLOWED_UPLOAD_TYPES",
    "LocalStorageClient",
    "StoredFile",
    "UploadedFile",
    "content_type_for",
    "get_storage_client",
]
