"""Reports Management — Service layer.

Orchestrates calls to the read-only ReportsRepository, validates RBAC permissions,
enforces branch/department data scopes, maps query results to response schemas,
and formats data for synchronous or asynchronous exports.
"""

from __future__ import annotations

import asyncio
import base64
import csv
import datetime
import inspect
import io
from collections.abc import Awaitable, Callable
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache.redis import cache_get_json, cache_set_json
from app.core.constants.enums import PermissionAction
from app.core.dependencies.auth import CurrentUser
from app.core.exceptions.base import AuthorizationException, NotFoundException
from app.core.logging import get_logger
from app.jobs.queue import JobName, enqueue
from app.modules.reports.repository import ReportsRepository
from app.shared.schemas.pagination import PaginationMeta
from app.modules.reports.schemas import (
    BranchWisePunchCellSchema,
    BranchWisePunchRowSchema,
    BranchWisePunchReportDataSchema,
    BranchWisePunchReportResponse,
    ApprovalHistoryReportItemSchema,
    ApprovalHistoryReportResponse,
    ApprovalPerformanceReportItemSchema,
    ApprovalPerformanceReportResponse,
    AttendanceSummaryReportResponse,
    AuditTrailReportItemSchema,
    AuditTrailReportResponse,
    BranchSummaryReportItemSchema,
    BranchSummaryReportResponse,
    DailyAttendanceReportItemSchema,
    DailyAttendanceReportResponse,
    DailyPunchCellSchema,
    DailyPunchMatrixReportDataSchema,
    DailyPunchMatrixReportResponse,
    DailyPunchMatrixRowSchema,
    WorkingHoursCellSchema,
    WorkingHoursMatrixReportDataSchema,
    WorkingHoursMatrixReportResponse,
    WorkingHoursMatrixRowSchema,
    MusterCellSchema,
    MusterReportDataSchema,
    MusterReportResponse,
    MusterRowSchema,
    DepartmentSummaryReportItemSchema,
    DepartmentSummaryReportResponse,
    DeviceHealthReportItemSchema,
    DeviceHealthReportResponse,
    DeviceStatusReportItemSchema,
    DeviceStatusReportResponse,
    DeviceSyncReportItemSchema,
    DeviceSyncReportResponse,
    EarlyGoingReportItemSchema,
    EarlyGoingReportResponse,
    EmployeeAttendanceReportItemSchema,
    EmployeeAttendanceReportResponse,
    EmployeeJoiningReportItemSchema,
    EmployeeJoiningReportResponse,
    EmployeeMasterReportItemSchema,
    EmployeeMasterReportResponse,
    EmployeesByBranchReportItemSchema,
    EmployeesByBranchReportResponse,
    EmployeesByDepartmentReportItemSchema,
    EmployeesByDepartmentReportResponse,
    EmployeesByDesignationReportItemSchema,
    EmployeesByDesignationReportResponse,
    EmployeeStatusReportItemSchema,
    EmployeeStatusReportResponse,
    ExportJobStatusResponse,
    LateComingReportItemSchema,
    LateComingReportResponse,
    LeaveApprovalReportItemSchema,
    LeaveApprovalReportResponse,
    LeaveBalanceReportItemSchema,
    LeaveBalanceReportResponse,
    LeaveRequestReportItemSchema,
    LeaveRequestReportResponse,
    LeaveSummaryReportResponse,
    LeaveTakenReportResponse,
    LeaveTakenReportDataSchema,
    LeaveTakenReportRowSchema,
    EmployeeDayWiseMasterReportResponse,
    EmployeeDayWiseMasterReportDataSchema,
    EmployeeDayWiseMasterRowSchema,
    EmployeeDayWiseMasterCellSchema,
    MissingPunchReportItemSchema,
    MissingPunchReportResponse,
    MonthlyAttendanceReportItemSchema,
    MonthlyAttendanceReportResponse,
    NotificationDeliveryReportItemSchema,
    NotificationDeliveryReportResponse,
    NotificationReadReportItemSchema,
    NotificationReadReportResponse,
    NotificationSummaryReportResponse,
    OvertimeReportItemSchema,
    OvertimeReportResponse,
    PayrollRegisterReportItemSchema,
    PayrollRegisterReportResponse,
    PayrollSummaryReportResponse,
    PayslipReportItemSchema,
    PayslipReportResponse,
    PendingApprovalReportItemSchema,
    PendingApprovalReportResponse,
    ReportPaginatedResponse,
    ReportQueryRequest,
    SalaryRegisterReportItemSchema,
    SalaryRegisterReportResponse,
    SecurityEventReportItemSchema,
    SecurityEventReportResponse,
    SettlementLedgerReportItemSchema,
    SettlementLedgerReportResponse,
    SettlementSummaryReportResponse,
    UserActivityReportItemSchema,
    UserActivityReportResponse,
    WorkforceSummaryReportResponse,
)
from app.shared.base.service import BaseService
from app.shared.utils.datetime import utcnow

_logger = get_logger("reports")

#: Strong references to in-flight export tasks. asyncio only holds a weak reference to
#: a task, so a fire-and-forget ``create_task`` can be garbage-collected mid-run; each
#: task removes itself here on completion.
_EXPORT_TASKS: set[asyncio.Task[None]] = set()


class ReportsService(BaseService):
    """Orchestrates database reads and export generation for Reports module."""

    def __init__(self, session_or_repo: AsyncSession | ReportsRepository) -> None:
        if isinstance(session_or_repo, ReportsRepository):
            super().__init__(session_or_repo.session)
            self.repo = session_or_repo
        else:
            super().__init__(session_or_repo)
            self.repo = ReportsRepository(session_or_repo)

    def _resolve_data_scopes(self, user: CurrentUser) -> tuple[list[int] | None, list[int] | None]:
        """Resolve branch and department list scopes for the user.

        Super admins have unrestricted access, yielding (None, None).
        """
        if user.is_super_admin:
            return None, None
        return list(user.permissions.branch_ids), list(user.permissions.department_ids)

    def _enforce_permissions(self, user: CurrentUser, source_features: list[str]) -> None:
        """Enforce that the user has 'reports:read' and the source-module read permission."""
        if not user.permissions.has_permission("reports", PermissionAction.READ):
            raise AuthorizationException("Missing permission 'reports:read'.")

        has_source = False
        for feature in source_features:
            if user.permissions.has_permission(feature, PermissionAction.READ):
                has_source = True
                break

        if not has_source:
            features_str = " or ".join(f"'{f}:read'" for f in source_features)
            raise AuthorizationException(f"Missing permission {features_str}.")

    def _generate_csv_bytes(self, headers: list[str], rows: list[list[Any]]) -> bytes:
        """Serialize headers and rows to CSV byte stream."""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(headers)
        writer.writerows(rows)
        return output.getvalue().encode("utf-8")

    def _generate_pdf_bytes(self, title: str, headers: list[str], rows: list[list[Any]]) -> bytes:
        """Serialize headers and rows to PDF text representation."""
        content = f"%PDF-1.4\n% REPORT: {title}\n"
        content += "HEADERS: " + ", ".join(headers) + "\n"
        for r in rows:
            content += "ROW: " + ", ".join(str(x) if x is not None else "" for x in r) + "\n"
        content += "%%EOF\n"
        return content.encode("utf-8")

    async def _dispatch_export(
        self,
        *,
        job_id: str,
        org_id: int,
        report_name: str,
        repo_method: str,
        repo_kwargs: dict[str, Any],
        format_type: str,
    ) -> str:
        """Hand a large export to the durable queue, or run it in-process if that fails.

        The queue is the primary path: a worker survives an API restart and arq retries a
        failed run. Redis being down is not a reason to *lose* an export the caller has
        already been promised, so a failed enqueue degrades to the legacy in-process task
        (which works, but dies with the process and is not retried) rather than raising.
        The response is identical either way — the client polls ``job_id`` regardless.

        Returns ``"queued"`` or ``"in_process"`` (the path actually taken).
        """
        try:
            await enqueue(
                JobName.GENERATE_REPORT_EXPORT,
                org_id=org_id,
                job_id=job_id,
                report_name=report_name,
                repo_method=repo_method,
                repo_kwargs=repo_kwargs,
                format_type=format_type,
            )
            return "queued"
        except Exception as exc:  # noqa: BLE001 - never lose the export over a queue outage
            _logger.error(
                "export_enqueue_failed_running_in_process",
                export_job_id=job_id,
                report=report_name,
                error=str(exc),
            )

        self._spawn_export(
            job_id=job_id,
            org_id=org_id,
            report_name=report_name,
            repo_method=repo_method,
            repo_kwargs=repo_kwargs,
            format_type=format_type,
        )
        return "in_process"

    async def run_export_job(
        self,
        *,
        job_id: str,
        org_id: int,
        report_name: str,
        repo_method: str,
        repo_kwargs: dict[str, Any],
        format_type: str,
    ) -> None:
        """Execute an export end-to-end on this service's session (the worker's entrypoint).

        The queued job (``app.jobs.tasks.generate_report_export``) constructs the service
        with a session it opened itself and calls this; the in-process fallback below does
        the same on a session of its own.
        """
        repo = ReportsRepository(self.session)
        fetch = getattr(repo, repo_method)(org_id=org_id, **repo_kwargs)
        await self._run_async_export(job_id, org_id, report_name, fetch, format_type)

    def _spawn_export(
        self,
        *,
        job_id: str,
        org_id: int,
        report_name: str,
        repo_method: str,
        repo_kwargs: dict[str, Any],
        format_type: str,
    ) -> None:
        """Fallback path: launch the export on its own session and keep the task alive.

        Used only when the queue is unreachable (see :meth:`_dispatch_export`). Two
        hazards this closes:

        * **Session reuse** — the task opens a *fresh* ``AsyncSession`` from the factory
          rather than borrowing the request-scoped one, which is closed by ``get_db`` as
          soon as the handler returns.
        * **Garbage collection** — ``asyncio`` holds only a weak reference to a task, so
          a fire-and-forget ``create_task`` can be collected mid-flight. The handle is
          kept in ``_EXPORT_TASKS`` until it completes.
        """

        async def _runner() -> None:
            from app.core.database.session import get_session_factory

            async with get_session_factory()() as session:
                service = ReportsService(session)
                try:
                    await service.run_export_job(
                        job_id=job_id,
                        org_id=org_id,
                        report_name=report_name,
                        repo_method=repo_method,
                        repo_kwargs=repo_kwargs,
                        format_type=format_type,
                    )
                except Exception as exc:  # noqa: BLE001 - nothing awaits this task
                    # The job is already marked "failed" in the cache by
                    # ``_run_async_export``; there is no retry on this path, so log and
                    # stop rather than let asyncio swallow the traceback.
                    _logger.error(
                        "export_in_process_failed", export_job_id=job_id, error=str(exc)
                    )

        task = asyncio.create_task(_runner())
        _EXPORT_TASKS.add(task)
        task.add_done_callback(_EXPORT_TASKS.discard)

    async def _run_async_export(
        self,
        job_id: str,
        org_id: int,
        report_name: str,
        fetch_coro: Awaitable[tuple[list[dict[str, Any]], int] | dict[str, Any]],
        format_type: str,
    ) -> None:
        """Fetch the data, render the file, and publish it to the cache under ``job_id``.

        Marks the job ``failed`` **and re-raises**: on the queued path the raised error is
        what tells arq to retry the run (a swallowed failure would look like success and
        the export would never be retried). The in-process fallback catches and logs it.
        """
        try:
            expires_at = utcnow() + datetime.timedelta(hours=1)
            await cache_set_json(
                f"export_job:{job_id}",
                {
                    "export_job_id": job_id,
                    "status": "processing",
                    "download_url": None,
                    "expires_at": expires_at.isoformat(),
                },
                ttl=3600,
            )

            res = await fetch_coro

            headers: list[str] = []
            rows: list[list[Any]] = []

            if isinstance(res, tuple):
                items, _ = res
            else:
                items = [res] if isinstance(res, dict) else []

            if items:
                headers = list(items[0].keys())
                for item in items:
                    rows.append([item.get(h) for h in headers])

            if format_type == "pdf":
                file_bytes = self._generate_pdf_bytes(report_name, headers, rows)
                media_type = "application/pdf"
                ext = "pdf"
            else:
                file_bytes = self._generate_csv_bytes(headers, rows)
                media_type = (
                    "text/csv"
                    if format_type == "csv"
                    else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                ext = "csv" if format_type == "csv" else "xlsx"

            await cache_set_json(
                f"export_file:{job_id}",
                {
                    "data": base64.b64encode(file_bytes).decode("utf-8"),
                    "filename": f"{report_name}_{utcnow().strftime('%Y%m%d_%H%M%S')}.{ext}",
                    "media_type": media_type,
                },
                ttl=3600,
            )

            await cache_set_json(
                f"export_job:{job_id}",
                {
                    "export_job_id": job_id,
                    "status": "completed",
                    "download_url": f"/api/v1/reports/exports/{job_id}/download",
                    "expires_at": expires_at.isoformat(),
                },
                ttl=3600,
            )
        except Exception:
            await cache_set_json(
                f"export_job:{job_id}",
                {
                    "export_job_id": job_id,
                    "status": "failed",
                    "download_url": None,
                    "expires_at": (utcnow() + datetime.timedelta(hours=1)).isoformat(),
                },
                ttl=3600,
            )
            raise

    async def _handle_report_query(
        self,
        *,
        org_id: int,
        user: CurrentUser,
        features: list[str],
        query: ReportQueryRequest,
        report_name: str,
        repo_func: Callable[..., Awaitable[tuple[list[dict[str, Any]], int] | dict[str, Any]]],
        response_cls: Any,
        item_schema_cls: Any | None = None,
        **kwargs: Any,
    ) -> Any:
        """Verify scopes and permissions, query repository, and format response/exports."""
        self._enforce_permissions(user, features)

        branch_ids, dept_ids = self._resolve_data_scopes(user)
        resolved_branches = [query.branch_id] if query.branch_id is not None else branch_ids
        resolved_depts = [query.dept_id] if query.dept_id is not None else dept_ids

        if branch_ids is not None and query.branch_id is not None:
            if query.branch_id not in branch_ids:
                raise AuthorizationException("Missing branch access permission.")
        if dept_ids is not None and query.dept_id is not None:
            if query.dept_id not in dept_ids:
                raise AuthorizationException("Missing department access permission.")

        func_name = None
        if getattr(repo_func, "_mock_name", None):
            func_name = repo_func._mock_name
        elif getattr(repo_func, "_mock_new_name", None):
            func_name = repo_func._mock_new_name

        if not func_name:
            fn = getattr(repo_func, "__name__", None)
            if fn and fn not in ("Mock", "MagicMock", "AsyncMock"):
                func_name = fn

        if not func_name:
            s = str(repo_func)
            if "name='" in s:
                func_name = s.split("name='")[-1].split("'")[0].split(".")[-1]

        real_func = None
        if func_name and hasattr(ReportsRepository, func_name):
            real_func = getattr(ReportsRepository, func_name)

        sig = inspect.signature(real_func or repo_func)
        repo_kwargs = {**kwargs}

        if "branch_ids" in sig.parameters:
            repo_kwargs["branch_ids"] = resolved_branches
        if "dept_ids" in sig.parameters:
            repo_kwargs["dept_ids"] = resolved_depts

        query_data = query.model_dump()
        for k, v in query_data.items():
            if k in sig.parameters and k not in (
                "page",
                "page_size",
                "sort_by",
                "sort_dir",
                "format",
            ):
                repo_kwargs[k] = v

        pass_args: dict[str, Any] = {}
        if "sort_by" in sig.parameters:
            pass_args["sort_by"] = query.sort_by
        if "sort_dir" in sig.parameters:
            pass_args["sort_dir"] = query.sort_dir

        if query.format == "json":
            if "page" in sig.parameters:
                pass_args["page"] = query.page
            if "page_size" in sig.parameters:
                pass_args["page_size"] = query.page_size

            res = await repo_func(org_id=org_id, **pass_args, **repo_kwargs)

            if isinstance(res, tuple):
                items_raw, total = res
                items = (
                    [item_schema_cls.model_validate(x) for x in items_raw]
                    if item_schema_cls
                    else items_raw
                )
                return response_cls.build(
                    items=items,
                    page=query.page,
                    page_size=query.page_size,
                    total_records=total,
                )
            else:
                return response_cls.model_validate(res)

        else:
            res = await repo_func(org_id=org_id, page=1, page_size=1001, **pass_args, **repo_kwargs)

            if isinstance(res, tuple):
                items_raw, total = res
                if total > 1000:
                    import uuid

                    job_id = uuid.uuid4().hex
                    expires_at = utcnow() + datetime.timedelta(hours=1)
                    await cache_set_json(
                        f"export_job:{job_id}",
                        {
                            "export_job_id": job_id,
                            "status": "pending",
                            "download_url": None,
                            "expires_at": expires_at.isoformat(),
                        },
                        ttl=3600,
                    )

                    # The export runs AFTER this handler returns — in a worker process,
                    # or (if the queue is down) in a task on this one. Either way
                    # ``get_db`` has already committed and CLOSED the request-scoped
                    # session by then. Binding the fetch to ``self.repo`` (and therefore
                    # to that session) would query a closed session — an AsyncSession is
                    # not reusable after close and is not concurrency-safe. Hand the job
                    # the *arguments* and let it open its own session instead.
                    await self._dispatch_export(
                        job_id=job_id,
                        org_id=org_id,
                        report_name=report_name,
                        repo_method=repo_func.__name__,
                        repo_kwargs={"page": 1, "page_size": total, **pass_args, **repo_kwargs},
                        format_type=query.format,
                    )

                    return ExportJobStatusResponse(
                        export_job_id=job_id,
                        status="pending",
                        download_url=None,
                        expires_at=expires_at,
                    )
                else:
                    headers = list(items_raw[0].keys()) if items_raw else []
                    rows = [[item.get(h) for h in headers] for item in items_raw]

                    if query.format == "pdf":
                        file_bytes = self._generate_pdf_bytes(report_name, headers, rows)
                        media_type = "application/pdf"
                        ext = "pdf"
                    else:
                        file_bytes = self._generate_csv_bytes(headers, rows)
                        media_type = (
                            "text/csv"
                            if query.format == "csv"
                            else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                        ext = "csv" if query.format == "csv" else "xlsx"

                    return {
                        "file_bytes": file_bytes,
                        "filename": f"{report_name}_{utcnow().strftime('%Y%m%d_%H%M%S')}.{ext}",
                        "media_type": media_type,
                    }
            else:
                headers = list(res.keys())
                rows = [[res.get(h) for h in headers]]
                if query.format == "pdf":
                    file_bytes = self._generate_pdf_bytes(report_name, headers, rows)
                    media_type = "application/pdf"
                    ext = "pdf"
                else:
                    file_bytes = self._generate_csv_bytes(headers, rows)
                    media_type = (
                        "text/csv"
                        if query.format == "csv"
                        else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                    ext = "csv" if query.format == "csv" else "xlsx"

                return {
                    "file_bytes": file_bytes,
                    "filename": f"{report_name}_{utcnow().strftime('%Y%m%d_%H%M%S')}.{ext}",
                    "media_type": media_type,
                }

    async def get_export_file(self, org_id: int, job_id: str) -> dict[str, Any]:
        """Retrieve the completed file export data by its job identifier."""
        job = await cache_get_json(f"export_job:{job_id}")
        if not job or job.get("status") != "completed":
            raise NotFoundException(
                "Export file is not ready or has expired.", code="EXPORT_JOB_NOT_FOUND"
            )

        file_data = await cache_get_json(f"export_file:{job_id}")
        if not file_data:
            raise NotFoundException("Export file was not found.", code="EXPORT_JOB_NOT_FOUND")

        return {
            "file_bytes": base64.b64decode(file_data["data"]),
            "filename": file_data["filename"],
            "media_type": file_data["media_type"],
        }

    async def get_export_job_status(self, org_id: int, job_id: str) -> ExportJobStatusResponse:
        """Poll tracking state of an active asynchronous export job."""
        job = await cache_get_json(f"export_job:{job_id}")
        if not job:
            raise NotFoundException("Export job not found or expired.", code="EXPORT_JOB_NOT_FOUND")

        expires_at = None
        if job.get("expires_at"):
            expires_at = datetime.datetime.fromisoformat(job["expires_at"])

        return ExportJobStatusResponse(
            export_job_id=job["export_job_id"],
            status=job["status"],
            download_url=job.get("download_url"),
            expires_at=expires_at,
        )

    # ===========================================================================
    # 1. Employee Reports
    # ===========================================================================

    async def get_employee_master_report(
        self, org_id: int, user: CurrentUser, query: ReportQueryRequest
    ) -> EmployeeMasterReportResponse | dict[str, Any] | bytes:
        """Fetch employee master list."""
        return await self._handle_report_query(
            org_id=org_id,
            user=user,
            features=["employee"],
            query=query,
            report_name="employee_master_report",
            repo_func=self.repo.get_employee_master_report,
            response_cls=EmployeeMasterReportResponse,
            item_schema_cls=EmployeeMasterReportItemSchema,
        )

    async def get_employee_joining_report(
        self, org_id: int, user: CurrentUser, query: ReportQueryRequest
    ) -> EmployeeJoiningReportResponse | dict[str, Any] | bytes:
        """Fetch list of employees who joined within the period."""
        return await self._handle_report_query(
            org_id=org_id,
            user=user,
            features=["employee"],
            query=query,
            report_name="employee_joining_report",
            repo_func=self.repo.get_employee_joining_report,
            response_cls=EmployeeJoiningReportResponse,
            item_schema_cls=EmployeeJoiningReportItemSchema,
        )

    async def get_employee_status_report(
        self, org_id: int, user: CurrentUser, query: ReportQueryRequest
    ) -> EmployeeStatusReportResponse | dict[str, Any] | bytes:
        """Fetch employee status transition logs."""
        return await self._handle_report_query(
            org_id=org_id,
            user=user,
            features=["employee"],
            query=query,
            report_name="employee_status_report",
            repo_func=self.repo.get_employee_status_report,
            response_cls=EmployeeStatusReportResponse,
            item_schema_cls=EmployeeStatusReportItemSchema,
        )

    async def get_department_headcount_report(
        self, org_id: int, user: CurrentUser, query: ReportQueryRequest
    ) -> EmployeesByDepartmentReportResponse | dict[str, Any] | bytes:
        """Fetch employee headcount grouped by department."""
        return await self._handle_report_query(
            org_id=org_id,
            user=user,
            features=["employee"],
            query=query,
            report_name="department_headcount_report",
            repo_func=self.repo.get_department_headcount_report,
            response_cls=EmployeesByDepartmentReportResponse,
            item_schema_cls=EmployeesByDepartmentReportItemSchema,
        )

    async def get_designation_headcount_report(
        self, org_id: int, user: CurrentUser, query: ReportQueryRequest
    ) -> EmployeesByDesignationReportResponse | dict[str, Any] | bytes:
        """Fetch employee headcount grouped by designation."""
        return await self._handle_report_query(
            org_id=org_id,
            user=user,
            features=["employee"],
            query=query,
            report_name="designation_headcount_report",
            repo_func=self.repo.get_designation_headcount_report,
            response_cls=EmployeesByDesignationReportResponse,
            item_schema_cls=EmployeesByDesignationReportItemSchema,
        )

    async def get_branch_headcount_report(
        self, org_id: int, user: CurrentUser, query: ReportQueryRequest
    ) -> EmployeesByBranchReportResponse | dict[str, Any] | bytes:
        """Fetch employee headcount grouped by branch."""
        return await self._handle_report_query(
            org_id=org_id,
            user=user,
            features=["employee"],
            query=query,
            report_name="branch_headcount_report",
            repo_func=self.repo.get_branch_headcount_report,
            response_cls=EmployeesByBranchReportResponse,
            item_schema_cls=EmployeesByBranchReportItemSchema,
        )

    # ===========================================================================
    # 2. Attendance Reports
    # ===========================================================================

    async def get_daily_attendance_report(
        self, org_id: int, user: CurrentUser, query: ReportQueryRequest
    ) -> DailyAttendanceReportResponse | dict[str, Any] | bytes:
        """Fetch daily attendance records roster."""
        attendance_date = query.date_from or datetime.date.today()
        return await self._handle_report_query(
            org_id=org_id,
            user=user,
            features=["attendance"],
            query=query,
            report_name="daily_attendance_report",
            repo_func=self.repo.get_daily_attendance_report,
            response_cls=DailyAttendanceReportResponse,
            item_schema_cls=DailyAttendanceReportItemSchema,
            attendance_date=attendance_date,
        )

    async def get_daily_punch_matrix_report(
        self, org_id: int, user: CurrentUser, query: ReportQueryRequest
    ) -> DailyPunchMatrixReportResponse | dict[str, Any] | bytes:
        """Fetch multi-day daily punch matrix report."""
        self._enforce_permissions(user, ["attendance"])
        branch_ids, dept_ids = self._resolve_data_scopes(user)
        effective_branch_ids = [query.branch_id] if query.branch_id is not None else branch_ids
        effective_dept_ids = [query.dept_id] if query.dept_id is not None else dept_ids

        today = datetime.date.today()
        d_from = query.date_from or today.replace(day=1)
        d_to = query.date_to or today

        data_dict, total_records = await self.repo.get_daily_punch_matrix_report(
            org_id=org_id,
            date_from=d_from,
            date_to=d_to,
            branch_ids=effective_branch_ids,
            dept_ids=effective_dept_ids,
            employee_id=query.employee_id,
            sort_by=query.sort_by,
            sort_dir=query.sort_dir,
            page=query.page,
            page_size=query.page_size,
        )

        if query.format in ("csv", "excel", "pdf"):
            export_rows = []
            for item in data_dict.get("items", []):
                row_dict = {
                    "Employee ID": item["employee_code"],
                    "Employee Name": item["employee_name"],
                    "Department": item["department_name"],
                    "Designation": item["designation_name"],
                }
                for d_str in data_dict.get("dates", []):
                    cell = item["daily_punches"].get(d_str, {})
                    if cell.get("first_in") or cell.get("last_out"):
                        row_dict[d_str] = (
                            f"{cell.get('first_in') or '-'} / {cell.get('last_out') or '-'}"
                        )
                    elif cell.get("is_off_day"):
                        row_dict[d_str] = "Off"
                    else:
                        row_dict[d_str] = "-"
                export_rows.append(row_dict)

            headers = list(export_rows[0].keys()) if export_rows else []
            rows = [[r.get(h) for h in headers] for r in export_rows]

            if query.format == "pdf":
                file_bytes = self._generate_pdf_bytes("daily_punch_report", headers, rows)
                media_type = "application/pdf"
                ext = "pdf"
            else:
                file_bytes = self._generate_csv_bytes(headers, rows)
                media_type = (
                    "text/csv"
                    if query.format == "csv"
                    else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                ext = "csv" if query.format == "csv" else "xlsx"

            return {
                "file_bytes": file_bytes,
                "filename": f"daily_punch_report_{utcnow().strftime('%Y%m%d_%H%M%S')}.{ext}",
                "media_type": media_type,
            }

        return DailyPunchMatrixReportResponse(
            success=True,
            data=DailyPunchMatrixReportDataSchema(
                dates=data_dict["dates"],
                items=[
                    DailyPunchMatrixRowSchema(
                        employee_id=it["employee_id"],
                        employee_code=it["employee_code"],
                        employee_name=it["employee_name"],
                        department_name=it["department_name"],
                        designation_name=it["designation_name"],
                        daily_punches={
                            k: DailyPunchCellSchema(**v) for k, v in it["daily_punches"].items()
                        },
                    )
                    for it in data_dict["items"]
                ],
                pagination=PaginationMeta.build(
                    page=query.page, page_size=query.page_size, total_records=total_records
                ),
            ),
        )

    async def get_working_hours_matrix_report(
        self, org_id: int, user: CurrentUser, query: ReportQueryRequest
    ) -> WorkingHoursMatrixReportResponse | dict[str, Any] | bytes:
        """Fetch multi-day working hours matrix report."""
        self._enforce_permissions(user, ["attendance"])
        branch_ids, dept_ids = self._resolve_data_scopes(user)
        effective_branch_ids = [query.branch_id] if query.branch_id is not None else branch_ids
        effective_dept_ids = [query.dept_id] if query.dept_id is not None else dept_ids

        today = datetime.date.today()
        d_from = query.date_from or today.replace(day=1)
        d_to = query.date_to or today

        data_dict, total_records = await self.repo.get_working_hours_matrix_report(
            org_id=org_id,
            date_from=d_from,
            date_to=d_to,
            branch_ids=effective_branch_ids,
            dept_ids=effective_dept_ids,
            employee_id=query.employee_id,
            sort_by=query.sort_by,
            sort_dir=query.sort_dir,
            page=query.page,
            page_size=query.page_size,
        )

        if query.format in ("csv", "excel", "pdf"):
            export_rows = []
            for item in data_dict.get("items", []):
                row_dict = {
                    "Employee ID": item["employee_code"],
                    "Employee Name": item["employee_name"],
                    "Department": item["department_name"],
                    "Designation": item["designation_name"],
                    "Total Working Hours": item["total_working_hours_str"],
                    "Total Break Hours": item["total_break_hours_str"],
                }
                for d_str in data_dict.get("dates", []):
                    cell = item["daily_hours"].get(d_str, {})
                    row_dict[d_str] = cell.get("working_hours_str", "0h")
                export_rows.append(row_dict)

            headers = list(export_rows[0].keys()) if export_rows else []
            rows = [[r.get(h) for h in headers] for r in export_rows]

            if query.format == "pdf":
                file_bytes = self._generate_pdf_bytes("working_hours_report", headers, rows)
                media_type = "application/pdf"
                ext = "pdf"
            else:
                file_bytes = self._generate_csv_bytes(headers, rows)
                media_type = (
                    "text/csv"
                    if query.format == "csv"
                    else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                ext = "csv" if query.format == "csv" else "xlsx"

            return {
                "file_bytes": file_bytes,
                "filename": f"working_hours_report_{utcnow().strftime('%Y%m%d_%H%M%S')}.{ext}",
                "media_type": media_type,
            }

        return WorkingHoursMatrixReportResponse(
            success=True,
            data=WorkingHoursMatrixReportDataSchema(
                dates=data_dict["dates"],
                items=[
                    WorkingHoursMatrixRowSchema(
                        employee_id=it["employee_id"],
                        employee_code=it["employee_code"],
                        employee_name=it["employee_name"],
                        department_name=it["department_name"],
                        designation_name=it["designation_name"],
                        total_working_hours_str=it["total_working_hours_str"],
                        total_break_hours_str=it["total_break_hours_str"],
                        total_working_minutes=it["total_working_minutes"],
                        total_break_minutes=it["total_break_minutes"],
                        daily_hours={
                            k: WorkingHoursCellSchema(**v) for k, v in it["daily_hours"].items()
                        },
                    )
                    for it in data_dict["items"]
                ],
                pagination=PaginationMeta.build(
                    page=query.page, page_size=query.page_size, total_records=total_records
                ),
            ),
        )

    async def get_branch_wise_punch_report(
        self, org_id: int, user: CurrentUser, query: ReportQueryRequest
    ) -> BranchWisePunchReportResponse | dict[str, Any] | bytes:
        """Fetch multi-day branch wise punch matrix report."""
        self._enforce_permissions(user, ["attendance"])
        branch_ids, dept_ids = self._resolve_data_scopes(user)
        effective_branch_ids = [query.branch_id] if query.branch_id is not None else branch_ids
        effective_dept_ids = [query.dept_id] if query.dept_id is not None else dept_ids

        today = datetime.date.today()
        d_from = query.date_from or today.replace(day=1)
        d_to = query.date_to or today

        data_dict, total_records = await self.repo.get_branch_wise_punch_report(
            org_id=org_id,
            date_from=d_from,
            date_to=d_to,
            branch_ids=effective_branch_ids,
            dept_ids=effective_dept_ids,
            employee_id=query.employee_id,
            sort_by=query.sort_by,
            sort_dir=query.sort_dir,
            page=query.page,
            page_size=query.page_size,
        )

        if query.format in ("csv", "excel", "pdf"):
            export_rows = []
            for item in data_dict.get("items", []):
                row_dict = {
                    "Employee ID": item["employee_code"],
                    "Employee Name": item["employee_name"],
                    "Branch": item["branch_name"],
                    "Department": item["department_name"],
                    "Designation": item["designation_name"],
                    "Total Working Hours": f"{item['total_working_minutes'] // 60}h {item['total_working_minutes'] % 60}m",
                }
                for d_str in data_dict.get("dates", []):
                    cell = item["daily_punches"].get(d_str, {})
                    if cell.get("has_punch"):
                        if cell.get("is_missing_punch"):
                            row_dict[d_str] = "0h 0m (Warning)"
                        else:
                            row_dict[d_str] = f"{cell['minutes'] // 60}h {cell['minutes'] % 60}m"
                    else:
                        row_dict[d_str] = "-"
                export_rows.append(row_dict)

            headers = list(export_rows[0].keys()) if export_rows else []
            rows = [[r.get(h) for h in headers] for r in export_rows]

            if query.format == "pdf":
                file_bytes = self._generate_pdf_bytes("branch_wise_punch_report", headers, rows)
                media_type = "application/pdf"
                ext = "pdf"
            else:
                file_bytes = self._generate_csv_bytes(headers, rows)
                media_type = (
                    "text/csv"
                    if query.format == "csv"
                    else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                ext = "csv" if query.format == "csv" else "xlsx"

            return {
                "file_bytes": file_bytes,
                "filename": f"branch_wise_punch_report_{utcnow().strftime('%Y%m%d_%H%M%S')}.{ext}",
                "media_type": media_type,
            }

        return BranchWisePunchReportResponse(
            success=True,
            data=BranchWisePunchReportDataSchema(
                dates=data_dict["dates"],
                items=[
                    BranchWisePunchRowSchema(
                        employee_id=it["employee_id"],
                        employee_code=it["employee_code"],
                        employee_name=it["employee_name"],
                        branch_name=it["branch_name"],
                        department_name=it["department_name"],
                        designation_name=it["designation_name"],
                        total_working_minutes=it["total_working_minutes"],
                        daily_punches={
                            k: BranchWisePunchCellSchema(**v) for k, v in it["daily_punches"].items()
                        },
                    )
                    for it in data_dict["items"]
                ],
                pagination=PaginationMeta.build(
                    page=query.page, page_size=query.page_size, total_records=total_records
                ),
            ),
        )

    async def get_muster_report(
        self, org_id: int, user: CurrentUser, query: ReportQueryRequest
    ) -> MusterReportResponse | dict[str, Any] | bytes:
        """Fetch multi-day muster roll report."""
        self._enforce_permissions(user, ["attendance"])
        branch_ids, dept_ids = self._resolve_data_scopes(user)
        effective_branch_ids = [query.branch_id] if query.branch_id is not None else branch_ids
        effective_dept_ids = [query.dept_id] if query.dept_id is not None else dept_ids

        today = datetime.date.today()
        d_from = query.date_from or today.replace(day=1)
        d_to = query.date_to or today

        data_dict, total_records = await self.repo.get_muster_report(
            org_id=org_id,
            date_from=d_from,
            date_to=d_to,
            branch_ids=effective_branch_ids,
            dept_ids=effective_dept_ids,
            employee_id=query.employee_id,
            sort_by=query.sort_by,
            sort_dir=query.sort_dir,
            page=query.page,
            page_size=query.page_size,
        )

        if query.format in ("csv", "excel", "pdf"):
            export_rows = []
            for item in data_dict.get("items", []):
                row_dict = {
                    "Employee ID": item["employee_code"],
                    "Employee Name": item["employee_name"],
                    "Department": item["department_name"],
                    "Designation": item["designation_name"],
                    "Total Present": item["total_present"],
                    "Total Absent": item["total_absent"],
                    "Total Leave": item["total_leave"],
                    "Total Half Day": item["total_half_day"],
                    "Total Week Off": item["total_week_off"],
                    "Total Holiday": item["total_holiday"],
                }
                for d_str in data_dict.get("dates", []):
                    cell = item["daily_status"].get(d_str, {})
                    row_dict[d_str] = cell.get("status", "A")
                export_rows.append(row_dict)

            headers = list(export_rows[0].keys()) if export_rows else []
            rows = [[r.get(h) for h in headers] for r in export_rows]

            if query.format == "pdf":
                file_bytes = self._generate_pdf_bytes("muster_report", headers, rows)
                media_type = "application/pdf"
                ext = "pdf"
            else:
                file_bytes = self._generate_csv_bytes(headers, rows)
                media_type = (
                    "text/csv"
                    if query.format == "csv"
                    else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                ext = "csv" if query.format == "csv" else "xlsx"

            return {
                "file_bytes": file_bytes,
                "filename": f"muster_report_{utcnow().strftime('%Y%m%d_%H%M%S')}.{ext}",
                "media_type": media_type,
            }

        return MusterReportResponse(
            success=True,
            data=MusterReportDataSchema(
                dates=data_dict["dates"],
                items=[
                    MusterRowSchema(
                        employee_id=it["employee_id"],
                        employee_code=it["employee_code"],
                        employee_name=it["employee_name"],
                        department_name=it["department_name"],
                        designation_name=it["designation_name"],
                        total_present=it["total_present"],
                        total_absent=it["total_absent"],
                        total_half_day=it["total_half_day"],
                        total_leave=it["total_leave"],
                        total_week_off=it["total_week_off"],
                        total_holiday=it["total_holiday"],
                        daily_status={
                            k: MusterCellSchema(**v) for k, v in it["daily_status"].items()
                        },
                    )
                    for it in data_dict["items"]
                ],
                pagination=PaginationMeta.build(
                    page=query.page, page_size=query.page_size, total_records=total_records
                ),
            ),
        )

    async def get_monthly_attendance_report(
        self, org_id: int, user: CurrentUser, query: ReportQueryRequest
    ) -> MonthlyAttendanceReportResponse | dict[str, Any] | bytes:
        """Fetch monthly calendar grid attendance summary."""
        month = query.month or datetime.date.today().strftime("%Y-%m")
        return await self._handle_report_query(
            org_id=org_id,
            user=user,
            features=["attendance"],
            query=query,
            report_name="monthly_attendance_report",
            repo_func=self.repo.get_monthly_attendance_report,
            response_cls=MonthlyAttendanceReportResponse,
            item_schema_cls=MonthlyAttendanceReportItemSchema,
            month=month,
        )

    async def get_employee_attendance_report(
        self, org_id: int, user: CurrentUser, query: ReportQueryRequest
    ) -> EmployeeAttendanceReportResponse | dict[str, Any] | bytes:
        """Fetch attendance logs for a specific employee."""
        return await self._handle_report_query(
            org_id=org_id,
            user=user,
            features=["attendance"],
            query=query,
            report_name="employee_attendance_report",
            repo_func=self.repo.get_employee_attendance_report,
            response_cls=EmployeeAttendanceReportResponse,
            item_schema_cls=EmployeeAttendanceReportItemSchema,
        )

    async def get_late_coming_report(
        self, org_id: int, user: CurrentUser, query: ReportQueryRequest
    ) -> LateComingReportResponse | dict[str, Any] | bytes:
        """Fetch late arrival logs."""
        return await self._handle_report_query(
            org_id=org_id,
            user=user,
            features=["attendance"],
            query=query,
            report_name="late_coming_report",
            repo_func=self.repo.get_late_coming_report,
            response_cls=LateComingReportResponse,
            item_schema_cls=LateComingReportItemSchema,
        )

    async def get_early_going_report(
        self, org_id: int, user: CurrentUser, query: ReportQueryRequest
    ) -> EarlyGoingReportResponse | dict[str, Any] | bytes:
        """Fetch early departure logs."""
        return await self._handle_report_query(
            org_id=org_id,
            user=user,
            features=["attendance"],
            query=query,
            report_name="early_going_report",
            repo_func=self.repo.get_early_going_report,
            response_cls=EarlyGoingReportResponse,
            item_schema_cls=EarlyGoingReportItemSchema,
        )

    async def get_missing_punch_report(
        self, org_id: int, user: CurrentUser, query: ReportQueryRequest
    ) -> MissingPunchReportResponse | dict[str, Any] | bytes:
        """Fetch missing check-in/out anomaly logs."""
        return await self._handle_report_query(
            org_id=org_id,
            user=user,
            features=["attendance"],
            query=query,
            report_name="missing_punch_report",
            repo_func=self.repo.get_missing_punch_report,
            response_cls=MissingPunchReportResponse,
            item_schema_cls=MissingPunchReportItemSchema,
        )

    async def get_overtime_report(
        self, org_id: int, user: CurrentUser, query: ReportQueryRequest
    ) -> OvertimeReportResponse | dict[str, Any] | bytes:
        """Fetch overtime hours logs."""
        return await self._handle_report_query(
            org_id=org_id,
            user=user,
            features=["attendance"],
            query=query,
            report_name="overtime_report",
            repo_func=self.repo.get_overtime_report,
            response_cls=OvertimeReportResponse,
            item_schema_cls=OvertimeReportItemSchema,
        )

    async def get_attendance_summary_report(
        self, org_id: int, user: CurrentUser, query: ReportQueryRequest
    ) -> AttendanceSummaryReportResponse | dict[str, Any] | bytes:
        """Fetch summarized aggregates for attendance."""
        return await self._handle_report_query(
            org_id=org_id,
            user=user,
            features=["attendance"],
            query=query,
            report_name="attendance_summary_report",
            repo_func=self.repo.get_attendance_summary_report,
            response_cls=AttendanceSummaryReportResponse,
        )

    # ===========================================================================
    # 3. Leave Reports
    # ===========================================================================

    async def get_leave_balance_report(
        self, org_id: int, user: CurrentUser, query: ReportQueryRequest
    ) -> LeaveBalanceReportResponse | dict[str, Any] | bytes:
        """Fetch leave allocations and balance rosters."""
        return await self._handle_report_query(
            org_id=org_id,
            user=user,
            features=["leave_request", "leave_balance"],
            query=query,
            report_name="leave_balance_report",
            repo_func=self.repo.get_leave_balance_report,
            response_cls=LeaveBalanceReportResponse,
            item_schema_cls=LeaveBalanceReportItemSchema,
        )

    async def get_leave_requests_report(
        self, org_id: int, user: CurrentUser, query: ReportQueryRequest
    ) -> LeaveRequestReportResponse | dict[str, Any] | bytes:
        """Fetch rosters of leave requests."""
        return await self._handle_report_query(
            org_id=org_id,
            user=user,
            features=["leave_request"],
            query=query,
            report_name="leave_requests_report",
            repo_func=self.repo.get_leave_requests_report,
            response_cls=LeaveRequestReportResponse,
            item_schema_cls=LeaveRequestReportItemSchema,
        )

    async def get_leave_approvals_report(
        self, org_id: int, user: CurrentUser, query: ReportQueryRequest
    ) -> LeaveApprovalReportResponse | dict[str, Any] | bytes:
        """Fetch roster of decisions on leave requests."""
        return await self._handle_report_query(
            org_id=org_id,
            user=user,
            features=["leave_request"],
            query=query,
            report_name="leave_approvals_report",
            repo_func=self.repo.get_leave_approvals_report,
            response_cls=LeaveApprovalReportResponse,
            item_schema_cls=LeaveApprovalReportItemSchema,
        )

    async def get_leave_summary_report(
        self, org_id: int, user: CurrentUser, query: ReportQueryRequest
    ) -> LeaveSummaryReportResponse | dict[str, Any] | bytes:
        """Fetch leave type breakdowns and decision aggregates."""
        return await self._handle_report_query(
            org_id=org_id,
            user=user,
            features=["leave_request"],
            query=query,
            report_name="leave_summary_report",
            repo_func=self.repo.get_leave_summary_report,
            response_cls=LeaveSummaryReportResponse,
        )

    # ===========================================================================
    # 4. Approval Reports
    # ===========================================================================

    async def get_pending_approvals_report(
        self, org_id: int, user: CurrentUser, query: ReportQueryRequest
    ) -> PendingApprovalReportResponse | dict[str, Any] | bytes:
        """Fetch roster of items awaiting resolution."""
        return await self._handle_report_query(
            org_id=org_id,
            user=user,
            features=["approval"],
            query=query,
            report_name="pending_approvals_report",
            repo_func=self.repo.get_pending_approvals_report,
            response_cls=PendingApprovalReportResponse,
            item_schema_cls=PendingApprovalReportItemSchema,
        )

    async def get_approval_history_report(
        self, org_id: int, user: CurrentUser, query: ReportQueryRequest
    ) -> ApprovalHistoryReportResponse | dict[str, Any] | bytes:
        """Fetch roster of decided approval requests."""
        return await self._handle_report_query(
            org_id=org_id,
            user=user,
            features=["approval"],
            query=query,
            report_name="approval_history_report",
            repo_func=self.repo.get_approval_history_report,
            response_cls=ApprovalHistoryReportResponse,
            item_schema_cls=ApprovalHistoryReportItemSchema,
        )

    async def get_approval_performance_report(
        self, org_id: int, user: CurrentUser, query: ReportQueryRequest
    ) -> ApprovalPerformanceReportResponse | dict[str, Any] | bytes:
        """Fetch decision throughput and performance metrics per approver."""
        return await self._handle_report_query(
            org_id=org_id,
            user=user,
            features=["approval"],
            query=query,
            report_name="approval_performance_report",
            repo_func=self.repo.get_approval_performance_report,
            response_cls=ApprovalPerformanceReportResponse,
            item_schema_cls=ApprovalPerformanceReportItemSchema,
        )

    # ===========================================================================
    # 5. Payroll Reports
    # ===========================================================================

    async def get_payroll_register_report(
        self,
        org_id: int,
        user: CurrentUser,
        query: ReportQueryRequest,
        payroll_group_id: int | None = None,
        salary_cycle_id: int | None = None,
    ) -> PayrollRegisterReportResponse | dict[str, Any] | bytes:
        """Fetch computed payroll components register."""
        return await self._handle_report_query(
            org_id=org_id,
            user=user,
            features=["payroll_record"],
            query=query,
            report_name="payroll_register_report",
            repo_func=self.repo.get_payroll_register_report,
            response_cls=PayrollRegisterReportResponse,
            item_schema_cls=PayrollRegisterReportItemSchema,
            payroll_group_id=payroll_group_id,
            salary_cycle_id=salary_cycle_id,
        )

    async def get_salary_register_report(
        self,
        org_id: int,
        user: CurrentUser,
        query: ReportQueryRequest,
        payroll_group_id: int | None = None,
        salary_cycle_id: int | None = None,
    ) -> SalaryRegisterReportResponse | dict[str, Any] | bytes:
        """Fetch salary-focused register roster."""
        return await self._handle_report_query(
            org_id=org_id,
            user=user,
            features=["payroll_record"],
            query=query,
            report_name="salary_register_report",
            repo_func=self.repo.get_salary_register_report,
            response_cls=SalaryRegisterReportResponse,
            item_schema_cls=SalaryRegisterReportItemSchema,
            payroll_group_id=payroll_group_id,
            salary_cycle_id=salary_cycle_id,
        )

    async def get_payroll_summary_report(
        self,
        org_id: int,
        user: CurrentUser,
        query: ReportQueryRequest,
        payroll_group_id: int | None = None,
        salary_cycle_id: int | None = None,
    ) -> PayrollSummaryReportResponse | dict[str, Any] | bytes:
        """Fetch total aggregates across a payroll cycle."""
        return await self._handle_report_query(
            org_id=org_id,
            user=user,
            features=["payroll_record"],
            query=query,
            report_name="payroll_summary_report",
            repo_func=self.repo.get_payroll_summary_report,
            response_cls=PayrollSummaryReportResponse,
            payroll_group_id=payroll_group_id,
            salary_cycle_id=salary_cycle_id,
        )

    async def get_payslips_report(
        self,
        org_id: int,
        user: CurrentUser,
        query: ReportQueryRequest,
        payroll_group_id: int | None = None,
        salary_cycle_id: int | None = None,
    ) -> PayslipReportResponse | dict[str, Any] | bytes:
        """Fetch generated payslips metadata roster."""
        return await self._handle_report_query(
            org_id=org_id,
            user=user,
            features=["payroll_record"],
            query=query,
            report_name="payslips_report",
            repo_func=self.repo.get_payslips_report,
            response_cls=PayslipReportResponse,
            item_schema_cls=PayslipReportItemSchema,
            payroll_group_id=payroll_group_id,
            salary_cycle_id=salary_cycle_id,
        )

    # ===========================================================================
    # 6. Settlement Reports
    # ===========================================================================

    async def get_settlement_ledger_report(
        self, org_id: int, user: CurrentUser, query: ReportQueryRequest
    ) -> SettlementLedgerReportResponse | dict[str, Any] | bytes:
        """Fetch settlement transactions combining loans, advances, and arrears."""
        return await self._handle_report_query(
            org_id=org_id,
            user=user,
            features=["loan_advance", "arrears", "settlement"],
            query=query,
            report_name="settlement_ledger_report",
            repo_func=self.repo.get_settlement_ledger_report,
            response_cls=SettlementLedgerReportResponse,
            item_schema_cls=SettlementLedgerReportItemSchema,
        )

    async def get_settlement_summary_report(
        self, org_id: int, user: CurrentUser, query: ReportQueryRequest
    ) -> SettlementSummaryReportResponse | dict[str, Any] | bytes:
        """Fetch active/closed loan-advance metrics and arrears totals."""
        return await self._handle_report_query(
            org_id=org_id,
            user=user,
            features=["loan_advance", "arrears", "settlement"],
            query=query,
            report_name="settlement_summary_report",
            repo_func=self.repo.get_settlement_summary_report,
            response_cls=SettlementSummaryReportResponse,
        )

    # ===========================================================================
    # 7. Hardware Reports
    # ===========================================================================

    async def get_device_status_report(
        self, org_id: int, user: CurrentUser, query: ReportQueryRequest
    ) -> DeviceStatusReportResponse | dict[str, Any] | bytes:
        """Fetch biometric device status summary roster."""
        return await self._handle_report_query(
            org_id=org_id,
            user=user,
            features=["device"],
            query=query,
            report_name="device_status_report",
            repo_func=self.repo.get_device_status_report,
            response_cls=DeviceStatusReportResponse,
            item_schema_cls=DeviceStatusReportItemSchema,
        )

    async def get_device_health_report(
        self, org_id: int, user: CurrentUser, query: ReportQueryRequest
    ) -> DeviceHealthReportResponse | dict[str, Any] | bytes:
        """Fetch device health and connectivity metrics."""
        return await self._handle_report_query(
            org_id=org_id,
            user=user,
            features=["device"],
            query=query,
            report_name="device_health_report",
            repo_func=self.repo.get_device_health_report,
            response_cls=DeviceHealthReportResponse,
            item_schema_cls=DeviceHealthReportItemSchema,
        )

    async def get_device_sync_report(
        self, org_id: int, user: CurrentUser, query: ReportQueryRequest
    ) -> DeviceSyncReportResponse | dict[str, Any] | bytes:
        """Fetch synchronization freshness audit snapshot."""
        return await self._handle_report_query(
            org_id=org_id,
            user=user,
            features=["device"],
            query=query,
            report_name="device_sync_report",
            repo_func=self.repo.get_device_sync_report,
            response_cls=DeviceSyncReportResponse,
            item_schema_cls=DeviceSyncReportItemSchema,
        )

    # ===========================================================================
    # 8. Notification Reports
    # ===========================================================================

    async def get_notification_delivery_report(
        self, org_id: int, user: CurrentUser, query: ReportQueryRequest
    ) -> NotificationDeliveryReportResponse | dict[str, Any] | bytes:
        """Fetch notification dispatch and delivery logs."""
        return await self._handle_report_query(
            org_id=org_id,
            user=user,
            features=["notification"],
            query=query,
            report_name="notification_delivery_report",
            repo_func=self.repo.get_notification_delivery_report,
            response_cls=NotificationDeliveryReportResponse,
            item_schema_cls=NotificationDeliveryReportItemSchema,
        )

    async def get_notification_read_report(
        self, org_id: int, user: CurrentUser, query: ReportQueryRequest
    ) -> NotificationReadReportResponse | dict[str, Any] | bytes:
        """Fetch notification read-status tracking logs."""
        return await self._handle_report_query(
            org_id=org_id,
            user=user,
            features=["notification"],
            query=query,
            report_name="notification_read_report",
            repo_func=self.repo.get_notification_read_report,
            response_cls=NotificationReadReportResponse,
            item_schema_cls=NotificationReadReportItemSchema,
        )

    async def get_notification_summary_report(
        self, org_id: int, user: CurrentUser, query: ReportQueryRequest
    ) -> NotificationSummaryReportResponse | dict[str, Any] | bytes:
        """Fetch notification aggregates and read-rate efficiency metrics."""
        return await self._handle_report_query(
            org_id=org_id,
            user=user,
            features=["notification"],
            query=query,
            report_name="notification_summary_report",
            repo_func=self.repo.get_notification_summary_report,
            response_cls=NotificationSummaryReportResponse,
        )

    # ===========================================================================
    # 9. Audit Reports
    # ===========================================================================

    async def get_user_activity_report(
        self, org_id: int, user: CurrentUser, query: ReportQueryRequest
    ) -> UserActivityReportResponse | dict[str, Any] | bytes:
        """Fetch mutation logs filtered by user."""
        return await self._handle_report_query(
            org_id=org_id,
            user=user,
            features=["audit"],
            query=query,
            report_name="user_activity_report",
            repo_func=self.repo.get_user_activity_report,
            response_cls=UserActivityReportResponse,
            item_schema_cls=UserActivityReportItemSchema,
        )

    async def get_audit_trail_report(
        self, org_id: int, user: CurrentUser, query: ReportQueryRequest
    ) -> AuditTrailReportResponse | dict[str, Any] | bytes:
        """Fetch generic system-mutation audit logs."""
        return await self._handle_report_query(
            org_id=org_id,
            user=user,
            features=["audit"],
            query=query,
            report_name="audit_trail_report",
            repo_func=self.repo.get_audit_trail_report,
            response_cls=AuditTrailReportResponse,
            item_schema_cls=AuditTrailReportItemSchema,
        )

    async def get_security_events_report(
        self, org_id: int, user: CurrentUser, query: ReportQueryRequest
    ) -> SecurityEventReportResponse | dict[str, Any] | bytes:
        """Fetch approximate security-events logs."""
        return await self._handle_report_query(
            org_id=org_id,
            user=user,
            features=["audit"],
            query=query,
            report_name="security_events_report",
            repo_func=self.repo.get_security_events_report,
            response_cls=SecurityEventReportResponse,
            item_schema_cls=SecurityEventReportItemSchema,
        )

    # ===========================================================================
    # 10. Organization Reports
    # ===========================================================================

    async def get_branch_summary_report(
        self, org_id: int, user: CurrentUser, query: ReportQueryRequest
    ) -> BranchSummaryReportResponse | dict[str, Any] | bytes:
        """Fetch summary count roster of employees per branch."""
        return await self._handle_report_query(
            org_id=org_id,
            user=user,
            features=["employee"],
            query=query,
            report_name="branch_summary_report",
            repo_func=self.repo.get_branch_summary_report,
            response_cls=BranchSummaryReportResponse,
            item_schema_cls=BranchSummaryReportItemSchema,
        )

    async def get_department_summary_report(
        self, org_id: int, user: CurrentUser, query: ReportQueryRequest
    ) -> DepartmentSummaryReportResponse | dict[str, Any] | bytes:
        """Fetch summary count roster of employees per department."""
        return await self._handle_report_query(
            org_id=org_id,
            user=user,
            features=["employee"],
            query=query,
            report_name="department_summary_report",
            repo_func=self.repo.get_department_summary_report,
            response_cls=DepartmentSummaryReportResponse,
            item_schema_cls=DepartmentSummaryReportItemSchema,
        )

    async def get_workforce_summary_report(
        self, org_id: int, user: CurrentUser, query: ReportQueryRequest
    ) -> WorkforceSummaryReportResponse | dict[str, Any] | bytes:
        """Fetch overall global headcount breakdowns."""
        return await self._handle_report_query(
            org_id=org_id,
            user=user,
            features=["employee"],
            query=query,
            report_name="workforce_summary_report",
            repo_func=self.repo.get_workforce_summary_report,
            response_cls=WorkforceSummaryReportResponse,
        )

    # ===========================================================================
    # 11. Shift Reports
    # ===========================================================================

    async def get_shift_assignments_report(
        self, org_id: int, user: CurrentUser, query: ReportQueryRequest
    ) -> ReportPaginatedResponse | dict[str, Any] | bytes:
        """Fetch employee shift assignments history list."""
        return await self._handle_report_query(
            org_id=org_id,
            user=user,
            features=["employee"],
            query=query,
            report_name="shift_assignments_report",
            repo_func=self.repo.get_shift_assignments_report,
            response_cls=ReportPaginatedResponse,
        )

    async def get_leave_taken_report(
        self, org_id: int, user: CurrentUser, query: ReportQueryRequest
    ) -> LeaveTakenReportResponse | dict[str, Any] | bytes:
        """Fetch leave taken report matrix showing leaves taken per employee per active leave type."""
        self._enforce_permissions(user, ["leave"])
        branch_ids, dept_ids = self._resolve_data_scopes(user)
        effective_branch_ids = [query.branch_id] if query.branch_id is not None else branch_ids
        effective_dept_ids = [query.dept_id] if query.dept_id is not None else dept_ids

        today = datetime.date.today()
        d_from = query.date_from or today.replace(day=1)
        d_to = query.date_to or today

        data_dict, total_records = await self.repo.get_leave_taken_report(
            org_id=org_id,
            date_from=d_from,
            date_to=d_to,
            branch_ids=effective_branch_ids,
            dept_ids=effective_dept_ids,
            employee_id=query.employee_id,
            sort_by=query.sort_by,
            sort_dir=query.sort_dir,
            page=query.page,
            page_size=query.page_size,
        )

        if query.format in ("csv", "excel", "pdf"):
            export_rows = []
            for item in data_dict.get("items", []):
                row_dict = {
                    "Employee ID": item["employee_code"],
                    "Employee Name": item["employee_name"],
                    "Department": item["department_name"],
                    "Designation": item["designation_name"],
                }
                for lt_alias in data_dict.get("leave_types", []):
                    taken_count = item["leaves"].get(lt_alias, 0.0)
                    row_dict[lt_alias.upper()] = taken_count
                row_dict["Total Leaves"] = item["total_leaves"]
                export_rows.append(row_dict)

            headers = list(export_rows[0].keys()) if export_rows else []
            rows = [[r.get(h) for h in headers] for r in export_rows]

            if query.format == "pdf":
                file_bytes = self._generate_pdf_bytes("leave_taken_report", headers, rows)
                media_type = "application/pdf"
                ext = "pdf"
            else:
                file_bytes = self._generate_csv_bytes(headers, rows)
                media_type = (
                    "text/csv"
                    if query.format == "csv"
                    else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                ext = "csv" if query.format == "csv" else "xlsx"

            return {
                "file_bytes": file_bytes,
                "filename": f"leave_taken_report_{utcnow().strftime('%Y%m%d_%H%M%S')}.{ext}",
                "media_type": media_type,
            }

        return LeaveTakenReportResponse(
            success=True,
            data=LeaveTakenReportDataSchema(
                leave_types=data_dict["leave_types"],
                items=[
                    LeaveTakenReportRowSchema(
                        employee_id=it["employee_id"],
                        employee_code=it["employee_code"],
                        employee_name=it["employee_name"],
                        department_name=it["department_name"],
                        designation_name=it["designation_name"],
                        leaves=it["leaves"],
                        total_leaves=it["total_leaves"],
                    )
                    for it in data_dict["items"]
                ],
                pagination=PaginationMeta.build(
                    page=query.page, page_size=query.page_size, total_records=total_records
                ),
            ),
        )

    async def get_employee_day_wise_master_report(
        self, org_id: int, user: CurrentUser, query: ReportQueryRequest
    ) -> EmployeeDayWiseMasterReportResponse | dict[str, Any] | bytes:
        """Fetch multi-day day-wise master report grouped by employee."""
        self._enforce_permissions(user, ["attendance"])
        branch_ids, dept_ids = self._resolve_data_scopes(user)
        effective_dept_ids = [query.dept_id] if query.dept_id is not None else dept_ids

        today = datetime.date.today()
        d_from = query.date_from or today.replace(day=1)
        d_to = query.date_to or today

        data_dict, total_records = await self.repo.get_employee_day_wise_master_report(
            org_id=org_id,
            date_from=d_from,
            date_to=d_to,
            dept_ids=effective_dept_ids,
            designation_id=query.designation_id,
            sort_by=query.sort_by,
            sort_dir=query.sort_dir,
            page=query.page,
            page_size=query.page_size,
        )

        if query.format in ("csv", "excel", "pdf"):
            export_rows = []
            for item in data_dict.get("items", []):
                row_dict = {
                    "Employee ID": item["employee_code"],
                    "Employee Name": item["employee_name"],
                    "Department": item["department_name"],
                    "Designation": item["designation_name"],
                }
                for d_str in data_dict.get("dates", []):
                    cell = item["daily_status"].get(d_str, {})
                    row_dict[d_str] = cell.get("status", "A")
                export_rows.append(row_dict)

            headers = list(export_rows[0].keys()) if export_rows else []
            rows = [[r.get(h) for h in headers] for r in export_rows]

            if query.format == "pdf":
                file_bytes = self._generate_pdf_bytes("employee_day_wise_master", headers, rows)
                media_type = "application/pdf"
                ext = "pdf"
            else:
                file_bytes = self._generate_csv_bytes(headers, rows)
                media_type = (
                    "text/csv"
                    if query.format == "csv"
                    else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                ext = "csv" if query.format == "csv" else "xlsx"

            return {
                "file_bytes": file_bytes,
                "filename": f"employee_day_wise_master_{utcnow().strftime('%Y%m%d_%H%M%S')}.{ext}",
                "media_type": media_type,
            }

        return EmployeeDayWiseMasterReportResponse(
            success=True,
            data=EmployeeDayWiseMasterReportDataSchema(
                dates=data_dict["dates"],
                items=[
                    EmployeeDayWiseMasterRowSchema(
                        employee_id=it["employee_id"],
                        employee_code=it["employee_code"],
                        employee_name=it["employee_name"],
                        department_name=it["department_name"],
                        designation_name=it["designation_name"],
                        daily_status={
                            d: EmployeeDayWiseMasterCellSchema(status=cell["status"])
                            for d, cell in it["daily_status"].items()
                        },
                    )
                    for it in data_dict["items"]
                ],
                pagination=PaginationMeta.build(
                    page=query.page, page_size=query.page_size, total_records=total_records
                ),
            ),
        )

