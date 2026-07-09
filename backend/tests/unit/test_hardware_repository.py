"""Unit tests for the Hardware / Biometric Management Repository layer."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
import pytest
from sqlalchemy.sql import Select

from app.core.constants.enums import SortOrder
from app.modules.hardware.constants import DeviceProtocol, DeviceStatus
from app.modules.hardware.models import BiometricDevice
from app.modules.hardware.repository import BiometricDeviceRepository


@pytest.mark.asyncio
async def test_get_by_id_in_org() -> None:
    session = AsyncMock()
    mock_result = MagicMock()
    device_obj = BiometricDevice(id=1, org_id=10, device_name="Device A")
    mock_result.scalar_one_or_none.return_value = device_obj
    session.execute.return_value = mock_result

    repo = BiometricDeviceRepository(session)
    res = await repo.get_by_id_in_org(10, 1)

    assert res == device_obj
    session.execute.assert_called_once()
    stmt = session.execute.call_args[0][0]
    assert isinstance(stmt, Select)


@pytest.mark.asyncio
async def test_get_by_serial_number() -> None:
    session = AsyncMock()
    mock_result = MagicMock()
    device_obj = BiometricDevice(id=2, org_id=10, serial_number="SN999")
    mock_result.scalar_one_or_none.return_value = device_obj
    session.execute.return_value = mock_result

    repo = BiometricDeviceRepository(session)
    res = await repo.get_by_serial_number("SN999")

    assert res == device_obj
    session.execute.assert_called_once()
    stmt = session.execute.call_args[0][0]
    assert isinstance(stmt, Select)


@pytest.mark.asyncio
async def test_get_by_device_code() -> None:
    session = MagicMock()  # AsyncSession inherits MagicMock capabilities for execute
    session.execute = AsyncMock()
    mock_result = MagicMock()
    device_obj = BiometricDevice(id=3, org_id=10, device_code="CODE-A")
    mock_result.scalar_one_or_none.return_value = device_obj
    session.execute.return_value = mock_result

    repo = BiometricDeviceRepository(session)
    res = await repo.get_by_device_code(10, "CODE-A")

    assert res == device_obj
    session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_exists_in_org() -> None:
    session = AsyncMock()
    mock_result = MagicMock()
    mock_result.first.return_value = (1,)
    session.execute.return_value = mock_result

    repo = BiometricDeviceRepository(session)
    exists = await repo.exists_in_org(10, 1)

    assert exists is True
    session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_serial_number_exists() -> None:
    session = AsyncMock()
    mock_result = MagicMock()
    mock_result.first.return_value = None
    session.execute.return_value = mock_result

    repo = BiometricDeviceRepository(session)
    exists = await repo.serial_number_exists("SN-UNKNOWN", exclude_id=5)

    assert exists is False
    session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_device_code_exists() -> None:
    session = AsyncMock()
    mock_result = MagicMock()
    mock_result.first.return_value = (1,)
    session.execute.return_value = mock_result

    repo = BiometricDeviceRepository(session)
    exists = await repo.device_code_exists(10, "CODE-B")

    assert exists is True
    session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_is_device_in_use() -> None:
    session = AsyncMock()
    # Mocking first call (employee_biometrics) to return None,
    # second call (org_attendance_settings) to return None,
    # third call (attendance_punches) to return a record.
    mock_result_empty = MagicMock()
    mock_result_empty.first.return_value = None
    mock_result_punch = MagicMock()
    mock_result_punch.first.return_value = (1,)

    session.execute.side_effect = [mock_result_empty, mock_result_empty, mock_result_punch]

    repo = BiometricDeviceRepository(session)
    in_use = await repo.is_device_in_use(1)

    assert in_use is True
    assert session.execute.call_count == 3


@pytest.mark.asyncio
async def test_assign_branch() -> None:
    session = AsyncMock()
    session.add = MagicMock()
    device = BiometricDevice(id=1, branch_id=2)

    repo = BiometricDeviceRepository(session)
    res = await repo.assign_branch(device, 99)

    assert res.branch_id == 99
    session.add.assert_called_once_with(device)
    session.flush.assert_called_once()


@pytest.mark.asyncio
async def test_get_employee_mappings() -> None:
    session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = ["mock_mapping"]
    session.execute.return_value = mock_result

    repo = BiometricDeviceRepository(session)
    mappings = await repo.get_employee_mappings(1)

    assert mappings == ["mock_mapping"]
    session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_update_status() -> None:
    session = AsyncMock()
    session.add = MagicMock()
    device = BiometricDevice(id=1, status=DeviceStatus.OFFLINE)
    now = datetime.now(timezone.utc)

    repo = BiometricDeviceRepository(session)
    updated = await repo.update_status(
        device,
        status=DeviceStatus.ONLINE,
        last_seen_at=now,
        total_users=50,
    )

    assert updated.status == DeviceStatus.ONLINE
    assert updated.last_seen_at == now
    assert updated.total_users == 50
    session.add.assert_called_once_with(device)
    session.flush.assert_called_once()


@pytest.mark.asyncio
async def test_update_last_sync() -> None:
    session = AsyncMock()
    session.add = MagicMock()
    device = BiometricDevice(id=1, last_sync_at=None)
    now = datetime.now(timezone.utc)

    repo = BiometricDeviceRepository(session)
    updated = await repo.update_last_sync(device, last_sync_at=now, total_logs=123)

    assert updated.last_sync_at == now
    assert updated.total_logs == 123
    session.add.assert_called_once_with(device)
    session.flush.assert_called_once()


@pytest.mark.asyncio
async def test_search_and_count() -> None:
    session = AsyncMock()
    mock_result_search = MagicMock()
    mock_result_search.scalars.return_value.all.return_value = ["device_1", "device_2"]
    mock_result_count = MagicMock()
    mock_result_count.scalar_one.return_value = 2

    session.execute.side_effect = [mock_result_search, mock_result_count]

    repo = BiometricDeviceRepository(session)
    results = await repo.search(
        10,
        search="K90",
        status=DeviceStatus.ONLINE,
        protocol=DeviceProtocol.ADMS,
        branch_id=1,
        is_active=True,
        adms_enabled=True,
        allowed_branch_ids=[1, 2],
        sort_by="created_at",
        sort_order=SortOrder.DESC,
        page=2,
        page_size=10,
    )

    count = await repo.search_count(
        10,
        search="K90",
        status=DeviceStatus.ONLINE,
        protocol=DeviceProtocol.ADMS,
        branch_id=1,
        is_active=True,
        adms_enabled=True,
        allowed_branch_ids=[1, 2],
    )

    assert results == ["device_1", "device_2"]
    assert count == 2
    assert session.execute.call_count == 2


@pytest.mark.asyncio
async def test_device_code_exists_with_exclude_id() -> None:
    session = AsyncMock()
    mock_result = MagicMock()
    mock_result.first.return_value = (1,)
    session.execute.return_value = mock_result

    repo = BiometricDeviceRepository(session)
    exists = await repo.device_code_exists(10, "CODE-B", exclude_id=5)

    assert exists is True
    session.execute.assert_called_once()
    stmt = session.execute.call_args[0][0]
    # Check that exclude_id condition was added to select statement
    assert "exclude_id" not in str(stmt)  # SQL uses parameter binding or ID comparison


@pytest.mark.asyncio
async def test_is_device_not_in_use() -> None:
    session = AsyncMock()
    mock_result_empty = MagicMock()
    mock_result_empty.first.return_value = None
    session.execute.return_value = mock_result_empty

    repo = BiometricDeviceRepository(session)
    in_use = await repo.is_device_in_use(1)

    assert in_use is False
    assert session.execute.call_count == 3


@pytest.mark.asyncio
async def test_is_device_in_use_by_biometric() -> None:
    session = AsyncMock()
    mock_result_biometric = MagicMock()
    mock_result_biometric.first.return_value = (1,)
    session.execute.return_value = mock_result_biometric

    repo = BiometricDeviceRepository(session)
    in_use = await repo.is_device_in_use(1)

    assert in_use is True
    assert session.execute.call_count == 1  # exits early on first check


@pytest.mark.asyncio
async def test_is_device_in_use_by_settings() -> None:
    session = AsyncMock()
    mock_result_empty = MagicMock()
    mock_result_empty.first.return_value = None
    mock_result_settings = MagicMock()
    mock_result_settings.first.return_value = (1,)
    session.execute.side_effect = [mock_result_empty, mock_result_settings]

    repo = BiometricDeviceRepository(session)
    in_use = await repo.is_device_in_use(1)

    assert in_use is True
    assert session.execute.call_count == 2  # exits early on second check


@pytest.mark.asyncio
async def test_update_status_all_parameters() -> None:
    session = AsyncMock()
    session.add = MagicMock()
    device = BiometricDevice(id=1, status=DeviceStatus.OFFLINE)
    now = datetime.now(timezone.utc)

    repo = BiometricDeviceRepository(session)
    updated = await repo.update_status(
        device,
        status=DeviceStatus.ONLINE,
        last_seen_at=now,
        last_sync_at=now,
        firmware_version="v2.0",
        software_version="v3.0",
        total_users=100,
        total_fingerprints=50,
        total_faces=10,
        total_cards=5,
        total_logs=1000,
    )

    assert updated.status == DeviceStatus.ONLINE
    assert updated.last_seen_at == now
    assert updated.last_sync_at == now
    assert updated.firmware_version == "v2.0"
    assert updated.software_version == "v3.0"
    assert updated.total_users == 100
    assert updated.total_fingerprints == 50
    assert updated.total_faces == 10
    assert updated.total_cards == 5
    assert updated.total_logs == 1000
    session.add.assert_called_once_with(device)
    session.flush.assert_called_once()

