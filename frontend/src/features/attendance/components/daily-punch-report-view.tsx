"use client";

import React, { useState, useMemo } from "react";
import {
  Search,
  RotateCcw,
  FileSpreadsheet,
  FileText,
  Clock,
  AlertTriangle,
  Calendar,
  ChevronLeft,
  ChevronRight,
  ArrowUpDown,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Moon,
  Palmtree,
  Sparkles,
} from "lucide-react";

// ==========================================
// TYPES & INTERFACES (Strict TypeScript)
// ==========================================

export type AttendanceStatusType =
  | "PRESENT"
  | "ABSENT"
  | "LEAVE"
  | "HOLIDAY"
  | "WEEK_OFF"
  | "MISSING_PUNCH"
  | "LATE"
  | "EARLY_OUT";

export interface MockPunchCell {
  firstIn: string | null;
  lastOut: string | null;
  status: AttendanceStatusType;
  isLate: boolean;
  isEarlyOut: boolean;
  isMissingPunch: boolean;
  isWeekOff: boolean;
  isHoliday: boolean;
  isLeave: boolean;
  punchCount: number;
}

export interface MockEmployeeDailyRow {
  employeeId: number;
  employeeCode: string;
  employeeName: string;
  department: string;
  designation: string;
  branch: string;
  shift: string;
  punches: Record<string, MockPunchCell>; // dateStr -> MockPunchCell
}

export interface OptionType {
  label: string;
  value: string;
}

// ==========================================
// MOCK DATA GENERATOR (50+ Employees)
// ==========================================

const DEPARTMENTS = [
  "Engineering",
  "Human Resources",
  "Operations",
  "Finance",
  "Sales & Marketing",
  "Customer Support",
];

const DESIGNATIONS: Record<string, string[]> = {
  Engineering: ["Senior Backend Engineer", "Frontend Architect", "QA Automation Lead", "DevOps Engineer"],
  "Human Resources": ["HR Executive", "Talent Acquisition Manager", "HRBP Lead"],
  Operations: ["Operations Manager", "Logistics Specialist", "Facility Lead"],
  Finance: ["Senior Accountant", "Financial Analyst", "Payroll Lead"],
  "Sales & Marketing": ["Account Executive", "Marketing Lead", "Growth Manager"],
  "Customer Support": ["Technical Support Specialist", "Customer Success Lead"],
};

const BRANCHES = ["Main HQ - Mumbai", "Tech Hub - Bengaluru", "North Hub - Delhi", "South Hub - Chennai"];
const SHIFTS = ["Morning Shift (09:00 - 18:00)", "General Shift (10:00 - 19:00)", "Night Shift (22:00 - 07:00)"];

const FIRST_NAMES = [
  "Aarav", "Ananya", "Rohan", "Priya", "Vikram", "Neha", "Rahul", "Sneha", "Aditya", "Pooja",
  "Karan", "Kavya", "Siddharth", "Meera", "Amit", "Riya", "Manish", "Divya", "Suresh", "Ishita",
  "Rajesh", "Tanvi", "Deepak", "Shreya", "Nitin", "Swati", "Harsh", "Bhavna", "Alok", "Nisha",
  "Varun", "Sonam", "Gaurav", "Simran", "Abhishek", "Kriti", "Mayank", "Ritika", "Akash", "Priti",
  "Tarun", "Nidhi", "Sanjay", "Anjali", "Yash", "Monika", "Vivek", "Payal", "Mohit", "Richa",
  "Sameer", "Juhi"
];

const LAST_NAMES = [
  "Sharma", "Verma", "Patel", "Gupta", "Singh", "Kumar", "Joshi", "Mehta", "Shah", "Nair",
  "Deshmukh", "Reddy", "Rao", "Chopra", "Malhotra", "Bhatia", "Kapoor", "Saxena", "Agarwal", "Kulkarni"
];

const generateMockEmployees = (): MockEmployeeDailyRow[] => {
  const dates = [
    "2026-07-01", "2026-07-02", "2026-07-03", "2026-07-04", "2026-07-05",
    "2026-07-06", "2026-07-07", "2026-07-08", "2026-07-09", "2026-07-10",
    "2026-07-11", "2026-07-12", "2026-07-13", "2026-07-14", "2026-07-15"
  ];

  const employees: MockEmployeeDailyRow[] = [];

  for (let i = 1; i <= 52; i++) {
    const fn = FIRST_NAMES[(i - 1) % FIRST_NAMES.length];
    const ln = LAST_NAMES[(i - 1) % LAST_NAMES.length];
    const dept = DEPARTMENTS[(i - 1) % DEPARTMENTS.length];
    const desigList = DESIGNATIONS[dept];
    const desig = desigList[(i - 1) % desigList.length];
    const branch = BRANCHES[(i - 1) % BRANCHES.length];
    const shift = SHIFTS[(i - 1) % SHIFTS.length];
    const empCode = `EMP${1000 + i}`;

    const punches: Record<string, MockPunchCell> = {};

    dates.forEach((dStr, dIdx) => {
      const dayOfWeek = new Date(dStr).getDay(); // 0 is Sunday, 6 is Saturday

      if (dayOfWeek === 0 || (dayOfWeek === 6 && i % 2 === 0)) {
        // Week Off
        punches[dStr] = {
          firstIn: null,
          lastOut: null,
          status: "WEEK_OFF",
          isLate: false,
          isEarlyOut: false,
          isMissingPunch: false,
          isWeekOff: true,
          isHoliday: false,
          isLeave: false,
          punchCount: 0,
        };
      } else if (dStr === "2026-07-10") {
        // Company Holiday
        punches[dStr] = {
          firstIn: null,
          lastOut: null,
          status: "HOLIDAY",
          isLate: false,
          isEarlyOut: false,
          isMissingPunch: false,
          isWeekOff: false,
          isHoliday: true,
          isLeave: false,
          punchCount: 0,
        };
      } else if ((i + dIdx) % 17 === 0) {
        // Leave
        punches[dStr] = {
          firstIn: null,
          lastOut: null,
          status: "LEAVE",
          isLate: false,
          isEarlyOut: false,
          isMissingPunch: false,
          isWeekOff: false,
          isHoliday: false,
          isLeave: true,
          punchCount: 0,
        };
      } else if ((i + dIdx) % 13 === 0) {
        // Absent
        punches[dStr] = {
          firstIn: null,
          lastOut: null,
          status: "ABSENT",
          isLate: false,
          isEarlyOut: false,
          isMissingPunch: false,
          isWeekOff: false,
          isHoliday: false,
          isLeave: false,
          punchCount: 0,
        };
      } else if ((i + dIdx) % 11 === 0) {
        // Missing Punch
        punches[dStr] = {
          firstIn: "09:05 AM",
          lastOut: null,
          status: "MISSING_PUNCH",
          isLate: false,
          isEarlyOut: false,
          isMissingPunch: true,
          isWeekOff: false,
          isHoliday: false,
          isLeave: false,
          punchCount: 1,
        };
      } else if ((i + dIdx) % 7 === 0) {
        // Late Arrival
        punches[dStr] = {
          firstIn: "09:42 AM",
          lastOut: "06:15 PM",
          status: "LATE",
          isLate: true,
          isEarlyOut: false,
          isMissingPunch: false,
          isWeekOff: false,
          isHoliday: false,
          isLeave: false,
          punchCount: 2,
        };
      } else if ((i + dIdx) % 9 === 0) {
        // Early Out
        punches[dStr] = {
          firstIn: "08:58 AM",
          lastOut: "04:30 PM",
          status: "EARLY_OUT",
          isLate: false,
          isEarlyOut: true,
          isMissingPunch: false,
          isWeekOff: false,
          isHoliday: false,
          isLeave: false,
          punchCount: 2,
        };
      } else {
        // On-Time Present
        punches[dStr] = {
          firstIn: "09:02 AM",
          lastOut: "06:08 PM",
          status: "PRESENT",
          isLate: false,
          isEarlyOut: false,
          isMissingPunch: false,
          isWeekOff: false,
          isHoliday: false,
          isLeave: false,
          punchCount: 2,
        };
      }
    });

    employees.push({
      employeeId: i,
      employeeCode: empCode,
      employeeName: `${fn} ${ln}`,
      department: dept,
      designation: desig,
      branch: branch,
      shift: shift,
      punches: punches,
    });
  }

  return employees;
};

export const DailyPunchReportView: React.FC = () => {
  // Static Mock Dataset
  const allEmployees = useMemo(() => generateMockEmployees(), []);

  // Filter Controls
  const [fromDate, setFromDate] = useState<string>("2026-07-01");
  const [toDate, setToDate] = useState<string>("2026-07-15");
  const [selectedBranch, setSelectedBranch] = useState<string>("");
  const [selectedDept, setSelectedDept] = useState<string>("");
  const [selectedShift, setSelectedShift] = useState<string>("");
  const [searchTerm, setSearchTerm] = useState<string>("");

  // Applied Filter States
  const [appliedBranch, setAppliedBranch] = useState<string>("");
  const [appliedDept, setAppliedDept] = useState<string>("");
  const [appliedShift, setAppliedShift] = useState<string>("");

  // Sort & Pagination States
  const [sortField, setSortField] = useState<"employeeCode" | "employeeName" | "department">("employeeCode");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("asc");
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [pageSize] = useState<number>(10);
  const [isLoading, setIsLoading] = useState<boolean>(false);

  // Dynamic Date Columns from Date Range
  const dateList = useMemo(() => {
    const list: { dateStr: string; dayNumber: string; monthName: string; dayName: string }[] = [];
    if (!fromDate || !toDate) return list;

    const curr = new Date(fromDate);
    const end = new Date(toDate);
    let count = 0;

    while (curr <= end && count < 31) {
      const dateStr = curr.toISOString().slice(0, 10);
      const dayNumber = dateStr.split("-")[2];
      const monthName = curr.toLocaleDateString("en-US", { month: "short" });
      const dayName = curr.toLocaleDateString("en-US", { weekday: "short" });
      list.push({ dateStr, dayNumber, monthName, dayName });
      curr.setDate(curr.getDate() + 1);
      count++;
    }
    return list;
  }, [fromDate, toDate]);

  // Filtered & Sorted Employees
  const processedEmployees = useMemo(() => {
    let result = [...allEmployees];

    // Branch Filter
    if (appliedBranch) {
      result = result.filter((e) => e.branch === appliedBranch);
    }
    // Department Filter
    if (appliedDept) {
      result = result.filter((e) => e.department === appliedDept);
    }
    // Shift Filter
    if (appliedShift) {
      result = result.filter((e) => e.shift === appliedShift);
    }
    // Search Term Filter
    if (searchTerm.trim()) {
      const term = searchTerm.toLowerCase().trim();
      result = result.filter(
        (e) =>
          e.employeeName.toLowerCase().includes(term) ||
          e.employeeCode.toLowerCase().includes(term) ||
          e.department.toLowerCase().includes(term) ||
          e.designation.toLowerCase().includes(term)
      );
    }

    // Sorting
    result.sort((a, b) => {
      const valA = a[sortField];
      const valB = b[sortField];
      if (sortOrder === "asc") {
        return valA.localeCompare(valB);
      } else {
        return valB.localeCompare(valA);
      }
    });

    return result;
  }, [allEmployees, appliedBranch, appliedDept, appliedShift, searchTerm, sortField, sortOrder]);

  // Paginated View Items
  const paginatedEmployees = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return processedEmployees.slice(start, start + pageSize);
  }, [processedEmployees, currentPage, pageSize]);

  const totalPages = Math.ceil(processedEmployees.length / pageSize) || 1;

  // Handlers
  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setAppliedBranch(selectedBranch);
    setAppliedDept(selectedDept);
    setAppliedShift(selectedShift);
    setCurrentPage(1);

    setTimeout(() => {
      setIsLoading(false);
    }, 300);
  };

  const handleResetFilters = () => {
    setIsLoading(true);
    setFromDate("2026-07-01");
    setToDate("2026-07-15");
    setSelectedBranch("");
    setSelectedDept("");
    setSelectedShift("");
    setSearchTerm("");
    setAppliedBranch("");
    setAppliedDept("");
    setAppliedShift("");
    setCurrentPage(1);

    setTimeout(() => {
      setIsLoading(false);
    }, 300);
  };

  const toggleSort = (field: "employeeCode" | "employeeName" | "department") => {
    if (sortField === field) {
      setSortOrder((prev) => (prev === "asc" ? "desc" : "asc"));
    } else {
      setSortField(field);
      setSortOrder("asc");
    }
  };

  // Status Badge Color Renderer (Compliant with Requirements)
  const renderStatusBadge = (cell: MockPunchCell) => {
    switch (cell.status) {
      case "PRESENT":
        return (
          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-bold bg-emerald-100 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300">
            <CheckCircle2 className="w-3 h-3" /> P
          </span>
        );
      case "LATE":
        return (
          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-bold bg-amber-100 dark:bg-amber-950/60 text-amber-800 dark:text-amber-300">
            <AlertCircle className="w-3 h-3" /> LATE
          </span>
        );
      case "EARLY_OUT":
        return (
          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-bold bg-yellow-100 dark:bg-yellow-950/60 text-yellow-800 dark:text-yellow-300">
            <Clock className="w-3 h-3" /> EO
          </span>
        );
      case "MISSING_PUNCH":
        return (
          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-bold bg-orange-100 dark:bg-orange-950/60 text-orange-800 dark:text-orange-300">
            <AlertTriangle className="w-3 h-3" /> MIS
          </span>
        );
      case "ABSENT":
        return (
          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-bold bg-rose-100 dark:bg-rose-950/60 text-rose-700 dark:text-rose-300">
            <XCircle className="w-3 h-3" /> A
          </span>
        );
      case "LEAVE":
        return (
          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-bold bg-sky-100 dark:bg-sky-950/60 text-sky-700 dark:text-sky-300">
            <Palmtree className="w-3 h-3" /> L
          </span>
        );
      case "HOLIDAY":
        return (
          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-bold bg-purple-100 dark:bg-purple-950/60 text-purple-700 dark:text-purple-300">
            <Sparkles className="w-3 h-3" /> H
          </span>
        );
      case "WEEK_OFF":
        return (
          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-bold bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400">
            <Moon className="w-3 h-3" /> WO
          </span>
        );
      default:
        return null;
    }
  };

  return (
    <div className="p-6 max-w-[1700px] mx-auto space-y-6">
      {/* Title Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100 flex items-center gap-2">
            Daily Punch Report
            <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-sky-100 dark:bg-sky-900/50 text-sky-700 dark:text-sky-300 border border-sky-200 dark:border-sky-800">
              Mock Preview Mode
            </span>
          </h1>
          <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
            Multi-day punch matrix detailing first check-in, last check-out, missing punch warnings, and off-days.
          </p>
        </div>

        {/* Action Buttons (UI Only) */}
        <div className="flex items-center gap-3">
          <button
            type="button"
            aria-label="Export to Excel"
            className="inline-flex items-center gap-2 px-4 py-2 border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-200 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 rounded-lg text-sm font-medium transition-colors shadow-sm focus:ring-2 focus:ring-sky-500 focus:outline-none"
          >
            <FileSpreadsheet className="w-4 h-4 text-emerald-600" />
            Export Excel
          </button>
          <button
            type="button"
            aria-label="Export to PDF"
            className="inline-flex items-center gap-2 px-4 py-2 border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-200 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 rounded-lg text-sm font-medium transition-colors shadow-sm focus:ring-2 focus:ring-sky-500 focus:outline-none"
          >
            <FileText className="w-4 h-4 text-rose-600" />
            Export PDF
          </button>
        </div>
      </div>

      {/* Filter Toolbar Card */}
      <div className="bg-white dark:bg-slate-800 p-4 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm space-y-4">
        <form onSubmit={handleSearchSubmit} className="flex flex-wrap items-center gap-4">
          {/* Date Range Picker */}
          <div className="flex items-center bg-slate-50 dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg p-1">
            <Calendar className="w-4 h-4 text-slate-400 ml-2 mr-1" />
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
          <div className="min-w-[160px]">
            <select
              aria-label="Branch Select"
              value={selectedBranch}
              onChange={(e) => setSelectedBranch(e.target.value)}
              className="w-full bg-slate-50 dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-sm font-medium text-slate-700 dark:text-slate-200 focus:ring-2 focus:ring-sky-500 px-3 py-2"
            >
              <option value="">All Branches</option>
              {BRANCHES.map((b) => (
                <option key={b} value={b}>
                  {b}
                </option>
              ))}
            </select>
          </div>

          {/* Department Select */}
          <div className="min-w-[160px]">
            <select
              aria-label="Department Select"
              value={selectedDept}
              onChange={(e) => setSelectedDept(e.target.value)}
              className="w-full bg-slate-50 dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-sm font-medium text-slate-700 dark:text-slate-200 focus:ring-2 focus:ring-sky-500 px-3 py-2"
            >
              <option value="">All Departments</option>
              {DEPARTMENTS.map((d) => (
                <option key={d} value={d}>
                  {d}
                </option>
              ))}
            </select>
          </div>

          {/* Shift Select */}
          <div className="min-w-[160px]">
            <select
              aria-label="Shift Select"
              value={selectedShift}
              onChange={(e) => setSelectedShift(e.target.value)}
              className="w-full bg-slate-50 dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-sm font-medium text-slate-700 dark:text-slate-200 focus:ring-2 focus:ring-sky-500 px-3 py-2"
            >
              <option value="">All Shifts</option>
              {SHIFTS.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>

          {/* Search Button */}
          <button
            type="submit"
            className="inline-flex items-center gap-2 px-5 py-2 bg-sky-600 hover:bg-sky-700 text-white rounded-lg text-sm font-medium transition-colors shadow-sm focus:ring-2 focus:ring-sky-500 focus:outline-none"
          >
            <Search className="w-4 h-4" />
            Search
          </button>

          {/* Reset Button */}
          <button
            type="button"
            onClick={handleResetFilters}
            className="inline-flex items-center gap-2 px-4 py-2 border border-slate-300 dark:border-slate-700 text-slate-600 dark:text-slate-300 bg-slate-50 dark:bg-slate-900 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg text-sm font-medium transition-colors focus:ring-2 focus:ring-sky-500 focus:outline-none"
          >
            <RotateCcw className="w-4 h-4" />
            Reset
          </button>

          {/* Search Input */}
          <div className="ml-auto w-full sm:w-64">
            <div className="relative">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                aria-label="Quick Search"
                placeholder="Search employee / code..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-9 pr-4 py-2 bg-slate-50 dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg text-sm text-slate-800 dark:text-slate-200 focus:ring-2 focus:ring-sky-500 focus:outline-none"
              />
            </div>
          </div>
        </form>
      </div>

      {/* Main Matrix Table Container */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm overflow-hidden">
        <div className="overflow-x-auto max-h-[600px] overflow-y-auto">
          <table className="w-full border-collapse text-left text-xs text-slate-700 dark:text-slate-200">
            {/* Sticky Table Header */}
            <thead className="sticky top-0 z-20 bg-slate-100 dark:bg-slate-900 border-b border-slate-200 dark:border-slate-700">
              <tr>
                {/* Sticky Left Column 1: Employee Code */}
                <th
                  onClick={() => toggleSort("employeeCode")}
                  className="sticky left-0 z-30 bg-slate-100 dark:bg-slate-900 py-3 px-4 min-w-[110px] font-semibold text-slate-700 dark:text-slate-200 cursor-pointer select-none border-r border-slate-200 dark:border-slate-700"
                >
                  <div className="flex items-center gap-1">
                    Emp Code
                    <ArrowUpDown className="w-3 h-3 text-slate-400" />
                  </div>
                </th>

                {/* Sticky Left Column 2: Employee Name */}
                <th
                  onClick={() => toggleSort("employeeName")}
                  className="sticky left-[110px] z-30 bg-slate-100 dark:bg-slate-900 py-3 px-4 min-w-[150px] font-semibold text-slate-700 dark:text-slate-200 cursor-pointer select-none border-r border-slate-200 dark:border-slate-700"
                >
                  <div className="flex items-center gap-1">
                    Employee Name
                    <ArrowUpDown className="w-3 h-3 text-slate-400" />
                  </div>
                </th>

                {/* Sticky Left Column 3: Department */}
                <th
                  onClick={() => toggleSort("department")}
                  className="sticky left-[260px] z-30 bg-slate-100 dark:bg-slate-900 py-3 px-4 min-w-[130px] font-semibold text-slate-700 dark:text-slate-200 cursor-pointer select-none border-r border-slate-200 dark:border-slate-700"
                >
                  <div className="flex items-center gap-1">
                    Department
                    <ArrowUpDown className="w-3 h-3 text-slate-400" />
                  </div>
                </th>

                {/* Sticky Left Column 4: Designation */}
                <th className="sticky left-[390px] z-30 bg-slate-100 dark:bg-slate-900 py-3 px-4 min-w-[130px] font-semibold text-slate-700 dark:text-slate-200 border-r-2 border-slate-300 dark:border-slate-600">
                  Designation
                </th>

                {/* Dynamic Date Column Headers */}
                {dateList.map(({ dateStr, dayNumber, monthName, dayName }) => (
                  <th
                    key={dateStr}
                    className="py-2 px-3 min-w-[130px] text-center border-r border-slate-200 dark:border-slate-700 whitespace-nowrap"
                  >
                    <div className="font-bold text-slate-800 dark:text-slate-100">
                      {dayNumber} {monthName}
                    </div>
                    <div className="text-[10px] text-slate-500 dark:text-slate-400 font-normal">
                      {dayName}
                    </div>
                  </th>
                ))}
              </tr>
            </thead>

            {/* Table Body */}
            <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
              {/* Skeleton Loader */}
              {isLoading &&
                Array.from({ length: 5 }).map((_, idx) => (
                  <tr key={idx} className="animate-pulse">
                    <td className="sticky left-0 bg-white dark:bg-slate-800 py-4 px-4 border-r border-slate-200 dark:border-slate-700"><div className="h-4 bg-slate-200 dark:bg-slate-700 rounded w-16" /></td>
                    <td className="sticky left-[110px] bg-white dark:bg-slate-800 py-4 px-4 border-r border-slate-200 dark:border-slate-700"><div className="h-4 bg-slate-200 dark:bg-slate-700 rounded w-28" /></td>
                    <td className="sticky left-[260px] bg-white dark:bg-slate-800 py-4 px-4 border-r border-slate-200 dark:border-slate-700"><div className="h-4 bg-slate-200 dark:bg-slate-700 rounded w-20" /></td>
                    <td className="sticky left-[390px] bg-white dark:bg-slate-800 py-4 px-4 border-r-2 border-slate-300 dark:border-slate-600"><div className="h-4 bg-slate-200 dark:bg-slate-700 rounded w-20" /></td>
                    {dateList.map((d) => (
                      <td key={d.dateStr} className="py-4 px-3 border-r border-slate-100 dark:border-slate-800 text-center">
                        <div className="h-6 bg-slate-200 dark:bg-slate-700 rounded w-20 mx-auto" />
                      </td>
                    ))}
                  </tr>
                ))}

              {/* Data Rows */}
              {!isLoading &&
                paginatedEmployees.length > 0 &&
                paginatedEmployees.map((emp) => (
                  <tr
                    key={emp.employeeId}
                    className="hover:bg-slate-50/80 dark:hover:bg-slate-700/50 transition-colors"
                  >
                    {/* Sticky Column 1: Emp Code */}
                    <td className="sticky left-0 z-10 bg-white dark:bg-slate-800 py-3 px-4 font-semibold text-slate-900 dark:text-slate-100 border-r border-slate-200 dark:border-slate-700">
                      {emp.employeeCode}
                    </td>

                    {/* Sticky Column 2: Emp Name */}
                    <td className="sticky left-[110px] z-10 bg-white dark:bg-slate-800 py-3 px-4 font-medium text-slate-800 dark:text-slate-200 border-r border-slate-200 dark:border-slate-700">
                      {emp.employeeName}
                    </td>

                    {/* Sticky Column 3: Dept */}
                    <td className="sticky left-[260px] z-10 bg-white dark:bg-slate-800 py-3 px-4 text-slate-600 dark:text-slate-400 border-r border-slate-200 dark:border-slate-700">
                      {emp.department}
                    </td>

                    {/* Sticky Column 4: Designation */}
                    <td className="sticky left-[390px] z-10 bg-white dark:bg-slate-800 py-3 px-4 text-slate-600 dark:text-slate-400 border-r-2 border-slate-300 dark:border-slate-600">
                      {emp.designation}
                    </td>

                    {/* Dynamic Punch Matrix Cells */}
                    {dateList.map(({ dateStr }) => {
                      const cell = emp.punches[dateStr] || {
                        firstIn: null,
                        lastOut: null,
                        status: "ABSENT",
                        isLate: false,
                        isEarlyOut: false,
                        isMissingPunch: false,
                        isWeekOff: false,
                        isHoliday: false,
                        isLeave: false,
                        punchCount: 0,
                      };

                      return (
                        <td
                          key={dateStr}
                          className="py-2.5 px-3 text-center border-r border-slate-100 dark:border-slate-800 whitespace-nowrap"
                        >
                          <div className="flex flex-col items-center justify-center gap-1">
                            {/* Status Badge */}
                            {renderStatusBadge(cell)}

                            {/* Punch Timestamps */}
                            {cell.firstIn || cell.lastOut ? (
                              <div className="text-[11px] font-medium text-slate-700 dark:text-slate-300 flex items-center justify-center gap-1 mt-0.5">
                                <span className={cell.isLate ? "text-amber-600 dark:text-amber-400 font-semibold" : ""}>
                                  {cell.firstIn || "-"}
                                </span>
                                <span className="text-slate-400">/</span>
                                <span className={cell.isEarlyOut || cell.isMissingPunch ? "text-rose-600 dark:text-rose-400 font-semibold" : ""}>
                                  {cell.lastOut || "-"}
                                </span>
                              </div>
                            ) : (
                              <div className="text-[11px] text-slate-400 dark:text-slate-500 font-medium">
                                - / -
                              </div>
                            )}
                          </div>
                        </td>
                      );
                    })}
                  </tr>
                ))}

              {/* Empty State */}
              {!isLoading && paginatedEmployees.length === 0 && (
                <tr>
                  <td
                    colSpan={4 + (dateList.length || 1)}
                    className="py-12 text-center text-slate-500 dark:text-slate-400"
                  >
                    <div className="flex flex-col items-center justify-center gap-2">
                      <Clock className="w-8 h-8 text-slate-300 dark:text-slate-600" />
                      <p className="text-sm font-medium">No matching daily punch records found.</p>
                      <p className="text-xs text-slate-400">
                        Try adjusting search terms or filter selections.
                      </p>
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Responsive Pagination Footer */}
        <div className="p-4 bg-white dark:bg-slate-800 border-t border-slate-200 dark:border-slate-700 flex flex-col sm:flex-row items-center justify-between gap-4">
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Showing <span className="font-medium text-slate-700 dark:text-slate-200">{paginatedEmployees.length}</span> of{" "}
            <span className="font-medium text-slate-700 dark:text-slate-200">{processedEmployees.length}</span> employees
          </p>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setCurrentPage((prev) => Math.max(prev - 1, 1))}
              disabled={currentPage <= 1 || isLoading}
              className="inline-flex items-center gap-1 px-3 py-1.5 border border-slate-300 dark:border-slate-700 rounded-md text-xs font-medium text-slate-600 dark:text-slate-300 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 disabled:opacity-50 transition-colors focus:ring-2 focus:ring-sky-500 focus:outline-none"
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
              className="inline-flex items-center gap-1 px-3 py-1.5 border border-slate-300 dark:border-slate-700 rounded-md text-xs font-medium text-slate-600 dark:text-slate-300 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 disabled:opacity-50 transition-colors focus:ring-2 focus:ring-sky-500 focus:outline-none"
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
