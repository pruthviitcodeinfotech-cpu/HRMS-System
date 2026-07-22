"use client";

import React, { useState, useMemo, useEffect } from "react";
import * as XLSX from "xlsx";
import jsPDF from "jspdf";
import autoTable from "jspdf-autotable";
import { toast } from "sonner";
import {
  Search,
  RotateCcw,
  FileSpreadsheet,
  FileText,
  AlertTriangle,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  RefreshCw,
  CalendarDays,
} from "lucide-react";
import { useBranchOptions } from "@/features/employees/hooks";
import { useMusterReport } from "../hooks/use-attendance";
import {
  MusterReportQueryParams,
  MusterRow,
  MusterCell,
} from "../services/attendance";

export const MusterReportView: React.FC = () => {
  const todayStr = useMemo(() => new Date().toISOString().slice(0, 10), []);

  // Form Input States
  const [fromDate, setFromDate] = useState<string>("2026-07-01");
  const [toDate, setToDate] = useState<string>(todayStr);
  const [branchId, setBranchId] = useState<string>("");
  const [isDropdownOpen, setIsDropdownOpen] = useState<boolean>(false);

  // Applied Filter States
  const [searchFromDate, setSearchFromDate] = useState<string>("2026-07-01");
  const [searchToDate, setSearchToDate] = useState<string>(todayStr);
  const [searchBranchId, setSearchBranchId] = useState<string>("");

  // Pagination & Search States
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(10);
  const [searchTerm, setSearchTerm] = useState<string>("");

  // Options Data (Branch Lookup Hook)
  const { data: branchOptions } = useBranchOptions();

  // Construct query params for live backend API
  const queryParams: MusterReportQueryParams = useMemo(() => {
    const params: MusterReportQueryParams = {
      page: currentPage,
      page_size: pageSize,
      sort_by: "employee_code",
      sort_dir: "asc",
    };

    if (searchBranchId) {
      params.branch_id = Number(searchBranchId);
    }

    if (searchFromDate && searchToDate) {
      params.date_from = searchFromDate;
      params.date_to = searchToDate;
    } else {
      params.date_from = "2026-07-01";
      params.date_to = todayStr;
    }

    return params;
  }, [currentPage, pageSize, searchFromDate, searchToDate, searchBranchId, todayStr]);

  // Query Backend Muster Roll Report API via React Query
  const { data, isLoading, isError, error, refetch } = useMusterReport(queryParams);

  useEffect(() => {
    if (isError && error) {
      toast.error(error instanceof Error ? error.message : "Failed to fetch muster report data");
    }
  }, [isError, error]);

  // Construct dynamic date column list directly from backend response or fallback date range
  const dateList = useMemo(() => {
    if (data?.dates && data.dates.length > 0) {
      return data.dates.map((dateStr) => {
        const dObj = new Date(dateStr);
        const dayNumber = dateStr.split("-")[2];
        const monthName = isNaN(dObj.getTime())
          ? ""
          : dObj.toLocaleDateString("en-US", { month: "long" });
        const dayName = isNaN(dObj.getTime())
          ? ""
          : dObj.toLocaleDateString("en-US", { weekday: "long" });
        return { dateStr, dayNumber, monthName, dayName };
      });
    }

    const list: { dateStr: string; dayNumber: string; monthName: string; dayName: string }[] = [];
    if (!searchFromDate || !searchToDate) return list;

    const curr = new Date(searchFromDate);
    const end = new Date(searchToDate);
    let count = 0;

    while (curr <= end && count < 31) {
      const dateStr = curr.toISOString().slice(0, 10);
      const dayNumber = dateStr.split("-")[2];
      const monthName = curr.toLocaleDateString("en-US", { month: "long" });
      const dayName = curr.toLocaleDateString("en-US", { weekday: "long" });
      list.push({ dateStr, dayNumber, monthName, dayName });
      curr.setDate(curr.getDate() + 1);
      count++;
    }
    return list;
  }, [data, searchFromDate, searchToDate]);

  // Client-side quick search filtering on backend items
  const filteredItems = useMemo(() => {
    if (!data?.items) return [];
    if (!searchTerm.trim()) return data.items;

    const term = searchTerm.toLowerCase().trim();
    return data.items.filter(
      (item: MusterRow) =>
        item.employee_name.toLowerCase().includes(term) ||
        item.employee_code.toLowerCase().includes(term) ||
        item.department_name.toLowerCase().includes(term) ||
        item.designation_name.toLowerCase().includes(term)
    );
  }, [data, searchTerm]);

  // Handle Search submit
  const handleSearch = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setSearchFromDate(fromDate);
    setSearchToDate(toDate);
    setSearchBranchId(branchId);
    setCurrentPage(1);
  };

  // Handle Reset filters
  const handleReset = () => {
    setFromDate("2026-07-01");
    setToDate(todayStr);
    setBranchId("");
    setSearchFromDate("2026-07-01");
    setSearchToDate(todayStr);
    setSearchBranchId("");
    setSearchTerm("");
    setCurrentPage(1);
  };

  // Pagination metadata
  const totalPages = data?.pagination?.total_pages || 1;
  const totalRecords = data?.pagination?.total_records || 0;
  const startIndex = (currentPage - 1) * pageSize + 1;
  const endIndex = Math.min(currentPage * pageSize, totalRecords);

  // Status Badge Rendering Helper matching Petpooja EXACT style
  const renderStatusBadge = (cell?: MusterCell) => {
    if (!cell) {
      return <span className="font-bold text-rose-600 text-xs">A</span>;
    }

    const st = (cell.status || "A").toUpperCase();
    const isOvertime = cell.is_overtime;
    const isMissing = cell.is_missing_punch;

    // Full Day / Present
    if (st === "FD" || st === "P" || st === "PRESENT") {
      return (
        <span className="inline-flex items-center gap-1 font-bold text-slate-900 dark:text-slate-100 text-xs">
          FD
          {isOvertime && (
            <span
              title="Overtime / Extra Hours"
              className="inline-flex items-center justify-center w-3.5 h-3.5 rounded-full bg-sky-500 text-white font-semibold text-[9px]"
            >
              O
            </span>
          )}
        </span>
      );
    }

    // Half Day
    if (st === "HD" || st === "HALF_DAY") {
      return (
        <span className="inline-flex items-center gap-1 font-bold text-amber-700 dark:text-amber-400 text-xs">
          HD
          {isOvertime && (
            <span
              title="Overtime / Extra Hours"
              className="inline-flex items-center justify-center w-3.5 h-3.5 rounded-full bg-sky-500 text-white font-semibold text-[9px]"
            >
              O
            </span>
          )}
        </span>
      );
    }

    // Absent
    if (st === "A" || st === "ABSENT") {
      return (
        <span className="inline-flex items-center gap-1 font-bold text-rose-600 dark:text-rose-400 text-xs">
          A
          {isMissing && (
            <span
              title="Missing Punch / Single Punch Warning"
              className="inline-flex items-center text-amber-500"
            >
              <AlertTriangle className="w-3 h-3 fill-amber-500 text-white" />
            </span>
          )}
        </span>
      );
    }

    // Leaves (LWP, CL, SL, PL, LEAVE)
    if (["LWP", "CL", "SL", "PL", "LEAVE", "L"].includes(st)) {
      return (
        <span className="font-bold text-amber-600 dark:text-amber-400 text-xs">
          {st}
        </span>
      );
    }

    // Week Off
    if (st === "WO" || st === "WEEK_OFF" || st === "WEEKOFF") {
      return (
        <span className="font-medium text-slate-400 dark:text-slate-500 text-xs">
          WO
        </span>
      );
    }

    // Holiday
    if (st === "H" || st === "HOLIDAY") {
      return (
        <span className="font-bold text-indigo-600 dark:text-indigo-400 text-xs">
          H
        </span>
      );
    }

    // Default Fallback
    return <span className="font-bold text-slate-700 dark:text-slate-300 text-xs">{st}</span>;
  };

  // Export to Excel
  const handleExportExcel = () => {
    if (!data?.items || data.items.length === 0) {
      toast.error("No data available to export");
      return;
    }

    try {
      const exportData = data.items.map((row) => {
        const rowObj: Record<string, string | number> = {
          "Employee ID": row.employee_code,
          "Employee Name": row.employee_name,
          Department: row.department_name,
          Designation: row.designation_name,
          "Full Days": row.total_present,
          "Half Days": row.total_half_day,
          "Absent Days": row.total_absent,
          "Week Off": row.total_week_off,
          Leaves: row.total_leave,
          Holidays: row.total_holiday,
        };

        dateList.forEach(({ dateStr, dayNumber, monthName }) => {
          const key = `${dayNumber} ${monthName}`;
          const cell = row.daily_status[dateStr];
          rowObj[key] = cell?.status || "A";
        });

        return rowObj;
      });

      const worksheet = XLSX.utils.json_to_sheet(exportData);
      const workbook = XLSX.utils.book_new();
      XLSX.utils.book_append_sheet(workbook, worksheet, "Muster Report");
      XLSX.writeFile(workbook, `Muster_Report_${searchFromDate}_to_${searchToDate}.xlsx`);
      toast.success("Excel report exported successfully");
    } catch {
      toast.error("Failed to export Excel report");
    }
  };

  // Export to PDF
  const handleExportPDF = () => {
    if (!data?.items || data.items.length === 0) {
      toast.error("No data available to export");
      return;
    }

    try {
      const doc = new jsPDF({ orientation: "landscape" });

      doc.setFontSize(14);
      doc.text("Muster Report", 14, 15);
      doc.setFontSize(9);
      doc.text(`Period: ${searchFromDate} to ${searchToDate}`, 14, 22);

      const headers = [
        "Employee ID",
        "Employee Name",
        "Department",
        "Designation",
        "FD",
        "HD",
        "A",
        "WO",
        "Leaves",
        "H",
        ...dateList.map((d) => `${d.dayNumber} ${d.monthName.slice(0, 3)}`),
      ];

      const body = data.items.map((row) => [
        row.employee_code,
        row.employee_name,
        row.department_name,
        row.designation_name,
        row.total_present,
        row.total_half_day,
        row.total_absent,
        row.total_week_off,
        row.total_leave,
        row.total_holiday,
        ...dateList.map((d) => row.daily_status[d.dateStr]?.status || "A"),
      ]);

      autoTable(doc, {
        head: [headers],
        body: body,
        startY: 26,
        styles: { fontSize: 7, cellPadding: 2 },
        headStyles: { fillColor: [41, 128, 185], textColor: 255 },
      });

      doc.save(`Muster_Report_${searchFromDate}_to_${searchToDate}.pdf`);
      toast.success("PDF report exported successfully");
    } catch {
      toast.error("Failed to export PDF report");
    }
  };

  return (
    <div className="p-6 max-w-[1600px] mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
            Muster Report
          </h1>
          <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
            Comprehensive multi-day attendance muster with daily status badges, leaves, and summary counts.
          </p>
        </div>

        {/* Top Right Action Buttons matching Petpooja */}
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={handleExportExcel}
            className="inline-flex items-center gap-2 px-4 py-2 border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-200 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 rounded-lg text-sm font-medium transition-colors shadow-sm"
          >
            <FileSpreadsheet className="w-4 h-4 text-emerald-600" />
            Export Excel
          </button>

          <button
            type="button"
            onClick={handleExportPDF}
            className="inline-flex items-center gap-2 px-4 py-2 border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-200 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 rounded-lg text-sm font-medium transition-colors shadow-sm"
          >
            <FileText className="w-4 h-4 text-rose-600" />
            Muster Report
          </button>

          <div className="relative">
            <button
              type="button"
              onClick={() => setIsDropdownOpen((prev) => !prev)}
              className="inline-flex items-center gap-2 px-4 py-2 border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-200 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 rounded-lg text-sm font-medium transition-colors shadow-sm"
            >
              Attendance Report
              <ChevronDown className={`w-4 h-4 text-slate-500 transition-transform ${isDropdownOpen ? "rotate-180" : ""}`} />
            </button>

            {isDropdownOpen && (
              <div className="absolute right-0 mt-2 w-44 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg shadow-lg py-1 z-50">
                <button
                  type="button"
                  onClick={() => {
                    setIsDropdownOpen(false);
                    handleExportPDF();
                  }}
                  className="w-full text-left px-4 py-2 text-sm text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
                >
                  Download PDF
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setIsDropdownOpen(false);
                    handleExportExcel();
                  }}
                  className="w-full text-left px-4 py-2 text-sm text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
                >
                  Download Excel
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Filter Control Card matching Petpooja */}
      <div className="bg-white dark:bg-slate-800 p-4 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm space-y-4">
        <form onSubmit={handleSearch} className="flex flex-wrap items-center gap-4">
          {/* Date Range Picker */}
          <div className="flex items-center bg-slate-50 dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg p-1">
            <input
              type="date"
              aria-label="From Date"
              value={fromDate}
              onChange={(e) => setFromDate(e.target.value)}
              className="bg-transparent border-0 text-sm font-medium text-slate-700 dark:text-slate-200 focus:ring-0 focus:outline-none px-2 py-1"
            />
            <span className="text-slate-400 font-medium px-1">—</span>
            <input
              type="date"
              aria-label="To Date"
              value={toDate}
              onChange={(e) => setToDate(e.target.value)}
              className="bg-transparent border-0 text-sm font-medium text-slate-700 dark:text-slate-200 focus:ring-0 focus:outline-none px-2 py-1"
            />
          </div>

          {/* Branch Select */}
          <div className="min-w-[200px]">
            <select
              aria-label="Choose Branch"
              value={branchId}
              onChange={(e) => setBranchId(e.target.value)}
              className="w-full bg-slate-50 dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-sm font-medium text-slate-700 dark:text-slate-200 focus:ring-2 focus:ring-sky-500 px-3 py-2"
            >
              <option value="" className="bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100">Choose Branch</option>
              {branchOptions?.map((b) => (
                <option key={b.branch_id} value={b.branch_id} className="bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100">
                  {b.branch_name}
                </option>
              ))}
            </select>
          </div>

          {/* Search Action Button */}
          <button
            type="submit"
            className="inline-flex items-center gap-2 px-6 py-2 bg-sky-500 hover:bg-sky-600 text-white rounded-lg text-sm font-medium transition-colors shadow-sm"
          >
            <Search className="w-4 h-4" />
            Search
          </button>

          {/* Reset Action Button */}
          <button
            type="button"
            onClick={handleReset}
            className="inline-flex items-center gap-2 px-4 py-2 border border-slate-300 dark:border-slate-700 text-slate-600 dark:text-slate-300 bg-slate-50 dark:bg-slate-900 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg text-sm font-medium transition-colors"
          >
            <RotateCcw className="w-4 h-4" />
            Reset
          </button>

          {/* Quick Filter Search Input */}
          <div className="ml-auto w-full sm:w-64">
            <div className="relative">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                aria-label="Quick Search"
                placeholder="Search employee / dept..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-9 pr-4 py-2 bg-slate-50 dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-sm text-slate-800 dark:text-slate-200 focus:ring-2 focus:ring-sky-500 focus:outline-none"
              />
            </div>
          </div>
        </form>
      </div>

      {/* Main Table Content Card matching Petpooja design */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm overflow-hidden">
        {/* Error State Banner */}
        {isError && (
          <div className="p-6 bg-rose-50 dark:bg-rose-900/20 border-b border-rose-200 dark:border-rose-800 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <AlertTriangle className="w-5 h-5 text-rose-600 dark:text-rose-400" />
              <p className="text-sm font-medium text-rose-800 dark:text-rose-200">
                {error instanceof Error ? error.message : "Failed to load muster report data."}
              </p>
            </div>
            <button
              type="button"
              onClick={() => refetch()}
              className="inline-flex items-center gap-2 px-3 py-1.5 bg-rose-600 hover:bg-rose-700 text-white rounded-md text-sm font-medium transition-colors"
            >
              <RefreshCw className="w-4 h-4" />
              Retry
            </button>
          </div>
        )}

        {/* Table Container with Horizontal Scroll */}
        <div className="overflow-x-auto max-w-full">
          <table className="w-full border-collapse text-left text-xs text-slate-700 dark:text-slate-200">
            <thead>
              <tr className="bg-slate-50/90 dark:bg-slate-900/90 border-b border-slate-200 dark:border-slate-700 font-semibold text-slate-700 dark:text-slate-300">
                {/* Fixed Columns */}
                <th className="py-3 px-3 min-w-[90px] whitespace-nowrap bg-slate-50/90 dark:bg-slate-900/90 sticky left-0 z-10 border-r border-slate-200 dark:border-slate-700">
                  Employee ID
                </th>
                <th className="py-3 px-4 min-w-[150px] whitespace-nowrap bg-slate-50/90 dark:bg-slate-900/90">
                  Employee Name
                </th>
                <th className="py-3 px-4 min-w-[110px] whitespace-nowrap bg-slate-50/90 dark:bg-slate-900/90">
                  Department
                </th>
                <th className="py-3 px-4 min-w-[120px] whitespace-nowrap bg-slate-50/90 dark:bg-slate-900/90 border-r border-slate-200 dark:border-slate-700">
                  Designation
                </th>

                {/* Summary Columns matching Petpooja */}
                <th className="py-3 px-3 min-w-[65px] text-center bg-sky-50/70 dark:bg-sky-950/20 text-slate-800 dark:text-slate-200 font-semibold">
                  Full Days
                </th>
                <th className="py-3 px-3 min-w-[65px] text-center bg-sky-50/70 dark:bg-sky-950/20 text-slate-800 dark:text-slate-200 font-semibold">
                  Half Days
                </th>
                <th className="py-3 px-3 min-w-[70px] text-center bg-sky-50/70 dark:bg-sky-950/20 text-slate-800 dark:text-slate-200 font-semibold">
                  Absent Days
                </th>
                <th className="py-3 px-3 min-w-[65px] text-center bg-sky-50/70 dark:bg-sky-950/20 text-slate-800 dark:text-slate-200 font-semibold">
                  Week Off
                </th>
                <th className="py-3 px-3 min-w-[60px] text-center bg-sky-50/70 dark:bg-sky-950/20 text-slate-800 dark:text-slate-200 font-semibold">
                  Leaves
                </th>
                <th className="py-3 px-3 min-w-[65px] text-center bg-sky-50/70 dark:bg-sky-950/20 text-slate-800 dark:text-slate-200 font-semibold border-r border-slate-200 dark:border-slate-700">
                  Holidays
                </th>

                {/* Dynamic Date Headers matching Petpooja (DD / Month / Day) */}
                {dateList.map(({ dateStr, dayNumber, monthName, dayName }) => (
                  <th
                    key={dateStr}
                    className="py-2 px-2 min-w-[58px] text-center border-r border-slate-200 dark:border-slate-700 whitespace-nowrap bg-slate-50/90 dark:bg-slate-900/90"
                  >
                    <div className="font-semibold text-slate-800 dark:text-slate-100 text-[11px]">
                      {dayNumber}
                    </div>
                    <div className="text-[10px] text-slate-600 dark:text-slate-400 font-normal">
                      {monthName}
                    </div>
                    <div className="text-[10px] text-slate-400 dark:text-slate-500 font-normal">
                      {dayName}
                    </div>
                  </th>
                ))}
              </tr>
            </thead>

            <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
              {/* Skeleton Loader */}
              {isLoading &&
                Array.from({ length: 5 }).map((_, idx) => (
                  <tr key={idx} className="animate-pulse">
                    <td className="py-4 px-3 sticky left-0 z-10 bg-white dark:bg-slate-800 border-r border-slate-200 dark:border-slate-700">
                      <div className="h-4 bg-slate-200 dark:bg-slate-700 rounded w-12" />
                    </td>
                    <td className="py-4 px-4"><div className="h-4 bg-slate-200 dark:bg-slate-700 rounded w-28" /></td>
                    <td className="py-4 px-4"><div className="h-4 bg-slate-200 dark:bg-slate-700 rounded w-20" /></td>
                    <td className="py-4 px-4 border-r border-slate-200 dark:border-slate-700"><div className="h-4 bg-slate-200 dark:bg-slate-700 rounded w-20" /></td>
                    <td className="py-4 px-3 text-center bg-sky-50/20 dark:bg-sky-950/10"><div className="h-4 bg-slate-200 dark:bg-slate-700 rounded w-6 mx-auto" /></td>
                    <td className="py-4 px-3 text-center bg-sky-50/20 dark:bg-sky-950/10"><div className="h-4 bg-slate-200 dark:bg-slate-700 rounded w-6 mx-auto" /></td>
                    <td className="py-4 px-3 text-center bg-sky-50/20 dark:bg-sky-950/10"><div className="h-4 bg-slate-200 dark:bg-slate-700 rounded w-6 mx-auto" /></td>
                    <td className="py-4 px-3 text-center bg-sky-50/20 dark:bg-sky-950/10"><div className="h-4 bg-slate-200 dark:bg-slate-700 rounded w-6 mx-auto" /></td>
                    <td className="py-4 px-3 text-center bg-sky-50/20 dark:bg-sky-950/10"><div className="h-4 bg-slate-200 dark:bg-slate-700 rounded w-6 mx-auto" /></td>
                    <td className="py-4 px-3 text-center bg-sky-50/20 dark:bg-sky-950/10 border-r border-slate-200 dark:border-slate-700"><div className="h-4 bg-slate-200 dark:bg-slate-700 rounded w-6 mx-auto" /></td>
                    {dateList.map((d) => (
                      <td key={d.dateStr} className="py-4 px-2 border-r border-slate-100 dark:border-slate-800 text-center">
                        <div className="h-5 bg-slate-200 dark:bg-slate-700 rounded w-6 mx-auto" />
                      </td>
                    ))}
                  </tr>
                ))}

              {/* Data Rows */}
              {!isLoading &&
                filteredItems.length > 0 &&
                filteredItems.map((row: MusterRow) => (
                  <tr
                    key={row.employee_id}
                    className="hover:bg-slate-50/80 dark:hover:bg-slate-700/50 transition-colors"
                  >
                    {/* Fixed Columns */}
                    <td className="py-3 px-3 font-medium text-slate-900 dark:text-slate-100 bg-white dark:bg-slate-800 sticky left-0 z-10 border-r border-slate-200 dark:border-slate-700">
                      {row.employee_code}
                    </td>
                    <td className="py-3 px-4 font-medium text-slate-800 dark:text-slate-200">
                      {row.employee_name}
                    </td>
                    <td className="py-3 px-4 text-slate-600 dark:text-slate-400">
                      {row.department_name}
                    </td>
                    <td className="py-3 px-4 text-slate-600 dark:text-slate-400 border-r border-slate-200 dark:border-slate-700">
                      {row.designation_name}
                    </td>

                    {/* Summary Totals */}
                    <td className="py-3 px-3 text-center font-medium text-slate-800 dark:text-slate-200 bg-sky-50/30 dark:bg-sky-950/10">
                      {row.total_present}
                    </td>
                    <td className="py-3 px-3 text-center font-medium text-slate-800 dark:text-slate-200 bg-sky-50/30 dark:bg-sky-950/10">
                      {row.total_half_day}
                    </td>
                    <td className="py-3 px-3 text-center font-medium text-slate-800 dark:text-slate-200 bg-sky-50/30 dark:bg-sky-950/10">
                      {row.total_absent}
                    </td>
                    <td className="py-3 px-3 text-center font-medium text-slate-800 dark:text-slate-200 bg-sky-50/30 dark:bg-sky-950/10">
                      {row.total_week_off}
                    </td>
                    <td className="py-3 px-3 text-center font-medium text-slate-800 dark:text-slate-200 bg-sky-50/30 dark:bg-sky-950/10">
                      {row.total_leave.toFixed(1)}
                    </td>
                    <td className="py-3 px-3 text-center font-medium text-slate-800 dark:text-slate-200 bg-sky-50/30 dark:bg-sky-950/10 border-r border-slate-200 dark:border-slate-700">
                      {row.total_holiday}
                    </td>

                    {/* Daily Muster Badges */}
                    {dateList.map(({ dateStr }) => {
                      const cell = row.daily_status[dateStr];
                      return (
                        <td
                          key={dateStr}
                          className="py-3 px-2 text-center border-r border-slate-100 dark:border-slate-800"
                        >
                          {renderStatusBadge(cell)}
                        </td>
                      );
                    })}
                  </tr>
                ))}

              {/* Empty State */}
              {!isLoading && filteredItems.length === 0 && (
                <tr>
                  <td
                    colSpan={10 + (dateList.length || 1)}
                    className="py-12 text-center text-slate-500 dark:text-slate-400"
                  >
                    <div className="flex flex-col items-center justify-center gap-2">
                      <CalendarDays className="w-8 h-8 text-slate-300 dark:text-slate-600" />
                      <p className="text-sm font-medium">No muster report records found.</p>
                      <p className="text-xs text-slate-400">
                        Try adjusting your date range or branch filters.
                      </p>
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Footer Pagination matching Petpooja */}
        <div className="p-4 bg-white dark:bg-slate-800 border-t border-slate-200 dark:border-slate-700 flex flex-col sm:flex-row items-center justify-between gap-4">
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Showing <span className="font-medium text-slate-700 dark:text-slate-200">{filteredItems.length ? startIndex : 0}</span> to{" "}
            <span className="font-medium text-slate-700 dark:text-slate-200">{endIndex}</span> of{" "}
            <span className="font-medium text-slate-700 dark:text-slate-200">{totalRecords}</span> Results
          </p>

          <div className="flex items-center gap-4">
            {/* Page Size Select */}
            <div className="flex items-center gap-1">
              <select
                aria-label="Items per page"
                value={pageSize}
                onChange={(e) => {
                  setPageSize(Number(e.target.value));
                  setCurrentPage(1);
                }}
                className="bg-slate-50 dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-md text-xs font-medium text-slate-700 dark:text-slate-200 px-2 py-1 focus:ring-2 focus:ring-sky-500"
              >
                <option value={10}>10 / Page</option>
                <option value={20}>20 / Page</option>
                <option value={50}>50 / Page</option>
              </select>
            </div>

            {/* Pagination Controls */}
            <div className="flex items-center gap-1">
              <button
                type="button"
                onClick={() => setCurrentPage((prev) => Math.max(prev - 1, 1))}
                disabled={currentPage <= 1 || isLoading}
                className="inline-flex items-center gap-1 px-3 py-1.5 border border-slate-300 dark:border-slate-700 rounded-md text-xs font-medium text-slate-600 dark:text-slate-300 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 disabled:opacity-50 transition-colors"
              >
                <ChevronLeft className="w-4 h-4" />
                Previous
              </button>

              {Array.from({ length: totalPages }, (_, i) => i + 1).map((pg) => (
                <button
                  key={pg}
                  type="button"
                  onClick={() => setCurrentPage(pg)}
                  disabled={isLoading}
                  className={`w-7 h-7 flex items-center justify-center rounded-md text-xs font-medium transition-colors ${
                    currentPage === pg
                      ? "bg-sky-500 text-white font-semibold shadow-sm"
                      : "border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700"
                  }`}
                >
                  {pg}
                </button>
              ))}

              <button
                type="button"
                onClick={() => setCurrentPage((prev) => Math.min(prev + 1, totalPages))}
                disabled={currentPage >= totalPages || isLoading}
                className="inline-flex items-center gap-1 px-3 py-1.5 border border-slate-300 dark:border-slate-700 rounded-md text-xs font-medium text-slate-600 dark:text-slate-300 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 disabled:opacity-50 transition-colors"
              >
                Next
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
