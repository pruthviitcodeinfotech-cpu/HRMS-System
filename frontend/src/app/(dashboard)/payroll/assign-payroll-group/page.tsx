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
  AlertCircle,
  SlidersHorizontal,
} from "lucide-react";
import { ProtectedRoute } from "@/features/auth";
import { useEmployees } from "@/features/employees/hooks";
import { usePayrollGroups, useAssignEmployeesToGroup } from "@/features/payroll/hooks/use-payroll";

export interface AssignEmployeeRow {
  employee_id: number;
  employee_name: string;
  department: string;
  designation: string;
  payroll_group: string;
}

export default function AssignPayrollGroupPage() {
  // Master Data hooks (Golden Rule)
  const {
    data: employeeData,
    isLoading: isLoadingEmployees,
    isError: isErrorEmployees,
    refetch: refetchEmployees,
  } = useEmployees({ page: 1, page_size: 100, status: "active" });

  const { data: groupsData } = usePayrollGroups({ page: 1, page_size: 100 });
  const assignMutation = useAssignEmployeesToGroup();

  const groupsList = useMemo(() => groupsData?.items || [], [groupsData?.items]);

  // Employee rows mapped from Employee master data
  const employeeRows: AssignEmployeeRow[] = useMemo(() => {
    if (employeeData?.items && employeeData.items.length > 0) {
      return employeeData.items.map((emp) => ({
        employee_id: emp.employee_id,
        employee_name: emp.employee_name,
        department: emp.department_name || "-",
        designation: emp.designation_name || "-",
        payroll_group: emp.payroll_group_id
          ? groupsList.find((g) => g.id === emp.payroll_group_id)?.name || "Assigned"
          : "Unassigned",
      }));
    }
    return [];
  }, [employeeData, groupsList]);

  // Filters State
  const [selectedPayrollType, setSelectedPayrollType] = useState<string>("");
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
  const [salaryType, setSalaryType] = useState<"monthly" | "hourly">("monthly");
  const [targetGroupId, setTargetGroupId] = useState<number | null>(null);

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
      if (selectedPayrollType === "Unassigned") {
        result = result.filter((emp) => emp.payroll_group === "Unassigned");
      } else {
        result = result.filter(
          (emp) => emp.payroll_group.toLowerCase() === selectedPayrollType.toLowerCase()
        );
      }
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
    const defaultGroup = groupsList[0]?.id || null;
    setTargetGroupId(defaultGroup);
    setShowAssignDrawer(true);
  };

  // Open Bulk Assign Drawer
  const handleOpenBulkAssign = () => {
    if (selectedEmployeeIds.length === 0) {
      toast.error("Please select at least one employee.");
      return;
    }
    setSingleTargetEmp(null);
    const defaultGroup = groupsList[0]?.id || null;
    setTargetGroupId(defaultGroup);
    setShowAssignDrawer(true);
  };

  // Confirm Assign Group Mutation
  const handleConfirmAssign = async () => {
    const empIdsToAssign = singleTargetEmp
      ? [singleTargetEmp.employee_id]
      : selectedEmployeeIds;

    if (empIdsToAssign.length === 0) {
      toast.error("No employees selected for assignment.");
      return;
    }

    if (!targetGroupId && groupsList.length > 0) {
      setTargetGroupId(groupsList[0].id);
    }

    const assignedGroupId = targetGroupId || groupsList[0]?.id;
    if (!assignedGroupId) {
      toast.error("No active payroll group selected.");
      return;
    }

    try {
      await assignMutation.mutateAsync({
        groupId: assignedGroupId,
        payload: {
          employee_ids: empIdsToAssign,
          salary_type: salaryType,
        },
      });

      const groupObj = groupsList.find((g) => g.id === assignedGroupId);
      const groupName = groupObj?.name || "Payroll Group";

      if (singleTargetEmp) {
        toast.success(`Assigned "${singleTargetEmp.employee_name}" to ${groupName}`);
      } else {
        toast.success(`Assigned ${empIdsToAssign.length} employees to ${groupName}`);
        setSelectedEmployeeIds([]);
      }

      setShowAssignDrawer(false);
    } catch (err: unknown) {
      const errorObj = err as { response?: { data?: { message?: string } }; message?: string };
      const msg = errorObj?.response?.data?.message || errorObj?.message || "Failed to assign payroll group.";
      toast.error(msg);
    }
  };

  return (
    <ProtectedRoute requiredPermission={{ feature: "payroll_group", action: "read" }}>
      <div className="p-4 md:p-6 space-y-6 bg-slate-50/50 dark:bg-slate-950/40 min-h-screen text-slate-800 dark:text-slate-200">
        
        {/* Header Section */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
              Assign Payroll Group ({totalRecords})
            </h1>
          </div>

          <div className="flex items-center gap-3">
            {/* Payroll Group Outline Button */}
            <Link
              href="/payroll/payroll-group"
              className="px-4 py-2 text-xs font-semibold text-slate-700 dark:text-slate-200 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-700/60 rounded-lg transition-colors cursor-pointer shadow-xs"
            >
              Payroll Group
            </Link>

            {/* Select Group Primary Button */}
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

        {/* Filter Bar */}
        <div className="bg-white dark:bg-slate-900 p-4 border border-slate-200 dark:border-slate-800 rounded-xl space-y-2">
          <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
            Payroll Group
          </label>
          <div className="flex items-center gap-2 max-w-xs">
            <select
              value={selectedPayrollType}
              onChange={(e) => {
                setSelectedPayrollType(e.target.value);
                setCurrentPage(1);
              }}
              className="w-full p-2.5 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-xs font-medium text-slate-800 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer"
            >
              <option value="">All Payroll Groups</option>
              <option value="Unassigned">Unassigned Employees</option>
              {groupsList.map((grp) => (
                <option key={grp.id} value={grp.name}>
                  {grp.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Main Table */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-xs overflow-hidden">
          {isLoadingEmployees ? (
            <div className="p-8 space-y-4">
              <div className="h-6 bg-slate-200 dark:bg-slate-800 rounded animate-pulse w-1/4" />
              <div className="space-y-3">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="h-12 bg-slate-100 dark:bg-slate-800/50 rounded animate-pulse" />
                ))}
              </div>
            </div>
          ) : isErrorEmployees ? (
            <div className="p-12 text-center space-y-4">
              <div className="w-12 h-12 rounded-full bg-red-100 dark:bg-red-950/50 text-red-600 dark:text-red-400 flex items-center justify-center mx-auto">
                <AlertCircle className="w-6 h-6" />
              </div>
              <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">
                Failed to Load Employees
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400 max-w-sm mx-auto">
                An error occurred while fetching employee data.
              </p>
              <button
                type="button"
                onClick={() => refetchEmployees()}
                className="px-4 py-2 text-xs font-semibold text-white bg-[#0B85C9] hover:bg-[#0974b0] rounded-lg cursor-pointer"
              >
                Retry
              </button>
            </div>
          ) : paginatedRows.length === 0 ? (
            <div className="p-12 text-center space-y-4">
              <div className="w-12 h-12 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-400 flex items-center justify-center mx-auto">
                <SlidersHorizontal className="w-6 h-6" />
              </div>
              <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">
                No Employees Found
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400 max-w-sm mx-auto">
                No active employees match the current filter selection.
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse min-w-[900px]">
                <thead>
                  <tr className="bg-blue-50/70 dark:bg-slate-800/90 text-slate-700 dark:text-slate-300 text-xs font-semibold border-b border-slate-200 dark:border-slate-700 select-none">
                    <th className="py-3 px-4 w-10">
                      <input
                        type="checkbox"
                        checked={
                          paginatedRows.length > 0 &&
                          paginatedRows.every((emp) =>
                            selectedEmployeeIds.includes(emp.employee_id)
                          )
                        }
                        onChange={handleSelectAll}
                        className="rounded border-slate-300 dark:border-slate-700 text-[#0B85C9] focus:ring-[#0B85C9] cursor-pointer"
                      />
                    </th>

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

                    <th
                      onClick={() => handleSort("payroll_group")}
                      className="py-3 px-4 min-w-[240px] cursor-pointer hover:bg-blue-100/50 dark:hover:bg-slate-700 transition-colors"
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

                    <th className="py-3 px-4 min-w-[160px]">Action</th>
                  </tr>
                </thead>

                <tbody className="divide-y divide-slate-100 dark:divide-slate-800 text-xs">
                  {paginatedRows.map((emp) => (
                    <tr
                      key={emp.employee_id}
                      className="hover:bg-slate-50/60 dark:hover:bg-slate-800/40 transition-colors"
                    >
                      <td className="py-3.5 px-4">
                        <input
                          type="checkbox"
                          checked={selectedEmployeeIds.includes(emp.employee_id)}
                          onChange={() => handleToggleRow(emp.employee_id)}
                          className="rounded border-slate-300 dark:border-slate-700 text-[#0B85C9] focus:ring-[#0B85C9] cursor-pointer"
                        />
                      </td>

                      <td className="py-3.5 px-4 font-mono text-slate-700 dark:text-slate-300 font-medium">
                        {emp.employee_id}
                      </td>

                      <td className="py-3.5 px-4 font-semibold text-slate-900 dark:text-slate-100">
                        {emp.employee_name}
                      </td>

                      <td className="py-3.5 px-4 text-slate-700 dark:text-slate-300">
                        {emp.department}
                      </td>

                      <td className="py-3.5 px-4 text-slate-700 dark:text-slate-300">
                        {emp.designation}
                      </td>

                      <td className="py-3.5 px-4 text-slate-700 dark:text-slate-300 font-medium">
                        {emp.payroll_group}
                      </td>

                      <td className="py-3.5 px-4">
                        <button
                          type="button"
                          onClick={() => handleOpenSingleAssign(emp)}
                          className="px-3 py-1 text-xs font-semibold text-slate-700 dark:text-slate-200 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-700 rounded-lg cursor-pointer transition-colors shadow-2xs"
                        >
                          Assign Payroll Group
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

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
        {/* ASSIGN PAYROLL GROUP DRAWER                          */}
        {/* ---------------------------------------------------- */}
        {showAssignDrawer && (
          <div className="fixed inset-0 z-50 overflow-hidden bg-black/50 backdrop-blur-xs flex justify-end">
            <div className="w-full max-w-md bg-white dark:bg-slate-900 h-full shadow-2xl flex flex-col border-l border-slate-200 dark:border-slate-800 animate-in slide-in-from-right duration-200">
              
              {/* Drawer Header */}
              <div className="flex items-center justify-between px-6 py-4 bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800">
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

              {/* Drawer Form Body */}
              <div className="p-6 space-y-6 text-xs overflow-y-auto flex-1">
                
                {/* Salary Type Select */}
                <div>
                  <label className="block font-medium text-slate-700 dark:text-slate-300 mb-1.5">
                    Salary Type
                  </label>
                  <div className="relative">
                    <select
                      value={salaryType}
                      onChange={(e) => setSalaryType(e.target.value as "monthly" | "hourly")}
                      className="w-full p-2.5 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg font-medium text-slate-800 dark:text-slate-100 appearance-none focus:outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer pr-8"
                    >
                      <option value="monthly">Monthly</option>
                      <option value="hourly">Hourly</option>
                    </select>
                    <ChevronDown className="w-4 h-4 text-slate-400 absolute right-2.5 top-3 pointer-events-none" />
                  </div>
                </div>

                {/* Payroll Group Select Dropdown */}
                <div>
                  <label className="block font-medium text-slate-700 dark:text-slate-300 mb-1.5">
                    Payroll Group
                  </label>
                  <div className="relative">
                    <select
                      value={targetGroupId || ""}
                      onChange={(e) => setTargetGroupId(Number(e.target.value) || null)}
                      className="w-full p-2.5 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg font-medium text-slate-800 dark:text-slate-100 appearance-none focus:outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer pr-8"
                    >
                      {groupsList.length === 0 ? (
                        <option value="">No Groups Available</option>
                      ) : (
                        groupsList.map((grp) => (
                          <option key={grp.id} value={grp.id}>
                            {grp.name}
                          </option>
                        ))
                      )}
                    </select>
                    <ChevronDown className="w-4 h-4 text-slate-400 absolute right-2.5 top-3 pointer-events-none" />
                  </div>
                </div>
              </div>

              {/* Drawer Footer */}
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
                  disabled={assignMutation.isPending}
                  onClick={handleConfirmAssign}
                  className="px-5 py-2 text-xs font-semibold text-white bg-[#0B85C9] hover:bg-[#0974b0] rounded-lg shadow-xs cursor-pointer transition-colors disabled:opacity-50"
                >
                  Assign Group
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </ProtectedRoute>
  );
}
