"""Integration tests for the Settings Management router."""

from __future__ import annotations

import datetime
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.dependencies.auth import assert_session_live
from app.modules.settings.dependencies import get_settings_service
from app.modules.settings.schemas import (
    ConfigurationViewResponse,
    FeaturesResponse,
    OrgSalarySlipResponse,
    OrgSettingsResponse,
)
from tests.conftest import API_PREFIX

_NOW = datetime.datetime(2026, 7, 10, 10, 0, 0, tzinfo=datetime.timezone.utc)  # noqa: UP017
_BASE = f"{API_PREFIX}/settings"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_settings_service() -> AsyncMock:
    """Mock stand-in for SettingsService."""
    return AsyncMock()


@pytest_asyncio.fixture
async def settings_client(app, mock_settings_service: AsyncMock) -> AsyncClient:
    """HTTP client with SettingsService mocked."""
    # The auth dependency re-validates the session against the DB on every request;
    # router tests exercise the HTTP layer without a database, so stub that check.
    app.dependency_overrides[assert_session_live] = lambda: None
    app.dependency_overrides[get_settings_service] = lambda: mock_settings_service
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Response builders
# ---------------------------------------------------------------------------


def _org_settings_schema() -> OrgSettingsResponse:
    return OrgSettingsResponse(
        id=1,
        org_id=1,
        advance_shift_enabled=False,
        enable_regularization=False,
        enable_photo_punch=False,
        device_sync_time=datetime.time(16, 51, 0),
        sync_code="SYNC001",
        pass_code="SECRET",
        updated_by=None,
        created_at=_NOW,
        updated_at=_NOW,
    )


def _slip_schema() -> OrgSalarySlipResponse:
    return OrgSalarySlipResponse(
        id=2,
        org_id=1,
        company_logo_url=None,
        company_name="ACME Corp",
        company_address="123 Main St",
        company_contact="9876543210",
        company_website_email=None,
        auto_release_payslip=True,
        branch_wise_payslip=False,
        updated_by=None,
        created_at=_NOW,
        updated_at=_NOW,
    )


def _config_view() -> ConfigurationViewResponse:
    return ConfigurationViewResponse(
        organization=_org_settings_schema(),
        salary_slip=_slip_schema(),
        cross_module_pointers={},
    )


def _features() -> FeaturesResponse:
    return FeaturesResponse(
        features={
            "advance_shift_enabled": False,
            "enable_regularization": False,
            "enable_photo_punch": False,
            "auto_release_payslip": True,
            "branch_wise_payslip": False,
        }
    )


# ===========================================================================
# 1. GET /settings  — Combined view
# ===========================================================================


@pytest.mark.asyncio
async def test_get_configuration_view_200(
    settings_client: AsyncClient,
    mock_settings_service: AsyncMock,
    super_admin_headers: dict[str, str],
) -> None:
    mock_settings_service.get_configuration_view.return_value = {
        "organization": _org_settings_schema(),
        "salary_slip": _slip_schema(),
        "cross_module_pointers": {},
    }

    resp = await settings_client.get(_BASE, headers=super_admin_headers)

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["data"]["organization"]["org_id"] == 1


@pytest.mark.asyncio
async def test_get_configuration_view_401_no_token(settings_client: AsyncClient) -> None:
    resp = await settings_client.get(_BASE)
    assert resp.status_code == 401


# ===========================================================================
# 2. GET /settings/organization
# ===========================================================================


@pytest.mark.asyncio
async def test_get_org_settings_200(
    settings_client: AsyncClient,
    mock_settings_service: AsyncMock,
    super_admin_headers: dict[str, str],
) -> None:
    mock_settings_service.get_org_settings.return_value = _org_settings_schema()

    resp = await settings_client.get(f"{_BASE}/organization", headers=super_admin_headers)

    assert resp.status_code == 200
    data = resp.json()
    assert data["data"]["pass_code"] == "********"  # masked


@pytest.mark.asyncio
async def test_get_org_settings_404(
    settings_client: AsyncClient,
    mock_settings_service: AsyncMock,
    super_admin_headers: dict[str, str],
) -> None:
    from app.modules.settings.exceptions import SettingsNotFoundException

    mock_settings_service.get_org_settings.side_effect = SettingsNotFoundException()

    resp = await settings_client.get(f"{_BASE}/organization", headers=super_admin_headers)

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_org_settings_401_no_token(settings_client: AsyncClient) -> None:
    resp = await settings_client.get(f"{_BASE}/organization")
    assert resp.status_code == 401


# ===========================================================================
# 3. PATCH /settings/organization
# ===========================================================================


@pytest.mark.asyncio
async def test_patch_org_settings_200(
    settings_client: AsyncClient,
    mock_settings_service: AsyncMock,
    super_admin_headers: dict[str, str],
) -> None:
    updated = _org_settings_schema()
    mock_settings_service.update_org_settings.return_value = updated

    payload = {"advance_shift_enabled": True, "sync_code": "NEW01", "pass_code": "PASS1"}
    resp = await settings_client.patch(
        f"{_BASE}/organization", json=payload, headers=super_admin_headers
    )

    assert resp.status_code == 200
    mock_settings_service.update_org_settings.assert_called_once()


@pytest.mark.asyncio
async def test_patch_org_settings_401_no_token(settings_client: AsyncClient) -> None:
    resp = await settings_client.patch(f"{_BASE}/organization", json={})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_patch_org_settings_validation_error(
    settings_client: AsyncClient,
    mock_settings_service: AsyncMock,
    super_admin_headers: dict[str, str],
) -> None:
    from app.modules.settings.exceptions import SettingsValidationException

    mock_settings_service.update_org_settings.side_effect = SettingsValidationException(
        "sync_code must not exceed 50 characters."
    )
    payload = {"sync_code": "X" * 60}
    resp = await settings_client.patch(
        f"{_BASE}/organization", json=payload, headers=super_admin_headers
    )

    assert resp.status_code == 422


# ===========================================================================
# 4. POST /settings/organization/reset
# ===========================================================================


@pytest.mark.asyncio
async def test_reset_org_settings_200(
    settings_client: AsyncClient,
    mock_settings_service: AsyncMock,
    super_admin_headers: dict[str, str],
) -> None:
    mock_settings_service.reset_org_settings.return_value = _org_settings_schema()

    resp = await settings_client.post(f"{_BASE}/organization/reset", headers=super_admin_headers)

    assert resp.status_code == 200
    assert "defaults" in resp.json()["message"].lower()


@pytest.mark.asyncio
async def test_reset_org_settings_404_not_initialized(
    settings_client: AsyncClient,
    mock_settings_service: AsyncMock,
    super_admin_headers: dict[str, str],
) -> None:
    from app.modules.settings.exceptions import SettingsNotFoundException

    mock_settings_service.reset_org_settings.side_effect = SettingsNotFoundException()

    resp = await settings_client.post(f"{_BASE}/organization/reset", headers=super_admin_headers)

    assert resp.status_code == 404


# ===========================================================================
# 5. GET /settings/salary-slip
# ===========================================================================


@pytest.mark.asyncio
async def test_get_salary_slip_200(
    settings_client: AsyncClient,
    mock_settings_service: AsyncMock,
    super_admin_headers: dict[str, str],
) -> None:
    mock_settings_service.get_salary_slip_settings.return_value = _slip_schema()

    resp = await settings_client.get(f"{_BASE}/salary-slip", headers=super_admin_headers)

    assert resp.status_code == 200
    assert resp.json()["data"]["company_name"] == "ACME Corp"


@pytest.mark.asyncio
async def test_get_salary_slip_404(
    settings_client: AsyncClient,
    mock_settings_service: AsyncMock,
    super_admin_headers: dict[str, str],
) -> None:
    from app.modules.settings.exceptions import SettingsNotFoundException

    mock_settings_service.get_salary_slip_settings.side_effect = SettingsNotFoundException()

    resp = await settings_client.get(f"{_BASE}/salary-slip", headers=super_admin_headers)

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_salary_slip_401_no_token(settings_client: AsyncClient) -> None:
    resp = await settings_client.get(f"{_BASE}/salary-slip")
    assert resp.status_code == 401


# ===========================================================================
# 6. PATCH /settings/salary-slip
# ===========================================================================


@pytest.mark.asyncio
async def test_patch_salary_slip_200(
    settings_client: AsyncClient,
    mock_settings_service: AsyncMock,
    super_admin_headers: dict[str, str],
) -> None:
    mock_settings_service.update_salary_slip_settings.return_value = _slip_schema()

    payload = {"company_name": "New Corp", "auto_release_payslip": False}
    resp = await settings_client.patch(
        f"{_BASE}/salary-slip", json=payload, headers=super_admin_headers
    )

    assert resp.status_code == 200
    mock_settings_service.update_salary_slip_settings.assert_called_once()


@pytest.mark.asyncio
async def test_patch_salary_slip_validation_error(
    settings_client: AsyncClient,
    mock_settings_service: AsyncMock,
    super_admin_headers: dict[str, str],
) -> None:
    from app.modules.settings.exceptions import SettingsValidationException

    mock_settings_service.update_salary_slip_settings.side_effect = SettingsValidationException(
        "company_name is required."
    )
    resp = await settings_client.patch(f"{_BASE}/salary-slip", json={}, headers=super_admin_headers)

    assert resp.status_code == 422


# ===========================================================================
# 7. GET /settings/features
# ===========================================================================


@pytest.mark.asyncio
async def test_get_features_200(
    settings_client: AsyncClient,
    mock_settings_service: AsyncMock,
    super_admin_headers: dict[str, str],
) -> None:
    mock_settings_service.get_features.return_value = {
        "advance_shift_enabled": True,
        "enable_regularization": False,
        "enable_photo_punch": False,
        "auto_release_payslip": True,
        "branch_wise_payslip": False,
    }

    resp = await settings_client.get(f"{_BASE}/features", headers=super_admin_headers)

    assert resp.status_code == 200
    assert resp.json()["data"]["features"]["advance_shift_enabled"] is True


@pytest.mark.asyncio
async def test_get_features_401_no_token(settings_client: AsyncClient) -> None:
    resp = await settings_client.get(f"{_BASE}/features")
    assert resp.status_code == 401


# ===========================================================================
# 8. PATCH /settings/features/{feature_key}
# ===========================================================================


@pytest.mark.asyncio
async def test_set_feature_enable_200(
    settings_client: AsyncClient,
    mock_settings_service: AsyncMock,
    super_admin_headers: dict[str, str],
) -> None:
    mock_settings_service.set_feature.return_value = {
        "advance_shift_enabled": True,
        "enable_regularization": False,
        "enable_photo_punch": False,
        "auto_release_payslip": True,
        "branch_wise_payslip": False,
    }

    resp = await settings_client.patch(
        f"{_BASE}/features/advance_shift_enabled",
        json={"enabled": True},
        headers=super_admin_headers,
    )

    assert resp.status_code == 200
    body = resp.json()
    assert "enabled" in body["message"]
    mock_settings_service.set_feature.assert_called_once()


@pytest.mark.asyncio
async def test_set_feature_disable_200(
    settings_client: AsyncClient,
    mock_settings_service: AsyncMock,
    super_admin_headers: dict[str, str],
) -> None:
    mock_settings_service.set_feature.return_value = {
        "advance_shift_enabled": False,
        "enable_regularization": False,
        "enable_photo_punch": False,
        "auto_release_payslip": True,
        "branch_wise_payslip": False,
    }

    resp = await settings_client.patch(
        f"{_BASE}/features/advance_shift_enabled",
        json={"enabled": False},
        headers=super_admin_headers,
    )

    assert resp.status_code == 200
    assert "disabled" in resp.json()["message"]


@pytest.mark.asyncio
async def test_set_feature_unknown_key_404(
    settings_client: AsyncClient,
    mock_settings_service: AsyncMock,
    super_admin_headers: dict[str, str],
) -> None:
    from app.modules.settings.exceptions import UnknownFeatureException

    mock_settings_service.set_feature.side_effect = UnknownFeatureException(
        "Unknown feature key: 'bad_key'."
    )

    resp = await settings_client.patch(
        f"{_BASE}/features/bad_key",
        json={"enabled": True},
        headers=super_admin_headers,
    )

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_set_feature_settings_not_found_404(
    settings_client: AsyncClient,
    mock_settings_service: AsyncMock,
    super_admin_headers: dict[str, str],
) -> None:
    from app.modules.settings.exceptions import SettingsNotFoundException

    mock_settings_service.set_feature.side_effect = SettingsNotFoundException()

    resp = await settings_client.patch(
        f"{_BASE}/features/advance_shift_enabled",
        json={"enabled": True},
        headers=super_admin_headers,
    )

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_set_feature_missing_body_422(
    settings_client: AsyncClient,
    super_admin_headers: dict[str, str],
) -> None:
    resp = await settings_client.patch(
        f"{_BASE}/features/advance_shift_enabled",
        json={},
        headers=super_admin_headers,
    )
    # 'enabled' field is required — Pydantic should reject
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_set_feature_401_no_token(settings_client: AsyncClient) -> None:
    resp = await settings_client.patch(
        f"{_BASE}/features/advance_shift_enabled", json={"enabled": True}
    )
    assert resp.status_code == 401
