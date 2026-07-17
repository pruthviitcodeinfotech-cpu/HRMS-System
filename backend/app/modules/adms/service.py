"""ADMS (iClock) integration service."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.modules.adms.constants import ADMS_RESPONSE_OK
from app.modules.adms.parser import parse_device_info
from app.modules.adms.repository import ADMSRepository
from app.modules.hardware.constants import DeviceProtocol, DeviceStatus
from app.modules.hardware.models import BiometricDevice
from app.shared.base.service import BaseService

_logger = get_logger("adms_service")


class ADMSService(BaseService):
    """Service class handling ADMS protocol registration and handshake workflows."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db)
        self.repository = ADMSRepository(db)

    async def register_or_update_device(self, info: dict[str, Any]) -> BiometricDevice:
        """Register a new device or update an existing device's heartbeat and status."""
        sn = info.get("serial_number")
        if not sn:
            raise ValueError("Serial number is required for device registration.")

        now = datetime.now(UTC)
        device = await self.repository.get_by_serial_number(sn)

        if device:
            # Device exists: update Last Seen, Heartbeat, and Mark Online
            update_data = {
                "last_seen_at": now,
                "status": DeviceStatus.ONLINE,
            }
            if info.get("ip_address"):
                update_data["ip_address"] = info["ip_address"]
            if info.get("firmware_version"):
                update_data["firmware_version"] = info["firmware_version"]
            if info.get("platform"):
                update_data["model"] = info["platform"]

            device = await self.repository.update(device, update_data)
            _logger.info("adms_device_heartbeat_updated", serial_number=sn, device_id=device.id)
        else:
            # Device does not exist: register it automatically
            org_id = await self.repository.get_first_active_org_id()
            if not org_id:
                # Default fallback org_id if none exists in the DB
                org_id = 1

            create_data = {
                "org_id": org_id,
                "device_name": info.get("device_name") or f"ADMS Device {sn}",
                "device_code": f"ADMS_{sn}",
                "serial_number": sn,
                "ip_address": info.get("ip_address"),
                "protocol": DeviceProtocol.ADMS,
                "status": DeviceStatus.ONLINE,
                "adms_enabled": True,
                "is_active": True,
                "last_seen_at": now,
                "firmware_version": info.get("firmware_version"),
                "model": info.get("platform"),
                "total_users": 0,
                "total_fingerprints": 0,
                "total_faces": 0,
                "total_cards": 0,
                "total_logs": 0,
            }
            device = await self.repository.create(create_data)
            _logger.info("adms_device_auto_registered", serial_number=sn, device_id=device.id)

        return device

    async def handle_cdata_get(
        self, query_params: dict[str, str], headers: dict[str, str], client_ip: str | None
    ) -> str:
        """Handle GET /iclock/cdata handshake and register/update the device."""
        info = parse_device_info(query_params, headers, client_ip)
        if info.get("serial_number"):
            await self.register_or_update_device(info)
            await self.commit()
        
        config_lines = [
            "RegistryCode=OK",
            "Delay=10",
            "ErrorDelay=30",
            "TransInterval=10",
            "TransTimes=00:00-23:59",
            "TransFlag=1111111111",
            "Realtime=1",
            "Encrypt=0",
        ]
        return "\r\n".join(config_lines) + "\r\n"

    async def handle_cdata_post(
        self, sn: str, table: str | None, payload: str, client_ip: str | None
    ) -> str:
        """Handle POST /iclock/cdata data upload and update device status/heartbeat."""
        _logger.info(
            "adms_cdata_post_request",
            serial_number=sn,
            table=table,
            payload_length=len(payload),
        )
        info = {"serial_number": sn, "ip_address": client_ip}
        device = await self.register_or_update_device(info)


        if table and table.upper() == "ATTLOG":
            from zoneinfo import ZoneInfo
            from sqlalchemy import select, or_, func, cast, Integer
            
            from app.modules.adms.parser import parse_attendance_payload
            from app.modules.attendance.constants import PunchSource, PunchType
            from app.modules.attendance.models import AttendancePunch
            from app.modules.attendance.service import AttendanceService
            from app.modules.employee.models.employee import Employee

            attendance_service = AttendanceService(self.session)
            records = parse_attendance_payload(payload)
            _logger.info("adms_cdata_post_parsed_records", serial_number=sn, count=len(records))

            tz_name = device.timezone or "UTC"
            try:
                device_tz = ZoneInfo(tz_name)
            except Exception:
                device_tz = ZoneInfo("UTC")

            inserted_count = 0
            for record in records:
                pin = record["pin"]
                time_str = record["time_str"]
                status = record["status"]
                verify_type = record["verify_type"]
                raw_line = record["raw_line"]

                try:
                    # 1. Parse timestamp
                    try:
                        naive_dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        _logger.warning("adms_punch_invalid_time_format", serial_number=sn, time_str=time_str)
                        continue

                    # Localize to device's timezone
                    local_dt = naive_dt.replace(tzinfo=device_tz)
                    punch_date = local_dt.date()

                    # 2. Resolve employee in device's organization
                    stmt = select(Employee).where(
                        Employee.org_id == device.org_id,
                        Employee.is_deleted.is_(False)
                    )
                    if pin.isdigit():
                        pin_int = int(pin)
                        numeric_part = func.regexp_replace(Employee.employee_code, r'\D', '', 'g')
                        safe_numeric_part = func.nullif(numeric_part, '')
                        cast_numeric_part = func.cast(safe_numeric_part, Integer)
                        stmt = stmt.where(
                            or_(
                                Employee.employee_code == pin,
                                Employee.employee_id == pin_int,
                                cast_numeric_part == pin_int
                            )
                        )
                    else:
                        stmt = stmt.where(Employee.employee_code == pin)

                    employee = (await self.session.execute(stmt)).scalar_one_or_none()

                    if not employee:
                        _logger.warning("adms_punch_employee_not_found", serial_number=sn, pin=pin)
                        continue

                    # 3. Check period lock
                    is_locked = await attendance_service.locks.is_locked(
                        org_id=device.org_id,
                        month=punch_date.month,
                        year=punch_date.year,
                        branch_id=employee.master_branch_id
                    )
                    if is_locked:
                        _logger.warning("adms_punch_rejected_period_locked", serial_number=sn, pin=pin, punch_time=local_dt)
                        continue

                    # 4. Map punch type status
                    # Standard ZK status: 0=Check-In, 1=Check-Out, 2=Break-Out, 3=Break-In, 4=Overtime-In, 5=Overtime-Out
                    if status in ("0", "4"):
                        punch_type_val = PunchType.IN.value
                    elif status in ("1", "5"):
                        punch_type_val = PunchType.OUT.value
                    elif status == "2":
                        punch_type_val = PunchType.BREAK_OUT.value
                    elif status == "3":
                        punch_type_val = PunchType.BREAK_IN.value
                    else:
                        punch_type_val = PunchType.IN.value

                    # 5. Check if punch already exists (avoid duplicates)
                    stmt = select(AttendancePunch).where(
                        AttendancePunch.org_id == device.org_id,
                        AttendancePunch.employee_id == employee.employee_id,
                        AttendancePunch.punch_time == local_dt,
                        AttendancePunch.punch_type == punch_type_val,
                    )
                    existing_punch = (await self.session.execute(stmt)).scalar_one_or_none()
                    if existing_punch:
                        _logger.info("adms_punch_duplicate_ignored", serial_number=sn, pin=pin, punch_time=local_dt)
                        continue

                    # 6. Map verify type to human readable verification mode
                    # Verify types: 1=Fingerprint, 3=Password, 4=Card, 15=Face, etc.
                    if verify_type == "1":
                        v_mode = "Fingerprint"
                    elif verify_type == "3":
                        v_mode = "Password"
                    elif verify_type == "4":
                        v_mode = "Card"
                    elif verify_type == "15":
                        v_mode = "Face"
                    else:
                        v_mode = f"Biometric / Other ({verify_type})"

                    # Use nested transaction savepoint to isolate DB failures per punch
                    async with self.session.begin_nested():
                        # Get or create AttendanceDay record
                        day = await attendance_service.days.get_by_employee_date(
                            device.org_id, employee.employee_id, punch_date
                        )
                        if not day:
                            from app.modules.shift.schemas import ShiftResolveQuery
                            from app.modules.shift.service import ShiftService
                            
                            shift_id = None
                            expected_start = None
                            expected_end = None
                            try:
                                shift_resolve = await ShiftService(self.session).resolve_shift(
                                    org_id=device.org_id,
                                    query=ShiftResolveQuery(employee_id=employee.employee_id, date=punch_date),
                                )
                                if shift_resolve.shift:
                                    shift_id = shift_resolve.shift.shift_id
                                    shift_detail = await attendance_service.shifts.get_active_by_id(shift_id, device.org_id)
                                    if shift_detail:
                                        weekday = (punch_date.weekday() + 1) % 7
                                        timing = next(
                                            (t for t in shift_detail.day_timings if t.day_of_week == weekday), None
                                        )
                                        if not timing:
                                            timing = next(
                                                (t for t in shift_detail.day_timings if t.day_of_week is None), None
                                            )
                                        if timing:
                                            expected_start = timing.start_time
                                            expected_end = timing.end_time
                            except Exception as e:
                                _logger.warning("adms_shift_resolution_failed", employee_id=employee.employee_id, date=punch_date, error=str(e))

                            from app.modules.attendance.constants import AttendanceDayStatus, AttendanceSource
                            day = await attendance_service.days.create({
                                "org_id": device.org_id,
                                "employee_id": employee.employee_id,
                                "attendance_date": punch_date,
                                "shift_id": shift_id,
                                "expected_start_time": expected_start,
                                "expected_end_time": expected_end,
                                "status": AttendanceDayStatus.NOT_MARKED.value,
                                "source": AttendanceSource.SYSTEM.value,
                            })

                        # Find sequence number
                        existing_punches = await attendance_service.punches.get_for_day(device.org_id, day.id)
                        seq_no = len(existing_punches) + 1

                        # Create the punch
                        await attendance_service.punches.create({
                            "org_id": device.org_id,
                            "employee_id": employee.employee_id,
                            "attendance_day_id": day.id,
                            "punch_type": punch_type_val,
                            "punch_time": local_dt,
                            "sequence_no": seq_no,
                            "punch_source": PunchSource.BIOMETRIC_DEVICE.value,
                            "device_id": device.id,
                            "verification_mode": v_mode,
                            "raw_payload": raw_line,
                            "is_valid": True,
                        })

                        # Recompute daily metrics
                        await attendance_service._recompute_day_metrics(device.org_id, day)
                        inserted_count += 1

                except Exception as e:
                    _logger.error("adms_punch_processing_error", serial_number=sn, pin=pin, error=str(e))
                    continue

            # Update the device total logs statistic
            if inserted_count > 0:
                await self.repository.update(device, {"total_logs": (device.total_logs or 0) + inserted_count})
            
            await self.commit()
            _logger.info("adms_cdata_post_success", serial_number=sn, total=len(records), processed=inserted_count)

        return ADMS_RESPONSE_OK

    async def handle_getrequest(self, sn: str, info_str: str | None, client_ip: str | None) -> str:
        """Handle GET /iclock/getrequest and update device status/heartbeat."""
        _logger.info("adms_getrequest", serial_number=sn, info=info_str)
        
        from app.modules.adms.parser import parse_device_stats
        stats = parse_device_stats(info_str)
        
        info = {"serial_number": sn, "ip_address": client_ip}
        device = await self.register_or_update_device(info)
        
        if stats:
            await self.repository.update(device, stats)
            _logger.info("adms_device_stats_updated", serial_number=sn, stats=stats)
            
        await self.commit()
        return ADMS_RESPONSE_OK

    async def handle_devicecmd_post(self, sn: str, payload: str, client_ip: str | None) -> str:
        """Handle POST /iclock/devicecmd and update device status/heartbeat."""
        _logger.info("adms_devicecmd_post", serial_number=sn, payload_length=len(payload))
        
        from app.modules.adms.parser import parse_device_command_ack
        acks = parse_device_command_ack(payload)
        
        info = {"serial_number": sn, "ip_address": client_ip}
        await self.register_or_update_device(info)
        
        for ack in acks:
            cmd_id = ack.get("ID")
            return_code = ack.get("Return")
            _logger.info(
                "adms_device_command_ack_received",
                serial_number=sn,
                command_id=cmd_id,
                return_code=return_code,
                ack=ack,
            )
            
        await self.commit()
        return ADMS_RESPONSE_OK
