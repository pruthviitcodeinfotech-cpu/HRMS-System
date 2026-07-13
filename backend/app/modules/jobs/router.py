from __future__ import annotations

from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.cache.redis import cache_get_json
from app.core.dependencies.auth import get_current_active_user
from app.core.middleware.request_context import get_request_id
from app.shared.schemas.response import SuccessResponse, success_response

router = APIRouter(tags=["Background Jobs"])


@router.get(
    "/jobs/{job_id}",
    response_model=SuccessResponse[dict[str, Any]],
    summary="Get Background Job Status",
)
async def get_job_status(
    job_id: str,
    current_user: Any = Depends(get_current_active_user),
) -> dict[str, Any]:
    """Retrieve the status and tracking metadata of an enqueued background job."""
    status_data = await cache_get_json(f"job_status:{job_id}")
    if status_data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found or status has expired."
        )
    return success_response(
        data=status_data,
        message="Job status retrieved.",
        request_id=get_request_id(),
    )
