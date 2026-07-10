"""Unit tests for the Settings Management Pydantic request-schema validation."""

from __future__ import annotations

import datetime

import pytest
from pydantic import ValidationError

from app.modules.settings.schemas import (
    ConfigurationViewResponse,
    FeaturesResponse,
    FeatureToggleRequest,
    ModulePointerSchema,
    OrgSalarySlipResponse,
    OrgSalarySlipUpdateRequest,
    OrgSettingsResponse,
    OrgSettingsUpdateRequest,
)


def test_org_settings_response_masking() -> None:
    now = datetime.datetime.now(datetime.timezone.utc)  # noqa: UP017
    res = OrgSettingsResponse(
        id=1,
        org_id=10,
        advance_shift_enabled=True,
        enable_regularization=True,
        enable_photo_punch=False,
        device_sync_time=datetime.time(16, 51, 0),
        sync_code="SYNC123",
        pass_code="PASS456",
        updated_by=42,
        created_at=now,
        updated_at=now,
    )
    assert res.id == 1
    assert res.org_id == 10
    assert res.advance_shift_enabled is True
    assert res.enable_photo_punch is False
    assert res.pass_code == "********"  # Masked!


def test_org_settings_update_request_valid() -> None:
    req = OrgSettingsUpdateRequest(
        advance_shift_enabled=False,
        enable_regularization=True,
        device_sync_time="12:30:00",
        sync_code="NEW_SYNC",
    )
    assert req.advance_shift_enabled is False
    assert req.enable_regularization is True
    assert req.device_sync_time == datetime.time(12, 30, 0)
    assert req.sync_code == "NEW_SYNC"


def test_org_salary_slip_response_valid() -> None:
    now = datetime.datetime.now(datetime.timezone.utc)  # noqa: UP017
    res = OrgSalarySlipResponse(
        id=1,
        org_id=10,
        company_logo_url="https://logo.com/img.png",
        company_name="Test Company",
        company_address="123 Main St",
        company_contact="123456789",
        company_website_email="info@test.com",
        auto_release_payslip=True,
        branch_wise_payslip=False,
        updated_by=None,
        created_at=now,
        updated_at=now,
    )
    assert res.company_name == "Test Company"
    assert res.company_website_email == "info@test.com"


def test_org_salary_slip_update_email_validation() -> None:
    # Valid email
    req1 = OrgSalarySlipUpdateRequest(company_website_email="SUPPORT@TEST.COM")
    assert req1.company_website_email == "support@test.com"

    # Valid non-email URL (passes through without @ validation)
    req2 = OrgSalarySlipUpdateRequest(company_website_email="https://test.com")
    assert req2.company_website_email == "https://test.com"

    # Invalid email format (contains @ but fails validation)
    with pytest.raises(ValidationError, match="invalid email format"):
        OrgSalarySlipUpdateRequest(company_website_email="invalid@email@format")


def test_configuration_view_response_valid() -> None:
    now = datetime.datetime.now(datetime.timezone.utc)  # noqa: UP017
    org_res = OrgSettingsResponse(
        id=1,
        org_id=10,
        advance_shift_enabled=True,
        enable_regularization=True,
        enable_photo_punch=False,
        device_sync_time=datetime.time(16, 51, 0),
        sync_code="SYNC123",
        pass_code="PASS456",
        updated_by=42,
        created_at=now,
        updated_at=now,
    )
    salary_res = OrgSalarySlipResponse(
        id=1,
        org_id=10,
        company_logo_url=None,
        company_name="Test Company",
        company_address="123 Main St",
        company_contact="123456789",
        company_website_email=None,
        auto_release_payslip=True,
        branch_wise_payslip=False,
        updated_by=None,
        created_at=now,
        updated_at=now,
    )
    view = ConfigurationViewResponse(
        organization=org_res,
        salary_slip=salary_res,
        cross_module_pointers={
            "leave": ModulePointerSchema(module="leave", description="Managed by Leave module.")
        },
    )
    assert view.organization == org_res
    assert view.salary_slip == salary_res
    assert view.cross_module_pointers["leave"].module == "leave"


def test_features_response_and_request() -> None:
    res = FeaturesResponse(features={"advance_shift_enabled": True})
    assert res.features["advance_shift_enabled"] is True

    req = FeatureToggleRequest(enabled=False)
    assert req.enabled is False
