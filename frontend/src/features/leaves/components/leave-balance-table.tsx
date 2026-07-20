"use client";

import { useState, useMemo } from "react";
import { ArrowUpDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import { LeaveBalanceEmployee } from "../types";

interface LeaveBalanceTableProps {
  employees: LeaveBalanceEmployee[];
  leaveColumns?: string[];
  isLoading?: boolean;
  selectedIds?: string[];
  onSelectionChange?: (ids: string[]) => void;
}

export function LeaveBalanceTable({
  employees,
  leaveColumns = ["Comp Off"],
  isLoading = false,
  selectedIds: controlledSelectedIds,
  onSelectionChange,
}: LeaveBalanceTableProps) {
  const [internalSelectedIds, setInternalSelectedIds] = useState<string[]>([]);
  const selectedIds = controlledSelectedIds ?? internalSelectedIds;

  const updateSelectedIds = (newIds: string[]) => {
    if (onSelectionChange) {
      onSelectionChange(newIds);
    } else {
      setInternalSelectedIds(newIds);
    }
  };

  const [sortField, setSortField] = useState<"employeeId" | "name" | "department" | "designation">("employeeId");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(10);

  // Toggle sorting
  const handleSort = (field: "employeeId" | "name" | "department" | "designation") => {
    if (sortField === field) {
      setSortOrder((prev) => (prev === "asc" ? "desc" : "asc"));
    } else {
      setSortField(field);
      setSortOrder("asc");
    }
  };

  // Sort employees
  const sortedEmployees = useMemo(() => {
    return [...employees].sort((a, b) => {
      let valA = a[sortField] || "";
      let valB = b[sortField] || "";
      if (sortField === "employeeId") {
        const numA = parseInt(valA, 10);
        const numB = parseInt(valB, 10);
        if (!isNaN(numA) && !isNaN(numB)) {
          return sortOrder === "asc" ? numA - numB : numB - numA;
        }
      }
      valA = valA.toString().toLowerCase();
      valB = valB.toString().toLowerCase();
      if (valA < valB) return sortOrder === "asc" ? -1 : 1;
      if (valA > valB) return sortOrder === "asc" ? 1 : -1;
      return 0;
    });
  }, [employees, sortField, sortOrder]);

  // Paginated employees
  const totalRecords = sortedEmployees.length;
  const totalPages = Math.max(1, Math.ceil(totalRecords / pageSize));
  const startIndex = (currentPage - 1) * pageSize;
  const paginatedEmployees = useMemo(() => {
    return sortedEmployees.slice(startIndex, startIndex + pageSize);
  }, [sortedEmployees, startIndex, pageSize]);

  // Select all logic
  const isAllSelected =
    paginatedEmployees.length > 0 &&
    paginatedEmployees.every((emp) => selectedIds.includes(emp.id));

  const toggleSelectAll = () => {
    if (isAllSelected) {
      const currentPageIds = paginatedEmployees.map((e) => e.id);
      updateSelectedIds(selectedIds.filter((id) => !currentPageIds.includes(id)));
    } else {
      const currentPageIds = paginatedEmployees.map((e) => e.id);
      updateSelectedIds(Array.from(new Set([...selectedIds, ...currentPageIds])));
    }
  };

  const toggleSelectRow = (id: string) => {
    if (selectedIds.includes(id)) {
      updateSelectedIds(selectedIds.filter((item) => item !== id));
    } else {
      updateSelectedIds([...selectedIds, id]);
    }
  };

  return (
    <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg shadow-2xs overflow-hidden flex flex-col">
      {/* Table Container */}
      <div className="w-full overflow-x-auto min-h-[360px]">
        <table className="w-full text-left border-collapse text-xs select-none">
          {/* Table Header */}
          <thead className="bg-[#EBF5FF] dark:bg-slate-950 text-slate-700 dark:text-slate-300 font-semibold border-b border-slate-200 dark:border-slate-800">
            <tr>
              <th className="px-4 py-3.5 w-12 text-center">
                <input
                  type="checkbox"
                  checked={isAllSelected}
                  onChange={toggleSelectAll}
                  className="h-4 w-4 rounded border-slate-300 text-[#0B85C9] focus:ring-[#0B85C9] cursor-pointer"
                />
              </th>
              <th className="px-4 py-3.5 min-w-[120px]">
                <button
                  onClick={() => handleSort("employeeId")}
                  className="flex items-center gap-1.5 font-bold hover:text-sky-600 dark:hover:text-sky-400 transition-colors cursor-pointer"
                >
                  <span>Employee ID</span>
                  <ArrowUpDown className="h-3 w-3 text-slate-400" />
                </button>
              </th>
              <th className="px-4 py-3.5 min-w-[180px]">
                <button
                  onClick={() => handleSort("name")}
                  className="flex items-center gap-1.5 font-bold hover:text-sky-600 dark:hover:text-sky-400 transition-colors cursor-pointer"
                >
                  <span>Employee Name</span>
                  <ArrowUpDown className="h-3 w-3 text-slate-400" />
                </button>
              </th>
              <th className="px-4 py-3.5 min-w-[140px]">
                <button
                  onClick={() => handleSort("department")}
                  className="flex items-center gap-1.5 font-bold hover:text-sky-600 dark:hover:text-sky-400 transition-colors cursor-pointer"
                >
                  <span>Department</span>
                  <ArrowUpDown className="h-3 w-3 text-slate-400" />
                </button>
              </th>
              <th className="px-4 py-3.5 min-w-[160px]">
                <button
                  onClick={() => handleSort("designation")}
                  className="flex items-center gap-1.5 font-bold hover:text-sky-600 dark:hover:text-sky-400 transition-colors cursor-pointer"
                >
                  <span>Designation</span>
                  <ArrowUpDown className="h-3 w-3 text-slate-400" />
                </button>
              </th>
              {leaveColumns.map((col) => (
                <th key={col} className="px-4 py-3.5 min-w-[140px] font-bold text-center">
                  {col}
                </th>
              ))}
            </tr>
          </thead>

          {/* Table Body */}
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60">
            {isLoading ? (
              Array.from({ length: 5 }).map((_, idx) => (
                <tr key={idx} className="animate-pulse">
                  <td className="px-4 py-3.5 text-center"><div className="h-4 w-4 bg-slate-200 dark:bg-slate-800 rounded mx-auto" /></td>
                  <td className="px-4 py-3.5"><div className="h-3.5 w-12 bg-slate-200 dark:bg-slate-800 rounded" /></td>
                  <td className="px-4 py-3.5"><div className="h-3.5 w-28 bg-slate-200 dark:bg-slate-800 rounded" /></td>
                  <td className="px-4 py-3.5"><div className="h-3.5 w-20 bg-slate-200 dark:bg-slate-800 rounded" /></td>
                  <td className="px-4 py-3.5"><div className="h-3.5 w-24 bg-slate-200 dark:bg-slate-800 rounded" /></td>
                  {leaveColumns.map((col) => (
                    <td key={col} className="px-4 py-3.5 text-center"><div className="h-3.5 w-16 bg-slate-200 dark:bg-slate-800 rounded mx-auto" /></td>
                  ))}
                </tr>
              ))
            ) : totalRecords === 0 ? (
              <tr>
                <td colSpan={5 + leaveColumns.length} className="px-6 py-16 text-center text-slate-400 dark:text-slate-500">
                  <p className="text-sm font-medium">No employee leave balance records found.</p>
                </td>
              </tr>
            ) : (
              paginatedEmployees.map((emp) => {
                const isSelected = selectedIds.includes(emp.id);
                return (
                  <tr
                    key={emp.id}
                    className={`hover:bg-slate-50/70 dark:hover:bg-slate-800/40 transition-colors text-slate-700 dark:text-slate-300 ${
                      isSelected ? "bg-sky-50/30 dark:bg-sky-950/20" : ""
                    }`}
                  >
                    <td className="px-4 py-3.5 text-center">
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => toggleSelectRow(emp.id)}
                        className="h-4 w-4 rounded border-slate-300 text-[#0B85C9] focus:ring-[#0B85C9] cursor-pointer"
                      />
                    </td>
                    <td className="px-4 py-3.5 text-slate-600 dark:text-slate-400">
                      {emp.employeeSummary?.employee_code || emp.employeeId}
                    </td>
                    <td className="px-4 py-3.5 font-medium text-slate-800 dark:text-slate-100">
                      {emp.employeeSummary?.employee_name || emp.name}
                    </td>
                    <td className="px-4 py-3.5 text-slate-600 dark:text-slate-400">
                      {emp.employeeSummary?.department_name || emp.department}
                    </td>
                    <td className="px-4 py-3.5 text-slate-600 dark:text-slate-400">
                      {emp.employeeSummary?.designation_name || emp.designation}
                    </td>
                    {leaveColumns.map((col) => {
                      const balanceVal = emp.leaveBalances[col] ?? "Not Assigned";
                      return (
                        <td key={col} className="px-4 py-3.5 text-center text-slate-600 dark:text-slate-400">
                          {typeof balanceVal === "number" ? balanceVal : balanceVal}
                        </td>
                      );
                    })}
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Footer */}
      <div className="px-4 py-3 border-t border-slate-200 dark:border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-slate-600 dark:text-slate-400">
        <div>
          Showing <span className="font-semibold text-slate-800 dark:text-slate-200">{totalRecords === 0 ? 0 : startIndex + 1}</span> to{" "}
          <span className="font-semibold text-slate-800 dark:text-slate-200">
            {Math.min(startIndex + pageSize, totalRecords)}
          </span>{" "}
          of <span className="font-semibold text-slate-800 dark:text-slate-200">{totalRecords}</span> Results
        </div>

        <div className="flex items-center gap-3">
          {/* 10 / Page Selector */}
          <select
            value={pageSize}
            onChange={(e) => {
              setPageSize(Number(e.target.value));
              setCurrentPage(1);
            }}
            className="h-8 px-2 text-xs bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded cursor-pointer focus:outline-none"
          >
            <option value={10}>10 / Page</option>
            <option value={20}>20 / Page</option>
            <option value={50}>50 / Page</option>
          </select>

          {/* Page Buttons */}
          <div className="flex items-center gap-1">
            <Button
              variant="outline"
              size="sm"
              disabled={currentPage <= 1}
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              className="h-8 px-3 text-xs bg-white dark:bg-slate-900 border-slate-300 dark:border-slate-700 cursor-pointer disabled:opacity-50"
            >
              Previous
            </Button>

            {Array.from({ length: Math.min(5, totalPages) }).map((_, idx) => {
              const pageNum = idx + 1;
              return (
                <button
                  key={pageNum}
                  onClick={() => setCurrentPage(pageNum)}
                  className={`h-8 w-8 text-xs font-medium rounded transition-colors cursor-pointer ${
                    currentPage === pageNum
                      ? "bg-[#0B85C9] text-white"
                      : "bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800"
                  }`}
                >
                  {pageNum}
                </button>
              );
            })}

            <Button
              variant="outline"
              size="sm"
              disabled={currentPage >= totalPages}
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              className="h-8 px-3 text-xs bg-white dark:bg-slate-900 border-slate-300 dark:border-slate-700 cursor-pointer disabled:opacity-50"
            >
              Next
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
