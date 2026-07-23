"use client";

import React, { useState } from "react";
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
  Trash2,
  AlertCircle,
  SlidersHorizontal,
} from "lucide-react";
import { ProtectedRoute } from "@/features/auth";
import {
  usePayrollGroups,
  useCreatePayrollGroup,
  useUpdatePayrollGroup,
  useDeletePayrollGroup,
  useGroupEmployees,
} from "@/features/payroll/hooks/use-payroll";
import { PayrollGroupItem } from "@/features/payroll/types";

export default function PayrollGroupManagementPage() {
  // Main Table State
  const [searchQuery, setSearchQuery] = useState("");
  const [sortField, setSortField] = useState<string>("created_at");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");

  // Pagination State
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  // Action Menu Popover State
  const [activeActionId, setActiveActionId] = useState<number | null>(null);

  // Create / Edit Drawer State
  const [showCreateDrawer, setShowCreateDrawer] = useState(false);
  const [editingGroupId, setEditingGroupId] = useState<number | null>(null);
  const [createForm, setCreateForm] = useState({
    name: "",
    payroll_type: "monthly_without_compliance",
    is_default: false,
  });
  const [formErrors, setFormErrors] = useState<Record<string, string>>({});

  // Members Drawer State (Opened when clicking Employee Count)
  const [showMembersDrawer, setShowMembersDrawer] = useState(false);
  const [selectedGroupForMembers, setSelectedGroupForMembers] = useState<PayrollGroupItem | null>(null);

  // Delete Confirmation Dialog State
  const [deleteConfirmGroup, setDeleteConfirmGroup] = useState<PayrollGroupItem | null>(null);

  // React Query Hooks
  const {
    data: groupsData,
    isLoading,
    isError,
    refetch,
  } = usePayrollGroups({
    page: currentPage,
    page_size: pageSize,
    search: searchQuery,
    sort_by: sortField,
    sort_order: sortOrder,
  });

  const createGroupMutation = useCreatePayrollGroup();
  const updateGroupMutation = useUpdatePayrollGroup();
  const deleteGroupMutation = useDeletePayrollGroup();

  // Group Members Query
  const { data: groupEmployeesData, isLoading: isLoadingMembers } = useGroupEmployees(
    selectedGroupForMembers?.id || 0,
    { page: 1, page_size: 100 }
  );

  const groupsList = groupsData?.items || [];
  const meta = groupsData?.meta as { total_records?: number } | undefined;
  const totalRecords: number = typeof meta?.total_records === "number" ? meta.total_records : groupsList.length;

  // Close active action dropdown when clicking outside
  React.useEffect(() => {
    const handleClickOutside = () => setActiveActionId(null);
    window.addEventListener("click", handleClickOutside);
    return () => window.removeEventListener("click", handleClickOutside);
  }, []);

  // Sorting Handler
  const handleSort = (field: string) => {
    if (sortField === field) {
      setSortOrder(sortOrder === "asc" ? "desc" : "asc");
    } else {
      setSortField(field);
      setSortOrder("asc");
    }
  };

  // Open Members Drawer
  const handleOpenMembersDrawer = (group: PayrollGroupItem) => {
    setSelectedGroupForMembers(group);
    setShowMembersDrawer(true);
  };

  // Open Edit Modal
  const handleOpenEdit = (group: PayrollGroupItem) => {
    setActiveActionId(null);
    setEditingGroupId(group.id);
    setCreateForm({
      name: group.name,
      payroll_type: group.payroll_type,
      is_default: group.is_default,
    });
    setFormErrors({});
    setShowCreateDrawer(true);
  };

  // Trigger Delete Confirmation Modal
  const handleOpenDelete = (group: PayrollGroupItem) => {
    setActiveActionId(null);
    if (group.is_default) {
      toast.error("Default payroll groups cannot be deleted.");
      return;
    }
    if (group.employee_count > 0) {
      toast.error(`Cannot delete group "${group.name}" with ${group.employee_count} assigned employees.`);
      return;
    }
    setDeleteConfirmGroup(group);
  };

  // Confirm Delete Action
  const handleConfirmDelete = async () => {
    if (!deleteConfirmGroup) return;
    try {
      await deleteGroupMutation.mutateAsync(deleteConfirmGroup.id);
      toast.success(`Deleted "${deleteConfirmGroup.name}" successfully.`);
      setDeleteConfirmGroup(null);
    } catch (err: unknown) {
      const errorObj = err as { response?: { data?: { message?: string } }; message?: string };
      const msg = errorObj?.response?.data?.message || errorObj?.message || "Failed to delete group.";
      toast.error(msg);
    }
  };

  // Submit Create / Edit Form
  const handleSaveGroup = async (e: React.FormEvent) => {
    e.preventDefault();
    const errors: Record<string, string> = {};
    if (!createForm.name.trim()) {
      errors.name = "Group Name is required.";
    }

    if (Object.keys(errors).length > 0) {
      setFormErrors(errors);
      return;
    }

    try {
      if (editingGroupId) {
        await updateGroupMutation.mutateAsync({
          id: editingGroupId,
          data: {
            name: createForm.name.trim(),
            payroll_type: createForm.payroll_type,
            is_default: createForm.is_default,
          },
        });
        toast.success("Payroll group updated successfully.");
      } else {
        await createGroupMutation.mutateAsync({
          name: createForm.name.trim(),
          payroll_type: createForm.payroll_type,
          is_default: createForm.is_default,
        });
        toast.success("Payroll group created successfully.");
      }

      setShowCreateDrawer(false);
      setEditingGroupId(null);
      setCreateForm({
        name: "",
        payroll_type: "monthly_without_compliance",
        is_default: false,
      });
    } catch (err: unknown) {
      const errorObj = err as { response?: { data?: { message?: string } }; message?: string };
      const msg = errorObj?.response?.data?.message || errorObj?.message || "Failed to save payroll group.";
      toast.error(msg);
    }
  };

  // Format Display Date
  const formatDateDisplay = (dateStr?: string) => {
    if (!dateStr) return "13 February 2026";
    try {
      return new Date(dateStr).toLocaleDateString("en-GB", {
        day: "2-digit",
        month: "long",
        year: "numeric",
      });
    } catch {
      return dateStr;
    }
  };

  // Helper mapping technical payroll_type to user display
  const getPayrollTypeLabel = (typeStr: string) => {
    switch (typeStr) {
      case "monthly_without_compliance":
        return "Monthly Without Compliance";
      case "monthly_with_compliance":
        return "Monthly With Compliance";
      case "hourly_payroll":
        return "Hourly Payroll";
      default:
        return typeStr;
    }
  };

  return (
    <ProtectedRoute requiredPermission={{ feature: "payroll_group", action: "read" }}>
      <div className="p-4 md:p-6 space-y-6 bg-slate-50/50 dark:bg-slate-950/40 min-h-screen text-slate-800 dark:text-slate-200">
        
        {/* Header Section */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
              Payroll Group ({totalRecords})
            </h1>
          </div>

          <div className="flex items-center gap-3">
            <Link
              href="/payroll/assign-payroll-group"
              className="px-4 py-2 text-xs font-semibold text-slate-700 dark:text-slate-200 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-700/60 rounded-lg transition-colors cursor-pointer flex items-center gap-1.5 shadow-xs"
            >
              <UserPlus className="w-3.5 h-3.5 text-slate-500" />
              <span>Assign Group</span>
            </Link>

            <button
              type="button"
              onClick={() => {
                setEditingGroupId(null);
                setCreateForm({
                  name: "",
                  payroll_type: "monthly_without_compliance",
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
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-xs min-h-[340px] flex flex-col justify-between">
          
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
                onClick={() => refetch()}
                className="px-4 py-2 text-xs font-semibold text-white bg-[#0B85C9] hover:bg-[#0974b0] rounded-lg cursor-pointer"
              >
                Retry
              </button>
            </div>
          ) : groupsList.length === 0 ? (
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
                className="px-4 py-2 text-xs font-semibold text-[#0B85C9] hover:underline cursor-pointer"
              >
                Reset Search
              </button>
            </div>
          ) : (
            /* Main Table */
            <div className="overflow-x-auto min-h-[240px] pb-16">
              <table className="w-full text-left border-collapse min-w-[800px]">
                <thead>
                  <tr className="bg-blue-50/70 dark:bg-slate-800/90 text-slate-700 dark:text-slate-300 text-xs font-semibold border-b border-slate-200 dark:border-slate-700 select-none">
                    
                    {/* Group Name Header */}
                    <th
                      onClick={() => handleSort("name")}
                      className="py-3 px-4 min-w-[280px] cursor-pointer hover:bg-blue-100/50 dark:hover:bg-slate-700 transition-colors"
                    >
                      <div className="flex items-center gap-1.5">
                        <span>Group Name</span>
                        {sortField === "name" ? (
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
                      onClick={() => handleSort("created_at")}
                      className="py-3 px-4 min-w-[160px] cursor-pointer hover:bg-blue-100/50 dark:hover:bg-slate-700 transition-colors"
                    >
                      <div className="flex items-center gap-1.5">
                        <span>Created On</span>
                        {sortField === "created_at" ? (
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
                      onClick={() => handleSort("updated_at")}
                      className="py-3 px-4 min-w-[160px] cursor-pointer hover:bg-blue-100/50 dark:hover:bg-slate-700 transition-colors"
                    >
                      <div className="flex items-center gap-1.5">
                        <span>Last Edited On</span>
                        {sortField === "updated_at" ? (
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
                  {groupsList.map((group) => (
                    <tr
                      key={group.id}
                      className="hover:bg-slate-50/60 dark:hover:bg-slate-800/40 transition-colors"
                    >
                      {/* Group Name & Default Badge */}
                      <td className="py-3.5 px-4">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-slate-900 dark:text-slate-100">
                            {group.name}
                          </span>
                          {group.is_default && (
                            <span className="px-2 py-0.5 text-[11px] font-medium bg-blue-50 dark:bg-blue-950/60 text-blue-600 dark:text-blue-400 rounded-md border border-blue-100 dark:border-blue-900/50 shrink-0">
                              Default
                            </span>
                          )}
                        </div>
                      </td>

                      {/* Employee Count (Clickable Underlined Button opening Group Members Drawer) */}
                      <td className="py-3.5 px-4 font-medium text-slate-900 dark:text-slate-100">
                        <button
                          type="button"
                          onClick={() => handleOpenMembersDrawer(group)}
                          className="underline underline-offset-2 hover:text-blue-600 cursor-pointer font-medium"
                        >
                          {group.employee_count}
                        </button>
                      </td>

                      {/* Created On */}
                      <td className="py-3.5 px-4 text-slate-700 dark:text-slate-300">
                        {formatDateDisplay(group.created_at)}
                      </td>

                      {/* Last Edited On */}
                      <td className="py-3.5 px-4 text-slate-700 dark:text-slate-300">
                        {formatDateDisplay(group.updated_at)}
                      </td>

                      {/* Action Cell */}
                      <td className="py-3.5 px-4 relative">
                        {group.is_default ? (
                          <span className="text-slate-400 font-bold ml-1">-</span>
                        ) : (
                          <div className="relative">
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                setActiveActionId(activeActionId === group.id ? null : group.id);
                              }}
                              className="p-1 rounded-md text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer"
                            >
                              <MoreVertical className="w-4 h-4" />
                            </button>

                            {/* Action Dropdown Menu */}
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
                                  onClick={() => handleOpenDelete(group)}
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

          {/* Pagination Controls */}
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
        {/* GROUP MEMBERS SLIDE-OVER DRAWER                      */}
        {/* ---------------------------------------------------- */}
        {showMembersDrawer && selectedGroupForMembers && (
          <div className="fixed inset-0 z-50 overflow-hidden bg-black/50 backdrop-blur-xs flex justify-end">
            <div className="w-full max-w-lg bg-white dark:bg-slate-900 h-full shadow-2xl flex flex-col border-l border-slate-200 dark:border-slate-800 animate-in slide-in-from-right duration-200">
              
              {/* Drawer Header */}
              <div className="flex items-center justify-between px-6 py-4 bg-blue-50/70 dark:bg-slate-800/80 border-b border-slate-200 dark:border-slate-800">
                <h2 className="text-base font-bold text-slate-900 dark:text-slate-100">
                  Payroll Group
                </h2>
                <button
                  type="button"
                  onClick={() => setShowMembersDrawer(false)}
                  className="p-1 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 cursor-pointer"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {/* Drawer Main Body */}
              <div className="flex-1 overflow-y-auto p-6 space-y-4 text-xs">
                <div className="space-y-1">
                  <div className="font-bold text-slate-900 dark:text-slate-100 text-sm">
                    Payroll Group: {selectedGroupForMembers.name}
                  </div>
                  <div className="text-slate-500 dark:text-slate-400 text-xs font-medium">
                    Total Employees: {groupEmployeesData?.total_employees ?? selectedGroupForMembers.employee_count}
                  </div>
                </div>

                {isLoadingMembers ? (
                  <div className="p-8 text-center space-y-3">
                    <div className="h-6 bg-slate-200 dark:bg-slate-800 rounded animate-pulse w-1/3 mx-auto" />
                    <div className="h-10 bg-slate-100 dark:bg-slate-800/50 rounded animate-pulse" />
                  </div>
                ) : (
                  <div className="border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden shadow-xs">
                    <table className="w-full text-left border-collapse">
                      <thead className="bg-slate-100/90 dark:bg-slate-800 text-slate-700 dark:text-slate-300 font-bold border-b border-slate-200 dark:border-slate-700 select-none">
                        <tr>
                          <th className="py-3 px-4 w-32">Employee ID</th>
                          <th className="py-3 px-4">Employee Name</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                        {(!groupEmployeesData?.items || groupEmployeesData.items.length === 0) ? (
                          <tr>
                            <td colSpan={2} className="py-8 px-4 text-center text-slate-400 font-medium">
                              No employees currently assigned to this group.
                            </td>
                          </tr>
                        ) : (
                          groupEmployeesData.items.map((emp) => (
                            <tr
                              key={emp.employee_id}
                              className="hover:bg-slate-50/60 dark:hover:bg-slate-800/40 transition-colors"
                            >
                              <td className="py-3 px-4 font-mono font-medium text-slate-700 dark:text-slate-300">
                                {emp.employee_id}
                              </td>
                              <td className="py-3 px-4 font-semibold text-slate-900 dark:text-slate-100">
                                {emp.employee_name}
                              </td>
                            </tr>
                          ))
                        )}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* ---------------------------------------------------- */}
        {/* CREATE / EDIT PAYROLL GROUP SLIDE-OVER DRAWER        */}
        {/* ---------------------------------------------------- */}
        {showCreateDrawer && (
          <div className="fixed inset-0 z-50 overflow-hidden bg-black/50 backdrop-blur-xs flex justify-end">
            <div className="w-full max-w-md bg-white dark:bg-slate-900 h-full shadow-2xl flex flex-col border-l border-slate-200 dark:border-slate-800 animate-in slide-in-from-right duration-200">
              
              {/* Drawer Header */}
              <div className="flex items-center justify-between px-6 py-4 bg-blue-50/70 dark:bg-slate-800/80 border-b border-slate-200 dark:border-slate-800">
                <h2 className="text-base font-bold text-slate-900 dark:text-slate-100">
                  {editingGroupId ? "Edit Payroll Group" : "New Payroll Group"}
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
                      value={createForm.name}
                      onChange={(e) => {
                        setCreateForm((prev) => ({ ...prev, name: e.target.value }));
                        if (formErrors.name) setFormErrors((prev) => ({ ...prev, name: "" }));
                      }}
                      className={`w-full p-2.5 bg-white dark:bg-slate-800 border ${
                        formErrors.name
                          ? "border-red-500 focus:ring-red-500"
                          : "border-slate-200 dark:border-slate-700 focus:ring-blue-500"
                      } rounded-lg font-medium text-slate-800 dark:text-slate-100 focus:outline-none focus:ring-2`}
                    />
                    {formErrors.name && (
                      <p className="text-[11px] text-red-500 mt-1 font-medium">{formErrors.name}</p>
                    )}
                  </div>

                  {/* Payroll Type Dropdown */}
                  <div>
                    <label className="block font-medium text-slate-700 dark:text-slate-300 mb-1.5">
                      Payroll Type<span className="text-red-500">*</span>
                    </label>
                    <select
                      value={createForm.payroll_type}
                      onChange={(e) =>
                        setCreateForm((prev) => ({ ...prev, payroll_type: e.target.value }))
                      }
                      className="w-full p-2.5 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg font-medium text-slate-800 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer"
                    >
                      <option value="monthly_without_compliance">Monthly Without Compliance</option>
                      <option value="monthly_with_compliance">Monthly With Compliance</option>
                      <option value="hourly_payroll">Hourly Payroll</option>
                    </select>
                  </div>
                </div>

                {/* Footer Action Buttons */}
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
                    disabled={!createForm.name.trim() || createGroupMutation.isPending || updateGroupMutation.isPending}
                    className={`px-5 py-2 text-xs font-semibold rounded-lg shadow-xs transition-colors ${
                      createForm.name.trim() && !createGroupMutation.isPending && !updateGroupMutation.isPending
                        ? "bg-[#0B85C9] text-white hover:bg-[#0974b0] cursor-pointer"
                        : "bg-[#D1D5DB] text-white cursor-not-allowed"
                    }`}
                  >
                    {editingGroupId ? "Save Changes" : "Create"}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* ---------------------------------------------------- */}
        {/* DELETE CONFIRMATION DIALOG                           */}
        {/* ---------------------------------------------------- */}
        {deleteConfirmGroup && (
          <div className="fixed inset-0 z-50 overflow-hidden bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
            <div className="bg-white dark:bg-slate-900 rounded-2xl max-w-sm w-full p-6 shadow-2xl border border-slate-200 dark:border-slate-800 space-y-4 animate-in zoom-in-95 duration-150">
              <div className="w-12 h-12 rounded-full bg-red-100 dark:bg-red-950/50 text-red-600 dark:text-red-400 flex items-center justify-center mx-auto">
                <AlertCircle className="w-6 h-6" />
              </div>
              <div className="text-center space-y-1">
                <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">
                  Delete Payroll Group?
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Are you sure you want to delete <span className="font-semibold text-slate-800 dark:text-slate-200">&quot;{deleteConfirmGroup.name}&quot;</span> ({getPayrollTypeLabel(deleteConfirmGroup.payroll_type)})? This action cannot be undone.
                </p>
              </div>
              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setDeleteConfirmGroup(null)}
                  className="px-4 py-2 text-xs font-semibold text-slate-700 dark:text-slate-300 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800 cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  disabled={deleteGroupMutation.isPending}
                  onClick={handleConfirmDelete}
                  className="px-4 py-2 text-xs font-semibold text-white bg-red-600 hover:bg-red-700 rounded-lg shadow-xs cursor-pointer disabled:opacity-50"
                >
                  Delete
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </ProtectedRoute>
  );
}
