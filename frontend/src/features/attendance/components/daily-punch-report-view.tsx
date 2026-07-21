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
} from "lucide-react";
import { useBranchOptions } from "@/features/employees/hooks";
import { useDailyPunchReport } from "../hooks/use-attendance";
import { DailyPunchReportQueryParams, DailyPunchMatrixRow } from "../services/attendance";

export const DailyPunchReportView: React.FC = () => {
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

  // Options Data
  const { data: branchOptions } = useBranchOptions();

  // Construct backend API query params
  const queryParams: DailyPunchReportQueryParams = useMemo(() => {
    const params: DailyPunchReportQueryParams = {
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

  // Query Backend Daily Punch Report API
  const { data, isLoading, isError, error, refetch } = useDailyPunchReport(queryParams);

  useEffect(() => {
    if (isError && error) {
      toast.error(error instanceof Error ? error.message : "Failed to fetch daily punch report data");
    }
  }, [isError, error]);

  // Construct dynamic date column list from backend response or fallback range
  const dateList = useMemo(() => {
    if (data?.dates && data.dates.length > 0) {
      return data.dates.map((dateStr) => {
        const [yyyy, mm, dd] = dateStr.split("-");
        const formattedHeader = `${dd}-${mm}-${yyyy}`;
        const dObj = new Date(dateStr);
        const dayName = isNaN(dObj.getTime())
          ? ""
          : dObj.toLocaleDateString("en-US", { weekday: "long" });
        return { dateStr, dayName, formattedHeader };
      });
    }

    const list: { dateStr: string; dayName: string; formattedHeader: string }[] = [];
    if (!searchFromDate || !searchToDate) return list;

    let curr = new Date(searchFromDate);
    const end = new Date(searchToDate);
    let count = 0;

    while (curr <= end && count < 31) {
      const dateStr = curr.toISOString().slice(0, 10);
      const [yyyy, mm, dd] = dateStr.split("-");
      const formattedHeader = `${dd}-${mm}-${yyyy}`;
      const dayName = curr.toLocaleDateString("en-US", { weekday: "long" });
      list.push({ dateStr, dayName, formattedHeader });
      curr.setDate(curr.getDate() + 1);
      count++;
    }
    return list;
  }, [data?.dates, searchFromDate, searchToDate]);

  // Matrix rows from backend response with optional local text search filter
  const matrixRows: DailyPunchMatrixRow[] = useMemo(() => {
    if (!data?.items) return [];

    let result = data.items;

    if (searchTerm.trim()) {
      const term = searchTerm.toLowerCase();
      result = result.filter(
        (r) =>
          r.employee_code.toLowerCase().includes(term) ||
          r.employee_name.toLowerCase().includes(term) ||
          r.department_name.toLowerCase().includes(term) ||
          r.designation_name.toLowerCase().includes(term)
      );
    }

    return result;
  }, [data?.items, searchTerm]);

  // Pagination metadata
  const totalRecords = data?.pagination?.total_records ?? matrixRows.length;
  const totalPages = data?.pagination?.total_pages ?? Math.max(1, Math.ceil(totalRecords / pageSize));

  // Handle Search submit
  const handleSearch = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setSearchFromDate(fromDate);
    setSearchToDate(toDate);
    setSearchBranchId(branchId);
    setCurrentPage(1);
    refetch();
    toast.success("Applied search filters");
  };

  // Handle Reset filters
  const handleReset = () => {
    const defaultFrom = "2026-07-01";
    const defaultTo = todayStr;
    setFromDate(defaultFrom);
    setToDate(defaultTo);
    setBranchId("");
    setSearchFromDate(defaultFrom);
    setSearchToDate(defaultTo);
    setSearchBranchId("");
    setSearchTerm("");
    setCurrentPage(1);
    toast.info("Filters reset to default");
  };

  // Excel Export Handler
  const handleExportExcel = () => {
    if (!matrixRows || matrixRows.length === 0) {
      toast.error("No data available to export");
      return;
    }

    const exportRows = matrixRows.map((r) => {
      const rowObj: Record<string, string> = {
        "Employee ID": r.employee_code,
        "Employee Name": r.employee_name,
        Department: r.department_name,
        Designation: r.designation_name,
      };

      dateList.forEach((d) => {
        const cell = r.daily_punches[d.dateStr];
        if (cell?.first_in || cell?.last_out) {
          rowObj[`${d.formattedHeader} (${d.dayName})`] = `${cell.first_in || "-"} / ${
            cell.last_out || "-"
          }${cell.is_missing_punch ? " [!] Missing" : ""}`;
        } else if (cell?.is_off_day) {
          rowObj[`${d.formattedHeader} (${d.dayName})`] = "Off";
        } else {
          rowObj[`${d.formattedHeader} (${d.dayName})`] = "-";
        }
      });

      return rowObj;
    });

    const worksheet = XLSX.utils.json_to_sheet(exportRows);
    const workbook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(workbook, worksheet, "Daily Punch Report");
    XLSX.writeFile(workbook, `Daily_Punch_Report_${searchFromDate}_to_${searchToDate}.xlsx`);
    toast.success("Excel report downloaded successfully");
  };

  // PDF Export Handler
  const handleExportPdf = () => {
    if (!matrixRows || matrixRows.length === 0) {
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

      doc.setFontSize(16);
      doc.setTextColor(2, 132, 199);
      doc.text("DAILY PUNCH REPORT", 14, 15);

      doc.setFontSize(9);
      doc.setTextColor(71, 85, 105);
      doc.text(
        `Date Range: ${searchFromDate || "01-07-2026"} to ${searchToDate || "Today"} | Branch: ${branchLabel} | Total Employees: ${totalRecords}`,
        14,
        22
      );

      const tableHeaders = [
        "Emp ID",
        "Employee Name",
        "Dept",
        "Designation",
        ...dateList.map((d) => d.formattedHeader.slice(0, 5)),
      ];

      const tableRows = matrixRows.map((r) => [
        r.employee_code,
        r.employee_name,
        r.department_name,
        r.designation_name,
        ...dateList.map((d) => {
          const cell = r.daily_punches[d.dateStr];
          if (cell?.first_in || cell?.last_out) {
            return `${cell.first_in || "-"}\n${cell.last_out || "-"}`;
          }
          if (cell?.is_off_day) return "Off";
          return "-";
        }),
      ]);

      autoTable(doc, {
        head: [tableHeaders],
        body: tableRows,
        startY: 26,
        styles: {
          fontSize: 6.5,
          cellPadding: 1.5,
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

      doc.save(`Daily_Punch_Report_${searchFromDate}_to_${searchToDate}.pdf`);
      toast.success("PDF report downloaded successfully");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to generate PDF download");
    }
  };

  return (
    <div className="p-6 space-y-6">
      {/* Title */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100 mb-1">
          Daily Punch Report
        </h1>
        <p className="text-sm text-slate-500 dark:text-slate-400">
          Multi-day punch matrix showing daily check-in / check-out timestamps, off-days, and missing punch alerts.
        </p>
      </div>

      {/* Filter Bar */}
      <div className="bg-card border border-border rounded-xl p-4 shadow-xs">
        <form onSubmit={handleSearch} className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex flex-wrap items-center gap-3">
            {/* Date Range Selector */}
            <div className="flex items-center space-x-2 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg px-3 py-2 text-xs">
              <input
                type="date"
                value={fromDate}
                onChange={(e) => setFromDate(e.target.value)}
                className="bg-transparent text-slate-700 dark:text-slate-300 focus:outline-hidden font-medium"
              />
              <span className="text-slate-400 font-semibold">—</span>
              <input
                type="date"
                value={toDate}
                onChange={(e) => setToDate(e.target.value)}
                className="bg-transparent text-slate-700 dark:text-slate-300 focus:outline-hidden font-medium"
              />
            </div>

            {/* Branch Selector */}
            <select
              value={branchId}
              onChange={(e) => setBranchId(e.target.value)}
              className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-700 dark:text-slate-300 focus:outline-hidden focus:ring-1 focus:ring-sky-500 font-medium"
            >
              <option value="">Choose Branch</option>
              {branchOptions?.map((b) => (
                <option key={b.branch_id} value={b.branch_id}>
                  {b.branch_name}
                </option>
              ))}
            </select>

            {/* Search Input Filter */}
            <div className="relative">
              <input
                type="text"
                placeholder="Filter employee name / ID..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg pl-8 pr-3 py-2 text-xs text-slate-700 dark:text-slate-300 focus:outline-hidden focus:ring-1 focus:ring-sky-500 font-medium w-48"
              />
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2.5" />
            </div>

            {/* Apply Search Button */}
            <button
              type="submit"
              className="inline-flex items-center px-4 py-2 bg-sky-600 hover:bg-sky-700 text-white font-medium text-xs rounded-lg transition-colors shadow-xs"
            >
              <Search className="w-3.5 h-3.5 mr-1.5" />
              Search
            </button>

            {/* Reset Button */}
            <button
              type="button"
              onClick={handleReset}
              className="inline-flex items-center px-3 py-2 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 font-medium text-xs rounded-lg transition-colors"
            >
              <RotateCcw className="w-3.5 h-3.5 mr-1.5" />
              Reset
            </button>
          </div>

          {/* Export Actions */}
          <div className="flex items-center space-x-2">
            <button
              type="button"
              onClick={handleExportExcel}
              className="inline-flex items-center px-3.5 py-2 bg-emerald-50 hover:bg-emerald-100 dark:bg-emerald-950/40 dark:hover:bg-emerald-900/40 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800 font-medium text-xs rounded-lg transition-colors"
            >
              <FileSpreadsheet className="w-3.5 h-3.5 mr-1.5" />
              Export Excel
            </button>
            <button
              type="button"
              onClick={handleExportPdf}
              className="inline-flex items-center px-3.5 py-2 bg-rose-50 hover:bg-rose-100 dark:bg-rose-950/40 dark:hover:bg-rose-900/40 text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-800 font-medium text-xs rounded-lg transition-colors"
            >
              <FileText className="w-3.5 h-3.5 mr-1.5" />
              Export PDF
            </button>
          </div>
        </form>
      </div>

      {/* Main Table Container */}
      <div className="bg-card border border-border rounded-xl shadow-xs overflow-hidden">
        {isLoading ? (
          <div className="p-12 text-center text-slate-500 dark:text-slate-400">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-sky-600 mb-3"></div>
            <p className="text-sm font-medium">Loading Daily Punch Matrix...</p>
          </div>
        ) : isError ? (
          <div className="p-12 text-center text-slate-500 dark:text-slate-400">
            <AlertTriangle className="w-10 h-10 mx-auto text-rose-500 mb-3" />
            <p className="text-base font-semibold text-slate-800 dark:text-slate-200">
              Failed to load daily punch report
            </p>
            <p className="text-xs text-slate-500 mt-1 mb-4">
              {error instanceof Error ? error.message : "An unexpected server error occurred."}
            </p>
            <button
              type="button"
              onClick={() => refetch()}
              className="inline-flex items-center px-4 py-2 bg-sky-600 hover:bg-sky-700 text-white font-medium text-xs rounded-lg transition-colors"
            >
              <RefreshCw className="w-3.5 h-3.5 mr-1.5" />
              Retry
            </button>
          </div>
        ) : matrixRows.length === 0 ? (
          <div className="p-12 text-center text-slate-500 dark:text-slate-400">
            <AlertTriangle className="w-10 h-10 mx-auto text-amber-500 mb-3 opacity-80" />
            <p className="text-base font-semibold text-slate-800 dark:text-slate-200">
              No punch records found
            </p>
            <p className="text-xs text-slate-500 mt-1">
              Try adjusting your date range or branch selection criteria.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-sky-50/80 dark:bg-slate-800/80 border-b border-border text-slate-700 dark:text-slate-200">
                  <th className="py-3 px-4 font-bold sticky left-0 z-20 bg-sky-50 dark:bg-slate-800 border-r border-slate-200 dark:border-slate-700 min-w-[90px]">
                    Employee ID
                  </th>
                  <th className="py-3 px-4 font-bold sticky left-[90px] z-20 bg-sky-50 dark:bg-slate-800 border-r border-slate-200 dark:border-slate-700 min-w-[140px]">
                    Employee Name
                  </th>
                  <th className="py-3 px-4 font-bold min-w-[110px]">Department</th>
                  <th className="py-3 px-4 font-bold min-w-[120px]">Designation</th>

                  {/* Dynamic Date Header Columns */}
                  {dateList.map((d) => (
                    <th
                      key={d.dateStr}
                      className="py-2 px-3 font-bold text-center border-l border-slate-200 dark:border-slate-700 min-w-[105px] whitespace-nowrap"
                    >
                      <div className="text-[11px] text-slate-800 dark:text-slate-200">
                        {d.formattedHeader}
                      </div>
                      <div className="text-[10px] font-normal text-slate-500 dark:text-slate-400">
                        {d.dayName}
                      </div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {matrixRows.map((row) => (
                  <tr
                    key={row.employee_id}
                    className="hover:bg-slate-50/80 dark:hover:bg-slate-800/50 transition-colors"
                  >
                    <td className="py-3 px-4 font-semibold text-slate-900 dark:text-slate-100 sticky left-0 z-10 bg-white dark:bg-slate-900 border-r border-slate-200 dark:border-slate-800">
                      {row.employee_code}
                    </td>
                    <td className="py-3 px-4 font-medium text-slate-800 dark:text-slate-200 sticky left-[90px] z-10 bg-white dark:bg-slate-900 border-r border-slate-200 dark:border-slate-800 whitespace-nowrap">
                      {row.employee_name}
                    </td>
                    <td className="py-3 px-4 text-slate-600 dark:text-slate-400">
                      {row.department_name}
                    </td>
                    <td className="py-3 px-4 text-slate-600 dark:text-slate-400">
                      {row.designation_name}
                    </td>

                    {/* Matrix Daily Punch Cells */}
                    {dateList.map((d) => {
                      const cell = row.daily_punches[d.dateStr];
                      const firstIn = cell?.first_in;
                      const lastOut = cell?.last_out;
                      const isMissing = cell?.is_missing_punch;
                      const isOff = cell?.is_off_day;

                      return (
                        <td
                          key={d.dateStr}
                          className="py-2.5 px-3 border-l border-slate-100 dark:border-slate-800/80 text-center align-middle"
                        >
                          {firstIn || lastOut ? (
                            <div className="flex flex-col items-center justify-center space-y-0.5">
                              <div className="flex items-center space-x-1">
                                <span className="text-[11px] font-medium text-sky-700 dark:text-sky-400 underline decoration-sky-300">
                                  {firstIn || "-"}
                                </span>
                                {isMissing && (
                                  <span title="Missing Punch Alert">
                                    <AlertTriangle className="w-3.5 h-3.5 text-amber-500 fill-amber-100 dark:fill-amber-900/40 inline-block" />
                                  </span>
                                )}
                              </div>
                              {lastOut && (
                                <span className="text-[11px] font-medium text-sky-700 dark:text-sky-400 underline decoration-sky-300">
                                  {lastOut}
                                </span>
                              )}
                            </div>
                          ) : isOff ? (
                            <div className="flex items-center justify-center">
                              <span
                                className="w-2.5 h-2.5 rounded-full border-2 border-sky-500 inline-block"
                                title="Scheduled Off Day / Holiday"
                              ></span>
                            </div>
                          ) : (
                            <span className="text-slate-300 dark:text-slate-600 font-bold">—</span>
                          )}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Footer Pagination Bar */}
        {!isLoading && !isError && matrixRows.length > 0 && (
          <div className="px-4 py-3 bg-slate-50 dark:bg-slate-900 border-t border-border flex items-center justify-between">
            <div className="text-xs text-slate-500 dark:text-slate-400">
              Showing <span className="font-semibold text-slate-800 dark:text-slate-200">{(currentPage - 1) * pageSize + 1}</span> to{" "}
              <span className="font-semibold text-slate-800 dark:text-slate-200">
                {Math.min(currentPage * pageSize, totalRecords)}
              </span>{" "}
              of <span className="font-semibold text-slate-800 dark:text-slate-200">{totalRecords}</span> employees
            </div>

            <div className="flex items-center space-x-2">
              <button
                type="button"
                disabled={currentPage === 1}
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                className="p-1.5 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 disabled:opacity-40 transition-colors"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <span className="text-xs text-slate-600 dark:text-slate-300 font-medium px-2">
                Page {currentPage} of {totalPages}
              </span>
              <button
                type="button"
                disabled={currentPage >= totalPages}
                onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                className="p-1.5 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 disabled:opacity-40 transition-colors"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
