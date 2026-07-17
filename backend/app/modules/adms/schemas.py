"""ADMS (iClock) validation schemas."""

from __future__ import annotations

from pydantic import Field

from app.shared.base.schema import BaseSchema


class ADMSCDataQuery(BaseSchema):
    """Query parameters for GET /iclock/cdata."""

    SN: str = Field(..., description="Device serial number")
    options: str | None = Field(default=None, description="Requested options")
    pushver: str | None = Field(default=None, description="Push version")
    Language: str | None = Field(default=None, description="Language")
    ClientIP: str | None = Field(default=None, description="Client IP")
    table: str | None = Field(default=None, description="Table name for POST data")
    Stamp: str | None = Field(default=None, description="Timestamp / Stamp")


class ADMSGetRequestQuery(BaseSchema):
    """Query parameters for GET /iclock/getrequest."""

    SN: str = Field(..., description="Device serial number")
    INFO: str | None = Field(default=None, description="Device info / status")


class ADMSDeviceCmdQuery(BaseSchema):
    """Query parameters for POST /iclock/devicecmd."""

    SN: str = Field(..., description="Device serial number")
