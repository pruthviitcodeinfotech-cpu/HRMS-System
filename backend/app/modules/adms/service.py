"""ADMS (iClock) integration service."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.modules.adms.constants import ADMS_RESPONSE_OK
from app.modules.adms.parser import parse_device_info
from app.modules.adms.repository import ADMSRepository
from app.modules.hardware.constants import DeviceProtocol, DeviceStatus
from app.modules.hardware.models import BiometricDevice
from app.shared.base.service import BaseService

import logging
import json

_logger = get_logger("adms_service")

file_logger = logging.getLogger("adms_file_debug")
if not file_logger.handlers:
    _fh = logging.FileHandler("/home/jignesh/Desktop/PAYROLL/backend/adms_debug.log")
    _fh.setFormatter(logging.Formatter("%(asctime)s | %(message)s"))
    file_logger.addHandler(_fh)
    file_logger.setLevel(logging.INFO)

def log_adms_event(event: str, **kwargs: Any) -> None:
    try:
        file_logger.info(f"EVENT: {event} | " + json.dumps(kwargs, default=str))
    except Exception:
        pass


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

        now = datetime.now(timezone.utc)
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

    async def resolve_employee_for_adms_pin(
        self, org_id: int, pin: str, device_sn: str
    ) -> tuple[Employee | None, str | None]:
        """Resolve employee using 4-priority cascade without MultipleResultsFound.
        
        Priority 1: Exact employee_code match (e.g. EMP001 or 1)
        Priority 2: Configured biometric_device_user_id / employee_uid match
        Priority 3: Numeric employee_code suffix match (e.g. PIN=1 matches EMP001 / EMP-001)
        Priority 4: employee_id match (primary key)
        """
        from sqlalchemy import select, func, cast, Integer, case
        from app.modules.employee.models.employee import Employee

        _logger.info(
            "adms_employee_lookup_started",
            serial_number=device_sn,
            pin=pin,
            org_id=org_id,
        )

        clean_pin = pin.strip()
        if not clean_pin:
            _logger.warning(
                "adms_employee_lookup_failed",
                serial_number=device_sn,
                pin=pin,
                reason="employee_not_found",
            )
            return None, None

        # Priority 1: Exact employee_code match
        stmt1 = select(Employee).where(
            Employee.org_id == org_id,
            Employee.is_deleted.is_(False),
            Employee.employee_code == clean_pin,
        ).order_by(Employee.employee_id.asc())

        emp = (await self.session.execute(stmt1)).scalars().first()
        if emp:
            _logger.info(
                "adms_employee_lookup_success",
                serial_number=device_sn,
                pin=pin,
                matched_employee_id=emp.employee_id,
                matched_employee_code=emp.employee_code,
                strategy_used="exact_code",
            )
            return emp, "exact_code"

        # Priority 2: Configured biometric_device_user_id / employee_uid match
        stmt2 = select(Employee).where(
            Employee.org_id == org_id,
            Employee.is_deleted.is_(False),
            Employee.employee_uid == clean_pin,
        ).order_by(Employee.employee_id.asc())

        emp = (await self.session.execute(stmt2)).scalars().first()
        if emp:
            _logger.info(
                "adms_employee_lookup_success",
                serial_number=device_sn,
                pin=pin,
                matched_employee_id=emp.employee_id,
                matched_employee_code=emp.employee_code,
                strategy_used="biometric_user_id",
            )
            return emp, "biometric_user_id"

        # Numeric strategies (Priority 3 & Priority 4)
        if clean_pin.isdigit():
            pin_int = int(clean_pin)

            # Priority 3: Numeric employee_code suffix match (e.g., PIN=1 matches EMP001 / EMP-001)
            numeric_part = func.regexp_replace(Employee.employee_code, r'\D', '', 'g')
            safe_numeric_part = func.nullif(numeric_part, '')
            cast_numeric_part = func.cast(safe_numeric_part, Integer)

            stmt3 = select(Employee).where(
                Employee.org_id == org_id,
                Employee.is_deleted.is_(False),
                cast_numeric_part == pin_int,
            ).order_by(
                case((Employee.employment_status == 'active', 0), else_=1),
                Employee.employee_id.asc(),
            )

            emp = (await self.session.execute(stmt3)).scalars().first()
            if emp:
                _logger.info(
                    "adms_employee_lookup_success",
                    serial_number=device_sn,
                    pin=pin,
                    matched_employee_id=emp.employee_id,
                    matched_employee_code=emp.employee_code,
                    strategy_used="numeric_suffix",
                )
                return emp, "numeric_suffix"

            # Priority 4: Primary key employee_id match
            stmt4 = select(Employee).where(
                Employee.org_id == org_id,
                Employee.is_deleted.is_(False),
                Employee.employee_id == pin_int,
            ).order_by(
                case((Employee.employment_status == 'active', 0), else_=1),
                Employee.employee_id.asc(),
            )

            emp = (await self.session.execute(stmt4)).scalars().first()
            if emp:
                _logger.info(
                    "adms_employee_lookup_success",
                    serial_number=device_sn,
                    pin=pin,
                    matched_employee_id=emp.employee_id,
                    matched_employee_code=emp.employee_code,
                    strategy_used="employee_id",
                )
                return emp, "employee_id"

        _logger.warning(
            "adms_employee_lookup_failed",
            serial_number=device_sn,
            pin=pin,
            reason="employee_not_found",
        )
        return None, None

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
        log_adms_event("adms_cdata_post_request", serial_number=sn, table=table, payload_length=len(payload), payload_raw=payload)
        info = {"serial_number": sn, "ip_address": client_ip}
        try:
            async with self.session.begin_nested():
                device = await self.register_or_update_device(info)
        except Exception as dev_err:
            _logger.warning("adms_device_registration_warning", serial_number=sn, error=str(dev_err))
            device = await self.repository.get_by_serial_number(sn)
            if not device:
                raise


        if table and table.upper() == "ATTLOG":
            import traceback
            from zoneinfo import ZoneInfo
            from sqlalchemy import select
            
            from app.modules.adms.parser import parse_attendance_payload
            from app.modules.attendance.constants import PunchSource, PunchType
            from app.modules.attendance.models import AttendancePunch
            from app.modules.attendance.service import AttendanceService
            from app.modules.employee.models.employee import Employee

            _logger.info(
                "adms_raw_punch_received",
                serial_number=sn,
                table=table,
                payload_raw=payload,
                payload_length=len(payload),
            )
            log_adms_event("adms_raw_punch_received", serial_number=sn, table=table, payload_raw=payload)

            attendance_service = AttendanceService(self.session)
            records = parse_attendance_payload(payload)
            _logger.info(
                "adms_cdata_post_parsed_records",
                serial_number=sn,
                count=len(records),
                records=records,
            )
            log_adms_event("adms_cdata_post_parsed_records", serial_number=sn, count=len(records), records=records)

            tz_name = device.timezone or "Asia/Kolkata"
            try:
                device_tz = ZoneInfo(tz_name)
            except Exception:
                device_tz = ZoneInfo("Asia/Kolkata")

            inserted_count = 0
            for record in records:
                pin = record.get("pin", "")
                time_str = record.get("time_str", "")
                status = record.get("status", "0")
                verify_type = record.get("verify_type", "1")
                work_code = record.get("work_code", "0")
                raw_line = record.get("raw_line", "")

                _logger.info(
                    "adms_punch_parsed",
                    serial_number=sn,
                    pin=pin,
                    timestamp=time_str,
                    status=status,
                    verify_type=verify_type,
                    work_code=work_code,
                    raw_line=raw_line,
                )

                try:
                    # 1. Parse timestamp (normalize slashes e.g. 2026/07/30 -> 2026-07-30)
                    clean_time_str = time_str.replace("/", "-")
                    try:
                        naive_dt = datetime.strptime(clean_time_str, "%Y-%m-%d %H:%M:%S")
                    except ValueError as ve:
                        _logger.warning(
                            "adms_punch_skipped",
                            serial_number=sn,
                            pin=pin,
                            time_str=time_str,
                            reason="invalid_timestamp",
                            error_details=str(ve),
                        )
                        continue

                    # Localize to device's timezone and convert to true UTC for storage
                    local_dt = naive_dt.replace(tzinfo=device_tz)
                    punch_date = local_dt.date()
                    utc_dt = local_dt.astimezone(ZoneInfo("UTC"))

                    # 2. Resolve employee in device's organization using 4-priority cascade
                    employee, match_strategy = await self.resolve_employee_for_adms_pin(
                        org_id=device.org_id,
                        pin=pin,
                        device_sn=sn,
                    )

                    _logger.info(
                        "adms_employee_lookup_result",
                        serial_number=sn,
                        pin=pin,
                        matched=employee is not None,
                        employee_id=employee.employee_id if employee else None,
                        employee_code=employee.employee_code if employee else None,
                        strategy_used=match_strategy,
                    )
                    log_adms_event("adms_employee_lookup_result", serial_number=sn, pin=pin, matched=employee is not None, employee_id=employee.employee_id if employee else None, employee_code=employee.employee_code if employee else None, strategy_used=match_strategy)

                    if not employee:
                        _logger.warning(
                            "adms_punch_skipped",
                            serial_number=sn,
                            pin=pin,
                            time_str=time_str,
                            reason="employee_not_found",
                            error_details=f"No active employee matched PIN '{pin}' in org {device.org_id}",
                        )
                        log_adms_event("adms_punch_skipped", serial_number=sn, pin=pin, time_str=time_str, reason="employee_not_found", error_details=f"No active employee matched PIN '{pin}' in org {device.org_id}")
                        continue

                    # 3. Check period lock
                    is_locked = await attendance_service.locks.is_locked(
                        org_id=device.org_id,
                        month=punch_date.month,
                        year=punch_date.year,
                        branch_id=employee.master_branch_id
                    )

                    _logger.info(
                        "adms_period_lock_result",
                        serial_number=sn,
                        employee_id=employee.employee_id,
                        is_locked=is_locked,
                        month=punch_date.month,
                        year=punch_date.year,
                    )

                    if is_locked:
                        _logger.warning(
                            "adms_punch_skipped",
                            serial_number=sn,
                            pin=pin,
                            employee_id=employee.employee_id,
                            time_str=time_str,
                            reason="attendance_locked",
                            error_details=f"Attendance period {punch_date.year}-{punch_date.month} is locked for branch {employee.master_branch_id}",
                        )
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
                        AttendancePunch.punch_time == utc_dt,
                        AttendancePunch.punch_type == punch_type_val,
                    )
                    existing_punch = (await self.session.execute(stmt)).scalar_one_or_none()

                    _logger.info(
                        "adms_duplicate_check_result",
                        serial_number=sn,
                        employee_id=employee.employee_id,
                        is_duplicate=existing_punch is not None,
                        existing_punch_id=existing_punch.id if existing_punch else None,
                    )
                    log_adms_event("adms_duplicate_check_result", serial_number=sn, employee_id=employee.employee_id, is_duplicate=existing_punch is not None, existing_punch_id=existing_punch.id if existing_punch else None)

                    if existing_punch:
                        _logger.info(
                            "adms_punch_skipped",
                            serial_number=sn,
                            pin=pin,
                            employee_id=employee.employee_id,
                            time_str=time_str,
                            reason="duplicate_punch",
                            error_details=f"Punch already exists with ID {existing_punch.id} at {utc_dt}",
                        )
                        log_adms_event("adms_punch_skipped", serial_number=sn, pin=pin, employee_id=employee.employee_id, time_str=time_str, reason="duplicate_punch", error_details=f"Punch already exists with ID {existing_punch.id} at {utc_dt}")
                        continue

                    # 6. Map verify type to human readable verification mode
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

                    _logger.info(
                        "adms_attendance_creation_attempt",
                        serial_number=sn,
                        pin=pin,
                        employee_id=employee.employee_id,
                        punch_time=str(utc_dt),
                        punch_date=str(punch_date),
                    )

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
                                async with self.session.begin_nested():
                                    shift_resolve = await ShiftService(self.session).resolve_shift(
                                        org_id=device.org_id,
                                        query=ShiftResolveQuery(employee_id=employee.employee_id, on_date=punch_date),
                                    )
                                    if shift_resolve and shift_resolve.shift:
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
                        created_punch = await attendance_service.punches.create({
                            "org_id": device.org_id,
                            "employee_id": employee.employee_id,
                            "attendance_day_id": day.id,
                            "punch_type": punch_type_val,
                            "punch_time": utc_dt,
                            "sequence_no": seq_no,
                            "punch_source": PunchSource.BIOMETRIC_DEVICE.value,
                            "device_id": device.id,
                            "verification_mode": v_mode,
                            "raw_payload": raw_line,
                            "is_valid": True,
                        })

                        # Recompute daily metrics
                        await attendance_service._recompute_day_metrics(device.org_id, day)

                        # Option 1: Auto-enroll in employee_biometrics if not already present
                        from app.modules.employee.models.satellites import EmployeeBiometric
                        bio_stmt = select(EmployeeBiometric).where(
                            EmployeeBiometric.employee_id == employee.employee_id,
                            EmployeeBiometric.is_deleted.is_(False),
                        )
                        existing_bio = (await self.session.execute(bio_stmt)).scalars().first()

                        if not existing_bio:
                            b_type = "face" if "face" in v_mode.lower() else "fingerprint"
                            new_bio = EmployeeBiometric(
                                employee_id=employee.employee_id,
                                device_id=device.id,
                                biometric_type=b_type,
                                biometric_template="AUTO_ENROLLED_VIA_ADMS_PUNCH",
                                registered_at=datetime.now(timezone.utc),
                                is_active=True,
                                is_deleted=False,
                            )
                            self.session.add(new_bio)
                            await self.session.flush()
                            log_adms_event("adms_biometric_auto_enrolled", serial_number=sn, employee_id=employee.employee_id, biometric_id=new_bio.biometric_id)

                        inserted_count += 1

                        _logger.info(
                            "adms_attendance_created",
                            serial_number=sn,
                            pin=pin,
                            employee_id=employee.employee_id,
                            attendance_day_id=day.id,
                            punch_id=created_punch.id,
                            punch_type=punch_type_val,
                            punch_time=str(utc_dt),
                        )
                        log_adms_event("adms_attendance_created", serial_number=sn, pin=pin, employee_id=employee.employee_id, attendance_day_id=day.id, punch_id=created_punch.id, punch_type=punch_type_val, punch_time=str(utc_dt))

                except Exception as e:
                    tb = traceback.format_exc()
                    emp_id = employee.employee_id if 'employee' in locals() and employee else None
                    _logger.error(
                        "adms_punch_exception",
                        serial_number=sn,
                        pin=pin,
                        employee_id=emp_id,
                        time_str=time_str,
                        exception_type=type(e).__name__,
                        exception_message=str(e),
                        full_traceback=tb,
                        punch_data=record,
                    )
                    _logger.error(
                        "adms_punch_skipped",
                        serial_number=sn,
                        pin=pin,
                        employee_id=emp_id,
                        time_str=time_str,
                        reason="database_error" if "sqlalchemy" in type(e).__module__.lower() or "asyncpg" in type(e).__module__.lower() else "exception_raised",
                        error_details=f"{type(e).__name__}: {str(e)}",
                    )
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
