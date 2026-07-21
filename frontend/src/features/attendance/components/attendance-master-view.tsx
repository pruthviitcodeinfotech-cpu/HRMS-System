"use client";

import React, { useState, useMemo, useEffect } from "react";
import * as XLSX from "xlsx";
import { toast } from "sonner";
import {
  AttendanceRecord,
  AttendanceFilter,
  AttendancePagination,
  SortField,
  SortOrder,
  AttendanceStatus,
} from "../types/attendance";
import { AttendanceFilterBar } from "./attendance-filter";
import { AttendanceTable } from "./attendance-table";
import { AttendancePaginationFooter } from "./attendance-pagination";
import { AttendanceEmptyState } from "./attendance-empty";
import { AttendanceLoadingSkeleton } from "./attendance-loading";
import { useAttendanceDays } from "../hooks/use-attendance";
import { AttendanceDailyQueryParams } from "../services/attendance";

const formatPunchTime = (isoString?: string | null): string => {
  if (!isoString) return "-";
  try {
    const d = new Date(isoString);
    if (isNaN(d.getTime())) return isoString;
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: true });
  } catch {
    return "-";
  }
};

const mapBackendStatus = (status?: string): AttendanceStatus => {
  switch (status) {
    case "present":
      return "FD";
    case "absent":
      return "Absent";
    case "half_day":
      return "Half Day";
    case "week_off":
      return "Weekly Off";
    case "holiday":
      return "Holiday";
    case "on_leave":
      return "Leave";
    default:
      return status ? (status as AttendanceStatus) : "Absent";
  }
};

export const AttendanceMasterView: React.FC = () => {
  const todayStr = useMemo(() => new Date().toISOString().slice(0, 10), []);

  const [filter, setFilter] = useState<AttendanceFilter>({
    fromDate: todayStr,
    toDate: todayStr,
    branchId: "",
  });
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(10);
  const [sortField, setSortField] = useState<SortField>("employeeId");
  const [sortOrder, setSortOrder] = useState<SortOrder>("desc");

  // Construct query parameters for server-side pagination, searching & filtering
  const queryParams: AttendanceDailyQueryParams = useMemo(() => {
    const params: AttendanceDailyQueryParams = {
      branch_id: filter.branchId ? Number(filter.branchId) : undefined,
      page: currentPage,
      page_size: pageSize,
    };

    if (filter.fromDate && filter.toDate) {
      if (filter.fromDate === filter.toDate) {
        params.date = filter.fromDate;
      } else {
        params.date_from = filter.fromDate;
        params.date_to = filter.toDate;
      }
    } else if (filter.fromDate) {
      params.date = filter.fromDate;
    } else {
      params.date = todayStr;
    }

    return params;
  }, [filter.fromDate, filter.toDate, filter.branchId, currentPage, pageSize, todayStr]);

  // Live backend API integration with React Query hook
  const { data, isLoading, isError, error } = useAttendanceDays(queryParams);

  useEffect(() => {
    if (isError && error) {
      toast.error(error instanceof Error ? error.message : "Failed to load attendance records");
    }
  }, [isError, error]);

  // Map live backend items to UI attendance records
  const rawRecords: AttendanceRecord[] = useMemo(() => {
    if (!data?.items) return [];
    return data.items.map((item) => {
      const dateVal = item.attendance_date || queryParams.date || todayStr;
      const dayName = new Date(dateVal).toLocaleDateString("en-US", { weekday: "long" });

      let workingHrsStr = "-";
      if (item.working_hours !== undefined && item.working_hours !== null) {
        workingHrsStr = `${item.working_hours}h`;
      } else if (item.worked_minutes) {
        const hrs = Math.floor(item.worked_minutes / 60);
        const mins = item.worked_minutes % 60;
        workingHrsStr = `${hrs}h ${mins}m`;
      }

      return {
        id: item.id ? String(item.id) : `${item.employee_id}-${dateVal}`,
        employeeId: item.employee_code || String(item.employee_id),
        employeeName: item.employee_name || `Employee ${item.employee_id}`,
        department: item.department_name || "-",
        designation: item.designation || "-",
        date: dateVal,
        day: dayName,
        firstPunch: formatPunchTime(item.first_punch || item.first_in),
        lastPunch: formatPunchTime(item.last_punch || item.last_out),
        totalWorkingHours: workingHrsStr,
        totalBreakHours:
          item.break_hours !== undefined && item.break_hours !== null
            ? `${item.break_hours}h`
            : "-",
        status: mapBackendStatus(item.status),
        hasAnomaly: item.late_minutes > 0 || item.status === "absent",
      };
    });
  }, [data, queryParams.date, todayStr]);

  // Apply sorting locally on current page records
  const records = useMemo(() => {
    if (!rawRecords || rawRecords.length === 0) return [];
    return [...rawRecords].sort((a, b) => {
      let valA = a[sortField] ?? "";
      let valB = b[sortField] ?? "";

      if (sortField === "employeeId") {
        const numA = Number(String(valA).replace(/\D/g, "")) || 0;
        const numB = Number(String(valB).replace(/\D/g, "")) || 0;
        return sortOrder === "asc" ? numA - numB : numB - numA;
      }

      if (typeof valA === "string") valA = valA.toLowerCase();
      if (typeof valB === "string") valB = valB.toLowerCase();

      if (valA < valB) return sortOrder === "asc" ? -1 : 1;
      if (valA > valB) return sortOrder === "asc" ? 1 : -1;
      return 0;
    });
  }, [rawRecords, sortField, sortOrder]);

  // Sorting Handler
  const handleSort = (field: SortField) => {
    let newOrder: SortOrder = "asc";
    if (sortField === field && sortOrder === "asc") {
      newOrder = "desc";
    }
    setSortField(field);
    setSortOrder(newOrder);
  };

  // Search Filter Handler
  const handleSearch = (newFilter: AttendanceFilter) => {
    setFilter(newFilter);
    setCurrentPage(1);
  };

  // Filter Reset Handler
  const handleResetFilters = () => {
    setFilter({
      fromDate: todayStr,
      toDate: todayStr,
      branchId: "",
    });
    setCurrentPage(1);
  };

  // Export Excel Functionality
  const handleExportExcel = () => {
    if (records.length === 0) {
      toast.error("No attendance records to export.");
      return;
    }

    const exportData = records.map((r) => ({
      "Employee ID": r.employeeId,
      "Employee Name": r.employeeName,
      Department: r.department,
      Designation: r.designation,
      Date: r.date,
      Day: r.day,
      "First Punch": r.firstPunch,
      "Last Punch": r.lastPunch,
      "Total Working Hours": r.totalWorkingHours,
      "Total Break Hours": r.totalBreakHours,
      Status: r.status,
    }));

    const worksheet = XLSX.utils.json_to_sheet(exportData);
    const workbook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(workbook, worksheet, "Attendance Master");

    const fileName = `Attendance_Master_${queryParams.date}.xlsx`;
    XLSX.writeFile(workbook, fileName);
    toast.success("Attendance Master exported to Excel successfully!");
  };

  // Export PDF Functionality
  const handleExportPdf = () => {
    if (records.length === 0) {
      toast.error("No attendance records to export.");
      return;
    }

    const printWindow = window.open("", "_blank");
    if (!printWindow) {
      toast.error("Please allow popups to export PDF.");
      return;
    }

    const tableRowsHtml = records
      .map(
        (r) => `
      <tr>
        <td style="padding: 8px; border: 1px solid #e2e8f0; font-weight: bold;">${r.employeeId}</td>
        <td style="padding: 8px; border: 1px solid #e2e8f0;">${r.employeeName}</td>
        <td style="padding: 8px; border: 1px solid #e2e8f0;">${r.department}</td>
        <td style="padding: 8px; border: 1px solid #e2e8f0;">${r.designation}</td>
        <td style="padding: 8px; border: 1px solid #e2e8f0;">${r.date}</td>
        <td style="padding: 8px; border: 1px solid #e2e8f0;">${r.day}</td>
        <td style="padding: 8px; border: 1px solid #e2e8f0;">${r.firstPunch}</td>
        <td style="padding: 8px; border: 1px solid #e2e8f0;">${r.lastPunch}</td>
        <td style="padding: 8px; border: 1px solid #e2e8f0;">${r.totalWorkingHours}</td>
        <td style="padding: 8px; border: 1px solid #e2e8f0;">${r.totalBreakHours}</td>
        <td style="padding: 8px; border: 1px solid #e2e8f0; font-weight: bold;">${r.status}</td>
      </tr>
    `
      )
      .join("");

    const htmlContent = `
      <!DOCTYPE html>
      <html>
        <head>
          <title>Attendance Master Report</title>
          <style>
            body { font-family: Arial, sans-serif; padding: 20px; color: #1e293b; }
            h1 { text-align: center; color: #0284c7; margin-bottom: 5px; }
            p.meta { text-align: center; font-size: 12px; color: #64748b; margin-bottom: 20px; }
            table { width: 100%; border-collapse: collapse; font-size: 11px; }
            th { background-color: #f0f9ff; padding: 10px 8px; border: 1px solid #cbd5e1; text-align: left; font-weight: bold; color: #0f172a; }
            @media print {
              body { padding: 0; }
              @page { size: landscape; margin: 10mm; }
            }
          </style>
        </head>
        <body>
          <h1>Attendance Master Report</h1>
          <p class="meta">Date: ${queryParams.date} | Total Records: ${data?.pagination?.total_records || records.length}</p>
          <table>
            <thead>
              <tr>
                <th>Emp ID</th>
                <th>Employee Name</th>
                <th>Department</th>
                <th>Designation</th>
                <th>Date</th>
                <th>Day</th>
                <th>First Punch</th>
                <th>Last Punch</th>
                <th>Working Hours</th>
                <th>Break Hours</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              ${tableRowsHtml}
            </tbody>
          </table>
          <script>
            window.onload = function() {
              window.print();
            };
          </script>
        </body>
      </html>
    `;

    printWindow.document.write(htmlContent);
    printWindow.document.close();
    toast.success("Attendance Master PDF print preview opened!");
  };

  // Build reactive pagination state for UI controls
  const paginationInfo: AttendancePagination = useMemo(() => {
    const totalRecords = data?.pagination?.total_records ?? 0;
    const totalPages =
      data?.pagination?.total_pages ?? (totalRecords > 0 ? Math.ceil(totalRecords / pageSize) : 1);
    return {
      currentPage,
      pageSize,
      totalRecords,
      totalPages: Math.max(1, totalPages),
    };
  }, [currentPage, pageSize, data?.pagination?.total_records, data?.pagination?.total_pages]);

  return (
    <div className="p-6 space-y-6">
      {/* Header Title */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
          Attendance Master
        </h1>
      </div>

      {/* Filter Bar */}
      <AttendanceFilterBar
        onSearch={handleSearch}
        onReset={handleResetFilters}
        onExportExcel={handleExportExcel}
        onExportPdf={handleExportPdf}
      />

      {/* Main Content Area: Table / Loading / Empty */}
      {isLoading ? (
        <AttendanceLoadingSkeleton rows={pageSize} />
      ) : records.length === 0 ? (
        <AttendanceEmptyState onReset={handleResetFilters} />
      ) : (
        <div className="space-y-0">
          <AttendanceTable
            records={records}
            sortField={sortField}
            sortOrder={sortOrder}
            onSort={handleSort}
          />
          <AttendancePaginationFooter
            pagination={paginationInfo}
            onPageChange={(page) => setCurrentPage(page)}
            onPageSizeChange={(size) => {
              setPageSize(size);
              setCurrentPage(1);
            }}
          />
        </div>
      )}
    </div>
  );
};
