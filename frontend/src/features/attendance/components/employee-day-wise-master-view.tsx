"use client";

import React, { useState, useMemo } from "react";
import {
  CalendarDays,
  FileSpreadsheet,
  ArrowUpDown,
  ChevronLeft,
  ChevronRight,
  RefreshCw,
  AlertTriangle,
} from "lucide-react";
import { toast } from "sonner";
import * as XLSX from "xlsx";

import { useDepartments, useDesignations } from "@/features/employees/hooks";
import { useEmployeeDayWiseMasterReport } from "../hooks/use-attendance";

const getStatusStyles = (status: string): string => {
  switch (status) {
    case "P":
      return "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-400 font-semibold";
    case "A":
      return "bg-rose-50 text-rose-700 dark:bg-rose-950/30 dark:text-rose-400 font-semibold";
    case "HD":
      return "bg-amber-50 text-amber-700 dark:bg-amber-950/30 dark:text-amber-400 font-semibold";
    case "WO":
      return "bg-slate-100 text-slate-500 dark:bg-slate-800/40 dark:text-slate-400 font-normal";
    case "H":
      return "bg-purple-50 text-purple-700 dark:bg-purple-950/30 dark:text-purple-400 font-semibold";
    case "L":
      return "bg-sky-50 text-sky-700 dark:bg-sky-950/30 dark:text-sky-400 font-semibold";
    case "LWP":
      return "bg-orange-50 text-orange-700 dark:bg-orange-950/30 dark:text-orange-400 font-semibold";
    case "CO":
      return "bg-teal-50 text-teal-700 dark:bg-teal-950/30 dark:text-teal-400 font-semibold";
    default:
      return "bg-slate-50 text-slate-600 dark:bg-slate-900 dark:text-slate-300";
  }
};

const getDatesInRange = (startDate: string, endDate: string): string[] => {
  const start = new Date(startDate);
  const end = new Date(endDate);
  const dates: string[] = [];

  if (isNaN(start.getTime()) || isNaN(end.getTime()) || start > end) {
    return [];
  }

  const curr = new Date(start);
  const limitDate = new Date(start);
  limitDate.setDate(limitDate.getDate() + 31);
  const realEnd = end > limitDate ? limitDate : end;

  while (curr <= realEnd) {
    dates.push(curr.toISOString().slice(0, 10));
    curr.setDate(curr.getDate() + 1);
  }
  return dates;
};

export const EmployeeDayWiseMasterView: React.FC = () => {
  const firstOfMonthStr = useMemo(() => {
    const d = new Date();
    d.setDate(1);
    return d.toISOString().slice(0, 10);
  }, []);

  const todayStr = useMemo(() => new Date().toISOString().slice(0, 10), []);

  // Filter states
  const [fromDate, setFromDate] = useState<string>(firstOfMonthStr);
  const [toDate, setToDate] = useState<string>(todayStr);
  const [searchFromDate, setSearchFromDate] = useState<string>(firstOfMonthStr);
  const [searchToDate, setSearchToDate] = useState<string>(todayStr);

  const [deptFilter, setDeptFilter] = useState<string>("");
  const [desFilter, setDesFilter] = useState<string>("");
  const [searchDept, setSearchDept] = useState<string>("");
  const [searchDes, setSearchDes] = useState<string>("");

  // Pagination & Sorting
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(10);
  const [sortField, setSortField] = useState<string>("employee_code");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("asc");

  // Dynamic dropdowns
  const { data: deptsData } = useDepartments({ page_size: 100 });
  const { data: desigsData } = useDesignations({ page_size: 100 });

  const departmentOptions = deptsData?.items || [];
  const designationOptions = desigsData?.items || [];

  // Query parameters mapping
  const reportParams = useMemo(() => ({
    date_from: searchFromDate,
    date_to: searchToDate,
    department_id: searchDept ? Number(searchDept) : undefined,
    designation_id: searchDes ? Number(searchDes) : undefined,
    page: currentPage,
    page_size: pageSize,
    sort_by: sortField,
    sort_dir: sortOrder,
  }), [searchFromDate, searchToDate, searchDept, searchDes, currentPage, pageSize, sortField, sortOrder]);

  // Query Hook
  const { data, isLoading, isError, refetch } = useEmployeeDayWiseMasterReport(reportParams);

  // Generate date list (from backend if loaded, otherwise local fallback)
  const dates = useMemo(() => {
    if (data?.dates && data.dates.length > 0) {
      return data.dates;
    }
    return getDatesInRange(searchFromDate, searchToDate);
  }, [data?.dates, searchFromDate, searchToDate]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setCurrentPage(1);
    setSearchFromDate(fromDate);
    setSearchToDate(toDate);
    setSearchDept(deptFilter);
    setSearchDes(desFilter);
  };

  const handleReset = () => {
    setFromDate(firstOfMonthStr);
    setToDate(todayStr);
    setDeptFilter("");
    setDesFilter("");
    setSearchFromDate(firstOfMonthStr);
    setSearchToDate(todayStr);
    setSearchDept("");
    setSearchDes("");
    setCurrentPage(1);
    setSortField("employee_code");
    setSortOrder("asc");
  };

  const toggleSort = (field: string) => {
    if (sortField === field) {
      setSortOrder((prev) => (prev === "asc" ? "desc" : "asc"));
    } else {
      setSortField(field);
      setSortOrder("asc");
    }
    setCurrentPage(1);
  };

  const handleRetry = () => {
    refetch();
  };

  const formatMinutesToHours = (totalMinutes?: number): string => {
    if (!totalMinutes || totalMinutes <= 0) return "-";
    const hours = Math.floor(totalMinutes / 60);
    const minutes = totalMinutes % 60;
    if (hours > 0 && minutes > 0) return `${hours}h ${minutes}m`;
    if (hours > 0) return `${hours}h`;
    return `${minutes}m`;
  };

  const formatOTMinutes = (totalMinutes?: number): string => {
    if (!totalMinutes || totalMinutes <= 0) return "-";
    const hours = Math.floor(totalMinutes / 60);
    const minutes = totalMinutes % 60;
    const hStr = hours < 10 ? `0${hours}` : `${hours}`;
    if (minutes > 0) return `${hStr}h ${String(minutes).padStart(2, "0")}m`;
    return `${hStr}h`;
  };

  const handleExportExcel = () => {
    const itemsToExport = data?.items || [];
    if (itemsToExport.length === 0) {
      toast.error("No data available to export");
      return;
    }

    try {
      const sheetRows: any[][] = [];

      // Build date header titles: 1(Wednesday), 2(Thursday), ...
      const dateHeaders = dates.map((dateStr) => {
        const d = new Date(dateStr);
        const dayNum = d.getDate();
        const weekday = d.toLocaleDateString("en-US", { weekday: "long" });
        return `${dayNum}(${weekday})`;
      });

      itemsToExport.forEach((row, idx) => {
        // Row 1: Employee Header Line
        const headerText = `From: ${searchFromDate} To: ${searchToDate} Employee Name: ${row.employee_name} Department: ${row.department_name} Designation: ${row.designation_name} Employee ID: ${row.employee_code}`;
        sheetRows.push([headerText]);

        // Row 2: Attendance Summary Line
        const summaryText = `Full Day: ${row.full_day_count || 0}  Half Day: ${row.half_day_count || 0}  Absent: ${row.absent_count || 0}  Week Off: ${row.week_off_count || 0}  Paid Leave: ${row.paid_leave_count || 0}  Total Working Hours: ${formatMinutesToHours(row.total_working_minutes)}  Total OT: ${formatOTMinutes(row.total_ot_minutes)}  Total Late In: ${formatMinutesToHours(row.total_late_minutes)}  Total Early Out: ${formatMinutesToHours(row.total_early_out_minutes)}`;
        sheetRows.push([summaryText]);

        // Row 3: Blank separator
        sheetRows.push([]);

        // Row 4: Day Header Row
        sheetRows.push(["Day", ...dateHeaders]);

        // Row 5: Status Row
        sheetRows.push([
          "Status",
          ...dates.map((dateStr) => {
            const cell = row.daily_status[dateStr];
            if (cell?.status_label) return cell.status_label;
            const st = cell?.status || "A";
            switch (st) {
              case "P": return "FD";
              case "HD": return "HD";
              case "WO": return "Week Off";
              case "H": return "Holiday";
              case "L": case "CO": return "Leave";
              case "LWP": return "LWP";
              default: return "Absent";
            }
          }),
        ]);

        // Row 6: First In
        sheetRows.push([
          "First In",
          ...dates.map((dateStr) => row.daily_status[dateStr]?.first_in || "-"),
        ]);

        // Row 7: Last Out
        sheetRows.push([
          "Last Out",
          ...dates.map((dateStr) => row.daily_status[dateStr]?.last_out || "-"),
        ]);

        // Row 8: Total OT
        sheetRows.push([
          "Total OT",
          ...dates.map((dateStr) => formatOTMinutes(row.daily_status[dateStr]?.total_ot_minutes)),
        ]);

        // Row 9: Late In
        sheetRows.push([
          "Late In",
          ...dates.map((dateStr) => formatMinutesToHours(row.daily_status[dateStr]?.late_minutes)),
        ]);

        // Row 10: Early Out
        sheetRows.push([
          "Early Out",
          ...dates.map((dateStr) => formatMinutesToHours(row.daily_status[dateStr]?.early_out_minutes)),
        ]);

        // Row 11: Total Hrs
        sheetRows.push([
          "Total Hrs",
          ...dates.map((dateStr) => formatMinutesToHours(row.daily_status[dateStr]?.working_minutes)),
        ]);

        // Separator between employee blocks (2 blank rows)
        if (idx < itemsToExport.length - 1) {
          sheetRows.push([]);
          sheetRows.push([]);
        }
      });

      const worksheet = XLSX.utils.aoa_to_sheet(sheetRows);
      const workbook = XLSX.utils.book_new();
      XLSX.utils.book_append_sheet(workbook, worksheet, "employee-master");
      XLSX.writeFile(workbook, `Employee-day-wise-master-report.xlsx`);
      toast.success("Excel report exported successfully");
    } catch (err) {
      console.error(err);
      toast.error("Failed to export Excel report");
    }
  };

  const paginatedEmployees = data?.items || [];
  const totalRecords = data?.pagination?.total_records || 0;
  const totalPages = data?.pagination?.total_pages || 1;

  const startRecord = Math.min((currentPage - 1) * pageSize + 1, totalRecords);
  const endRecord = Math.min(currentPage * pageSize, totalRecords);

  return (
    <div className="space-y-6">
      {/* Title Panel */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
              Employee Day Wise Master
            </h1>
          </div>
          <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
            Display detailed daily attendance status mapping per employee.
          </p>
        </div>
      </div>

      {/* Filter Toolbar Card */}
      <div className="bg-white dark:bg-slate-800 p-4 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm">
        <form onSubmit={handleSearch} className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex flex-wrap items-center gap-3">
            {/* Date Range picker */}
            <div className="flex items-center bg-slate-50 dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg p-1.5 shadow-xs">
              <CalendarDays className="w-4 h-4 text-slate-400 ml-2" />
              <input
                type="date"
                aria-label="From Date"
                value={fromDate}
                onChange={(e) => setFromDate(e.target.value)}
                className="bg-transparent border-0 text-sm font-medium text-slate-700 dark:text-slate-200 focus:ring-0 focus:outline-none px-2 py-0.5"
              />
              <span className="text-slate-400 font-medium px-1">—</span>
              <input
                type="date"
                aria-label="To Date"
                value={toDate}
                onChange={(e) => setToDate(e.target.value)}
                className="bg-transparent border-0 text-sm font-medium text-slate-700 dark:text-slate-200 focus:ring-0 focus:outline-none px-2 py-0.5"
              />
            </div>

            {/* Department Dropdown */}
            <div className="flex items-center bg-slate-50 dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg p-1.5 shadow-xs">
              <select
                aria-label="Choose Department"
                value={deptFilter}
                onChange={(e) => setDeptFilter(e.target.value)}
                className="bg-transparent border-0 text-sm font-medium text-slate-700 dark:text-slate-200 focus:ring-0 focus:outline-none px-2 py-0.5"
              >
                <option value="" className="bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100">Select Department</option>
                {departmentOptions.map((dept) => (
                  <option key={dept.dept_id} value={dept.dept_id} className="bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100">
                    {dept.dept_name}
                  </option>
                ))}
              </select>
            </div>

            {/* Designation Dropdown */}
            <div className="flex items-center bg-slate-50 dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg p-1.5 shadow-xs">
              <select
                aria-label="Choose Designation"
                value={desFilter}
                onChange={(e) => setDesFilter(e.target.value)}
                className="bg-transparent border-0 text-sm font-medium text-slate-700 dark:text-slate-200 focus:ring-0 focus:outline-none px-2 py-0.5"
              >
                <option value="" className="bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100">Select Designation</option>
                {designationOptions.map((des) => (
                  <option key={des.designation_id} value={des.designation_id} className="bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100">
                    {des.designation_name}
                  </option>
                ))}
              </select>
            </div>

            {/* Search/Filter Submit */}
            <button
              type="submit"
              className="inline-flex items-center gap-1.5 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-semibold transition-colors cursor-pointer shadow-sm"
            >
              Search
            </button>

            {/* Reset Button */}
            <button
              type="button"
              onClick={handleReset}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 border border-slate-300 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 rounded-lg text-sm font-medium transition-colors cursor-pointer shadow-sm"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              Reset
            </button>
          </div>

          {/* Export Excel Button */}
          <button
            type="button"
            onClick={handleExportExcel}
            className="inline-flex items-center gap-2 px-4 py-2 border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-200 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 rounded-lg text-sm font-medium transition-colors shadow-sm cursor-pointer"
          >
            <FileSpreadsheet className="w-4 h-4 text-emerald-600" />
            Export Excel
          </button>
        </form>
      </div>

      {/* Main Grid View / State Panels */}
      {isError ? (
        <div className="flex flex-col items-center justify-center py-16 px-4 text-center bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-xs">
          <div className="w-12 h-12 rounded-full bg-rose-50 dark:bg-rose-950/30 flex items-center justify-center mb-3 text-rose-500 dark:text-rose-400">
            <AlertTriangle className="h-6 w-6" />
          </div>
          <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 mb-1">
            Failed to load Day Wise Master Report
          </h3>
          <p className="text-xs text-slate-500 dark:text-slate-400 max-w-sm mb-4">
            An unexpected error occurred while processing report data. Please try again.
          </p>
          <button
            type="button"
            onClick={handleRetry}
            className="px-4 py-1.5 text-xs font-semibold bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors cursor-pointer shadow-sm"
          >
            Retry
          </button>
        </div>
      ) : isLoading ? (
        <div className="w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden shadow-sm p-6 space-y-4 animate-pulse">
          <div className="h-4 bg-slate-200 dark:bg-slate-800 rounded-md w-1/4" />
          <div className="border border-slate-100 dark:border-slate-800 rounded-lg overflow-hidden">
            <div className="h-10 bg-slate-100 dark:bg-slate-800/60" />
            <div className="divide-y divide-slate-100 dark:divide-slate-800">
              {Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="h-12 bg-white dark:bg-slate-900" />
              ))}
            </div>
          </div>
        </div>
      ) : paginatedEmployees.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 px-4 text-center bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-xs">
          <div className="w-12 h-12 rounded-full bg-slate-100 dark:bg-slate-800 flex items-center justify-center mb-3 text-slate-400">
            <AlertTriangle className="h-6 w-6" />
          </div>
          <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 mb-1">
            No Records Matches Filters
          </h3>
          <p className="text-xs text-slate-500 dark:text-slate-400 max-w-sm mb-4">
            No employee attendance records matches your selected criteria.
          </p>
          <button
            type="button"
            onClick={handleReset}
            className="px-3.5 py-1.5 text-xs font-semibold text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-950/40 hover:bg-blue-100 dark:hover:bg-blue-900/50 rounded-lg transition-colors cursor-pointer"
          >
            Reset Filters
          </button>
        </div>
      ) : (
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-sm overflow-hidden">
          {/* Outer scroll wrapper */}
          <div className="overflow-x-auto max-w-full">
            <table className="w-full border-collapse text-xs table-fixed">
              <thead>
                <tr className="bg-slate-50 dark:bg-slate-900/80">
                  {/* Sticky Header Columns */}
                  <th
                    onClick={() => toggleSort("employee_code")}
                    className="py-4 px-4 sticky left-0 z-20 bg-slate-50 dark:bg-slate-900 border-b border-r border-slate-200 dark:border-slate-700 w-[100px] text-left font-semibold text-slate-700 dark:text-slate-300 cursor-pointer select-none hover:text-sky-600"
                  >
                    <div className="flex items-center gap-1">
                      <span>Employee ID</span>
                      <ArrowUpDown className="w-3 h-3 opacity-60" />
                    </div>
                  </th>
                  <th
                    onClick={() => toggleSort("employee_name")}
                    className="py-4 px-4 sticky left-[100px] z-20 bg-slate-50 dark:bg-slate-900 border-b border-r border-slate-200 dark:border-slate-700 w-[160px] text-left font-semibold text-slate-700 dark:text-slate-300 cursor-pointer select-none hover:text-sky-600"
                  >
                    <div className="flex items-center gap-1">
                      <span>Employee Name</span>
                      <ArrowUpDown className="w-3 h-3 opacity-60" />
                    </div>
                  </th>
                  <th
                    onClick={() => toggleSort("department_name")}
                    className="py-4 px-4 sticky left-[260px] z-20 bg-slate-50 dark:bg-slate-900 border-b border-r border-slate-200 dark:border-slate-700 w-[120px] text-left font-semibold text-slate-700 dark:text-slate-300 cursor-pointer select-none hover:text-sky-600"
                  >
                    <div className="flex items-center gap-1">
                      <span>Department</span>
                      <ArrowUpDown className="w-3 h-3 opacity-60" />
                    </div>
                  </th>
                  <th
                    onClick={() => toggleSort("designation_name")}
                    className="py-4 px-4 sticky left-[380px] z-20 bg-slate-50 dark:bg-slate-900 border-b border-r border-slate-200 dark:border-slate-700 w-[140px] text-left font-semibold text-slate-700 dark:text-slate-300 cursor-pointer select-none hover:text-sky-600"
                  >
                    <div className="flex items-center gap-1">
                      <span>Designation</span>
                      <ArrowUpDown className="w-3 h-3 opacity-60" />
                    </div>
                  </th>

                  {/* Dynamic Date Columns */}
                  {dates.map((dateStr) => {
                    const d = new Date(dateStr);
                    const day = String(d.getDate()).padStart(2, "0");
                    const month = d.toLocaleDateString("en-US", { month: "short" });
                    const weekday = d.toLocaleDateString("en-US", { weekday: "short" });
                    return (
                      <th
                        key={dateStr}
                        className="py-2 px-1 border-b border-slate-200 dark:border-slate-700 w-[60px] text-center font-semibold text-slate-700 dark:text-slate-300"
                      >
                        <div className="flex flex-col items-center leading-tight">
                          <span className="text-xs font-bold text-slate-800 dark:text-slate-200">{day}</span>
                          <span className="text-[9px] text-slate-500 uppercase font-medium">{month}</span>
                          <span className="text-[9px] text-slate-400 font-normal">{weekday}</span>
                        </div>
                      </th>
                    );
                  })}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                {paginatedEmployees.map((emp) => (
                  <tr key={emp.employee_id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/30">
                    {/* Sticky Employee Columns */}
                    <td className="py-2 px-4 sticky left-0 z-10 bg-white dark:bg-slate-900 border-r border-slate-200 dark:border-slate-800 font-medium text-slate-900 dark:text-slate-100">
                      {emp.employee_code}
                    </td>
                    <td className="py-2 px-4 sticky left-[100px] z-10 bg-white dark:bg-slate-900 border-r border-slate-200 dark:border-slate-800 font-semibold text-slate-700 dark:text-slate-200">
                      {emp.employee_name}
                    </td>
                    <td className="py-2 px-4 sticky left-[260px] z-10 bg-white dark:bg-slate-900 border-r border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400">
                      {emp.department_name}
                    </td>
                    <td className="py-2 px-4 sticky left-[380px] z-10 bg-white dark:bg-slate-900 border-r border-slate-200 dark:border-slate-800 text-slate-500 dark:text-slate-400">
                      {emp.designation_name}
                    </td>

                    {/* Dynamic Date Columns values */}
                    {dates.map((dateStr) => {
                      const status = emp.daily_status[dateStr]?.status || "A";
                      return (
                        <td key={dateStr} className="py-2 px-1 text-center border-r border-slate-100 dark:border-slate-800/40">
                          <div
                            className={`inline-flex items-center justify-center w-8 h-8 rounded-lg text-[10px] ${getStatusStyles(
                              status
                            )}`}
                          >
                            {status}
                          </div>
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Standalone Pagination Footer */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4 py-3.5 px-4 border-t border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-xs">
            <div className="text-slate-600 dark:text-slate-400 font-medium">
              Showing <span className="font-semibold text-slate-900 dark:text-slate-100">{startRecord}</span> to{" "}
              <span className="font-semibold text-slate-900 dark:text-slate-100">{endRecord}</span> of{" "}
              <span className="font-semibold text-slate-900 dark:text-slate-100">{totalRecords}</span> Results
            </div>

            <div className="flex flex-wrap items-center gap-3">
              {/* Rows selector */}
              <div className="flex items-center space-x-1.5">
                <select
                  aria-label="Rows per page"
                  value={pageSize}
                  onChange={(e) => {
                    setPageSize(Number(e.target.value));
                    setCurrentPage(1);
                  }}
                  className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300 font-semibold rounded-lg px-2.5 py-1 focus:outline-none cursor-pointer shadow-xs"
                >
                  <option value={10}>10 / Page</option>
                  <option value={20}>20 / Page</option>
                  <option value={50}>50 / Page</option>
                </select>
              </div>

              {/* Navigation Buttons */}
              <div className="flex items-center space-x-1">
                <button
                  type="button"
                  onClick={() => setCurrentPage((prev) => Math.max(1, prev - 1))}
                  disabled={currentPage === 1}
                  className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-slate-600 dark:text-slate-300 font-medium hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer transition-colors shadow-xs"
                >
                  <ChevronLeft className="h-3.5 w-3.5" />
                  <span>Previous</span>
                </button>

                <div className="text-slate-700 dark:text-slate-300 font-semibold px-2">
                  Page {currentPage} of {totalPages}
                </div>

                <button
                  type="button"
                  onClick={() => setCurrentPage((prev) => Math.min(totalPages, prev + 1))}
                  disabled={currentPage === totalPages}
                  className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-slate-600 dark:text-slate-300 font-medium hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer transition-colors shadow-xs"
                >
                  <span>Next</span>
                  <ChevronRight className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
