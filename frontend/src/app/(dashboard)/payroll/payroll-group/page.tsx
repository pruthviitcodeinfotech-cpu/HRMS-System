"use client";

import React, { useState, useMemo } from "react";
import Link from "next/link";
import { toast } from "sonner";
import {
  Plus,
  UserPlus,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  X,
  MoreVertical,
  Edit2,
  Copy,
  Trash2,
  AlertCircle,
  SlidersHorizontal,
} from "lucide-react";
import { ProtectedRoute } from "@/features/auth";

// Payroll Group Interface
export interface PayrollGroupItem {
  id: number;
  group_name: string;
  description?: string;
  payroll_type: "Monthly Payroll" | "Hourly Payroll";
  has_compliance: boolean;
  is_default: boolean;
  employee_count: number;
  created_on: string;
  last_edited_on: string;
}

// Initial 3 reference groups matching Petpooja HRMS design exactly
const INITIAL_GROUPS: PayrollGroupItem[] = [
  {
    id: 1,
    group_name: "Monthly Payroll (No Compliance)",
    description: "Standard monthly fixed salary structure without statutory compliance deductions.",
    payroll_type: "Monthly Payroll",
    has_compliance: false,
    is_default: true,
    employee_count: 59,
    created_on: "13 February 2026",
    last_edited_on: "13 February 2026",
  },
  {
    id: 2,
    group_name: "Hourly Payroll",
    description: "Hourly wage payout structure based on attendance time logs.",
    payroll_type: "Hourly Payroll",
    has_compliance: false,
    is_default: true,
    employee_count: 0,
    created_on: "13 February 2026",
    last_edited_on: "13 February 2026",
  },
  {
    id: 3,
    group_name: "Monthly Payroll (With Compliance)",
    description: "Full statutory compliance monthly payroll with PF, ESI, and Tax calculations.",
    payroll_type: "Monthly Payroll",
    has_compliance: true,
    is_default: true,
    employee_count: 0,
    created_on: "13 February 2026",
    last_edited_on: "13 February 2026",
  },
];

export default function PayrollGroupManagementPage() {
  // Main Table State
  const [groups, setGroups] = useState<PayrollGroupItem[]>(INITIAL_GROUPS);
  const [searchQuery, setSearchQuery] = useState("");
  const [sortField, setSortField] = useState<keyof PayrollGroupItem>("created_on");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");

  // Pagination State
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  // Action Menu Popover State
  const [activeActionId, setActiveActionId] = useState<number | null>(null);

  // Create New Drawer State
  const [showCreateDrawer, setShowCreateDrawer] = useState(false);
  const [editingGroupId, setEditingGroupId] = useState<number | null>(null);
  const [createForm, setCreateForm] = useState({
    group_name: "",
    description: "",
    payroll_type: "Monthly Payroll" as "Monthly Payroll" | "Hourly Payroll",
    has_compliance: true,
    is_default: false,
  });
  const [formErrors, setFormErrors] = useState<Record<string, string>>({});

  // Simulation States
  const [isLoading] = useState(false);
  const [isError, setIsError] = useState(false);

  // Sorting Handler
  const handleSort = (field: keyof PayrollGroupItem) => {
    if (sortField === field) {
      setSortOrder(sortOrder === "asc" ? "desc" : "asc");
    } else {
      setSortField(field);
      setSortOrder("asc");
    }
  };

  // Filtered & Sorted Groups
  const filteredGroups = useMemo(() => {
    let result = groups.filter((g) =>
      g.group_name.toLowerCase().includes(searchQuery.toLowerCase().trim())
    );

    if (sortField) {
      result = [...result].sort((a, b) => {
        const valA = a[sortField] ?? "";
        const valB = b[sortField] ?? "";
        if (typeof valA === "number" && typeof valB === "number") {
          return sortOrder === "asc" ? valA - valB : valB - valA;
        }
        return sortOrder === "asc"
          ? String(valA).localeCompare(String(valB))
          : String(valB).localeCompare(String(valA));
      });
    }

    return result;
  }, [groups, searchQuery, sortField, sortOrder]);

  // Paginated Groups
  const totalRecords = filteredGroups.length;
  const paginatedGroups = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return filteredGroups.slice(start, start + pageSize);
  }, [filteredGroups, currentPage, pageSize]);

  // Handle Form Input Change
  const handleFormChange = (key: string, value: string | boolean) => {
    setCreateForm((prev) => ({ ...prev, [key]: value }));
    if (formErrors[key]) {
      setFormErrors((prev) => ({ ...prev, [key]: "" }));
    }
  };

  // Open Edit Modal
  const handleOpenEdit = (group: PayrollGroupItem) => {
    setActiveActionId(null);
    setEditingGroupId(group.id);
    setCreateForm({
      group_name: group.group_name,
      description: group.description || "",
      payroll_type: group.payroll_type,
      has_compliance: group.has_compliance,
      is_default: group.is_default,
    });
    setFormErrors({});
    setShowCreateDrawer(true);
  };

  // Duplicate Group
  const handleDuplicate = (group: PayrollGroupItem) => {
    setActiveActionId(null);
    const newId = Math.max(0, ...groups.map((g) => g.id)) + 1;
    const duplicated: PayrollGroupItem = {
      ...group,
      id: newId,
      group_name: `${group.group_name} (Copy)`,
      is_default: false,
      employee_count: 0,
      created_on: new Date().toLocaleDateString("en-GB", { day: "2-digit", month: "long", year: "numeric" }),
      last_edited_on: new Date().toLocaleDateString("en-GB", { day: "2-digit", month: "long", year: "numeric" }),
    };
    setGroups((prev) => [...prev, duplicated]);
    toast.success(`Duplicated "${group.group_name}" successfully.`);
  };

  // Delete Group
  const handleDelete = (group: PayrollGroupItem) => {
    setActiveActionId(null);
    if (group.is_default) {
      toast.error("Default groups cannot be deleted.");
      return;
    }
    setGroups((prev) => prev.filter((g) => g.id !== group.id));
    toast.success(`Deleted "${group.group_name}" successfully.`);
  };

  // Submit Create / Edit Group Form
  const handleSaveGroup = (e: React.FormEvent) => {
    e.preventDefault();
    const errors: Record<string, string> = {};
    if (!createForm.group_name.trim()) {
      errors.group_name = "Group Name is required.";
    }

    if (Object.keys(errors).length > 0) {
      setFormErrors(errors);
      return;
    }

    const todayFormatted = new Date().toLocaleDateString("en-GB", {
      day: "2-digit",
      month: "long",
      year: "numeric",
    });

    if (editingGroupId) {
      // Update existing group
      setGroups((prev) =>
        prev.map((g) =>
          g.id === editingGroupId
            ? {
                ...g,
                group_name: createForm.group_name.trim(),
                description: createForm.description.trim(),
                payroll_type: createForm.payroll_type,
                has_compliance: createForm.has_compliance,
                is_default: createForm.is_default,
                last_edited_on: todayFormatted,
              }
            : createForm.is_default
            ? { ...g, is_default: false }
            : g
        )
      );
      toast.success("Payroll group updated successfully.");
    } else {
      // Create new group
      const newId = Math.max(0, ...groups.map((g) => g.id)) + 1;
      const newGroup: PayrollGroupItem = {
        id: newId,
        group_name: createForm.group_name.trim(),
        description: createForm.description.trim(),
        payroll_type: createForm.payroll_type,
        has_compliance: createForm.has_compliance,
        is_default: createForm.is_default,
        employee_count: 0,
        created_on: todayFormatted,
        last_edited_on: todayFormatted,
      };

      if (createForm.is_default) {
        setGroups((prev) => prev.map((g) => ({ ...g, is_default: false })).concat(newGroup));
      } else {
        setGroups((prev) => [...prev, newGroup]);
      }
      toast.success("Payroll group created successfully.");
    }

    setShowCreateDrawer(false);
    setEditingGroupId(null);
    setCreateForm({
      group_name: "",
      description: "",
      payroll_type: "Monthly Payroll",
      has_compliance: true,
      is_default: false,
    });
  };

  return (
    <ProtectedRoute requiredPermission={{ feature: "payroll_processing", action: "read" }}>
      <div className="p-4 md:p-6 space-y-6 bg-slate-50/50 dark:bg-slate-950/40 min-h-screen text-slate-800 dark:text-slate-200">
        
        {/* Header Section */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
              Payroll Group ({groups.length})
            </h1>
          </div>

          <div className="flex items-center gap-3">
            {/* Assign Group Button — Navigates to /payroll/assign-payroll-group per user screenshot */}
            <Link
              href="/payroll/assign-payroll-group"
              className="px-4 py-2 text-xs font-semibold text-slate-700 dark:text-slate-200 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-700/60 rounded-lg transition-colors cursor-pointer flex items-center gap-1.5 shadow-xs"
            >
              <UserPlus className="w-3.5 h-3.5 text-slate-500" />
              <span>Assign Group</span>
            </Link>

            {/* Create New Button */}
            <button
              type="button"
              onClick={() => {
                setEditingGroupId(null);
                setCreateForm({
                  group_name: "",
                  description: "",
                  payroll_type: "Monthly Payroll",
                  has_compliance: true,
                  is_default: false,
                });
                setFormErrors({});
                setShowCreateDrawer(true);
              }}
              className="px-4 py-2 text-xs font-semibold text-white bg-[#0B85C9] hover:bg-[#0974b0] rounded-lg transition-colors cursor-pointer flex items-center gap-1.5 shadow-xs"
            >
              <Plus className="w-4 h-4" />
              <span>Create New</span>
            </button>
          </div>
        </div>

        {/* Main Table Container */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-xs overflow-hidden">
          
          {isLoading ? (
            /* Loading Skeleton */
            <div className="p-8 space-y-4">
              <div className="h-6 bg-slate-200 dark:bg-slate-800 rounded animate-pulse w-1/4" />
              <div className="space-y-3">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="h-12 bg-slate-100 dark:bg-slate-800/50 rounded animate-pulse" />
                ))}
              </div>
            </div>
          ) : isError ? (
            /* Error State */
            <div className="p-12 text-center space-y-4">
              <div className="w-12 h-12 rounded-full bg-red-100 dark:bg-red-950/50 text-red-600 dark:text-red-400 flex items-center justify-center mx-auto">
                <AlertCircle className="w-6 h-6" />
              </div>
              <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">
                Failed to Load Payroll Groups
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400 max-w-sm mx-auto">
                An error occurred while communicating with the server.
              </p>
              <button
                type="button"
                onClick={() => setIsError(false)}
                className="px-4 py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg cursor-pointer"
              >
                Retry
              </button>
            </div>
          ) : paginatedGroups.length === 0 ? (
            /* Empty State */
            <div className="p-12 text-center space-y-4">
              <div className="w-12 h-12 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-400 flex items-center justify-center mx-auto">
                <SlidersHorizontal className="w-6 h-6" />
              </div>
              <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">
                No Payroll Groups Found
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400 max-w-sm mx-auto">
                No configured payroll groups match your search criteria.
              </p>
              <button
                type="button"
                onClick={() => setSearchQuery("")}
                className="px-4 py-2 text-xs font-semibold text-blue-600 dark:text-blue-400 hover:underline cursor-pointer"
              >
                Reset Search
              </button>
            </div>
          ) : (
            /* Main Table */
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse min-w-[800px]">
                <thead>
                  <tr className="bg-blue-50/70 dark:bg-slate-800/90 text-slate-700 dark:text-slate-300 text-xs font-semibold border-b border-slate-200 dark:border-slate-700 select-none">
                    
                    {/* Group Name Header */}
                    <th
                      onClick={() => handleSort("group_name")}
                      className="py-3 px-4 min-w-[280px] cursor-pointer hover:bg-blue-100/50 dark:hover:bg-slate-700 transition-colors"
                    >
                      <div className="flex items-center gap-1.5">
                        <span>Group Name</span>
                        {sortField === "group_name" ? (
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

                    {/* Employee Count Header */}
                    <th className="py-3 px-4 min-w-[140px]">
                      Employee Count
                    </th>

                    {/* Created On Header */}
                    <th
                      onClick={() => handleSort("created_on")}
                      className="py-3 px-4 min-w-[160px] cursor-pointer hover:bg-blue-100/50 dark:hover:bg-slate-700 transition-colors"
                    >
                      <div className="flex items-center gap-1.5">
                        <span>Created On</span>
                        {sortField === "created_on" ? (
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

                    {/* Last Edited On Header */}
                    <th
                      onClick={() => handleSort("last_edited_on")}
                      className="py-3 px-4 min-w-[160px] cursor-pointer hover:bg-blue-100/50 dark:hover:bg-slate-700 transition-colors"
                    >
                      <div className="flex items-center gap-1.5">
                        <span>Last Edited On</span>
                        {sortField === "last_edited_on" ? (
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
                    <th className="py-3 px-4 min-w-[100px]">
                      Action
                    </th>
                  </tr>
                </thead>

                <tbody className="divide-y divide-slate-100 dark:divide-slate-800 text-xs">
                  {paginatedGroups.map((group) => (
                    <tr
                      key={group.id}
                      className="hover:bg-slate-50/60 dark:hover:bg-slate-800/40 transition-colors"
                    >
                      {/* Group Name & Default Badge */}
                      <td className="py-3.5 px-4">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-slate-900 dark:text-slate-100">
                            {group.group_name}
                          </span>
                          {group.is_default && (
                            <span className="px-2 py-0.5 text-[11px] font-medium bg-blue-50 dark:bg-blue-950/60 text-blue-600 dark:text-blue-400 rounded-md border border-blue-100 dark:border-blue-900/50 shrink-0">
                              Default
                            </span>
                          )}
                        </div>
                      </td>

                      {/* Employee Count (Clickable Underlined Link navigating to /payroll/assign-payroll-group) */}
                      <td className="py-3.5 px-4 font-medium text-slate-900 dark:text-slate-100">
                        <Link
                          href="/payroll/assign-payroll-group"
                          className="underline underline-offset-2 hover:text-blue-600 cursor-pointer font-medium"
                        >
                          {group.employee_count}
                        </Link>
                      </td>

                      {/* Created On */}
                      <td className="py-3.5 px-4 text-slate-700 dark:text-slate-300">
                        {group.created_on}
                      </td>

                      {/* Last Edited On */}
                      <td className="py-3.5 px-4 text-slate-700 dark:text-slate-300">
                        {group.last_edited_on}
                      </td>

                      {/* Action Cell */}
                      <td className="py-3.5 px-4 relative">
                        {group.is_default ? (
                          <span className="text-slate-400 font-bold ml-1">-</span>
                        ) : (
                          <div className="relative">
                            <button
                              type="button"
                              onClick={() =>
                                setActiveActionId(activeActionId === group.id ? null : group.id)
                              }
                              className="p-1 rounded-md text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer"
                            >
                              <MoreVertical className="w-4 h-4" />
                            </button>

                            {/* Dropdown Menu */}
                            {activeActionId === group.id && (
                              <div className="absolute right-0 top-full mt-1 w-44 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-xl p-1 z-50 text-xs font-medium space-y-0.5">
                                <button
                                  type="button"
                                  onClick={() => handleOpenEdit(group)}
                                  className="w-full flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300 cursor-pointer"
                                >
                                  <Edit2 className="w-3.5 h-3.5 text-blue-500" />
                                  <span>Edit</span>
                                </button>
                                <Link
                                  href="/payroll/assign-payroll-group"
                                  className="w-full flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300 cursor-pointer"
                                >
                                  <UserPlus className="w-3.5 h-3.5 text-emerald-500" />
                                  <span>Assign Employees</span>
                                </Link>
                                <button
                                  type="button"
                                  onClick={() => handleDuplicate(group)}
                                  className="w-full flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300 cursor-pointer"
                                >
                                  <Copy className="w-3.5 h-3.5 text-purple-500" />
                                  <span>Duplicate</span>
                                </button>
                                <button
                                  type="button"
                                  onClick={() => handleDelete(group)}
                                  className="w-full flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-red-50 dark:hover:bg-red-950/40 text-red-600 dark:text-red-400 cursor-pointer"
                                >
                                  <Trash2 className="w-3.5 h-3.5" />
                                  <span>Delete</span>
                                </button>
                              </div>
                            )}
                          </div>
                        )}
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
              {/* Page Size Selector */}
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

              {/* Pagination Controls */}
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
        {/* CREATE / EDIT PAYROLL GROUP SLIDE-OVER DRAWER        */}
        {/* ---------------------------------------------------- */}
        {showCreateDrawer && (
          <div className="fixed inset-0 z-50 overflow-hidden bg-black/50 backdrop-blur-xs flex justify-end">
            <div className="w-full max-w-md bg-white dark:bg-slate-900 h-full shadow-2xl flex flex-col border-l border-slate-200 dark:border-slate-800 animate-in slide-in-from-right duration-200">
              
              {/* Drawer Header */}
              <div className="flex items-center justify-between px-6 py-4 bg-blue-50/70 dark:bg-slate-800/80 border-b border-slate-200 dark:border-slate-800">
                <h2 className="text-base font-bold text-slate-900 dark:text-slate-100">
                  New Payroll Group
                </h2>
                <button
                  type="button"
                  onClick={() => setShowCreateDrawer(false)}
                  className="p-1 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 cursor-pointer"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {/* Drawer Form Content */}
              <form onSubmit={handleSaveGroup} className="flex-1 flex flex-col justify-between overflow-hidden">
                <div className="p-6 space-y-6 text-xs overflow-y-auto flex-1">
                  
                  {/* Group Name Field */}
                  <div>
                    <label className="block font-medium text-slate-700 dark:text-slate-300 mb-1.5">
                      Group Name<span className="text-red-500">*</span>
                    </label>
                    <input
                      type="text"
                      placeholder="Enter Name"
                      value={createForm.group_name}
                      onChange={(e) => handleFormChange("group_name", e.target.value)}
                      className={`w-full p-2.5 bg-white dark:bg-slate-800 border ${
                        formErrors.group_name
                          ? "border-red-500 focus:ring-red-500"
                          : "border-slate-200 dark:border-slate-700 focus:ring-blue-500"
                      } rounded-lg font-medium text-slate-800 dark:text-slate-100 focus:outline-none focus:ring-2`}
                    />
                    {formErrors.group_name && (
                      <p className="text-[11px] text-red-500 mt-1 font-medium">{formErrors.group_name}</p>
                    )}
                  </div>

                  {/* Payroll Type Dropdown */}
                  <div>
                    <label className="block font-medium text-slate-700 dark:text-slate-300 mb-1.5">
                      Payroll Type<span className="text-red-500">*</span>
                    </label>
                    <select
                      value={createForm.payroll_type}
                      onChange={(e) => handleFormChange("payroll_type", e.target.value)}
                      className="w-full p-2.5 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg font-medium text-slate-800 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer"
                    >
                      <option value="" disabled>Select Payroll Type</option>
                      <option value="Monthly Payroll">Monthly Payroll</option>
                      <option value="Hourly Payroll">Hourly Payroll</option>
                    </select>
                  </div>
                </div>

                {/* Footer Drawer Action Buttons matching Reference Screenshot */}
                <div className="flex items-center justify-end gap-3 px-6 py-3.5 bg-blue-50/70 dark:bg-slate-800/80 border-t border-slate-200 dark:border-slate-800">
                  <button
                    type="button"
                    onClick={() => setShowCreateDrawer(false)}
                    className="px-5 py-2 text-xs font-semibold text-slate-700 dark:text-slate-300 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-700 rounded-lg cursor-pointer transition-colors"
                  >
                    Close
                  </button>
                  <button
                    type="submit"
                    disabled={!createForm.group_name.trim()}
                    className={`px-5 py-2 text-xs font-semibold rounded-lg shadow-xs transition-colors ${
                      createForm.group_name.trim()
                        ? "bg-[#0B85C9] text-white hover:bg-[#0974b0] cursor-pointer"
                        : "bg-[#D1D5DB] text-white cursor-not-allowed"
                    }`}
                  >
                    Create
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </ProtectedRoute>
  );
}
