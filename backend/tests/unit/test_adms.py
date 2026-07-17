"""Unit tests for ADMS (iClock) module."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.sql import Select

from app.modules.adms.parser import parse_adms_post_body, parse_device_info
from app.modules.adms.repository import ADMSRepository
from app.modules.adms.service import ADMSService
from app.modules.hardware.constants import DeviceProtocol, DeviceStatus
from app.modules.hardware.models import BiometricDevice


def test_parser_post_body() -> None:
    body = "SN=123\tName=Main\tIP=192.168.1.1\nSN=456\tName=Office\n"
    records = parse_adms_post_body(body)
    assert len(records) == 2
    assert records[0]["SN"] == "123"
    assert records[0]["Name"] == "Main"
    assert records[1]["SN"] == "456"


def test_parser_device_info() -> None:
    query = {"SN": "SN12345", "ClientIP": "10.0.0.5", "pushver": "3.1.1", "Platform": "ZEM560"}
    headers = {"user-agent": "iClock Reader"}
    info = parse_device_info(query, headers, client_ip="127.0.0.1")
    assert info["serial_number"] == "SN12345"
    assert info["ip_address"] == "10.0.0.5"
    assert info["firmware_version"] == "3.1.1"
    assert info["platform"] == "ZEM560"
    assert info["device_name"] == "ADMS Device SN12345"


@pytest.mark.asyncio
async def test_repo_get_by_serial_number() -> None:
    session = AsyncMock()
    mock_result = MagicMock()
    device = BiometricDevice(id=1, serial_number="SN123")
    mock_result.scalar_one_or_none.return_value = device
    session.execute.return_value = mock_result

    repo = ADMSRepository(session)
    res = await repo.get_by_serial_number("SN123")
    assert res == device
    session.execute.assert_called_once()
    stmt = session.execute.call_args[0][0]
    assert isinstance(stmt, Select)


@pytest.mark.asyncio
async def test_service_register_new_device() -> None:
    session = AsyncMock()
    service = ADMSService(session)
    service.repository = AsyncMock()
    service.repository.get_by_serial_number.return_value = None
    service.repository.get_first_active_org_id.return_value = 10

    created_device = BiometricDevice(id=5, serial_number="SN123", org_id=10)
    service.repository.create.return_value = created_device

    info = {
        "serial_number": "SN123",
        "ip_address": "192.168.1.10",
        "firmware_version": "1.0",
        "platform": "K90",
    }
    res = await service.register_or_update_device(info)
    assert res == created_device
    service.repository.create.assert_called_once()
    create_data = service.repository.create.call_args[0][0]
    assert create_data["org_id"] == 10
    assert create_data["serial_number"] == "SN123"
    assert create_data["protocol"] == DeviceProtocol.ADMS
    assert create_data["status"] == DeviceStatus.ONLINE


@pytest.mark.asyncio
async def test_service_update_existing_device() -> None:
    session = AsyncMock()
    service = ADMSService(session)
    service.repository = AsyncMock()

    existing_device = BiometricDevice(
        id=5, serial_number="SN123", org_id=10, status=DeviceStatus.OFFLINE
    )
    service.repository.get_by_serial_number.return_value = existing_device
    service.repository.update.return_value = existing_device

    info = {
        "serial_number": "SN123",
        "ip_address": "192.168.1.20",
        "firmware_version": "2.0",
        "platform": "K90-Pro",
    }
    res = await service.register_or_update_device(info)
    assert res == existing_device
    service.repository.update.assert_called_once()
    device_arg, update_data = service.repository.update.call_args[0]
    assert device_arg == existing_device
    assert update_data["status"] == DeviceStatus.ONLINE
    assert update_data["ip_address"] == "192.168.1.20"
    assert update_data["firmware_version"] == "2.0"
    assert update_data["model"] == "K90-Pro"


def test_parser_attendance_payload() -> None:
    from app.modules.adms.parser import parse_attendance_payload
    body = (
        "#TAB:ATTLOG\r\n"
        "1001\t2026-07-17 10:15:30\t0\t1\t0\t0\t0\r\n"
        "1002\t2026-07-17 10:16:45\t1\t4\t0\t0\t0\r\n"
    )
    records = parse_attendance_payload(body)
    assert len(records) == 2
    assert records[0]["pin"] == "1001"
    assert records[0]["time_str"] == "2026-07-17 10:15:30"
    assert records[0]["status"] == "0"
    assert records[0]["verify_type"] == "1"
    assert records[0]["raw_line"] == "1001\t2026-07-17 10:15:30\t0\t1\t0\t0\t0"
    assert records[1]["pin"] == "1002"
    assert records[1]["time_str"] == "2026-07-17 10:16:45"
    assert records[1]["status"] == "1"
    assert records[1]["verify_type"] == "4"


from unittest.mock import patch

@pytest.mark.asyncio
async def test_service_handle_cdata_post_attlog() -> None:
    from app.modules.employee.models.employee import Employee
    from app.modules.attendance.models import AttendanceDay, AttendancePunch

    session = AsyncMock()
    # Configure begin_nested (synchronous mock returning async context manager)
    session.begin_nested = MagicMock()
    async_ctx = AsyncMock()
    async_ctx.__aenter__ = AsyncMock()
    async_ctx.__aexit__ = AsyncMock()
    session.begin_nested.return_value = async_ctx
    
    service = ADMSService(session)
    service.repository = AsyncMock()

    device = BiometricDevice(
        id=5, serial_number="SN123", org_id=10, status=DeviceStatus.ONLINE, timezone="UTC", total_logs=0
    )
    service.repository.get_by_serial_number.return_value = device
    service.repository.update.return_value = device

    # Mock employee resolution execute results
    mock_employee = Employee(employee_id=101, employee_code="1001", org_id=10, master_branch_id=1)
    mock_result_employee = MagicMock()
    mock_result_employee.scalar_one_or_none.side_effect = [
        mock_employee,  # First call resolves employee
        None,           # Second call resolves duplicate punch (returns None, i.e., no duplicate)
    ]
    session.execute.return_value = mock_result_employee

    payload = "1001\t2026-07-17 10:15:30\t0\t1\t0\t0\t0\r\n"

    with patch("app.modules.attendance.service.AttendanceService") as mock_att_service_class:
        mock_att_service = mock_att_service_class.return_value
        mock_att_service.locks.is_locked = AsyncMock(return_value=False)
        
        mock_day = AttendanceDay(id=20, org_id=10, employee_id=101)
        mock_att_service.days.get_by_employee_date = AsyncMock(return_value=mock_day)
        mock_att_service.punches.get_for_day = AsyncMock(return_value=[])
        mock_att_service.punches.create = AsyncMock()
        mock_att_service._recompute_day_metrics = AsyncMock()

        res = await service.handle_cdata_post(
            sn="SN123", table="ATTLOG", payload=payload, client_ip="192.168.1.50"
        )

        assert res == "OK"
        service.repository.get_by_serial_number.assert_called_once_with("SN123")
        mock_att_service.locks.is_locked.assert_called_once_with(
            org_id=10, month=7, year=2026, branch_id=1
        )
        mock_att_service.punches.create.assert_called_once()
        mock_att_service._recompute_day_metrics.assert_called_once_with(10, mock_day)
        session.commit.assert_called_once()
        assert service.repository.update.call_count == 2
        assert service.repository.update.call_args_list[-1][0][0] == device
        assert service.repository.update.call_args_list[-1][0][1] == {"total_logs": 1}


def test_parser_device_stats() -> None:
    from app.modules.adms.parser import parse_device_stats
    info_str = "UserCount=25,FPCount=50,FaceCount=10,CardCount=15"
    stats = parse_device_stats(info_str)
    assert stats["total_users"] == 25
    assert stats["total_fingerprints"] == 50
    assert stats["total_faces"] == 10
    assert stats["total_cards"] == 15


def test_parser_device_command_ack() -> None:
    from app.modules.adms.parser import parse_device_command_ack
    payload = "ID=999&Return=0&CMD=INFO\nID=1000&Return=-1&CMD=REBOOT"
    acks = parse_device_command_ack(payload)
    assert len(acks) == 2
    assert acks[0]["ID"] == "999"
    assert acks[0]["Return"] == "0"
    assert acks[0]["CMD"] == "INFO"
    assert acks[1]["ID"] == "1000"
    assert acks[1]["Return"] == "-1"
    assert acks[1]["CMD"] == "REBOOT"


@pytest.mark.asyncio
async def test_service_handle_getrequest_stats() -> None:
    session = AsyncMock()
    service = ADMSService(session)
    service.repository = AsyncMock()

    device = BiometricDevice(
        id=5, serial_number="SN123", org_id=10, status=DeviceStatus.ONLINE, timezone="UTC"
    )
    service.repository.get_by_serial_number.return_value = device
    service.repository.update.return_value = device

    info_str = "UserCount=50,FPCount=100"
    res = await service.handle_getrequest(sn="SN123", info_str=info_str, client_ip="192.168.1.50")
    
    assert res == "OK"
    assert service.repository.update.call_count == 2
    # Second call should update statistics
    assert service.repository.update.call_args_list[-1][0][1] == {
        "total_users": 50,
        "total_fingerprints": 100,
    }
    session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_service_handle_devicecmd_post_ack() -> None:
    session = AsyncMock()
    service = ADMSService(session)
    service.repository = AsyncMock()

    device = BiometricDevice(
        id=5, serial_number="SN123", org_id=10, status=DeviceStatus.ONLINE, timezone="UTC"
    )
    service.repository.get_by_serial_number.return_value = device
    service.repository.update.return_value = device

    payload = "ID=101&Return=0"
    res = await service.handle_devicecmd_post(sn="SN123", payload=payload, client_ip="192.168.1.50")
    
    assert res == "OK"
    service.repository.get_by_serial_number.assert_called_once_with("SN123")
    # First and only repository.update call is for the registration/heartbeat (inside register_or_update_device)
    assert service.repository.update.call_count == 1
    session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_service_handle_cdata_get_config() -> None:
    session = AsyncMock()
    service = ADMSService(session)
    service.repository = AsyncMock()

    device = BiometricDevice(
        id=5, serial_number="SN123", org_id=10, status=DeviceStatus.ONLINE, timezone="UTC"
    )
    service.repository.get_by_serial_number.return_value = device
    service.repository.update.return_value = device

    query = {"SN": "SN123", "options": "all"}
    res = await service.handle_cdata_get(query_params=query, headers={}, client_ip="192.168.1.50")
    
    assert "RegistryCode=OK" in res
    assert "Realtime=1" in res
    assert "TransFlag=1111111111" in res
    service.repository.get_by_serial_number.assert_called_once_with("SN123")
    session.commit.assert_called_once()
