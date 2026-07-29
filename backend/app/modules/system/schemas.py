"""System Administration — Pydantic request/response DTOs."""

from __future__ import annotations

import datetime
from typing import Any

from pydantic import Field

from app.shared.base.schema import BaseSchema


class ComponentHealthSchema(BaseSchema):
    """Health status of a single infrastructure component."""

    status: str = Field(..., description="Status: ok, degraded, down.")
    latency_ms: float = Field(..., description="Latency response time in milliseconds.")
    details: dict[str, Any] = Field(default_factory=dict, description="Additional status details.")


class SystemHealthResponse(BaseSchema):
    """Aggregated health status of the HRMS infrastructure."""

    status: str = Field(..., description="Overall status: ok, degraded, down.")
    api: ComponentHealthSchema
    database: ComponentHealthSchema
    redis: ComponentHealthSchema
    scheduler: ComponentHealthSchema
    failed_jobs_count: int = Field(..., description="Total failed background jobs.")
    timestamp: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc)
    )


class AuditDashboardSummaryResponse(BaseSchema):
    """Audit & Security Dashboard analytics summary."""

    total_activities: int = Field(..., description="Total activity mutations logged.")
    total_logins_24h: int = Field(..., description="User login count in past 24 hours.")
    failed_logins_24h: int = Field(..., description="Failed login attempts in past 24 hours.")
    security_events_count: int = Field(..., description="Security event logs in past 24 hours.")


class BackgroundJobLogSchema(BaseSchema):
    """Background job log record."""

    id: int = Field(..., description="Job log PK.")
    job_id: str = Field(..., description="Unique job UUID.")
    job_name: str = Field(..., description="Background task name.")
    status: str = Field(..., description="Status: queued, running, completed, failed.")
    error_message: str | None = Field(default=None, description="Error message if failed.")
    retry_count: int = Field(..., description="Number of times job was retried.")
    created_at: datetime.datetime = Field(..., description="Created timestamp.")
    updated_at: datetime.datetime = Field(..., description="Last updated timestamp.")


class SlowApiMetricSchema(BaseSchema):
    """Slow API performance metric."""

    endpoint_path: str = Field(..., description="API endpoint path.")
    http_method: str = Field(..., description="HTTP method: GET, POST, etc.")
    status_code: int = Field(..., description="HTTP status code.")
    execution_time_ms: float = Field(..., description="Execution time in milliseconds.")
    query_count: int = Field(..., description="Number of database queries executed.")
    logged_at: datetime.datetime = Field(..., description="Timestamp when metric was captured.")
