"""Unit tests for Enterprise Employee Document Management System (EDMS)."""

from __future__ import annotations

import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.employee.schemas import (
    DocumentApprovalRequest,
    EmployeeDocumentCreateRequest,
)
from app.modules.employee.service import EmployeeService

_ORG_ID = 10
_EMP_ID = 101
_USER_ID = 42
_NOW = datetime.datetime(2026, 7, 29, 10, 0, 0, tzinfo=datetime.timezone.utc)


def _make_service() -> EmployeeService:
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    svc = EmployeeService(session)
    svc.documents = AsyncMock()
    svc.audit = AsyncMock()
    svc.storage = AsyncMock()
    svc._get_active_employee = AsyncMock()
    return svc


@pytest.mark.asyncio
async def test_add_document_with_versioning() -> None:
    """Uploading a new document version increments version_number and sets previous_version_id."""
    svc = _make_service()

    prev_doc = SimpleNamespace(
        document_id=1,
        document_type="id_proof",
        category="id_proof",
        version_number=1,
    )
    svc.documents.list_for_employee.return_value = [prev_doc]

    stored_file = SimpleNamespace(
        key="employees/101/passport_v2.pdf",
        original_filename="passport_v2.pdf",
        size_bytes=204800,
        content_type="application/pdf",
    )
    svc.storage.save_upload = AsyncMock(return_value=stored_file)

    created_doc = SimpleNamespace(
        document_id=2,
        document_type="id_proof",
        category="id_proof",
        original_filename="passport_v2.pdf",
        file_size_bytes=204800,
        mime_type="application/pdf",
        version_number=2,
        previous_version_id=1,
        expiry_date=datetime.date(2030, 1, 1),
        is_confidential=True,
        approval_status="approved",
        uploaded_by=_USER_ID,
        created_at=_NOW,
        updated_at=_NOW,
    )
    svc.documents.create.return_value = created_doc

    payload = EmployeeDocumentCreateRequest(
        document_type="id_proof",
        category="id_proof",
        expiry_date=datetime.date(2030, 1, 1),
        is_confidential=True,
    )

    fake_file = SimpleNamespace(filename="passport_v2.pdf")
    res = await svc.add_document(
        org_id=_ORG_ID,
        actor_id=_USER_ID,
        employee_id=_EMP_ID,
        data=payload,
        upload=fake_file,
    )

    assert res.version_number == 2
    assert res.previous_version_id == 1
    assert res.is_confidential is True
    svc.documents.create.assert_called_once()
    svc.audit.record.assert_called_once()


@pytest.mark.asyncio
async def test_approve_document_status() -> None:
    """Approving or rejecting a document updates approval_status."""
    svc = _make_service()

    mock_doc = SimpleNamespace(
        document_id=10,
        employee_id=_EMP_ID,
        approval_status="pending",
        updated_at=_NOW,
        document_type="contract",
        category="contract",
        original_filename="contract.pdf",
        file_size_bytes=100,
        mime_type="application/pdf",
        version_number=1,
        previous_version_id=None,
        expiry_date=None,
        is_confidential=False,
        uploaded_by=_USER_ID,
        created_at=_NOW,
    )

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_doc
    svc.session.execute.return_value = mock_result

    res = await svc.approve_document(
        org_id=_ORG_ID,
        actor_id=_USER_ID,
        document_id=10,
        approval_status="approved",
        comment="Verified valid contract",
    )

    assert mock_doc.approval_status == "approved"
    svc.audit.record.assert_called_once()
