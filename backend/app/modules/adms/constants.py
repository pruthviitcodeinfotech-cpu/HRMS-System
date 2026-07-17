"""ADMS (iClock) integration constants."""

from __future__ import annotations

from enum import StrEnum


class ADMSTableName(StrEnum):
    """Supported tables in ADMS upload packets."""

    ATTENDANCE = "ATTLOG"
    OPERLOG = "OPERLOG"
    BIOPHOTO = "BIOPHOTO"


ADMS_RESPONSE_OK = "OK"
