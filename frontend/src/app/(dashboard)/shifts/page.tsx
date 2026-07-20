"use client";

import React, { useState, useEffect } from "react";
import {
  Search,
  SlidersHorizontal,
  Download,
  Clock,
  X,
  Settings,
  HelpCircle,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { toast } from "sonner";
import { useRouter } from "next/navigation";
import { ProtectedRoute } from "@/features/auth";
import { isAxiosError } from "axios";
import {
  useShifts,
  useShift,
  useCreateShift,
  useUpdateShift,
  useDeleteShift,
} from "@/features/shifts/hooks";
import type {
  ShiftSummarySchema,
  ShiftSortBy,
} from "@/features/shifts/types";
import { useDebouncedValue } from "@/features/employees/hooks";

interface ApiErrorData {
  error?: { message?: string };
}

const getErrMsg = (err: unknown, fallback: string): string => {
  if (isAxiosError(err)) {
    const d = err.response?.data as ApiErrorData | undefined;
    return d?.error?.message || fallback;
  }
  if (err instanceof Error) return err.message;
  return fallback;
};

const WEEKDAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];

/** Format ISO datetime → YYYY-MM-DD for display. */
const fmtDate = (iso: string): string => {
  try { return iso.slice(0, 10); } catch { return iso; }
};

export default function ShiftsPage() {
  const router = useRouter();
  const [searchQuery, setSearchQuery] = useState("");
  const debouncedSearch = useDebouncedValue(searchQuery, 400);

  // View modes
  const [isAdvancedMode, setIsAdvancedMode] = useState(false);
  const [showSwitchModal, setShowSwitchModal] = useState(false);

  // Sorting — server-side
  const [sortField, setSortField] = useState<ShiftSortBy>("shift_name");
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("asc");

  // Pagination — server-side
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  // Delete confirmation
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [shiftToDelete, setShiftToDelete] = useState<number | null>(null);

  // Create/Edit Shift Drawer state
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [drawerMode, setDrawerMode] = useState<"add" | "edit">("add");
  const [selectedShiftId, setSelectedShiftId] = useState<number | null>(null);

  // Form Fields
  const [formName, setFormName] = useState("");
  const [oneShiftTimeForAllDays, setOneShiftTimeForAllDays] = useState(true);
  const [addBreakTime, setAddBreakTime] = useState(false);
  const [formStartTime, setFormStartTime] = useState("");
  const [formEndTime, setFormEndTime] = useState("");
  const [formBreakStart, setFormBreakStart] = useState("");
  const [formBreakEnd, setFormBreakEnd] = useState("");
  const [shiftColor, setShiftColor] = useState("#0B85C9");
  const [formRemark, setFormRemark] = useState("");
  const [dayTimings, setDayTimings] = useState<Record<string, { check_in: string; check_out: string; is_working: boolean }>>({});

  // Working hours Drawer
  const [isWorkingHoursOpen, setIsWorkingHoursOpen] = useState(false);
  const [workingHoursType, setWorkingHoursType] = useState<"fixed" | "shift_wise">("fixed");
  const [fullDayHours, setFullDayHours] = useState("08:00");
  const [halfDayHours, setHalfDayHours] = useState("04:00");
  const [attendanceMode, setAttendanceMode] = useState<"all" | "first_last" | "single" | "default">("all");
  const [isConfigHistoryOpen, setIsConfigHistoryOpen] = useState(true);

  // Validation Errors
  const [errors, setErrors] = useState<Record<string, string>>({});

  // ---- React Query ----
  const shiftsQuery = useShifts({
    page: currentPage,
    page_size: pageSize,
    q: debouncedSearch.trim() || undefined,
    sort_by: sortField,
    sort_order: sortDirection,
  });

  const shiftDetailQuery = useShift(
    selectedShiftId ?? 0,
    drawerMode === "edit" && !!selectedShiftId
  );

  const createMutation = useCreateShift();
  const updateMutation = useUpdateShift();
  const deleteMutation = useDeleteShift();

  const isSaving = createMutation.isPending || updateMutation.isPending;
  const isDeleting = deleteMutation.isPending;

  const shifts = shiftsQuery.data?.items ?? [];
  const pagination = shiftsQuery.data?.pagination;
  const totalRecords = pagination?.total_records ?? 0;
  const totalPages = pagination?.total_pages ?? 1;
  const isLoading = shiftsQuery.isLoading;

  // Form validation
  const validateForm = () => {
    const newErrors: Record<string, string> = {};
    if (!formName.trim()) newErrors.shift_name = "Shift Name is required";
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // Populate form from backend detail when editDrawer detail loads
  useEffect(() => {
    if (drawerMode === "edit" && shiftDetailQuery.data) {
      const s = shiftDetailQuery.data;
      setFormName(s.shift_name);
      setFormRemark(s.remark || "");
      setShiftColor(s.shift_color || "#0B85C9");
      setOneShiftTimeForAllDays(s.is_uniform_time);
      setAddBreakTime(s.has_break_time);

      // Find uniform timing row (day_of_week === null) or first row
      const uniformRow = s.day_timings.find((t) => t.day_of_week === null) ?? s.day_timings[0];
      setFormStartTime(uniformRow?.start_time?.slice(0, 5) ?? "");
      setFormEndTime(uniformRow?.end_time?.slice(0, 5) ?? "");
      setFormBreakStart(uniformRow?.break_start_time?.slice(0, 5) ?? "");
      setFormBreakEnd(uniformRow?.break_end_time?.slice(0, 5) ?? "");

      // Per-day timings (day_of_week 0=Sun … 6=Sat)
      const mapped: Record<string, { check_in: string; check_out: string; is_working: boolean }> = {};
      WEEKDAYS.forEach((day, idx) => {
        const row = s.day_timings.find((t) => t.day_of_week === idx);
        mapped[day] = {
          check_in: row?.start_time?.slice(0, 5) ?? "",
          check_out: row?.end_time?.slice(0, 5) ?? "",
          is_working: row?.is_working_day ?? true,
        };
      });
      setDayTimings(mapped);
    }
  }, [drawerMode, shiftDetailQuery.data]);

  // Handle Sort (server-side)
  const handleSort = (field: ShiftSortBy) => {
    if (sortField === field) {
      setSortDirection((prev) => (prev === "asc" ? "desc" : "asc"));
    } else {
      setSortField(field);
      setSortDirection("asc");
    }
    setCurrentPage(1);
  };

  // Open Add Shift
  const handleOpenAdd = () => {
    setDrawerMode("add");
    setSelectedShiftId(null);
    setFormName("");
    setOneShiftTimeForAllDays(true);
    setAddBreakTime(false);
    setFormStartTime("");
    setFormEndTime("");
    setFormBreakStart("");
    setFormBreakEnd("");
    setShiftColor("#0B85C9");
    setFormRemark("");
    const initialDays: Record<string, { check_in: string; check_out: string; is_working: boolean }> = {};
    WEEKDAYS.forEach((d) => { initialDays[d] = { check_in: "", check_out: "", is_working: true }; });
    setDayTimings(initialDays);
    setErrors({});
    setIsDrawerOpen(true);
  };

  // Open Edit Shift — load from backend via useShift()
  const handleOpenEdit = (shift: ShiftSummarySchema) => {
    setDrawerMode("edit");
    setSelectedShiftId(shift.shift_id);
    // Pre-populate from summary while detail loads
    setFormName(shift.shift_name);
    setShiftColor(shift.shift_color || "#0B85C9");
    setFormRemark("");
    setOneShiftTimeForAllDays(shift.is_uniform_time);
    setAddBreakTime(shift.has_break_time);
    setFormStartTime("");
    setFormEndTime("");
    setFormBreakStart("");
    setFormBreakEnd("");
    const initialDays: Record<string, { check_in: string; check_out: string; is_working: boolean }> = {};
    WEEKDAYS.forEach((d) => { initialDays[d] = { check_in: "", check_out: "", is_working: true }; });
    setDayTimings(initialDays);
    setErrors({});
    setIsDrawerOpen(true);
  };

  // Build day_timings payload from form state
  const buildDayTimingsPayload = () => {
    if (oneShiftTimeForAllDays) {
      return [{
        day_of_week: null,
        start_time: formStartTime || null,
        end_time: formEndTime || null,
        break_start_time: addBreakTime && formBreakStart ? formBreakStart : null,
        break_end_time: addBreakTime && formBreakEnd ? formBreakEnd : null,
        is_working_day: !!(formStartTime && formEndTime),
        crosses_midnight: false,
      }];
    }
    return WEEKDAYS.map((day, idx) => {
      const info = dayTimings[day] || { check_in: "", check_out: "", is_working: true };
      return {
        day_of_week: idx,
        start_time: info.is_working && info.check_in ? info.check_in : null,
        end_time: info.is_working && info.check_out ? info.check_out : null,
        break_start_time: null,
        break_end_time: null,
        is_working_day: info.is_working,
        crosses_midnight: false,
      };
    });
  };

  // Save Shift — calls backend
  const handleSaveShift = (e: React.FormEvent) => {
    e.preventDefault();
    if (!validateForm()) {
      toast.error("Please fill in the Shift Name.");
      return;
    }

    const payload = {
      shift_name: formName.trim(),
      shift_color: shiftColor || null,
      remark: formRemark.trim() || null,
      is_uniform_time: oneShiftTimeForAllDays,
      has_break_time: addBreakTime,
      day_timings: buildDayTimingsPayload(),
    };

    if (drawerMode === "add") {
      createMutation.mutate(payload, {
        onSuccess: () => {
          toast.success("Shift created successfully.");
          setIsDrawerOpen(false);
        },
        onError: (err: unknown) => {
          toast.error(getErrMsg(err, "Failed to create shift"));
        },
      });
    } else {
      if (!selectedShiftId) return;
      updateMutation.mutate(
        { id: selectedShiftId, data: payload },
        {
          onSuccess: () => {
            toast.success("Shift updated successfully.");
            setIsDrawerOpen(false);
          },
          onError: (err: unknown) => {
            toast.error(getErrMsg(err, "Failed to update shift"));
          },
        }
      );
    }
  };

  // Delete shift
  const initiateDelete = (shiftId: number) => {
    setShiftToDelete(shiftId);
    setIsDeleteModalOpen(true);
  };

  const confirmDelete = () => {
    if (!shiftToDelete) return;
    deleteMutation.mutate(shiftToDelete, {
      onSuccess: () => {
        toast.success("Shift deleted successfully.");
        setIsDeleteModalOpen(false);
        setShiftToDelete(null);
      },
      onError: (err: unknown) => {
        toast.error(getErrMsg(err, "Failed to delete shift"));
      },
    });
  };

  // Reset Filters
  const handleResetFilters = () => {
    setSearchQuery("");
    setCurrentPage(1);
  };

  // Toggle Mode Confirmation Dialog Trigger
  const handleToggleModeClick = () => {
    if (!isAdvancedMode) {
      setShowSwitchModal(true);
    } else {
      setIsAdvancedMode(false);
    }
  };

  const handleConfirmSwitch = () => {
    setIsAdvancedMode(true);
    setShowSwitchModal(false);
  };

  return (
    <ProtectedRoute requiredPermission={{ feature: "shift", action: "read" }}>
      <div className="p-6 space-y-6 bg-slate-50/40 min-h-screen">
        {/* Upper breadcrumbs */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <button
              onClick={() => router.back()}
              className="flex items-center gap-1 text-sm font-semibold text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
            >
              <span>Dashboard</span>
            </button>
          </div>
          <div className="text-right text-xs text-muted-foreground">
            Active Workspace: <span className="font-semibold text-foreground">Itcode Infotech</span>
          </div>
        </div>

        {/* Title Block - Matching Layout with side-by-side buttons */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold text-slate-800 dark:text-slate-100 flex items-center gap-1">
              Shifts <span className="text-[#0B85C9] font-bold">({totalRecords})</span>
            </h1>
          </div>

          {/* Premium side-by-side buttons exactly as screenshot */}
          <div className="flex flex-wrap items-center gap-2.5">
            <Button
              variant="primary"
              size="sm"
              onClick={handleToggleModeClick}
              className="h-9 px-4 text-xs font-bold bg-[#0B85C9] hover:bg-[#0974b0] text-white rounded-lg shadow-sm border-0"
            >
              {isAdvancedMode ? "Switch To Weekly View" : "Switch To Advanced Shift"}
            </Button>

            <Button
              variant="primary"
              size="sm"
              onClick={() => router.push("/shifts/assignments")}
              className="h-9 px-4 text-xs font-bold bg-[#0B85C9] hover:bg-[#0974b0] text-white rounded-lg shadow-sm border-0"
            >
              Assign Shift
            </Button>

            <Button
              variant="primary"
              size="sm"
              onClick={() => setIsWorkingHoursOpen(true)}
              className="h-9 px-4 text-xs font-bold bg-[#0B85C9] hover:bg-[#0974b0] text-white rounded-lg shadow-sm border-0"
            >
              Set Working Hours
            </Button>

            <Button
              variant="primary"
              size="sm"
              onClick={handleOpenAdd}
              className="h-9 px-4 text-xs font-bold bg-[#0B85C9] hover:bg-[#0974b0] text-white rounded-lg shadow-sm border-0"
            >
              Create Shift
            </Button>
          </div>
        </div>

        {/* Main Grid Wrapper */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 rounded-xl shadow-xs overflow-hidden">
          
          {/* Toolbar */}
          <div className="p-4 border-b border-slate-200/80 dark:border-slate-800 flex flex-col md:flex-row items-center justify-between gap-4 bg-slate-50/45 dark:bg-slate-950/20">
            
            {/* Left search */}
            <div className="relative w-full md:max-w-xs shrink-0">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400 dark:text-slate-500" />
              <Input
                type="text"
                placeholder="Search shifts..."
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  setCurrentPage(1);
                }}
                className="pl-9 h-9 text-xs w-full bg-white dark:bg-slate-955 text-slate-800 dark:text-slate-100 placeholder:text-slate-450 dark:placeholder:text-slate-500 border border-slate-200 dark:border-slate-800 focus-visible:ring-blue-500/20 focus-visible:border-blue-500"
              />
            </div>

            {/* Middle Filters */}
            <div className="flex flex-wrap items-center gap-3 w-full md:w-auto md:justify-end">
              <Button
                variant="outline"
                size="sm"
                onClick={handleResetFilters}
                className="h-8 text-xs font-semibold text-slate-655 dark:text-slate-300 border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 hover:bg-slate-50 dark:hover:bg-slate-800/50"
              >
                <SlidersHorizontal className="h-3.5 w-3.5 mr-1" />
                Reset Filters
              </Button>

              <Button
                variant="outline"
                size="sm"
                onClick={() => toast.success("Export initiated.")}
                className="h-8 text-xs font-semibold text-slate-600 dark:text-slate-300 border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 hover:bg-slate-50 dark:hover:bg-slate-800/50"
              >
                <Download className="h-3.5 w-3.5 mr-1 text-slate-400 dark:text-slate-500" />
                Export
              </Button>
            </div>
          </div>

          {/* Table Container */}
          <div className="overflow-x-auto relative min-h-[250px]">
            <table className="w-full text-left border-collapse text-xs">
              
              <thead className="bg-[#f8fafc] dark:bg-slate-950 border-b border-slate-200/80 dark:border-slate-800 uppercase text-[10px] tracking-wider text-slate-500 font-bold">
                <tr>
                  <th
                    onClick={() => handleSort("shift_name")}
                    className="px-6 py-3.5 cursor-pointer hover:text-slate-800 transition-colors select-none font-bold"
                  >
                    <div className="flex items-center gap-1.5">
                      Shift Name
                      <span className="text-[9px] text-slate-400">
                        {sortField === "shift_name" ? (sortDirection === "asc" ? "▲" : "▼") : "↕"}
                      </span>
                    </div>
                  </th>
                  
                  {/* Ordered Weekdays starting with Sunday as requested */}
                  <th className="px-3 py-3.5 font-bold text-center">Sunday</th>
                  <th className="px-3 py-3.5 font-bold text-center">Monday</th>
                  <th className="px-3 py-3.5 font-bold text-center">Tuesday</th>
                  <th className="px-3 py-3.5 font-bold text-center">Wednesday</th>
                  <th className="px-3 py-3.5 font-bold text-center">Thursday</th>
                  <th className="px-3 py-3.5 font-bold text-center">Friday</th>
                  <th className="px-3 py-3.5 font-bold text-center">Saturday</th>
                  
                  <th
                    onClick={() => handleSort("created_at")}
                    className="px-4 py-3.5 cursor-pointer hover:text-slate-800 transition-colors text-center select-none font-bold whitespace-nowrap"
                  >
                    <div className="flex items-center justify-center gap-1.5">
                      Assigned Employees
                      <span className="text-[9px] text-slate-400">
                        {sortField === "created_at" ? (sortDirection === "asc" ? "▲" : "▼") : "↕"}
                      </span>
                    </div>
                  </th>

                  {/* Created On Column */}
                  <th className="px-4 py-3.5 font-bold text-left whitespace-nowrap">
                    Created
                  </th>

                  <th className="px-6 py-3.5 text-right font-bold">Actions</th>
                </tr>
              </thead>

              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {isLoading ? (
                  Array.from({ length: 4 }).map((_, idx) => (
                    <tr key={idx} className="border-b border-slate-100 dark:border-slate-800">
                      <td className="px-6 py-5">
                        <div className="flex items-center gap-2">
                          <div className="h-7 w-7 rounded-lg bg-slate-100 dark:bg-slate-800 animate-pulse" />
                          <div className="h-4 w-28 bg-slate-100 dark:bg-slate-800 rounded animate-pulse" />
                        </div>
                      </td>
                      {Array.from({ length: 9 }).map((_, i) => (
                        <td key={i} className="px-3 py-5">
                          <div className="h-4 w-16 bg-slate-100 dark:bg-slate-800 rounded mx-auto animate-pulse" />
                        </td>
                      ))}
                      <td className="px-6 py-5 text-right">
                        <div className="h-8 w-12 bg-slate-100 dark:bg-slate-800 rounded-lg ml-auto animate-pulse" />
                      </td>
                    </tr>
                  ))
                ) : shiftsQuery.isError ? (
                  <tr>
                    <td colSpan={11} className="px-6 py-16 text-center">
                      <div className="flex flex-col items-center justify-center space-y-4 max-w-sm mx-auto">
                        <div className="h-14 w-14 rounded-full bg-red-50 flex items-center justify-center text-red-400">
                          <HelpCircle className="h-7 w-7" />
                        </div>
                        <div>
                          <h4 className="text-sm font-semibold text-slate-800 dark:text-slate-200">Failed to Load Shifts</h4>
                          <p className="text-xs text-slate-500 mt-1">Please try again.</p>
                        </div>
                        <Button variant="outline" size="sm" onClick={() => shiftsQuery.refetch()} className="text-xs">
                          Retry
                        </Button>
                      </div>
                    </td>
                  </tr>
                ) : shifts.length === 0 ? (
                  <tr>
                    <td colSpan={11} className="px-6 py-16 text-center">
                      <div className="flex flex-col items-center justify-center space-y-4 max-w-sm mx-auto">
                        <div className="h-14 w-14 rounded-full bg-slate-50 dark:bg-slate-850 flex items-center justify-center text-slate-400">
                          <HelpCircle className="h-7 w-7" />
                        </div>
                        <div>
                          <h4 className="text-sm font-semibold text-slate-800 dark:text-slate-200">No Shifts Found</h4>
                        </div>
                      </div>
                    </td>
                  </tr>
                ) : (
                  shifts.map((shift) => (
                    <tr
                      key={shift.shift_id}
                      className="hover:bg-slate-50/40 dark:hover:bg-slate-800/10 transition-colors border-b border-slate-100 dark:border-slate-800/60 align-middle"
                    >
                      <td className="px-6 py-4.5 font-bold text-slate-800 dark:text-slate-200 whitespace-nowrap">
                        <div className="flex items-center gap-2.5">
                          <div
                            className="p-2 rounded-xl border border-slate-100 dark:border-slate-800/60 shrink-0"
                            style={{ color: shift.shift_color || "#0B85C9", backgroundColor: `${shift.shift_color || "#0B85C9"}12` }}
                          >
                            <Clock className="h-4.5 w-4.5" />
                          </div>
                          <div>
                            <div className="flex items-center gap-1.5">
                              <span className="hover:text-blue-600 transition-colors cursor-pointer" onClick={() => handleOpenEdit(shift)}>
                                {shift.shift_name}
                              </span>
                              {shift.is_default && (
                                <span className="px-2 py-0.5 text-[9px] font-bold rounded bg-blue-50 text-blue-600 border border-blue-200/50">
                                  Default
                                </span>
                              )}
                              {shift.is_open_shift && (
                                <span className="px-2 py-0.5 text-[9px] font-bold rounded bg-emerald-50 text-emerald-600 border border-emerald-200/50">
                                  Open
                                </span>
                              )}
                            </div>
                          </div>
                        </div>
                      </td>

                      {/* Day columns — show schedule badge since list API does not include per-day timings */}
                      {WEEKDAYS.map((_, idx) => (
                        <td key={idx} className="px-3 py-4 text-center whitespace-nowrap border-l border-slate-100 dark:border-slate-850">
                          {shift.is_open_shift ? (
                            <span className="text-emerald-500 font-semibold text-[10px]">Open</span>
                          ) : shift.is_uniform_time ? (
                            <span className="text-blue-500 font-semibold text-[10px]">Uniform</span>
                          ) : (
                            <span className="text-slate-400 font-semibold text-[10px]">Varied</span>
                          )}
                        </td>
                      ))}

                      <td className="px-4 py-4 text-center whitespace-nowrap font-bold text-slate-700 dark:text-slate-300">
                        —
                      </td>

                      <td className="px-4 py-4 text-left whitespace-nowrap font-semibold text-slate-650 dark:text-slate-400">
                        {fmtDate(shift.created_at)}
                      </td>

                      <td className="px-6 py-4 text-right whitespace-nowrap">
                        <div className="flex items-center justify-end gap-2">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleOpenEdit(shift)}
                            className="h-8 px-3.5 text-xs font-bold text-blue-600 dark:text-blue-450 border-blue-200 dark:border-blue-800/80 bg-white dark:bg-slate-900 hover:bg-blue-50 dark:hover:bg-blue-950/30 cursor-pointer"
                          >
                            Edit
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => initiateDelete(shift.shift_id)}
                            className="h-8 px-3.5 text-xs font-bold text-red-600 dark:text-red-400 border-red-200 dark:border-red-800/80 bg-white dark:bg-slate-900 hover:bg-red-50 dark:hover:bg-red-950/30 cursor-pointer"
                          >
                            Delete
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination Footer */}
          <div className="p-4 border-t border-slate-200 dark:border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-4 bg-slate-50/20 dark:bg-slate-950/10">
            <div className="text-xs text-slate-500 font-semibold">
              Showing{" "}
              <span className="font-bold text-slate-800 dark:text-slate-200">
                {totalRecords === 0 ? 0 : (currentPage - 1) * pageSize + 1}
              </span>{" "}
              to{" "}
              <span className="font-bold text-slate-800 dark:text-slate-200">
                {Math.min(currentPage * pageSize, totalRecords)}
              </span>{" "}
              of <span className="font-bold text-slate-800 dark:text-slate-200">{totalRecords}</span> Results
            </div>

            <div className="flex items-center gap-3">
              <div className="flex items-center gap-1.5">
                <span className="text-xs text-slate-400 font-bold uppercase tracking-wider">Page Size:</span>
                <select
                  value={pageSize}
                  onChange={(e) => {
                    setPageSize(Number(e.target.value));
                    setCurrentPage(1);
                  }}
                  className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-md px-2 py-1 text-xs font-semibold text-slate-700 dark:text-slate-350 focus:outline-none"
                >
                  {[5, 10, 20, 50].map((size) => (
                    <option key={size} value={size}>
                      {size} / Page
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
                  className="h-8 px-2.5 text-xs text-slate-700 dark:text-slate-300 border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 hover:bg-slate-50 dark:hover:bg-slate-800/50"
                >
                  Previous
                </Button>
                <div className="h-8 px-3 flex items-center justify-center text-xs font-bold bg-[#0B85C9]/10 text-[#0B85C9] border border-[#0B85C9]/20 rounded-md">
                  {currentPage}
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCurrentPage((prev) => Math.min(prev + 1, totalPages))}
                  disabled={currentPage === totalPages || totalPages <= 1}
                  className="h-8 px-2.5 text-xs text-slate-700 dark:text-slate-300 border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 hover:bg-slate-50 dark:hover:bg-slate-800/50"
                >
                  Next
                </Button>
              </div>
            </div>
          </div>
        </div>

        {/* SWITCH CONFIRMATION MODAL */}
        {showSwitchModal && (
          <div className="fixed inset-0 z-[110] flex items-center justify-center p-4">
            <div
              className="absolute inset-0 bg-black/60 backdrop-blur-xs transition-opacity"
              onClick={() => setShowSwitchModal(false)}
            />
            <div className="relative w-full max-w-md bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 rounded-2xl shadow-2xl p-6 z-10 space-y-4 animate-in zoom-in-95 duration-150">
              <div className="flex items-start gap-4">
                <div className="p-2.5 bg-blue-50 text-blue-600 rounded-full shrink-0">
                  <Settings className="h-6 w-6" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-800 dark:text-slate-200">Switch to Advanced Shift Mode?</h3>
                  <p className="text-xs text-slate-500 dark:text-slate-400 mt-1.5 leading-relaxed">
                    Are you sure you want to switch to Advanced Shift mode? This will display detailed grace periods, check-in thresholds, break times, and validation parameters.
                  </p>
                </div>
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-100 dark:border-slate-800">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setShowSwitchModal(false)}
                  className="text-xs h-9 px-4 font-semibold text-slate-650 dark:text-slate-355"
                >
                  Cancel
                </Button>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={handleConfirmSwitch}
                  className="text-xs h-9 px-4 font-semibold bg-[#0B85C9] hover:bg-[#0974b0] text-white"
                >
                  Yes, Switch
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* DELETE CONFIRMATION MODAL */}
        {isDeleteModalOpen && (
          <div className="fixed inset-0 z-[110] flex items-center justify-center p-4">
            <div
              className="absolute inset-0 bg-black/60 backdrop-blur-xs transition-opacity"
              onClick={() => { setIsDeleteModalOpen(false); setShiftToDelete(null); }}
            />
            <div className="relative w-full max-w-md bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 rounded-2xl shadow-2xl p-6 z-10 space-y-4 animate-in zoom-in-95 duration-150">
              <div className="flex items-start gap-4">
                <div className="p-2.5 bg-red-50 text-red-600 rounded-full shrink-0">
                  <HelpCircle className="h-6 w-6" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-800 dark:text-slate-200">Delete Shift?</h3>
                  <p className="text-xs text-slate-500 dark:text-slate-400 mt-1.5 leading-relaxed">
                    This action cannot be undone. The shift will be deleted and may be blocked if active assignments reference it.
                  </p>
                </div>
              </div>
              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-100 dark:border-slate-800">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => { setIsDeleteModalOpen(false); setShiftToDelete(null); }}
                  disabled={isDeleting}
                  className="text-xs h-9 px-4 font-semibold"
                >
                  Cancel
                </Button>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={confirmDelete}
                  disabled={isDeleting}
                  className="text-xs h-9 px-4 font-semibold bg-red-600 hover:bg-red-700 text-white"
                >
                  {isDeleting ? "Deleting..." : "Yes, Delete"}
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* ADJUST FULL DAY/HALF DAY HOURS DRAWER */}
        {isWorkingHoursOpen && (
          <div className="fixed inset-0 z-[100] flex justify-end">
            <div
              className="absolute inset-0 bg-black/50 transition-opacity"
              onClick={() => setIsWorkingHoursOpen(false)}
            />
            
            <div className="relative w-full max-w-lg bg-white dark:bg-slate-900 h-full shadow-2xl flex flex-col justify-between z-10 animate-in slide-in-from-right duration-200">
              {/* Header: light blue bg, Adjust Full Day/Half Day Hours */}
              <div className="p-5 border-b border-slate-200/60 dark:border-slate-800 flex items-center justify-between bg-[#EBF5FF] dark:bg-slate-950">
                <h3 className="text-base font-bold text-slate-800 dark:text-slate-100">
                  Adjust Full Day/Half Day Hours
                </h3>
                <button
                  onClick={() => setIsWorkingHoursOpen(false)}
                  className="p-1.5 hover:bg-slate-200/50 dark:hover:bg-slate-800/50 rounded-md text-slate-500 hover:text-slate-800 dark:hover:text-slate-200 transition-colors cursor-pointer focus:outline-none"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>

              {/* Body */}
              <div className="flex-1 overflow-y-auto p-6 space-y-6">
                <div className="space-y-5">
                  {/* Two Radio Buttons side by side */}
                  <div className="flex items-center gap-6">
                    <label className="flex items-center gap-2 text-xs font-bold text-slate-700 dark:text-slate-350 cursor-pointer select-none">
                      <input
                        type="radio"
                        name="workingHoursType"
                        checked={workingHoursType === "fixed"}
                        onChange={() => setWorkingHoursType("fixed")}
                        className="h-4.5 w-4.5 border-slate-300 text-blue-600 focus:ring-blue-500 cursor-pointer"
                      />
                      <span>Fixed Working Hours Per Day</span>
                      <HelpCircle className="h-4 w-4 text-slate-400 hover:text-slate-655" />
                    </label>

                    <label className="flex items-center gap-2 text-xs font-bold text-slate-750 dark:text-slate-400 cursor-pointer select-none">
                      <input
                        type="radio"
                        name="workingHoursType"
                        checked={workingHoursType === "shift_wise"}
                        onChange={() => setWorkingHoursType("shift_wise")}
                        className="h-4.5 w-4.5 border-slate-300 text-blue-600 focus:ring-blue-500 cursor-pointer"
                      />
                      <span>Shift Wise Working Hour</span>
                      <HelpCircle className="h-4 w-4 text-slate-400 hover:text-slate-655" />
                    </label>
                  </div>

                  {/* Full Day Working Hours input */}
                  <div className="space-y-1.5">
                    <label className="text-xs font-bold text-slate-700 dark:text-slate-300">
                      Full Day Working Hours
                    </label>
                    <div className="relative">
                      <Clock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400 dark:text-slate-500" />
                      <input
                        type="text"
                        value={fullDayHours}
                        onChange={(e) => setFullDayHours(e.target.value)}
                        className="pl-9 w-full rounded-md border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950 h-10 text-xs font-medium text-slate-800 dark:text-slate-100 focus:ring-2 focus:ring-blue-500/20 focus:outline-none"
                      />
                    </div>
                  </div>

                  {/* Half Working Day Hours input */}
                  <div className="space-y-1.5">
                    <label className="text-xs font-bold text-slate-700 dark:text-slate-300">
                      Half Working Day Hours
                    </label>
                    <div className="relative">
                      <Clock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400 dark:text-slate-500" />
                      <input
                        type="text"
                        value={halfDayHours}
                        onChange={(e) => setHalfDayHours(e.target.value)}
                        className="pl-9 w-full rounded-md border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950 h-10 text-xs font-medium text-slate-800 dark:text-slate-100 focus:ring-2 focus:ring-blue-500/20 focus:outline-none"
                      />
                    </div>
                  </div>

                  {/* Attendance Mode Radio Buttons list */}
                  <div className="space-y-3 pt-2">
                    <label className="text-xs font-bold text-slate-700 dark:text-slate-300 block">
                      Attendance Mode
                    </label>
                    <div className="space-y-2.5 pl-0.5">
                      {[
                        { key: "all", label: "Consider All Punch" },
                        { key: "first_last", label: "Consider First and Last Punch Only" },
                        { key: "single", label: "Full Day on Single Punch" },
                        { key: "default", label: "Default Full Day" },
                      ].map((mode) => (
                        <label key={mode.key} className="flex items-center gap-2.5 text-xs font-semibold text-slate-700 dark:text-slate-300 cursor-pointer select-none">
                          <input
                            type="radio"
                            name="attendanceMode"
                            checked={attendanceMode === mode.key}
                            onChange={() => setAttendanceMode(mode.key as any)}
                            className="h-4.5 w-4.5 border-slate-300 text-blue-600 focus:ring-blue-500 cursor-pointer"
                          />
                          <span>{mode.label}</span>
                        </label>
                      ))}
                    </div>
                  </div>

                  {/* Note block light blue background */}
                  <div className="p-4 bg-blue-50 dark:bg-blue-950/20 border border-blue-100 dark:border-blue-900/50 rounded-xl space-y-1">
                    <span className="text-xs font-bold text-blue-600 dark:text-blue-400 block">Note:</span>
                    <p className="text-[11px] text-blue-600/90 dark:text-blue-400/90 font-medium">
                      The changes you made will take effect from tomorrow onwards.
                    </p>
                  </div>

                  {/* Configuration History accordion */}
                  <div className="border border-blue-100 dark:border-blue-900/50 rounded-xl overflow-hidden">
                    <button
                      onClick={() => setIsConfigHistoryOpen(!isConfigHistoryOpen)}
                      className="w-full flex items-center justify-between p-3.5 bg-blue-50 dark:bg-slate-950 text-xs font-bold text-slate-700 dark:text-slate-205 focus:outline-none"
                    >
                      <span>Configuration History</span>
                      {isConfigHistoryOpen ? <ChevronUp className="h-4 w-4 text-slate-400" /> : <ChevronDown className="h-4 w-4 text-slate-400" />}
                    </button>
                    {isConfigHistoryOpen && (
                      <div className="p-3.5 bg-white dark:bg-slate-900 border-t border-blue-50 dark:border-blue-900/50 space-y-2 text-[11px] text-slate-500 dark:text-slate-400">
                        <div className="flex justify-between border-b border-slate-50 dark:border-slate-800 pb-1.5">
                          <span className="font-semibold">Fixed Working Hours: 08:00</span>
                          <span>Today, 12:44 PM</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="font-semibold">Attendance Mode: Consider All Punch</span>
                          <span>Yesterday, 09:30 AM</span>
                        </div>
                      </div>
                    )}
                  </div>

                </div>
              </div>

              {/* Footer */}
              <div className="p-4 border-t border-slate-200/60 dark:border-slate-800 bg-[#EBF5FF] dark:bg-slate-950 flex items-center justify-end">
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => {
                    toast.success("Working hours setting updated.");
                    setIsWorkingHoursOpen(false);
                  }}
                  className="text-xs h-9 px-6 font-semibold bg-[#0B85C9] hover:bg-[#0974b0] text-white shadow-sm rounded-lg"
                >
                  Save
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* CREATE / EDIT SHIFT TEMPLATE DRAWER */}
        {isDrawerOpen && (
          <div className="fixed inset-0 z-[100] flex justify-end">
            {/* Backdrop */}
            <div
              className="absolute inset-0 bg-black/50 transition-opacity"
              onClick={() => setIsDrawerOpen(false)}
            />
            
            {/* Drawer Panel */}
            <div className="relative w-full max-w-lg bg-white dark:bg-slate-900 h-full shadow-2xl flex flex-col justify-between z-10 animate-in slide-in-from-right duration-200">
              
              {/* Header: light blue background, close button */}
              <div className="p-5 border-b border-slate-200/60 dark:border-slate-800 flex items-center justify-between bg-[#EBF5FF] dark:bg-slate-950">
                <h3 className="text-base font-bold text-slate-800 dark:text-slate-100">
                  {drawerMode === "add" ? "Create Shift" : "Edit Shift"}
                </h3>
                <button
                  onClick={() => setIsDrawerOpen(false)}
                  className="p-1.5 hover:bg-slate-200/50 dark:hover:bg-slate-800/50 rounded-md text-slate-550 hover:text-slate-800 dark:hover:text-slate-200 transition-colors cursor-pointer focus:outline-none"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>

              {/* Body: white background, padding */}
              <div className="flex-1 overflow-y-auto p-6 space-y-5">
                <form onSubmit={handleSaveShift} className="space-y-5">
                  
                  {/* Shift Name Field */}
                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                      Shift Name <span className="text-red-500">*</span>
                    </label>
                    <Input
                      value={formName}
                      onChange={(e) => {
                        setFormName(e.target.value);
                        if (errors.shift_name) {
                          setErrors((prev) => {
                            const copy = { ...prev };
                            delete copy.shift_name;
                            return copy;
                          });
                        }
                      }}
                      placeholder="Write Shift Name Here"
                      className={`h-10 text-xs w-full bg-white dark:bg-slate-955 text-slate-800 dark:text-slate-100 border border-slate-200 dark:border-slate-800 placeholder:text-slate-400 dark:placeholder:text-slate-500 ${
                        errors.shift_name ? "border-red-500 focus-visible:ring-red-500" : ""
                      }`}
                    />
                    {errors.shift_name && (
                      <p className="text-[10px] font-semibold text-red-500 mt-0.5">{errors.shift_name}</p>
                    )}
                  </div>

                  {/* Toggle: One shift time for all days */}
                  <div className="flex items-center gap-2.5 py-1">
                    <input
                      type="checkbox"
                      id="oneShiftTime"
                      checked={oneShiftTimeForAllDays}
                      onChange={(e) => setOneShiftTimeForAllDays(e.target.checked)}
                      className="h-4.5 w-4.5 rounded border-slate-300 dark:border-slate-700 text-blue-650 focus:ring-blue-500 cursor-pointer"
                    />
                    <label htmlFor="oneShiftTime" className="text-xs font-bold text-slate-700 dark:text-slate-300 cursor-pointer select-none">
                      One shift time for all days.
                    </label>
                  </div>

                  {/* Toggle: Add break time */}
                  <div className="flex items-center gap-2.5 py-1">
                    <input
                      type="checkbox"
                      id="addBreak"
                      checked={addBreakTime}
                      onChange={(e) => setAddBreakTime(e.target.checked)}
                      className="h-4.5 w-4.5 rounded border-slate-300 dark:border-slate-700 text-blue-655 focus:ring-blue-500 cursor-pointer"
                    />
                    <label htmlFor="addBreak" className="text-xs font-bold text-slate-700 dark:text-slate-300 cursor-pointer select-none">
                      Add break time
                    </label>
                  </div>

                  {/* Conditional Timings grid */}
                  {oneShiftTimeForAllDays ? (
                    /* Uniform start and end times */
                    <div className="space-y-4">
                      <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-1.5">
                          <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                            Start Time <span className="text-red-500">*</span>
                          </label>
                          <div className="relative">
                            <Clock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400 dark:text-slate-500" />
                            <input
                              type="time"
                              value={formStartTime}
                              placeholder="Choose From Time"
                              onChange={(e) => setFormStartTime(e.target.value)}
                              className="pl-9 w-full rounded-md border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950 h-10 text-xs text-slate-800 dark:text-slate-100 focus:ring-2 focus:ring-blue-500/20 focus:outline-none"
                            />
                          </div>
                        </div>

                        <div className="space-y-1.5">
                          <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                            End Time <span className="text-red-500">*</span>
                          </label>
                          <div className="relative">
                            <Clock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400 dark:text-slate-500" />
                            <input
                              type="time"
                              value={formEndTime}
                              placeholder="Choose To Time"
                              onChange={(e) => setFormEndTime(e.target.value)}
                              className="pl-9 w-full rounded-md border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950 h-10 text-xs text-slate-800 dark:text-slate-100 focus:ring-2 focus:ring-blue-500/20 focus:outline-none"
                            />
                          </div>
                        </div>
                      </div>

                      {/* Optional break time fields */}
                      {addBreakTime && (
                        <div className="grid grid-cols-2 gap-4 p-3 bg-slate-50 dark:bg-slate-950 rounded-xl border border-slate-100 dark:border-slate-800">
                          <div className="space-y-1.5">
                            <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">Break Start</label>
                            <input
                              type="time"
                              value={formBreakStart}
                              onChange={(e) => setFormBreakStart(e.target.value)}
                              className="w-full rounded-md border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 h-10 px-3 text-xs text-slate-850 dark:text-slate-100 focus:outline-none focus:ring-2"
                            />
                          </div>
                          <div className="space-y-1.5">
                            <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">Break End</label>
                            <input
                              type="time"
                              value={formBreakEnd}
                              onChange={(e) => setFormBreakEnd(e.target.value)}
                              className="w-full rounded-md border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 h-10 px-3 text-xs text-slate-855 dark:text-slate-100 focus:outline-none focus:ring-2"
                            />
                          </div>
                        </div>
                      )}
                    </div>
                  ) : (
                    /* Day-wise timing parameters */
                    <div className="space-y-3 p-3 bg-slate-50/50 dark:bg-slate-950 rounded-xl border border-slate-100 dark:border-slate-800">
                      <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Individual Days Schedule</span>
                      <div className="divide-y divide-slate-100 dark:divide-slate-800">
                        {WEEKDAYS.map((d) => {
                          const info = dayTimings[d] || { check_in: "", check_out: "", is_working: true };
                          return (
                            <div key={d} className="py-2.5 grid grid-cols-12 gap-2 items-center">
                              <div className="col-span-4 flex items-center gap-2">
                                <input
                                  type="checkbox"
                                  checked={info.is_working}
                                  onChange={(e) => {
                                    setDayTimings((prev) => ({
                                      ...prev,
                                      [d]: { ...info, is_working: e.target.checked },
                                    }));
                                  }}
                                  className="h-4 w-4 rounded border-slate-300 dark:border-slate-700 text-blue-650 cursor-pointer"
                                />
                                <span className="text-xs font-semibold text-slate-700 dark:text-slate-300">{d}</span>
                              </div>
                              {info.is_working ? (
                                <>
                                  <div className="col-span-4">
                                    <input
                                      type="time"
                                      value={info.check_in}
                                      onChange={(e) => {
                                        setDayTimings((prev) => ({
                                          ...prev,
                                          [d]: { ...info, check_in: e.target.value },
                                        }));
                                      }}
                                      className="w-full border border-slate-200 dark:border-slate-800 rounded px-2 py-1 text-xs bg-white dark:bg-slate-950 text-slate-850 dark:text-slate-100"
                                    />
                                  </div>
                                  <div className="col-span-4">
                                    <input
                                      type="time"
                                      value={info.check_out}
                                      onChange={(e) => {
                                        setDayTimings((prev) => ({
                                          ...prev,
                                          [d]: { ...info, check_out: e.target.value },
                                        }));
                                      }}
                                      className="w-full border border-slate-200 dark:border-slate-800 rounded px-2 py-1 text-xs bg-white dark:bg-slate-955 text-slate-850 dark:text-slate-100"
                                    />
                                  </div>
                                </>
                              ) : (
                                <div className="col-span-8 text-xs text-slate-400 italic">Off Day</div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}

                  {/* Choose Shift Color Dropdown */}
                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                      Choose Shift Color <span className="text-red-500">*</span>
                    </label>
                    <select
                      value={shiftColor}
                      onChange={(e) => setShiftColor(e.target.value)}
                      className="w-full rounded-md border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950 h-10 px-3 text-xs text-slate-800 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                    >
                      <option value="#0B85C9">Blue</option>
                      <option value="#10B981">Green</option>
                      <option value="#EF4444">Red</option>
                      <option value="#8B5CF6">Purple</option>
                      <option value="#F59E0B">Orange</option>
                    </select>
                  </div>

                  {/* Remark / Textarea field */}
                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">Remark</label>
                    <textarea
                      value={formRemark}
                      onChange={(e) => setFormRemark(e.target.value)}
                      placeholder="Write your remarks or comments here..."
                      rows={4}
                      className="w-full border border-slate-200 dark:border-slate-800 rounded-lg p-3 text-xs focus:ring-2 focus:ring-blue-500/20 focus:outline-none bg-white dark:bg-slate-950 text-slate-800 dark:text-slate-100 resize-none placeholder:text-slate-400 dark:placeholder:text-slate-500"
                    />
                  </div>

                  <button type="submit" className="hidden" id="drawer-submit-btn" />
                </form>
              </div>

              {/* Footer: light blue background, Save button aligned right */}
              <div className="p-4 border-t border-slate-200/60 dark:border-slate-800 bg-[#EBF5FF] dark:bg-slate-950 flex items-center justify-end">
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => document.getElementById("drawer-submit-btn")?.click()}
                  className="text-xs h-9 px-6 font-semibold bg-[#0B85C9] hover:bg-[#0974b0] text-white shadow-sm rounded-lg"
                  disabled={!formName.trim() || isSaving}
                >
                  {isSaving ? "Saving..." : "Save"}
                </Button>
              </div>
            </div>
          </div>
        )}

      </div>
    </ProtectedRoute>
  );
}
