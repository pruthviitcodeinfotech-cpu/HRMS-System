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
  RefreshCw,
  Clock,
} from "lucide-react";
import { useBranchOptions } from "@/features/employees/hooks";
import { useWorkingHoursReport } from "../hooks/use-attendance";
import {
  WorkingHoursReportQueryParams,
  WorkingHoursMatrixRow,
} from "../services/attendance";

export const WorkingHoursReportView: React.FC = () => {
  const todayStr = useMemo(() => new Date().toISOString().slice(0, 10), []);

  // Form Input States
  const [fromDate, setFromDate] = useState<string>("2026-07-01");
  const [toDate, setToDate] = useState<string>(todayStr);
  const [branchId, setBranchId] = useState<string>("");

  // Applied Filter States
  const [searchFromDate, setSearchFromDate] = useState<string>("2026-07-01");
  const [searchToDate, setSearchToDate] = useState<string>(todayStr);
  const [searchBranchId, setSearchBranchId] = useState<string>("");

  // Pagination & Search States
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [pageSize] = useState<number>(10);
  const [searchTerm, setSearchTerm] = useState<string>("");

  // Options Data (Branch Lookup Hook)
  const { data: branchOptions } = useBranchOptions();

  // Construct backend API query params
  const queryParams: WorkingHoursReportQueryParams = useMemo(() => {
    const params: WorkingHoursReportQueryParams = {
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

  // Query Backend Working Hours Report API via React Query
  const { data, isLoading, isError, error, refetch } = useWorkingHoursReport(queryParams);

  useEffect(() => {
    if (isError && error) {
      toast.error(error instanceof Error ? error.message : "Failed to fetch working hours report data");
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
      (item: WorkingHoursMatrixRow) =>
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

  // Export to Excel
  const handleExportExcel = () => {
    if (!data?.items || data.items.length === 0) {
      toast.error("No data available to export");
      return;
    }

    try {
      const exportData = data.items.map((row) => {
        const rowObj: Record<string, string> = {
          "Employee ID": row.employee_code,
          "Employee Name": row.employee_name,
          Department: row.department_name,
          Designation: row.designation_name,
          "Total Working Hour": row.total_working_hours_str,
          "Total Break Hour": row.total_break_hours_str,
        };

        dateList.forEach(({ dateStr, dayNumber, monthName }) => {
          const key = `${dayNumber} ${monthName}`;
          const cell = row.daily_hours[dateStr];
          rowObj[key] = cell?.working_hours_str || "0h";
        });

        return rowObj;
      });

      const worksheet = XLSX.utils.json_to_sheet(exportData);
      const workbook = XLSX.utils.book_new();
      XLSX.utils.book_append_sheet(workbook, worksheet, "Working Hours Report");
      XLSX.writeFile(workbook, `Working_Hours_Report_${searchFromDate}_to_${searchToDate}.xlsx`);
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
      doc.text("Working Hours Report", 14, 15);
      doc.setFontSize(9);
      doc.text(`Period: ${searchFromDate} to ${searchToDate}`, 14, 22);

      const headers = [
        "Employee ID",
        "Employee Name",
        "Department",
        "Designation",
        "Total Work",
        "Total Break",
        ...dateList.map((d) => `${d.dayNumber} ${d.monthName.slice(0, 3)}`),
      ];

      const body = data.items.map((row) => [
        row.employee_code,
        row.employee_name,
        row.department_name,
        row.designation_name,
        row.total_working_hours_str,
        row.total_break_hours_str,
        ...dateList.map((d) => row.daily_hours[d.dateStr]?.working_hours_str || "0h"),
      ]);

      autoTable(doc, {
        head: [headers],
        body: body,
        startY: 26,
        styles: { fontSize: 7, cellPadding: 2 },
        headStyles: { fillColor: [41, 128, 185], textColor: 255 },
      });

      doc.save(`Working_Hours_Report_${searchFromDate}_to_${searchToDate}.pdf`);
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
            Working Hours Report
          </h1>
          <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
            Review total working hours, break hours, and daily attendance matrix calculations.
          </p>
        </div>

        {/* Action Buttons */}
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
            Export PDF
          </button>
        </div>
      </div>

      {/* Filter Control Card */}
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
          <div className="min-w-[180px]">
            <select
              aria-label="Branch Select"
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
            className="inline-flex items-center gap-2 px-5 py-2 bg-sky-600 hover:bg-sky-700 text-white rounded-lg text-sm font-medium transition-colors shadow-sm"
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

          {/* Quick Filter Search input */}
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

      {/* Main Table Content Card */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm overflow-hidden">
        {/* Error State Banner */}
        {isError && (
          <div className="p-6 bg-rose-50 dark:bg-rose-900/20 border-b border-rose-200 dark:border-rose-800 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <AlertTriangle className="w-5 h-5 text-rose-600 dark:text-rose-400" />
              <p className="text-sm font-medium text-rose-800 dark:text-rose-200">
                {error instanceof Error ? error.message : "Failed to load working hours report data."}
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

        {/* Table View */}
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-left text-xs text-slate-700 dark:text-slate-200">
            <thead>
              <tr className="bg-slate-50 dark:bg-slate-900/80 border-b border-slate-200 dark:border-slate-700 font-semibold text-slate-600 dark:text-slate-300">
                <th className="py-3 px-4 min-w-[90px] whitespace-nowrap">Employee ID</th>
                <th className="py-3 px-4 min-w-[140px] whitespace-nowrap">Employee Name</th>
                <th className="py-3 px-4 min-w-[110px] whitespace-nowrap">Department</th>
                <th className="py-3 px-4 min-w-[110px] whitespace-nowrap">Designation</th>
                <th className="py-3 px-4 min-w-[120px] whitespace-nowrap text-center bg-slate-100 dark:bg-slate-800">
                  Total Working Hour
                </th>
                <th className="py-3 px-4 min-w-[110px] whitespace-nowrap text-center bg-slate-100 dark:bg-slate-800">
                  Total Break Hour
                </th>

                {/* Dynamic Date Headers */}
                {dateList.map(({ dateStr, dayNumber, monthName, dayName }) => (
                  <th
                    key={dateStr}
                    className="py-2 px-3 min-w-[95px] text-center border-l border-slate-200 dark:border-slate-700 whitespace-nowrap"
                  >
                    <div className="font-semibold text-slate-800 dark:text-slate-100">
                      {dayNumber}
                    </div>
                    <div className="text-[10px] text-slate-500 dark:text-slate-400 font-normal">
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
                    <td className="py-4 px-4"><div className="h-4 bg-slate-200 dark:bg-slate-700 rounded w-12" /></td>
                    <td className="py-4 px-4"><div className="h-4 bg-slate-200 dark:bg-slate-700 rounded w-28" /></td>
                    <td className="py-4 px-4"><div className="h-4 bg-slate-200 dark:bg-slate-700 rounded w-20" /></td>
                    <td className="py-4 px-4"><div className="h-4 bg-slate-200 dark:bg-slate-700 rounded w-20" /></td>
                    <td className="py-4 px-4 bg-slate-50/50 dark:bg-slate-900/30"><div className="h-4 bg-slate-200 dark:bg-slate-700 rounded w-14 mx-auto" /></td>
                    <td className="py-4 px-4 bg-slate-50/50 dark:bg-slate-900/30"><div className="h-4 bg-slate-200 dark:bg-slate-700 rounded w-14 mx-auto" /></td>
                    {dateList.map((d) => (
                      <td key={d.dateStr} className="py-4 px-3 border-l border-slate-100 dark:border-slate-800">
                        <div className="h-4 bg-slate-200 dark:bg-slate-700 rounded w-10 mx-auto" />
                      </td>
                    ))}
                  </tr>
                ))}

              {/* Data Rows */}
              {!isLoading &&
                filteredItems.length > 0 &&
                filteredItems.map((row: WorkingHoursMatrixRow) => (
                  <tr
                    key={row.employee_id}
                    className="hover:bg-slate-50/80 dark:hover:bg-slate-700/50 transition-colors"
                  >
                    <td className="py-3 px-4 font-medium text-slate-900 dark:text-slate-100">
                      {row.employee_code}
                    </td>
                    <td className="py-3 px-4 font-medium text-slate-800 dark:text-slate-200">
                      {row.employee_name}
                    </td>
                    <td className="py-3 px-4 text-slate-600 dark:text-slate-400">
                      {row.department_name}
                    </td>
                    <td className="py-3 px-4 text-slate-600 dark:text-slate-400">
                      {row.designation_name}
                    </td>
                    <td className="py-3 px-4 text-center font-semibold text-slate-900 dark:text-slate-100 bg-slate-50/50 dark:bg-slate-900/30">
                      {row.total_working_hours_str}
                    </td>
                    <td className="py-3 px-4 text-center text-slate-600 dark:text-slate-400 bg-slate-50/50 dark:bg-slate-900/30">
                      {row.total_break_hours_str}
                    </td>

                    {/* Daily Hours Matrix Cells */}
                    {dateList.map(({ dateStr }) => {
                      const cell = row.daily_hours[dateStr];
                      const workStr = cell?.working_hours_str || "0h";
                      const isMissing = cell?.is_missing_punch;
                      const isOff = cell?.is_off_day;

                      return (
                        <td
                          key={dateStr}
                          className="py-3 px-3 text-center border-l border-slate-100 dark:border-slate-800"
                        >
                          <div className="inline-flex items-center justify-center gap-1">
                            <span
                              className={`font-medium underline decoration-slate-300 dark:decoration-slate-600 underline-offset-2 ${
                                isOff
                                  ? "text-slate-400 dark:text-slate-500"
                                  : workStr === "0h"
                                  ? "text-slate-600 dark:text-slate-400"
                                  : "text-slate-900 dark:text-slate-100"
                              }`}
                            >
                              {workStr}
                            </span>

                            {/* Alert / Warning Icon */}
                            {isMissing && (
                              <span
                                title="Missing punch or incomplete cycle"
                                className="inline-flex items-center justify-center p-0.5 rounded bg-amber-100 dark:bg-amber-900/40 text-amber-600 dark:text-amber-400"
                              >
                                <AlertTriangle className="w-3 h-3" />
                              </span>
                            )}
                          </div>
                        </td>
                      );
                    })}
                  </tr>
                ))}

              {/* Empty State */}
              {!isLoading && filteredItems.length === 0 && (
                <tr>
                  <td
                    colSpan={6 + (dateList.length || 1)}
                    className="py-12 text-center text-slate-500 dark:text-slate-400"
                  >
                    <div className="flex flex-col items-center justify-center gap-2">
                      <Clock className="w-8 h-8 text-slate-300 dark:text-slate-600" />
                      <p className="text-sm font-medium">No working hours records found.</p>
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

        {/* Server-Side Pagination Footer */}
        <div className="p-4 bg-white dark:bg-slate-800 border-t border-slate-200 dark:border-slate-700 flex flex-col sm:flex-row items-center justify-between gap-4">
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Showing <span className="font-medium text-slate-700 dark:text-slate-200">{filteredItems.length}</span> of{" "}
            <span className="font-medium text-slate-700 dark:text-slate-200">{totalRecords}</span> total records
          </p>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setCurrentPage((prev) => Math.max(prev - 1, 1))}
              disabled={currentPage <= 1 || isLoading}
              className="inline-flex items-center gap-1 px-3 py-1.5 border border-slate-300 dark:border-slate-700 rounded-md text-xs font-medium text-slate-600 dark:text-slate-300 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 disabled:opacity-50 transition-colors"
            >
              <ChevronLeft className="w-4 h-4" />
              Previous
            </button>

            <span className="text-xs font-medium text-slate-700 dark:text-slate-300 px-2">
              Page {currentPage} of {totalPages}
            </span>

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
  );
};
