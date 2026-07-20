"use client";

import { useState, useMemo } from "react";
import { ArrowUpDown, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { HolidayAssignEmployee } from "../types";

interface HolidayAssignTableProps {
  employees: HolidayAssignEmployee[];
  isLoading?: boolean;
  totalRecords?: number;
  currentPage?: number;
  pageSize?: number;
  onPageChange?: (page: number) => void;
  onPageSizeChange?: (size: number) => void;
  searchQuery?: string;
  onSearchChange?: (query: string) => void;
  selectedIds: string[];
  onSelectionChange: (ids: string[]) => void;
}

export function HolidayAssignTable({
  employees,
  isLoading = false,
  totalRecords: externalTotalRecords,
  currentPage: externalCurrentPage,
  pageSize: externalPageSize,
  onPageChange,
  onPageSizeChange,
  searchQuery: externalSearchQuery,
  onSearchChange,
  selectedIds,
  onSelectionChange,
}: HolidayAssignTableProps) {
  const [internalSearchQuery, setInternalSearchQuery] = useState<string>("");
  const [sortField, setSortField] = useState<
    "employeeId" | "name" | "department" | "designation" | "assignedTemplate"
  >("employeeId");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");
  const [internalCurrentPage, setInternalCurrentPage] = useState<number>(1);
  const [internalPageSize, setInternalPageSize] = useState<number>(10);

  const searchQuery = externalSearchQuery !== undefined ? externalSearchQuery : internalSearchQuery;
  const currentPage = externalCurrentPage !== undefined ? externalCurrentPage : internalCurrentPage;
  const pageSize = externalPageSize !== undefined ? externalPageSize : internalPageSize;

  const handleSearchChange = (val: string) => {
    if (onSearchChange) {
      onSearchChange(val);
    } else {
      setInternalSearchQuery(val);
      setInternalCurrentPage(1);
    }
  };

  const handlePageChange = (p: number) => {
    if (onPageChange) {
      onPageChange(p);
    } else {
      setInternalCurrentPage(p);
    }
  };

  const handlePageSizeChange = (sz: number) => {
    if (onPageSizeChange) {
      onPageSizeChange(sz);
    } else {
      setInternalPageSize(sz);
      setInternalCurrentPage(1);
    }
  };

  // Search filter
  const filteredEmployees = useMemo(() => {
    if (externalSearchQuery !== undefined || !searchQuery.trim()) return employees;
    const q = searchQuery.toLowerCase();
    return employees.filter(
      (e) =>
        e.employeeId.toLowerCase().includes(q) ||
        e.name.toLowerCase().includes(q) ||
        e.department.toLowerCase().includes(q) ||
        e.designation.toLowerCase().includes(q) ||
        (e.assignedTemplate && e.assignedTemplate.toLowerCase().includes(q))
    );
  }, [employees, searchQuery, externalSearchQuery]);

  // Sort employees
  const sortedEmployees = useMemo(() => {
    return [...filteredEmployees].sort((a, b) => {
      let valA = a[sortField] || "";
      let valB = b[sortField] || "";

      if (sortField === "employeeId") {
        const numA = parseInt(valA, 10);
        const numB = parseInt(valB, 10);
        if (!isNaN(numA) && !isNaN(numB)) {
          return sortOrder === "asc" ? numA - numB : numB - numA;
        }
      }

      valA = String(valA).toLowerCase();
      valB = String(valB).toLowerCase();

      if (valA < valB) return sortOrder === "asc" ? -1 : 1;
      if (valA > valB) return sortOrder === "asc" ? 1 : -1;
      return 0;
    });
  }, [filteredEmployees, sortField, sortOrder]);

  const handleSort = (
    field: "employeeId" | "name" | "department" | "designation" | "assignedTemplate"
  ) => {
    if (sortField === field) {
      setSortOrder((prev) => (prev === "asc" ? "desc" : "asc"));
    } else {
      setSortField(field);
      setSortOrder("asc");
    }
  };

  // Pagination logic
  const totalRecords =
    externalTotalRecords !== undefined ? externalTotalRecords : sortedEmployees.length;
  const totalPages = Math.ceil(totalRecords / pageSize) || 1;
  const startIndex = (currentPage - 1) * pageSize;
  const displayEmployees =
    externalTotalRecords !== undefined
      ? sortedEmployees
      : sortedEmployees.slice(startIndex, startIndex + pageSize);

  // Selection handlers
  const isAllSelected =
    displayEmployees.length > 0 && displayEmployees.every((emp) => selectedIds.includes(emp.id));

  const toggleSelectAll = () => {
    if (isAllSelected) {
      const currentPageIds = displayEmployees.map((e) => e.id);
      onSelectionChange(selectedIds.filter((id) => !currentPageIds.includes(id)));
    } else {
      const currentPageIds = displayEmployees.map((e) => e.id);
      onSelectionChange(Array.from(new Set([...selectedIds, ...currentPageIds])));
    }
  };

  const toggleSelectRow = (id: string) => {
    if (selectedIds.includes(id)) {
      onSelectionChange(selectedIds.filter((item) => item !== id));
    } else {
      onSelectionChange([...selectedIds, id]);
    }
  };

  return (
    <div className="space-y-4">
      {/* Top Filter & Search Bar */}
      <div className="flex items-center justify-between gap-4">
        <div className="relative w-72">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
          <Input
            placeholder="Search employee or template..."
            value={searchQuery}
            onChange={(e) => handleSearchChange(e.target.value)}
            className="pl-9 h-9 text-xs bg-white dark:bg-slate-900 border-slate-300 dark:border-slate-700"
          />
        </div>
      </div>

      {/* Main Table Container */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg shadow-2xs overflow-hidden flex flex-col">
        <div className="w-full overflow-x-auto min-h-[380px]">
          <table className="w-full text-left border-collapse text-xs select-none">
            <thead className="bg-[#EBF5FF] dark:bg-slate-950 text-slate-700 dark:text-slate-300 font-semibold border-b border-slate-200 dark:border-slate-800">
              <tr>
                <th className="px-4 py-3 w-10 text-center">
                  <input
                    type="checkbox"
                    checked={isAllSelected}
                    onChange={toggleSelectAll}
                    className="h-4 w-4 rounded border-slate-300 text-sky-600 focus:ring-sky-500 cursor-pointer"
                  />
                </th>

                <th className="px-4 py-3 min-w-[140px]">
                  <button
                    onClick={() => handleSort("employeeId")}
                    className="flex items-center gap-1.5 font-bold hover:text-sky-600 dark:hover:text-sky-400 transition-colors cursor-pointer"
                  >
                    <span>Employee ID</span>
                    <ArrowUpDown className="h-3 w-3 text-slate-400" />
                  </button>
                </th>

                <th className="px-4 py-3 min-w-[180px]">
                  <button
                    onClick={() => handleSort("name")}
                    className="flex items-center gap-1.5 font-bold hover:text-sky-600 dark:hover:text-sky-400 transition-colors cursor-pointer"
                  >
                    <span>Employee Name</span>
                    <ArrowUpDown className="h-3 w-3 text-slate-400" />
                  </button>
                </th>

                <th className="px-4 py-3 min-w-[160px]">
                  <button
                    onClick={() => handleSort("department")}
                    className="flex items-center gap-1.5 font-bold hover:text-sky-600 dark:hover:text-sky-400 transition-colors cursor-pointer"
                  >
                    <span>Department</span>
                    <ArrowUpDown className="h-3 w-3 text-slate-400" />
                  </button>
                </th>

                <th className="px-4 py-3 min-w-[180px]">
                  <button
                    onClick={() => handleSort("designation")}
                    className="flex items-center gap-1.5 font-bold hover:text-sky-600 dark:hover:text-sky-400 transition-colors cursor-pointer"
                  >
                    <span>Designation</span>
                    <ArrowUpDown className="h-3 w-3 text-slate-400" />
                  </button>
                </th>

                <th className="px-4 py-3 min-w-[180px]">
                  <button
                    onClick={() => handleSort("assignedTemplate")}
                    className="flex items-center gap-1.5 font-bold hover:text-sky-600 dark:hover:text-sky-400 transition-colors cursor-pointer"
                  >
                    <span>Template Assigned</span>
                    <ArrowUpDown className="h-3 w-3 text-slate-400" />
                  </button>
                </th>
              </tr>
            </thead>

            <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60">
              {isLoading ? (
                Array.from({ length: pageSize }).map((_, idx) => (
                  <tr key={idx} className="animate-pulse">
                    <td className="px-4 py-3.5 text-center">
                      <div className="h-4 w-4 bg-slate-200 dark:bg-slate-800 rounded mx-auto" />
                    </td>
                    <td className="px-4 py-3.5">
                      <div className="h-4 w-12 bg-slate-200 dark:bg-slate-800 rounded" />
                    </td>
                    <td className="px-4 py-3.5">
                      <div className="h-4 w-32 bg-slate-200 dark:bg-slate-800 rounded" />
                    </td>
                    <td className="px-4 py-3.5">
                      <div className="h-4 w-24 bg-slate-200 dark:bg-slate-800 rounded" />
                    </td>
                    <td className="px-4 py-3.5">
                      <div className="h-4 w-28 bg-slate-200 dark:bg-slate-800 rounded" />
                    </td>
                    <td className="px-4 py-3.5">
                      <div className="h-4 w-24 bg-slate-200 dark:bg-slate-800 rounded" />
                    </td>
                  </tr>
                ))
              ) : totalRecords === 0 ? (
                <tr>
                  <td colSpan={6} className="px-6 py-16 text-center text-slate-400">
                    No employee records found.
                  </td>
                </tr>
              ) : (
                displayEmployees.map((emp) => (
                  <tr
                    key={emp.id}
                    className="hover:bg-slate-50/70 dark:hover:bg-slate-800/40 transition-colors text-slate-700 dark:text-slate-300"
                  >
                    <td className="px-4 py-3.5 text-center">
                      <input
                        type="checkbox"
                        checked={selectedIds.includes(emp.id)}
                        onChange={() => toggleSelectRow(emp.id)}
                        className="h-4 w-4 rounded border-slate-300 text-sky-600 focus:ring-sky-500 cursor-pointer"
                      />
                    </td>
                    <td className="px-4 py-3.5 font-medium text-slate-700 dark:text-slate-300">
                      {emp.employeeId}
                    </td>
                    <td className="px-4 py-3.5 font-semibold text-slate-800 dark:text-slate-100">
                      {emp.name}
                    </td>
                    <td className="px-4 py-3.5 text-slate-600 dark:text-slate-400">
                      {emp.department}
                    </td>
                    <td className="px-4 py-3.5 text-slate-600 dark:text-slate-400">
                      {emp.designation}
                    </td>
                    <td className="px-4 py-3.5 text-slate-600 dark:text-slate-400">
                      {emp.assignedTemplate || "-"}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Server-ready Pagination Footer */}
        <div className="px-4 py-3 border-t border-slate-200 dark:border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-slate-600 dark:text-slate-400">
          <div>
            Showing{" "}
            <span className="font-semibold text-slate-800 dark:text-slate-200">
              {totalRecords === 0 ? 0 : startIndex + 1}
            </span>{" "}
            to{" "}
            <span className="font-semibold text-slate-800 dark:text-slate-200">
              {Math.min(startIndex + pageSize, totalRecords)}
            </span>{" "}
            of{" "}
            <span className="font-semibold text-slate-800 dark:text-slate-200">{totalRecords}</span>{" "}
            Results
          </div>

          <div className="flex items-center gap-3">
            <select
              value={pageSize}
              onChange={(e) => handlePageSizeChange(Number(e.target.value))}
              className="h-8 px-2 text-xs bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded cursor-pointer focus:outline-none"
            >
              <option value={10}>10 / Page</option>
              <option value={20}>20 / Page</option>
              <option value={50}>50 / Page</option>
            </select>

            <div className="flex items-center gap-1">
              <Button
                variant="outline"
                size="sm"
                disabled={currentPage <= 1}
                onClick={() => handlePageChange(Math.max(1, currentPage - 1))}
                className="h-8 px-3 text-xs bg-white dark:bg-slate-900 border-slate-300 dark:border-slate-700 cursor-pointer disabled:opacity-50"
              >
                Previous
              </Button>

              {Array.from({ length: totalPages }).map((_, idx) => {
                const pageNum = idx + 1;
                return (
                  <button
                    key={pageNum}
                    onClick={() => handlePageChange(pageNum)}
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
                onClick={() => handlePageChange(Math.min(totalPages, currentPage + 1))}
                className="h-8 px-3 text-xs bg-white dark:bg-slate-900 border-slate-300 dark:border-slate-700 cursor-pointer disabled:opacity-50"
              >
                Next
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
