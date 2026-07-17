"""ADMS (iClock) integration router."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query, Request, status
from fastapi.responses import Response

from app.modules.adms.dependencies import ADMSServiceDep

router = APIRouter(tags=["iClock ADMS"])


@router.get(
    "/cdata",
    summary="iClock Get Configuration / Handshake",
    status_code=status.HTTP_200_OK,
)
async def cdata_get(
    request: Request,
    service: ADMSServiceDep,
    sn: Annotated[str, Query(alias="SN", description="Device serial number")],
    options: Annotated[
        str | None, Query(description="Requested option configuration list")
    ] = None,
    pushver: Annotated[str | None, Query(description="Push version")] = None,
    language: Annotated[
        str | None, Query(alias="Language", description="Language of device")
    ] = None,
    client_ip: Annotated[
        str | None, Query(alias="ClientIP", description="Client IP address of device")
    ] = None,
) -> Response:
    """Device handshake and configuration query endpoint."""
    query_params = {
        "SN": sn,
    }
    if options is not None:
        query_params["options"] = options
    if pushver is not None:
        query_params["pushver"] = pushver
    if language is not None:
        query_params["Language"] = language
    if client_ip is not None:
        query_params["ClientIP"] = client_ip

    headers = dict(request.headers)
    ip_addr = client_ip or (request.client.host if request.client else None)

    result = await service.handle_cdata_get(
        query_params=query_params,
        headers=headers,
        client_ip=ip_addr,
    )
    return Response(content=result, media_type="text/plain")


@router.post(
    "/cdata",
    summary="iClock Upload Data",
    status_code=status.HTTP_200_OK,
)
async def cdata_post(
    request: Request,
    service: ADMSServiceDep,
    sn: Annotated[str, Query(alias="SN", description="Device serial number")],
    table: Annotated[
        str | None, Query(description="Table name being uploaded (e.g. ATTLOG, OPERLOG)")
    ] = None,
    stamp: Annotated[
        str | None, Query(alias="Stamp", description="Unique synchronization stamp")
    ] = None,
) -> Response:
    """Device data upload endpoint (punches, logs, etc.)."""
    body_bytes = await request.body()
    payload = body_bytes.decode("utf-8", errors="ignore")
    ip_addr = request.client.host if request.client else None
    result = await service.handle_cdata_post(
        sn=sn, table=table, payload=payload, client_ip=ip_addr
    )
    return Response(content=result, media_type="text/plain")


@router.get(
    "/cdata.aspx",
    summary="iClock Get Configuration / Handshake (ADMS Compatibility)",
    status_code=status.HTTP_200_OK,
)
async def cdata_aspx_get(
    request: Request,
    service: ADMSServiceDep,
    sn: Annotated[str, Query(alias="SN", description="Device serial number")],
    options: Annotated[
        str | None, Query(description="Requested option configuration list")
    ] = None,
    pushver: Annotated[str | None, Query(description="Push version")] = None,
    language: Annotated[
        str | None, Query(alias="Language", description="Language of device")
    ] = None,
    client_ip: Annotated[
        str | None, Query(alias="ClientIP", description="Client IP address of device")
    ] = None,
) -> Response:
    """Device handshake and configuration query endpoint (ADMS Compatibility)."""
    return await cdata_get(
        request=request,
        service=service,
        sn=sn,
        options=options,
        pushver=pushver,
        language=language,
        client_ip=client_ip,
    )


@router.post(
    "/cdata.aspx",
    summary="iClock Upload Data (ADMS Compatibility)",
    status_code=status.HTTP_200_OK,
)
async def cdata_aspx_post(
    request: Request,
    service: ADMSServiceDep,
    sn: Annotated[str, Query(alias="SN", description="Device serial number")],
    table: Annotated[
        str | None, Query(description="Table name being uploaded (e.g. ATTLOG, OPERLOG)")
    ] = None,
    stamp: Annotated[
        str | None, Query(alias="Stamp", description="Unique synchronization stamp")
    ] = None,
) -> Response:
    """Device data upload endpoint (punches, logs, etc.) (ADMS Compatibility)."""
    return await cdata_post(
        request=request,
        service=service,
        sn=sn,
        table=table,
        stamp=stamp,
    )



@router.get(
    "/getrequest",
    summary="iClock Get Pending Commands",
    status_code=status.HTTP_200_OK,
)
async def getrequest_get(
    request: Request,
    service: ADMSServiceDep,
    sn: Annotated[str, Query(alias="SN", description="Device serial number")],
    info: Annotated[
        str | None, Query(alias="INFO", description="Device current info/status")
    ] = None,
) -> Response:
    """Endpoint for device to pull pending commands from the server."""
    ip_addr = request.client.host if request.client else None
    result = await service.handle_getrequest(sn=sn, info_str=info, client_ip=ip_addr)
    return Response(content=result, media_type="text/plain")


@router.get(
    "/getrequest.aspx",
    summary="iClock Get Pending Commands (ADMS Compatibility)",
    status_code=status.HTTP_200_OK,
)
async def getrequest_aspx_get(
    request: Request,
    service: ADMSServiceDep,
    sn: Annotated[str, Query(alias="SN", description="Device serial number")],
    info: Annotated[
        str | None, Query(alias="INFO", description="Device current info/status")
    ] = None,
) -> Response:
    """Endpoint for device to pull pending commands from the server (ADMS Compatibility)."""
    return await getrequest_get(request=request, service=service, sn=sn, info=info)



@router.post(
    "/devicecmd",
    summary="iClock Command Acknowledgement",
    status_code=status.HTTP_200_OK,
)
async def devicecmd_post(
    request: Request,
    service: ADMSServiceDep,
    sn: Annotated[str, Query(alias="SN", description="Device serial number")],
) -> Response:
    """Endpoint for device to post execution results of commands."""
    body_bytes = await request.body()
    payload = body_bytes.decode("utf-8", errors="ignore")
    ip_addr = request.client.host if request.client else None
    result = await service.handle_devicecmd_post(sn=sn, payload=payload, client_ip=ip_addr)
    return Response(content=result, media_type="text/plain")
