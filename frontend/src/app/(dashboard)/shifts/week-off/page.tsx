"use client";

import { useState, useEffect, useMemo } from "react";
import {
  ArrowUpDown,
  Search,
  Filter,
  ChevronLeft,
  X,
  AlertCircle,
  CheckCircle2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { toast } from "sonner";
import { useRouter } from "next/navigation";
import { isAxiosError } from "axios";
import { ProtectedRoute } from "@/features/auth";
import {
  useEmployees,
  useDepartmentOptions,
} from "@/features/employees/hooks";
import { EmployeeSummary, EmployeeSortBy, SortOrder } from "@/features/employees/types";
import {
  useEmployeeWeekoffs,
  useConfigureWeekoffs,
  useBulkWeekoffUpdate,
} from "@/features/shifts/hooks";
import { DayOfWeek, WeekoffType, WeeklyOffSchema } from "@/features/shifts/types";

const WEEKDAYS: { key: DayOfWeek; label: string }[] = [
  { key: 0, label: "Sunday" },
  { key: 1, label: "Monday" },
  { key: 2, label: "Tuesday" },
  { key: 3, label: "Wednesday" },
  { key: 4, label: "Thursday" },
  { key: 5, label: "Friday" },
  { key: 6, label: "Saturday" },
];

function getErrorMessage(err: unknown, fallback: string): string {
  if (isAxiosError(err)) {
    const data = err.response?.data as { message?: string; detail?: string } | undefined;
    return data?.message || data?.detail || fallback;
  }
  if (err instanceof Error) return err.message;
  return fallback;
}

function getWeekoffDisplayType(weekoff?: WeeklyOffSchema): WeekoffType {
  if (!weekoff) return "working";
  if (weekoff.weekoff_type === "working") return "working";

  const occs = [
    weekoff.occurrence_1st,
    weekoff.occurrence_2nd,
    weekoff.occurrence_3rd,
    weekoff.occurrence_4th,
    weekoff.occurrence_5th,
  ];
  const trueCount = occs.filter(Boolean).length;

  if (trueCount === 5) return "week_off";
  if (trueCount === 0) return "working";
  return "occasional_week_off";
}

function WeekOffSymbolIcon({ type }: { type: WeekoffType }) {
  if (type === "working") {
    return (
      <span
        title="Working Day"
        className="inline-flex items-center justify-center h-4 w-4 rounded-full bg-emerald-600 shrink-0 hover:scale-110 transition-transform cursor-pointer shadow-2xs"
      />
    );
  }
  if (type === "week_off") {
    return (
      <span
        title="WO Week Off"
        className="inline-flex items-center justify-center h-4 w-4 rounded-full bg-[#0B85C9] text-white text-[9px] font-bold shrink-0 hover:scale-110 transition-transform cursor-pointer shadow-2xs"
      >
        WO
      </span>
    );
  }
  return (
    <span
      title="Occasional Week Off"
      className="inline-flex items-center justify-center h-4 w-4 shrink-0 text-amber-500 text-xs font-bold leading-none hover:scale-110 transition-transform cursor-pointer"
    >
      ▲
    </span>
  );
}

// Sub-component for individual employee row to query week-offs via React Query
function EmployeeWeekoffTableRow({
  employee,
  isSelected,
  onSelectRow,
  onCellClick,
}: {
  employee: EmployeeSummary;
  isSelected: boolean;
  onSelectRow: (id: number) => void;
  onCellClick: (
    employeeId: number,
    employeeName: string,
    day: DayOfWeek,
    dayLabel: string,
    currentWeekoff?: WeeklyOffSchema
  ) => void;
}) {
  const { data: weekoffData, isLoading } = useEmployeeWeekoffs(employee.employee_id);

  const weekoffByDay = useMemo(() => {
    const map = new Map<DayOfWeek, WeeklyOffSchema>();
    if (weekoffData?.items) {
      weekoffData.items.forEach((item) => {
        map.set(item.day_of_week, item);
      });
    }
    return map;
  }, [weekoffData]);

  return (
    <tr
      className={`hover:bg-slate-50/80 dark:hover:bg-slate-800/40 transition-colors border-b border-slate-100 dark:border-slate-800/60 align-middle ${
        isSelected ? "bg-blue-50/40 dark:bg-blue-950/20" : ""
      }`}
    >
      <td className="px-4 py-3.5 text-center">
        <input
          type="checkbox"
          checked={isSelected}
          onChange={() => onSelectRow(employee.employee_id)}
          className="h-4 w-4 rounded border-slate-300 dark:border-slate-700 text-[#0B85C9] focus:ring-[#0B85C9] cursor-pointer"
        />
      </td>
      <td className="px-5 py-3.5 font-medium text-slate-600 dark:text-slate-400 whitespace-nowrap">
        {employee.employee_code || employee.employee_id}
      </td>
      <td className="px-5 py-3.5 font-semibold text-slate-800 dark:text-slate-200 whitespace-nowrap">
        {employee.employee_name}
      </td>
      <td className="px-5 py-3.5 font-medium text-slate-600 dark:text-slate-400 whitespace-nowrap">
        {employee.department_name || "-"}
      </td>
      {WEEKDAYS.map(({ key: day, label: dayLabel }) => {
        const item = weekoffByDay.get(day);
        const displayType = getWeekoffDisplayType(item);

        return (
          <td
            key={day}
            onClick={() =>
              onCellClick(
                employee.employee_id,
                employee.employee_name,
                day,
                dayLabel,
                item
              )
            }
            className="px-4 py-3.5 text-center select-none cursor-pointer hover:bg-blue-50/50 dark:hover:bg-slate-800/50 transition-colors"
          >
            <div className="flex items-center justify-center">
              {isLoading ? (
                <span className="h-3.5 w-3.5 rounded-full bg-slate-200 dark:bg-slate-700 animate-pulse" />
              ) : (
                <WeekOffSymbolIcon type={displayType} />
              )}
            </div>
          </td>
        );
      })}
    </tr>
  );
}

interface CellEditState {
  employeeId: number;
  employeeName: string;
  day: DayOfWeek;
  dayLabel: string;
  occurrence_1st: boolean;
  occurrence_2nd: boolean;
  occurrence_3rd: boolean;
  occurrence_4th: boolean;
  occurrence_5th: boolean;
}

export default function WeekOffPage() {
  const router = useRouter();

  // Search & Debounce
  const [searchInput, setSearchInput] = useState<string>("");
  const [debouncedSearch, setDebouncedSearch] = useState<string>("");

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchInput);
    }, 400);
    return () => clearTimeout(timer);
  }, [searchInput]);

  // Filters & Sorting
  const [selectedDeptId, setSelectedDeptId] = useState<number | undefined>(undefined);
  const [sortField, setSortField] = useState<EmployeeSortBy>("employee_code");
  const [sortOrder, setSortOrder] = useState<SortOrder>("desc");

  // Pagination
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(10);

  // Selection
  const [selectedEmpIds, setSelectedEmpIds] = useState<number[]>([]);

  // Success alert message banner state
  const [successBanner, setSuccessBanner] = useState<string | null>(null);

  // Cell Edit Modal state (Select Week Off Modal)
  const [cellEditState, setCellEditState] = useState<CellEditState | null>(null);

  // Bulk Modal state
  const [isBulkModalOpen, setIsBulkModalOpen] = useState<boolean>(false);
  const [bulkDay, setBulkDay] = useState<DayOfWeek>(0);
  const [bulkOcc1, setBulkOcc1] = useState<boolean>(true);
  const [bulkOcc2, setBulkOcc2] = useState<boolean>(true);
  const [bulkOcc3, setBulkOcc3] = useState<boolean>(true);
  const [bulkOcc4, setBulkOcc4] = useState<boolean>(true);
  const [bulkOcc5, setBulkOcc5] = useState<boolean>(true);

  // React Query Hooks
  const { data: departmentOptions = [] } = useDepartmentOptions();

  const {
    data: employeesData,
    isLoading: isEmployeesLoading,
    isError: isEmployeesError,
    error: employeesError,
  } = useEmployees({
    page: currentPage,
    page_size: pageSize,
    q: debouncedSearch.trim() || undefined,
    department_id: selectedDeptId,
    sort_by: sortField,
    sort_order: sortOrder,
    status: "active",
  });

  const configureMutation = useConfigureWeekoffs();
  const bulkUpdateMutation = useBulkWeekoffUpdate();

  const employees = useMemo(() => employeesData?.items || [], [employeesData]);
  const pagination = employeesData?.pagination;
  const totalRecords = pagination?.total_records || 0;
  const totalPages = pagination?.total_pages || 1;

  const currentPageEmpIds = useMemo(
    () => employees.map((e) => e.employee_id),
    [employees]
  );

  const isAllOnPageSelected =
    currentPageEmpIds.length > 0 &&
    currentPageEmpIds.every((id) => selectedEmpIds.includes(id));

  const handleSelectAll = () => {
    if (isAllOnPageSelected) {
      setSelectedEmpIds((prev) =>
        prev.filter((id) => !currentPageEmpIds.includes(id))
      );
    } else {
      setSelectedEmpIds((prev) =>
        Array.from(new Set([...prev, ...currentPageEmpIds]))
      );
    }
  };

  const handleSelectRow = (empId: number) => {
    setSelectedEmpIds((prev) =>
      prev.includes(empId) ? prev.filter((id) => id !== empId) : [...prev, empId]
    );
  };

  const handleSort = (field: EmployeeSortBy) => {
    if (sortField === field) {
      setSortOrder((prev) => (prev === "asc" ? "desc" : "asc"));
    } else {
      setSortField(field);
      setSortOrder("asc");
    }
  };

  // Open Popover/Modal for cell click
  const handleCellClick = (
    employeeId: number,
    employeeName: string,
    day: DayOfWeek,
    dayLabel: string,
    currentWeekoff?: WeeklyOffSchema
  ) => {
    const isWorking = !currentWeekoff || currentWeekoff.weekoff_type === "working";
    setCellEditState({
      employeeId,
      employeeName,
      day,
      dayLabel,
      occurrence_1st: isWorking ? true : currentWeekoff.occurrence_1st,
      occurrence_2nd: isWorking ? true : currentWeekoff.occurrence_2nd,
      occurrence_3rd: isWorking ? true : currentWeekoff.occurrence_3rd,
      occurrence_4th: isWorking ? true : currentWeekoff.occurrence_4th,
      occurrence_5th: isWorking ? true : currentWeekoff.occurrence_5th,
    });
  };

  // Apply cell popover changes
  const handleApplyCellChanges = () => {
    if (!cellEditState) return;

    const {
      employeeId,
      day,
      occurrence_1st,
      occurrence_2nd,
      occurrence_3rd,
      occurrence_4th,
      occurrence_5th,
    } = cellEditState;

    const trueCount = [
      occurrence_1st,
      occurrence_2nd,
      occurrence_3rd,
      occurrence_4th,
      occurrence_5th,
    ].filter(Boolean).length;

    let weekoff_type: WeekoffType = "working";
    if (trueCount === 5) {
      weekoff_type = "week_off";
    } else if (trueCount > 0) {
      weekoff_type = "occasional_week_off";
    }

    configureMutation.mutate(
      {
        employeeId,
        data: {
          weekoffs: [
            {
              day_of_week: day,
              weekoff_type,
              occurrence_1st,
              occurrence_2nd,
              occurrence_3rd,
              occurrence_4th,
              occurrence_5th,
            },
          ],
        },
      },
      {
        onSuccess: () => {
          const bannerMsg = "Employee Weekoff Saved Successfully";
          toast.success(bannerMsg);
          setSuccessBanner(bannerMsg);
          setCellEditState(null);
          setTimeout(() => setSuccessBanner(null), 5000);
        },
        onError: (err: unknown) => {
          toast.error(getErrorMessage(err, "Failed to update employee week off."));
        },
      }
    );
  };

  // Bulk update handler
  const handleBulkUpdate = () => {
    if (selectedEmpIds.length === 0) return;

    const trueCount = [
      bulkOcc1,
      bulkOcc2,
      bulkOcc3,
      bulkOcc4,
      bulkOcc5,
    ].filter(Boolean).length;

    let weekoff_type: WeekoffType = "working";
    if (trueCount === 5) {
      weekoff_type = "week_off";
    } else if (trueCount > 0) {
      weekoff_type = "occasional_week_off";
    }

    bulkUpdateMutation.mutate(
      {
        employeeIds: selectedEmpIds,
        weekoffs: [
          {
            day_of_week: bulkDay,
            weekoff_type,
            occurrence_1st: bulkOcc1,
            occurrence_2nd: bulkOcc2,
            occurrence_3rd: bulkOcc3,
            occurrence_4th: bulkOcc4,
            occurrence_5th: bulkOcc5,
          },
        ],
      },
      {
        onSuccess: () => {
          const bannerMsg = "Employee Weekoff Saved Successfully";
          toast.success(bannerMsg);
          setSuccessBanner(bannerMsg);
          setIsBulkModalOpen(false);
          setSelectedEmpIds([]);
          setTimeout(() => setSuccessBanner(null), 5000);
        },
        onError: (err: unknown) => {
          toast.error(getErrorMessage(err, "Failed to execute bulk week off update."));
        },
      }
    );
  };

  return (
    <ProtectedRoute requiredPermission={{ feature: "weekoff", action: "read" }}>
      <div className="p-6 space-y-5 bg-slate-50/40 min-h-screen relative">
        {/* Success Alert Banner (matching screenshot top-right banner) */}
        {successBanner && (
          <div className="fixed top-5 right-5 z-[200] flex items-center justify-between gap-3 px-4 py-3 bg-emerald-50 border border-emerald-300 text-emerald-800 rounded-lg shadow-lg animate-in fade-in slide-in-from-top-2 duration-200 max-w-md">
            <div className="flex items-center gap-2 text-xs font-semibold">
              <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0" />
              <span>{successBanner}</span>
            </div>
            <button
              onClick={() => setSuccessBanner(null)}
              className="p-1 hover:bg-emerald-100 rounded text-emerald-600 transition-colors"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
        )}

        {/* Page Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <button
                onClick={() => router.push("/shifts")}
                className="p-1 hover:bg-slate-200/60 dark:hover:bg-slate-800/60 rounded-lg text-slate-700 dark:text-slate-200 transition-colors cursor-pointer"
              >
                <ChevronLeft className="h-5 w-5" />
              </button>
              <h1 className="text-xl font-bold text-slate-800 dark:text-slate-100">
                Assign Week Off
              </h1>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 font-medium pl-8">
              Click on the cell icon to handle week offs (WO)
            </p>
          </div>

          {/* Top Right Action & Legend Section */}
          <div className="flex flex-wrap items-center gap-3">
            <Button
              variant="outline"
              size="sm"
              disabled={selectedEmpIds.length === 0}
              onClick={() => setIsBulkModalOpen(true)}
              className="h-9 px-4 text-xs font-semibold bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300 disabled:opacity-50 disabled:cursor-not-allowed shadow-2xs"
            >
              Bulk Update {selectedEmpIds.length > 0 && `(${selectedEmpIds.length})`}
            </Button>

            {/* Legend Box matching UI spec with identical symbol heights */}
            <div className="flex items-center gap-3 px-3.5 py-1.5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg shadow-2xs text-xs font-medium text-slate-700 dark:text-slate-300">
              <div className="flex items-center gap-1.5">
                <WeekOffSymbolIcon type="week_off" />
                <span>WO Week Off</span>
              </div>
              <span className="text-slate-300 dark:text-slate-700">|</span>
              <div className="flex items-center gap-1.5">
                <WeekOffSymbolIcon type="working" />
                <span>Working Day</span>
              </div>
              <span className="text-slate-300 dark:text-slate-700">|</span>
              <div className="flex items-center gap-1.5">
                <WeekOffSymbolIcon type="occasional_week_off" />
                <span>Occasional Week Off</span>
              </div>
            </div>
          </div>
        </div>

        {/* Filter and Table Card */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 rounded-xl shadow-xs overflow-hidden">
          
          {/* Search & Filter Toolbar */}
          <div className="p-4 border-b border-slate-200/80 dark:border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-4 bg-slate-50/45 dark:bg-slate-950/20">
            <div className="relative w-full sm:max-w-xs shrink-0">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400 dark:text-slate-500" />
              <Input
                type="text"
                placeholder="Search employee..."
                value={searchInput}
                onChange={(e) => {
                  setSearchInput(e.target.value);
                  setCurrentPage(1);
                }}
                className="pl-9 h-9 text-xs w-full bg-white dark:bg-slate-950 text-slate-800 dark:text-slate-100 placeholder:text-slate-400 border border-slate-200 dark:border-slate-800"
              />
            </div>

            <div className="flex items-center gap-3 w-full sm:w-auto justify-end">
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-500 dark:text-slate-400 font-medium">
                  Department:
                </span>
                <select
                  value={selectedDeptId ?? "All"}
                  onChange={(e) => {
                    const val = e.target.value;
                    setSelectedDeptId(val === "All" ? undefined : Number(val));
                    setCurrentPage(1);
                  }}
                  className="h-9 px-3 text-xs bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-md text-slate-700 dark:text-slate-300 focus:outline-none"
                >
                  <option value="All">All Departments</option>
                  {departmentOptions.map((dept) => (
                    <option key={dept.dept_id} value={dept.dept_id}>
                      {dept.dept_name}
                    </option>
                  ))}
                </select>
              </div>

              {(searchInput || selectedDeptId !== undefined) && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setSearchInput("");
                    setSelectedDeptId(undefined);
                    setCurrentPage(1);
                  }}
                  className="h-9 px-3 text-xs text-slate-600 border-slate-200"
                >
                  <Filter className="h-3.5 w-3.5 mr-1" />
                  Reset
                </Button>
              )}
            </div>
          </div>

          {/* Table */}
          <div className="w-full overflow-x-auto relative min-h-[320px]">
            <table className="w-full text-left border-collapse text-xs">
              <thead className="bg-[#EBF5FF] dark:bg-slate-950/80 border-b border-slate-200/80 dark:border-slate-800 text-[11px] tracking-wider text-slate-700 dark:text-slate-300 font-bold sticky top-0 z-10">
                <tr>
                  <th className="px-4 py-3.5 w-12 text-center">
                    <input
                      type="checkbox"
                      checked={isAllOnPageSelected}
                      onChange={handleSelectAll}
                      className="h-4 w-4 rounded border-slate-300 dark:border-slate-700 text-[#0B85C9] focus:ring-[#0B85C9] cursor-pointer"
                    />
                  </th>
                  <th
                    onClick={() => handleSort("employee_code")}
                    className="px-5 py-3.5 font-bold text-slate-700 dark:text-slate-300 cursor-pointer hover:text-slate-900 select-none whitespace-nowrap"
                  >
                    <div className="flex items-center gap-1">
                      Employee ID
                      <ArrowUpDown className="h-3 w-3 text-slate-400" />
                    </div>
                  </th>
                  <th
                    onClick={() => handleSort("employee_name")}
                    className="px-5 py-3.5 font-bold text-slate-700 dark:text-slate-300 cursor-pointer hover:text-slate-900 select-none whitespace-nowrap"
                  >
                    <div className="flex items-center gap-1">
                      Employee Name
                      <ArrowUpDown className="h-3 w-3 text-slate-400" />
                    </div>
                  </th>
                  <th className="px-5 py-3.5 font-bold text-slate-700 dark:text-slate-300 whitespace-nowrap">
                    <div className="flex items-center gap-1">
                      Department
                      <ArrowUpDown className="h-3 w-3 text-slate-400" />
                    </div>
                  </th>
                  {WEEKDAYS.map(({ key, label }) => (
                    <th key={key} className="px-4 py-3.5 text-center font-bold text-slate-700 dark:text-slate-300">
                      {label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800/65">
                {isEmployeesLoading ? (
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
                      {WEEKDAYS.map(({ key }) => (
                        <td key={key} className="px-4 py-3.5 text-center">
                          <div className="h-3.5 w-3.5 bg-slate-200 dark:bg-slate-800 rounded-full mx-auto" />
                        </td>
                      ))}
                    </tr>
                  ))
                ) : isEmployeesError ? (
                  <tr>
                    <td colSpan={11} className="px-6 py-12 text-center text-rose-500 font-medium">
                      <div className="flex flex-col items-center justify-center space-y-2">
                        <AlertCircle className="h-8 w-8 text-rose-400" />
                        <span>{getErrorMessage(employeesError, "Failed to load employees.")}</span>
                      </div>
                    </td>
                  </tr>
                ) : employees.length === 0 ? (
                  <tr>
                    <td colSpan={11} className="px-6 py-12 text-center text-slate-400 font-medium">
                      <div className="flex flex-col items-center justify-center space-y-2">
                        <AlertCircle className="h-8 w-8 text-slate-300 dark:text-slate-600" />
                        <span>No employees found matching filter criteria.</span>
                      </div>
                    </td>
                  </tr>
                ) : (
                  employees.map((emp) => (
                    <EmployeeWeekoffTableRow
                      key={emp.employee_id}
                      employee={emp}
                      isSelected={selectedEmpIds.includes(emp.employee_id)}
                      onSelectRow={handleSelectRow}
                      onCellClick={handleCellClick}
                    />
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination Footer */}
          <div className="p-4 border-t border-slate-200 dark:border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-4 bg-slate-50/20 dark:bg-slate-950/10">
            <div className="text-xs text-slate-500 font-medium">
              Showing{" "}
              <span className="font-semibold text-slate-800 dark:text-slate-200">
                {totalRecords === 0 ? 0 : (currentPage - 1) * pageSize + 1}
              </span>{" "}
              to{" "}
              <span className="font-semibold text-slate-800 dark:text-slate-200">
                {Math.min(currentPage * pageSize, totalRecords)}
              </span>{" "}
              of{" "}
              <span className="font-semibold text-slate-800 dark:text-slate-200">
                {totalRecords}
              </span>{" "}
              Results
            </div>

            <div className="flex items-center gap-3">
              <div className="flex items-center gap-1.5">
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
                  disabled={currentPage === 1 || totalPages <= 1}
                  className="h-8 px-2.5 text-xs text-slate-700 dark:text-slate-300 border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 hover:bg-slate-50 dark:hover:bg-slate-800/50"
                >
                  Previous
                </Button>
                {Array.from({ length: totalPages }).map((_, idx) => {
                  const pNum = idx + 1;
                  return (
                    <button
                      key={pNum}
                      onClick={() => setCurrentPage(pNum)}
                      className={`h-8 w-8 text-xs font-bold rounded-md transition-colors ${
                        currentPage === pNum
                          ? "bg-[#0B85C9] text-white"
                          : "bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-50"
                      }`}
                    >
                      {pNum}
                    </button>
                  );
                })}
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

        {/* SELECT WEEK OFF POPOVER MODAL (Matches user screenshot popover) */}
        {cellEditState && (
          <div className="fixed inset-0 z-[150] flex items-center justify-center p-4">
            <div
              className="absolute inset-0 bg-black/40 backdrop-blur-[1px]"
              onClick={() => setCellEditState(null)}
            />
            <div className="relative w-full max-w-sm bg-white dark:bg-slate-900 rounded-xl shadow-2xl border border-slate-200 dark:border-slate-800 p-5 space-y-4 z-10 animate-in fade-in zoom-in-95 duration-150">
              
              {/* Modal Header */}
              <h3 className="text-sm font-bold text-slate-800 dark:text-slate-100">
                Select Week Off ({cellEditState.dayLabel})
              </h3>

              {/* Grid with 1st, 2nd, 3rd, 4th, 5th occurrence headers and checkboxes */}
              <div className="border border-slate-200 dark:border-slate-800 rounded-lg overflow-hidden text-xs">
                <div className="grid grid-cols-5 bg-slate-50 dark:bg-slate-800/60 border-b border-slate-200 dark:border-slate-800 text-center py-2 font-bold text-slate-700 dark:text-slate-300">
                  <div>1<sup>st</sup></div>
                  <div>2<sup>nd</sup></div>
                  <div>3<sup>rd</sup></div>
                  <div>4<sup>th</sup></div>
                  <div>5<sup>th</sup></div>
                </div>
                <div className="grid grid-cols-5 py-3.5 bg-white dark:bg-slate-900 text-center items-center">
                  {[
                    { key: "occurrence_1st" as const },
                    { key: "occurrence_2nd" as const },
                    { key: "occurrence_3rd" as const },
                    { key: "occurrence_4th" as const },
                    { key: "occurrence_5th" as const },
                  ].map((occ) => (
                    <div key={occ.key} className="flex justify-center">
                      <input
                        type="checkbox"
                        checked={cellEditState[occ.key]}
                        onChange={(e) =>
                          setCellEditState((prev) =>
                            prev ? { ...prev, [occ.key]: e.target.checked } : null
                          )
                        }
                        className="h-4 w-4 rounded border-slate-300 dark:border-slate-700 text-[#0B85C9] focus:ring-[#0B85C9] cursor-pointer"
                      />
                    </div>
                  ))}
                </div>
              </div>

              {/* Modal Actions */}
              <div className="flex items-center justify-end gap-2.5 pt-1">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCellEditState(null)}
                  className="h-8 text-xs px-4 text-slate-700 dark:text-slate-300 border-slate-300 dark:border-slate-700"
                >
                  Cancel
                </Button>
                <Button
                  variant="primary"
                  size="sm"
                  disabled={configureMutation.isPending}
                  onClick={handleApplyCellChanges}
                  className="h-8 text-xs px-4 font-bold bg-[#0B85C9] hover:bg-[#0974b0] text-white border-0 shadow-xs disabled:opacity-50"
                >
                  {configureMutation.isPending ? "Applying..." : "Apply Changes"}
                </Button>
              </div>

            </div>
          </div>
        )}

        {/* BULK UPDATE MODAL */}
        {isBulkModalOpen && (
          <div className="fixed inset-0 z-[140] flex items-center justify-center p-4">
            <div
              className="absolute inset-0 bg-black/50 backdrop-blur-[1px]"
              onClick={() => setIsBulkModalOpen(false)}
            />
            <div className="relative w-full max-w-md bg-white dark:bg-slate-900 rounded-xl shadow-xl border border-slate-200 dark:border-slate-800 p-6 space-y-5 z-10 animate-in fade-in zoom-in-95 duration-150">
              
              {/* Modal Header */}
              <div className="flex items-center justify-between pb-3 border-b border-slate-200 dark:border-slate-800">
                <h3 className="text-base font-bold text-slate-800 dark:text-slate-100">
                  Bulk Update Week Off
                </h3>
                <button
                  onClick={() => setIsBulkModalOpen(false)}
                  className="p-1 hover:bg-slate-100 dark:hover:bg-slate-800 rounded text-slate-400 hover:text-slate-600 transition-colors"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              {/* Form Controls */}
              <div className="space-y-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                    Select Weekday
                  </label>
                  <select
                    value={bulkDay}
                    onChange={(e) => setBulkDay(Number(e.target.value) as DayOfWeek)}
                    className="w-full h-9 px-3 text-xs bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-md text-slate-800 dark:text-slate-200 focus:outline-none"
                  >
                    {WEEKDAYS.map(({ key, label }) => (
                      <option key={key} value={key}>
                        {label}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                    Select Week Off Occurrences
                  </label>
                  <div className="border border-slate-200 dark:border-slate-800 rounded-lg overflow-hidden text-xs">
                    <div className="grid grid-cols-5 bg-slate-50 dark:bg-slate-800/60 border-b border-slate-200 dark:border-slate-800 text-center py-2 font-bold text-slate-700 dark:text-slate-300">
                      <div>1<sup>st</sup></div>
                      <div>2<sup>nd</sup></div>
                      <div>3<sup>rd</sup></div>
                      <div>4<sup>th</sup></div>
                      <div>5<sup>th</sup></div>
                    </div>
                    <div className="grid grid-cols-5 py-3 bg-white dark:bg-slate-900 text-center items-center">
                      {[
                        { val: bulkOcc1, setVal: setBulkOcc1 },
                        { val: bulkOcc2, setVal: setBulkOcc2 },
                        { val: bulkOcc3, setVal: setBulkOcc3 },
                        { val: bulkOcc4, setVal: setBulkOcc4 },
                        { val: bulkOcc5, setVal: setBulkOcc5 },
                      ].map((item, idx) => (
                        <div key={idx} className="flex justify-center">
                          <input
                            type="checkbox"
                            checked={item.val}
                            onChange={(e) => item.setVal(e.target.checked)}
                            className="h-4 w-4 rounded border-slate-300 dark:border-slate-700 text-[#0B85C9] focus:ring-[#0B85C9] cursor-pointer"
                          />
                        </div>
                      ))}
                    </div>
                  </div>
                  <div className="flex items-center gap-2 pt-1">
                    <button
                      type="button"
                      onClick={() => {
                        setBulkOcc1(true);
                        setBulkOcc2(true);
                        setBulkOcc3(true);
                        setBulkOcc4(true);
                        setBulkOcc5(true);
                      }}
                      className="text-[11px] text-[#0B85C9] hover:underline font-medium cursor-pointer"
                    >
                      Check All
                    </button>
                    <span className="text-slate-300">|</span>
                    <button
                      type="button"
                      onClick={() => {
                        setBulkOcc1(false);
                        setBulkOcc2(false);
                        setBulkOcc3(false);
                        setBulkOcc4(false);
                        setBulkOcc5(false);
                      }}
                      className="text-[11px] text-slate-500 hover:underline font-medium cursor-pointer"
                    >
                      Clear All
                    </button>
                  </div>
                </div>

                <p className="text-[11px] text-slate-500 dark:text-slate-400">
                  This will update <strong>{selectedEmpIds.length}</strong> selected employee(s).
                </p>
              </div>

              {/* Footer Actions */}
              <div className="flex items-center justify-end gap-3 pt-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setIsBulkModalOpen(false)}
                  className="text-xs h-9 px-4"
                >
                  Cancel
                </Button>
                <Button
                  variant="primary"
                  size="sm"
                  disabled={bulkUpdateMutation.isPending}
                  onClick={handleBulkUpdate}
                  className="text-xs h-9 px-5 font-bold bg-[#0B85C9] hover:bg-[#0974b0] text-white rounded-md border-0 disabled:opacity-50"
                >
                  {bulkUpdateMutation.isPending ? "Updating..." : "Apply Changes"}
                </Button>
              </div>

            </div>
          </div>
        )}

      </div>
    </ProtectedRoute>
  );
}
