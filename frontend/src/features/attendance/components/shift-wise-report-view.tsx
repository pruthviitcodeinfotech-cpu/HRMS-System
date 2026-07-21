"use client";

import React, { useState, useMemo, useEffect } from "react";
import * as XLSX from "xlsx";
import jsPDF from "jspdf";
import autoTable from "jspdf-autotable";
import { toast } from "sonner";
import {
  Calendar as CalendarIcon,
  Search,
  RotateCcw,
  FileSpreadsheet,
  FileText,
  AlertTriangle,
  ArrowUpDown,
  ChevronLeft,
  ChevronRight,
  X,
} from "lucide-react";
import { useBranchOptions } from "@/features/employees/hooks";
import { shiftService } from "@/features/shifts/services";
import { useAttendanceDays } from "../hooks/use-attendance";
import { AttendanceDailyQueryParams } from "../services/attendance";

interface ShiftOption {
  id: number;
  name: string;
}

export interface ShiftWiseRecord {
  id: string;
  employeeId: string;
  employeeName: string;
  department: string;
  designation: string;
  date: string;
  day: string;
  shiftName: string;
  shiftFrom: string;
  shiftTo: string;
  breakFrom: string;
  breakTo: string;
  firstPunch: string;
  lastPunch: string;
  totalWorkingHours: string;
  totalBreakHours: string;
  hasAnomaly: boolean;
}

type SortField =
  | "employeeId"
  | "employeeName"
  | "department"
  | "designation"
  | "date"
  | "shiftName";
type SortOrder = "asc" | "desc";

const formatTime = (isoString?: string | null): string => {
  if (!isoString) return "-";
  try {
    const d = new Date(isoString);
    if (isNaN(d.getTime())) return isoString;
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: true });
  } catch {
    return "-";
  }
};

const formatDate = (dateStr?: string | null): string => {
  if (!dateStr) return "-";
  try {
    const parts = dateStr.split("-");
    if (parts.length === 3) {
      return `${parts[2]}-${parts[1]}-${parts[0]}`;
    }
    const d = new Date(dateStr);
    const day = String(d.getDate()).padStart(2, "0");
    const month = String(d.getMonth() + 1).padStart(2, "0");
    const year = d.getFullYear();
    return `${day}-${month}-${year}`;
  } catch {
    return dateStr;
  }
};

export const ShiftWiseReportView: React.FC = () => {
  const todayStr = useMemo(() => new Date().toISOString().slice(0, 10), []);

  // Form Input States
  const [fromDate, setFromDate] = useState<string>("2026-07-01");
  const [toDate, setToDate] = useState<string>(todayStr);
  const [branchId, setBranchId] = useState<string>("");
  const [shiftId, setShiftId] = useState<string>("");

  // Applied Filter States (submitted via Search or Reset)
  const [searchFromDate, setSearchFromDate] = useState<string>("2026-07-01");
  const [searchToDate, setSearchToDate] = useState<string>(todayStr);
  const [searchBranchId, setSearchBranchId] = useState<string>("");
  const [searchShiftId, setSearchShiftId] = useState<string>("");

  // Pagination & Sorting States
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(10);
  const [sortField, setSortField] = useState<SortField>("employeeId");
  const [sortOrder, setSortOrder] = useState<SortOrder>("desc");

  // Options Data
  const { data: branchOptions } = useBranchOptions();
  const [shiftOptions, setShiftOptions] = useState<ShiftOption[]>([]);

  // Load shifts for filter dropdown
  useEffect(() => {
    shiftService
      .getShifts({ page_size: 100 })
      .then((res) => {
        if (res.data?.items) {
          setShiftOptions(
            res.data.items.map((s) => ({
              id: s.shift_id,
              name: s.shift_name,
            }))
          );
        }
      })
      .catch(() => {
        // Fallback silently if shifts cannot be loaded
      });
  }, []);

  // Construct query parameters for live backend fetch
  const queryParams: AttendanceDailyQueryParams = useMemo(() => {
    const params: AttendanceDailyQueryParams = {
      page: currentPage,
      page_size: pageSize,
    };

    if (searchBranchId) {
      params.branch_id = Number(searchBranchId);
    }
    if (searchShiftId) {
      params.shift_id = Number(searchShiftId);
    }

    if (searchFromDate && searchToDate) {
      params.date_from = searchFromDate;
      params.date_to = searchToDate;
    } else if (searchFromDate) {
      params.date_from = searchFromDate;
    } else if (searchToDate) {
      params.date_to = searchToDate;
    } else {
      params.date_from = "2026-07-01";
      params.date_to = todayStr;
    }

    return params;
  }, [searchFromDate, searchToDate, searchBranchId, searchShiftId, currentPage, pageSize, todayStr]);

  // Query Backend Attendance API
  const { data, isLoading, isError, error, refetch } = useAttendanceDays(queryParams);

  useEffect(() => {
    if (isError && error) {
      toast.error(error instanceof Error ? error.message : "Failed to fetch shift report data");
    }
  }, [isError, error]);

  // Handle Search submit
  const handleSearch = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setSearchFromDate(fromDate);
    setSearchToDate(toDate);
    setSearchBranchId(branchId);
    setSearchShiftId(shiftId);
    setCurrentPage(1);
    refetch();
  };

  // Handle Reset filters
  const handleReset = () => {
    const defaultFrom = "2026-07-01";
    const defaultTo = todayStr;
    setFromDate(defaultFrom);
    setToDate(defaultTo);
    setBranchId("");
    setShiftId("");
    setSearchFromDate(defaultFrom);
    setSearchToDate(defaultTo);
    setSearchBranchId("");
    setSearchShiftId("");
    setCurrentPage(1);
    toast.info("Filters reset to default");
  };

  // Map Backend Data to Shift Wise Report Records
  const rawRecords: ShiftWiseRecord[] = useMemo(() => {
    if (!data?.items) return [];

    let filtered = data.items;

    // Client-side filter by selected shift if specified
    if (searchShiftId) {
      filtered = filtered.filter(
        (item) => String(item.shift_id) === searchShiftId || item.shift_name === searchShiftId
      );
    }

    return filtered.map((item) => {
      const dateVal = item.attendance_date || queryParams.date || todayStr;
      const dayName = new Date(dateVal).toLocaleDateString("en-US", { weekday: "long" });

      let workingHrsStr = "-";
      let isZeroAnomaly = false;

      if (item.working_hours !== undefined && item.working_hours !== null) {
        workingHrsStr = `${item.working_hours}h`;
        if (item.working_hours === 0 && (item.first_punch || item.first_in)) {
          isZeroAnomaly = true;
          workingHrsStr = "0h";
        }
      } else if (item.worked_minutes !== undefined) {
        const hrs = Math.floor(item.worked_minutes / 60);
        const mins = item.worked_minutes % 60;
        workingHrsStr = hrs > 0 || mins > 0 ? `${hrs}h ${mins}m` : "0h";
        if (item.worked_minutes === 0 && (item.first_punch || item.first_in)) {
          isZeroAnomaly = true;
        }
      }

      return {
        id: item.id ? String(item.id) : `${item.employee_id}-${dateVal}`,
        employeeId: item.employee_code || String(item.employee_id),
        employeeName: item.employee_name || `Employee ${item.employee_id}`,
        department: item.department_name || "-",
        designation: item.designation || "-",
        date: formatDate(dateVal),
        day: dayName,
        shiftName: item.shift_name || "Daily",
        shiftFrom: "09:20 AM",
        shiftTo: "06:50 PM",
        breakFrom: "-",
        breakTo: "-",
        firstPunch: formatTime(item.first_punch || item.first_in),
        lastPunch: formatTime(item.last_punch || item.last_out),
        totalWorkingHours: workingHrsStr,
        totalBreakHours:
          item.break_hours !== undefined && item.break_hours !== null && item.break_hours > 0
            ? `${item.break_hours}h`
            : "-",
        hasAnomaly: isZeroAnomaly,
      };
    });
  }, [data, queryParams.date, shiftId, todayStr]);

  // Client-side Sort Records
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

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortOrder(sortOrder === "asc" ? "desc" : "asc");
    } else {
      setSortField(field);
      setSortOrder("asc");
    }
  };

  // Export handlers
  const handleExportExcel = () => {
    if (!records || records.length === 0) {
      toast.error("No data available to export");
      return;
    }

    const exportData = records.map((r) => ({
      "Employee ID": r.employeeId,
      "Employee Name": r.employeeName,
      Department: r.department,
      Designation: r.designation,
      Date: r.date,
      Day: r.day,
      Shift: r.shiftName,
      "Shift From": r.shiftFrom,
      "Shift To": r.shiftTo,
      "Break From": r.breakFrom,
      "Break To": r.breakTo,
      "First Punch": r.firstPunch,
      "Last Punch": r.lastPunch,
      "Total Working Hours": r.totalWorkingHours,
      "Total Break Hours": r.totalBreakHours,
    }));

    const worksheet = XLSX.utils.json_to_sheet(exportData);
    const workbook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(workbook, worksheet, "Shift Wise Report");
    XLSX.writeFile(workbook, `Shift_Wise_Report_${fromDate}_to_${toDate}.xlsx`);
    toast.success("Excel report exported successfully");
  };

  const handleExportPdf = () => {
    if (!records || records.length === 0) {
      toast.error("No data available to export");
      return;
    }

    try {
      const doc = new jsPDF({
        orientation: "landscape",
        unit: "mm",
        format: "a4",
      });

      const branchLabel =
        branchOptions?.find((b) => String(b.branch_id) === searchBranchId)?.branch_name ||
        "All Branches";
      const shiftLabel =
        shiftOptions.find((s) => String(s.id) === searchShiftId)?.name || "All Shifts";

      // Report Header Title
      doc.setFontSize(16);
      doc.setTextColor(2, 132, 199); // Sky Blue #0284c7
      doc.text("SHIFT WISE ATTENDANCE REPORT", 14, 15);

      // Metadata Bar
      doc.setFontSize(9);
      doc.setTextColor(71, 85, 105); // Slate-600
      doc.text(
        `Date Range: ${searchFromDate || "01-07-2026"} to ${searchToDate || "Today"} | Branch: ${branchLabel} | Shift: ${shiftLabel} | Records: ${records.length}`,
        14,
        22
      );

      const tableHeaders = [
        "Emp ID",
        "Employee Name",
        "Department",
        "Designation",
        "Date",
        "Day",
        "Shift",
        "From",
        "To",
        "Break From",
        "Break To",
        "First Punch",
        "Last Punch",
        "Working Hrs",
        "Break Hrs",
      ];

      const tableRows = records.map((r) => [
        r.employeeId,
        r.employeeName,
        r.department,
        r.designation,
        r.date,
        r.day,
        r.shiftName,
        r.shiftFrom,
        r.shiftTo,
        r.breakFrom,
        r.breakTo,
        r.firstPunch,
        r.lastPunch,
        r.totalWorkingHours,
        r.totalBreakHours,
      ]);

      autoTable(doc, {
        head: [tableHeaders],
        body: tableRows,
        startY: 26,
        styles: {
          fontSize: 7.5,
          cellPadding: 2,
          overflow: "linebreak",
        },
        headStyles: {
          fillColor: [2, 132, 199],
          textColor: [255, 255, 255],
          fontStyle: "bold",
        },
        alternateRowStyles: {
          fillColor: [248, 250, 252],
        },
        margin: { top: 26, left: 10, right: 10, bottom: 15 },
      });

      const fileName = `Shift_Wise_Report_${searchFromDate || "01-07-2026"}_to_${searchToDate || "today"}.pdf`;
      doc.save(fileName);
      toast.success("PDF report downloaded successfully");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to generate PDF download");
    }
  };

  const totalRecords = data?.pagination?.total_records || records.length;
  const totalPages = data?.pagination?.total_pages || Math.ceil(totalRecords / pageSize) || 1;

  return (
    <div className="p-6 space-y-6">
      {/* Title */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100 mb-1">
          Shift Wise Report
        </h1>
        <p className="text-sm text-slate-500 dark:text-slate-400">
          Analyze employee attendance and punch timestamps grouped by assigned shifts.
        </p>
      </div>

      {/* Filter Bar */}
      <div className="bg-card border border-border rounded-xl p-4 shadow-xs">
        <form onSubmit={handleSearch} className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex flex-wrap items-center gap-3">
            {/* Date Range Selector */}
            <div className="flex items-center space-x-2 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg px-3 py-2 text-xs">
              <CalendarIcon className="h-4 w-4 text-slate-400 shrink-0" />
              <input
                type="date"
                value={fromDate}
                onChange={(e) => setFromDate(e.target.value)}
                className="bg-transparent border-none text-slate-700 dark:text-slate-200 focus:outline-hidden cursor-pointer"
              />
              <span className="text-slate-400 font-bold">→</span>
              <input
                type="date"
                value={toDate}
                onChange={(e) => setToDate(e.target.value)}
                className="bg-transparent border-none text-slate-700 dark:text-slate-200 focus:outline-hidden cursor-pointer"
              />
              {(fromDate || toDate) && (
                <button
                  type="button"
                  onClick={() => {
                    setFromDate("");
                    setToDate("");
                  }}
                  className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                  title="Clear Dates"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              )}
            </div>

            {/* Branch Selector */}
            <div className="min-w-[180px]">
              <select
                value={branchId}
                onChange={(e) => setBranchId(e.target.value)}
                className="w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg px-3 py-2 text-xs font-medium text-slate-700 dark:text-slate-200 focus:outline-hidden cursor-pointer"
              >
                <option value="">Choose Branch</option>
                {branchOptions?.map((b) => (
                  <option key={b.branch_id} value={String(b.branch_id)}>
                    {b.branch_name}
                  </option>
                ))}
              </select>
            </div>

            {/* Shift Selector */}
            <div className="min-w-[180px]">
              <select
                value={shiftId}
                onChange={(e) => setShiftId(e.target.value)}
                className="w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg px-3 py-2 text-xs font-medium text-slate-700 dark:text-slate-200 focus:outline-hidden cursor-pointer"
              >
                <option value="">Choose Shift</option>
                {shiftOptions.map((s) => (
                  <option key={s.id} value={String(s.id)}>
                    {s.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Search Button */}
            <button
              type="submit"
              className="inline-flex items-center justify-center space-x-1.5 bg-sky-600 hover:bg-sky-700 text-white text-xs font-semibold px-4 py-2 rounded-lg transition-colors shadow-xs"
            >
              <Search className="h-3.5 w-3.5" />
              <span>Search</span>
            </button>

            {/* Reset Button */}
            <button
              type="button"
              onClick={handleReset}
              className="inline-flex items-center justify-center space-x-1.5 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 text-xs font-medium px-3 py-2 rounded-lg transition-colors"
              title="Reset Filters"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              <span>Reset</span>
            </button>
          </div>

          {/* Export Action Buttons */}
          <div className="flex items-center space-x-2">
            <button
              type="button"
              onClick={handleExportExcel}
              className="inline-flex items-center space-x-1.5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-200 text-xs font-medium px-3.5 py-2 rounded-lg shadow-xs transition-colors"
            >
              <FileSpreadsheet className="h-4 w-4 text-emerald-600" />
              <span>Export Excel</span>
            </button>
            <button
              type="button"
              onClick={handleExportPdf}
              className="inline-flex items-center space-x-1.5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-200 text-xs font-medium px-3.5 py-2 rounded-lg shadow-xs transition-colors"
            >
              <FileText className="h-4 w-4 text-rose-600" />
              <span>Export PDF</span>
            </button>
          </div>
        </form>
      </div>

      {/* Main Table Container */}
      <div className="bg-card border border-border rounded-xl shadow-xs overflow-hidden">
        {isLoading ? (
          <div className="p-8 space-y-4">
            <div className="h-8 bg-slate-100 dark:bg-slate-800 rounded-md animate-pulse w-full" />
            <div className="h-12 bg-slate-100 dark:bg-slate-800 rounded-md animate-pulse w-full" />
            <div className="h-12 bg-slate-100 dark:bg-slate-800 rounded-md animate-pulse w-full" />
            <div className="h-12 bg-slate-100 dark:bg-slate-800 rounded-md animate-pulse w-full" />
          </div>
        ) : records.length === 0 ? (
          <div className="p-12 text-center">
            <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-400 mb-3">
              <CalendarIcon className="h-6 w-6" />
            </div>
            <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100 mb-1">
              No shift attendance records found
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 max-w-sm mx-auto">
              Try adjusting your date range, branch, or shift filter options to view available shift logs.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left border-collapse">
              <thead>
                <tr className="bg-sky-50/80 dark:bg-slate-800/60 border-b border-sky-100 dark:border-slate-700 text-slate-700 dark:text-slate-200">
                  <th
                    onClick={() => handleSort("employeeId")}
                    className="py-3 px-3.5 font-semibold cursor-pointer hover:bg-sky-100/60 dark:hover:bg-slate-700/60 transition-colors"
                  >
                    <div className="flex items-center space-x-1">
                      <span>Employee ID</span>
                      <ArrowUpDown className="h-3 w-3 text-slate-400" />
                    </div>
                  </th>
                  <th
                    onClick={() => handleSort("employeeName")}
                    className="py-3 px-3.5 font-semibold cursor-pointer hover:bg-sky-100/60 dark:hover:bg-slate-700/60 transition-colors"
                  >
                    <div className="flex items-center space-x-1">
                      <span>Employee Name</span>
                      <ArrowUpDown className="h-3 w-3 text-slate-400" />
                    </div>
                  </th>
                  <th
                    onClick={() => handleSort("department")}
                    className="py-3 px-3.5 font-semibold cursor-pointer hover:bg-sky-100/60 dark:hover:bg-slate-700/60 transition-colors"
                  >
                    <div className="flex items-center space-x-1">
                      <span>Department</span>
                      <ArrowUpDown className="h-3 w-3 text-slate-400" />
                    </div>
                  </th>
                  <th
                    onClick={() => handleSort("designation")}
                    className="py-3 px-3.5 font-semibold cursor-pointer hover:bg-sky-100/60 dark:hover:bg-slate-700/60 transition-colors"
                  >
                    <div className="flex items-center space-x-1">
                      <span>Designation</span>
                      <ArrowUpDown className="h-3 w-3 text-slate-400" />
                    </div>
                  </th>
                  <th
                    onClick={() => handleSort("date")}
                    className="py-3 px-3.5 font-semibold cursor-pointer hover:bg-sky-100/60 dark:hover:bg-slate-700/60 transition-colors"
                  >
                    <div className="flex items-center space-x-1">
                      <span>Date</span>
                      <ArrowUpDown className="h-3 w-3 text-slate-400" />
                    </div>
                  </th>
                  <th className="py-3 px-3.5 font-semibold">Day</th>
                  <th
                    onClick={() => handleSort("shiftName")}
                    className="py-3 px-3.5 font-semibold cursor-pointer hover:bg-sky-100/60 dark:hover:bg-slate-700/60 transition-colors"
                  >
                    <div className="flex items-center space-x-1">
                      <span>Shift</span>
                      <ArrowUpDown className="h-3 w-3 text-slate-400" />
                    </div>
                  </th>
                  <th className="py-3 px-3.5 font-semibold">From</th>
                  <th className="py-3 px-3.5 font-semibold">To</th>
                  <th className="py-3 px-3.5 font-semibold">Break From</th>
                  <th className="py-3 px-3.5 font-semibold">Break To</th>
                  <th className="py-3 px-3.5 font-semibold">First Punch</th>
                  <th className="py-3 px-3.5 font-semibold">Last Punch</th>
                  <th className="py-3 px-3.5 font-semibold text-right">Total Working Hours</th>
                  <th className="py-3 px-3.5 font-semibold text-right">Total Break Hours</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {records.map((r, idx) => (
                  <tr
                    key={`${r.id}-${idx}`}
                    className="hover:bg-slate-50/70 dark:hover:bg-slate-800/40 transition-colors text-slate-700 dark:text-slate-200"
                  >
                    <td className="py-3 px-3.5 font-medium text-slate-900 dark:text-slate-100">
                      {r.employeeId}
                    </td>
                    <td className="py-3 px-3.5 font-semibold text-slate-800 dark:text-slate-200 whitespace-nowrap">
                      {r.employeeName}
                    </td>
                    <td className="py-3 px-3.5">{r.department}</td>
                    <td className="py-3 px-3.5">{r.designation}</td>
                    <td className="py-3 px-3.5 whitespace-nowrap">{r.date}</td>
                    <td className="py-3 px-3.5">{r.day}</td>
                    <td className="py-3 px-3.5 font-medium text-slate-800 dark:text-slate-200">
                      {r.shiftName}
                    </td>
                    <td className="py-3 px-3.5 whitespace-nowrap text-slate-600 dark:text-slate-400">
                      {r.shiftFrom}
                    </td>
                    <td className="py-3 px-3.5 whitespace-nowrap text-slate-600 dark:text-slate-400">
                      {r.shiftTo}
                    </td>
                    <td className="py-3 px-3.5 text-slate-400">{r.breakFrom}</td>
                    <td className="py-3 px-3.5 text-slate-400">{r.breakTo}</td>
                    <td className="py-3 px-3.5 whitespace-nowrap">{r.firstPunch}</td>
                    <td className="py-3 px-3.5 whitespace-nowrap">{r.lastPunch}</td>
                    <td className="py-3 px-3.5 text-right font-medium whitespace-nowrap">
                      {r.hasAnomaly ? (
                        <span className="inline-flex items-center space-x-1 text-amber-600 font-semibold bg-amber-50 dark:bg-amber-950/40 px-1.5 py-0.5 rounded-sm">
                          <span>{r.totalWorkingHours}</span>
                          <AlertTriangle className="h-3 w-3 text-amber-500 fill-amber-500" />
                        </span>
                      ) : (
                        <span className="underline decoration-slate-300 underline-offset-2">
                          {r.totalWorkingHours}
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-3.5 text-right text-slate-400">{r.totalBreakHours}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Footer Pagination */}
        <div className="flex flex-col sm:flex-row items-center justify-between px-4 py-3 border-t border-border bg-slate-50/50 dark:bg-slate-900/50 gap-3 text-xs">
          <div className="flex items-center space-x-2 text-slate-500 dark:text-slate-400">
            <span>Rows per page:</span>
            <select
              value={pageSize}
              onChange={(e) => {
                setPageSize(Number(e.target.value));
                setCurrentPage(1);
              }}
              className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-md px-2 py-1 focus:outline-hidden"
            >
              <option value={10}>10</option>
              <option value={25}>25</option>
              <option value={50}>50</option>
              <option value={100}>100</option>
            </select>
            <span className="ml-2">
              Showing page {currentPage} of {totalPages} ({totalRecords} records)
            </span>
          </div>

          <div className="flex items-center space-x-1.5">
            <button
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              disabled={currentPage === 1}
              className="p-1.5 rounded-md border border-slate-200 dark:border-slate-800 hover:bg-white dark:hover:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <span className="px-2 font-medium text-slate-700 dark:text-slate-200">
              {currentPage} / {totalPages}
            </span>
            <button
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              disabled={currentPage >= totalPages}
              className="p-1.5 rounded-md border border-slate-200 dark:border-slate-800 hover:bg-white dark:hover:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
