"""ADMS (iClock) integration constants."""

from __future__ import annotations

try:
    from enum import StrEnum
except ImportError:
    from enum import Enum

    class StrEnum(str, Enum):
        pass


class ADMSTableName(StrEnum):
    """Supported tables in ADMS upload packets."""

    ATTENDANCE = "ATTLOG"
    OPERLOG = "OPERLOG"
    BIOPHOTO = "BIOPHOTO"


ADMS_RESPONSE_OK = "OK"
