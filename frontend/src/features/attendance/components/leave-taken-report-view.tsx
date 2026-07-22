"use client";

import React, { useState, useMemo, useRef, useEffect } from "react";
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
  ArrowUpDown,
  CalendarDays,
} from "lucide-react";


import { useLeaveTakenReport } from "../hooks/use-attendance";
import { useBranchOptions, useDepartmentOptions } from "@/features/employees/hooks";



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
  const [isFilterOpen, setIsFilterOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    if (!isFilterOpen) return;
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsFilterOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [isFilterOpen]);

  return (
    <th
      className={`py-3 px-4 bg-slate-50/90 dark:bg-slate-900/90 font-semibold text-slate-700 dark:text-slate-300 group border-b border-slate-200 dark:border-slate-700 relative ${
        isSticky ? "sticky left-0 z-10 border-r" : ""
      } ${extraClass}`}
    >
      <div className="flex items-center justify-between gap-1.5 w-full">
        {/* Label & Sort Button */}
        <div
          onClick={() => onSort(field)}
          className="flex items-center gap-1.5 cursor-pointer select-none hover:text-sky-600 transition-colors"
        >
          <span>{label}</span>
          <ArrowUpDown
            className={`w-3 h-3 transition-all ${
              isSorted
                ? "text-sky-500 font-bold scale-110"
                : "text-slate-400 opacity-60 group-hover:opacity-100"
            } ${isSorted && activeDir === "desc" ? "rotate-180" : ""}`}
          />
        </div>

        {/* Hover-activated search icon button */}
        {onFilterChange && (
          <div className="relative" ref={dropdownRef}>
            <button
              type="button"
              onClick={() => setIsFilterOpen(!isFilterOpen)}
              className={`p-1 rounded hover:bg-slate-200 dark:hover:bg-slate-800 transition-all ${
                filterValue
                  ? "text-sky-500 opacity-100"
                  : "text-slate-400 opacity-0 group-hover:opacity-100"
              }`}
            >
              <Search className="w-3.5 h-3.5" />
            </button>

            {/* Dropdown Popover */}
            {isFilterOpen && (
              <div className="absolute right-0 mt-2 w-48 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg shadow-xl p-3 z-30 animate-in fade-in slide-in-from-top-1 duration-150">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[11px] font-bold text-slate-500 dark:text-slate-400">Filter {label}</span>
                  {filterValue && (
                    <button
                      type="button"
                      onClick={() => {
                        onFilterChange("");
                        setIsFilterOpen(false);
                      }}
                      className="text-[10px] text-rose-500 hover:underline"
                    >
                      Clear
                    </button>
                  )}
                </div>
                <input
                  type="text"
                  placeholder={`Search ${label}...`}
                  value={filterValue}
                  onChange={(e) => onFilterChange(e.target.value)}
                  autoFocus
                  className="w-full text-xs px-2 py-1.5 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-md focus:outline-none focus:border-sky-500 focus:ring-1 focus:ring-sky-500 text-slate-700 dark:text-slate-200 font-normal"
                />
              </div>
            )}
          </div>
        )}
      </div>
    </th>
  );
};

export const LeaveTakenReportView: React.FC = () => {
  const todayStr = useMemo(() => new Date().toISOString().slice(0, 10), []);
  const firstOfMonthStr = useMemo(() => {
    const d = new Date();
    d.setDate(1);
    return d.toISOString().slice(0, 10);
  }, []);

  // Filter States
  const [fromDate, setFromDate] = useState<string>(firstOfMonthStr);
  const [toDate, setToDate] = useState<string>(todayStr);
  const [searchFromDate, setSearchFromDate] = useState<string>(firstOfMonthStr);
  const [searchToDate, setSearchToDate] = useState<string>(todayStr);

  const [branchId, setBranchId] = useState<string>("");
  const [searchBranchId, setSearchBranchId] = useState<string>("");

  const [deptId, setDeptId] = useState<string>("");
  const [searchDeptId, setSearchDeptId] = useState<string>("");

  // Search & Pagination
  const [searchTerm, setSearchTerm] = useState<string>("");
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(10);

  // Sorting
  const [sortField, setSortField] = useState<string>("employee_code");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("asc");

  // Column Header Filters
  const [filterEmpId, setFilterEmpId] = useState<string>("");
  const [filterEmpName, setFilterEmpName] = useState<string>("");
  const [filterDept, setFilterDept] = useState<string>("");
  const [filterDesignation, setFilterDesignation] = useState<string>("");

  // Load dropdown options
  const { data: branchOptions } = useBranchOptions();
  const { data: departmentOptions } = useDepartmentOptions();

  // Query parameters for the hook
  const queryParams = useMemo(() => {
    return {
      date_from: searchFromDate,
      date_to: searchToDate,
      branch_id: searchBranchId ? Number(searchBranchId) : undefined,
      department_id: searchDeptId ? Number(searchDeptId) : undefined,
      page: currentPage,
      page_size: pageSize,
      sort_by: sortField,
      sort_dir: sortOrder,
    };
  }, [searchFromDate, searchToDate, searchBranchId, searchDeptId, currentPage, pageSize, sortField, sortOrder]);

  // Fetch live API report data
  const {
    data: reportData,
    isLoading,
    isError,
    error,
    refetch,
  } = useLeaveTakenReport(queryParams);

  const LEAVE_TYPES = useMemo(() => {
    if (reportData?.leave_types && reportData.leave_types.length > 0) {
      return reportData.leave_types.map((alias) => ({
        code: alias,
        label: alias,
      }));
    }
    return [
      { code: "CL", label: "CL" },
      { code: "SL", label: "SL" },
      { code: "EL", label: "EL" },
      { code: "COMP OFF", label: "COMP OFF" },
      { code: "LWP", label: "LWP" },
    ];
  }, [reportData?.leave_types]);

  // Local client-side filters (Quick Search + Column specific filters)
  const processedItems = useMemo(() => {
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
    filterDept,
    filterDesignation,
  ]);

  const totalRecords = reportData?.pagination?.total_records || 0;
  const totalPages = reportData?.pagination?.total_pages || 1;

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setSearchFromDate(fromDate);
    setSearchToDate(toDate);
    setSearchBranchId(branchId);
    setSearchDeptId(deptId);
    setCurrentPage(1);
  };

  const handleReset = () => {
    setFromDate(firstOfMonthStr);
    setToDate(todayStr);
    setBranchId("");
    setDeptId("");
    setSearchFromDate(firstOfMonthStr);
    setSearchToDate(todayStr);
    setSearchBranchId("");
    setSearchDeptId("");
    setSearchTerm("");
    setCurrentPage(1);
    setSortField("employee_code");
    setSortOrder("asc");
    setFilterEmpId("");
    setFilterEmpName("");
    setFilterDept("");
    setFilterDesignation("");
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

  const handleExportExcel = () => {
    if (processedItems.length === 0) {
      toast.error("No data available to export");
      return;
    }

    try {
      const exportData = processedItems.map((row) => {
        const rowObj: Record<string, any> = {
          "Employee ID": row.employee_code,
          "Employee Name": row.employee_name,
          Department: row.department_name,
          Designation: row.designation_name,
        };

        LEAVE_TYPES.forEach((lt) => {
          rowObj[lt.label] = row.leaves[lt.code] || 0;
        });

        rowObj["Total Leaves"] = row.total_leaves;

        return rowObj;
      });

      const worksheet = XLSX.utils.json_to_sheet(exportData);
      const workbook = XLSX.utils.book_new();
      XLSX.utils.book_append_sheet(workbook, worksheet, "Leave Taken Report");
      XLSX.writeFile(workbook, `Leave_Taken_Report_${searchFromDate}_to_${searchToDate}.xlsx`);
      toast.success("Excel report exported successfully");
    } catch {
      toast.error("Failed to export Excel report");
    }
  };

  const handleExportPDF = () => {
    if (processedItems.length === 0) {
      toast.error("No data available to export");
      return;
    }

    try {
      const doc = new jsPDF({ orientation: "landscape" });

      doc.setFontSize(14);
      doc.text("Leave Taken Report", 14, 15);
      doc.setFontSize(9);
      doc.text(`Period: ${searchFromDate} to ${searchToDate}`, 14, 22);

      const headers = [
        "Employee ID",
        "Employee Name",
        "Department",
        "Designation",
        ...LEAVE_TYPES.map((lt) => lt.label),
        "Total",
      ];

      const body = processedItems.map((row) => [
        row.employee_code,
        row.employee_name,
        row.department_name,
        row.designation_name,
        ...LEAVE_TYPES.map((lt) => (row.leaves[lt.code] || 0).toString()),
        row.total_leaves.toString(),
      ]);

      autoTable(doc, {
        head: [headers],
        body: body,
        startY: 28,
        styles: { fontSize: 8 },
      });

      doc.save(`Leave_Taken_Report_${searchFromDate}_to_${searchToDate}.pdf`);
      toast.success("PDF report exported successfully");
    } catch {
      toast.error("Failed to export PDF report");
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Panel */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
              Leave Taken Report
            </h1>
            <span className="px-2 py-0.5 text-[10px] font-semibold bg-sky-50 dark:bg-sky-950/50 text-sky-600 dark:text-sky-400 rounded-full border border-sky-200/50 dark:border-sky-800/30">
              Live
            </span>
          </div>
          <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
            Track and monitor leave usage across departments and employee designations.
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
          {/* Date Picker */}
          <div className="flex items-center bg-slate-50 dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg p-1">
            <CalendarDays className="w-4 h-4 text-slate-400 ml-2" />
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
          <div className="flex items-center bg-slate-50 dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg p-1">
            <select
              aria-label="Choose Branch"
              value={branchId}
              onChange={(e) => setBranchId(e.target.value)}
              className="bg-transparent border-0 text-sm font-medium text-slate-700 dark:text-slate-200 focus:ring-0 focus:outline-none px-2 py-1"
            >
              <option value="" className="bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100">All Branches</option>
              {branchOptions?.map((b) => (
                <option key={b.branch_id} value={b.branch_id} className="bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100">
                  {b.branch_name}
                </option>
              ))}
            </select>
          </div>

          {/* Department Select */}
          <div className="flex items-center bg-slate-50 dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg p-1">
            <select
              aria-label="Choose Department"
              value={deptId}
              onChange={(e) => setDeptId(e.target.value)}
              className="bg-transparent border-0 text-sm font-medium text-slate-700 dark:text-slate-200 focus:ring-0 focus:outline-none px-2 py-1"
            >
              <option value="" className="bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100">All Departments</option>
              {departmentOptions?.map((d) => (
                <option key={d.dept_id} value={d.dept_id} className="bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100">
                  {d.dept_name}
                </option>
              ))}
            </select>
          </div>

          {/* Search Button */}
          <button
            type="submit"
            className="inline-flex items-center gap-2 px-5 py-2 bg-sky-600 hover:bg-sky-700 text-white rounded-lg text-sm font-medium transition-colors shadow-sm"
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

      {/* Main Table Content */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm overflow-hidden">
        {/* Error State */}
        {isError && (
          <div className="p-6 bg-rose-50 dark:bg-rose-900/20 border-b border-rose-200 dark:border-rose-800 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <AlertTriangle className="w-5 h-5 text-rose-600 dark:text-rose-400" />
              <p className="text-sm font-medium text-rose-800 dark:text-rose-200">
                {error instanceof Error ? error.message : "Failed to load leave taken report data."}
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

        {/* Table Wrapper */}
        <div className="overflow-x-auto max-w-full">
          <table className="w-full border-collapse text-left text-xs text-slate-700 dark:text-slate-200">
            <thead>
              <tr className="bg-slate-50/90 dark:bg-slate-900/90 border-b border-slate-200 dark:border-slate-700 font-semibold text-slate-700 dark:text-slate-300">
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
                  label="Department"
                  field="department_name"
                  activeField={sortField}
                  activeDir={sortOrder}
                  onSort={toggleSort}
                  filterValue={filterDept}
                  onFilterChange={setFilterDept}
                  extraClass="min-w-[140px] px-4"
                />
                <HeaderCell
                  label="Designation"
                  field="designation_name"
                  activeField={sortField}
                  activeDir={sortOrder}
                  onSort={toggleSort}
                  filterValue={filterDesignation}
                  onFilterChange={setFilterDesignation}
                  extraClass="min-w-[140px] px-4 border-r border-slate-200 dark:border-slate-700"
                />

                {/* Dynamic Leave Types Columns */}
                {LEAVE_TYPES.map((lt) => (
                  <HeaderCell
                    key={lt.code}
                    label={lt.label}
                    field={lt.code}
                    activeField={sortField}
                    activeDir={sortOrder}
                    onSort={toggleSort}
                    extraClass="min-w-[120px] px-4 border-r border-slate-200 dark:border-slate-700 text-center"
                  />
                ))}

                {/* Total Column */}
                <HeaderCell
                  label="Total"
                  field="total_leaves"
                  activeField={sortField}
                  activeDir={sortOrder}
                  onSort={toggleSort}
                  extraClass="min-w-[100px] px-4 text-center font-bold"
                />
              </tr>
            </thead>

            <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
              {/* Skeleton State */}
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
                    <td className="py-4 px-4 border-r border-slate-200 dark:border-slate-700">
                      <div className="h-4 bg-slate-200 dark:bg-slate-700 rounded w-20" />
                    </td>
                    {LEAVE_TYPES.map((lt) => (
                      <td key={lt.code} className="py-4 px-4 border-r border-slate-100 dark:border-slate-800 text-center">
                        <div className="h-4 bg-slate-200 dark:bg-slate-700 rounded w-8 mx-auto" />
                      </td>
                    ))}
                    <td className="py-4 px-4 text-center">
                      <div className="h-4 bg-slate-200 dark:bg-slate-700 rounded w-8 mx-auto" />
                    </td>
                  </tr>
                ))}

              {/* Success state - Data list */}
              {!isLoading && !isError &&
                processedItems.map((row) => (
                  <tr
                    key={row.employee_id}
                    className="hover:bg-slate-50/80 dark:hover:bg-slate-700/50 transition-colors"
                  >
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

                    {/* Dynamic cells */}
                    {LEAVE_TYPES.map((lt) => {
                      const count = row.leaves[lt.code] || 0;
                      return (
                        <td
                          key={lt.code}
                          className={`py-3 px-4 border-r border-slate-100 dark:border-slate-800 text-center font-medium ${
                            count > 0 ? "text-slate-800 dark:text-slate-200" : "text-slate-400"
                          }`}
                        >
                          {count}
                        </td>
                      );
                    })}

                    {/* Total Cell */}
                    <td className="py-3 px-4 text-center font-bold text-slate-900 dark:text-slate-100">
                      {row.total_leaves}
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>

        {/* Empty state view */}
        {!isLoading && !isError && processedItems.length === 0 && (
          <div className="p-12 text-center">
            <AlertTriangle className="w-12 h-12 text-slate-300 dark:text-slate-600 mx-auto mb-4" />
            <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100 mb-1">
              No leave records found
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              No employees match the applied filter criteria. Try adjusting dates or search query.
            </p>
          </div>
        )}

        {/* Footer controls: pagination */}
        {!isLoading && !isError && processedItems.length > 0 && (
          <div className="flex items-center justify-between px-6 py-4 border-t border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/50">
            <span className="text-xs text-slate-500 dark:text-slate-400">
              Showing <span className="font-semibold text-slate-800 dark:text-slate-200">{(currentPage - 1) * pageSize + 1}</span> to{" "}
              <span className="font-semibold text-slate-800 dark:text-slate-200">
                {Math.min(currentPage * pageSize, totalRecords)}
              </span>{" "}
              of <span className="font-semibold text-slate-800 dark:text-slate-200">{totalRecords}</span> Results
            </span>

            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-500 dark:text-slate-400">Rows per page:</span>
                <select
                  aria-label="Rows per page select"
                  value={pageSize}
                  onChange={(e) => {
                    setPageSize(Number(e.target.value));
                    setCurrentPage(1);
                  }}
                  className="bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-md text-xs px-2 py-1"
                >
                  {[5, 10, 20, 50].map((val) => (
                    <option key={val} value={val}>
                      {val}
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex items-center gap-1.5">
                <button
                  type="button"
                  disabled={currentPage === 1}
                  onClick={() => setCurrentPage((p) => Math.max(p - 1, 1))}
                  className="p-1.5 border border-slate-300 dark:border-slate-700 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-50 disabled:pointer-events-none"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <span className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                  {currentPage} of {totalPages}
                </span>
                <button
                  type="button"
                  disabled={currentPage === totalPages}
                  onClick={() => setCurrentPage((p) => Math.min(p + 1, totalPages))}
                  className="p-1.5 border border-slate-300 dark:border-slate-700 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-50 disabled:pointer-events-none"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
