"""Unit tests for :class:`LocalStorageClient` (upload validation + path safety).

The storage layer is the only place that touches the filesystem, so it owns the
security-critical rules: size ceiling, extension/content-type allowlist,
server-generated keys, and the guarantee that no key can escape ``upload_dir``.
"""

from __future__ import annotations

import pytest

from app.core.exceptions.base import NotFoundException, ValidationException
from app.infrastructure.storage.client import LocalStorageClient

_PDF = b"%PDF-1.4 minimal"


class _FakeUpload:
    """Minimal stand-in for Starlette's ``UploadFile``."""

    def __init__(self, content: bytes, filename: str | None, content_type: str | None) -> None:
        self.filename = filename
        self.content_type = content_type
        self._buffer = content

    async def read(self, size: int = -1) -> bytes:
        if size is None or size < 0:
            chunk, self._buffer = self._buffer, b""
            return chunk
        chunk, self._buffer = self._buffer[:size], self._buffer[size:]
        return chunk


@pytest.fixture
def storage(tmp_path) -> LocalStorageClient:
    """A client rooted at a temp dir with a small (1 KiB) size ceiling."""
    return LocalStorageClient(base_dir=tmp_path, max_size_bytes=1024)


# ===========================================================================
# Happy path — server-generated keys
# ===========================================================================
async def test_save_upload_uses_server_generated_key(storage, tmp_path) -> None:
    stored = await storage.save_upload(
        _FakeUpload(_PDF, "pan card.pdf", "application/pdf"), prefix="employees/7"
    )

    # Key is <prefix>/<uuid4hex>.<ext> — the client name is metadata only.
    assert stored.key.startswith("employees/7/")
    assert stored.key.endswith(".pdf")
    assert "pan" not in stored.key
    assert stored.original_filename == "pan_card.pdf"
    assert stored.size_bytes == len(_PDF)
    assert stored.content_type == "application/pdf"

    written = tmp_path / stored.key
    assert written.read_bytes() == _PDF
    # No stray temp files left behind by the atomic write.
    assert [p.name for p in written.parent.iterdir()] == [written.name]


async def test_read_and_delete_round_trip(storage) -> None:
    stored = await storage.save_upload(
        _FakeUpload(_PDF, "id.png", "image/png"), prefix="employees/7"
    )
    assert await storage.read(stored.key) == _PDF
    assert await storage.delete(stored.key) is True
    assert await storage.delete(stored.key) is False
    with pytest.raises(NotFoundException) as exc:
        await storage.read(stored.key)
    assert exc.value.code == "FILE_NOT_FOUND"


# ===========================================================================
# Size validation
# ===========================================================================
async def test_oversize_upload_rejected(storage, tmp_path) -> None:
    oversize = b"x" * 2048  # ceiling is 1024
    with pytest.raises(ValidationException) as exc:
        await storage.save_upload(
            _FakeUpload(oversize, "big.pdf", "application/pdf"), prefix="employees/7"
        )
    assert exc.value.code == "FILE_TOO_LARGE"
    assert exc.value.status_code == 422
    # Nothing was written.
    assert not list(tmp_path.rglob("*.pdf"))


async def test_empty_upload_rejected(storage) -> None:
    with pytest.raises(ValidationException) as exc:
        await storage.save_upload(
            _FakeUpload(b"", "empty.pdf", "application/pdf"), prefix="employees/7"
        )
    assert exc.value.code == "EMPTY_UPLOAD"


async def test_size_ceiling_defaults_to_settings() -> None:
    from app.core.config.settings import get_settings

    assert LocalStorageClient().max_size_bytes == get_settings().max_upload_size_bytes


# ===========================================================================
# Type validation (extension + content type allowlist)
# ===========================================================================
@pytest.mark.parametrize(
    ("filename", "content_type"),
    [
        ("payload.exe", "application/octet-stream"),
        ("payload.svg", "image/svg+xml"),
        ("payload.html", "text/html"),
        ("payload", "application/pdf"),  # no extension at all
        ("payload.pdf.exe", "application/pdf"),  # double extension
    ],
)
async def test_disallowed_extension_rejected(storage, filename, content_type) -> None:
    with pytest.raises(ValidationException) as exc:
        await storage.save_upload(
            _FakeUpload(_PDF, filename, content_type), prefix="employees/7"
        )
    assert exc.value.code == "UNSUPPORTED_FILE_TYPE"


async def test_content_type_must_match_extension(storage) -> None:
    """A .pdf carrying an image content type is a mismatch — reject it."""
    with pytest.raises(ValidationException) as exc:
        await storage.save_upload(
            _FakeUpload(_PDF, "doc.pdf", "image/png"), prefix="employees/7"
        )
    assert exc.value.code == "UNSUPPORTED_FILE_TYPE"


@pytest.mark.parametrize(
    ("filename", "content_type"),
    [
        ("scan.pdf", "application/pdf"),
        ("scan.PNG", "image/png"),
        ("scan.jpg", "image/jpeg"),
        ("scan.jpeg", "image/jpeg; charset=binary"),
    ],
)
async def test_allowlisted_types_accepted(storage, filename, content_type) -> None:
    stored = await storage.save_upload(
        _FakeUpload(_PDF, filename, content_type), prefix="employees/7"
    )
    assert stored.key.startswith("employees/7/")


# ===========================================================================
# Path traversal
# ===========================================================================
async def test_traversal_filename_cannot_escape_upload_dir(storage, tmp_path) -> None:
    """``../../etc/passwd`` has no allow-listed extension AND cannot escape the root."""
    with pytest.raises(ValidationException) as exc:
        await storage.save_upload(
            _FakeUpload(b"root:x:0:0", "../../etc/passwd", "application/pdf"),
            prefix="employees/7",
        )
    assert exc.value.code == "UNSUPPORTED_FILE_TYPE"
    assert not (tmp_path.parent / "etc").exists()


async def test_traversal_filename_with_allowed_extension_is_flattened(storage, tmp_path) -> None:
    """Even a traversal name ending in .pdf only ever contributes its extension."""
    stored = await storage.save_upload(
        _FakeUpload(_PDF, "../../../../tmp/evil.pdf", "application/pdf"), prefix="employees/7"
    )
    assert stored.key.startswith("employees/7/")
    assert ".." not in stored.key
    assert stored.original_filename == "evil.pdf"
    written = (tmp_path / stored.key).resolve()
    assert written.is_relative_to(tmp_path.resolve())
    assert written.read_bytes() == _PDF


async def test_traversal_prefix_is_sanitised(storage) -> None:
    key = storage.build_key(prefix="employees/../../etc", filename="x.pdf")
    assert ".." not in key
    assert storage.resolve(key).is_relative_to(storage.root)


@pytest.mark.parametrize(
    "key",
    [
        "../../etc/passwd",
        "employees/../../../etc/passwd",
        "/etc/passwd",
        "employees/1/\x00.pdf",
        "",
        "   ",
    ],
)
def test_resolve_rejects_unsafe_keys(storage, key) -> None:
    with pytest.raises(ValidationException) as exc:
        storage.resolve(key)
    assert exc.value.code == "INVALID_STORAGE_KEY"


def test_resolve_keeps_safe_keys_inside_root(storage) -> None:
    resolved = storage.resolve("employees/7/abc.pdf")
    assert resolved.is_relative_to(storage.root)
    assert resolved.name == "abc.pdf"


def test_path_for_missing_file_is_404(storage) -> None:
    with pytest.raises(NotFoundException) as exc:
        storage.path_for("employees/7/nope.pdf")
    assert exc.value.code == "FILE_NOT_FOUND"


async def test_delete_rejects_traversal_key(storage) -> None:
    with pytest.raises(ValidationException):
        await storage.delete("../../etc/passwd")
