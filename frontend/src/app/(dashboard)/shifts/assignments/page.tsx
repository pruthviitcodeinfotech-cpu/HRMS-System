"use client";

import { useState, useMemo, useCallback } from "react";
import { useRouter } from "next/navigation";
import { isAxiosError } from "axios";
import { toast } from "sonner";
import {
  ChevronLeft,
  X,
  ArrowUpDown,
  Search,
  Filter,
  Loader2,
  AlertCircle,
  Check,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ProtectedRoute } from "@/features/auth";
import { useEmployees } from "@/features/employees/hooks";
import { EmployeeSortBy, SortOrder } from "@/features/employees/types";
import {
  useShifts,
  useShiftAssignments,
  useBulkAssignShift,
} from "@/features/shifts/hooks";
import { ShiftSummarySchema } from "@/features/shifts/types";

const getErrorMessage = (err: unknown): string => {
  if (isAxiosError(err)) {
    return (
      err.response?.data?.message ||
      err.response?.data?.detail ||
      "An unexpected error occurred."
    );
  }
  if (err instanceof Error) {
    return err.message;
  }
  return "An unexpected error occurred.";
};

const getTodayString = (): string => {
  const d = new Date();
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
};

export default function ShiftAssignmentsPage() {
  const router = useRouter();

  // Search & Pagination State
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(10);

  // Server-side Sorting State
  const [sortField, setSortField] = useState<EmployeeSortBy>("employee_code");
  const [sortDirection, setSortDirection] = useState<SortOrder>("asc");

  // Selection & Drawer State
  const [selectedEmpIds, setSelectedEmpIds] = useState<number[]>([]);
  const [isDrawerOpen, setIsDrawerOpen] = useState<boolean>(false);
  const [selectedShiftId, setSelectedShiftId] = useState<number | null>(null);
  const [effectiveFrom, setEffectiveFrom] = useState<string>(getTodayString());

  // Confirmation Modal State
  const [isConfirmOpen, setIsConfirmOpen] = useState<boolean>(false);

  // 1. Fetch Employees (Server-side paginated, searched, sorted)
  const {
    data: employeesData,
    isLoading: isLoadingEmployees,
    isError: isErrorEmployees,
    error: employeesError,
    refetch: refetchEmployees,
  } = useEmployees({
    page: currentPage,
    page_size: pageSize,
    q: searchQuery.trim() || undefined,
    sort_by: sortField,
    sort_order: sortDirection,
  });

  // 2. Fetch Active Shift Definitions (for selection inside drawer)
  const {
    data: shiftsData,
    isLoading: isLoadingShifts,
  } = useShifts({ page_size: 100 });

  // 3. Fetch Active Shift Assignments (for current shift column mapping)
  const todayStr = useMemo(() => getTodayString(), []);
  const { data: assignmentsData } = useShiftAssignments({
    active_on: todayStr,
    page_size: 200,
  });

  // 4. Bulk Assign Mutation
  const bulkAssignMutation = useBulkAssignShift();

  // Map employee_id -> shift_name for display
  const shiftMap = useMemo(() => {
    const map = new Map<number, string>();
    if (!shiftsData?.items) return map;
    const shiftDict = new Map<number, string>();
    shiftsData.items.forEach((s: ShiftSummarySchema) => {
      shiftDict.set(s.shift_id, s.shift_name);
    });

    if (assignmentsData?.items) {
      assignmentsData.items.forEach((a) => {
        const name = shiftDict.get(a.shift_id) || "Assigned";
        map.set(a.employee_id, name);
      });
    }
    return map;
  }, [shiftsData, assignmentsData]);

  // Statistics calculation
  const totalEmployees = employeesData?.pagination.total_records || 0;
  const assignedCount = useMemo(() => {
    if (!employeesData?.items) return 0;
    return employeesData.items.filter((emp) => shiftMap.has(emp.employee_id)).length;
  }, [employeesData, shiftMap]);
  const unassignedCount = Math.max(0, totalEmployees - assignedCount);

  // Current page employees
  const currentEmployees = useMemo(
    () => employeesData?.items || [],
    [employeesData?.items]
  );
  const currentPageEmpIds = useMemo(
    () => currentEmployees.map((e) => e.employee_id),
    [currentEmployees]
  );

  // Selection Logic
  const isAllOnPageSelected =
    currentPageEmpIds.length > 0 &&
    currentPageEmpIds.every((id) => selectedEmpIds.includes(id));

  const handleSelectAll = useCallback(() => {
    if (isAllOnPageSelected) {
      setSelectedEmpIds((prev) =>
        prev.filter((id) => !currentPageEmpIds.includes(id))
      );
    } else {
      setSelectedEmpIds((prev) =>
        Array.from(new Set([...prev, ...currentPageEmpIds]))
      );
    }
  }, [isAllOnPageSelected, currentPageEmpIds]);

  const handleSelectRow = useCallback((empId: number) => {
    setSelectedEmpIds((prev) =>
      prev.includes(empId) ? prev.filter((id) => id !== empId) : [...prev, empId]
    );
  }, []);

  // Sorting Handler
  const handleSort = (field: EmployeeSortBy) => {
    if (sortField === field) {
      setSortDirection((prev) => (prev === "asc" ? "desc" : "asc"));
    } else {
      setSortField(field);
      setSortDirection("asc");
    }
    setCurrentPage(1);
  };

  // Open Drawer
  const handleOpenAssign = () => {
    if (selectedEmpIds.length === 0) return;
    setIsDrawerOpen(true);
  };

  // Submit Assignment
  const handleConfirmAssignment = () => {
    if (!selectedShiftId) {
      toast.error("Please choose a shift to assign.");
      return;
    }
    if (!effectiveFrom) {
      toast.error("Please select an effective date.");
      return;
    }
    setIsConfirmOpen(true);
  };

  const executeBulkAssign = async () => {
    if (!selectedShiftId) return;

    try {
      const result = await bulkAssignMutation.mutateAsync({
        employee_ids: selectedEmpIds,
        shift_id: selectedShiftId,
        effective_from: effectiveFrom,
      });

      if (result.skipped_count > 0) {
        const reasons = result.results
          .filter((r) => r.status === "skipped" && r.reason)
          .map((r) => r.reason)
          .join(", ");
        toast.warning(
          `Assigned shift to ${result.created_count} employee(s). Skipped ${result.skipped_count}${reasons ? `: ${reasons}` : ""}`
        );
      } else {
        toast.success(
          `Successfully assigned shift to ${result.created_count} employee(s).`
        );
      }

      setIsConfirmOpen(false);
      setIsDrawerOpen(false);
      setSelectedEmpIds([]);
      setSelectedShiftId(null);
    } catch (err: unknown) {
      toast.error(getErrorMessage(err));
    }
  };

  const selectedShiftObj = useMemo(() => {
    if (!shiftsData?.items || !selectedShiftId) return null;
    return shiftsData.items.find((s) => s.shift_id === selectedShiftId) || null;
  }, [shiftsData, selectedShiftId]);

  return (
    <ProtectedRoute requiredPermission={{ feature: "shift_assignment", action: "create" }}>
      <div className="p-6 space-y-6 bg-slate-50/40 min-h-screen">

        {/* Page Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <button
                onClick={() => router.push("/shifts")}
                className="p-1 hover:bg-slate-200/60 dark:hover:bg-slate-800/60 rounded-lg text-slate-700 dark:text-slate-200 transition-colors cursor-pointer"
              >
                <ChevronLeft className="h-5 w-5" />
              </button>
              <h1 className="text-xl font-bold text-slate-800 dark:text-slate-100">
                Assign Shifts To Employees
              </h1>
            </div>
            {/* Statistics */}
            <div className="text-xs text-slate-500 dark:text-slate-400 font-medium pl-8 space-x-3">
              <span>
                Assigned:{" "}
                <strong className="text-slate-700 dark:text-slate-200">{assignedCount}</strong>
              </span>
              <span>
                Unassigned:{" "}
                <strong className="text-slate-700 dark:text-slate-200">{unassignedCount}</strong>
              </span>
            </div>
          </div>

          <div>
            <Button
              variant="primary"
              size="sm"
              disabled={selectedEmpIds.length === 0}
              onClick={handleOpenAssign}
              className="h-9 px-5 text-xs font-bold bg-[#0B85C9] hover:bg-[#0974b0] disabled:bg-slate-300 disabled:cursor-not-allowed text-white rounded-lg shadow-sm border-0"
            >
              Assign Shift ({selectedEmpIds.length})
            </Button>
          </div>
        </div>

        {/* Main Grid Wrapper */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 rounded-xl shadow-xs overflow-hidden">
          
          {/* Search & Filter Bar */}
          <div className="p-4 border-b border-slate-200/80 dark:border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-4 bg-slate-50/45 dark:bg-slate-950/20">
            <div className="relative w-full sm:max-w-xs shrink-0">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400 dark:text-slate-500" />
              <Input
                type="text"
                placeholder="Search employee..."
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  setCurrentPage(1);
                }}
                className="pl-9 h-9 text-xs w-full bg-white dark:bg-slate-950 text-slate-800 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500 border border-slate-200 dark:border-slate-800 focus-visible:ring-blue-500/20 focus-visible:border-blue-500"
              />
            </div>

            <div className="flex items-center gap-2 w-full sm:w-auto justify-end">
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setSearchQuery("");
                  setCurrentPage(1);
                }}
                className="h-9 px-3 text-xs text-slate-600 dark:text-slate-300 border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900"
              >
                <Filter className="h-3.5 w-3.5 mr-1" />
                Clear Search
              </Button>
            </div>
          </div>

          {/* Table Area */}
          <div className="w-full overflow-x-auto relative min-h-[300px]">
            {isErrorEmployees ? (
              <div className="p-8 text-center flex flex-col items-center justify-center space-y-3">
                <AlertCircle className="h-10 w-10 text-rose-500" />
                <p className="text-sm font-semibold text-slate-700 dark:text-slate-300">
                  Failed to load employee list.
                </p>
                <p className="text-xs text-slate-500 max-w-md">
                  {getErrorMessage(employeesError)}
                </p>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => refetchEmployees()}
                  className="mt-2 text-xs"
                >
                  Retry
                </Button>
              </div>
            ) : (
              <table className="w-full text-left border-collapse text-xs">
                <thead className="bg-[#EBF5FF] dark:bg-slate-950/80 border-b border-slate-200/80 dark:border-slate-800 uppercase text-[11px] tracking-wider text-slate-700 dark:text-slate-300 font-bold sticky top-0 z-10">
                  <tr>
                    <th className="px-4 py-3.5 w-12 text-center">
                      <input
                        type="checkbox"
                        checked={isAllOnPageSelected}
                        onChange={handleSelectAll}
                        disabled={currentEmployees.length === 0}
                        className="h-4 w-4 rounded border-slate-300 dark:border-slate-700 text-[#0B85C9] focus:ring-[#0B85C9] cursor-pointer disabled:cursor-not-allowed"
                      />
                    </th>
                    <th
                      onClick={() => handleSort("employee_code")}
                      className="px-5 py-3.5 font-bold text-slate-700 dark:text-slate-300 cursor-pointer hover:text-slate-900 transition-colors select-none"
                    >
                      <div className="flex items-center gap-1">
                        Employee ID
                        <ArrowUpDown className="h-3 w-3 text-slate-400" />
                      </div>
                    </th>
                    <th
                      onClick={() => handleSort("employee_name")}
                      className="px-5 py-3.5 font-bold text-slate-700 dark:text-slate-300 cursor-pointer hover:text-slate-900 transition-colors select-none"
                    >
                      <div className="flex items-center gap-1">
                        Employee Name
                        <ArrowUpDown className="h-3 w-3 text-slate-400" />
                      </div>
                    </th>
                    <th className="px-5 py-3.5 font-bold text-slate-700 dark:text-slate-300 select-none">
                      Department
                    </th>
                    <th className="px-5 py-3.5 font-bold text-slate-700 dark:text-slate-300 select-none">
                      Designation
                    </th>
                    <th className="px-5 py-3.5 font-bold text-slate-700 dark:text-slate-300 select-none">
                      Branch
                    </th>
                    <th className="px-5 py-3.5 font-bold text-slate-700 dark:text-slate-300 select-none">
                      Shifts
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800/65">
                  {isLoadingEmployees ? (
                    // Skeleton Loading Rows
                    Array.from({ length: pageSize }).map((_, i) => (
                      <tr key={i} className="animate-pulse">
                        <td className="px-4 py-3.5 text-center">
                          <div className="h-4 w-4 bg-slate-200 dark:bg-slate-800 rounded mx-auto" />
                        </td>
                        <td className="px-5 py-3.5">
                          <div className="h-4 w-12 bg-slate-200 dark:bg-slate-800 rounded" />
                        </td>
                        <td className="px-5 py-3.5">
                          <div className="h-4 w-32 bg-slate-200 dark:bg-slate-800 rounded" />
                        </td>
                        <td className="px-5 py-3.5">
                          <div className="h-4 w-24 bg-slate-200 dark:bg-slate-800 rounded" />
                        </td>
                        <td className="px-5 py-3.5">
                          <div className="h-4 w-24 bg-slate-200 dark:bg-slate-800 rounded" />
                        </td>
                        <td className="px-5 py-3.5">
                          <div className="h-4 w-24 bg-slate-200 dark:bg-slate-800 rounded" />
                        </td>
                        <td className="px-5 py-3.5">
                          <div className="h-4 w-16 bg-slate-200 dark:bg-slate-800 rounded" />
                        </td>
                      </tr>
                    ))
                  ) : currentEmployees.length === 0 ? (
                    // Empty State
                    <tr>
                      <td colSpan={7} className="px-6 py-12 text-center text-slate-400 font-medium">
                        No employees found matching query.
                      </td>
                    </tr>
                  ) : (
                    // Live Employee Rows
                    currentEmployees.map((emp) => {
                      const isSelected = selectedEmpIds.includes(emp.employee_id);
                      const currentShiftName = shiftMap.get(emp.employee_id) || "Daily";

                      return (
                        <tr
                          key={emp.employee_id}
                          className={`hover:bg-slate-50/70 dark:hover:bg-slate-800/30 transition-colors border-b border-slate-100 dark:border-slate-800/60 align-middle ${
                            isSelected ? "bg-blue-50/30 dark:bg-blue-950/20" : ""
                          }`}
                        >
                          <td className="px-4 py-3.5 text-center">
                            <input
                              type="checkbox"
                              checked={isSelected}
                              onChange={() => handleSelectRow(emp.employee_id)}
                              className="h-4 w-4 rounded border-slate-300 dark:border-slate-700 text-[#0B85C9] focus:ring-[#0B85C9] cursor-pointer"
                            />
                          </td>
                          <td className="px-5 py-3.5 font-medium text-slate-600 dark:text-slate-400 whitespace-nowrap">
                            {emp.employee_code}
                          </td>
                          <td className="px-5 py-3.5 font-semibold text-slate-800 dark:text-slate-200 whitespace-nowrap">
                            {emp.employee_name}
                          </td>
                          <td className="px-5 py-3.5 font-medium text-slate-600 dark:text-slate-400 whitespace-nowrap">
                            {emp.department_name || "-"}
                          </td>
                          <td className="px-5 py-3.5 font-medium text-slate-600 dark:text-slate-400 whitespace-nowrap">
                            {emp.designation_name || "-"}
                          </td>
                          <td className="px-5 py-3.5 font-medium text-slate-600 dark:text-slate-400 whitespace-nowrap">
                            {emp.branch_name || "-"}
                          </td>
                          <td className="px-5 py-3.5 font-semibold text-slate-700 dark:text-slate-300 whitespace-nowrap">
                            <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300">
                              {currentShiftName}
                            </span>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            )}
          </div>

          {/* Pagination Footer */}
          <div className="p-4 border-t border-slate-200 dark:border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-4 bg-slate-50/20 dark:bg-slate-950/10">
            <div className="text-xs text-slate-500 font-medium">
              Showing{" "}
              <span className="font-semibold text-slate-800 dark:text-slate-200">
                {totalEmployees === 0 ? 0 : (currentPage - 1) * pageSize + 1}
              </span>{" "}
              to{" "}
              <span className="font-semibold text-slate-800 dark:text-slate-200">
                {Math.min(currentPage * pageSize, totalEmployees)}
              </span>{" "}
              of{" "}
              <span className="font-semibold text-slate-800 dark:text-slate-200">
                {totalEmployees}
              </span>{" "}
              Results
            </div>

            <div className="flex items-center gap-3">
              <div className="flex items-center gap-1.5">
                <span className="text-xs text-slate-400 font-medium uppercase tracking-wider">
                  Page Size:
                </span>
                <select
                  value={pageSize}
                  onChange={(e) => {
                    setPageSize(Number(e.target.value));
                    setCurrentPage(1);
                  }}
                  className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-md px-2 py-1 text-xs font-semibold text-slate-700 dark:text-slate-300 focus:outline-none"
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
                  disabled={currentPage === 1 || !employeesData?.pagination.has_previous}
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
                  onClick={() => setCurrentPage((prev) => prev + 1)}
                  disabled={!employeesData?.pagination.has_next}
                  className="h-8 px-2.5 text-xs text-slate-700 dark:text-slate-300 border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 hover:bg-slate-50 dark:hover:bg-slate-800/50"
                >
                  Next
                </Button>
              </div>
            </div>
          </div>
        </div>

        {/* CHOOSE SHIFT TO ASSIGN DRAWER */}
        {isDrawerOpen && (
          <div className="fixed inset-0 z-[100] flex justify-end">
            <div
              className="absolute inset-0 bg-black/40 backdrop-blur-[1px] transition-opacity"
              onClick={() => setIsDrawerOpen(false)}
            />
            
            <div className="relative w-full max-w-lg bg-white dark:bg-slate-900 h-full shadow-2xl flex flex-col justify-between z-10 animate-in slide-in-from-right duration-200">
              
              {/* Drawer Header */}
              <div className="px-6 py-4 border-b border-slate-200/80 dark:border-slate-800 flex items-center justify-between bg-[#F0F7FF] dark:bg-slate-950">
                <div>
                  <h2 className="text-base font-semibold text-slate-800 dark:text-slate-100">
                    Choose Shift To Assign
                  </h2>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Assigning shift to {selectedEmpIds.length} employee(s)
                  </p>
                </div>
                <button
                  onClick={() => setIsDrawerOpen(false)}
                  className="p-1 hover:bg-slate-200/60 dark:hover:bg-slate-800/60 rounded text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors focus:outline-none"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>

              {/* Drawer Content Body */}
              <div className="flex-1 overflow-y-auto p-6 space-y-6">
                
                {/* Effective Date Selection */}
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                    Effective From Date
                  </label>
                  <Input
                    type="date"
                    value={effectiveFrom}
                    onChange={(e) => setEffectiveFrom(e.target.value)}
                    className="h-9 text-xs w-full bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-800"
                  />
                </div>

                {/* Shift Options Table */}
                <div className="border border-slate-200/80 dark:border-slate-800 rounded-lg overflow-hidden bg-white dark:bg-slate-900">
                  <div className="bg-slate-50 dark:bg-slate-950/80 px-6 py-3 border-b border-slate-200/80 dark:border-slate-800 text-center font-bold text-xs text-slate-700 dark:text-slate-300">
                    Shift Name
                  </div>

                  <div className="divide-y divide-slate-100 dark:divide-slate-800 max-h-[380px] overflow-y-auto">
                    {isLoadingShifts ? (
                      <div className="p-8 text-center flex items-center justify-center gap-2 text-xs text-slate-500">
                        <Loader2 className="h-4 w-4 animate-spin text-[#0B85C9]" />
                        Loading available shifts...
                      </div>
                    ) : !shiftsData?.items || shiftsData.items.length === 0 ? (
                      <div className="p-6 text-center text-xs text-slate-400">
                        No active shifts available.
                      </div>
                    ) : (
                      shiftsData.items.map((shift: ShiftSummarySchema) => {
                        const isSelected = selectedShiftId === shift.shift_id;
                        return (
                          <div
                            key={shift.shift_id}
                            onClick={() => setSelectedShiftId(shift.shift_id)}
                            className={`px-6 py-4 flex items-center gap-6 cursor-pointer hover:bg-slate-50/80 dark:hover:bg-slate-800/40 transition-colors ${
                              isSelected ? "bg-blue-50/40 dark:bg-blue-950/20" : ""
                            }`}
                          >
                            <input
                              type="radio"
                              name="selected_shift"
                              checked={isSelected}
                              onChange={() => setSelectedShiftId(shift.shift_id)}
                              className="h-4 w-4 border-slate-300 text-[#0B85C9] focus:ring-[#0B85C9] cursor-pointer shrink-0"
                            />
                            <div className="flex flex-col">
                              <span className="text-xs font-semibold text-slate-800 dark:text-slate-200">
                                {shift.shift_name}
                              </span>
                              {shift.is_open_shift && (
                                <span className="text-[11px] text-slate-400 dark:text-slate-500 mt-0.5">
                                  Flexible timing based on punch
                                </span>
                              )}
                            </div>
                          </div>
                        );
                      })
                    )}
                  </div>
                </div>

              </div>

              {/* Drawer Footer */}
              <div className="px-6 py-4 border-t border-slate-200/80 dark:border-slate-800 bg-[#F0F7FF] dark:bg-slate-950 flex items-center justify-end gap-4">
                <button
                  type="button"
                  onClick={() => setIsDrawerOpen(false)}
                  className="text-xs font-semibold text-[#0B85C9] hover:underline cursor-pointer px-2 py-1"
                >
                  Close
                </button>
                <Button
                  variant="primary"
                  size="sm"
                  disabled={!selectedShiftId}
                  onClick={handleConfirmAssignment}
                  className="text-xs h-9 px-5 font-bold bg-[#0B85C9] hover:bg-[#0974b0] disabled:bg-slate-300 disabled:cursor-not-allowed text-white rounded-md shadow-xs border-0"
                >
                  Assign Shift
                </Button>
              </div>

            </div>
          </div>
        )}

        {/* CONFIRMATION DIALOG */}
        {isConfirmOpen && selectedShiftObj && (
          <div className="fixed inset-0 z-[120] flex items-center justify-center p-4">
            <div
              className="absolute inset-0 bg-black/50 backdrop-blur-[1px]"
              onClick={() => setIsConfirmOpen(false)}
            />
            <div className="relative w-full max-w-md bg-white dark:bg-slate-900 rounded-xl shadow-xl border border-slate-200 dark:border-slate-800 p-6 space-y-4 z-10 animate-in fade-in zoom-in-95 duration-150">
              <div className="flex items-center gap-3 text-slate-800 dark:text-slate-100 font-semibold text-base">
                <div className="p-2 bg-blue-50 dark:bg-blue-950/40 text-[#0B85C9] rounded-lg">
                  <Check className="h-5 w-5" />
                </div>
                Confirm Shift Assignment
              </div>
              <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
                Are you sure you want to assign shift{" "}
                <strong className="text-slate-800 dark:text-slate-200">{selectedShiftObj.shift_name}</strong> to{" "}
                <strong className="text-slate-800 dark:text-slate-200">{selectedEmpIds.length}</strong> selected employee(s) effective from{" "}
                <strong className="text-slate-800 dark:text-slate-200">{effectiveFrom}</strong>?
              </p>
              <div className="flex items-center justify-end gap-3 pt-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setIsConfirmOpen(false)}
                  disabled={bulkAssignMutation.isPending}
                  className="text-xs h-9 px-4"
                >
                  Cancel
                </Button>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={executeBulkAssign}
                  disabled={bulkAssignMutation.isPending}
                  className="text-xs h-9 px-5 font-bold bg-[#0B85C9] hover:bg-[#0974b0] text-white rounded-md border-0"
                >
                  {bulkAssignMutation.isPending ? (
                    <>
                      <Loader2 className="h-3.5 w-3.5 animate-spin mr-1.5" />
                      Assigning...
                    </>
                  ) : (
                    "Confirm & Assign"
                  )}
                </Button>
              </div>
            </div>
          </div>
        )}

      </div>
    </ProtectedRoute>
  );
}
