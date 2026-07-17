"""ADMS (iClock) protocol parser."""

from __future__ import annotations

from typing import Any


def parse_adms_post_body(body: str) -> list[dict[str, Any]]:
    """Parse raw plain-text payload from ADMS device into structured dictionaries.

    This is a placeholder for actual parsing of biometric records.
    """
    lines = body.strip().split("\n")
    records = []
    for line in lines:
        if not line.strip():
            continue
        parts = line.strip().split("\t")
        record = {}
        for part in parts:
            if "=" in part:
                k, v = part.split("=", 1)
                record[k] = v
        if record:
            records.append(record)
    return records


def parse_attendance_payload(body: str) -> list[dict[str, Any]]:
    """Parse raw plain-text ATTLOG payload from ADMS device.

    Example line format:
    PIN\tTime\tStatus\tVerifyType\tWorkCode\tReserved\tReserved
    1001\t2026-07-17 10:15:30\t0\t1\t0\t0\t0
    """
    lines = body.strip().split("\n")
    records = []
    for line in lines:
        line_str = line.strip()
        if not line_str or line_str.startswith("#"):
            continue
        parts = line_str.split("\t")
        if len(parts) >= 2:
            pin = parts[0].strip()
            time_str = parts[1].strip()
            
            # Status defaults to '0' (check-in)
            status = "0"
            if len(parts) >= 3:
                status = parts[2].strip()
                
            # VerifyType defaults to '1' (fingerprint)
            verify_type = "1"
            if len(parts) >= 4:
                verify_type = parts[3].strip()

            records.append({
                "pin": pin,
                "time_str": time_str,
                "status": status,
                "verify_type": verify_type,
                "raw_line": line_str,
            })
    return records


def parse_device_info(
    query_params: dict[str, str],
    headers: dict[str, str],
    client_ip: str | None = None,
) -> dict[str, Any]:
    """Parse device registration/handshake info from query parameters and headers."""
    # 1. Serial Number (SN)
    sn = None
    for k, v in query_params.items():
        if k.upper() == "SN":
            sn = v
            break

    # 2. IP Address
    ip = None
    for k, v in query_params.items():
        if k.upper() == "CLIENTIP":
            ip = v
            break
    if not ip:
        ip = client_ip

    # 3. Firmware Version
    firmware = None
    for k, v in query_params.items():
        if k.upper() in ("PUSHVER", "VERSION"):
            firmware = v
            break

    # 4. Platform
    platform = None
    for k, v in query_params.items():
        if k.upper() == "PLATFORM":
            platform = v
            break

    # 5. Device Name
    device_name = None
    for k, v in query_params.items():
        if k.upper() in ("NAME", "DEVICENAME"):
            device_name = v
            break
    if not device_name and sn:
        device_name = f"ADMS Device {sn}"

    return {
        "serial_number": sn,
        "device_name": device_name,
        "ip_address": ip,
        "firmware_version": firmware,
        "platform": platform,
    }


def parse_device_command_ack(payload: str) -> list[dict[str, Any]]:
    """Parse device command acknowledgements from POST /iclock/devicecmd body.

    Example line format:
    ID=101&Return=0&CMD=INFO
    """
    lines = payload.strip().split("\n")
    acks = []
    for line in lines:
        line_str = line.strip()
        if not line_str:
            continue
        parts = line_str.split("&")
        ack = {}
        for part in parts:
            if "=" in part:
                k, v = part.split("=", 1)
                ack[k.strip()] = v.strip()
        if ack:
            acks.append(ack)
    return acks


def parse_device_stats(info_str: str | None) -> dict[str, int]:
    """Parse device status/stats from INFO parameter.

    Example format:
    "UserCount=10,FPCount=20,FaceCount=5,CardCount=15"
    """
    stats = {}
    if not info_str:
        return stats
    parts = info_str.split(",")
    for part in parts:
        if "=" in part:
            k, v = part.split("=", 1)
            k_clean = k.strip().upper()
            try:
                val = int(v.strip())
                if k_clean in ("USERCOUNT", "USER", "USERS"):
                    stats["total_users"] = val
                elif k_clean in ("FPCOUNT", "FP", "FINGERPRINT", "FINGERPRINTS"):
                    stats["total_fingerprints"] = val
                elif k_clean in ("FACECOUNT", "FACE", "FACES"):
                    stats["total_faces"] = val
                elif k_clean in ("CARDCOUNT", "CARD", "CARDS"):
                    stats["total_cards"] = val
            except ValueError:
                continue
    return stats
