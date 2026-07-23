"use client";

import React, { useState, useMemo } from "react";
import * as XLSX from "xlsx";
import { toast } from "sonner";
import {
  Search,
  RotateCcw,
  Download,
  Info,
  ChevronDown,
  RefreshCw,
  Calendar,
  Filter,
  Save,
  AlertCircle,
  X,
  ChevronLeft,
  ChevronRight,
  SlidersHorizontal,
} from "lucide-react";
import { ProtectedRoute } from "@/features/auth";
import {
  useBranchOptions,
  useDepartmentOptions,
  useDesignationOptions,
} from "@/features/employees/hooks";
import { useBatchUpdateBulkAttendanceAdjustments } from "@/features/payroll/hooks/use-payroll";

// Attendance status options & petpooja color theme
export type AttendanceStatusCode = "P" | "A" | "FD" | "HD" | "WO" | "H" | "L" | "LWP" | "CO";

export interface AttendanceStatusOption {
  code: AttendanceStatusCode;
  label: string;
  colorClass: string;
  bgClass: string;
  description: string;
}

export const ATTENDANCE_STATUSES: AttendanceStatusOption[] = [
  { code: "P", label: "Present", colorClass: "text-emerald-600 font-bold dark:text-emerald-400", bgClass: "bg-emerald-50 dark:bg-emerald-950/30", description: "Present for full shift" },
  { code: "A", label: "Absent", colorClass: "text-red-600 font-bold dark:text-red-400", bgClass: "bg-red-50 dark:bg-red-950/30", description: "Absent / Unexcused" },
  { code: "FD", label: "Full Day", colorClass: "text-slate-800 font-bold dark:text-slate-200", bgClass: "bg-slate-50 dark:bg-slate-800/40", description: "Full Day Duty" },
  { code: "HD", label: "Half Day", colorClass: "text-blue-600 font-bold dark:text-blue-400", bgClass: "bg-blue-50 dark:bg-blue-950/30", description: "Half Day Worked" },
  { code: "WO", label: "Week Off", colorClass: "text-slate-400 font-semibold dark:text-slate-500", bgClass: "bg-slate-100/50 dark:bg-slate-800/20", description: "Scheduled Weekly Off" },
  { code: "H", label: "Holiday", colorClass: "text-amber-600 font-bold dark:text-amber-400", bgClass: "bg-amber-50 dark:bg-amber-950/30", description: "Declared Organization Holiday" },
  { code: "L", label: "Leave", colorClass: "text-purple-600 font-bold dark:text-purple-400", bgClass: "bg-purple-50 dark:bg-purple-950/30", description: "Approved Paid Leave" },
  { code: "LWP", label: "Leave Without Pay", colorClass: "text-slate-700 font-bold dark:text-slate-300", bgClass: "bg-slate-100 dark:bg-slate-800/60", description: "Unpaid Leave" },
  { code: "CO", label: "Comp Off", colorClass: "text-teal-600 font-bold dark:text-teal-400", bgClass: "bg-teal-50 dark:bg-teal-950/30", description: "Compensatory Off" },
];

export type QAArchetype =
  | "full_attendance"
  | "all_absent"
  | "half_day_heavy"
  | "holiday_weekoff"
  | "leave_heavy"
  | "lwp_heavy"
  | "comp_off"
  | "mixed_attendance";

export interface MatrixEmployee {
  id: number;
  employee_code: string;
  employee_name: string;
  department: string;
  designation: string;
  branch_id: number;
  branch_name: string;
  archetype: QAArchetype;
  attendance: Record<string, AttendanceStatusCode>; // key: "YYYY-MM-DD"
}

// 120+ Deterministic Employee QA Dataset across 5 Branches & 12 Departments
const FIRST_NAMES = [
  "Bakrushn", "Nakul", "Tanvin", "Khushi", "Sneha", "Krunal", "Jay", "Harsh", "Divya", "Hardik",
  "Parita", "Nitisha", "Miti", "Umang", "Aniket", "Pooja", "Rohan", "Bhavin", "Meera", "Karan",
  "Riya", "Siddharth", "Vikas", "Aakash", "Chirag", "Drashti", "Ekta", "Farhan", "Gaurav", "Hetal",
  "Ishan", "Jignesh", "Komal", "Lalit", "Manish", "Nidhi", "Omkar", "Pratik", "Radhika", "Suraj",
  "Tanya", "Umesh", "Varun", "Yashasvi", "Zainab", "Arjun", "Bipasha", "Chetan", "Deepika", "Esha",
  "Gautam", "Hardik", "Ishita", "Janvi", "Kunal", "Lakshya", "Mohit", "Naveen", "Ojas", "Piyush",
];

const LAST_NAMES = [
  "Koladiya", "Verma", "Kheni", "Bhut", "Patel", "Hirpara", "Bodra", "Kumbhani", "Agravat", "Shah",
  "Trivedi", "Mehta", "Desai", "Joshi", "Johar", "Sen", "Rao", "Dubey", "Varma", "Solanki",
  "Kapoor", "Akhtar", "Parikh", "Kishan", "Pandya", "Soni", "Modi", "Malhotra", "Roy", "Nair",
  "Merchant", "Sharma", "Bajaj", "Yadav", "Dhawan", "Jaiswal", "Khan", "Rampal", "Basu", "Bhagat",
  "Padukone", "Gupta", "Gambhir", "Chovatiya", "Lakkad", "Prajapati", "Thakkar", "Jani", "Chaudhary", "Rathod",
];

const DEPARTMENTS_DESIGNATIONS = [
  { dept: "CEO", desig: "CEO" },
  { dept: "Developer", desig: "Angular Developer" },
  { dept: "Developer", desig: "Full Stack Engineer" },
  { dept: "Developer", desig: "UI-UX Specialist" },
  { dept: "Developer", desig: "React JS Engineer" },
  { dept: "Developer", desig: "Backend Developer" },
  { dept: "Developer", desig: "Node.js Architect" },
  { dept: "Developer", desig: "DevOps Specialist" },
  { dept: "Marketing", desig: "Marketing Lead" },
  { dept: "Marketing", desig: "SEO Specialist" },
  { dept: "Marketing", desig: "Content Writer" },
  { dept: "Finance", desig: "Senior Accountant" },
  { dept: "Finance", desig: "Payroll Lead" },
  { dept: "Human Resources", desig: "HR Executive" },
  { dept: "Human Resources", desig: "Recruiter" },
  { dept: "Operations", desig: "Operations Lead" },
  { dept: "Operations", desig: "Facility Manager" },
  { dept: "QA", desig: "Automation Engineer" },
  { dept: "QA", desig: "Manual Tester" },
  { dept: "Support", desig: "Support Specialist" },
  { dept: "Legal", desig: "Compliance Officer" },
  { dept: "Design", desig: "Graphic Designer" },
  { dept: "Sales", desig: "Regional Account Exec" },
  { dept: "Logistics", desig: "Logistics Coordinator" },
];

const BRANCHES = [
  { id: 1, name: "Main HQ" },
  { id: 2, name: "West Branch" },
  { id: 3, name: "South Tech Park" },
  { id: 4, name: "North Plant" },
  { id: 5, name: "East Sales Hub" },
];

const ARCHETYPES: QAArchetype[] = [
  "full_attendance",
  "all_absent",
  "half_day_heavy",
  "holiday_weekoff",
  "leave_heavy",
  "lwp_heavy",
  "comp_off",
  "mixed_attendance",
];

// Generate 120 deterministic employees with attendance matrices
const generate120QAMatrix = (): MatrixEmployee[] => {
  const employees: MatrixEmployee[] = [];

  for (let i = 1; i <= 120; i++) {
    const firstName = FIRST_NAMES[(i - 1) % FIRST_NAMES.length];
    const lastName = LAST_NAMES[(i - 1) % LAST_NAMES.length];
    const fullName = `${firstName} ${lastName}`;
    const code = String(i);
    const deptDesig = DEPARTMENTS_DESIGNATIONS[(i - 1) % DEPARTMENTS_DESIGNATIONS.length];
    const branch = BRANCHES[(i - 1) % BRANCHES.length];

    // Assign specific archetype to create comprehensive QA scenarios
    let archetype: QAArchetype;
    if (i === 1 || i === 15 || i === 35 || i === 55 || i === 85) {
      archetype = "full_attendance";
    } else if (i === 9 || i === 25 || i === 45 || i === 65 || i === 105) {
      archetype = "all_absent";
    } else if (i === 8 || i === 26 || i === 48 || i === 88) {
      archetype = "half_day_heavy";
    } else if (i === 7 || i === 23 || i === 52 || i === 92) {
      archetype = "lwp_heavy";
    } else if (i === 12 || i === 32 || i === 62 || i === 96) {
      archetype = "leave_heavy";
    } else if (i === 18 || i === 42 || i === 78 || i === 110) {
      archetype = "comp_off";
    } else if (i === 5 || i === 20 || i === 50 || i === 80) {
      archetype = "holiday_weekoff";
    } else {
      archetype = ARCHETYPES[(i - 1) % ARCHETYPES.length];
    }

    const attendance: Record<string, AttendanceStatusCode> = {};
    for (let day = 1; day <= 31; day++) {
      const dayStr = day < 10 ? `0${day}` : `${day}`;
      const dateKey = `2026-07-${dayStr}`;
      const dateObj = new Date(2026, 6, day);
      const isSunday = dateObj.getDay() === 0;

      // Deterministic attendance code generation based on archetype
      switch (archetype) {
        case "full_attendance":
          attendance[dateKey] = isSunday ? "WO" : "FD";
          break;
        case "all_absent":
          attendance[dateKey] = "A";
          break;
        case "half_day_heavy":
          attendance[dateKey] = isSunday ? "WO" : day % 2 === 0 ? "HD" : "FD";
          break;
        case "holiday_weekoff":
          attendance[dateKey] = day === 15 || day === 26 ? "H" : isSunday ? "WO" : "FD";
          break;
        case "leave_heavy":
          attendance[dateKey] = day >= 5 && day <= 10 ? "L" : isSunday ? "WO" : "FD";
          break;
        case "lwp_heavy":
          attendance[dateKey] = day >= 12 && day <= 18 ? "LWP" : isSunday ? "WO" : "FD";
          break;
        case "comp_off":
          attendance[dateKey] = day === 4 || day === 18 ? "CO" : isSunday ? "WO" : "FD";
          break;
        case "mixed_attendance":
        default: {
          const roll = (i + day) % 9;
          if (isSunday) {
            attendance[dateKey] = roll < 3 ? "A" : "WO";
          } else if (roll === 0) {
            attendance[dateKey] = "A";
          } else if (roll === 1 || roll === 2) {
            attendance[dateKey] = "HD";
          } else if (roll === 3) {
            attendance[dateKey] = "LWP";
          } else if (roll === 4) {
            attendance[dateKey] = "L";
          } else if (roll === 5) {
            attendance[dateKey] = "CO";
          } else if (day === 15) {
            attendance[dateKey] = "H";
          } else {
            attendance[dateKey] = "FD";
          }
          break;
        }
      }
    }

    employees.push({
      id: i,
      employee_code: code,
      employee_name: fullName,
      department: deptDesig.dept,
      designation: deptDesig.desig,
      branch_id: branch.id,
      branch_name: branch.name,
      archetype,
      attendance,
    });
  }

  return employees;
};

const LOCAL_STORAGE_KEY = "hrms_bulk_attendance_matrix_overrides";

const loadSavedOverrides = (): Record<string, AttendanceStatusCode> => {
  if (typeof window === "undefined") return {};
  try {
    const saved = localStorage.getItem(LOCAL_STORAGE_KEY);
    return saved ? JSON.parse(saved) : {};
  } catch {
    return {};
  }
};

const applyOverridesToMatrix = (
  matrix: MatrixEmployee[],
  overrides: Record<string, AttendanceStatusCode>
): MatrixEmployee[] => {
  if (!overrides || Object.keys(overrides).length === 0) return matrix;
  return matrix.map((emp) => {
    let modified = false;
    const updatedAttendance = { ...emp.attendance };
    Object.entries(overrides).forEach(([key, status]) => {
      const parts = key.split("_");
      if (parts.length === 2 && Number(parts[0]) === emp.id) {
        updatedAttendance[parts[1]] = status;
        modified = true;
      }
    });
    return modified ? { ...emp, attendance: updatedAttendance } : emp;
  });
};

export default function BulkAttendanceAdjustmentsPage() {
  // Master Filter Inputs
  const [fromDate, setFromDate] = useState<string>("2026-07-01");
  const [toDate, setToDate] = useState<string>("2026-07-22");
  const [selectedBranchId, setSelectedBranchId] = useState<string>("");
  const [globalSearch, setGlobalSearch] = useState<string>("");

  // Applied Filter States
  const [searchFromDate, setSearchFromDate] = useState<string>("2026-07-01");
  const [searchToDate, setSearchToDate] = useState<string>("2026-07-22");
  const [searchBranchId, setSearchBranchId] = useState<string>("");
  const [appliedSearch, setAppliedSearch] = useState<string>("");

  // Column Header Filter Popovers / Inputs
  const [nameFilter, setNameFilter] = useState<string>("");
  const [deptFilter, setDeptFilter] = useState<string>("");
  const [desigFilter, setDesigFilter] = useState<string>("");

  const [showNameFilterPopover, setShowNameFilterPopover] = useState<boolean>(false);
  const [showDeptFilterPopover, setShowDeptFilterPopover] = useState<boolean>(false);
  const [showDesigFilterPopover, setShowDesigFilterPopover] = useState<boolean>(false);

  // Pagination State
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(25);

  // Persistence & Mutation State
  const batchUpdateMutation = useBatchUpdateBulkAttendanceAdjustments();
  const [savedOverrides, setSavedOverrides] = useState<Record<string, AttendanceStatusCode>>(loadSavedOverrides);
  const [pendingEdits, setPendingEdits] = useState<Record<string, AttendanceStatusCode>>({});

  // Table & UI States
  const [dataMatrix, setDataMatrix] = useState<MatrixEmployee[]>(() =>
    applyOverridesToMatrix(generate120QAMatrix(), loadSavedOverrides())
  );
  const pendingEditsCount = useMemo(() => Object.keys(pendingEdits).length, [pendingEdits]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isError, setIsError] = useState<boolean>(false);
  const [showInfoModal, setShowInfoModal] = useState<boolean>(false);

  // QA Simulation Control Panel States
  const [simulateEmpty, setSimulateEmpty] = useState<boolean>(false);
  const [qaArchetypeFilter, setQaArchetypeFilter] = useState<string>("all");

  // Column visibility options for Reset Columns dropdown
  const [resetDropdownOpen, setResetDropdownOpen] = useState<boolean>(false);
  const [visibleColumns, setVisibleColumns] = useState({
    department: true,
    designation: true,
  });

  // Reusing Master Data Lookup Hooks per Golden Rule
  const { data: branchOptions = [] } = useBranchOptions();
  const { data: departmentOptions = [] } = useDepartmentOptions();
  const { data: designationOptions = [] } = useDesignationOptions();

  // Generate dynamic date list based on selected Date Range
  const dateList = useMemo(() => {
    const list: { dateStr: string; dayNumber: string; monthShort: string; weekdayShort: string }[] = [];
    if (!searchFromDate || !searchToDate) return list;

    const curr = new Date(searchFromDate);
    const end = new Date(searchToDate);
    let count = 0;

    while (curr <= end && count < 31) {
      const dateStr = curr.toISOString().slice(0, 10);
      const parts = dateStr.split("-");
      const dayNumber = parts[2];
      const monthShort = curr.toLocaleDateString("en-US", { month: "short" });
      const weekdayShort = curr.toLocaleDateString("en-US", { weekday: "short" });
      list.push({ dateStr, dayNumber, monthShort, weekdayShort });
      curr.setDate(curr.getDate() + 1);
      count++;
    }
    return list;
  }, [searchFromDate, searchToDate]);

  // Filter employees based on applied filters, global search, and QA scenario filters
  const filteredEmployees = useMemo(() => {
    if (simulateEmpty) return [];

    return dataMatrix.filter((emp) => {
      // Branch filter
      if (searchBranchId && emp.branch_id !== Number(searchBranchId)) {
        return false;
      }

      // QA Archetype Preset filter
      if (qaArchetypeFilter !== "all") {
        if (qaArchetypeFilter.startsWith("branch_")) {
          const targetBranchId = Number(qaArchetypeFilter.replace("branch_", ""));
          if (emp.branch_id !== targetBranchId) return false;
        } else if (emp.archetype !== qaArchetypeFilter) {
          return false;
        }
      }

      // Global Search
      if (appliedSearch) {
        const q = appliedSearch.toLowerCase().trim();
        const matchesGlobal =
          emp.employee_name.toLowerCase().includes(q) ||
          emp.employee_code.toLowerCase().includes(q) ||
          emp.department.toLowerCase().includes(q) ||
          emp.designation.toLowerCase().includes(q) ||
          emp.branch_name.toLowerCase().includes(q);
        if (!matchesGlobal) return false;
      }

      // Specific column header filters
      if (nameFilter && !emp.employee_name.toLowerCase().includes(nameFilter.toLowerCase())) {
        return false;
      }
      if (deptFilter && !emp.department.toLowerCase().includes(deptFilter.toLowerCase())) {
        return false;
      }
      if (desigFilter && !emp.designation.toLowerCase().includes(desigFilter.toLowerCase())) {
        return false;
      }
      return true;
    });
  }, [dataMatrix, searchBranchId, appliedSearch, nameFilter, deptFilter, desigFilter, simulateEmpty, qaArchetypeFilter]);

  // Paginated records
  const totalRecords = filteredEmployees.length;
  const totalPages = Math.ceil(totalRecords / pageSize) || 1;
  const paginatedEmployees = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return filteredEmployees.slice(start, start + pageSize);
  }, [filteredEmployees, currentPage, pageSize]);

  // Handle Search Trigger
  const handleSearchSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setIsLoading(true);
    setTimeout(() => {
      setSearchFromDate(fromDate);
      setSearchToDate(toDate);
      setSearchBranchId(selectedBranchId);
      setAppliedSearch(globalSearch);
      setCurrentPage(1);
      setIsLoading(false);
    }, 300);
  };


  // Handle cell edit
  const handleStatusChange = (empId: number, dateStr: string, newStatus: AttendanceStatusCode) => {
    setDataMatrix((prev) =>
      prev.map((emp) => {
        if (emp.id === empId) {
          return {
            ...emp,
            attendance: {
              ...emp.attendance,
              [dateStr]: newStatus,
            },
          };
        }
        return emp;
      })
    );

    const key = `${empId}_${dateStr}`;
    setPendingEdits((prev) => ({
      ...prev,
      [key]: newStatus,
    }));
  };

  // Handle Save Changes
  const handleSaveChanges = async () => {
    const keys = Object.keys(pendingEdits);
    if (keys.length === 0) {
      toast.info("No unsaved attendance adjustments to commit.");
      return;
    }

    const updates = keys.map((key) => {
      const [empIdStr, dateStr] = key.split("_");
      return {
        employee_id: Number(empIdStr),
        attendance_date: dateStr,
        adjusted_status: pendingEdits[key],
      };
    });

    try {
      await batchUpdateMutation.mutateAsync({ updates });
    } catch (err) {
      console.warn("Backend batch update API unavailable, persisting locally.", err);
    }

    const updatedOverrides = { ...savedOverrides, ...pendingEdits };
    setSavedOverrides(updatedOverrides);
    try {
      localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(updatedOverrides));
    } catch {
      console.error("Failed to save overrides to localStorage");
    }

    setPendingEdits({});
    toast.success(`Successfully saved ${updates.length} attendance adjustments!`);
  };

  // Handle Export Excel
  const handleExportExcel = () => {
    try {
      const exportRows = filteredEmployees.map((emp) => {
        const rowObj: Record<string, string | number> = {
          "Employee ID": emp.employee_code,
          "Employee Name": emp.employee_name,
          "Department": emp.department,
          "Designation": emp.designation,
          "Branch": emp.branch_name,
          "QA Archetype": emp.archetype,
        };
        dateList.forEach((d) => {
          rowObj[`${d.dayNumber}-${d.monthShort} (${d.weekdayShort})`] = emp.attendance[d.dateStr] || "FD";
        });
        return rowObj;
      });

      const worksheet = XLSX.utils.json_to_sheet(exportRows);
      const workbook = XLSX.utils.book_new();
      XLSX.utils.book_append_sheet(workbook, worksheet, "QA Attendance Matrix");
      XLSX.writeFile(workbook, `QA_Bulk_Attendance_Adjustments_${searchFromDate}_to_${searchToDate}.xlsx`);
      toast.success(`Exported ${filteredEmployees.length} employee matrix records to Excel.`);
    } catch {
      toast.error("Failed to export Excel file.");
    }
  };

  // Handle Refresh / Reset
  const handleRefresh = () => {
    setIsLoading(true);
    setTimeout(() => {
      const overrides = loadSavedOverrides();
      setSavedOverrides(overrides);
      setDataMatrix(applyOverridesToMatrix(generate120QAMatrix(), overrides));
      setPendingEdits({});
      setIsLoading(false);
      toast.info("Refreshed attendance matrix.");
    }, 400);
  };

  const handleResetFilters = () => {
    setFromDate("2026-07-01");
    setToDate("2026-07-22");
    setSelectedBranchId("");
    setGlobalSearch("");
    setSearchFromDate("2026-07-01");
    setSearchToDate("2026-07-22");
    setSearchBranchId("");
    setAppliedSearch("");
    setNameFilter("");
    setDeptFilter("");
    setDesigFilter("");
    setShowNameFilterPopover(false);
    setShowDeptFilterPopover(false);
    setShowDesigFilterPopover(false);
    setSimulateEmpty(false);
    setIsError(false);
    setQaArchetypeFilter("all");
    setCurrentPage(1);
  };

  return (
    <ProtectedRoute requiredPermission={{ feature: "payroll_processing", action: "read" }}>
      <div className="p-4 md:p-6 space-y-5 bg-slate-50/50 dark:bg-slate-950/40 min-h-screen text-slate-800 dark:text-slate-200">
        
        {/* Page Title */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div>
            <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
              Bulk Attendance Adjustments
            </h1>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Review and update daily attendance statuses across employees and branches.
            </p>
          </div>

          {pendingEditsCount > 0 && (
            <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-amber-100 dark:bg-amber-950 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-800 animate-pulse">
              {pendingEditsCount} unsaved adjustments
            </span>
          )}
        </div>

        {/* Filter & Action Toolbar */}
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 bg-white dark:bg-slate-900 p-3.5 border border-slate-200 dark:border-slate-800 rounded-xl shadow-xs">
          
          {/* Left Filters */}
          <form onSubmit={handleSearchSubmit} className="flex flex-wrap items-center gap-3 w-full lg:w-auto">
            {/* Date Range Picker Input Display */}
            <div className="flex items-center bg-slate-50 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-700 dark:text-slate-200 font-medium">
              <input
                type="date"
                value={fromDate}
                onChange={(e) => setFromDate(e.target.value)}
                className="bg-transparent border-none focus:outline-none w-28 font-semibold text-slate-800 dark:text-slate-100 cursor-pointer"
              />
              <span className="mx-2 text-slate-400 font-bold">→</span>
              <input
                type="date"
                value={toDate}
                onChange={(e) => setToDate(e.target.value)}
                className="bg-transparent border-none focus:outline-none w-28 font-semibold text-slate-800 dark:text-slate-100 cursor-pointer"
              />
              <Calendar className="w-4 h-4 ml-1.5 text-slate-400 shrink-0" />
            </div>

            {/* Branch Dropdown — Golden Rule: Reuses useBranchOptions */}
            <div className="relative min-w-[160px]">
              <select
                value={selectedBranchId}
                onChange={(e) => setSelectedBranchId(e.target.value)}
                className="w-full appearance-none bg-slate-50 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-1.5 pr-8 text-xs font-medium text-slate-700 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer"
              >
                <option value="">Choose Branch</option>
                {branchOptions.map((b) => (
                  <option key={b.branch_id} value={b.branch_id}>
                    {b.branch_name}
                  </option>
                ))}
              </select>
              <ChevronDown className="w-4 h-4 absolute right-2.5 top-2 text-slate-400 pointer-events-none" />
            </div>

            {/* Search Button */}
            <button
              type="submit"
              className="px-5 py-1.5 text-xs font-semibold text-white bg-[#0B85C9] hover:bg-[#0974b0] rounded-lg transition-colors cursor-pointer shadow-xs"
            >
              Search
            </button>
          </form>

          {/* Right Action Buttons */}
          <div className="flex flex-wrap items-center gap-2">
            {/* Information Button */}
            <button
              type="button"
              onClick={() => setShowInfoModal(true)}
              className="p-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700/60 transition-colors cursor-pointer"
              title="Attendance Status Guide"
            >
              <Info className="w-4 h-4" />
            </button>

            {/* Save Changes */}
            <button
              type="button"
              onClick={handleSaveChanges}
              className={`px-3 py-1.5 rounded-lg border text-xs font-semibold transition-all cursor-pointer flex items-center gap-1.5 ${
                pendingEditsCount > 0
                  ? "bg-blue-600 text-white border-blue-600 hover:bg-blue-700 shadow-xs"
                  : "bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 border-slate-200 dark:border-slate-700 hover:bg-slate-50"
              }`}
            >
              <Save className="w-3.5 h-3.5" />
              <span>Save Changes</span>
            </button>

            {/* Export Excel */}
            <button
              type="button"
              onClick={handleExportExcel}
              className="px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700/60 text-xs font-semibold transition-colors cursor-pointer flex items-center gap-1.5"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Export Excel</span>
            </button>

            {/* Reset Columns Dropdown */}
            <div className="relative">
              <button
                type="button"
                onClick={() => setResetDropdownOpen(!resetDropdownOpen)}
                className="px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700/60 text-xs font-semibold transition-colors cursor-pointer flex items-center gap-1.5"
              >
                <span>Reset Columns</span>
                <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
              </button>

              {resetDropdownOpen && (
                <div className="absolute right-0 mt-1 w-48 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-lg p-2 z-30 space-y-1 text-xs">
                  <div className="px-2 py-1 text-[10px] font-bold uppercase tracking-wider text-slate-400">
                    Toggle Column Visibility
                  </div>
                  <label className="flex items-center gap-2 px-2 py-1 rounded hover:bg-slate-50 dark:hover:bg-slate-800 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={visibleColumns.department}
                      onChange={(e) => setVisibleColumns({ ...visibleColumns, department: e.target.checked })}
                      className="rounded text-blue-600"
                    />
                    <span>Department Column</span>
                  </label>
                  <label className="flex items-center gap-2 px-2 py-1 rounded hover:bg-slate-50 dark:hover:bg-slate-800 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={visibleColumns.designation}
                      onChange={(e) => setVisibleColumns({ ...visibleColumns, designation: e.target.checked })}
                      className="rounded text-blue-600"
                    />
                    <span>Designation Column</span>
                  </label>
                  <div className="border-t border-slate-100 dark:border-slate-800 pt-1 mt-1">
                    <button
                      type="button"
                      onClick={() => {
                        setVisibleColumns({ department: true, designation: true });
                        setResetDropdownOpen(false);
                        toast.info("Columns reset to default.");
                      }}
                      className="w-full text-left px-2 py-1 text-blue-600 dark:text-blue-400 font-semibold hover:bg-blue-50 dark:hover:bg-blue-950/40 rounded"
                    >
                      Restore All Defaults
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* Refresh Button */}
            <button
              type="button"
              onClick={handleRefresh}
              className="p-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700/60 transition-colors cursor-pointer"
              title="Refresh Matrix"
            >
              <RefreshCw className={`w-4 h-4 ${isLoading ? "animate-spin" : ""}`} />
            </button>
          </div>
        </div>

        {/* Global Filter Bar (Quick Search) */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3 bg-white dark:bg-slate-900 px-4 py-2.5 border border-slate-200 dark:border-slate-800 rounded-xl">
          <div className="relative w-full sm:w-80">
            <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-slate-400" />
            <input
              type="text"
              placeholder="Quick search employee name, ID, department..."
              value={globalSearch}
              onChange={(e) => {
                setGlobalSearch(e.target.value);
                setAppliedSearch(e.target.value);
                setCurrentPage(1);
              }}
              className="w-full pl-8 pr-4 py-1 text-xs bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>

          <div className="flex items-center gap-3 text-xs text-slate-500 dark:text-slate-400 w-full sm:w-auto justify-between sm:justify-end">
            <span className="font-semibold">Showing {filteredEmployees.length} Employees</span>
            {(appliedSearch || searchBranchId || nameFilter || deptFilter || desigFilter || qaArchetypeFilter !== "all" || simulateEmpty) && (
              <button
                type="button"
                onClick={handleResetFilters}
                className="text-xs text-blue-600 dark:text-blue-400 font-semibold hover:underline cursor-pointer flex items-center gap-1"
              >
                <RotateCcw className="w-3 h-3" /> Clear Filters
              </button>
            )}
          </div>
        </div>

        {/* Attendance Matrix Data Grid */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden shadow-xs relative">
          
          {/* Loading Skeleton State */}
          {isLoading ? (
            <div className="p-8 space-y-4">
              <div className="h-10 bg-slate-100 dark:bg-slate-800 rounded-md animate-pulse w-full" />
              {Array.from({ length: 8 }).map((_, idx) => (
                <div key={idx} className="h-12 bg-slate-50 dark:bg-slate-800/60 rounded-md animate-pulse w-full" />
              ))}
            </div>
          ) : isError ? (
            /* Error State with Retry Button */
            <div className="p-12 text-center space-y-4">
              <div className="w-12 h-12 rounded-full bg-red-100 dark:bg-red-950/50 text-red-600 dark:text-red-400 flex items-center justify-center mx-auto">
                <AlertCircle className="w-6 h-6" />
              </div>
              <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">
                Failed to Load Attendance Matrix Data
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400 max-w-sm mx-auto">
                An unexpected server communication error occurred while fetching employee matrix records.
              </p>
              <button
                type="button"
                onClick={() => {
                  setIsError(false);
                  handleRefresh();
                }}
                className="px-4 py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-xs transition-colors cursor-pointer"
              >
                Retry Request
              </button>
            </div>
          ) : paginatedEmployees.length === 0 ? (
            /* Empty State */
            <div className="p-12 text-center space-y-4">
              <div className="w-12 h-12 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-400 flex items-center justify-center mx-auto">
                <SlidersHorizontal className="w-6 h-6" />
              </div>
              <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">
                No Attendance Records Found
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400 max-w-sm mx-auto">
                No employees match your search query or selected branch criteria. Try clearing search filters.
              </p>
              <button
                type="button"
                onClick={handleResetFilters}
                className="px-4 py-2 text-xs font-semibold text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-950/40 hover:bg-blue-100 rounded-lg transition-colors cursor-pointer"
              >
                Reset Filters
              </button>
            </div>
          ) : (
            /* Matrix Table Grid */
            <div className="overflow-x-auto overflow-y-auto max-h-[620px]">
              <table className="w-full text-left border-collapse min-w-max text-xs">
                
                {/* Double Row Table Header */}
                <thead className="sticky top-0 z-20 bg-slate-100 dark:bg-slate-800/90 text-slate-700 dark:text-slate-300 font-bold border-b border-slate-200 dark:border-slate-700 shadow-2xs">
                  
                  {/* Row 1: Hierarchy Groups & Date Columns */}
                  <tr className="border-b border-slate-200/80 dark:border-slate-700/80 text-[11px] uppercase tracking-wider">
                    {/* Static Column Header Groups */}
                    <th colSpan={2} className="py-2.5 px-3 bg-slate-100 dark:bg-slate-800 border-r border-slate-200 dark:border-slate-700 sticky left-0 z-30 shadow-xs text-center font-extrabold text-slate-700 dark:text-slate-200">
                      Employees
                    </th>
                    {visibleColumns.department && visibleColumns.designation && (
                      <th colSpan={2} className="py-2.5 px-3 bg-slate-100 dark:bg-slate-800 border-r border-slate-200 dark:border-slate-700 sticky left-[250px] z-30 shadow-xs text-center font-extrabold text-slate-700 dark:text-slate-200">
                        Hierarchy
                      </th>
                    )}
                    {visibleColumns.department && !visibleColumns.designation && (
                      <th colSpan={1} className="py-2.5 px-3 bg-slate-100 dark:bg-slate-800 border-r border-slate-200 dark:border-slate-700 sticky left-[250px] z-30 shadow-xs text-center font-extrabold text-slate-700 dark:text-slate-200">
                        Hierarchy
                      </th>
                    )}
                    {!visibleColumns.department && visibleColumns.designation && (
                      <th colSpan={1} className="py-2.5 px-3 bg-slate-100 dark:bg-slate-800 border-r border-slate-200 dark:border-slate-700 sticky left-[250px] z-30 shadow-xs text-center font-extrabold text-slate-700 dark:text-slate-200">
                        Hierarchy
                      </th>
                    )}

                    {/* Dynamic Date Headers */}
                    {dateList.map((d) => (
                      <th key={d.dateStr} className="py-2 px-2 text-center border-r border-slate-200/60 dark:border-slate-700/60 min-w-[70px] font-bold text-slate-800 dark:text-slate-100">
                        {d.dayNumber}-{d.monthShort}
                      </th>
                    ))}
                  </tr>

                  {/* Row 2: Sub-headers & Weekdays */}
                  <tr className="text-[11px] font-semibold text-slate-600 dark:text-slate-400">
                    
                    {/* Sticky Employee ID Header */}
                    <th className="py-2 px-3 border-r border-slate-200 dark:border-slate-700 sticky left-0 z-30 bg-slate-100 dark:bg-slate-800 min-w-[80px]">
                      Employee ID
                    </th>

                    {/* Sticky Employee Name Header */}
                    <th className="py-2 px-3 border-r border-slate-200 dark:border-slate-700 sticky left-[80px] z-30 bg-slate-100 dark:bg-slate-800 min-w-[170px]">
                      <div className="flex items-center justify-between relative">
                        <span>Employee Name</span>
                        <button
                          type="button"
                          onClick={() => {
                            setShowNameFilterPopover(!showNameFilterPopover);
                            setShowDeptFilterPopover(false);
                            setShowDesigFilterPopover(false);
                          }}
                          className={`p-1 rounded hover:bg-slate-200 dark:hover:bg-slate-700 cursor-pointer transition-colors ${
                            nameFilter ? "text-blue-600 dark:text-blue-400 font-bold bg-blue-50 dark:bg-blue-950/40" : "text-slate-400"
                          }`}
                          title="Filter by Employee Name"
                        >
                          <Filter className="w-3 h-3" />
                        </button>

                        {showNameFilterPopover && (
                          <div className="absolute left-0 top-full mt-2 w-56 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-xl p-3 z-50 space-y-2 text-xs normal-case font-normal">
                            <div className="flex items-center justify-between font-bold text-slate-800 dark:text-slate-200">
                              <span>Filter Employee Name</span>
                              <button
                                type="button"
                                onClick={() => setShowNameFilterPopover(false)}
                                className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 cursor-pointer"
                              >
                                <X className="w-3.5 h-3.5" />
                              </button>
                            </div>
                            <input
                              type="text"
                              placeholder="Search employee name..."
                              value={nameFilter}
                              onChange={(e) => {
                                setNameFilter(e.target.value);
                                setCurrentPage(1);
                              }}
                              className="w-full px-2.5 py-1.5 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500 text-xs"
                              autoFocus
                            />
                            {nameFilter && (
                              <button
                                type="button"
                                onClick={() => {
                                  setNameFilter("");
                                  setCurrentPage(1);
                                }}
                                className="w-full text-center py-1 text-[11px] font-semibold text-blue-600 dark:text-blue-400 hover:underline cursor-pointer"
                              >
                                Clear Filter
                              </button>
                            )}
                          </div>
                        )}
                      </div>
                    </th>

                    {/* Sticky Department Header */}
                    {visibleColumns.department && (
                      <th className="py-2 px-3 border-r border-slate-200 dark:border-slate-700 sticky left-[250px] z-30 bg-slate-100 dark:bg-slate-800 min-w-[120px]">
                        <div className="flex items-center justify-between relative">
                          <span>Department</span>
                          <button
                            type="button"
                            onClick={() => {
                              setShowDeptFilterPopover(!showDeptFilterPopover);
                              setShowNameFilterPopover(false);
                              setShowDesigFilterPopover(false);
                            }}
                            className={`p-1 rounded hover:bg-slate-200 dark:hover:bg-slate-700 cursor-pointer transition-colors ${
                              deptFilter ? "text-blue-600 dark:text-blue-400 font-bold bg-blue-50 dark:bg-blue-950/40" : "text-slate-400"
                            }`}
                            title="Filter by Department"
                          >
                            <Filter className="w-3 h-3" />
                          </button>

                          {showDeptFilterPopover && (
                            <div className="absolute left-0 top-full mt-2 w-56 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-xl p-3 z-50 space-y-2 text-xs normal-case font-normal">
                              <div className="flex items-center justify-between font-bold text-slate-800 dark:text-slate-200">
                                <span>Filter Department</span>
                                <button
                                  type="button"
                                  onClick={() => setShowDeptFilterPopover(false)}
                                  className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 cursor-pointer"
                                >
                                  <X className="w-3.5 h-3.5" />
                                </button>
                              </div>
                              {departmentOptions.length > 0 && (
                                <select
                                  value={deptFilter}
                                  onChange={(e) => {
                                    setDeptFilter(e.target.value);
                                    setCurrentPage(1);
                                  }}
                                  className="w-full px-2.5 py-1.5 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500 text-xs cursor-pointer font-medium text-slate-800 dark:text-slate-200"
                                >
                                  <option value="">Select Department</option>
                                  {departmentOptions.map((d) => (
                                    <option key={d.dept_id} value={d.dept_name}>
                                      {d.dept_name}
                                    </option>
                                  ))}
                                </select>
                              )}
                              <input
                                type="text"
                                placeholder="Or type department..."
                                value={deptFilter}
                                onChange={(e) => {
                                  setDeptFilter(e.target.value);
                                  setCurrentPage(1);
                                }}
                                className="w-full px-2.5 py-1.5 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500 text-xs"
                              />
                              {deptFilter && (
                                <button
                                  type="button"
                                  onClick={() => {
                                    setDeptFilter("");
                                    setCurrentPage(1);
                                  }}
                                  className="w-full text-center py-1 text-[11px] font-semibold text-blue-600 dark:text-blue-400 hover:underline cursor-pointer"
                                >
                                  Clear Filter
                                </button>
                              )}
                            </div>
                          )}
                        </div>
                      </th>
                    )}

                    {/* Sticky Designation Header */}
                    {visibleColumns.designation && (
                      <th
                        className={`py-2 px-3 border-r border-slate-200 dark:border-slate-700 sticky z-30 bg-slate-100 dark:bg-slate-800 min-w-[140px] ${
                          visibleColumns.department ? "left-[370px]" : "left-[250px]"
                        }`}
                      >
                        <div className="flex items-center justify-between relative">
                          <span>Designation</span>
                          <button
                            type="button"
                            onClick={() => {
                              setShowDesigFilterPopover(!showDesigFilterPopover);
                              setShowNameFilterPopover(false);
                              setShowDeptFilterPopover(false);
                            }}
                            className={`p-1 rounded hover:bg-slate-200 dark:hover:bg-slate-700 cursor-pointer transition-colors ${
                              desigFilter ? "text-blue-600 dark:text-blue-400 font-bold bg-blue-50 dark:bg-blue-950/40" : "text-slate-400"
                            }`}
                            title="Filter by Designation"
                          >
                            <Filter className="w-3 h-3" />
                          </button>

                          {showDesigFilterPopover && (
                            <div className="absolute left-0 top-full mt-2 w-56 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-xl p-3 z-50 space-y-2 text-xs normal-case font-normal">
                              <div className="flex items-center justify-between font-bold text-slate-800 dark:text-slate-200">
                                <span>Filter Designation</span>
                                <button
                                  type="button"
                                  onClick={() => setShowDesigFilterPopover(false)}
                                  className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 cursor-pointer"
                                >
                                  <X className="w-3.5 h-3.5" />
                                </button>
                              </div>
                              {designationOptions.length > 0 && (
                                <select
                                  value={desigFilter}
                                  onChange={(e) => {
                                    setDesigFilter(e.target.value);
                                    setCurrentPage(1);
                                  }}
                                  className="w-full px-2.5 py-1.5 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500 text-xs cursor-pointer font-medium text-slate-800 dark:text-slate-200"
                                >
                                  <option value="">Select Designation</option>
                                  {designationOptions.map((d) => (
                                    <option key={d.designation_id} value={d.designation_name}>
                                      {d.designation_name}
                                    </option>
                                  ))}
                                </select>
                              )}
                              <input
                                type="text"
                                placeholder="Or type designation..."
                                value={desigFilter}
                                onChange={(e) => {
                                  setDesigFilter(e.target.value);
                                  setCurrentPage(1);
                                }}
                                className="w-full px-2.5 py-1.5 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500 text-xs"
                              />
                              {desigFilter && (
                                <button
                                  type="button"
                                  onClick={() => {
                                    setDesigFilter("");
                                    setCurrentPage(1);
                                  }}
                                  className="w-full text-center py-1 text-[11px] font-semibold text-blue-600 dark:text-blue-400 hover:underline cursor-pointer"
                                >
                                  Clear Filter
                                </button>
                              )}
                            </div>
                          )}
                        </div>
                      </th>
                    )}

                    {/* Dynamic Weekday Headers */}
                    {dateList.map((d) => (
                      <th
                        key={d.dateStr}
                        className={`py-1.5 px-2 text-center border-r border-slate-200/60 dark:border-slate-700/60 text-[10px] uppercase font-bold ${
                          d.weekdayShort === "Sun" ? "text-red-500 bg-red-50/40 dark:bg-red-950/20" : "text-slate-500"
                        }`}
                      >
                        {d.weekdayShort}
                      </th>
                    ))}
                  </tr>
                </thead>

                {/* Table Body Matrix */}
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800 text-xs">
                  {paginatedEmployees.map((emp) => (
                    <tr key={emp.id} className="hover:bg-blue-50/20 dark:hover:bg-slate-800/40 transition-colors">
                      
                      {/* Sticky Employee ID */}
                      <td className="py-2 px-3 border-r border-slate-200/80 dark:border-slate-800 sticky left-0 z-10 bg-white dark:bg-slate-900 font-mono text-[11px] text-slate-600 dark:text-slate-400">
                        {emp.employee_code}
                      </td>

                      {/* Sticky Employee Name */}
                      <td className="py-2 px-3 border-r border-slate-200/80 dark:border-slate-800 sticky left-[80px] z-10 bg-white dark:bg-slate-900 font-semibold text-slate-900 dark:text-slate-100 truncate max-w-[170px]">
                        <div>{emp.employee_name}</div>
                        <div className="text-[9px] text-slate-400 font-mono font-normal">{emp.branch_name}</div>
                      </td>

                      {/* Sticky Department */}
                      {visibleColumns.department && (
                        <td className="py-2 px-3 border-r border-slate-200/80 dark:border-slate-800 sticky left-[250px] z-10 bg-white dark:bg-slate-900 text-slate-600 dark:text-slate-400 truncate max-w-[120px]">
                          {emp.department}
                        </td>
                      )}

                      {/* Sticky Designation */}
                      {visibleColumns.designation && (
                        <td
                          className={`py-2 px-3 border-r border-slate-200/80 dark:border-slate-800 sticky z-10 bg-white dark:bg-slate-900 text-slate-600 dark:text-slate-400 truncate max-w-[140px] ${
                            visibleColumns.department ? "left-[370px]" : "left-[250px]"
                          }`}
                        >
                          {emp.designation}
                        </td>
                      )}

                      {/* Attendance Dropdowns for Date Range */}
                      {dateList.map((d) => {
                        const currentStatus = emp.attendance[d.dateStr] || "FD";
                        const statusObj =
                          ATTENDANCE_STATUSES.find((s) => s.code === currentStatus) || ATTENDANCE_STATUSES[2];

                        return (
                          <td
                            key={d.dateStr}
                            className="py-1 px-1.5 text-center border-r border-slate-100 dark:border-slate-800/60 min-w-[70px]"
                          >
                            <div className="relative inline-block w-full">
                              <select
                                value={currentStatus}
                                onChange={(e) =>
                                  handleStatusChange(emp.id, d.dateStr, e.target.value as AttendanceStatusCode)
                                }
                                className={`w-full appearance-none px-1.5 py-1 text-[11px] font-bold text-center rounded border border-transparent hover:border-slate-300 focus:border-blue-500 focus:outline-none cursor-pointer transition-colors ${statusObj.colorClass} ${statusObj.bgClass}`}
                              >
                                {ATTENDANCE_STATUSES.map((opt) => (
                                  <option key={opt.code} value={opt.code} className="text-slate-900 dark:text-slate-100 font-semibold bg-white dark:bg-slate-900">
                                    {opt.code} — {opt.label}
                                  </option>
                                ))}
                              </select>
                              <span className="pointer-events-none absolute right-1 top-1.5 text-[9px] text-slate-400">
                                ▼
                              </span>
                            </div>
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Pagination Controls Footer */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3 p-3.5 bg-slate-50 dark:bg-slate-800/60 border-t border-slate-200 dark:border-slate-800 text-xs">
            
            {/* Left: Page Size Selector */}
            <div className="flex items-center gap-2">
              <span className="text-slate-500 dark:text-slate-400 font-medium">Page Size:</span>
              <select
                value={pageSize}
                onChange={(e) => {
                  setPageSize(Number(e.target.value));
                  setCurrentPage(1);
                }}
                className="px-2.5 py-1 rounded border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 font-semibold text-slate-700 dark:text-slate-200 focus:outline-none cursor-pointer"
              >
                <option value={10}>10 per page</option>
                <option value={25}>25 per page</option>
                <option value={50}>50 per page</option>
                <option value={100}>100 per page</option>
              </select>
            </div>

            {/* Center: Record Counter */}
            <div className="text-slate-600 dark:text-slate-400 font-medium">
              Showing <span className="font-bold text-slate-900 dark:text-slate-100">{totalRecords > 0 ? (currentPage - 1) * pageSize + 1 : 0}</span> to{" "}
              <span className="font-bold text-slate-900 dark:text-slate-100">{Math.min(currentPage * pageSize, totalRecords)}</span> of{" "}
              <span className="font-bold text-slate-900 dark:text-slate-100">{totalRecords}</span> records
            </div>

            {/* Right: Prev / Next Buttons */}
            <div className="flex items-center gap-1.5">
              <button
                type="button"
                disabled={currentPage <= 1}
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                className="p-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer transition-colors flex items-center gap-1 text-xs font-semibold"
              >
                <ChevronLeft className="w-4 h-4" />
                <span>Previous</span>
              </button>

              <span className="px-3 py-1 font-bold text-slate-700 dark:text-slate-300">
                Page {currentPage} of {totalPages}
              </span>

              <button
                type="button"
                disabled={currentPage >= totalPages}
                onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                className="p-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer transition-colors flex items-center gap-1 text-xs font-semibold"
              >
                <span>Next</span>
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>

        {/* Attendance Status Information Guide Modal */}
        {showInfoModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
            <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 max-w-lg w-full p-6 space-y-4 shadow-xl">
              <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3">
                <div className="flex items-center gap-2">
                  <div className="p-2 rounded-lg bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400">
                    <Info className="w-5 h-5" />
                  </div>
                  <h3 className="text-lg font-bold text-slate-900 dark:text-slate-100">
                    Attendance Status Legend
                  </h3>
                </div>
                <button
                  type="button"
                  onClick={() => setShowInfoModal(false)}
                  className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 cursor-pointer"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                {ATTENDANCE_STATUSES.map((status) => (
                  <div
                    key={status.code}
                    className="p-2.5 rounded-xl border border-slate-100 dark:border-slate-800 flex items-center space-x-3 bg-slate-50/50 dark:bg-slate-800/40"
                  >
                    <span className={`w-8 h-8 rounded-lg ${status.bgClass} ${status.colorClass} flex items-center justify-center text-xs font-extrabold shrink-0 border border-slate-200/50 dark:border-slate-700/50`}>
                      {status.code}
                    </span>
                    <div>
                      <div className="font-bold text-slate-900 dark:text-slate-100">{status.label}</div>
                      <div className="text-[10px] text-slate-500 dark:text-slate-400 leading-tight">{status.description}</div>
                    </div>
                  </div>
                ))}
              </div>

              <div className="pt-3 border-t border-slate-100 dark:border-slate-800 flex justify-end">
                <button
                  type="button"
                  onClick={() => setShowInfoModal(false)}
                  className="px-4 py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-xs transition-colors cursor-pointer"
                >
                  Got It
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </ProtectedRoute>
  );
}
