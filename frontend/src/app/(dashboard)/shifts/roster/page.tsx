"use client";

import { useState, useMemo, useRef, useEffect } from "react";
import {
  Calendar as CalendarIcon,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  Download,
  Maximize2,
  Minimize2,
  Save,
  Search,
  SlidersHorizontal,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { toast } from "sonner";
import { ProtectedRoute } from "@/features/auth";
import {
  useEmployees,
  useBranchOptions,
  useDebouncedValue,
} from "@/features/employees";
import {
  useShifts,
  useRoster,
  useUpsertRosterEntry,
  useBulkSetRoster,
  useUpdateRosterEntry,
  RosterBulkEntry,
} from "@/features/shifts";

interface DateHeader {
  dateStr: string;
  dateLabel: string;
  dayLabel: string;
}

interface CellValue {
  shift_id: number | null;
  is_week_off: boolean;
  roster_id?: number;
}

const MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const DAY_NAMES_SHORT = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"];

function formatDisplayDate(d: Date): string {
  const day = d.getDate();
  const monthStr = MONTH_NAMES[d.getMonth()];
  const year = d.getFullYear();
  return `${day} ${monthStr} ${year}`;
}

function formatDateISO(d: Date): string {
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd}`;
}

export default function RosterSpreadsheetPage() {
  // Calendar range picker states
  const [pickerStart, setPickerStart] = useState<Date>(new Date(2026, 6, 22)); // July 22, 2026
  const [pickerEnd, setPickerEnd] = useState<Date | null>(new Date(2026, 6, 29)); // July 29, 2026
  const [isDatePickerOpen, setIsDatePickerOpen] = useState<boolean>(false);
  const [viewYear, setViewYear] = useState<number>(2026);
  const [viewMonth, setViewMonth] = useState<number>(6); // 6 = July (0-indexed)

  const datePickerRef = useRef<HTMLDivElement>(null);

  // Close calendar popover on click outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (datePickerRef.current && !datePickerRef.current.contains(event.target as Node)) {
        setIsDatePickerOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Compute dynamic table dates list
  const dynamicDates = useMemo(() => {
    if (!pickerStart || !pickerEnd) return [];
    const result: DateHeader[] = [];
    const curr = new Date(pickerStart);
    const end = new Date(pickerEnd);

    const fullDayNames = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

    while (curr <= end) {
      const dateStr = formatDateISO(curr);
      const dateLabel = `${curr.getDate()}-${MONTH_NAMES[curr.getMonth()]}`;
      const dayLabel = fullDayNames[curr.getDay()];

      result.push({ dateStr, dateLabel, dayLabel });
      curr.setDate(curr.getDate() + 1);
      if (result.length >= 31) break; // max 31 days horizon
    }
    return result;
  }, [pickerStart, pickerEnd]);

  // Branch filter state
  const [selectedBranchId, setSelectedBranchId] = useState<number | undefined>(undefined);
  const { data: branchOptions = [] } = useBranchOptions();

  // Search input state & 400ms debouncing
  const [searchInput, setSearchInput] = useState<string>("");
  const debouncedSearch = useDebouncedValue(searchInput, 400);

  // Pagination state
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(10);

  // Fullscreen state
  const [isFullscreen, setIsFullscreen] = useState<boolean>(false);

  // Live Backend Shifts options (GET /shifts)
  const { data: backendShiftsData } = useShifts({ page_size: 100 });

  const shiftOptions = useMemo(() => {
    const list: {
      id: number | null;
      value: string;
      label: string;
      bgClass: string;
      textClass: string;
      isWeekOff: boolean;
    }[] = [
      {
        id: null,
        value: "Week Off",
        label: "Week Off",
        bgClass: "bg-[#FEE2E2] dark:bg-red-950/40",
        textClass: "text-[#991B1B] dark:text-red-300",
        isWeekOff: true,
      },
    ];

    if (backendShiftsData?.items && backendShiftsData.items.length > 0) {
      backendShiftsData.items.forEach((s) => {
        list.push({
          id: s.shift_id,
          value: String(s.shift_id),
          label: s.shift_name,
          bgClass: s.shift_color ? `bg-[${s.shift_color}]/10` : "bg-[#E0F7FA] dark:bg-cyan-950/40",
          textClass: s.shift_color ? `text-[${s.shift_color}]` : "text-[#00796B] dark:text-cyan-300",
          isWeekOff: false,
        });
      });
    } else {
      list.push(
        { id: 1, value: "1", label: "Daily", bgClass: "bg-[#E0F7FA] dark:bg-cyan-950/40", textClass: "text-[#00796B] dark:text-cyan-300", isWeekOff: false },
        { id: 2, value: "2", label: "Night Shift", bgClass: "bg-[#F3E8FF] dark:bg-purple-950/40", textClass: "text-[#6B21A8] dark:text-purple-300", isWeekOff: false },
        { id: 3, value: "3", label: "Open Shift", bgClass: "bg-[#FEF3C7] dark:bg-amber-950/40", textClass: "text-[#92400E] dark:text-amber-300", isWeekOff: false },
        { id: 4, value: "4", label: "Morning Shift", bgClass: "bg-[#E0F2FE] dark:bg-sky-950/40", textClass: "text-[#075985] dark:text-sky-300", isWeekOff: false }
      );
    }

    return list;
  }, [backendShiftsData]);

  // Live Backend Employees Query (GET /employees)
  const { data: employeesData, isLoading: isEmployeesLoading } = useEmployees({
    page: currentPage,
    page_size: pageSize,
    q: debouncedSearch,
    branch_id: selectedBranchId,
    status: "active",
  });

  const employees = useMemo(() => {
    if (!employeesData?.items) return [];
    return employeesData.items.map((emp) => ({
      id: emp.employee_id,
      code: emp.employee_code || String(emp.employee_id),
      name: emp.employee_name,
      department: emp.department_name || "-",
      designation: emp.designation_name || "-",
      branch: emp.branch_name || "-",
    }));
  }, [employeesData]);

  const totalRecords = employeesData?.pagination?.total_records ?? employees.length;
  const totalPages = employeesData?.pagination?.total_pages ?? Math.max(1, Math.ceil(totalRecords / pageSize));

  // Date range formatted for backend queries
  const dateFromStr = useMemo(() => (pickerStart ? formatDateISO(pickerStart) : undefined), [pickerStart]);
  const dateToStr = useMemo(() => (pickerEnd ? formatDateISO(pickerEnd) : undefined), [pickerEnd]);

  // Live Backend Roster Query (GET /roster)
  const { data: rosterData, isLoading: isRosterLoading } = useRoster({
    date_from: dateFromStr,
    date_to: dateToStr,
    branch_id: selectedBranchId,
    page: currentPage,
    page_size: pageSize,
  });

  // Local grid cell overrides: map `${employee_id}_${dateStr}` -> CellValue
  const [localCellMap, setLocalCellMap] = useState<Record<string, CellValue>>({});
  // Track modified entries for Save (POST /roster/bulk)
  const [modifiedCells, setModifiedCells] = useState<Record<string, RosterBulkEntry>>({});

  // Combine server-fetched roster entries with local user modifications
  const effectiveCellMap = useMemo(() => {
    const map: Record<string, CellValue> = {};
    if (rosterData?.items) {
      rosterData.items.forEach((item) => {
        const key = `${item.employee_id}_${item.roster_date}`;
        map[key] = {
          shift_id: item.shift_id,
          is_week_off: item.is_week_off,
          roster_id: item.roster_id,
        };
      });
    }
    Object.entries(localCellMap).forEach(([k, v]) => {
      map[k] = v;
    });
    return map;
  }, [rosterData, localCellMap]);

  // React Query Mutations
  const upsertMutation = useUpsertRosterEntry();
  const updateMutation = useUpdateRosterEntry();
  const bulkSetMutation = useBulkSetRoster();

  // Single cell shift change handler (PATCH or PUT)
  const handleShiftChange = (empId: number, dateStr: string, optValue: string) => {
    const selectedOpt = shiftOptions.find((opt) => opt.value === optValue) || shiftOptions[0];
    const key = `${empId}_${dateStr}`;

    const newCell: CellValue = {
      shift_id: selectedOpt.isWeekOff ? null : selectedOpt.id,
      is_week_off: selectedOpt.isWeekOff,
    };

    setLocalCellMap((prev) => ({
      ...prev,
      [key]: newCell,
    }));

    // Record modified entry for Save button
    setModifiedCells((prev) => ({
      ...prev,
      [key]: {
        employee_id: empId,
        roster_date: dateStr,
        shift_id: newCell.shift_id,
        is_week_off: newCell.is_week_off,
      },
    }));

    // Perform live backend sync
    const existing = effectiveCellMap[key];
    if (existing?.roster_id) {
      updateMutation.mutate(
        {
          rosterId: existing.roster_id,
          data: {
            shift_id: newCell.shift_id,
            is_week_off: newCell.is_week_off,
          },
        },
        {
          onSuccess: (updated) => {
            setLocalCellMap((prev) => ({
              ...prev,
              [key]: {
                shift_id: updated.shift_id,
                is_week_off: updated.is_week_off,
                roster_id: updated.roster_id,
              },
            }));
            toast.success(`Updated shift assignment for ${dateStr}.`);
          },
          onError: (err: unknown) => {
            const msg = (err as { message?: string })?.message || "Failed to update roster entry.";
            toast.error(msg);
          },
        }
      );
    } else {
      upsertMutation.mutate(
        {
          employee_id: empId,
          roster_date: dateStr,
          shift_id: newCell.shift_id,
          is_week_off: newCell.is_week_off,
        },
        {
          onSuccess: (result) => {
            setLocalCellMap((prev) => ({
              ...prev,
              [key]: {
                shift_id: result.entry.shift_id,
                is_week_off: result.entry.is_week_off,
                roster_id: result.entry.roster_id,
              },
            }));
            toast.success(`Saved roster assignment for ${dateStr}.`);
          },
          onError: (err: unknown) => {
            const msg = (err as { message?: string })?.message || "Failed to save roster entry.";
            toast.error(msg);
          },
        }
      );
    }
  };

  // Bulk Save handler (POST /roster/bulk)
  const handleSave = () => {
    const entries = Object.values(modifiedCells);
    if (entries.length === 0) {
      toast.info("No modified roster cells to save.");
      return;
    }

    bulkSetMutation.mutate(
      { entries },
      {
        onSuccess: (res) => {
          setModifiedCells({});
          toast.success(
            `Bulk save complete: ${res.created_count} created, ${res.updated_count} updated, ${res.skipped_count} skipped.`
          );
        },
        onError: (err: unknown) => {
          const msg = (err as { message?: string })?.message || "Failed to execute bulk save.";
          toast.error(msg);
        },
      }
    );
  };

  // Export Excel / CSV handler
  const handleExportExcel = () => {
    try {
      const headers = [
        "Employee Code",
        "Employee Name",
        "Department",
        "Designation",
        ...dynamicDates.map((d) => `"${d.dateLabel} (${d.dayLabel})"`),
      ];

      const rows = employees.map((emp) => {
        const rowCells = [
          `"${emp.code}"`,
          `"${emp.name.replace(/"/g, '""')}"`,
          `"${emp.department.replace(/"/g, '""')}"`,
          `"${emp.designation.replace(/"/g, '""')}"`,
          ...dynamicDates.map((d) => {
            const cellKey = `${emp.id}_${d.dateStr}`;
            const cell = effectiveCellMap[cellKey];
            if (!cell || cell.is_week_off) return '"Week Off"';
            const opt = shiftOptions.find((o) => o.id === cell.shift_id);
            return `"${opt ? opt.label : "Daily"}"`;
          }),
        ];
        return rowCells.join(",");
      });

      const csvContent = [headers.join(","), ...rows].join("\n");
      const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");

      const startDateLabel = pickerStart ? formatDateISO(pickerStart) : "schedule";
      const endDateLabel = pickerEnd ? formatDateISO(pickerEnd) : "";

      link.setAttribute("href", url);
      link.setAttribute("download", `Roster_Spreadsheet_${startDateLabel}_to_${endDateLabel}.csv`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);

      toast.success("Roster spreadsheet exported to Excel (CSV) successfully.");
    } catch (err) {
      console.error("Export error:", err);
      toast.error("Failed to export Roster Spreadsheet.");
    }
  };

  // Track range selection state in popover
  const [isSelectingStart, setIsSelectingStart] = useState<boolean>(true);

  // Date selection logic in calendar popover
  const handleCalendarDayClick = (year: number, month: number, day: number) => {
    const clickedDate = new Date(year, month, day);

    if (isSelectingStart) {
      setPickerStart(clickedDate);
      setPickerEnd(null);
      setIsSelectingStart(false);
    } else {
      if (pickerStart && clickedDate < pickerStart) {
        setPickerEnd(pickerStart);
        setPickerStart(clickedDate);
      } else {
        setPickerEnd(clickedDate);
      }
      setIsSelectingStart(true);
      setIsDatePickerOpen(false);
    }
  };

  // Month navigation helpers
  const handlePrevYear = () => setViewYear((prev) => prev - 1);
  const handleNextYear = () => setViewYear((prev) => prev + 1);
  const handlePrevMonth = () => {
    if (viewMonth === 0) {
      setViewMonth(11);
      setViewYear((prev) => prev - 1);
    } else {
      setViewMonth((prev) => prev - 1);
    }
  };
  const handleNextMonth = () => {
    if (viewMonth === 11) {
      setViewMonth(0);
      setViewYear((prev) => prev + 1);
    } else {
      setViewMonth((prev) => prev + 1);
    }
  };

  // Build calendar matrix for a month
  const renderCalendarMonth = (year: number, month: number, isRightMonth: boolean) => {
    const firstDayIndex = new Date(year, month, 1).getDay(); // 0=Sun
    const totalDays = new Date(year, month + 1, 0).getDate();
    const monthLabel = MONTH_NAMES[month];

    const startTime = pickerStart
      ? new Date(pickerStart.getFullYear(), pickerStart.getMonth(), pickerStart.getDate()).getTime()
      : null;
    const endTime = pickerEnd
      ? new Date(pickerEnd.getFullYear(), pickerEnd.getMonth(), pickerEnd.getDate()).getTime()
      : null;

    const cells = [];
    for (let i = 0; i < firstDayIndex; i++) {
      cells.push(<div key={`blank-${i}`} className="h-7 w-7" />);
    }

    for (let day = 1; day <= totalDays; day++) {
      const curTime = new Date(year, month, day).getTime();

      const isStart = startTime !== null && curTime === startTime;
      const isEnd = endTime !== null && curTime === endTime;
      const isInRange = startTime !== null && endTime !== null && curTime > startTime && curTime < endTime;

      const isToday =
        year === 2026 &&
        month === 6 &&
        day === 20;

      let cellStyle = "hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300 rounded-md";

      if (isStart || isEnd) {
        cellStyle = "bg-[#0B85C9] text-white font-bold rounded-md shadow-2xs";
      } else if (isInRange) {
        cellStyle = "bg-[#E0F2FE] text-slate-800 font-semibold rounded-none";
      } else if (isToday) {
        cellStyle += " border border-slate-400 font-semibold";
      }

      cells.push(
        <button
          key={`day-${day}`}
          type="button"
          onClick={() => handleCalendarDayClick(year, month, day)}
          className={`h-7 w-7 flex items-center justify-center text-xs transition-colors cursor-pointer ${cellStyle}`}
        >
          {day}
        </button>
      );
    }

    return (
      <div className="space-y-2">
        <div className="flex items-center justify-between h-7 px-1">
          {!isRightMonth ? (
            <>
              <div className="flex items-center space-x-1">
                <button
                  type="button"
                  onClick={handlePrevYear}
                  className="p-1 hover:bg-slate-100 dark:hover:bg-slate-800 rounded text-slate-400 hover:text-slate-700 cursor-pointer"
                  title="Previous Year"
                >
                  <ChevronsLeft className="h-3.5 w-3.5" />
                </button>
                <button
                  type="button"
                  onClick={handlePrevMonth}
                  className="p-1 hover:bg-slate-100 dark:hover:bg-slate-800 rounded text-slate-400 hover:text-slate-700 cursor-pointer"
                  title="Previous Month"
                >
                  <ChevronLeft className="h-3.5 w-3.5" />
                </button>
              </div>
              <div className="text-xs font-bold text-slate-800 dark:text-slate-100">
                {monthLabel} {year}
              </div>
              <div className="w-10" />
            </>
          ) : (
            <>
              <div className="w-10" />
              <div className="text-xs font-bold text-slate-800 dark:text-slate-100">
                {monthLabel} {year}
              </div>
              <div className="flex items-center space-x-1">
                <button
                  type="button"
                  onClick={handleNextMonth}
                  className="p-1 hover:bg-slate-100 dark:hover:bg-slate-800 rounded text-slate-400 hover:text-slate-700 cursor-pointer"
                  title="Next Month"
                >
                  <ChevronRight className="h-3.5 w-3.5" />
                </button>
                <button
                  type="button"
                  onClick={handleNextYear}
                  className="p-1 hover:bg-slate-100 dark:hover:bg-slate-800 rounded text-slate-400 hover:text-slate-700 cursor-pointer"
                  title="Next Year"
                >
                  <ChevronsRight className="h-3.5 w-3.5" />
                </button>
              </div>
            </>
          )}
        </div>

        <div className="grid grid-cols-7 gap-1 text-center">
          {DAY_NAMES_SHORT.map((d) => (
            <div key={d} className="text-[11px] font-semibold text-slate-400 py-1">
              {d}
            </div>
          ))}
          {cells}
        </div>
      </div>
    );
  };

  const month2Year = viewMonth === 11 ? viewYear + 1 : viewYear;
  const month2Month = viewMonth === 11 ? 0 : viewMonth + 1;

  const isLoading = isEmployeesLoading || isRosterLoading;

  return (
    <ProtectedRoute requiredPermission={{ feature: "shift", action: "read" }}>
      <div
        className={`bg-[#F4F6F9] dark:bg-slate-950 font-sans min-h-screen text-slate-800 dark:text-slate-100 ${
          isFullscreen ? "fixed inset-0 z-[200] overflow-auto p-4 bg-white dark:bg-slate-950" : "p-6 space-y-4"
        }`}
      >
        {/* Page Title */}
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-bold text-slate-800 dark:text-slate-100">
            Roster Spreadsheet
          </h1>
          {isFullscreen && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsFullscreen(false)}
              className="text-xs bg-white dark:bg-slate-900 border-slate-300"
            >
              <Minimize2 className="h-3.5 w-3.5 mr-1" />
              Exit Fullscreen
            </Button>
          )}
        </div>

        {/* Filter Bar Card */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg p-3.5 shadow-2xs flex flex-wrap items-center justify-between gap-3 relative z-30">
          {/* Left Controls: Date Picker, Branch, Search Button */}
          <div className="flex flex-wrap items-center gap-3">
            {/* Date Range Input Display & Dropdown Popover */}
            <div className="relative" ref={datePickerRef}>
              <div
                onClick={() => setIsDatePickerOpen((prev) => !prev)}
                className="flex items-center bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded px-3 py-1.5 text-xs text-slate-700 dark:text-slate-200 space-x-2 cursor-pointer hover:border-slate-400 transition-colors shadow-2xs select-none"
              >
                <span>{pickerStart ? formatDisplayDate(pickerStart) : "Select Start"}</span>
                <span className="text-slate-400">→</span>
                <span>{pickerEnd ? formatDisplayDate(pickerEnd) : "Select End"}</span>
                <CalendarIcon className="h-3.5 w-3.5 text-slate-400 ml-1" />
              </div>

              {/* DUAL MONTH CALENDAR POPOVER */}
              {isDatePickerOpen && (
                <div className="absolute top-full left-0 mt-2 z-50 w-[580px] bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-2xl p-4 space-y-3 animate-in fade-in zoom-in-95 duration-100">
                  <div className="absolute -top-1.5 left-8 w-3 h-3 rotate-45 bg-white dark:bg-slate-900 border-t border-l border-slate-200 dark:border-slate-800" />
                  <div className="grid grid-cols-2 gap-6 pt-1">
                    {renderCalendarMonth(viewYear, viewMonth, false)}
                    {renderCalendarMonth(month2Year, month2Month, true)}
                  </div>
                </div>
              )}
            </div>

            {/* Branch Select */}
            <select
              value={selectedBranchId ?? "all"}
              onChange={(e) => {
                const val = e.target.value;
                setSelectedBranchId(val === "all" ? undefined : Number(val));
                setCurrentPage(1);
              }}
              className="h-8 px-3 text-xs bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded text-slate-700 dark:text-slate-200 focus:outline-none"
            >
              <option value="all">All Branches</option>
              {branchOptions.map((b) => (
                <option key={b.branch_id} value={b.branch_id}>
                  {b.branch_name}
                </option>
              ))}
            </select>

            {/* Search Input & Button */}
            <div className="flex items-center gap-2">
              <div className="relative">
                <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-400" />
                <Input
                  type="text"
                  placeholder="Search code or name..."
                  value={searchInput}
                  onChange={(e) => setSearchInput(e.target.value)}
                  className="pl-8 h-8 text-xs w-44 bg-white dark:bg-slate-950 border-slate-300"
                />
              </div>

              <Button
                onClick={() => setCurrentPage(1)}
                size="sm"
                className="h-8 px-4 text-xs font-semibold bg-[#0B85C9] hover:bg-[#0974b0] text-white rounded border-0 shadow-2xs cursor-pointer"
              >
                Search
              </Button>
            </div>
          </div>

          {/* Right Controls: Save, Export Excel, Enter Fullscreen */}
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleSave}
              disabled={bulkSetMutation.isPending}
              className="h-8 px-3 text-xs font-medium bg-white dark:bg-slate-900 border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 cursor-pointer shadow-2xs"
            >
              <Save className="h-3.5 w-3.5 mr-1 text-slate-500 dark:text-slate-400" />
              {bulkSetMutation.isPending ? "Saving..." : "Save"}
            </Button>

            <Button
              variant="outline"
              size="sm"
              onClick={handleExportExcel}
              className="h-8 px-3 text-xs font-medium bg-white dark:bg-slate-900 border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 cursor-pointer shadow-2xs"
            >
              <Download className="h-3.5 w-3.5 mr-1 text-slate-500 dark:text-slate-400" />
              Export Excel
            </Button>

            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsFullscreen((prev) => !prev)}
              className="h-8 px-3 text-xs font-medium bg-white dark:bg-slate-900 border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-200 hover:bg-slate-50"
            >
              {isFullscreen ? (
                <>
                  <Minimize2 className="h-3.5 w-3.5 mr-1 text-slate-500" />
                  Exit Fullscreen
                </>
              ) : (
                <>
                  <Maximize2 className="h-3.5 w-3.5 mr-1 text-slate-500" />
                  Enter Fullscreen
                </>
              )}
            </Button>
          </div>
        </div>

        {/* Spreadsheet Table Container */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg shadow-2xs overflow-hidden flex flex-col z-10 relative">
          {/* Scrollable Table Wrapper with sticky frozen headers */}
          <div className="w-full overflow-x-auto max-h-[620px] overflow-y-auto relative border-b border-slate-200 dark:border-slate-800">
            <table className="w-full text-left border-collapse text-xs select-none table-fixed">
              {/* Column Width Definitions */}
              <colgroup>
                <col className="w-[90px] min-w-[90px] max-w-[90px]" />
                <col className="w-[150px] min-w-[150px] max-w-[150px]" />
                <col className="w-[130px] min-w-[130px] max-w-[130px]" />
                <col className="w-[140px] min-w-[140px] max-w-[140px]" />
                {dynamicDates.map((d) => (
                  <col key={d.dateStr} className="w-[125px] min-w-[125px] max-w-[125px]" />
                ))}
              </colgroup>

              {/* Header Group 1 & 2 */}
              <thead className="sticky top-0 z-40 bg-[#EBF5FF] dark:bg-slate-950 text-slate-800 dark:text-slate-200 font-semibold border-b border-slate-300 dark:border-slate-700">
                {/* Row 1: Category headers */}
                <tr className="border-b border-slate-300 dark:border-slate-700">
                  <th
                    colSpan={2}
                    className="sticky top-0 left-0 z-50 isolate bg-[#EBF5FF] dark:bg-slate-950 px-3 py-2 w-[240px] min-w-[240px] max-w-[240px] border-r border-slate-300 dark:border-slate-700 text-xs font-bold text-slate-700 dark:text-slate-300"
                  >
                    Employees
                  </th>
                  <th
                    colSpan={2}
                    className="sticky top-0 left-[240px] z-50 isolate bg-[#EBF5FF] dark:bg-slate-950 px-3 py-2 w-[270px] min-w-[270px] max-w-[270px] border-r-2 border-slate-400 dark:border-slate-600 text-xs font-bold text-slate-700 dark:text-slate-300 shadow-[2px_0_5px_-2px_rgba(0,0,0,0.1)]"
                  >
                    Hierarchy
                  </th>
                  {dynamicDates.map((d) => (
                    <th
                      key={d.dateStr}
                      className="px-3 py-2 border-r border-slate-300 dark:border-slate-700/80 text-center min-w-[125px] w-[125px] font-bold text-slate-700 dark:text-slate-300"
                    >
                      {d.dateLabel}
                    </th>
                  ))}
                </tr>

                {/* Row 2: Sub-column headers */}
                <tr className="border-b border-slate-300 dark:border-slate-700">
                  <th className="sticky top-[33px] left-0 z-50 isolate bg-[#EBF5FF] dark:bg-slate-950 px-3 py-2 w-[90px] min-w-[90px] max-w-[90px] border-r border-slate-300 dark:border-slate-700/80 font-semibold text-slate-600 dark:text-slate-400">
                    <div className="flex items-center gap-1">
                      <SlidersHorizontal className="h-3 w-3 text-slate-400 shrink-0" />
                      <span className="truncate">Code</span>
                    </div>
                  </th>
                  <th className="sticky top-[33px] left-[90px] z-50 isolate bg-[#EBF5FF] dark:bg-slate-950 px-3 py-2 w-[150px] min-w-[150px] max-w-[150px] border-r border-slate-300 dark:border-slate-700/80 font-semibold text-slate-600 dark:text-slate-400">
                    <div className="flex items-center gap-1">
                      <SlidersHorizontal className="h-3 w-3 text-slate-400 shrink-0" />
                      <span className="truncate">Name</span>
                    </div>
                  </th>
                  <th className="sticky top-[33px] left-[240px] z-50 isolate bg-[#EBF5FF] dark:bg-slate-950 px-3 py-2 w-[130px] min-w-[130px] max-w-[130px] border-r border-slate-300 dark:border-slate-700/80 font-semibold text-slate-600 dark:text-slate-400">
                    <div className="flex items-center gap-1">
                      <SlidersHorizontal className="h-3 w-3 text-slate-400 shrink-0" />
                      <span className="truncate">Department</span>
                    </div>
                  </th>
                  <th className="sticky top-[33px] left-[370px] z-50 isolate bg-[#EBF5FF] dark:bg-slate-950 px-3 py-2 w-[140px] min-w-[140px] max-w-[140px] border-r-2 border-slate-400 dark:border-slate-600 font-semibold text-slate-600 dark:text-slate-400 shadow-[2px_0_5px_-2px_rgba(0,0,0,0.1)]">
                    <div className="flex items-center gap-1">
                      <SlidersHorizontal className="h-3 w-3 text-slate-400 shrink-0" />
                      <span className="truncate">Designation</span>
                    </div>
                  </th>
                  {dynamicDates.map((d) => (
                    <th
                      key={d.dateStr}
                      className="px-3 py-2 border-r border-slate-300 dark:border-slate-700/80 text-center min-w-[125px] w-[125px] font-semibold text-slate-600 dark:text-slate-400"
                    >
                      {d.dayLabel}
                    </th>
                  ))}
                </tr>
              </thead>

              {/* Table Body */}
              <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                {isLoading ? (
                  Array.from({ length: pageSize }).map((_, idx) => (
                    <tr key={idx} className="animate-pulse">
                      <td className="sticky left-0 z-30 isolate bg-white dark:bg-slate-900 px-3 py-3 w-[90px] min-w-[90px] border-r border-slate-300 dark:border-slate-700/80">
                        <div className="h-3.5 w-12 bg-slate-200 dark:bg-slate-800 rounded" />
                      </td>
                      <td className="sticky left-[90px] z-30 isolate bg-white dark:bg-slate-900 px-3 py-3 w-[150px] min-w-[150px] border-r border-slate-300 dark:border-slate-700/80">
                        <div className="h-3.5 w-28 bg-slate-200 dark:bg-slate-800 rounded" />
                      </td>
                      <td className="sticky left-[240px] z-30 isolate bg-white dark:bg-slate-900 px-3 py-3 w-[130px] min-w-[130px] border-r border-slate-300 dark:border-slate-700/80">
                        <div className="h-3.5 w-20 bg-slate-200 dark:bg-slate-800 rounded" />
                      </td>
                      <td className="sticky left-[370px] z-30 isolate bg-white dark:bg-slate-900 px-3 py-3 w-[140px] min-w-[140px] border-r-2 border-slate-400 dark:border-slate-600 shadow-[2px_0_5px_-2px_rgba(0,0,0,0.1)]">
                        <div className="h-3.5 w-20 bg-slate-200 dark:bg-slate-800 rounded" />
                      </td>
                      {dynamicDates.map((d) => (
                        <td key={d.dateStr} className="relative z-0 px-3 py-3 border-r border-slate-300 dark:border-slate-700/80 text-center min-w-[125px] w-[125px]">
                          <div className="h-6 w-20 bg-slate-200 dark:bg-slate-800 rounded mx-auto" />
                        </td>
                      ))}
                    </tr>
                  ))
                ) : employees.length === 0 ? (
                  <tr>
                    <td colSpan={4 + dynamicDates.length} className="px-6 py-12 text-center text-slate-400">
                      No matching employee records found.
                    </td>
                  </tr>
                ) : (
                  employees.map((emp) => (
                    <tr
                      key={emp.id}
                      className="group hover:bg-slate-50/70 dark:hover:bg-slate-800/40 transition-colors border-b border-slate-200 dark:border-slate-800"
                    >
                      {/* Frozen Code Column */}
                      <td className="sticky left-0 z-30 isolate bg-white dark:bg-slate-900 group-hover:bg-slate-50 dark:group-hover:bg-slate-800/90 px-3 py-3 w-[90px] min-w-[90px] max-w-[90px] border-r border-slate-300 dark:border-slate-700/80 font-medium text-slate-600 dark:text-slate-300 truncate">
                        {emp.code}
                      </td>

                      {/* Frozen Name Column */}
                      <td className="sticky left-[90px] z-30 isolate bg-white dark:bg-slate-900 group-hover:bg-slate-50 dark:group-hover:bg-slate-800/90 px-3 py-3 w-[150px] min-w-[150px] max-w-[150px] border-r border-slate-300 dark:border-slate-700/80 font-semibold text-slate-800 dark:text-slate-100 truncate" title={emp.name}>
                        {emp.name}
                      </td>

                      {/* Frozen Department Column */}
                      <td className="sticky left-[240px] z-30 isolate bg-white dark:bg-slate-900 group-hover:bg-slate-50 dark:group-hover:bg-slate-800/90 px-3 py-3 w-[130px] min-w-[130px] max-w-[130px] border-r border-slate-300 dark:border-slate-700/80 text-slate-600 dark:text-slate-300 truncate" title={emp.department}>
                        {emp.department}
                      </td>

                      {/* Frozen Designation Column */}
                      <td className="sticky left-[370px] z-30 isolate bg-white dark:bg-slate-900 group-hover:bg-slate-50 dark:group-hover:bg-slate-800/90 px-3 py-3 w-[140px] min-w-[140px] max-w-[140px] border-r-2 border-slate-400 dark:border-slate-600 text-slate-600 dark:text-slate-300 truncate shadow-[2px_0_5px_-2px_rgba(0,0,0,0.1)]" title={emp.designation}>
                        {emp.designation}
                      </td>

                      {/* Date Shift Dropdown Cells */}
                      {dynamicDates.map((d) => {
                        const cellKey = `${emp.id}_${d.dateStr}`;
                        const cell = effectiveCellMap[cellKey];

                        let currentOptVal = "Week Off";
                        if (cell) {
                          if (cell.is_week_off || cell.shift_id === null) {
                            currentOptVal = "Week Off";
                          } else {
                            const matchedOpt = shiftOptions.find((o) => o.id === cell.shift_id);
                            currentOptVal = matchedOpt ? matchedOpt.value : String(cell.shift_id);
                          }
                        }

                        const shiftOpt =
                          shiftOptions.find((s) => s.value === currentOptVal) || shiftOptions[0];

                        return (
                          <td
                            key={d.dateStr}
                            className="relative z-0 px-2 py-2 border-r border-slate-200 dark:border-slate-800 text-center min-w-[125px] w-[125px]"
                          >
                            <select
                              value={currentOptVal}
                              onChange={(e) =>
                                handleShiftChange(emp.id, d.dateStr, e.target.value)
                              }
                              className={`w-full h-7 px-2 text-xs font-semibold rounded border border-transparent cursor-pointer focus:outline-none focus:ring-1 focus:ring-sky-500 ${shiftOpt.bgClass} ${shiftOpt.textClass}`}
                            >
                              {shiftOptions.map((opt) => (
                                <option key={opt.value} value={opt.value} className="bg-white text-slate-800 dark:bg-slate-900 dark:text-slate-100">
                                  {opt.label}
                                </option>
                              ))}
                            </select>
                          </td>
                        );
                      })}
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination Footer */}
          <div className="p-3 bg-slate-50/60 dark:bg-slate-950 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs">
            <div className="text-slate-500 dark:text-slate-400 font-medium">
              Showing{" "}
              <span className="font-semibold text-slate-700 dark:text-slate-200">
                {totalRecords === 0 ? 0 : (currentPage - 1) * pageSize + 1}
              </span>{" "}
              to{" "}
              <span className="font-semibold text-slate-700 dark:text-slate-200">
                {Math.min(currentPage * pageSize, totalRecords)}
              </span>{" "}
              of{" "}
              <span className="font-semibold text-slate-700 dark:text-slate-200">
                {totalRecords}
              </span>{" "}
              Entries
            </div>

            <div className="flex items-center gap-3">
              <div className="flex items-center gap-1">
                <span className="text-slate-500">Rows:</span>
                <select
                  value={pageSize}
                  onChange={(e) => {
                    setPageSize(Number(e.target.value));
                    setCurrentPage(1);
                  }}
                  className="h-7 px-2 text-xs bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded text-slate-700 dark:text-slate-200 focus:outline-none"
                >
                  {[5, 10, 20, 50].map((sz) => (
                    <option key={sz} value={sz}>
                      {sz}
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex items-center gap-1">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCurrentPage((prev) => Math.max(prev - 1, 1))}
                  disabled={currentPage === 1 || totalPages <= 1}
                  className="h-7 px-2.5 text-xs bg-white dark:bg-slate-900 border-slate-300"
                >
                  <ChevronLeft className="h-3.5 w-3.5" />
                  Previous
                </Button>
                <span className="px-2 py-1 text-xs font-semibold text-slate-700 dark:text-slate-200">
                  Page {currentPage} of {totalPages}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCurrentPage((prev) => Math.min(prev + 1, totalPages))}
                  disabled={currentPage === totalPages || totalPages <= 1}
                  className="h-7 px-2.5 text-xs bg-white dark:bg-slate-900 border-slate-300"
                >
                  Next
                  <ChevronRight className="h-3.5 w-3.5" />
                </Button>
              </div>
            </div>
          </div>
        </div>

      </div>
    </ProtectedRoute>
  );
}
