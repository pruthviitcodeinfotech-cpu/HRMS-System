"use client";

import { useState, useRef, useEffect, useMemo } from "react";
import {
  Calendar,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  FileSpreadsheet,
  FileText,
  Printer,
  ChevronsUpDown,
  ArrowUp,
  ArrowDown,
  RotateCw,
  AlertTriangle,
  FileX,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { useActivityLogs, useExportActivityLogs } from "../hooks/use-activity-logs";
import { ActivityLogItem } from "../types";

type SortableField =
  | "module"
  | "sub_module"
  | "employee_name"
  | "title"
  | "payroll_date"
  | "performed_by_name"
  | "log_date"
  | "log_time";

const MONTH_NAMES = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
];

const FULL_MONTH_NAMES = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December"
];

function formatDateDisplay(d: Date): string {
  const day = String(d.getDate()).padStart(2, "0");
  const month = MONTH_NAMES[d.getMonth()];
  const year = d.getFullYear();
  return `${day} ${month} ${year}`;
}

function toInputDateValue(d: Date): string {
  const day = String(d.getDate()).padStart(2, "0");
  const month = String(d.getMonth() + 1).padStart(2, "0");
  const year = d.getFullYear();
  return `${year}-${month}-${day}`;
}

function parseInputDateValue(str: string): Date | null {
  if (!str) return null;
  const parts = str.split("-");
  if (parts.length !== 3) return null;
  const y = parseInt(parts[0], 10);
  const m = parseInt(parts[1], 10) - 1;
  const d = parseInt(parts[2], 10);
  if (isNaN(y) || isNaN(m) || isNaN(d)) return null;
  return new Date(y, m, d);
}

export function ActivityLogPage() {
  // Dynamic Initial Date Range (First of current month to today)
  const initialRange = useMemo(() => {
    const now = new Date();
    const firstDay = new Date(now.getFullYear(), now.getMonth(), 1);
    return {
      from: firstDay,
      to: now,
      fromStr: formatDateDisplay(firstDay),
      toStr: formatDateDisplay(now),
    };
  }, []);

  // Toolbar & Date Picker States
  const [startDateDisplay, setStartDateDisplay] = useState(initialRange.fromStr);
  const [endDateDisplay, setEndDateDisplay] = useState(initialRange.toStr);
  const [isDatePickerOpen, setIsDatePickerOpen] = useState(false);

  // Calendar Selection States
  const [tempFromDate, setTempFromDate] = useState<Date>(initialRange.from);
  const [tempToDate, setTempToDate] = useState<Date>(initialRange.to);
  const [calMonth, setCalMonth] = useState<number>(initialRange.from.getMonth());
  const [calYear, setCalYear] = useState<number>(initialRange.from.getFullYear());
  const [selectionPhase, setSelectionPhase] = useState<"start" | "end">("start");

  // Date filter applied toggle state
  const [isDateFilterApplied, setIsDateFilterApplied] = useState(false);

  // Search & Actions State
  const [isActionsOpen, setIsActionsOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [appliedSearch, setAppliedSearch] = useState("");

  // Pagination State
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  // Sorting State
  const [sortField, setSortField] = useState<SortableField | null>(null);
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("desc");

  // Refs for click outside handling
  const actionsRef = useRef<HTMLDivElement>(null);
  const datePickerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (actionsRef.current && !actionsRef.current.contains(event.target as Node)) {
        setIsActionsOpen(false);
      }
      if (datePickerRef.current && !datePickerRef.current.contains(event.target as Node)) {
        setIsDatePickerOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // React Query Hooks
  const queryParams = useMemo(() => {
    return {
      page: currentPage,
      page_size: pageSize,
      search: appliedSearch.trim() || undefined,
      date_from: isDateFilterApplied ? toInputDateValue(tempFromDate) : undefined,
      date_to: isDateFilterApplied ? toInputDateValue(tempToDate) : undefined,
      sort_by: sortField ? (sortField === "performed_by_name" ? "logged_at" : sortField) : undefined,
      sort_order: sortDirection,
    };
  }, [currentPage, pageSize, appliedSearch, isDateFilterApplied, tempFromDate, tempToDate, sortField, sortDirection]);

  const { data: apiResponse, isLoading, isError, error, refetch, isFetching } = useActivityLogs(queryParams);
  const exportMutation = useExportActivityLogs();

  // Extract items and pagination from backend API envelope
  const logsItems: ActivityLogItem[] = useMemo(() => {
    return apiResponse?.items || [];
  }, [apiResponse]);

  const totalCount = apiResponse?.pagination?.total_records ?? apiResponse?.pagination?.total ?? logsItems.length;
  const totalPages = apiResponse?.pagination?.total_pages ?? Math.max(1, Math.ceil(totalCount / pageSize));

  // Range Calculations
  const startIndex = totalCount === 0 ? 0 : (currentPage - 1) * pageSize + 1;
  const endIndex = Math.min(currentPage * pageSize, totalCount);

  // Dynamic Page Numbers
  const pageNumbers = useMemo(() => {
    const maxVisiblePages = 5;
    let startPage = Math.max(1, currentPage - 2);
    let endPage = Math.min(totalPages, startPage + maxVisiblePages - 1);

    if (endPage - startPage + 1 < maxVisiblePages) {
      startPage = Math.max(1, endPage - maxVisiblePages + 1);
    }

    const pages: number[] = [];
    for (let p = startPage; p <= endPage; p++) {
      pages.push(p);
    }
    return pages;
  }, [currentPage, totalPages]);

  // Apply Date Range
  const handleApplyDateRange = () => {
    setStartDateDisplay(formatDateDisplay(tempFromDate));
    setEndDateDisplay(formatDateDisplay(tempToDate));
    setIsDateFilterApplied(true);
    setIsDatePickerOpen(false);
    setCurrentPage(1);
  };

  // Calendar Day Click Handler
  const handleDayClick = (dayNum: number) => {
    const clickedDate = new Date(calYear, calMonth, dayNum);
    if (selectionPhase === "start" || clickedDate < tempFromDate) {
      setTempFromDate(clickedDate);
      if (clickedDate > tempToDate) {
        setTempToDate(clickedDate);
      }
      setSelectionPhase("end");
    } else {
      setTempToDate(clickedDate);
      setSelectionPhase("start");
    }
  };

  // Preset Handlers
  const handlePresetSelect = (preset: string) => {
    const now = new Date();
    let from = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    let to = new Date(now.getFullYear(), now.getMonth(), now.getDate());

    if (preset === "today") {
      from = new Date(now.getFullYear(), now.getMonth(), now.getDate());
      to = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    } else if (preset === "yesterday") {
      const y = new Date(now.getFullYear(), now.getMonth(), now.getDate() - 1);
      from = y;
      to = y;
    } else if (preset === "thisMonth") {
      from = new Date(now.getFullYear(), now.getMonth(), 1);
      to = new Date(now.getFullYear(), now.getMonth() + 1, 0);
    } else if (preset === "lastMonth") {
      from = new Date(now.getFullYear(), now.getMonth() - 1, 1);
      to = new Date(now.getFullYear(), now.getMonth(), 0);
    } else if (preset === "last7") {
      from = new Date(now.getFullYear(), now.getMonth(), now.getDate() - 6);
      to = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    }

    setTempFromDate(from);
    setTempToDate(to);
    setCalMonth(from.getMonth());
    setCalYear(from.getFullYear());
    setIsDateFilterApplied(true);
  };

  // Month Navigation
  const handlePrevMonth = () => {
    if (calMonth === 0) {
      setCalMonth(11);
      setCalYear((prev) => prev - 1);
    } else {
      setCalMonth((prev) => prev - 1);
    }
  };

  const handleNextMonth = () => {
    if (calMonth === 11) {
      setCalMonth(0);
      setCalYear((prev) => prev + 1);
    } else {
      setCalMonth((prev) => prev + 1);
    }
  };

  // Handle Sort Toggle
  const handleSort = (field: SortableField) => {
    if (sortField === field) {
      if (sortDirection === "asc") {
        setSortDirection("desc");
      } else {
        setSortField(null);
        setSortDirection("desc");
      }
    } else {
      setSortField(field);
      setSortDirection("asc");
    }
  };

  // Handle Search Click
  const handleSearch = () => {
    setAppliedSearch(searchQuery);
    setCurrentPage(1);
  };

  // Handle Page Size Change
  const handlePageSizeChange = (newSize: number) => {
    setPageSize(newSize);
    setCurrentPage(1);
  };

  // Export handlers
  const handleExport = (type: "excel" | "csv" | "print") => {
    setIsActionsOpen(false);
    exportMutation.mutate({ format: type, params: queryParams });
  };

  // Clear filters
  const handleClearFilters = () => {
    const init = initialRange;
    setSearchQuery("");
    setAppliedSearch("");
    setSortField(null);
    setTempFromDate(init.from);
    setTempToDate(init.to);
    setStartDateDisplay(init.fromStr);
    setEndDateDisplay(init.toStr);
    setCalMonth(init.from.getMonth());
    setCalYear(init.from.getFullYear());
    setIsDateFilterApplied(false);
    setCurrentPage(1);
    refetch();
  };

  // Render Sort Icon Helper
  const renderSortIcon = (field: SortableField) => {
    if (sortField !== field) {
      return <ChevronsUpDown className="h-3.5 w-3.5 text-slate-400 hover:text-slate-600 transition-colors ml-1 inline-block" />;
    }
    return sortDirection === "asc" ? (
      <ArrowUp className="h-3.5 w-3.5 text-blue-600 ml-1 inline-block" />
    ) : (
      <ArrowDown className="h-3.5 w-3.5 text-blue-600 ml-1 inline-block" />
    );
  };

  return (
    <div className="space-y-4 p-4 sm:p-6 bg-slate-50/50 dark:bg-slate-950 min-h-screen">
      {/* PAGE HEADER WITH COUNT */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <h1 className="text-xl font-bold text-slate-800 dark:text-slate-100 tracking-tight">
            Activity Logs
          </h1>
          <span className="text-base font-semibold text-blue-600 dark:text-blue-400">
            {totalCount}
          </span>
        </div>

        {/* Refresh Button */}
        <Button
          type="button"
          variant="outline"
          onClick={() => refetch()}
          disabled={isFetching}
          aria-label="Refresh Data"
          className="bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 text-xs font-semibold px-3 py-1.5 h-8 rounded-md hover:bg-slate-50 dark:hover:bg-slate-800 cursor-pointer shadow-2xs"
        >
          <RotateCw className={`h-3.5 w-3.5 mr-1.5 text-slate-500 ${isFetching ? "animate-spin" : ""}`} />
          <span>Refresh</span>
        </Button>
      </div>

      {/* TOP TOOLBAR */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg p-3 sm:p-4 shadow-2xs flex flex-col md:flex-row md:items-center justify-between gap-3">
        {/* LEFT TOOLBAR: Date Range Picker & Search Button */}
        <div className="flex flex-wrap items-center gap-2.5">
          {/* Date Range Picker */}
          <div className="relative" ref={datePickerRef}>
            <div
              onClick={() => setIsDatePickerOpen(!isDatePickerOpen)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  setIsDatePickerOpen(!isDatePickerOpen);
                }
              }}
              aria-label="Select date range"
              aria-expanded={isDatePickerOpen}
              className="flex items-center space-x-2 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 hover:border-blue-400 rounded-md px-3 py-2 text-xs font-medium text-slate-700 dark:text-slate-200 shadow-2xs cursor-pointer focus:outline-none focus:ring-2 focus:ring-blue-500 transition-colors"
            >
              <span>{startDateDisplay}</span>
              <span className="text-slate-400 font-normal">→</span>
              <span>{endDateDisplay}</span>
              <Calendar className="h-4 w-4 text-slate-500 ml-1.5" />
            </div>

            {/* Date Range Dropdown Popover with Visual Interactive Calendar */}
            {isDatePickerOpen && (
              <div className="absolute left-0 mt-1 w-[320px] sm:w-[350px] bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg shadow-xl z-30 p-3.5 text-xs space-y-3.5 animate-in fade-in zoom-in-95">
                {/* Popover Header */}
                <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-2.5">
                  <span className="font-bold text-slate-800 dark:text-slate-100 text-xs">
                    Select Date Range
                  </span>
                  <button
                    type="button"
                    onClick={() => setIsDatePickerOpen(false)}
                    aria-label="Close date picker"
                    className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 cursor-pointer"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>

                {/* From Date & To Date Input Controls */}
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="block text-[11px] font-semibold text-slate-500 dark:text-slate-400 mb-1">
                      From Date
                    </label>
                    <input
                      type="date"
                      value={toInputDateValue(tempFromDate)}
                      onChange={(e) => {
                        const d = parseInputDateValue(e.target.value);
                        if (d) {
                          setTempFromDate(d);
                          setCalMonth(d.getMonth());
                          setCalYear(d.getFullYear());
                        }
                      }}
                      className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-md px-2 py-1.5 text-xs font-medium text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer"
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] font-semibold text-slate-500 dark:text-slate-400 mb-1">
                      To Date
                    </label>
                    <input
                      type="date"
                      value={toInputDateValue(tempToDate)}
                      onChange={(e) => {
                        const d = parseInputDateValue(e.target.value);
                        if (d) {
                          setTempToDate(d);
                        }
                      }}
                      className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-md px-2 py-1.5 text-xs font-medium text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer"
                    />
                  </div>
                </div>

                {/* Quick Presets Pills */}
                <div className="flex flex-wrap gap-1 pt-0.5">
                  <button
                    type="button"
                    onClick={() => handlePresetSelect("today")}
                    className="px-2 py-1 bg-slate-100 dark:bg-slate-800 hover:bg-blue-50 dark:hover:bg-blue-900/40 hover:text-blue-600 rounded text-[11px] font-medium text-slate-600 dark:text-slate-300 transition-colors cursor-pointer"
                  >
                    Today
                  </button>
                  <button
                    type="button"
                    onClick={() => handlePresetSelect("yesterday")}
                    className="px-2 py-1 bg-slate-100 dark:bg-slate-800 hover:bg-blue-50 dark:hover:bg-blue-900/40 hover:text-blue-600 rounded text-[11px] font-medium text-slate-600 dark:text-slate-300 transition-colors cursor-pointer"
                  >
                    Yesterday
                  </button>
                  <button
                    type="button"
                    onClick={() => handlePresetSelect("thisMonth")}
                    className="px-2 py-1 bg-slate-100 dark:bg-slate-800 hover:bg-blue-50 dark:hover:bg-blue-900/40 hover:text-blue-600 rounded text-[11px] font-medium text-slate-600 dark:text-slate-300 transition-colors cursor-pointer"
                  >
                    This Month
                  </button>
                  <button
                    type="button"
                    onClick={() => handlePresetSelect("lastMonth")}
                    className="px-2 py-1 bg-slate-100 dark:bg-slate-800 hover:bg-blue-50 dark:hover:bg-blue-900/40 hover:text-blue-600 rounded text-[11px] font-medium text-slate-600 dark:text-slate-300 transition-colors cursor-pointer"
                  >
                    Last Month
                  </button>
                  <button
                    type="button"
                    onClick={() => handlePresetSelect("last7")}
                    className="px-2 py-1 bg-slate-100 dark:bg-slate-800 hover:bg-blue-50 dark:hover:bg-blue-900/40 hover:text-blue-600 rounded text-[11px] font-medium text-slate-600 dark:text-slate-300 transition-colors cursor-pointer"
                  >
                    Last 7 Days
                  </button>
                </div>

                {/* VISUAL MONTH CALENDAR GRID */}
                <div className="border border-slate-200 dark:border-slate-800 rounded-md p-2 bg-slate-50/50 dark:bg-slate-800/30">
                  {/* Month Navigation Header */}
                  <div className="flex items-center justify-between px-1 mb-2">
                    <button
                      type="button"
                      onClick={handlePrevMonth}
                      aria-label="Previous month"
                      className="p-1 hover:bg-slate-200 dark:hover:bg-slate-700 rounded text-slate-600 dark:text-slate-300 transition-colors cursor-pointer"
                    >
                      <ChevronLeft className="h-4 w-4" />
                    </button>
                    <span className="font-bold text-slate-800 dark:text-slate-100 text-xs">
                      {FULL_MONTH_NAMES[calMonth]} {calYear}
                    </span>
                    <button
                      type="button"
                      onClick={handleNextMonth}
                      aria-label="Next month"
                      className="p-1 hover:bg-slate-200 dark:hover:bg-slate-700 rounded text-slate-600 dark:text-slate-300 transition-colors cursor-pointer"
                    >
                      <ChevronRight className="h-4 w-4" />
                    </button>
                  </div>

                  {/* Weekday Labels */}
                  <div className="grid grid-cols-7 text-center font-bold text-[10px] text-slate-400 mb-1">
                    <span>Su</span>
                    <span>Mo</span>
                    <span>Tu</span>
                    <span>We</span>
                    <span>Th</span>
                    <span>Fr</span>
                    <span>Sa</span>
                  </div>

                  {/* Calendar Day Grid */}
                  <div className="grid grid-cols-7 text-center gap-y-1 text-xs">
                    {Array.from({ length: new Date(calYear, calMonth, 1).getDay() }).map((_, idx) => (
                      <div key={`empty-${idx}`} />
                    ))}

                    {Array.from({ length: new Date(calYear, calMonth + 1, 0).getDate() }).map((_, idx) => {
                      const dayNum = idx + 1;
                      const currDate = new Date(calYear, calMonth, dayNum);
                      
                      const isStart =
                        tempFromDate &&
                        currDate.getFullYear() === tempFromDate.getFullYear() &&
                        currDate.getMonth() === tempFromDate.getMonth() &&
                        currDate.getDate() === tempFromDate.getDate();

                      const isEnd =
                        tempToDate &&
                        currDate.getFullYear() === tempToDate.getFullYear() &&
                        currDate.getMonth() === tempToDate.getMonth() &&
                        currDate.getDate() === tempToDate.getDate();

                      const isInRange =
                        tempFromDate &&
                        tempToDate &&
                        currDate > tempFromDate &&
                        currDate < tempToDate;

                      let btnStyles = "text-slate-700 dark:text-slate-200 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-md";
                      
                      if (isStart || isEnd) {
                        btnStyles = "bg-blue-600 text-white font-bold rounded-md shadow-2xs";
                      } else if (isInRange) {
                        btnStyles = "bg-blue-100 dark:bg-blue-900/60 text-blue-800 dark:text-blue-200 font-medium rounded-none";
                      }

                      return (
                        <button
                          key={dayNum}
                          type="button"
                          onClick={() => handleDayClick(dayNum)}
                          className={`h-7 w-full flex items-center justify-center transition-colors cursor-pointer text-xs ${btnStyles}`}
                        >
                          {dayNum}
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* Popover Footer Action Buttons */}
                <div className="flex items-center justify-between pt-1 border-t border-slate-100 dark:border-slate-800">
                  <button
                    type="button"
                    onClick={() => {
                      const init = initialRange;
                      setTempFromDate(init.from);
                      setTempToDate(init.to);
                      setCalMonth(init.from.getMonth());
                      setCalYear(init.from.getFullYear());
                    }}
                    className="text-[11px] font-medium text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 underline cursor-pointer"
                  >
                    Reset Dates
                  </button>
                  <Button
                    type="button"
                    onClick={handleApplyDateRange}
                    className="bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs px-4 py-1.5 h-8 rounded-md shadow-2xs cursor-pointer"
                  >
                    Apply Range
                  </Button>
                </div>
              </div>
            )}
          </div>

          {/* Search Input Box */}
          <div className="relative">
            <input
              type="text"
              placeholder="Search logs..."
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setCurrentPage(1);
              }}
              onKeyDown={(e) => {
                if (e.key === "Enter") handleSearch();
              }}
              className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-md px-3 py-2 pr-8 text-xs font-medium text-slate-700 dark:text-slate-200 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 w-44 sm:w-56"
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => {
                  setSearchQuery("");
                  setAppliedSearch("");
                  setCurrentPage(1);
                }}
                aria-label="Clear search"
                className="absolute right-2.5 top-2.5 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 cursor-pointer"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            )}
          </div>

          {/* Blue Search Button */}
          <Button
            type="button"
            onClick={handleSearch}
            aria-label="Execute search"
            className="bg-blue-600 hover:bg-blue-700 text-white font-medium text-xs px-5 py-2 h-9 rounded-md shadow-2xs transition-colors cursor-pointer"
          >
            Search
          </Button>
        </div>

        {/* RIGHT TOOLBAR: Actions Dropdown */}
        <div className="relative" ref={actionsRef}>
          <Button
            type="button"
            onClick={() => setIsActionsOpen(!isActionsOpen)}
            aria-label="Actions menu"
            aria-expanded={isActionsOpen}
            className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-200 text-xs font-semibold px-4 py-2 h-9 rounded-md flex items-center space-x-1.5 shadow-2xs transition-colors cursor-pointer"
          >
            <span>Actions</span>
            <ChevronDown className="h-4 w-4 text-slate-500" />
          </Button>

          {/* Dropdown Menu Items */}
          {isActionsOpen && (
            <div className="absolute right-0 mt-1 w-44 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-md shadow-lg z-30 py-1 text-xs animate-in fade-in zoom-in-95">
              <button
                type="button"
                onClick={() => handleExport("excel")}
                className="w-full text-left px-4 py-2 hover:bg-slate-50 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-200 flex items-center space-x-2 transition-colors cursor-pointer"
              >
                <FileSpreadsheet className="h-4 w-4 text-emerald-600" />
                <span>Export Excel</span>
              </button>
              <button
                type="button"
                onClick={() => handleExport("csv")}
                className="w-full text-left px-4 py-2 hover:bg-slate-50 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-200 flex items-center space-x-2 transition-colors cursor-pointer"
              >
                <FileText className="h-4 w-4 text-blue-600" />
                <span>Export CSV</span>
              </button>
              <button
                type="button"
                onClick={() => handleExport("print")}
                className="w-full text-left px-4 py-2 hover:bg-slate-50 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-200 flex items-center space-x-2 transition-colors cursor-pointer"
              >
                <Printer className="h-4 w-4 text-slate-600" />
                <span>Print</span>
              </button>
            </div>
          )}
        </div>
      </div>

      {/* ERROR STATE VIEW */}
      {isError && (
        <div className="p-8 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg shadow-2xs flex flex-col items-center justify-center text-center space-y-4 my-4 py-16">
          <div className="p-3.5 bg-red-50 dark:bg-red-950/50 rounded-full text-red-600 dark:text-red-400 border border-red-100 dark:border-red-900">
            <AlertTriangle className="h-8 w-8" />
          </div>
          <div className="space-y-1">
            <h3 className="text-base font-bold text-slate-800 dark:text-slate-100">
              Unable to load activity logs
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 max-w-sm">
              {(error as any)?.message || "An unexpected error occurred while loading activity logs."}
            </p>
          </div>
          <Button
            type="button"
            onClick={() => refetch()}
            className="bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold px-5 py-2 h-9 rounded-md shadow-2xs transition-colors cursor-pointer"
          >
            Retry
          </Button>
        </div>
      )}

      {/* SKELETON LOADING STATE VIEW */}
      {isLoading && (
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg shadow-2xs overflow-hidden">
          <div className="w-full overflow-x-auto">
            <table className="w-full text-left border-collapse min-w-[1200px]">
              <thead>
                <tr className="bg-[#eef6ff] dark:bg-slate-800/80 border-b border-slate-200 dark:border-slate-700">
                  {Array.from({ length: 11 }).map((_, idx) => (
                    <th key={idx} className="py-3.5 px-3.5">
                      <div className="h-4 bg-slate-200 dark:bg-slate-700 rounded w-20 animate-pulse" />
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {Array.from({ length: 8 }).map((_, rowIdx) => (
                  <tr key={rowIdx} className="animate-pulse">
                    <td className="py-3.5 px-3.5"><div className="h-4 bg-slate-200 dark:bg-slate-800 rounded w-24" /></td>
                    <td className="py-3.5 px-3.5"><div className="h-4 bg-slate-200 dark:bg-slate-800 rounded w-28" /></td>
                    <td className="py-3.5 px-3.5"><div className="h-4 bg-slate-200 dark:bg-slate-800 rounded w-20" /></td>
                    <td className="py-3.5 px-3.5"><div className="h-4 bg-slate-200 dark:bg-slate-800 rounded w-36" /></td>
                    <td className="py-3.5 px-3.5"><div className="h-4 bg-slate-200 dark:bg-slate-800 rounded w-48" /></td>
                    <td className="py-3.5 px-3.5"><div className="h-4 bg-slate-200 dark:bg-slate-800 rounded w-20" /></td>
                    <td className="py-3.5 px-3.5"><div className="h-4 bg-slate-200 dark:bg-slate-800 rounded w-16" /></td>
                    <td className="py-3.5 px-3.5"><div className="h-4 bg-slate-200 dark:bg-slate-800 rounded w-16" /></td>
                    <td className="py-3.5 px-3.5"><div className="h-4 bg-slate-200 dark:bg-slate-800 rounded w-20" /></td>
                    <td className="py-3.5 px-3.5"><div className="h-4 bg-slate-200 dark:bg-slate-800 rounded w-16" /></td>
                    <td className="py-3.5 px-3.5"><div className="h-4 bg-slate-200 dark:bg-slate-800 rounded w-16" /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* EMPTY STATE VIEW */}
      {!isLoading && !isError && logsItems.length === 0 && (
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg shadow-2xs p-12 text-center flex flex-col items-center justify-center space-y-4 my-4 py-16">
          <div className="p-3.5 bg-blue-50 dark:bg-blue-950/40 rounded-full text-blue-600 dark:text-blue-400 border border-blue-100 dark:border-blue-900">
            <FileX className="h-8 w-8" />
          </div>
          <div className="space-y-1">
            <h3 className="text-base font-bold text-slate-800 dark:text-slate-100">
              No Activity Logs Found
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 max-w-sm">
              {appliedSearch
                ? `No activity log records matching "${appliedSearch}" were found.`
                : "No matching activity log records were found for the selected date range or search filters."}
            </p>
          </div>
          <Button
            type="button"
            onClick={handleClearFilters}
            className="bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold px-5 py-2 h-9 rounded-md shadow-2xs transition-colors cursor-pointer"
          >
            Clear Filters
          </Button>
        </div>
      )}

      {/* NORMAL STATE: TABLE & PAGINATION */}
      {!isLoading && !isError && logsItems.length > 0 && (
        <>
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg shadow-2xs overflow-hidden">
            <div className="w-full overflow-x-auto max-h-[650px] overflow-y-auto">
              <table className="w-full text-left border-collapse text-xs min-w-[1200px]" role="table">
                {/* STICKY TABLE HEADER */}
                <thead className="sticky top-0 z-10 bg-[#eef6ff] dark:bg-slate-800 text-slate-700 dark:text-slate-200 font-semibold border-b border-slate-200 dark:border-slate-700 shadow-2xs">
                  <tr>
                    {/* 1. Module (Sort icon) */}
                    <th
                      scope="col"
                      onClick={() => handleSort("module")}
                      className="py-3 px-3.5 font-semibold text-slate-700 dark:text-slate-200 whitespace-nowrap cursor-pointer hover:bg-blue-100/50 dark:hover:bg-slate-700/50 transition-colors select-none"
                    >
                      <div className="flex items-center">
                        <span>Module</span>
                        {renderSortIcon("module")}
                      </div>
                    </th>

                    {/* 2. Sub Module (Sort icon) */}
                    <th
                      scope="col"
                      onClick={() => handleSort("sub_module")}
                      className="py-3 px-3.5 font-semibold text-slate-700 dark:text-slate-200 whitespace-nowrap cursor-pointer hover:bg-blue-100/50 dark:hover:bg-slate-700/50 transition-colors select-none"
                    >
                      <div className="flex items-center">
                        <span>Sub Module</span>
                        {renderSortIcon("sub_module")}
                      </div>
                    </th>

                    {/* 3. Employee Name (Sort icon) */}
                    <th
                      scope="col"
                      onClick={() => handleSort("employee_name")}
                      className="py-3 px-3.5 font-semibold text-slate-700 dark:text-slate-200 whitespace-nowrap cursor-pointer hover:bg-blue-100/50 dark:hover:bg-slate-700/50 transition-colors select-none"
                    >
                      <div className="flex items-center">
                        <span>Employee Name</span>
                        {renderSortIcon("employee_name")}
                      </div>
                    </th>

                    {/* 4. Title (Sort icon) */}
                    <th
                      scope="col"
                      onClick={() => handleSort("title")}
                      className="py-3 px-3.5 font-semibold text-slate-700 dark:text-slate-200 whitespace-nowrap cursor-pointer hover:bg-blue-100/50 dark:hover:bg-slate-700/50 transition-colors select-none"
                    >
                      <div className="flex items-center">
                        <span>Title</span>
                        {renderSortIcon("title")}
                      </div>
                    </th>

                    {/* 5. Description */}
                    <th
                      scope="col"
                      className="py-3 px-3.5 font-semibold text-slate-700 dark:text-slate-200 whitespace-nowrap"
                    >
                      <span>Description</span>
                    </th>

                    {/* 6. Payroll Date (Sort icon) */}
                    <th
                      scope="col"
                      onClick={() => handleSort("payroll_date")}
                      className="py-3 px-3.5 font-semibold text-slate-700 dark:text-slate-200 whitespace-nowrap cursor-pointer hover:bg-blue-100/50 dark:hover:bg-slate-700/50 transition-colors select-none"
                    >
                      <div className="flex items-center">
                        <span>Payroll Date</span>
                        {renderSortIcon("payroll_date")}
                      </div>
                    </th>

                    {/* 7. Action */}
                    <th
                      scope="col"
                      className="py-3 px-3.5 font-semibold text-slate-700 dark:text-slate-200 whitespace-nowrap"
                    >
                      <span>Action</span>
                    </th>

                    {/* 8. Action By (Sort icon) */}
                    <th
                      scope="col"
                      onClick={() => handleSort("performed_by_name")}
                      className="py-3 px-3.5 font-semibold text-slate-700 dark:text-slate-200 whitespace-nowrap cursor-pointer hover:bg-blue-100/50 dark:hover:bg-slate-700/50 transition-colors select-none"
                    >
                      <div className="flex items-center">
                        <span>Action By</span>
                        {renderSortIcon("performed_by_name")}
                      </div>
                    </th>

                    {/* 9. Log Date (Sort icon) */}
                    <th
                      scope="col"
                      onClick={() => handleSort("log_date")}
                      className="py-3 px-3.5 font-semibold text-slate-700 dark:text-slate-200 whitespace-nowrap cursor-pointer hover:bg-blue-100/50 dark:hover:bg-slate-700/50 transition-colors select-none"
                    >
                      <div className="flex items-center">
                        <span>Log Date</span>
                        {renderSortIcon("log_date")}
                      </div>
                    </th>

                    {/* 10. Log Time (Sort icon) */}
                    <th
                      scope="col"
                      onClick={() => handleSort("log_time")}
                      className="py-3 px-3.5 font-semibold text-slate-700 dark:text-slate-200 whitespace-nowrap cursor-pointer hover:bg-blue-100/50 dark:hover:bg-slate-700/50 transition-colors select-none"
                    >
                      <div className="flex items-center">
                        <span>Log Time</span>
                        {renderSortIcon("log_time")}
                      </div>
                    </th>

                    {/* 11. Action From */}
                    <th
                      scope="col"
                      className="py-3 px-3.5 font-semibold text-slate-700 dark:text-slate-200 whitespace-nowrap"
                    >
                      <span>Action From</span>
                    </th>
                  </tr>
                </thead>

                {/* TABLE BODY WITH HOVER ROWS */}
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800 bg-white dark:bg-slate-900">
                  {logsItems.map((log) => (
                    <tr
                      key={log.id}
                      className="hover:bg-slate-50/80 dark:hover:bg-slate-800/60 transition-colors text-slate-700 dark:text-slate-300"
                    >
                      {/* Module */}
                      <td className="py-3 px-3.5 whitespace-nowrap font-normal">
                        {log.module}
                      </td>

                      {/* Sub Module */}
                      <td className="py-3 px-3.5 whitespace-nowrap font-normal">
                        {log.sub_module || "-"}
                      </td>

                      {/* Employee Name */}
                      <td className="py-3 px-3.5 whitespace-nowrap font-normal">
                        {log.employee_name || "-"}
                      </td>

                      {/* Title */}
                      <td className="py-3 px-3.5 whitespace-nowrap font-normal">
                        {log.title}
                      </td>

                      {/* Description (Truncated Ellipsis) */}
                      <td className="py-3 px-3.5 font-normal max-w-[260px]">
                        <span
                          className="block truncate text-slate-600 dark:text-slate-400"
                          title={log.description || ""}
                        >
                          {log.description || "-"}
                        </span>
                      </td>

                      {/* Payroll Date */}
                      <td className="py-3 px-3.5 whitespace-nowrap font-normal">
                        {log.payroll_date || "-"}
                      </td>

                      {/* Action */}
                      <td className="py-3 px-3.5 whitespace-nowrap font-normal">
                        {log.action_type}
                      </td>

                      {/* Action By */}
                      <td className="py-3 px-3.5 whitespace-nowrap font-normal">
                        {log.performed_by_name}
                      </td>

                      {/* Log Date */}
                      <td className="py-3 px-3.5 whitespace-nowrap font-normal">
                        {log.log_date}
                      </td>

                      {/* Log Time */}
                      <td className="py-3 px-3.5 whitespace-nowrap font-normal">
                        {log.log_time}
                      </td>

                      {/* Action From */}
                      <td className="py-3 px-3.5 whitespace-nowrap font-normal">
                        {log.action_from}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* BOTTOM PAGINATION TOOLBAR */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-2 px-1 text-xs text-slate-600 dark:text-slate-400">
            {/* Left: Display Count */}
            <div>
              <span>Showing {startIndex} to {endIndex} of {totalCount} Results</span>
            </div>

            {/* Right: Page Size Dropdown & Pagination Controls */}
            <div className="flex items-center space-x-2 sm:space-x-3">
              {/* Page Size Dropdown */}
              <div className="relative">
                <select
                  value={pageSize}
                  onChange={(e) => handlePageSizeChange(Number(e.target.value))}
                  aria-label="Select items per page"
                  className="appearance-none bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-md px-3 py-1.5 pr-7 text-xs font-medium text-slate-700 dark:text-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer shadow-2xs"
                >
                  <option value={10}>10 / Page</option>
                  <option value={25}>25 / Page</option>
                  <option value={50}>50 / Page</option>
                  <option value={100}>100 / Page</option>
                </select>
                <ChevronDown className="h-3.5 w-3.5 text-slate-500 absolute right-2 top-2.5 pointer-events-none" />
              </div>

              {/* Previous Button */}
              <Button
                type="button"
                variant="outline"
                disabled={currentPage === 1}
                onClick={() => setCurrentPage((prev) => Math.max(prev - 1, 1))}
                aria-label="Previous page"
                className="bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 text-xs px-3 py-1.5 h-8 rounded-md hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-50 cursor-pointer"
              >
                Previous
              </Button>

              {/* Page Number Buttons */}
              <div className="flex items-center space-x-1">
                {pageNumbers.map((pageNum) => (
                  <button
                    key={pageNum}
                    type="button"
                    onClick={() => setCurrentPage(pageNum)}
                    aria-label={`Go to page ${pageNum}`}
                    className={`h-8 w-8 rounded-md text-xs font-medium transition-all ${
                      currentPage === pageNum
                        ? "bg-blue-600 text-white font-semibold shadow-2xs"
                        : "bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 border border-slate-200 dark:border-slate-700"
                    }`}
                  >
                    {pageNum}
                  </button>
                ))}
              </div>

              {/* Next Button */}
              <Button
                type="button"
                variant="outline"
                disabled={currentPage >= totalPages}
                onClick={() => setCurrentPage((prev) => Math.min(prev + 1, totalPages))}
                aria-label="Next page"
                className="bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-700 text-blue-600 dark:text-blue-400 font-medium text-xs px-3 py-1.5 h-8 rounded-md hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-50 cursor-pointer"
              >
                Next
              </Button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
