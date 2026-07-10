"""Notifications Management — HTTP routes (thin controllers).

Maps the Notification Management API Contract onto FastAPI endpoints.
Controllers resolve dependencies, parse queries, call NotificationService,
and return standard SuccessResponse envelopes.
"""

from __future__ import annotations

import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Response, status

from app.core.constants.enums import PermissionAction as A
from app.core.constants.enums import SortOrder
from app.core.dependencies.auth import (
    CurrentUser,
    get_current_active_user,
    require_permission,
)
from app.core.dependencies.pagination import PaginationParams, pagination_params
from app.core.exceptions.base import AppException
from app.core.middleware.request_context import get_request_id
from app.modules.notifications.dependencies import NotificationServiceDep
from app.modules.notifications.schemas import (
    MyNotificationCountResponse,
    MyNotificationListResponse,
    MyNotificationSchema,
    MyNotificationSearchQuery,
    NotificationAssignRequest,
    NotificationAssignResponse,
    NotificationBulkActionRequest,
    NotificationBulkActionResponse,
    NotificationCreateRequest,
    NotificationDetailsSchema,
    NotificationListResponse,
    NotificationRecipientAssignmentResult,
    NotificationRecipientListResponse,
    NotificationRecipientSearchQuery,
    NotificationSchema,
    NotificationSearchQuery,
    NotificationTimelineEventSchema,
)
from app.shared.schemas.response import SuccessResponse, success_response

router = APIRouter(tags=["Notification Management"])

# Feature-permission key from permission matrix
_FEATURE_KEY = "notification"


# =========================================================================
# Common Dependencies & Helpers
# =========================================================================


def get_org_id(current_user: Annotated[CurrentUser, Depends(get_current_active_user)]) -> int:
    """Return the caller's tenant organization ID, or raise TENANT_UNRESOLVED if absent."""
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


# =========================================================================
# 1. Admin Management — Notifications (feature key: notification)
# =========================================================================


@router.post(
    "/notifications",
    response_model=SuccessResponse[NotificationSchema],
    status_code=status.HTTP_201_CREATED,
    summary="Create Notification",
    dependencies=[Depends(require_permission(_FEATURE_KEY, A.CREATE))],
)
async def create_notification(
    payload: NotificationCreateRequest,
    service: NotificationServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Create a new manual/broadcast notification and optionally assign target recipients."""
    result = await service.create_notification(
        org_id=org_id,
        caller_user_id=current_user.user_id,
        title=payload.title,
        message=payload.message,
        notification_type=payload.notification_type,
        priority=payload.priority,
        source_module=payload.source_module,
        source_entity_type=payload.source_entity_type,
        source_entity_id=payload.source_entity_id,
        expires_at=payload.expires_at,
        recipient_user_ids=payload.recipient_user_ids,
    )
    return _ok(result, "Notification created successfully.")


@router.get(
    "/notifications",
    response_model=SuccessResponse[NotificationListResponse],
    summary="List / Search / Filter Notifications",
    dependencies=[Depends(require_permission(_FEATURE_KEY, A.READ))],
)
async def list_notifications(
    service: NotificationServiceDep,
    org_id: OrgIdDep,
    pagination: Annotated[PaginationParams, Depends(pagination_params)],
    notification_type: Annotated[str | None, Query(description="Filter by category.")] = None,
    priority: Annotated[str | None, Query(description="Filter by priority.")] = None,
    source_module: Annotated[str | None, Query(description="Filter by originating module.")] = None,
    source_entity_type: Annotated[
        str | None, Query(description="Filter by related entity type.")
    ] = None,
    source_entity_id: Annotated[
        int | None, Query(description="Filter by related entity ID.")
    ] = None,
    date_from: Annotated[
        datetime.datetime | None, Query(description="Filter created after this time.")
    ] = None,
    date_to: Annotated[
        datetime.datetime | None, Query(description="Filter created before this time.")
    ] = None,
    search: Annotated[
        str | None, Query(description="Search term matching title or message.")
    ] = None,
    sort_by: Annotated[str | None, Query(description="Field to sort by.")] = "created_at",
    sort_order: Annotated[
        SortOrder | None, Query(description="Sort order (asc/desc).")
    ] = SortOrder.DESC,
) -> dict[str, Any]:
    """Search and filter through all notification definitions inside the organization."""
    query = NotificationSearchQuery(
        page=pagination.page,
        page_size=pagination.page_size,
        notification_type=notification_type,
        priority=priority,
        source_module=source_module,
        source_entity_type=source_entity_type,
        source_entity_id=source_entity_id,
        date_from=date_from,
        date_to=date_to,
        search=search,
    )
    result = await service.list_notifications(
        org_id=org_id,
        notification_type=query.notification_type,
        priority=query.priority,
        source_module=query.source_module,
        source_entity_type=query.source_entity_type,
        source_entity_id=query.source_entity_id,
        date_from=query.date_from,
        date_to=query.date_to,
        search=query.search,
        sort_by=sort_by,
        sort_order=sort_order or SortOrder.DESC,
        page=query.page,
        page_size=query.page_size,
    )
    return _ok(result)


@router.get(
    "/notifications/{notification_id}",
    response_model=SuccessResponse[NotificationDetailsSchema],
    summary="Get Notification Details",
    dependencies=[Depends(require_permission(_FEATURE_KEY, A.READ))],
)
async def get_notification_details(
    notification_id: int,
    service: NotificationServiceDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Retrieve detailed notification definition plus recipient/delivery counts."""
    result = await service.get_notification_details(org_id, notification_id)
    return _ok(result)


# =========================================================================
# 2. Admin Management — Recipients (feature key: notification)
# =========================================================================


@router.post(
    "/notifications/{notification_id}/recipients",
    response_model=SuccessResponse[NotificationAssignResponse],
    summary="Assign Notification to User(s)",
    dependencies=[Depends(require_permission(_FEATURE_KEY, A.CREATE))],
)
async def assign_recipients(
    notification_id: int,
    payload: NotificationAssignRequest,
    service: NotificationServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Idempotently assign recipient users to an existing notification."""
    results = await service.assign_recipients(
        org_id=org_id,
        notification_id=notification_id,
        user_ids=payload.user_ids,
        caller_user_id=current_user.user_id,
    )
    # Wrap in assign response DTO format
    dto_list = [NotificationRecipientAssignmentResult(**r) for r in results]
    response_dto = NotificationAssignResponse(results=dto_list)
    return _ok(response_dto, "Assignment completed.")


@router.get(
    "/notifications/{notification_id}/recipients",
    response_model=SuccessResponse[NotificationRecipientListResponse],
    summary="View Recipients + Delivery Status",
    dependencies=[Depends(require_permission(_FEATURE_KEY, A.READ))],
)
async def list_recipients(
    notification_id: int,
    service: NotificationServiceDep,
    org_id: OrgIdDep,
    pagination: Annotated[PaginationParams, Depends(pagination_params)],
    delivered: Annotated[bool | None, Query(description="Filter by delivery status.")] = None,
    read: Annotated[bool | None, Query(description="Filter by read status.")] = None,
) -> dict[str, Any]:
    """List recipient user records and their interaction states for a notification."""
    query = NotificationRecipientSearchQuery(
        page=pagination.page,
        page_size=pagination.page_size,
        delivered=delivered,
        read=read,
    )
    result = await service.list_recipients(
        org_id=org_id,
        notification_id=notification_id,
        delivered=query.delivered,
        read=query.read,
        page=query.page,
        page_size=query.page_size,
    )
    return _ok(result)


# =========================================================================
# 3. User Notification Center (Self-Service)
# =========================================================================


@router.get(
    "/me/notifications",
    response_model=SuccessResponse[MyNotificationListResponse],
    summary="My Notifications Center",
)
async def get_my_notifications(
    service: NotificationServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
    pagination: Annotated[PaginationParams, Depends(pagination_params)],
    status: Annotated[
        str | None, Query(description="Filter by status: 'read' or 'unread'.")
    ] = None,
    archived: Annotated[
        bool, Query(description="Filter by archive status. Default false.")
    ] = False,
    notification_type: Annotated[str | None, Query(description="Filter by category.")] = None,
    priority: Annotated[str | None, Query(description="Filter by priority.")] = None,
    source_module: Annotated[str | None, Query(description="Filter by originating module.")] = None,
    include_expired: Annotated[
        bool, Query(description="Include expired notifications. Default false.")
    ] = False,
    sort_by: Annotated[str | None, Query(description="Field to sort by.")] = "created_at",
    sort_order: Annotated[
        SortOrder | None, Query(description="Sort order (asc/desc).")
    ] = SortOrder.DESC,
) -> dict[str, Any]:
    """Retrieve and search the caller's personalized notification center inbox."""
    query = MyNotificationSearchQuery(
        page=pagination.page,
        page_size=pagination.page_size,
        status=status,
        archived=archived,
        notification_type=notification_type,
        priority=priority,
        source_module=source_module,
        include_expired=include_expired,
    )
    result = await service.get_user_notifications(
        org_id=org_id,
        user_id=current_user.user_id,
        status=query.status,
        archived=query.archived,
        notification_type=query.notification_type,
        priority=query.priority,
        source_module=query.source_module,
        include_expired=query.include_expired,
        page=query.page,
        page_size=query.page_size,
    )
    return _ok(result)


@router.get(
    "/me/notifications/count",
    response_model=SuccessResponse[MyNotificationCountResponse],
    summary="My Notification Count",
)
async def get_my_notification_counts(
    service: NotificationServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Get active counters (unread, archived, total) for the caller's badge."""
    result = await service.get_user_notification_counts(org_id, current_user.user_id)
    dto = MyNotificationCountResponse(**result)
    return _ok(dto)


@router.get(
    "/me/notifications/{notification_id}",
    response_model=SuccessResponse[MyNotificationSchema],
    summary="Get My Notification Details",
)
async def get_my_notification(
    notification_id: int,
    service: NotificationServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Retrieve a single notification's details and mark it delivered on fetch."""
    result = await service.get_user_notification(org_id, notification_id, current_user.user_id)
    return _ok(result)


# =========================================================================
# 4. User Notification Center Toggles (Self-Service Actions)
# =========================================================================


@router.post(
    "/me/notifications/{notification_id}/read",
    response_model=SuccessResponse[None],
    summary="Mark as Read",
)
async def mark_read(
    notification_id: int,
    service: NotificationServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Mark a single notification recipient record as read."""
    await service.mark_read(org_id, notification_id, current_user.user_id)
    return _ok(None, "Notification marked as read.")


@router.post(
    "/me/notifications/{notification_id}/unread",
    response_model=SuccessResponse[None],
    summary="Mark as Unread",
)
async def mark_unread(
    notification_id: int,
    service: NotificationServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Mark a single notification recipient record as unread."""
    await service.mark_unread(org_id, notification_id, current_user.user_id)
    return _ok(None, "Notification marked as unread.")


@router.post(
    "/me/notifications/{notification_id}/archive",
    response_model=SuccessResponse[None],
    summary="Archive Notification",
)
async def archive_notification(
    notification_id: int,
    service: NotificationServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Archive a single notification recipient record."""
    await service.archive_notification(org_id, notification_id, current_user.user_id)
    return _ok(None, "Notification archived.")


@router.post(
    "/me/notifications/{notification_id}/unarchive",
    response_model=SuccessResponse[None],
    summary="Unarchive Notification",
)
async def unarchive_notification(
    notification_id: int,
    service: NotificationServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Unarchive a single notification recipient record."""
    await service.unarchive_notification(org_id, notification_id, current_user.user_id)
    return _ok(None, "Notification unarchived.")


@router.delete(
    "/me/notifications/{notification_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Notification",
)
async def delete_notification(
    notification_id: int,
    service: NotificationServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> Response:
    """Soft-delete a notification for the recipient."""
    await service.delete_notification(org_id, notification_id, current_user.user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# =========================================================================
# 5. Bulk Operations (Self-Service)
# =========================================================================


@router.post(
    "/me/notifications/bulk-read",
    response_model=SuccessResponse[NotificationBulkActionResponse],
    summary="Mark Multiple or All as Read",
)
async def bulk_mark_read(
    payload: NotificationBulkActionRequest,
    service: NotificationServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Bulk mark multiple or all unread notifications as read."""
    count = await service.bulk_mark_read(
        org_id=org_id,
        user_id=current_user.user_id,
        notification_ids=payload.notification_ids,
        all_unread=payload.all_unread or False,
    )
    return _ok(NotificationBulkActionResponse(affected_count=count))


@router.post(
    "/me/notifications/bulk-archive",
    response_model=SuccessResponse[NotificationBulkActionResponse],
    summary="Archive Multiple Notifications",
)
async def bulk_archive(
    payload: NotificationBulkActionRequest,
    service: NotificationServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Archive multiple notifications in bulk."""
    if not payload.notification_ids:
        raise AppException("notification_ids list is required.", code="VALIDATION_ERROR")
    count = await service.bulk_archive(
        org_id=org_id,
        user_id=current_user.user_id,
        notification_ids=payload.notification_ids,
    )
    return _ok(NotificationBulkActionResponse(affected_count=count))


@router.post(
    "/me/notifications/bulk-delete",
    response_model=SuccessResponse[NotificationBulkActionResponse],
    summary="Delete Multiple Notifications",
)
async def bulk_delete(
    payload: NotificationBulkActionRequest,
    service: NotificationServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Soft-delete multiple notifications in bulk."""
    if not payload.notification_ids:
        raise AppException("notification_ids list is required.", code="VALIDATION_ERROR")
    count = await service.bulk_delete(
        org_id=org_id,
        user_id=current_user.user_id,
        notification_ids=payload.notification_ids,
    )
    return _ok(NotificationBulkActionResponse(affected_count=count))


# =========================================================================
# 6. Recipient Timeline / History
# =========================================================================


@router.get(
    "/me/notifications/{notification_id}/timeline",
    response_model=SuccessResponse[list[NotificationTimelineEventSchema]],
    summary="Notification Timeline",
)
async def get_notification_timeline(
    notification_id: int,
    service: NotificationServiceDep,
    current_user: CurrentUserDep,
    org_id: OrgIdDep,
) -> dict[str, Any]:
    """Retrieve chronological lifecycle events for the recipient record."""
    events = await service.get_notification_timeline(org_id, notification_id, current_user.user_id)
    dto_list = [NotificationTimelineEventSchema(**ev) for ev in events]
    return _ok(dto_list)
