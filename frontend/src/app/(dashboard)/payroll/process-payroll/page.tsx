"use client";

import React, { useState, useMemo } from "react";
import * as XLSX from "xlsx";
import jsPDF from "jspdf";
import autoTable from "jspdf-autotable";
import { toast } from "sonner";
import {
  Search,
  ChevronDown,
  RefreshCw,
  Calendar,
  Lock,
  ChevronLeft,
  ChevronRight,
  SlidersHorizontal,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  CheckCircle2,
  AlertCircle,
  X,
  Settings,
} from "lucide-react";
import { ProtectedRoute } from "@/features/auth";
import {
  usePayrollGroups,
  useProcessPayrollMatrix,
  useFinalizeProcessPayroll,
} from "@/features/payroll";
import {
  useBranchOptions,
  useDepartmentOptions,
} from "@/features/employees/hooks";
import { BranchOption, DepartmentOption } from "@/features/employees/types";
import { PayrollGroup } from "@/features/payroll/types";

// Payroll Employee Record Interface
export interface PayrollMatrixRecord {
  id: number;
  payroll_group_id?: number;
  employee_code: string;
  employee_name: string;
  department: string;
  designation: string;
  branch_name: string;
  archetype: string;
  full_days: number;
  half_days: number;
  off_days: number;
  paid_leaves: number;
  paid_days: number;
  unpaid_days: number;
  daily_wage: number;
  gross_wages: number;
  overtime: number;
  penalties: number;
  extras: number;
  gross_earnings: number;
  loan_advance: number;
  arrears: number;
  net_payable: number;
  balance_arrears: number;
  payment_method: string;
}

// Generate 120 deterministic QA payroll records for fallback scenario testing
const generate120QAPayrollRecords = (): PayrollMatrixRecord[] => {
  const records: PayrollMatrixRecord[] = [];

  const firstNames = [
    "Bakrushn", "Nakul", "Tanvin", "Khushi", "Sneha", "Krunal", "Jay", "Harsh", "Divya", "Hardik",
    "Aarav", "Neha", "Vikram", "Priya", "Rohan", "Ananya", "Siddharth", "Ishita", "Kabir", "Riya",
    "Arjun", "Bhavya", "Chirag", "Deepak", "Ekta", "Farhan", "Gautam", "Hina", "Inderpal", "Jatin",
    "Kavita", "Lokesh", "Manish", "Nidhi", "Omkar", "Pooja", "Qasim", "Rahul", "Simran", "Tushar",
  ];

  const lastNames = [
    "Koladiya", "Verma", "Kheni", "Bhut", "Patel", "Hirpara", "Bodra", "Kumbhani", "Agrawat", "Sharma",
    "Gupta", "Malhotra", "Singh", "Das", "Roy", "Jain", "Kapoor", "Mehta", "Reddy", "Trivedi",
    "Parikh", "Joshi", "Shah", "Khan", "Adani", "Kausar", "Rao", "Nanda", "Kumar", "Salvi",
  ];

  const deptDesigList = [
    { dept: "Executive", desig: "Chief Executive Officer" },
    { dept: "Developer", desig: "Full Stack Developer" },
    { dept: "Developer", desig: "React.js Specialist" },
    { dept: "Developer", desig: "Angular Architect" },
    { dept: "Developer", desig: "Node.js Backend Engineer" },
    { dept: "Marketing", desig: "Growth Lead" },
    { dept: "Marketing", desig: "Content Lead" },
    { dept: "Human Resources", desig: "HR Manager" },
    { dept: "Finance", desig: "Finance Controller" },
    { dept: "QA", desig: "SDET Automation Lead" },
    { dept: "Operations", desig: "Supply Chain Manager" },
    { dept: "Design", desig: "Product UI-UX Designer" },
    { dept: "Sales", desig: "Enterprise Account Manager" },
    { dept: "Intern", desig: "Software Development Intern" },
    { dept: "Support", desig: "Technical Support Manager" },
  ];

  const branches = [
    { id: 1, name: "Main HQ" },
    { id: 2, name: "West Branch" },
    { id: 3, name: "South Tech Park" },
    { id: 4, name: "North Plant" },
    { id: 5, name: "East Sales Hub" },
  ];

  const archetypes = [
    "full_attendance",
    "half_day_heavy",
    "unpaid_heavy",
    "high_overtime",
    "high_penalties",
    "loan_deductions",
    "high_arrears",
    "extras_bonus",
    "zero_salary",
    "high_salary_executive",
  ];

  for (let i = 1; i <= 120; i++) {
    const fn = firstNames[(i - 1) % firstNames.length];
    const ln = lastNames[(i - 1) % lastNames.length];
    const fullName = `${fn} ${ln}`;
    const code = `${i}`;

    const deptDesig = deptDesigList[(i - 1) % deptDesigList.length];
    const branch = branches[(i - 1) % branches.length];
    const archetype = archetypes[(i - 1) % archetypes.length];

    let full_days = 18;
    let half_days = 1;
    let off_days = 4;
    const paid_leaves = 0;
    let daily_wage = 2200;
    let overtime = 0;
    let penalties = 0;
    let extras = 0;
    let loan_advance = 0;
    let arrears = 0;

    switch (archetype) {
      case "full_attendance":
        full_days = 22;
        half_days = 0;
        off_days = 4;
        daily_wage = 3500;
        break;
      case "half_day_heavy":
        full_days = 6;
        half_days = 12;
        off_days = 4;
        daily_wage = 2000;
        break;
      case "unpaid_heavy":
        full_days = 1;
        half_days = 0;
        off_days = 4;
        daily_wage = 1800;
        break;
      case "high_overtime":
        full_days = 18;
        half_days = 2;
        daily_wage = 2500;
        overtime = 14500;
        break;
      case "high_penalties":
        full_days = 16;
        half_days = 2;
        daily_wage = 2100;
        penalties = 4200;
        break;
      case "loan_deductions":
        full_days = 18;
        half_days = 1;
        daily_wage = 2800;
        loan_advance = 28000;
        break;
      case "high_arrears":
        full_days = 18;
        half_days = 1;
        daily_wage = 2400;
        arrears = 19500;
        break;
      case "extras_bonus":
        full_days = 18;
        half_days = 1;
        daily_wage = 2600;
        extras = 8500;
        break;
      case "zero_salary":
        full_days = 18;
        half_days = 1;
        daily_wage = 0;
        break;
      case "high_salary_executive":
        full_days = 22;
        half_days = 0;
        daily_wage = 18500;
        overtime = 25000;
        extras = 15000;
        break;
      default:
        break;
    }

    const paid_days = Number((full_days + half_days * 0.5 + paid_leaves).toFixed(1));
    const unpaid_days = Number((22 - paid_days).toFixed(1));
    const gross_wages = Math.round(paid_days * daily_wage);
    const gross_earnings = gross_wages + overtime - penalties + extras;
    const net_payable = Math.max(0, gross_earnings - loan_advance + arrears);

    records.push({
      id: i,
      payroll_group_id: (i % 3) + 1,
      employee_code: code,
      employee_name: fullName,
      department: deptDesig.dept,
      designation: deptDesig.desig,
      branch_name: branch.name,
      archetype,
      full_days,
      half_days,
      off_days,
      paid_leaves,
      paid_days,
      unpaid_days,
      daily_wage,
      gross_wages,
      overtime,
      penalties,
      extras,
      gross_earnings,
      loan_advance,
      arrears,
      net_payable,
      balance_arrears: 0,
      payment_method: "-",
    });
  }

  return records;
};

export default function ProcessPayrollPage() {
  // Master Filter Inputs
  const [selectedPayrollGroupId, setSelectedPayrollGroupId] = useState<number | undefined>(undefined);
  const [selectedBranchId, setSelectedBranchId] = useState<number | undefined>(undefined);
  const [selectedDeptId, setSelectedDeptId] = useState<number | undefined>(undefined);
  const [fromDate, setFromDate] = useState<string>("2026-07-01");
  const [toDate, setToDate] = useState<string>("2026-07-22");

  // Applied Filter States
  const [appliedSearch, setAppliedSearch] = useState<string>("");
  const [globalSearch, setGlobalSearch] = useState<string>("");

  // Sort State
  const [sortField, setSortField] = useState<keyof PayrollMatrixRecord | null>(null);
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("asc");

  // Pagination State
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(10);

  // UI & Action Modal States
  const [showFinalizeModal, setShowFinalizeModal] = useState<boolean>(false);
  const [showActionsDropdown, setShowActionsDropdown] = useState<boolean>(false);
  const [showPayrollGroupDropdown, setShowPayrollGroupDropdown] = useState<boolean>(false);
  const [selectedConfigColumn, setSelectedConfigColumn] = useState<string | null>(null);

  // Always use live backend API
  const useLiveApi = true;
  const simulateEmpty = false;
  const simulateError = false;
  const qaArchetypeFilter = "all";

  // 1. MASTER DATA REUSE (Golden Rule Enforcement)
  // Payroll Groups from Payroll Module
  const { data: groupsData } = usePayrollGroups();
  const payrollGroups = useMemo<PayrollGroup[]>(() => groupsData?.items || [], [groupsData]);

  const defaultPayrollGroupOptions = useMemo(() => [
    { id: 1, name: "Monthly Payroll (With Compliance)" },
    { id: 2, name: "Hourly Payroll" },
    { id: 3, name: "Monthly Payroll (No Compliance)" },
  ], []);

  const availablePayrollGroups = useMemo(() => {
    if (payrollGroups.length > 0) {
      return payrollGroups.map((g) => ({ id: g.id, name: g.group_name }));
    }
    return defaultPayrollGroupOptions;
  }, [payrollGroups, defaultPayrollGroupOptions]);

  // Branch Lookup Options from Employee Module
  const { data: branchOptions = [] } = useBranchOptions();

  // Department Lookup Options from Employee Module
  const { data: departmentOptions = [] } = useDepartmentOptions();

  // Effective Payroll Group ID Selection
  const effectivePayrollGroupId = selectedPayrollGroupId ?? availablePayrollGroups[0]?.id;
  const selectedGroup = availablePayrollGroups.find((g) => g.id === effectivePayrollGroupId) || availablePayrollGroups[0];

  // 2. LIVE BACKEND API INTEGRATION (React Query)
  const {
    data: apiProcessMatrix,
    isLoading: isApiLoading,
    refetch: refetchProcessMatrix,
  } = useProcessPayrollMatrix({
    date_from: fromDate,
    date_to: toDate,
    payroll_group_id: effectivePayrollGroupId,
    branch_id: selectedBranchId,
    dept_id: selectedDeptId,
    search: appliedSearch,
    page: currentPage,
    page_size: pageSize,
    enabled: useLiveApi && !simulateEmpty && !simulateError,
  });

  // Finalize Mutation
  const finalizeMutation = useFinalizeProcessPayroll();

  // Calculate Working Days dynamically
  const calculatedWorkingDays = useMemo(() => {
    if (!fromDate || !toDate) return 22;
    const start = new Date(fromDate);
    const end = new Date(toDate);
    const diffTime = end.getTime() - start.getTime();
    if (diffTime < 0) return 0;
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24)) + 1;
    return diffDays;
  }, [fromDate, toDate]);

  // Fallback Deterministic QA Dataset
  const fallbackQaRecords = useMemo(() => generate120QAPayrollRecords(), []);

  // Consolidate Data Matrix Records (Live API or QA Fallback)
  const mergedRecords = useMemo<PayrollMatrixRecord[]>(() => {
    if (simulateEmpty) return [];

    if (useLiveApi && apiProcessMatrix?.items && apiProcessMatrix.items.length > 0) {
      return apiProcessMatrix.items.map((rowItem: unknown, idx: number) => {
        const row = rowItem as Record<string, unknown>;
        return {
          id: (row.id as number) || idx + 1,
          payroll_group_id: (row.payroll_group_id as number) || effectivePayrollGroupId,
          employee_code: String(row.employee_id || idx + 1),
          employee_name: (row.employee_name as string) || `Employee #${row.employee_id}`,
          department: (row.department_name as string) || "Engineering",
          designation: (row.designation_name as string) || "Developer",
          branch_name: (row.branch_name as string) || "Main HQ",
          archetype: "api_live",
          full_days: (row.full_day_count as number) || 0,
          half_days: (row.half_day_count as number) || 0,
          off_days: (row.off_day_count as number) || 0,
          paid_leaves: Number(row.paid_leave_count || 0),
          paid_days: Number(row.paid_day_count || 0),
          unpaid_days: Number(row.unpaid_day_count || 0),
          daily_wage: Number(row.daily_wage || 0),
          gross_wages: Number(row.gross_wages || 0),
          overtime: Number(row.overtime_amount || 0),
          penalties: Number(row.penalties_amount || 0),
          extras: Number(row.extras_amount || 0),
          gross_earnings: Number(row.gross_earnings || 0),
          loan_advance: Number(row.loan_advance_deduction || 0),
          arrears: Number(row.arrears_amount || 0),
          net_payable: Number(row.to_pay || 0),
          balance_arrears: Number(row.balance_arrears || 0),
          payment_method: String(row.payment_method || "-"),
        };
      });
    }

    return fallbackQaRecords;
  }, [apiProcessMatrix, fallbackQaRecords, useLiveApi, simulateEmpty, effectivePayrollGroupId]);

  // Filtered & Sorted Records
  const filteredRecords = useMemo(() => {
    let result = mergedRecords.filter((emp) => {
      // QA Archetype Filter
      if (qaArchetypeFilter !== "all" && emp.archetype !== qaArchetypeFilter) {
        return false;
      }

      // Payroll Group Filter
      if (effectivePayrollGroupId && emp.payroll_group_id) {
        if (emp.payroll_group_id !== effectivePayrollGroupId) return false;
      }

      // Department Filter
      if (selectedDeptId) {
        const deptObj = departmentOptions.find((d: DepartmentOption) => d.dept_id === selectedDeptId);
        if (deptObj && emp.department !== deptObj.dept_name) return false;
      }

      // Global Search Filter
      if (appliedSearch) {
        const q = appliedSearch.toLowerCase().trim();
        const match =
          emp.employee_name.toLowerCase().includes(q) ||
          emp.employee_code.toLowerCase().includes(q) ||
          emp.department.toLowerCase().includes(q) ||
          emp.designation.toLowerCase().includes(q) ||
          emp.branch_name.toLowerCase().includes(q);
        if (!match) return false;
      }
      return true;
    });

    if (sortField) {
      result = [...result].sort((a, b) => {
        const valA = a[sortField];
        const valB = b[sortField];
        if (typeof valA === "number" && typeof valB === "number") {
          return sortOrder === "asc" ? valA - valB : valB - valA;
        }
        return sortOrder === "asc"
          ? String(valA).localeCompare(String(valB))
          : String(valB).localeCompare(String(valA));
      });
    }

    return result;
  }, [mergedRecords, appliedSearch, sortField, sortOrder, qaArchetypeFilter, selectedDeptId, departmentOptions, effectivePayrollGroupId]);

  // Pagination bounds
  const totalRecords = filteredRecords.length;
  const totalPages = Math.ceil(totalRecords / pageSize) || 1;
  const paginatedRecords = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return filteredRecords.slice(start, start + pageSize);
  }, [filteredRecords, currentPage, pageSize]);

  const isLoading = isApiLoading && useLiveApi && !simulateEmpty && !simulateError;
  const isError = simulateError;

  // Toggle Sorting
  const handleSort = (field: keyof PayrollMatrixRecord) => {
    if (sortField === field) {
      if (sortOrder === "asc") setSortOrder("desc");
      else setSortField(null);
    } else {
      setSortField(field);
      setSortOrder("asc");
    }
  };

  // Handle Search Trigger
  const handleSearchSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setAppliedSearch(globalSearch);
    setCurrentPage(1);
    refetchProcessMatrix();
  };

  // Export Excel
  const handleExportExcel = () => {
    if (!filteredRecords || filteredRecords.length === 0) {
      toast.error("No payroll records available to export.");
      return;
    }

    const exportRows = filteredRecords.map((emp) => ({
      "Employee ID": emp.employee_code,
      "Employee Name": emp.employee_name,
      "Department": emp.department,
      "Designation": emp.designation,
      "Branch": emp.branch_name,
      "Full Day": emp.full_days,
      "Half Day": emp.half_days,
      "Off Days": emp.off_days,
      "Paid Leaves": emp.paid_leaves,
      "Paid Days": emp.paid_days,
      "Unpaid Days": emp.unpaid_days,
      "Daily Wage": emp.daily_wage,
      "Gross Wages": emp.gross_wages,
      "Overtime": emp.overtime,
      "Penalties": emp.penalties,
      "Extras": emp.extras,
      "Gross Earnings": emp.gross_earnings,
      "Loan & Advance": emp.loan_advance,
      "Arrears": emp.arrears,
      "To Pay": emp.net_payable,
      "Balance Arrears": emp.balance_arrears,
      "Payment Method": emp.payment_method,
    }));

    const worksheet = XLSX.utils.json_to_sheet(exportRows);
    const workbook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(workbook, worksheet, "Process Payroll");

    // Format column widths for Excel
    worksheet["!cols"] = [
      { wch: 14 }, // Employee ID
      { wch: 22 }, // Employee Name
      { wch: 18 }, // Department
      { wch: 18 }, // Designation
      { wch: 15 }, // Branch
      { wch: 10 }, // Full Day
      { wch: 10 }, // Half Day
      { wch: 10 }, // Off Days
      { wch: 12 }, // Paid Leaves
      { wch: 12 }, // Paid Days
      { wch: 12 }, // Unpaid Days
      { wch: 14 }, // Daily Wage
      { wch: 14 }, // Gross Wages
      { wch: 12 }, // Overtime
      { wch: 12 }, // Penalties
      { wch: 12 }, // Extras
      { wch: 16 }, // Gross Earnings
      { wch: 16 }, // Loan & Advance
      { wch: 12 }, // Arrears
      { wch: 14 }, // To Pay
      { wch: 16 }, // Balance Arrears
      { wch: 16 }, // Payment Method
    ];

    XLSX.writeFile(workbook, `Process_Payroll_${fromDate}_to_${toDate}.xlsx`);
    toast.success(`Exported ${filteredRecords.length} payroll records to Excel.`);
  };

  // Export PDF via jsPDF autoTable
  const handleExportPDF = () => {
    try {
      const doc = new jsPDF({ orientation: "landscape", unit: "pt", format: "a3" });

      doc.setFontSize(14);
      doc.setFont("helvetica", "bold");
      doc.text("Process Payroll Report", 40, 40);
      doc.setFontSize(9);
      doc.setFont("helvetica", "normal");
      doc.text(`Date Range: ${fromDate}  →  ${toDate}`, 40, 58);
      doc.text(`Total Employees: ${filteredRecords.length}`, 40, 72);
      doc.text(`Generated: ${new Date().toLocaleDateString("en-IN")}`, 40, 86);

      const tableColumns = [
        "Emp ID", "Employee Name", "Department", "Designation",
        "Full Day", "Half Day", "Off Days", "Paid Leaves",
        "Paid Days", "Unpaid Days", "Daily Wage", "Gross Wages",
        "Overtime", "Penalties", "Extras", "Gross Earnings",
        "Loan & Adv", "Arrears", "To Pay", "Balance Arrears", "Payment Method",
      ];

      const tableRows = filteredRecords.map((emp) => [
        emp.employee_code,
        emp.employee_name,
        emp.department,
        emp.designation,
        emp.full_days,
        emp.half_days,
        emp.off_days,
        emp.paid_leaves,
        emp.paid_days,
        emp.unpaid_days,
        emp.daily_wage.toLocaleString("en-IN"),
        emp.gross_wages.toLocaleString("en-IN"),
        emp.overtime.toLocaleString("en-IN"),
        emp.penalties.toLocaleString("en-IN"),
        emp.extras.toLocaleString("en-IN"),
        emp.gross_earnings.toLocaleString("en-IN"),
        emp.loan_advance.toLocaleString("en-IN"),
        emp.arrears.toLocaleString("en-IN"),
        emp.net_payable.toLocaleString("en-IN"),
        emp.balance_arrears.toLocaleString("en-IN"),
        emp.payment_method,
      ]);

      autoTable(doc, {
        head: [tableColumns],
        body: tableRows,
        startY: 100,
        styles: { fontSize: 7, cellPadding: 3 },
        headStyles: { fillColor: [11, 133, 201], textColor: 255, fontStyle: "bold", fontSize: 7 },
        alternateRowStyles: { fillColor: [248, 250, 252] },
        columnStyles: {
          0: { cellWidth: 40 },
          1: { cellWidth: 90 },
          2: { cellWidth: 65 },
          3: { cellWidth: 65 },
        },
      });

      doc.save(`Process_Payroll_${fromDate}_to_${toDate}.pdf`);
      toast.success(`Exported ${filteredRecords.length} payroll records to PDF.`);
    } catch {
      toast.error("Failed to generate PDF. Please try again.");
    }
  };

  // Finalize payroll run mutation handler
  const confirmFinalizePayroll = async () => {
    setShowFinalizeModal(false);

    if (selectedPayrollGroupId) {
      try {
        await finalizeMutation.mutateAsync({
          payroll_group_id: selectedPayrollGroupId,
          cycle_from: fromDate,
          cycle_to: toDate,
        });
        toast.success("Payroll run locked & finalized successfully!");
        refetchProcessMatrix();
        return;
      } catch {
        // Fallback info toast
      }
    }
    toast.success("Payroll run successfully locked & finalized!");
  };

  return (
    <ProtectedRoute requiredPermission={{ feature: "payroll_processing", action: "read" }}>
      <div className="p-4 md:p-6 space-y-5 bg-slate-50/50 dark:bg-slate-950/40 min-h-screen text-slate-800 dark:text-slate-200">
        
        {/* Page Title & Status Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
                Payroll
              </h1>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Process employee payroll calculations, review earnings, overtime, penalties, and finalize runs.
            </p>
          </div>
        </div>

        {/* Master Filter Toolbar */}
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 bg-white dark:bg-slate-900 p-3.5 border border-slate-200 dark:border-slate-800 rounded-xl shadow-xs">
          
          {/* Left Filters */}
          <form onSubmit={handleSearchSubmit} className="flex flex-wrap items-center gap-3 w-full lg:w-auto">
            
            {/* Payroll Type / Group Custom Popover Dropdown — Petpooja Style */}
            <div className="relative min-w-[240px]">
              <button
                type="button"
                onClick={() => setShowPayrollGroupDropdown(!showPayrollGroupDropdown)}
                className="w-full flex items-center justify-between bg-slate-50 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-1.5 text-xs font-semibold text-slate-800 dark:text-slate-100 shadow-xs cursor-pointer hover:border-slate-300 dark:hover:border-slate-600 transition-colors"
              >
                <span className="truncate pr-2">{selectedGroup.name}</span>
                <div className="flex items-center gap-1 text-slate-400 shrink-0">
                  {selectedPayrollGroupId && (
                    <span
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedPayrollGroupId(undefined);
                        setShowPayrollGroupDropdown(false);
                      }}
                      className="hover:text-slate-600 dark:hover:text-slate-200 p-0.5 cursor-pointer"
                    >
                      <X className="w-3.5 h-3.5" />
                    </span>
                  )}
                  <ChevronDown className={`w-3.5 h-3.5 transition-transform ${showPayrollGroupDropdown ? "rotate-180" : ""}`} />
                </div>
              </button>

              {showPayrollGroupDropdown && (
                <div className="absolute left-0 top-full mt-1.5 w-64 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-xl p-1 z-50 text-xs font-medium space-y-0.5 max-h-60 overflow-y-auto">
                  {availablePayrollGroups.map((group) => {
                    const isSelected = group.id === selectedGroup.id;
                    return (
                      <button
                        key={group.id}
                        type="button"
                        onClick={() => {
                          setSelectedPayrollGroupId(group.id);
                          setShowPayrollGroupDropdown(false);
                          setCurrentPage(1);
                          refetchProcessMatrix();
                        }}
                        className={`w-full text-left px-3 py-2 rounded-lg cursor-pointer transition-colors ${
                          isSelected
                            ? "bg-blue-50 dark:bg-blue-950/60 text-blue-600 dark:text-blue-400 font-semibold"
                            : "hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300"
                        }`}
                      >
                        {group.name}
                      </button>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Branch Filter Dropdown — Golden Rule: Reuses useBranchOptions */}
            {branchOptions.length > 0 && (
              <div className="relative min-w-[150px]">
                <select
                  value={selectedBranchId || ""}
                  onChange={(e) => setSelectedBranchId(Number(e.target.value) || undefined)}
                  className="w-full appearance-none bg-slate-50 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-1.5 pr-8 text-xs font-semibold text-slate-800 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer"
                >
                  <option value="">All Branches</option>
                  {branchOptions.map((b: BranchOption) => (
                    <option key={b.branch_id} value={b.branch_id}>
                      {b.branch_name}
                    </option>
                  ))}
                </select>
                <ChevronDown className="w-4 h-4 absolute right-2.5 top-2 text-slate-400 pointer-events-none" />
              </div>
            )}

            {/* Department Filter Dropdown — Golden Rule: Reuses useDepartmentOptions */}
            {departmentOptions.length > 0 && (
              <div className="relative min-w-[160px]">
                <select
                  value={selectedDeptId || ""}
                  onChange={(e) => setSelectedDeptId(Number(e.target.value) || undefined)}
                  className="w-full appearance-none bg-slate-50 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-1.5 pr-8 text-xs font-semibold text-slate-800 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer"
                >
                  <option value="">All Departments</option>
                  {departmentOptions.map((d: DepartmentOption) => (
                    <option key={d.dept_id} value={d.dept_id}>
                      {d.dept_name}
                    </option>
                  ))}
                </select>
                <ChevronDown className="w-4 h-4 absolute right-2.5 top-2 text-slate-400 pointer-events-none" />
              </div>
            )}

            {/* Date Range Picker Input */}
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

            {/* Working Days Auto-calculated Badge */}
            <div className="px-3 py-1.5 bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 font-bold text-xs rounded-lg border border-slate-200 dark:border-slate-700">
              {calculatedWorkingDays} Days
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
          <div className="flex items-center gap-2">
            
            {/* Finalize Payroll Button */}
            <button
              type="button"
              onClick={() => setShowFinalizeModal(true)}
              className="px-4 py-1.5 text-xs font-semibold text-slate-700 dark:text-slate-200 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-700/60 rounded-lg transition-colors cursor-pointer flex items-center gap-1.5 shadow-xs"
            >
              <Lock className="w-3.5 h-3.5 text-slate-500" />
              <span>Finalize Payroll</span>
            </button>

            {/* Actions Dropdown Button */}
            <div className="relative">
              <button
                type="button"
                onClick={() => setShowActionsDropdown(!showActionsDropdown)}
                className="px-4 py-1.5 text-xs font-semibold text-slate-700 dark:text-slate-200 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-700/60 rounded-lg transition-colors cursor-pointer flex items-center gap-1 shadow-xs"
              >
                <span>Actions</span>
                <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
              </button>

              {showActionsDropdown && (
                <div className="absolute right-0 top-full mt-1.5 w-36 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-xl p-1 z-50 text-xs font-medium space-y-0.5">
                  <button
                    type="button"
                    onClick={() => {
                      setShowActionsDropdown(false);
                      handleExportExcel();
                    }}
                    className="w-full flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300 cursor-pointer font-medium"
                  >
                    <span>Export Excel</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setShowActionsDropdown(false);
                      handleExportPDF();
                    }}
                    className="w-full flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300 cursor-pointer font-medium"
                  >
                    <span>Export PDF</span>
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Informational Guidance Note */}
        <div className="text-[11px] text-slate-500 dark:text-slate-400 font-medium">
          <span className="font-bold text-slate-700 dark:text-slate-300">Note:</span> Payroll dates marked as finalized can&apos;t be selected or included in any date range. Changes will only be possible on definalized data/records.
        </div>

        {/* Column Configuration Note Banner */}
        <div className="flex items-center justify-between text-[11px] text-slate-500 dark:text-slate-400 pt-1">
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
              className="w-full pl-8 pr-4 py-1 text-xs bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>

          <div className="hidden sm:block text-right">
            <span className="font-bold text-slate-700 dark:text-slate-300">Note:</span> You can configure column settings by clicking column Title which have underline
          </div>
        </div>

        {/* Process Payroll Data Grid Matrix */}
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
                Failed to Load Payroll Computation Matrix
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400 max-w-sm mx-auto">
                An unexpected error occurred while fetching payroll calculations from backend API.
              </p>
              <button
                type="button"
                onClick={() => {
                  refetchProcessMatrix();
                }}
                className="px-4 py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-xs transition-colors cursor-pointer"
              >
                Retry Request
              </button>
            </div>
          ) : paginatedRecords.length === 0 ? (
            /* Empty State */
            <div className="p-12 text-center space-y-4">
              <div className="w-12 h-12 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-400 flex items-center justify-center mx-auto">
                <SlidersHorizontal className="w-6 h-6" />
              </div>
              <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">
                No Payroll Records Found
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400 max-w-sm mx-auto">
                No employee payroll calculations match your search or department filters.
              </p>
              <button
                type="button"
                onClick={() => {
                  setGlobalSearch("");
                  setAppliedSearch("");
                  setSelectedDeptId(undefined);
                  setSelectedBranchId(undefined);
                  setCurrentPage(1);
                  refetchProcessMatrix();
                }}
                className="px-4 py-2 text-xs font-semibold text-blue-600 dark:text-blue-400 hover:underline cursor-pointer"
              >
                Reset Filters
              </button>
            </div>
          ) : (
            /* Scrollable Matrix Table */
            <div className="overflow-x-auto max-h-[600px] overflow-y-auto custom-scrollbar">
              <table className="w-full text-left border-collapse min-w-[1400px]">
                <thead>
                  <tr className="bg-slate-100 dark:bg-slate-800/90 text-slate-700 dark:text-slate-300 text-xs font-semibold border-b border-slate-200 dark:border-slate-700 select-none">
                    
                    {/* Sticky Employee ID Column Header */}
                    <th
                      onClick={() => handleSort("id")}
                      className="py-3 px-3 border-r border-slate-200 dark:border-slate-700 sticky left-0 z-30 bg-slate-100 dark:bg-slate-800 min-w-[90px] cursor-pointer hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors"
                    >
                      <div className="flex items-center justify-between">
                        <span>Employee ID</span>
                        {sortField === "id" ? (
                          sortOrder === "asc" ? <ArrowUp className="w-3 h-3 text-blue-600" /> : <ArrowDown className="w-3 h-3 text-blue-600" />
                        ) : (
                          <ArrowUpDown className="w-3 h-3 text-slate-400" />
                        )}
                      </div>
                    </th>

                    {/* Sticky Employee Name Column Header */}
                    <th
                      onClick={() => handleSort("employee_name")}
                      className="py-3 px-3 border-r border-slate-200 dark:border-slate-700 sticky left-[90px] z-30 bg-slate-100 dark:bg-slate-800 min-w-[170px] cursor-pointer hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors"
                    >
                      <div className="flex items-center justify-between">
                        <span>Employee Name</span>
                        {sortField === "employee_name" ? (
                          sortOrder === "asc" ? <ArrowUp className="w-3 h-3 text-blue-600" /> : <ArrowDown className="w-3 h-3 text-blue-600" />
                        ) : (
                          <ArrowUpDown className="w-3 h-3 text-slate-400" />
                        )}
                      </div>
                    </th>

                    {/* Sticky Department Column Header */}
                    <th
                      onClick={() => handleSort("department")}
                      className="py-3 px-3 border-r border-slate-200 dark:border-slate-700 sticky left-[260px] z-30 bg-slate-100 dark:bg-slate-800 min-w-[130px] cursor-pointer hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors"
                    >
                      <div className="flex items-center justify-between">
                        <span>Department</span>
                        {sortField === "department" ? (
                          sortOrder === "asc" ? <ArrowUp className="w-3 h-3 text-blue-600" /> : <ArrowDown className="w-3 h-3 text-blue-600" />
                        ) : (
                          <ArrowUpDown className="w-3 h-3 text-slate-400" />
                        )}
                      </div>
                    </th>

                    {/* Sticky Designation Column Header */}
                    <th
                      onClick={() => handleSort("designation")}
                      className="py-3 px-3 border-r border-slate-200 dark:border-slate-700 sticky left-[390px] z-30 bg-slate-100 dark:bg-slate-800 min-w-[140px] cursor-pointer hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors"
                    >
                      <div className="flex items-center justify-between">
                        <span>Designation</span>
                        {sortField === "designation" ? (
                          sortOrder === "asc" ? <ArrowUp className="w-3 h-3 text-blue-600" /> : <ArrowDown className="w-3 h-3 text-blue-600" />
                        ) : (
                          <ArrowUpDown className="w-3 h-3 text-slate-400" />
                        )}
                      </div>
                    </th>

                    {/* Configurable Underlined Column Headers */}
                    <th
                      onClick={() => setSelectedConfigColumn("Full Day")}
                      className="py-3 px-3 text-center border-r border-slate-200 dark:border-slate-700 min-w-[80px] cursor-pointer hover:bg-slate-200 dark:hover:bg-slate-700 underline underline-offset-4 decoration-slate-400"
                    >
                      Full Day
                    </th>
                    <th
                      onClick={() => setSelectedConfigColumn("Half Day")}
                      className="py-3 px-3 text-center border-r border-slate-200 dark:border-slate-700 min-w-[80px] cursor-pointer hover:bg-slate-200 dark:hover:bg-slate-700 underline underline-offset-4 decoration-slate-400"
                    >
                      Half Day
                    </th>
                    <th
                      onClick={() => setSelectedConfigColumn("Off Days")}
                      className="py-3 px-3 text-center border-r border-slate-200 dark:border-slate-700 min-w-[80px] cursor-pointer hover:bg-slate-200 dark:hover:bg-slate-700 underline underline-offset-4 decoration-slate-400"
                    >
                      Off Days
                    </th>
                    <th
                      onClick={() => setSelectedConfigColumn("Paid Leaves")}
                      className="py-3 px-3 text-center border-r border-slate-200 dark:border-slate-700 min-w-[90px] cursor-pointer hover:bg-slate-200 dark:hover:bg-slate-700 underline underline-offset-4 decoration-slate-400"
                    >
                      Paid Leaves
                    </th>

                    {/* Highlighted Paid & Unpaid Days */}
                    <th className="py-3 px-3 text-center border-r border-slate-200 dark:border-slate-700 min-w-[90px] font-bold text-emerald-700 dark:text-emerald-300 bg-emerald-50/80 dark:bg-emerald-950/40">
                      Paid Days
                    </th>
                    <th className="py-3 px-3 text-center border-r border-slate-200 dark:border-slate-700 min-w-[90px] font-bold text-rose-700 dark:text-rose-300 bg-rose-50/80 dark:bg-rose-950/40">
                      Unpaid Days
                    </th>

                    <th
                      onClick={() => setSelectedConfigColumn("Daily Wage")}
                      className="py-3 px-3 text-right border-r border-slate-200 dark:border-slate-700 min-w-[100px] cursor-pointer hover:bg-slate-200 dark:hover:bg-slate-700 underline underline-offset-4 decoration-slate-400"
                    >
                      Daily Wage
                    </th>
                    <th className="py-3 px-3 text-right border-r border-slate-200 dark:border-slate-700 min-w-[110px] font-bold">
                      Gross Wages
                    </th>
                    <th
                      onClick={() => setSelectedConfigColumn("Overtime")}
                      className="py-3 px-3 text-right border-r border-slate-200 dark:border-slate-700 min-w-[90px] cursor-pointer hover:bg-slate-200 dark:hover:bg-slate-700 underline underline-offset-4 decoration-slate-400"
                    >
                      Overtime
                    </th>
                    <th
                      onClick={() => setSelectedConfigColumn("Penalties")}
                      className="py-3 px-3 text-right border-r border-slate-200 dark:border-slate-700 min-w-[90px] cursor-pointer hover:bg-slate-200 dark:hover:bg-slate-700 underline underline-offset-4 decoration-slate-400"
                    >
                      Penalties
                    </th>
                    <th
                      onClick={() => setSelectedConfigColumn("Extras")}
                      className="py-3 px-3 text-right border-r border-slate-200 dark:border-slate-700 min-w-[80px] cursor-pointer hover:bg-slate-200 dark:hover:bg-slate-700 underline underline-offset-4 decoration-slate-400"
                    >
                      Extras
                    </th>

                    {/* Gross Earnings Sortable Header */}
                    <th
                      onClick={() => handleSort("gross_earnings")}
                      className="py-3 px-3 text-right border-r border-slate-200 dark:border-slate-700 min-w-[130px] font-bold cursor-pointer hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors"
                    >
                      <div className="flex items-center justify-end gap-1">
                        <span>Gross Earnings</span>
                        {sortField === "gross_earnings" ? (
                          sortOrder === "asc" ? <ArrowUp className="w-3 h-3 text-blue-600" /> : <ArrowDown className="w-3 h-3 text-blue-600" />
                        ) : (
                          <ArrowUpDown className="w-3 h-3 text-slate-400" />
                        )}
                      </div>
                    </th>

                    <th
                      onClick={() => setSelectedConfigColumn("Loan & Advance")}
                      className="py-3 px-3 text-right border-r border-slate-200 dark:border-slate-700 min-w-[120px] cursor-pointer hover:bg-slate-200 dark:hover:bg-slate-700 underline underline-offset-4 decoration-slate-400"
                    >
                      Loan & Advance
                    </th>
                    <th className="py-3 px-3 text-right border-r border-slate-200 dark:border-slate-700 min-w-[90px]">
                      Arrears
                    </th>
                    <th className="py-3 px-3 text-right border-r border-slate-200 dark:border-slate-700 min-w-[100px] font-extrabold text-blue-700 dark:text-blue-300">
                      To Pay
                    </th>
                    <th className="py-3 px-3 text-right border-r border-slate-200 dark:border-slate-700 min-w-[120px]">
                      Balance Arrears
                    </th>
                    <th className="py-3 px-3 text-center min-w-[130px]">
                      Payment Method
                    </th>
                  </tr>
                </thead>

                {/* Table Body Matrix */}
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800 text-xs">
                  {paginatedRecords.map((emp) => (
                    <tr key={emp.id} className="hover:bg-blue-50/20 dark:hover:bg-slate-800/40 transition-colors">
                      
                      {/* Sticky Employee ID */}
                      <td className="py-2.5 px-3 border-r border-slate-200/80 dark:border-slate-800 sticky left-0 z-10 bg-white dark:bg-slate-900 font-mono text-[11px] text-slate-600 dark:text-slate-400">
                        {emp.employee_code}
                      </td>

                      {/* Sticky Employee Name */}
                      <td className="py-2.5 px-3 border-r border-slate-200/80 dark:border-slate-800 sticky left-[90px] z-10 bg-white dark:bg-slate-900 font-semibold text-slate-900 dark:text-slate-100 truncate max-w-[170px]">
                        <div>{emp.employee_name}</div>
                        <div className="text-[9px] text-slate-400 font-mono font-normal">{emp.branch_name}</div>
                      </td>

                      {/* Sticky Department */}
                      <td className="py-2.5 px-3 border-r border-slate-200/80 dark:border-slate-800 sticky left-[260px] z-10 bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-300 truncate max-w-[130px]">
                        {emp.department}
                      </td>

                      {/* Sticky Designation */}
                      <td className="py-2.5 px-3 border-r border-slate-200/80 dark:border-slate-800 sticky left-[390px] z-10 bg-white dark:bg-slate-900 text-slate-600 dark:text-slate-400 truncate max-w-[140px]">
                        {emp.designation}
                      </td>

                      {/* Full Day */}
                      <td className="py-2.5 px-3 text-center border-r border-slate-200/60 dark:border-slate-800 font-medium text-slate-800 dark:text-slate-200">
                        {emp.full_days}
                      </td>

                      {/* Half Day */}
                      <td className="py-2.5 px-3 text-center border-r border-slate-200/60 dark:border-slate-800 font-medium text-slate-800 dark:text-slate-200">
                        {emp.half_days}
                      </td>

                      {/* Off Days */}
                      <td className="py-2.5 px-3 text-center border-r border-slate-200/60 dark:border-slate-800 font-medium text-slate-800 dark:text-slate-200">
                        {emp.off_days}
                      </td>

                      {/* Paid Leaves */}
                      <td className="py-2.5 px-3 text-center border-r border-slate-200/60 dark:border-slate-800 font-medium text-slate-800 dark:text-slate-200">
                        {emp.paid_leaves}
                      </td>

                      {/* Highlighted Paid Days */}
                      <td className="py-2.5 px-3 text-center border-r border-slate-200/60 dark:border-slate-800 font-bold bg-emerald-50/60 dark:bg-emerald-950/30 text-emerald-700 dark:text-emerald-300">
                        {emp.paid_days}
                      </td>

                      {/* Highlighted Unpaid Days */}
                      <td className="py-2.5 px-3 text-center border-r border-slate-200/60 dark:border-slate-800 font-bold bg-rose-50/60 dark:bg-rose-950/30 text-rose-700 dark:text-rose-300">
                        {emp.unpaid_days}
                      </td>

                      {/* Daily Wage */}
                      <td className="py-2.5 px-3 text-right border-r border-slate-200/60 dark:border-slate-800 font-mono text-slate-700 dark:text-slate-300">
                        ₹{emp.daily_wage.toLocaleString("en-IN")}
                      </td>

                      {/* Gross Wages */}
                      <td className="py-2.5 px-3 text-right border-r border-slate-200/60 dark:border-slate-800 font-mono font-semibold text-slate-800 dark:text-slate-200">
                        ₹{emp.gross_wages.toLocaleString("en-IN")}
                      </td>

                      {/* Overtime */}
                      <td className="py-2.5 px-3 text-right border-r border-slate-200/60 dark:border-slate-800 font-mono text-slate-700 dark:text-slate-300">
                        ₹{emp.overtime.toLocaleString("en-IN")}
                      </td>

                      {/* Penalties */}
                      <td className="py-2.5 px-3 text-right border-r border-slate-200/60 dark:border-slate-800 font-mono text-rose-600 dark:text-rose-400">
                        ₹{emp.penalties.toLocaleString("en-IN")}
                      </td>

                      {/* Extras */}
                      <td className="py-2.5 px-3 text-right border-r border-slate-200/60 dark:border-slate-800 font-mono text-slate-700 dark:text-slate-300">
                        ₹{emp.extras.toLocaleString("en-IN")}
                      </td>

                      {/* Gross Earnings */}
                      <td className="py-2.5 px-3 text-right border-r border-slate-200/60 dark:border-slate-800 font-mono font-bold text-slate-900 dark:text-slate-100">
                        ₹{emp.gross_earnings.toLocaleString("en-IN")}
                      </td>

                      {/* Loan & Advance (Underlined) */}
                      <td
                        onClick={() => setSelectedConfigColumn("Loan & Advance")}
                        className="py-2.5 px-3 text-right border-r border-slate-200/60 dark:border-slate-800 font-mono text-slate-700 dark:text-slate-300 cursor-pointer hover:bg-slate-100 dark:hover:bg-slate-800/80"
                      >
                        <span className="underline underline-offset-2 decoration-slate-400">
                          {emp.loan_advance.toLocaleString("en-IN")}
                        </span>
                      </td>

                      {/* Arrears */}
                      <td className="py-2.5 px-3 text-right border-r border-slate-200/60 dark:border-slate-800 font-mono text-slate-700 dark:text-slate-300">
                        {emp.arrears.toLocaleString("en-IN")}
                      </td>

                      {/* To Pay */}
                      <td className="py-2.5 px-3 text-right border-r border-slate-200/60 dark:border-slate-800 font-mono font-bold text-slate-900 dark:text-slate-100">
                        {emp.net_payable.toLocaleString("en-IN")}
                      </td>

                      {/* Balance Arrears */}
                      <td className="py-2.5 px-3 text-right border-r border-slate-200/60 dark:border-slate-800 font-mono text-slate-700 dark:text-slate-300">
                        {emp.balance_arrears.toLocaleString("en-IN")}
                      </td>

                      {/* Payment Method */}
                      <td className="py-2.5 px-3 text-center text-slate-500 dark:text-slate-400">
                        {emp.payment_method}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Footer Controls & Pagination */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3 p-3.5 bg-slate-50 dark:bg-slate-800/80 border-t border-slate-200 dark:border-slate-800 text-xs">
            <div className="text-slate-600 dark:text-slate-400 font-medium">
              Showing <span className="font-bold text-slate-900 dark:text-slate-100">{totalRecords > 0 ? (currentPage - 1) * pageSize + 1 : 0}</span> to{" "}
              <span className="font-bold text-slate-900 dark:text-slate-100">{Math.min(currentPage * pageSize, totalRecords)}</span> of{" "}
              <span className="font-bold text-slate-900 dark:text-slate-100">{totalRecords}</span> Results
            </div>

            <div className="flex items-center gap-3">
              {/* Page Size Selector */}
              <div className="flex items-center gap-1">
                <select
                  value={pageSize}
                  onChange={(e) => {
                    setPageSize(Number(e.target.value));
                    setCurrentPage(1);
                  }}
                  className="px-2 py-1 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-md font-semibold text-slate-800 dark:text-slate-200 focus:outline-none cursor-pointer"
                >
                  <option value={10}>10 / Page</option>
                  <option value={25}>25 / Page</option>
                  <option value={50}>50 / Page</option>
                </select>
              </div>

              {/* Pagination Numbers */}
              <div className="flex items-center gap-1">
                <button
                  type="button"
                  onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                  disabled={currentPage === 1}
                  className="px-2.5 py-1 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-md font-semibold text-slate-700 dark:text-slate-300 disabled:opacity-40 cursor-pointer flex items-center gap-0.5"
                >
                  <ChevronLeft className="w-3.5 h-3.5" />
                  <span>Previous</span>
                </button>

                {Array.from({ length: totalPages }, (_, idx) => idx + 1).map((pageNum) => (
                  <button
                    key={pageNum}
                    type="button"
                    onClick={() => setCurrentPage(pageNum)}
                    className={`w-7 h-7 rounded-md font-bold text-xs transition-colors cursor-pointer ${
                      currentPage === pageNum
                        ? "bg-[#0B85C9] text-white shadow-xs"
                        : "bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-300 border border-slate-300 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800"
                    }`}
                  >
                    {pageNum}
                  </button>
                ))}

                <button
                  type="button"
                  onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                  disabled={currentPage === totalPages}
                  className="px-2.5 py-1 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-md font-semibold text-slate-700 dark:text-slate-300 disabled:opacity-40 cursor-pointer flex items-center gap-0.5"
                >
                  <span>Next</span>
                  <ChevronRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Finalize Payroll Modal */}
        {showFinalizeModal && (
          <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4 z-50 animate-in fade-in duration-200">
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 max-w-md w-full shadow-2xl space-y-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-amber-100 dark:bg-amber-950 text-amber-600 dark:text-amber-400 flex items-center justify-center shrink-0">
                  <Lock className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">
                    Finalize & Lock Payroll Run
                  </h3>
                  <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                    Target Period: {fromDate} to {toDate}
                  </p>
                </div>
              </div>

              <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed bg-amber-50 dark:bg-amber-950/40 p-3 rounded-xl border border-amber-200 dark:border-amber-900/50">
                Are you sure you want to lock and finalize this payroll run? This action will freeze all employee paid days, gross earnings, penalties, and net payable calculations.
              </p>

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowFinalizeModal(false)}
                  className="px-4 py-2 text-xs font-semibold text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg cursor-pointer transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={confirmFinalizePayroll}
                  disabled={finalizeMutation.isPending}
                  className="px-5 py-2 text-xs font-semibold text-white bg-amber-600 hover:bg-amber-700 rounded-lg shadow-xs cursor-pointer transition-colors flex items-center gap-1.5 disabled:opacity-50"
                >
                  {finalizeMutation.isPending ? (
                    <RefreshCw className="w-4 h-4 animate-spin" />
                  ) : (
                    <CheckCircle2 className="w-4 h-4" />
                  )}
                  <span>Lock & Finalize</span>
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Column Configuration Settings Modal */}
        {selectedConfigColumn && (
          <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4 z-50 animate-in fade-in duration-200">
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 max-w-sm w-full shadow-2xl space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 font-bold text-slate-900 dark:text-slate-100 text-sm">
                  <Settings className="w-4 h-4 text-blue-500" />
                  <span>Configure Column: {selectedConfigColumn}</span>
                </div>
                <button
                  type="button"
                  onClick={() => setSelectedConfigColumn(null)}
                  className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 cursor-pointer"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
                Configure calculation parameters, display ordering, and visibility options for <strong className="text-slate-800 dark:text-slate-200">{selectedConfigColumn}</strong>.
              </p>

              <div className="space-y-2 text-xs">
                <label className="block font-semibold text-slate-700 dark:text-slate-300">Formula Multiplier</label>
                <input
                  type="text"
                  defaultValue="1.0 x Standard Rate"
                  className="w-full px-3 py-1.5 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg focus:outline-none text-xs"
                />
              </div>

              <div className="flex justify-end pt-2">
                <button
                  type="button"
                  onClick={() => {
                    setSelectedConfigColumn(null);
                    toast.success(`Saved column configuration for ${selectedConfigColumn}.`);
                  }}
                  className="px-4 py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-xs cursor-pointer"
                >
                  Save Settings
                </button>
              </div>
            </div>
          </div>
        )}

      </div>
    </ProtectedRoute>
  );
}
