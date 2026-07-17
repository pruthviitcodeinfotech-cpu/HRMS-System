"use client";

import React, { useState, useMemo } from "react";
import { ChevronLeft, X, Search, SlidersHorizontal } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { toast } from "sonner";
import { useRouter } from "next/navigation";
import { ProtectedRoute } from "@/features/auth";

interface EmployeeAssignment {
  employee_id: string;
  name: string;
  department: string;
  designation: string;
  branch: string;
  shift_name: string;
}

const INITIAL_ASSIGNMENTS: EmployeeAssignment[] = [
  { employee_id: "58", name: "Savan Kamuni", department: "Marketing", designation: "marketing", branch: "Itcode Infotech", shift_name: "Daily" },
  { employee_id: "57", name: "Tulsi baladhiya", department: "Marketing", designation: "Graphic Designer", branch: "Itcode Infotech", shift_name: "Daily" },
  { employee_id: "56", name: "Hetal Gohil", department: "Marketing", designation: "marketing", branch: "Itcode Infotech", shift_name: "Daily" },
  { employee_id: "55", name: "Mansi Baghra", department: "Developer", designation: "Python", branch: "Itcode Infotech", shift_name: "Daily" },
  { employee_id: "54", name: "Divyesh Pipaliya", department: "Marketing", designation: "marketing", branch: "Itcode Infotech", shift_name: "Daily" },
  { employee_id: "53", name: "Pratik raval", department: "Marketing", designation: "marketing", branch: "Itcode Infotech", shift_name: "Daily" },
  { employee_id: "52", name: "Krishna Chodvadiya", department: "BDM", designation: "BDM", branch: "Itcode Infotech", shift_name: "Daily" },
  { employee_id: "51", name: "Kunalji Kikani", department: "video editing", designation: "video editing", branch: "Itcode Infotech", shift_name: "Daily" },
  { employee_id: "50", name: "Vivek Rathod", department: "Graphic Designer", designation: "Graphic Designer", branch: "Itcode Infotech", shift_name: "Daily" },
  { employee_id: "49", name: "Rahi Patel", department: "video editing", designation: "video editing", branch: "Itcode Infotech", shift_name: "Daily" },
];

export default function ShiftAssignmentsPage() {
  const router = useRouter();
  const [assignments, setAssignments] = useState<EmployeeAssignment[]>(INITIAL_ASSIGNMENTS);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  
  // Search, Filters & Pagination
  const [searchQuery, setSearchQuery] = useState("");
  const [deptFilter, setDeptFilter] = useState("All");
  const [shiftFilter, setShiftFilter] = useState("All");
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  // Sorting
  const [sortField, setSortField] = useState<string>("employee_id");
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("asc");

  // Drawer state
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [targetShift, setTargetShift] = useState("Daily");

  // Sorting Handler
  const handleSort = (field: string) => {
    if (sortField === field) {
      setSortDirection((prev) => (prev === "asc" ? "desc" : "asc"));
    } else {
      setSortField(field);
      setSortDirection("asc");
    }
  };

  // Toggle selection
  const handleSelectRow = (empId: string) => {
    setSelectedIds((prev) =>
      prev.includes(empId) ? prev.filter((id) => id !== empId) : [...prev, empId]
    );
  };

  const handleSelectAll = (filteredIds: string[]) => {
    if (selectedIds.length === filteredIds.length) {
      setSelectedIds([]);
    } else {
      setSelectedIds(filteredIds);
    }
  };

  // Reset Filters
  const handleResetFilters = () => {
    setSearchQuery("");
    setDeptFilter("All");
    setShiftFilter("All");
    setCurrentPage(1);
  };

  // Open Assign Drawer
  const handleOpenAssign = () => {
    if (selectedIds.length === 0) {
      toast.warning("Please select at least one employee to assign a shift.");
      return;
    }
    setIsDrawerOpen(true);
  };

  // Save Assignment
  const handleSaveAssignment = (e: React.FormEvent) => {
    e.preventDefault();
    setAssignments((prev) =>
      prev.map((a) =>
        selectedIds.includes(a.employee_id) ? { ...a, shift_name: targetShift } : a
      )
    );
    toast.success(`Assigned "${targetShift}" shift to ${selectedIds.length} employees.`);
    setIsDrawerOpen(false);
    setSelectedIds([]);
  };

  // Filtered and Sorted list
  const processedAssignments = useMemo(() => {
    let result = [...assignments];

    // Search query
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      result = result.filter(
        (a) =>
          a.employee_id.toLowerCase().includes(q) ||
          a.name.toLowerCase().includes(q) ||
          a.department.toLowerCase().includes(q) ||
          a.designation.toLowerCase().includes(q)
      );
    }

    // Dept Filter
    if (deptFilter !== "All") {
      result = result.filter((a) => a.department === deptFilter);
    }

    // Shift Filter
    if (shiftFilter !== "All") {
      result = result.filter((a) => a.shift_name === shiftFilter);
    }

    // Sorting
    result.sort((a: any, b: any) => {
      let valA = a[sortField];
      let valB = b[sortField];

      if (sortField === "employee_id") {
        const numA = parseInt(valA) || 0;
        const numB = parseInt(valB) || 0;
        return sortDirection === "asc" ? numA - numB : numB - numA;
      }

      if (typeof valA === "string") {
        return sortDirection === "asc"
          ? valA.localeCompare(valB)
          : valB.localeCompare(valA);
      } else {
        return sortDirection === "asc" ? valA - valB : valB - valA;
      }
    });

    return result;
  }, [assignments, searchQuery, deptFilter, shiftFilter, sortField, sortDirection]);

  // Paginated list
  const paginatedAssignments = useMemo(() => {
    const startIndex = (currentPage - 1) * pageSize;
    return processedAssignments.slice(startIndex, startIndex + pageSize);
  }, [processedAssignments, currentPage, pageSize]);

  const totalPages = Math.ceil(processedAssignments.length / pageSize) || 1;
  const filteredIdsList = processedAssignments.map((a) => a.employee_id);

  return (
    <ProtectedRoute requiredPermission={{ feature: "shift", action: "read" }}>
      <div className="p-6 space-y-6 bg-slate-50/40 min-h-screen">
        
        {/* Title area matching screenshot */}
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
            {/* Stats matching screenshot */}
            <div className="text-xs text-slate-500 dark:text-slate-400 font-semibold pl-8">
              Assigned: <span className="text-slate-800 dark:text-slate-200">40</span>
              <span className="mx-2 text-slate-300 dark:text-slate-700">|</span>
              Unassigned: <span className="text-slate-800 dark:text-slate-200">0</span>
            </div>
          </div>

          <div>
            <Button
              variant="primary"
              size="sm"
              onClick={handleOpenAssign}
              className="h-9 px-5 text-xs font-bold bg-[#0B85C9] hover:bg-[#0974b0] text-white rounded-lg shadow-sm border-0"
            >
              Assign Shift
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
                placeholder="Search employee..."
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  setCurrentPage(1);
                }}
                className="pl-9 h-9 text-xs w-full bg-white dark:bg-slate-950 text-slate-800 dark:text-slate-100 placeholder:text-slate-450 dark:placeholder:text-slate-500 border border-slate-200 dark:border-slate-800 focus-visible:ring-blue-500/20 focus-visible:border-blue-500"
              />
            </div>

            {/* Middle Filters */}
            <div className="flex flex-wrap items-center gap-3 w-full md:w-auto md:justify-end">
              <div className="flex items-center gap-1.5">
                <span className="text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider">Dept:</span>
                <select
                  value={deptFilter}
                  onChange={(e) => {
                    setDeptFilter(e.target.value);
                    setCurrentPage(1);
                  }}
                  className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-md px-2 py-1 h-8 text-xs font-semibold text-slate-700 dark:text-slate-350 focus:outline-none"
                >
                  <option value="All">All Departments</option>
                  <option value="Marketing">Marketing</option>
                  <option value="Developer">Developer</option>
                  <option value="BDM">BDM</option>
                  <option value="video editing">video editing</option>
                </select>
              </div>

              <div className="flex items-center gap-1.5">
                <span className="text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider">Shift:</span>
                <select
                  value={shiftFilter}
                  onChange={(e) => {
                    setShiftFilter(e.target.value);
                    setCurrentPage(1);
                  }}
                  className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-md px-2 py-1 h-8 text-xs font-semibold text-slate-700 dark:text-slate-350 focus:outline-none"
                >
                  <option value="All">All Shifts</option>
                  <option value="Daily">Daily</option>
                  <option value="Night Shift Developer">Night Shift Developer</option>
                  <option value="Khushi maam 8 to 6">Khushi maam 8 to 6</option>
                  <option value="Open Shift">Open Shift</option>
                </select>
              </div>

              <Button
                variant="outline"
                size="sm"
                onClick={handleResetFilters}
                className="h-8 text-xs font-semibold text-slate-600 dark:text-slate-300 border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 hover:bg-slate-50 dark:hover:bg-slate-800/50"
              >
                <SlidersHorizontal className="h-3.5 w-3.5 mr-1" />
                Reset
              </Button>
            </div>
          </div>

          {/* Table representation matching screenshot exactly */}
          <div className="w-full overflow-x-auto relative min-h-[250px]">
            <table className="w-full text-left border-collapse text-xs">
              <thead className="bg-[#EBF5FF] dark:bg-slate-950/80 border-b border-slate-200/80 dark:border-slate-800 uppercase text-[10px] tracking-wider text-slate-650 dark:text-slate-400 font-bold">
                <tr>
                  <th className="px-5 py-3.5 w-12 text-center">
                    <input
                      type="checkbox"
                      checked={selectedIds.length === filteredIdsList.length && filteredIdsList.length > 0}
                      onChange={() => handleSelectAll(filteredIdsList)}
                      className="h-4 w-4 rounded border-slate-300 dark:border-slate-700 text-blue-600 focus:ring-blue-500 cursor-pointer"
                    />
                  </th>
                  <th
                    onClick={() => handleSort("employee_id")}
                    className="px-6 py-3.5 font-bold text-slate-700 dark:text-slate-300 cursor-pointer hover:text-slate-800 transition-colors select-none"
                  >
                    <div className="flex items-center gap-1">
                      Employee ID
                      <span className="text-[9px] text-slate-400">
                        {sortField === "employee_id" ? (sortDirection === "asc" ? "▲" : "▼") : "↕"}
                      </span>
                    </div>
                  </th>
                  <th
                    onClick={() => handleSort("name")}
                    className="px-6 py-3.5 font-bold text-slate-700 dark:text-slate-300 cursor-pointer hover:text-slate-800 transition-colors select-none"
                  >
                    <div className="flex items-center gap-1">
                      Employee Name
                      <span className="text-[9px] text-slate-400">
                        {sortField === "name" ? (sortDirection === "asc" ? "▲" : "▼") : "↕"}
                      </span>
                    </div>
                  </th>
                  <th
                    onClick={() => handleSort("department")}
                    className="px-6 py-3.5 font-bold text-slate-700 dark:text-slate-300 cursor-pointer hover:text-slate-800 transition-colors select-none"
                  >
                    <div className="flex items-center gap-1">
                      Department
                      <span className="text-[9px] text-slate-400">
                        {sortField === "department" ? (sortDirection === "asc" ? "▲" : "▼") : "↕"}
                      </span>
                    </div>
                  </th>
                  <th
                    onClick={() => handleSort("designation")}
                    className="px-6 py-3.5 font-bold text-slate-700 dark:text-slate-300 cursor-pointer hover:text-slate-800 transition-colors select-none"
                  >
                    <div className="flex items-center gap-1">
                      Designation
                      <span className="text-[9px] text-slate-400">
                        {sortField === "designation" ? (sortDirection === "asc" ? "▲" : "▼") : "↕"}
                      </span>
                    </div>
                  </th>
                  <th
                    onClick={() => handleSort("branch")}
                    className="px-6 py-3.5 font-bold text-slate-700 dark:text-slate-300 cursor-pointer hover:text-slate-800 transition-colors select-none"
                  >
                    <div className="flex items-center gap-1">
                      Branch
                      <span className="text-[9px] text-slate-400">
                        {sortField === "branch" ? (sortDirection === "asc" ? "▲" : "▼") : "↕"}
                      </span>
                    </div>
                  </th>
                  <th
                    onClick={() => handleSort("shift_name")}
                    className="px-6 py-3.5 font-bold text-slate-700 dark:text-slate-300 cursor-pointer hover:text-slate-800 transition-colors select-none"
                  >
                    <div className="flex items-center gap-1">
                      Shifts
                      <span className="text-[9px] text-slate-400">
                        {sortField === "shift_name" ? (sortDirection === "asc" ? "▲" : "▼") : "↕"}
                      </span>
                    </div>
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800/65">
                {paginatedAssignments.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-6 py-12 text-center text-slate-400 font-semibold">
                      No shift assignments matching filters.
                    </td>
                  </tr>
                ) : (
                  paginatedAssignments.map((assign) => {
                    const isSelected = selectedIds.includes(assign.employee_id);
                    return (
                      <tr
                        key={assign.employee_id}
                        className="hover:bg-slate-50/40 dark:hover:bg-slate-800/10 transition-colors border-b border-slate-100 dark:border-slate-800/60 align-middle"
                      >
                        <td className="px-5 py-4 text-center">
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={() => handleSelectRow(assign.employee_id)}
                            className="h-4 w-4 rounded border-slate-300 dark:border-slate-700 text-blue-600 focus:ring-blue-500 cursor-pointer"
                          />
                        </td>
                        <td className="px-6 py-4 font-semibold text-slate-600 dark:text-slate-400 whitespace-nowrap">
                          {assign.employee_id}
                        </td>
                        <td className="px-6 py-4 font-bold text-slate-800 dark:text-slate-200 whitespace-nowrap">
                          {assign.name}
                        </td>
                        <td className="px-6 py-4 font-semibold text-slate-600 dark:text-slate-400 whitespace-nowrap">
                          {assign.department}
                        </td>
                        <td className="px-6 py-4 font-semibold text-slate-600 dark:text-slate-400 whitespace-nowrap">
                          {assign.designation}
                        </td>
                        <td className="px-6 py-4 font-semibold text-slate-600 dark:text-slate-400 whitespace-nowrap">
                          {assign.branch}
                        </td>
                        {/* Shift name column rendered as plain text matching screenshot exactly */}
                        <td className="px-6 py-4 font-bold text-slate-700 dark:text-slate-300 whitespace-nowrap">
                          {assign.shift_name}
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination Footer */}
          <div className="p-4 border-t border-slate-200 dark:border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-4 bg-slate-50/20 dark:bg-slate-950/10">
            <div className="text-xs text-slate-500 font-semibold">
              Showing{" "}
              <span className="font-bold text-slate-800 dark:text-slate-200">
                {processedAssignments.length === 0 ? 0 : (currentPage - 1) * pageSize + 1}
              </span>{" "}
              to{" "}
              <span className="font-bold text-slate-800 dark:text-slate-200">
                {Math.min(currentPage * pageSize, processedAssignments.length)}
              </span>{" "}
              of <span className="font-bold text-slate-800 dark:text-slate-200">{processedAssignments.length}</span> Results
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

        {/* ASSIGN SHIFT DRAWER */}
        {isDrawerOpen && (
          <div className="fixed inset-0 z-[100] flex justify-end">
            {/* Backdrop */}
            <div
              className="absolute inset-0 bg-black/50 transition-opacity"
              onClick={() => setIsDrawerOpen(false)}
            />
            
            {/* Drawer Panel */}
            <div className="relative w-full max-w-md bg-white dark:bg-slate-900 h-full shadow-2xl flex flex-col justify-between z-10 animate-in slide-in-from-right duration-200">
              
              {/* Header: light blue background, close button */}
              <div className="p-5 border-b border-slate-200/60 dark:border-slate-800 flex items-center justify-between bg-[#EBF5FF] dark:bg-slate-950">
                <h3 className="text-base font-bold text-slate-800 dark:text-slate-100">
                  Assign Shift
                </h3>
                <button
                  onClick={() => setIsDrawerOpen(false)}
                  className="p-1.5 hover:bg-slate-200/50 dark:hover:bg-slate-800/50 rounded-md text-slate-500 hover:text-slate-800 dark:hover:text-slate-200 transition-colors cursor-pointer focus:outline-none"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>

              {/* Body: white background, padding */}
              <div className="flex-1 overflow-y-auto p-6 space-y-5">
                <form onSubmit={handleSaveAssignment} className="space-y-5" id="assign-shift-form">
                  
                  {/* Selected Employees list info */}
                  <div className="p-3 bg-blue-50/50 dark:bg-blue-950/20 border border-blue-100 dark:border-blue-900/50 rounded-xl space-y-1.5">
                    <span className="text-[10px] font-bold text-blue-500 uppercase tracking-wider block">
                      Target Employees ({selectedIds.length})
                    </span>
                    <p className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                      {assignments
                        .filter((a) => selectedIds.includes(a.employee_id))
                        .map((a) => a.name)
                        .join(", ")}
                    </p>
                  </div>

                  {/* Choose Shift template */}
                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                      Choose Shift Template
                    </label>
                    <select
                      value={targetShift}
                      onChange={(e) => setTargetShift(e.target.value)}
                      className="w-full rounded-md border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950 h-10 px-3 text-xs text-slate-800 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                    >
                      <option value="Daily">Daily (09:20 AM - 06:50 PM)</option>
                      <option value="Night Shift Developer">Night Shift Developer (10:30 PM - 06:30 AM)</option>
                      <option value="Khushi maam 8 to 6">Khushi maam 8 to 6 (08:30 AM - 06:00 PM)</option>
                      <option value="Open Shift">Open Shift (Flexible)</option>
                    </select>
                  </div>

                </form>
              </div>

              {/* Footer: light blue background, Assign button aligned right */}
              <div className="p-4 border-t border-slate-200/60 dark:border-slate-800 bg-[#EBF5FF] dark:bg-slate-950 flex items-center justify-end">
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => document.getElementById("assign-shift-form")?.dispatchEvent(new Event("submit", { cancelable: true, bubbles: true }))}
                  className="text-xs h-9 px-6 font-semibold bg-[#0B85C9] hover:bg-[#0974b0] text-white shadow-sm rounded-lg"
                >
                  Assign
                </Button>
              </div>
            </div>
          </div>
        )}

      </div>
    </ProtectedRoute>
  );
}
