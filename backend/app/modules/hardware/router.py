"""Hardware / Biometric Management — HTTP routes (thin controllers).

Maps the Hardware/Biometric Management API Contract onto FastAPI endpoints.
Controllers only resolve dependencies, build schemas, call BiometricDeviceService,
and wrap the result in the standard success envelope. No business logic lives here.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import Response

from app.core.constants.enums import PermissionAction as A
from app.core.dependencies.auth import (
    CurrentUser,
    get_current_active_user,
    require_permission,
)
from app.core.dependencies.pagination import PaginationParams, pagination_params
from app.core.exceptions.base import AppException
from app.core.middleware.request_context import get_request_id
from app.modules.hardware.constants import DeviceProtocol, DeviceStatus
from app.modules.hardware.dependencies import HardwareServiceDep
from app.modules.hardware.schemas import (
    BiometricDeviceAssignBranchRequest,
    BiometricDeviceConfigureRequest,
    BiometricDeviceConfigurationSchema,
    BiometricDeviceHeartbeatRequest,
    BiometricDeviceHealthSchema,
    BiometricDeviceListResponse,
    BiometricDeviceRegisterRequest,
    BiometricDeviceSchema,
    BiometricDeviceSearchQuery,
    BiometricDeviceStatusSchema,
    BiometricDeviceUpdateRequest,
)
from app.shared.schemas.response import SuccessResponse, success_response

router = APIRouter(tags=["Hardware / Biometric Management"])

_DEVICE = "device"


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------

def get_org_id(current_user: Annotated[CurrentUser, Depends(get_current_active_user)]) -> int:
    """Return the caller's tenant id, or raise TENANT_UNRESOLVED if absent."""
    if current_user.org_id is None:
        exc = AppException("Organization context is required.", code="TENANT_UNRESOLVED")
        exc.status_code = status.HTTP_400_BAD_REQUEST
        raise exc
    return current_user.org_id


OrgIdDep = Annotated[int, Depends(get_org_id)]
CurrentUserDep = Annotated[CurrentUser, Depends(get_current_active_user)]


def _ok(data: Any, message: str = "OK") -> dict[str, Any]:
    """Helper to wrap controller responses in the standard SuccessResponse envelope."""
    return success_response(data=data, message=message, request_id=get_request_id())


def _branch_scope(current_user: CurrentUser) -> list[int] | None:
    """Resolve caller's branch data scope. None means unrestricted admin/org-wide access."""
    branch_ids = current_user.permissions.branch_ids
    if current_user.is_super_admin or not branch_ids:
        return None
    return list(branch_ids)


# ===========================================================================
# Device Lifecycle Endpoints
# ===========================================================================

@router.post(
    "/devices",
    response_model=SuccessResponse[BiometricDeviceSchema],
    status_code=status.HTTP_201_CREATED,
    summary="Register Device",
    dependencies=[Depends(require_permission(_DEVICE, A.CREATE))],
)
async def register_device(
    payload: BiometricDeviceRegisterRequest,
    service: HardwareServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Register a new biometric device within the organization's tenant context."""
    result = await service.register_device(
        org_id=org_id, actor_id=current_user.user_id, data=payload
    )
    return _ok(result, "Device registered successfully.")


@router.get(
    "/devices",
    response_model=SuccessResponse[BiometricDeviceListResponse],
    summary="List / Search Devices",
    dependencies=[Depends(require_permission(_DEVICE, A.READ))],
)
async def list_devices(
    service: HardwareServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
    pagination: Annotated[PaginationParams, Depends(pagination_params)],
    search: Annotated[str | None, Query(description="Search by name, code or serial number.")] = None,
    status: Annotated[DeviceStatus | None, Query(description="Filter by connectivity status.")] = None,
    protocol: Annotated[DeviceProtocol | None, Query(description="Filter by communication protocol.")] = None,
    branch_id: Annotated[int | None, Query(description="Filter by branch assignment.")] = None,
    is_active: Annotated[bool | None, Query(description="Filter by administrative active state.")] = None,
    adms_enabled: Annotated[bool | None, Query(description="Filter by ADMS enabled mode.")] = None,
    sort_by: Annotated[str | None, Query(description="Field to sort by (device_name, created_at, last_seen_at).")] = None,
    sort_order: Annotated[str | None, Query(description="Sort order: asc, desc.")] = None,
) -> dict[str, Any]:
    """Search, filter, and list biometric devices (respects branch data scope boundaries)."""
    query = BiometricDeviceSearchQuery(
        page=pagination.page,
        page_size=pagination.page_size,
        search=search,
        status=status,
        protocol=protocol,
        branch_id=branch_id,
        is_active=is_active,
        adms_enabled=adms_enabled,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    result = await service.list_devices(
        org_id=org_id, query=query, allowed_branch_ids=_branch_scope(current_user)
    )
    return _ok(result)


@router.get(
    "/devices/{device_id}",
    response_model=SuccessResponse[BiometricDeviceSchema],
    summary="Get Device Details",
    dependencies=[Depends(require_permission(_DEVICE, A.READ))],
)
async def get_device(
    device_id: int,
    service: HardwareServiceDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Retrieve full details of a specific biometric device registry."""
    result = await service.get_device(org_id=org_id, device_id=device_id)
    return _ok(result)


@router.patch(
    "/devices/{device_id}",
    response_model=SuccessResponse[BiometricDeviceSchema],
    summary="Update Device",
    dependencies=[Depends(require_permission(_DEVICE, A.EDIT))],
)
async def update_device(
    device_id: int,
    payload: BiometricDeviceUpdateRequest,
    service: HardwareServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Update primary identity, branch, and metadata attributes of a registered device."""
    result = await service.update_device(
        org_id=org_id, actor_id=current_user.user_id, device_id=device_id, data=payload
    )
    return _ok(result, "Device updated successfully.")


@router.delete(
    "/devices/{device_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Device",
    dependencies=[Depends(require_permission(_DEVICE, A.DELETE))],
)
async def delete_device(
    device_id: int,
    service: HardwareServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> Response:
    """Hard delete a device registry if it is not currently referenced by punches or templates."""
    await service.delete_device(org_id=org_id, actor_id=current_user.user_id, device_id=device_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ===========================================================================
# Configuration & Assignment Endpoints
# ===========================================================================

@router.get(
    "/devices/{device_id}/configuration",
    response_model=SuccessResponse[BiometricDeviceConfigurationSchema],
    summary="Get Device Configuration",
    dependencies=[Depends(require_permission(_DEVICE, A.READ))],
)
async def get_device_configuration(
    device_id: int,
    service: HardwareServiceDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Retrieve network and ADMS synchronization configurations (secrets redacted)."""
    result = await service.get_device_configuration(org_id=org_id, device_id=device_id)
    return _ok(result)


@router.patch(
    "/devices/{device_id}/configuration",
    response_model=SuccessResponse[BiometricDeviceConfigurationSchema],
    summary="Update Device Configuration",
    dependencies=[Depends(require_permission(_DEVICE, A.EDIT))],
)
async def update_device_configuration(
    device_id: int,
    payload: BiometricDeviceConfigureRequest,
    service: HardwareServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Update connection credentials, endpoints, timezone and synchronization keys."""
    result = await service.update_device_configuration(
        org_id=org_id, actor_id=current_user.user_id, device_id=device_id, data=payload
    )
    return _ok(result, "Device configuration updated successfully.")


@router.put(
    "/devices/{device_id}/branch",
    response_model=SuccessResponse[BiometricDeviceSchema],
    summary="Assign Device to Branch",
    dependencies=[Depends(require_permission(_DEVICE, A.EDIT))],
)
async def assign_device_to_branch(
    device_id: int,
    payload: BiometricDeviceAssignBranchRequest,
    service: HardwareServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Assign or unassign (by passing null) a biometric device to/from a branch."""
    result = await service.assign_device_to_branch(
        org_id=org_id, actor_id=current_user.user_id, device_id=device_id, data=payload
    )
    return _ok(result, "Device branch assignment updated successfully.")


@router.post(
    "/devices/{device_id}/enable",
    response_model=SuccessResponse[BiometricDeviceSchema],
    summary="Enable Device",
    dependencies=[Depends(require_permission(_DEVICE, A.EDIT))],
)
async def enable_device(
    device_id: int,
    service: HardwareServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Administratively enable the biometric device."""
    result = await service.enable_device(
        org_id=org_id, actor_id=current_user.user_id, device_id=device_id
    )
    return _ok(result, "Device enabled.")


@router.post(
    "/devices/{device_id}/disable",
    response_model=SuccessResponse[BiometricDeviceSchema],
    summary="Disable Device",
    dependencies=[Depends(require_permission(_DEVICE, A.EDIT))],
)
async def disable_device(
    device_id: int,
    service: HardwareServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Administratively disable the biometric device."""
    result = await service.disable_device(
        org_id=org_id, actor_id=current_user.user_id, device_id=device_id
    )
    return _ok(result, "Device disabled.")


# ===========================================================================
# Status, Heartbeat, and Health Endpoints
# ===========================================================================

@router.get(
    "/devices/{device_id}/status",
    response_model=SuccessResponse[BiometricDeviceStatusSchema],
    summary="Check Device Status / Connectivity",
    dependencies=[Depends(require_permission(_DEVICE, A.READ))],
)
async def get_device_status(
    device_id: int,
    service: HardwareServiceDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Retrieve current network connectivity status and heartbeat timestamps."""
    result = await service.get_device_status(org_id=org_id, device_id=device_id)
    return _ok(result)


@router.put(
    "/devices/{device_id}/heartbeat",
    response_model=SuccessResponse[BiometricDeviceSchema],
    summary="Device Heartbeat / Status Report",
    dependencies=[Depends(require_permission(_DEVICE, A.EDIT))],
)
async def report_heartbeat(
    device_id: int,
    payload: BiometricDeviceHeartbeatRequest,
    service: HardwareServiceDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Endpoint consumed by integration daemon to update live online status and metrics."""
    result = await service.report_heartbeat(
        org_id=org_id, device_id=device_id, data=payload
    )
    return _ok(result, "Heartbeat recorded successfully.")


@router.get(
    "/devices/{device_id}/health",
    response_model=SuccessResponse[BiometricDeviceHealthSchema],
    summary="Device Health Status",
    dependencies=[Depends(require_permission(_DEVICE, A.READ))],
)
async def get_device_health(
    device_id: int,
    service: HardwareServiceDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Retrieve full capacity metrics, firmware/software editions, and connectivity health."""
    result = await service.get_device_health(org_id=org_id, device_id=device_id)
    return _ok(result)
