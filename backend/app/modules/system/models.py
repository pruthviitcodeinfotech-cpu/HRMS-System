"""System Administration — Database models.

Tables:
- background_job_logs: Track background queue job executions, status, and retries.
- performance_metrics: Captures API and database execution latency metrics.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database.base import Base


class BackgroundJobLog(Base):
    __tablename__ = "background_job_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    job_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    org_id: Mapped[int | None] = mapped_column(BigInteger)
    job_name: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'queued'")
    )
    error_message: Mapped[str | None] = mapped_column(Text)
    retry_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    __table_args__ = (
        Index("ix_background_job_logs_job_id", "job_id"),
        Index("ix_background_job_logs_status", "status"),
    )


class PerformanceMetric(Base):
    __tablename__ = "performance_metrics"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    endpoint_path: Mapped[str] = mapped_column(String(200), nullable=False)
    http_method: Mapped[str] = mapped_column(String(10), nullable=False)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    execution_time_ms: Mapped[float] = mapped_column(nullable=False)
    query_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("1")
    )
    logged_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    __table_args__ = (
        Index("ix_performance_metrics_endpoint_path", "endpoint_path"),
        Index("ix_performance_metrics_execution_time_ms", "execution_time_ms"),
    )
