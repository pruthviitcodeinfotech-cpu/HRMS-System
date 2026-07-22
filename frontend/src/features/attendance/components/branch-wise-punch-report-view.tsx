"use client";

import React, { useState, useMemo } from "react";
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
  ArrowUpDown,
} from "lucide-react";
import { useBranchOptions } from "@/features/employees/hooks";
import { useBranchWisePunchReport } from "../hooks/use-attendance";
import { BranchWisePunchReportQueryParams, BranchWisePunchCell } from "../services/attendance";

interface HeaderCellProps {
  label: string;
  field: string;
  activeField: string;
  activeDir: "asc" | "desc";
  onSort: (field: string) => void;
  filterValue?: string;
  onFilterChange?: (val: string) => void;
  isSticky?: boolean;
  extraClass?: string;
}

const HeaderCell: React.FC<HeaderCellProps> = ({
  label,
  field,
  activeField,
  activeDir,
  onSort,
  filterValue = "",
  onFilterChange,
  isSticky = false,
  extraClass = "",
}) => {
  const isSorted = activeField === field;
  return (
    <th
      className={`py-3 px-4 whitespace-nowrap bg-slate-50/90 dark:bg-slate-900/90 font-semibold text-slate-700 dark:text-slate-300 group border-b border-slate-200 dark:border-slate-700 ${
        isSticky ? "sticky left-0 z-10 border-r" : ""
      } ${extraClass}`}
    >
      <div className="flex flex-col gap-1.5 w-full">
        {/* Label & Sort Button */}
        <div
          onClick={() => onSort(field)}
          className="flex items-center gap-1.5 cursor-pointer select-none hover:text-sky-600 transition-colors"
        >
          <span>{label}</span>
          <ArrowUpDown
            className={`w-3.5 h-3.5 transition-all ${
              isSorted
                ? "text-sky-500 font-bold scale-110"
                : "text-slate-400 opacity-60 group-hover:opacity-100"
            } ${isSorted && activeDir === "desc" ? "rotate-180" : ""}`}
          />
        </div>

        {/* Hover-activated search input */}
        {onFilterChange && (
          <div
            className={`transition-all duration-300 ease-in-out ${
              filterValue
                ? "h-8 opacity-100 mt-1"
                : "h-0 opacity-0 overflow-hidden group-hover:h-8 group-hover:opacity-100 group-hover:mt-1"
            }`}
            onClick={(e) => e.stopPropagation()}
          >
            <input
              type="text"
              placeholder={`Filter ${label}...`}
              value={filterValue}
              onChange={(e) => onFilterChange(e.target.value)}
              className="w-full text-[11px] px-2 py-1 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-md shadow-sm focus:outline-none focus:border-sky-500 focus:ring-1 focus:ring-sky-500 text-slate-700 dark:text-slate-200 font-normal"
            />
          </div>
        )}
      </div>
    </th>
  );
};

export const BranchWisePunchReportView: React.FC = () => {
  // Date range helpers: Default to 1st of current month to today
  const todayStr = useMemo(() => new Date().toISOString().slice(0, 10), []);
  const firstOfMonthStr = useMemo(() => {
    const d = new Date();
    d.setDate(1);
    return d.toISOString().slice(0, 10);
  }, []);

  // Filter States (inputs)
  const [fromDate, setFromDate] = useState<string>(firstOfMonthStr);
  const [toDate, setToDate] = useState<string>(todayStr);
  const [branchId, setBranchId] = useState<string>("");

  // Applied Filter States (actual query parameters)
  const [searchFromDate, setSearchFromDate] = useState<string>(firstOfMonthStr);
  const [searchToDate, setSearchToDate] = useState<string>(todayStr);
  const [searchBranchId, setSearchBranchId] = useState<string>("");

  // Search & Pagination
  const [searchTerm, setSearchTerm] = useState<string>("");
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(10);
  const [isDropdownOpen, setIsDropdownOpen] = useState<boolean>(false);

  // Sorting States
  const [sortField, setSortField] = useState<string>("employee_code");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("asc");

  // Column Header Filter States
  const [filterEmpId, setFilterEmpId] = useState<string>("");
  const [filterEmpName, setFilterEmpName] = useState<string>("");
  const [filterBranch, setFilterBranch] = useState<string>("");
  const [filterDept, setFilterDept] = useState<string>("");
  const [filterDesignation, setFilterDesignation] = useState<string>("");

  // Load Branch Options
  const { data: branchOptions } = useBranchOptions();

  // Query Params
  const queryParams: BranchWisePunchReportQueryParams = useMemo(() => {
    return {
      date_from: searchFromDate,
      date_to: searchToDate,
      branch_id: searchBranchId ? Number(searchBranchId) : undefined,
      page: currentPage,
      page_size: pageSize,
      sort_by: sortField,
      sort_dir: sortOrder,
    };
  }, [searchFromDate, searchToDate, searchBranchId, currentPage, pageSize, sortField, sortOrder]);

  // Fetch Live Data
  const {
    data: reportData,
    isLoading,
    isError,
    error,
    refetch,
  } = useBranchWisePunchReport(queryParams);

  // Local client-side filters (Quick Search + Column specific filters)
  const filteredItems = useMemo(() => {
    if (!reportData?.items) return [];
    let items = reportData.items;

    // Quick search term
    if (searchTerm.trim()) {
      const term = searchTerm.toLowerCase().trim();
      items = items.filter(
        (item) =>
          item.employee_name.toLowerCase().includes(term) ||
          item.employee_code.toLowerCase().includes(term) ||
          item.department_name.toLowerCase().includes(term) ||
          item.designation_name.toLowerCase().includes(term)
      );
    }

    // Column Header Filters
    if (filterEmpId.trim()) {
      const term = filterEmpId.toLowerCase().trim();
      items = items.filter((item) => item.employee_code.toLowerCase().includes(term));
    }
    if (filterEmpName.trim()) {
      const term = filterEmpName.toLowerCase().trim();
      items = items.filter((item) => item.employee_name.toLowerCase().includes(term));
    }
    if (filterBranch.trim()) {
      const term = filterBranch.toLowerCase().trim();
      items = items.filter((item) => item.branch_name.toLowerCase().includes(term));
    }
    if (filterDept.trim()) {
      const term = filterDept.toLowerCase().trim();
      items = items.filter((item) => item.department_name.toLowerCase().includes(term));
    }
    if (filterDesignation.trim()) {
      const term = filterDesignation.toLowerCase().trim();
      items = items.filter((item) => item.designation_name.toLowerCase().includes(term));
    }

    return items;
  }, [
    reportData?.items,
    searchTerm,
    filterEmpId,
    filterEmpName,
    filterBranch,
    filterDept,
    filterDesignation,
  ]);

  // Generate dynamic date list from response
  const dates = reportData?.dates || [];
  const dateList = useMemo(() => {
    return dates.map((dateStr) => {
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
  }, [dates]);

  // Format minutes helper
  const formatMins = (totalMins: number) => {
    const hrs = Math.floor(totalMins / 60);
    const mins = totalMins % 60;
    return `${hrs}h ${mins}m`;
  };

  // Cell rendering logic matching Petpooja style
  const renderCellContent = (cell?: BranchWisePunchCell) => {
    if (!cell || !cell.has_punch) {
      return <span className="text-slate-400 font-medium">-</span>;
    }
    if (cell.is_missing_punch) {
      return (
        <span className="inline-flex items-center gap-1 font-bold text-amber-600 dark:text-amber-500 text-xs">
          0h 0m
          <AlertTriangle className="w-3.5 h-3.5 fill-amber-500 text-white" />
        </span>
      );
    }
    return (
      <span className="font-medium text-slate-800 dark:text-slate-200 text-xs">
        {formatMins(cell.minutes)}
      </span>
    );
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setSearchFromDate(fromDate);
    setSearchToDate(toDate);
    setSearchBranchId(branchId);
    setCurrentPage(1);
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

  const handleReset = () => {
    setFromDate(firstOfMonthStr);
    setToDate(todayStr);
    setBranchId("");
    setSearchFromDate(firstOfMonthStr);
    setSearchToDate(todayStr);
    setSearchBranchId("");
    setSearchTerm("");
    setCurrentPage(1);
    setSortField("employee_code");
    setSortOrder("asc");
    setFilterEmpId("");
    setFilterEmpName("");
    setFilterBranch("");
    setFilterDept("");
    setFilterDesignation("");
  };

  const handleExportExcel = () => {
    if (!reportData?.items || reportData.items.length === 0) {
      toast.error("No data available to export");
      return;
    }
    try {
      const exportRows = reportData.items.map((row) => {
        const rowObj: Record<string, string | number> = {
          "Employee ID": row.employee_code,
          "Employee Name": row.employee_name,
          Branch: row.branch_name,
          Department: row.department_name,
          Designation: row.designation_name,
          "Total Working Hours": formatMins(row.total_working_minutes),
        };
        dateList.forEach(({ dateStr, dayNumber, monthName }) => {
          const key = `${dayNumber} ${monthName}`;
          const cell = row.daily_punches[dateStr];
          rowObj[key] = cell?.has_punch
            ? cell.is_missing_punch
              ? "0h 0m (Warning)"
              : formatMins(cell.minutes)
            : "-";
        });
        return rowObj;
      });

      const worksheet = XLSX.utils.json_to_sheet(exportRows);
      const workbook = XLSX.utils.book_new();
      XLSX.utils.book_append_sheet(workbook, worksheet, "Branch Wise Punch");
      XLSX.writeFile(
        workbook,
        `Branch_Wise_Punch_Report_${searchFromDate}_to_${searchToDate}.xlsx`
      );
      toast.success("Excel report exported successfully");
    } catch {
      toast.error("Failed to export Excel report");
    }
  };

  const handleExportPDF = () => {
    if (!reportData?.items || reportData.items.length === 0) {
      toast.error("No data available to export");
      return;
    }
    try {
      const doc = new jsPDF({ orientation: "landscape" });
      doc.setFontSize(14);
      doc.text("Branch Wise Punch Report", 14, 15);
      doc.setFontSize(9);
      doc.text(`Period: ${searchFromDate} to ${searchToDate}`, 14, 22);

      const headers = [
        "Employee ID",
        "Employee Name",
        "Branch",
        "Department",
        "Designation",
        "Total Hours",
        ...dateList.map((d) => `${d.dayNumber} ${d.monthName.slice(0, 3)}`),
      ];

      const body = reportData.items.map((row) => [
        row.employee_code,
        row.employee_name,
        row.branch_name,
        row.department_name,
        row.designation_name,
        formatMins(row.total_working_minutes),
        ...dateList.map((d) => {
          const cell = row.daily_punches[d.dateStr];
          return cell?.has_punch
            ? cell.is_missing_punch
              ? "0h 0m (⚠️)"
              : formatMins(cell.minutes)
            : "-";
        }),
      ]);

      autoTable(doc, {
        head: [headers],
        body: body,
        startY: 26,
        styles: { fontSize: 6.5, cellPadding: 2 },
        headStyles: { fillColor: [41, 128, 185], textColor: 255 },
      });

      doc.save(`Branch_Wise_Punch_Report_${searchFromDate}_to_${searchToDate}.pdf`);
      toast.success("PDF report exported successfully");
    } catch {
      toast.error("Failed to export PDF report");
    }
  };

  const pagination = reportData?.pagination || {
    page: 1,
    page_size: 10,
    total_records: 0,
    total_pages: 1,
  };

  const startIndex = (currentPage - 1) * pageSize + 1;
  const endIndex = Math.min(currentPage * pageSize, pagination.total_records);

  return (
    <div className="p-6 max-w-[1600px] mx-auto space-y-6">
      {/* Header with Beta Badge */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
              Branch Wise Punch Report
            </h1>
            <span className="px-2 py-0.5 text-xs font-semibold text-sky-600 bg-sky-50 dark:bg-sky-950/40 rounded-full border border-sky-200 dark:border-sky-800">
              Beta
            </span>
          </div>
          <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
            Track daily working hours and missing punches across branches and departments.
          </p>
        </div>

        {/* Action Buttons matching Petpooja */}
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
            Branch Wise Punch Report
          </button>

          <div className="relative">
            <button
              type="button"
              onClick={() => setIsDropdownOpen((prev) => !prev)}
              className="inline-flex items-center gap-2 px-4 py-2 border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-200 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 rounded-lg text-sm font-medium transition-colors shadow-sm"
            >
              Attendance Report
              <ChevronDown
                className={`w-4 h-4 text-slate-500 transition-transform ${
                  isDropdownOpen ? "rotate-180" : ""
                }`}
              />
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
          {/* Date Picker Range */}
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

          {/* Branch Select Dropdown */}
          <div className="min-w-[200px]">
            <select
              aria-label="Choose Branch"
              value={branchId}
              onChange={(e) => setBranchId(e.target.value)}
              className="w-full bg-slate-50 dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-sm font-medium text-slate-700 dark:text-slate-200 focus:ring-2 focus:ring-sky-500 px-3 py-2"
            >
              <option value="" className="bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100">All branches selected</option>
              {branchOptions?.map((b) => (
                <option key={b.branch_id} value={b.branch_id} className="bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100">
                  {b.branch_name}
                </option>
              ))}
            </select>
          </div>

          {/* Search Button */}
          <button
            type="submit"
            className="inline-flex items-center gap-2 px-6 py-2 bg-sky-500 hover:bg-sky-600 text-white rounded-lg text-sm font-medium transition-colors shadow-sm"
          >
            <Search className="w-4 h-4" />
            Search
          </button>

          {/* Reset Button */}
          <button
            type="button"
            onClick={handleReset}
            className="inline-flex items-center gap-2 px-4 py-2 border border-slate-300 dark:border-slate-700 text-slate-600 dark:text-slate-300 bg-slate-50 dark:bg-slate-900 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg text-sm font-medium transition-colors"
          >
            <RotateCcw className="w-4 h-4" />
            Reset
          </button>

          {/* Quick Search Input */}
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
        {/* Error State View */}
        {isError && (
          <div className="p-6 bg-rose-50 dark:bg-rose-900/20 border-b border-rose-200 dark:border-rose-800 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <AlertTriangle className="w-5 h-5 text-rose-600 dark:text-rose-400" />
              <p className="text-sm font-medium text-rose-800 dark:text-rose-200">
                {error instanceof Error ? error.message : "Failed to load branch wise punch report data."}
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

        {/* Table Wrapper with horizontal scroll */}
        <div className="overflow-x-auto max-w-full">
          <table className="w-full border-collapse text-left text-xs text-slate-700 dark:text-slate-200">
            <thead>
              <tr className="bg-slate-50/90 dark:bg-slate-900/90 border-b border-slate-200 dark:border-slate-700 font-semibold text-slate-700 dark:text-slate-300">
                {/* Fixed Columns */}
                <HeaderCell
                  label="Employee ID"
                  field="employee_code"
                  activeField={sortField}
                  activeDir={sortOrder}
                  onSort={toggleSort}
                  filterValue={filterEmpId}
                  onFilterChange={setFilterEmpId}
                  isSticky={true}
                  extraClass="min-w-[100px] border-r border-slate-200 dark:border-slate-700 px-3 py-3"
                />
                <HeaderCell
                  label="Employee Name"
                  field="employee_name"
                  activeField={sortField}
                  activeDir={sortOrder}
                  onSort={toggleSort}
                  filterValue={filterEmpName}
                  onFilterChange={setFilterEmpName}
                  extraClass="min-w-[170px] px-4"
                />
                <HeaderCell
                  label="Branch"
                  field="branch_name"
                  activeField={sortField}
                  activeDir={sortOrder}
                  onSort={toggleSort}
                  filterValue={filterBranch}
                  onFilterChange={setFilterBranch}
                  extraClass="min-w-[150px] px-4"
                />
                <HeaderCell
                  label="Department"
                  field="department_name"
                  activeField={sortField}
                  activeDir={sortOrder}
                  onSort={toggleSort}
                  filterValue={filterDept}
                  onFilterChange={setFilterDept}
                  extraClass="min-w-[130px] px-4"
                />
                <HeaderCell
                  label="Designation"
                  field="designation_name"
                  activeField={sortField}
                  activeDir={sortOrder}
                  onSort={toggleSort}
                  filterValue={filterDesignation}
                  onFilterChange={setFilterDesignation}
                  extraClass="min-w-[140px] px-4"
                />
                <HeaderCell
                  label="Total Working Hours"
                  field="total_working_minutes"
                  activeField={sortField}
                  activeDir={sortOrder}
                  onSort={toggleSort}
                  extraClass="min-w-[140px] px-4 border-r border-slate-200 dark:border-slate-700"
                />

                {/* Dynamic Date Headers */}
                {!isLoading &&
                  !isError &&
                  dateList.map(({ dateStr, dayNumber, monthName, dayName }) => (
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
              {/* Loading Skeleton state */}
              {isLoading &&
                Array.from({ length: 5 }).map((_, idx) => (
                  <tr key={idx} className="animate-pulse">
                    <td className="py-4 px-3 sticky left-0 z-10 bg-white dark:bg-slate-800 border-r border-slate-200 dark:border-slate-700">
                      <div className="h-4 bg-slate-200 dark:bg-slate-700 rounded w-12" />
                    </td>
                    <td className="py-4 px-4">
                      <div className="h-4 bg-slate-200 dark:bg-slate-700 rounded w-28" />
                    </td>
                    <td className="py-4 px-4">
                      <div className="h-4 bg-slate-200 dark:bg-slate-700 rounded w-20" />
                    </td>
                    <td className="py-4 px-4">
                      <div className="h-4 bg-slate-200 dark:bg-slate-700 rounded w-20" />
                    </td>
                    <td className="py-4 px-4">
                      <div className="h-4 bg-slate-200 dark:bg-slate-700 rounded w-20" />
                    </td>
                    <td className="py-4 px-4 border-r border-slate-200 dark:border-slate-700">
                      <div className="h-4 bg-slate-200 dark:bg-slate-700 rounded w-16" />
                    </td>
                    {Array.from({ length: 15 }).map((_, dIdx) => (
                      <td
                        key={dIdx}
                        className="py-4 px-2 border-r border-slate-100 dark:border-slate-800 text-center"
                      >
                        <div className="h-4 bg-slate-200 dark:bg-slate-700 rounded w-8 mx-auto" />
                      </td>
                    ))}
                  </tr>
                ))}

              {/* Standard Data Rows */}
              {!isLoading &&
                !isError &&
                filteredItems.map((row) => (
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
                      {row.branch_name}
                    </td>
                    <td className="py-3 px-4 text-slate-600 dark:text-slate-400">
                      {row.department_name}
                    </td>
                    <td className="py-3 px-4 text-slate-600 dark:text-slate-400">
                      {row.designation_name}
                    </td>
                    <td className="py-3 px-4 font-semibold text-slate-900 dark:text-slate-100 border-r border-slate-200 dark:border-slate-700">
                      {formatMins(row.total_working_minutes)}
                    </td>

                    {/* Dynamic punch cells */}
                    {dateList.map(({ dateStr }) => {
                      const cell = row.daily_punches[dateStr];
                      return (
                        <td
                          key={dateStr}
                          className="py-3 px-2 text-center border-r border-slate-100 dark:border-slate-800"
                        >
                          {renderCellContent(cell)}
                        </td>
                      );
                    })}
                  </tr>
                ))}

              {/* Empty State View */}
              {!isLoading && !isError && filteredItems.length === 0 && (
                <tr>
                  <td
                    colSpan={6 + dateList.length}
                    className="py-12 text-center text-slate-500 dark:text-slate-400"
                  >
                    <div className="flex flex-col items-center justify-center gap-2">
                      <CalendarDays className="w-8 h-8 text-slate-300 dark:text-slate-600" />
                      <p className="text-sm font-medium">No branch wise punch records found.</p>
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
            Showing{" "}
            <span className="font-medium text-slate-700 dark:text-slate-200">
              {filteredItems.length ? startIndex : 0}
            </span>{" "}
            to{" "}
            <span className="font-medium text-slate-700 dark:text-slate-200">
              {Math.min(endIndex, startIndex + filteredItems.length - 1)}
            </span>{" "}
            of{" "}
            <span className="font-medium text-slate-700 dark:text-slate-200">
              {pagination.total_records}
            </span>{" "}
            Results
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

              {Array.from({ length: pagination.total_pages }, (_, i) => i + 1).map((pg) => (
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
                onClick={() => setCurrentPage((prev) => Math.min(prev + 1, pagination.total_pages))}
                disabled={currentPage >= pagination.total_pages || isLoading}
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
