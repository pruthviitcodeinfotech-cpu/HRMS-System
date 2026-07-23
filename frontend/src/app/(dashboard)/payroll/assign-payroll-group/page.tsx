"use client";

import React, { useState, useMemo } from "react";
import Link from "next/link";
import { toast } from "sonner";
import {
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  X,
  ChevronDown,
} from "lucide-react";
import { ProtectedRoute } from "@/features/auth";
import { useEmployees } from "@/features/employees/hooks";

export interface AssignEmployeeRow {
  employee_id: number;
  employee_name: string;
  department: string;
  designation: string;
  payroll_group: string;
}

// Initial dataset matching reference screenshot 2 exactly
const INITIAL_ASSIGN_EMPLOYEES: AssignEmployeeRow[] = [
  { employee_id: 37, employee_name: "chirag kanani", department: "Developer", designation: "Full Stack", payroll_group: "Monthly Payroll (No Compliance)" },
  { employee_id: 36, employee_name: "maulik bhadani", department: "Developer", designation: "Full Stack", payroll_group: "Monthly Payroll (No Compliance)" },
  { employee_id: 35, employee_name: "Priyansh Desai", department: "Developer", designation: "Full Stack", payroll_group: "Monthly Payroll (No Compliance)" },
  { employee_id: 34, employee_name: "Kamlesh Sahu", department: "Developer", designation: "React.js", payroll_group: "Monthly Payroll (No Compliance)" },
  { employee_id: 33, employee_name: "Hepit Talaviya", department: "Graphic Designer", designation: "Graphic Designer", payroll_group: "Monthly Payroll (No Compliance)" },
  { employee_id: 31, employee_name: "Sneha Nadapara", department: "BDM", designation: "BDM", payroll_group: "Monthly Payroll (No Compliance)" },
  { employee_id: 6, employee_name: "tanvin kheni", department: "Developer", designation: "Full Stack", payroll_group: "Monthly Payroll (No Compliance)" },
  { employee_id: 28, employee_name: "Vipul Rawal", department: "Project Manager", designation: "Project Manager", payroll_group: "Monthly Payroll (No Compliance)" },
  { employee_id: 27, employee_name: "Rutvik Manvar", department: "Developer", designation: "Backend Developer", payroll_group: "Monthly Payroll (No Compliance)" },
  { employee_id: 3, employee_name: "Nakul verma", department: "Developer", designation: "Angular", payroll_group: "Monthly Payroll (No Compliance)" },
];

export default function AssignPayrollGroupPage() {
  // Active employees query from Employee module (Golden Rule)
  const { data: employeeData } = useEmployees({ page: 1, page_size: 100, status: "active" });

  const employeeRows: AssignEmployeeRow[] = useMemo(() => {
    if (employeeData?.items && employeeData.items.length > 0) {
      return employeeData.items.map((emp) => ({
        employee_id: emp.employee_id,
        employee_name: emp.employee_name,
        department: emp.department_name || "Developer",
        designation: emp.designation_name || "Full Stack",
        payroll_group: "Monthly Payroll (No Compliance)",
      }));
    }
    return INITIAL_ASSIGN_EMPLOYEES;
  }, [employeeData]);

  // Filters State
  const [selectedPayrollType, setSelectedPayrollType] = useState<string>("Monthly Payroll (No Compliance)");
  const [selectedEmployeeIds, setSelectedEmployeeIds] = useState<number[]>([]);

  // Sorting State
  const [sortField, setSortField] = useState<keyof AssignEmployeeRow>("employee_id");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");

  // Pagination State
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  // Drawer Modal State
  const [showAssignDrawer, setShowAssignDrawer] = useState(false);
  const [singleTargetEmp, setSingleTargetEmp] = useState<AssignEmployeeRow | null>(null);

  // Form State inside Assign Drawer
  const [salaryType, setSalaryType] = useState<string>("Monthly");
  const [targetGroupChoice, setTargetGroupChoice] = useState<string>("Monthly Payroll (No Compliance)");

  // Sorting Handler
  const handleSort = (field: keyof AssignEmployeeRow) => {
    if (sortField === field) {
      setSortOrder(sortOrder === "asc" ? "desc" : "asc");
    } else {
      setSortField(field);
      setSortOrder("desc");
    }
  };

  // Filtered & Sorted Employees
  const filteredEmployees = useMemo(() => {
    let result = employeeRows;
    if (selectedPayrollType) {
      result = result.filter((emp) =>
        emp.payroll_group.toLowerCase().includes(selectedPayrollType.toLowerCase())
      );
    }

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
  }, [employeeRows, selectedPayrollType, sortField, sortOrder]);

  // Paginated Rows
  const totalRecords = filteredEmployees.length;
  const paginatedRows = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return filteredEmployees.slice(start, start + pageSize);
  }, [filteredEmployees, currentPage, pageSize]);

  // Checkbox Handlers
  const handleSelectAll = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.checked) {
      setSelectedEmployeeIds(filteredEmployees.map((emp) => emp.employee_id));
    } else {
      setSelectedEmployeeIds([]);
    }
  };

  const handleToggleRow = (id: number) => {
    setSelectedEmployeeIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  // Open Single Employee Assign Drawer
  const handleOpenSingleAssign = (emp: AssignEmployeeRow) => {
    setSingleTargetEmp(emp);
    setTargetGroupChoice(emp.payroll_group);
    setShowAssignDrawer(true);
  };

  // Open Bulk Assign Drawer
  const handleOpenBulkAssign = () => {
    if (selectedEmployeeIds.length === 0) {
      toast.error("Please select at least one employee.");
      return;
    }
    setSingleTargetEmp(null);
    setShowAssignDrawer(true);
  };

  // Confirm Assign Group
  const handleConfirmAssign = () => {
    if (singleTargetEmp) {
      toast.success(`Assigned "${singleTargetEmp.employee_name}" to ${targetGroupChoice}`);
    } else {
      toast.success(`Assigned ${selectedEmployeeIds.length} employees to ${targetGroupChoice}`);
      setSelectedEmployeeIds([]);
    }
    setShowAssignDrawer(false);
  };

  return (
    <ProtectedRoute requiredPermission={{ feature: "payroll_processing", action: "read" }}>
      <div className="p-4 md:p-6 space-y-6 bg-slate-50/50 dark:bg-slate-950/40 min-h-screen text-slate-800 dark:text-slate-200">
        
        {/* Header Section matching Screenshot 2 */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
              Assign Payroll Group ({totalRecords})
            </h1>
          </div>

          <div className="flex items-center gap-3">
            {/* Payroll Group (Outline Button) */}
            <Link
              href="/payroll/payroll-group"
              className="px-4 py-2 text-xs font-semibold text-slate-700 dark:text-slate-200 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-700/60 rounded-lg transition-colors cursor-pointer shadow-xs"
            >
              Payroll Group
            </Link>

            {/* Select Group (Primary Button) */}
            <button
              type="button"
              onClick={handleOpenBulkAssign}
              disabled={selectedEmployeeIds.length === 0}
              className={`px-4 py-2 text-xs font-semibold rounded-lg transition-colors cursor-pointer shadow-xs ${
                selectedEmployeeIds.length > 0
                  ? "bg-[#0B85C9] text-white hover:bg-[#0974b0]"
                  : "bg-slate-200 text-slate-400 dark:bg-slate-800 dark:text-slate-600 cursor-not-allowed"
              }`}
            >
              Select Group
            </button>
          </div>
        </div>

        {/* Filter Bar matching Screenshot 2 */}
        <div className="bg-white dark:bg-slate-900 p-4 border border-slate-200 dark:border-slate-800 rounded-xl space-y-2">
          <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
            Payroll Type
          </label>
          
          <div className="flex items-center gap-2">
            <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-xs font-medium text-slate-800 dark:text-slate-200">
              <span>Monthly Without C...</span>
              {selectedPayrollType && (
                <button
                  type="button"
                  onClick={() => setSelectedPayrollType("")}
                  className="hover:text-red-500 cursor-pointer"
                >
                  <X className="w-3.5 h-3.5 text-slate-400 hover:text-slate-600" />
                </button>
              )}
              <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
            </div>
          </div>
        </div>

        {/* Main Data Table matching Screenshot 2 */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-xs overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse min-w-[900px]">
              <thead>
                <tr className="bg-blue-50/70 dark:bg-slate-800/90 text-slate-700 dark:text-slate-300 text-xs font-semibold border-b border-slate-200 dark:border-slate-700 select-none">
                  
                  {/* Checkbox Header */}
                  <th className="py-3 px-4 w-12 text-center">
                    <input
                      type="checkbox"
                      onChange={handleSelectAll}
                      checked={
                        filteredEmployees.length > 0 &&
                        selectedEmployeeIds.length === filteredEmployees.length
                      }
                      className="rounded border-slate-300 text-blue-600 focus:ring-blue-500 cursor-pointer"
                    />
                  </th>

                  {/* Employee ID Header */}
                  <th
                    onClick={() => handleSort("employee_id")}
                    className="py-3 px-4 min-w-[120px] cursor-pointer hover:bg-blue-100/50 dark:hover:bg-slate-700 transition-colors"
                  >
                    <div className="flex items-center gap-1.5">
                      <span>Employee ID</span>
                      {sortField === "employee_id" ? (
                        sortOrder === "asc" ? (
                          <ArrowUp className="w-3.5 h-3.5 text-blue-600" />
                        ) : (
                          <ArrowDown className="w-3.5 h-3.5 text-blue-600" />
                        )
                      ) : (
                        <ArrowUpDown className="w-3.5 h-3.5 text-slate-400" />
                      )}
                    </div>
                  </th>

                  {/* Employee Name Header */}
                  <th
                    onClick={() => handleSort("employee_name")}
                    className="py-3 px-4 min-w-[200px] cursor-pointer hover:bg-blue-100/50 dark:hover:bg-slate-700 transition-colors"
                  >
                    <div className="flex items-center gap-1.5">
                      <span>Employee Name</span>
                      {sortField === "employee_name" ? (
                        sortOrder === "asc" ? (
                          <ArrowUp className="w-3.5 h-3.5 text-blue-600" />
                        ) : (
                          <ArrowDown className="w-3.5 h-3.5 text-blue-600" />
                        )
                      ) : (
                        <ArrowUpDown className="w-3.5 h-3.5 text-slate-400" />
                      )}
                    </div>
                  </th>

                  {/* Department Header */}
                  <th
                    onClick={() => handleSort("department")}
                    className="py-3 px-4 min-w-[160px] cursor-pointer hover:bg-blue-100/50 dark:hover:bg-slate-700 transition-colors"
                  >
                    <div className="flex items-center gap-1.5">
                      <span>Department</span>
                      {sortField === "department" ? (
                        sortOrder === "asc" ? (
                          <ArrowUp className="w-3.5 h-3.5 text-blue-600" />
                        ) : (
                          <ArrowDown className="w-3.5 h-3.5 text-blue-600" />
                        )
                      ) : (
                        <ArrowUpDown className="w-3.5 h-3.5 text-slate-400" />
                      )}
                    </div>
                  </th>

                  {/* Designation Header */}
                  <th
                    onClick={() => handleSort("designation")}
                    className="py-3 px-4 min-w-[160px] cursor-pointer hover:bg-blue-100/50 dark:hover:bg-slate-700 transition-colors"
                  >
                    <div className="flex items-center gap-1.5">
                      <span>Designation</span>
                      {sortField === "designation" ? (
                        sortOrder === "asc" ? (
                          <ArrowUp className="w-3.5 h-3.5 text-blue-600" />
                        ) : (
                          <ArrowDown className="w-3.5 h-3.5 text-blue-600" />
                        )
                      ) : (
                        <ArrowUpDown className="w-3.5 h-3.5 text-slate-400" />
                      )}
                    </div>
                  </th>

                  {/* Payroll Group Header */}
                  <th
                    onClick={() => handleSort("payroll_group")}
                    className="py-3 px-4 min-w-[220px] cursor-pointer hover:bg-blue-100/50 dark:hover:bg-slate-700 transition-colors"
                  >
                    <div className="flex items-center gap-1.5">
                      <span>Payroll Group</span>
                      {sortField === "payroll_group" ? (
                        sortOrder === "asc" ? (
                          <ArrowUp className="w-3.5 h-3.5 text-blue-600" />
                        ) : (
                          <ArrowDown className="w-3.5 h-3.5 text-blue-600" />
                        )
                      ) : (
                        <ArrowUpDown className="w-3.5 h-3.5 text-slate-400" />
                      )}
                    </div>
                  </th>

                  {/* Action Header */}
                  <th className="py-3 px-4 min-w-[160px]">
                    Action
                  </th>
                </tr>
              </thead>

              <tbody className="divide-y divide-slate-100 dark:divide-slate-800 text-xs">
                {paginatedRows.map((row) => {
                  const isChecked = selectedEmployeeIds.includes(row.employee_id);
                  return (
                    <tr
                      key={row.employee_id}
                      className={`hover:bg-slate-50/60 dark:hover:bg-slate-800/40 transition-colors ${
                        isChecked ? "bg-blue-50/30 dark:bg-blue-950/20" : ""
                      }`}
                    >
                      {/* Checkbox Cell */}
                      <td className="py-3.5 px-4 text-center">
                        <input
                          type="checkbox"
                          checked={isChecked}
                          onChange={() => handleToggleRow(row.employee_id)}
                          className="rounded border-slate-300 text-blue-600 focus:ring-blue-500 cursor-pointer"
                        />
                      </td>

                      {/* Employee ID */}
                      <td className="py-3.5 px-4 font-medium text-slate-700 dark:text-slate-300">
                        {row.employee_id}
                      </td>

                      {/* Employee Name */}
                      <td className="py-3.5 px-4 font-medium text-slate-900 dark:text-slate-100">
                        {row.employee_name}
                      </td>

                      {/* Department */}
                      <td className="py-3.5 px-4 text-slate-700 dark:text-slate-300">
                        {row.department}
                      </td>

                      {/* Designation */}
                      <td className="py-3.5 px-4 text-slate-700 dark:text-slate-300">
                        {row.designation}
                      </td>

                      {/* Payroll Group */}
                      <td className="py-3.5 px-4 text-slate-700 dark:text-slate-300">
                        {row.payroll_group}
                      </td>

                      {/* Action Button */}
                      <td className="py-3.5 px-4">
                        <button
                          type="button"
                          onClick={() => handleOpenSingleAssign(row)}
                          className="px-3 py-1.5 text-xs font-semibold text-slate-700 dark:text-slate-200 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-700/60 rounded-lg transition-colors cursor-pointer"
                        >
                          Assign Payroll Group
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Footer Controls & Pagination */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3 p-3.5 bg-white dark:bg-slate-900 border-t border-slate-200 dark:border-slate-800 text-xs">
            <div className="text-slate-600 dark:text-slate-400 font-medium">
              Showing <span className="font-bold text-slate-900 dark:text-slate-100">{totalRecords > 0 ? (currentPage - 1) * pageSize + 1 : 0}</span> to{" "}
              <span className="font-bold text-slate-900 dark:text-slate-100">{Math.min(currentPage * pageSize, totalRecords)}</span> of{" "}
              <span className="font-bold text-slate-900 dark:text-slate-100">{totalRecords}</span> Results
            </div>

            <div className="flex items-center gap-3">
              <div className="flex items-center gap-1">
                <select
                  value={pageSize}
                  onChange={(e) => {
                    setPageSize(Number(e.target.value));
                    setCurrentPage(1);
                  }}
                  className="bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-2.5 py-1 text-xs font-semibold text-slate-800 dark:text-slate-100 cursor-pointer focus:outline-none"
                >
                  <option value={10}>10 / Page</option>
                  <option value={25}>25 / Page</option>
                  <option value={50}>50 / Page</option>
                </select>
              </div>

              <div className="flex items-center gap-1">
                <button
                  type="button"
                  disabled={currentPage === 1}
                  onClick={() => setCurrentPage((prev) => Math.max(1, prev - 1))}
                  className="px-3 py-1 text-xs font-semibold text-slate-500 border border-slate-200 dark:border-slate-700 rounded-lg disabled:opacity-40 cursor-pointer disabled:cursor-not-allowed hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
                >
                  Previous
                </button>
                
                <span className="px-3 py-1 text-xs font-semibold text-white bg-[#0B85C9] rounded-lg shadow-xs">
                  {currentPage}
                </span>

                <button
                  type="button"
                  disabled={currentPage * pageSize >= totalRecords}
                  onClick={() => setCurrentPage((prev) => prev + 1)}
                  className="px-3 py-1 text-xs font-semibold text-slate-500 border border-slate-200 dark:border-slate-700 rounded-lg disabled:opacity-40 cursor-pointer disabled:cursor-not-allowed hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
                >
                  Next
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* ---------------------------------------------------- */}
        {/* ASSIGN PAYROLL GROUP DRAWER matching Screenshot 3    */}
        {/* ---------------------------------------------------- */}
        {showAssignDrawer && (
          <div className="fixed inset-0 z-50 overflow-hidden bg-black/50 backdrop-blur-xs flex justify-end">
            <div className="w-full max-w-md bg-white dark:bg-slate-900 h-full shadow-2xl flex flex-col border-l border-slate-200 dark:border-slate-800 animate-in slide-in-from-right duration-200">
              
              {/* Drawer Header */}
              <div className="flex items-center justify-between px-6 py-4 bg-blue-50/60 dark:bg-slate-800/80 border-b border-slate-200 dark:border-slate-800">
                <h2 className="text-base font-bold text-slate-900 dark:text-slate-100">
                  Assign Payroll Group
                </h2>
                <button
                  type="button"
                  onClick={() => setShowAssignDrawer(false)}
                  className="p-1 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 cursor-pointer"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {/* Drawer Content */}
              <div className="flex-1 flex flex-col justify-between overflow-hidden">
                <div className="p-6 space-y-6 text-xs overflow-y-auto flex-1">
                  
                  {/* Salary Type Dropdown */}
                  <div>
                    <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                      Salary Type
                    </label>
                    <select
                      value={salaryType}
                      onChange={(e) => setSalaryType(e.target.value)}
                      className="w-full p-2.5 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg font-medium text-slate-800 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer"
                    >
                      <option value="Monthly">Monthly</option>
                      <option value="Hourly">Hourly</option>
                    </select>
                  </div>

                  {/* Payroll Group Radio Options */}
                  <div>
                    <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-2">
                      Payroll Group
                    </label>

                    <div className="space-y-2.5">
                      <label className="flex items-center gap-2.5 cursor-pointer">
                        <input
                          type="radio"
                          name="target_payroll_group"
                          value="Monthly Payroll (No Compliance)"
                          checked={targetGroupChoice === "Monthly Payroll (No Compliance)"}
                          onChange={(e) => setTargetGroupChoice(e.target.value)}
                          className="w-4 h-4 text-blue-600 focus:ring-blue-500 cursor-pointer"
                        />
                        <span className="font-medium text-slate-800 dark:text-slate-200">
                          Monthly Payroll (No Compliance)
                        </span>
                      </label>

                      <label className="flex items-center gap-2.5 cursor-pointer">
                        <input
                          type="radio"
                          name="target_payroll_group"
                          value="Hourly Payroll"
                          checked={targetGroupChoice === "Hourly Payroll"}
                          onChange={(e) => setTargetGroupChoice(e.target.value)}
                          className="w-4 h-4 text-blue-600 focus:ring-blue-500 cursor-pointer"
                        />
                        <span className="font-medium text-slate-800 dark:text-slate-200">
                          Hourly Payroll
                        </span>
                      </label>

                      <label className="flex items-center gap-2.5 cursor-pointer">
                        <input
                          type="radio"
                          name="target_payroll_group"
                          value="Monthly Payroll (With Compliance)"
                          checked={targetGroupChoice === "Monthly Payroll (With Compliance)"}
                          onChange={(e) => setTargetGroupChoice(e.target.value)}
                          className="w-4 h-4 text-blue-600 focus:ring-blue-500 cursor-pointer"
                        />
                        <span className="font-medium text-slate-800 dark:text-slate-200">
                          Monthly Payroll (With Compliance)
                        </span>
                      </label>
                    </div>
                  </div>
                </div>

                {/* Drawer Footer matching Screenshot 3 */}
                <div className="flex items-center justify-end gap-3 px-6 py-3.5 bg-blue-50/70 dark:bg-slate-800/80 border-t border-slate-200 dark:border-slate-800">
                  <button
                    type="button"
                    onClick={() => setShowAssignDrawer(false)}
                    className="px-5 py-2 text-xs font-semibold text-slate-700 dark:text-slate-300 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-700 rounded-lg cursor-pointer transition-colors"
                  >
                    Close
                  </button>
                  <button
                    type="button"
                    onClick={handleConfirmAssign}
                    className="px-5 py-2 text-xs font-semibold text-white bg-[#0B85C9] hover:bg-[#0974b0] rounded-lg cursor-pointer shadow-xs transition-colors"
                  >
                    Assign Group
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </ProtectedRoute>
  );
}
