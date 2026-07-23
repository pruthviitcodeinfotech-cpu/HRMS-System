"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  MoreVertical,
  ChevronDown,
  ChevronsUpDown,
  Edit2,
  Trash2,
  Eye,
  Copy,
  CheckCircle2,
  XCircle,
  ShieldCheck,
  History,
  Search,
  RotateCw,
  AlertCircle,
  Plus,
  X,
  Loader2,
  Users,
  UserPlus,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  useRightsTemplates,
  useDeleteRightsTemplate,
  useDuplicateRightsTemplate,
  useActivateRightsTemplate,
  useDeactivateRightsTemplate,
  useRightsTemplateDetail,
  useRightsTemplatesLogs,
} from "../hooks/use-rights-templates";
import { PermissionGuard } from "@/features/auth";
import { RightsTemplate } from "../types";
import { AssignTemplateModal } from "./assign-template-modal";
import { ManageUsersPage } from "./manage-users-page";

export function UserManagementPage() {
  const router = useRouter();

  // Primary Section Tab State ("templates" | "users")
  const [activeTab, setActiveTab] = useState<"templates" | "users">("templates");

  // Search & Filters
  const [searchQuery, setSearchQuery] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");

  // Pagination & Sorting
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("asc");

  // Debounce search
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedSearch(searchQuery);
      setCurrentPage(1);
    }, 400);
    return () => clearTimeout(handler);
  }, [searchQuery]);

  // React Query Hook - Live Backend API
  const {
    data: paginatedData,
    isLoading,
    isError,
    error,
    refetch,
    isFetching,
  } = useRightsTemplates({
    page: currentPage,
    page_size: pageSize,
    search: debouncedSearch || undefined,
  });

  // Action mutations
  const deleteMutation = useDeleteRightsTemplate();
  const duplicateMutation = useDuplicateRightsTemplate();
  const activateMutation = useActivateRightsTemplate();
  const deactivateMutation = useDeactivateRightsTemplate();

  // Active Dropdown & Modal State
  const [activeActionRowId, setActiveActionRowId] = useState<number | null>(null);
  const actionMenuRef = useRef<HTMLTableCellElement>(null);

  // Modals state
  const [assignModalTemplateId, setAssignModalTemplateId] = useState<number | null>(null);
  const [isAssignModalOpen, setIsAssignModalOpen] = useState(false);

  const [viewDetailId, setViewDetailId] = useState<number | null>(null);
  const [duplicateModalItem, setDuplicateModalItem] = useState<RightsTemplate | null>(null);
  const [duplicateName, setDuplicateName] = useState("");
  const [deleteConfirmItem, setDeleteConfirmItem] = useState<RightsTemplate | null>(null);
  const [isLogsModalOpen, setIsLogsModalOpen] = useState(false);

  // Query detail for View modal
  const { data: detailData, isLoading: isDetailLoading } = useRightsTemplateDetail(
    viewDetailId || undefined
  );

  // Query logs for Logs modal
  const { data: logsData, isLoading: isLogsLoading } = useRightsTemplatesLogs();

  // Close dropdown on click outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        actionMenuRef.current &&
        !actionMenuRef.current.contains(event.target as Node)
      ) {
        setActiveActionRowId(null);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

  const items = paginatedData?.items || [];
  const totalRecords = paginatedData?.total_records || 0;
  const totalPages = paginatedData?.total_pages || Math.ceil(totalRecords / pageSize) || 1;

  // Sorting
  const sortedItems = [...items].sort((a, b) => {
    if (sortOrder === "asc") return a.name.localeCompare(b.name);
    return b.name.localeCompare(a.name);
  });

  // Date formatter
  const formatDate = (dateStr?: string) => {
    if (!dateStr) return "-";
    try {
      const date = new Date(dateStr);
      return new Intl.DateTimeFormat("en-GB", {
        day: "2-digit",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
      }).format(date);
    } catch {
      return dateStr;
    }
  };

  const handleDuplicateSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!duplicateModalItem || !duplicateName.trim()) return;
    duplicateMutation.mutate(
      { id: duplicateModalItem.id, name: duplicateName.trim() },
      {
        onSuccess: () => {
          setDuplicateModalItem(null);
          setDuplicateName("");
        },
      }
    );
  };

  const handleDeleteConfirm = () => {
    if (!deleteConfirmItem) return;
    deleteMutation.mutate(deleteConfirmItem.id, {
      onSuccess: () => setDeleteConfirmItem(null),
    });
  };

  return (
    <div className="p-6 max-w-[1600px] mx-auto space-y-6 animate-in fade-in duration-200">
      {/* Primary Navigation Section Tabs */}
      <div className="flex items-center space-x-1 border-b border-slate-200 dark:border-slate-800 pb-2">
        <button
          onClick={() => setActiveTab("templates")}
          className={`px-4 py-2 text-xs font-bold rounded-lg transition-all cursor-pointer flex items-center space-x-2 ${
            activeTab === "templates"
              ? "bg-blue-600 text-white shadow-2xs"
              : "text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
          }`}
        >
          <ShieldCheck className="h-4 w-4" />
          <span>Manage Rights Templates</span>
        </button>

        <button
          onClick={() => setActiveTab("users")}
          className={`px-4 py-2 text-xs font-bold rounded-lg transition-all cursor-pointer flex items-center space-x-2 ${
            activeTab === "users"
              ? "bg-blue-600 text-white shadow-2xs"
              : "text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
          }`}
        >
          <Users className="h-4 w-4" />
          <span>Manage Users & Assignments</span>
        </button>
      </div>

      {/* Render Tab 2: Manage Users */}
      {activeTab === "users" ? (
        <ManageUsersPage />
      ) : (
        <>
          {/* Page Header */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h1 className="text-xl font-bold text-slate-800 dark:text-slate-100 tracking-tight">
                Manage Rights Templates
              </h1>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                Configure access templates and role-based permissions
              </p>
            </div>

            <div className="flex items-center space-x-3">
              <Button
                type="button"
                variant="outline"
                onClick={() => refetch()}
                disabled={isFetching}
                className="bg-white dark:bg-slate-900 border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 text-xs font-semibold px-3 py-2 h-9 rounded-md transition-all cursor-pointer"
                title="Refresh Templates"
              >
                <RotateCw className={`h-3.5 w-3.5 mr-1.5 ${isFetching ? "animate-spin" : ""}`} />
                <span>Refresh</span>
              </Button>

              <Button
                type="button"
                onClick={() => setIsLogsModalOpen(true)}
                variant="outline"
                className="bg-white dark:bg-slate-900 border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 text-xs font-semibold px-3 py-2 h-9 rounded-md transition-all cursor-pointer"
              >
                <History className="h-3.5 w-3.5 mr-1.5 text-slate-500" />
                <span>View Logs</span>
              </Button>

              <PermissionGuard permission={{ feature: "user_management", action: "edit" }}>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => {
                    setAssignModalTemplateId(null);
                    setIsAssignModalOpen(true);
                  }}
                  className="bg-white dark:bg-slate-900 border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 text-xs font-semibold px-3 py-2 h-9 rounded-md transition-all cursor-pointer"
                >
                  <UserPlus className="h-3.5 w-3.5 mr-1.5 text-blue-600" />
                  <span>Assign Group</span>
                </Button>
              </PermissionGuard>

              <PermissionGuard permission={{ feature: "user_management", action: "create" }}>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setActiveTab("users")}
                  className="bg-white dark:bg-slate-900 border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 text-xs font-semibold px-3 py-2 h-9 rounded-md transition-all cursor-pointer"
                >
                  <UserPlus className="h-3.5 w-3.5 mr-1.5 text-blue-600" />
                  <span>Create User</span>
                </Button>
              </PermissionGuard>

              <PermissionGuard permission={{ feature: "user_management", action: "create" }}>
                <Button
                  type="button"
                  onClick={() => router.push("/right-template")}
                  className="bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold px-4 py-2 h-9 rounded-md shadow-2xs transition-all cursor-pointer"
                >
                  <Plus className="h-4 w-4 mr-1.5" />
                  <span>Create Template</span>
                </Button>
              </PermissionGuard>
            </div>
          </div>

          {/* Filter & Search Bar */}
          <div className="flex items-center justify-between bg-white dark:bg-slate-900 p-4 border border-slate-200 dark:border-slate-800 rounded-lg shadow-2xs">
            <div className="relative w-full sm:w-80">
              <Search className="h-3.5 w-3.5 text-slate-400 absolute left-3 top-2.5 pointer-events-none" />
              <Input
                type="text"
                placeholder="Search templates by name..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9 text-xs bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-700 h-9 rounded-md"
              />
            </div>
          </div>

          {/* Error Alert Banner */}
          {isError && (
            <div className="p-4 bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800 rounded-lg flex items-center justify-between text-xs text-red-700 dark:text-red-300">
              <div className="flex items-center space-x-2">
                <AlertCircle className="h-4 w-4 text-red-500 shrink-0" />
                <span>
                  {(error as any)?.message || "Failed to load rights templates from backend server."}
                </span>
              </div>
              <Button
                size="sm"
                variant="outline"
                onClick={() => refetch()}
                className="h-7 text-xs border-red-300 text-red-700 dark:text-red-300 hover:bg-red-100"
              >
                Retry
              </Button>
            </div>
          )}

          {/* Rights Templates Data Table Card */}
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg shadow-2xs flex flex-col justify-between min-h-[420px] relative">
            <div className="w-full">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-[#eef6ff] dark:bg-slate-800/80 border-b border-slate-200 dark:border-slate-700/80">
                    <th className="py-3 px-4 text-xs font-semibold text-slate-700 dark:text-slate-200 whitespace-nowrap">
                      <button
                        type="button"
                        onClick={() => setSortOrder(sortOrder === "asc" ? "desc" : "asc")}
                        className="flex items-center space-x-1.5 cursor-pointer select-none"
                      >
                        <span>Template Name</span>
                        <ChevronsUpDown className="h-3.5 w-3.5 text-slate-500 dark:text-slate-400 shrink-0" />
                      </button>
                    </th>
                    <th className="py-3 px-4 text-xs font-semibold text-slate-700 dark:text-slate-200 whitespace-nowrap">
                      Assigned Users Count
                    </th>
                    <th className="py-3 px-4 text-xs font-semibold text-slate-700 dark:text-slate-200 whitespace-nowrap">
                      Created On
                    </th>
                    <th className="py-3 px-4 text-xs font-semibold text-slate-700 dark:text-slate-200 whitespace-nowrap">
                      Last Modified
                    </th>
                    <th className="py-3 px-4 text-xs font-semibold text-slate-700 dark:text-slate-200 whitespace-nowrap">
                      Status
                    </th>
                    <th className="py-3 px-4 text-xs font-semibold text-slate-700 dark:text-slate-200 text-right pr-6 whitespace-nowrap">
                      Action
                    </th>
                  </tr>
                </thead>

                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {/* Skeleton Loading State */}
                  {isLoading &&
                    Array.from({ length: 5 }).map((_, idx) => (
                      <tr key={idx} className="animate-pulse">
                        <td className="py-4 px-4"><div className="h-4 bg-slate-200 dark:bg-slate-800 rounded w-28" /></td>
                        <td className="py-4 px-4"><div className="h-4 bg-slate-200 dark:bg-slate-800 rounded w-12" /></td>
                        <td className="py-4 px-4"><div className="h-4 bg-slate-200 dark:bg-slate-800 rounded w-36" /></td>
                        <td className="py-4 px-4"><div className="h-4 bg-slate-200 dark:bg-slate-800 rounded w-36" /></td>
                        <td className="py-4 px-4"><div className="h-4 bg-slate-200 dark:bg-slate-800 rounded w-16" /></td>
                        <td className="py-4 px-4 text-right pr-6"><div className="h-6 bg-slate-200 dark:bg-slate-800 rounded w-8 ml-auto" /></td>
                      </tr>
                    ))}

                  {/* Empty State */}
                  {!isLoading && sortedItems.length === 0 && (
                    <tr>
                      <td colSpan={6} className="py-12 text-center">
                        <div className="flex flex-col items-center justify-center space-y-3">
                          <ShieldCheck className="h-10 w-10 text-slate-300 dark:text-slate-700" />
                          <p className="text-sm font-semibold text-slate-700 dark:text-slate-300">
                            No Rights Templates Found
                          </p>
                          <p className="text-xs text-slate-500 max-w-sm">
                            {debouncedSearch
                              ? `No template matching "${debouncedSearch}" was found.`
                              : "Get started by creating your first access rights template."}
                          </p>
                          {debouncedSearch ? (
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => setSearchQuery("")}
                              className="text-xs"
                            >
                              Clear Search
                            </Button>
                          ) : (
                            <Button
                              onClick={() => router.push("/right-template")}
                              className="text-xs bg-blue-600 hover:bg-blue-700 text-white"
                            >
                              <Plus className="h-3.5 w-3.5 mr-1" />
                              Create Template
                            </Button>
                          )}
                        </div>
                      </td>
                    </tr>
                  )}

                  {/* Data Rows */}
                  {!isLoading &&
                    sortedItems.map((template, idx) => {
                      const isDeleted = template.is_deleted ?? false;
                      const isNearBottom =
                        idx >= Math.max(0, sortedItems.length - 2) ||
                        sortedItems.length <= 3;
                      return (
                        <tr
                          key={template.id}
                          className="hover:bg-slate-50/60 dark:hover:bg-slate-800/40 transition-colors"
                        >
                          <td className="py-4 px-4 text-xs font-semibold text-slate-800 dark:text-slate-100">
                            {template.name}
                          </td>
                          <td className="py-4 px-4 text-xs font-normal text-slate-700 dark:text-slate-300">
                            {template.assigned_user_count ?? 0}
                          </td>
                          <td className="py-4 px-4 text-xs font-normal text-slate-600 dark:text-slate-400">
                            {formatDate(template.created_at)}
                          </td>
                          <td className="py-4 px-4 text-xs font-normal text-slate-600 dark:text-slate-400">
                            {formatDate(template.updated_at)}
                          </td>
                          <td className="py-4 px-4 text-xs">
                            <span
                              className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                                !isDeleted
                                  ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-900"
                                  : "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400 border border-slate-200 dark:border-slate-700"
                              }`}
                            >
                              {!isDeleted ? "Active" : "Inactive"}
                            </span>
                          </td>
                          <td
                            ref={activeActionRowId === template.id ? actionMenuRef : null}
                            className="py-4 px-4 text-xs text-right pr-6 relative"
                          >
                            <button
                              onClick={() =>
                                setActiveActionRowId(
                                  activeActionRowId === template.id ? null : template.id
                                )
                              }
                              className="p-1.5 border border-slate-200 dark:border-slate-700 rounded-md hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 dark:text-slate-400 transition-colors cursor-pointer inline-flex items-center justify-center bg-white dark:bg-slate-900"
                              title="Actions"
                            >
                              <MoreVertical className="h-4 w-4" />
                            </button>

                            {/* Action Dropdown Menu */}
                            {activeActionRowId === template.id && (
                              <div
                                className={`absolute right-4 z-50 w-52 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700/90 rounded-lg shadow-2xl py-1.5 text-left animate-in fade-in zoom-in-95 duration-150 ${
                                  isNearBottom ? "bottom-full mb-1" : "top-full mt-1"
                                }`}
                              >
                                {/* View */}
                                <button
                                  onClick={() => {
                                    setActiveActionRowId(null);
                                    setViewDetailId(template.id);
                                  }}
                                  className="w-full flex items-center space-x-2.5 px-3.5 py-2 text-xs text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors cursor-pointer"
                                >
                                  <Eye className="h-3.5 w-3.5 text-slate-500" />
                                  <span>View Details</span>
                                </button>

                                {/* Edit */}
                                <button
                                  onClick={() => {
                                    setActiveActionRowId(null);
                                    router.push(`/right-template?id=${template.id}`);
                                  }}
                                  className="w-full flex items-center space-x-2.5 px-3.5 py-2 text-xs text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors cursor-pointer"
                                >
                                  <Edit2 className="h-3.5 w-3.5 text-slate-500" />
                                  <span>Edit Template</span>
                                </button>

                                {/* Assign Users to this Template */}
                                <button
                                  onClick={() => {
                                    setActiveActionRowId(null);
                                    setAssignModalTemplateId(template.id);
                                    setIsAssignModalOpen(true);
                                  }}
                                  className="w-full flex items-center space-x-2.5 px-3.5 py-2 text-xs text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors cursor-pointer"
                                >
                                  <UserPlus className="h-3.5 w-3.5 text-blue-500" />
                                  <span>Assign Users to Template</span>
                                </button>

                                {/* Duplicate */}
                                <button
                                  onClick={() => {
                                    setActiveActionRowId(null);
                                    setDuplicateModalItem(template);
                                    setDuplicateName(`${template.name} (Copy)`);
                                  }}
                                  className="w-full flex items-center space-x-2.5 px-3.5 py-2 text-xs text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors cursor-pointer"
                                >
                                  <Copy className="h-3.5 w-3.5 text-slate-500" />
                                  <span>Duplicate</span>
                                </button>

                                {/* Manage Permissions */}
                                <button
                                  onClick={() => {
                                    setActiveActionRowId(null);
                                    router.push(`/right-template?id=${template.id}`);
                                  }}
                                  className="w-full flex items-center space-x-2.5 px-3.5 py-2 text-xs text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors cursor-pointer"
                                >
                                  <ShieldCheck className="h-3.5 w-3.5 text-blue-500" />
                                  <span>Manage Permissions</span>
                                </button>

                                <div className="border-t border-slate-100 dark:border-slate-800 my-1" />

                                {/* Activate / Deactivate Toggle */}
                                {isDeleted ? (
                                  <button
                                    onClick={() => {
                                      setActiveActionRowId(null);
                                      activateMutation.mutate(template.id);
                                    }}
                                    className="w-full flex items-center space-x-2.5 px-3.5 py-2 text-xs text-emerald-600 dark:text-emerald-400 hover:bg-emerald-50 dark:hover:bg-emerald-950/30 transition-colors cursor-pointer"
                                  >
                                    <CheckCircle2 className="h-3.5 w-3.5" />
                                    <span>Activate</span>
                                  </button>
                                ) : (
                                  <button
                                    onClick={() => {
                                      setActiveActionRowId(null);
                                      deactivateMutation.mutate(template.id);
                                    }}
                                    className="w-full flex items-center space-x-2.5 px-3.5 py-2 text-xs text-amber-600 dark:text-amber-400 hover:bg-amber-50 dark:hover:bg-amber-950/30 transition-colors cursor-pointer"
                                  >
                                    <XCircle className="h-3.5 w-3.5" />
                                    <span>Deactivate</span>
                                  </button>
                                )}

                                {/* Delete */}
                                <button
                                  onClick={() => {
                                    setActiveActionRowId(null);
                                    setDeleteConfirmItem(template);
                                  }}
                                  className="w-full flex items-center space-x-2.5 px-3.5 py-2 text-xs text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-950/30 transition-colors cursor-pointer"
                                >
                                  <Trash2 className="h-3.5 w-3.5" />
                                  <span>Delete</span>
                                </button>
                              </div>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                </tbody>
              </table>
            </div>

            {/* Table Footer & Pagination */}
            <div className="flex flex-col sm:flex-row items-center justify-between px-4 py-3 border-t border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-xs text-slate-500 dark:text-slate-400 gap-3 mt-auto rounded-b-lg">
              <div className="text-slate-600 dark:text-slate-400">
                Showing{" "}
                <span className="font-bold text-slate-800 dark:text-slate-200">
                  {totalRecords > 0 ? (currentPage - 1) * pageSize + 1 : 0}
                </span>{" "}
                to{" "}
                <span className="font-bold text-slate-800 dark:text-slate-200">
                  {Math.min(currentPage * pageSize, totalRecords)}
                </span>{" "}
                of{" "}
                <span className="font-bold text-slate-800 dark:text-slate-200">{totalRecords}</span>{" "}
                Results
              </div>

              <div className="flex items-center space-x-3">
                <div className="relative inline-block text-left">
                  <select
                    value={pageSize}
                    onChange={(e) => {
                      setPageSize(Number(e.target.value));
                      setCurrentPage(1);
                    }}
                    className="appearance-none bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-md px-3 py-1 pr-8 text-xs font-medium text-slate-700 dark:text-slate-200 cursor-pointer focus:outline-none hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
                  >
                    <option value={10}>10 / Page</option>
                    <option value={25}>25 / Page</option>
                    <option value={50}>50 / Page</option>
                    <option value={100}>100 / Page</option>
                  </select>
                  <ChevronDown className="h-3.5 w-3.5 text-slate-500 absolute right-2.5 top-2 pointer-events-none" />
                </div>

                <div className="flex items-center space-x-1.5">
                  <button
                    disabled={currentPage <= 1 || isLoading}
                    onClick={() => setCurrentPage((p) => Math.max(p - 1, 1))}
                    className="px-3 py-1 border border-slate-200 dark:border-slate-800 rounded-md text-slate-700 dark:text-slate-300 disabled:text-slate-300 dark:disabled:text-slate-600 bg-white dark:bg-slate-900 text-xs font-medium cursor-pointer disabled:cursor-not-allowed hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
                  >
                    Previous
                  </button>

                  <button className="px-2.5 py-1 bg-blue-600 text-white rounded-md text-xs font-bold shadow-2xs">
                    {currentPage}
                  </button>

                  <button
                    disabled={currentPage >= totalPages || isLoading}
                    onClick={() => setCurrentPage((p) => Math.min(p + 1, totalPages))}
                    className="px-3 py-1 border border-slate-200 dark:border-slate-800 rounded-md text-slate-700 dark:text-slate-300 disabled:text-slate-300 dark:disabled:text-slate-600 bg-white dark:bg-slate-900 text-xs font-medium cursor-pointer disabled:cursor-not-allowed hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
                  >
                    Next
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* View Detail Modal */}
          {viewDetailId && (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4 animate-in fade-in duration-150">
              <div className="w-full max-w-lg rounded-xl bg-white dark:bg-slate-900 shadow-2xl border border-slate-200 dark:border-slate-800 overflow-hidden flex flex-col max-h-[85vh]">
                <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 dark:border-slate-800">
                  <h2 className="text-base font-semibold text-slate-800 dark:text-slate-100">
                    Template Details
                  </h2>
                  <button
                    onClick={() => setViewDetailId(null)}
                    className="p-1 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800"
                  >
                    <X className="h-5 w-5" />
                  </button>
                </div>

                <div className="p-6 space-y-4 overflow-y-auto flex-1 text-xs">
                  {isDetailLoading ? (
                    <div className="py-8 flex justify-center items-center">
                      <Loader2 className="h-6 w-6 text-blue-600 animate-spin" />
                    </div>
                  ) : detailData ? (
                    <div className="space-y-4">
                      <div>
                        <span className="text-slate-400 block mb-0.5">Template Name</span>
                        <span className="font-semibold text-slate-800 dark:text-slate-100 text-sm">
                          {detailData.name}
                        </span>
                      </div>

                      <div className="grid grid-cols-2 gap-4 pt-2 border-t border-slate-100 dark:border-slate-800">
                        <div>
                          <span className="text-slate-400 block mb-0.5">Assigned Users</span>
                          <span className="font-medium text-slate-700 dark:text-slate-300">
                            {detailData.assigned_user_count ?? 0}
                          </span>
                        </div>
                        <div>
                          <span className="text-slate-400 block mb-0.5">Permissions Count</span>
                          <span className="font-medium text-slate-700 dark:text-slate-300">
                            {detailData.permissions?.length || 0}
                          </span>
                        </div>
                      </div>

                      <div className="grid grid-cols-2 gap-4 pt-2 border-t border-slate-100 dark:border-slate-800">
                        <div>
                          <span className="text-slate-400 block mb-0.5">Created On</span>
                          <span className="text-slate-600 dark:text-slate-400">
                            {formatDate(detailData.created_at)}
                          </span>
                        </div>
                        <div>
                          <span className="text-slate-400 block mb-0.5">Last Modified</span>
                          <span className="text-slate-600 dark:text-slate-400">
                            {formatDate(detailData.updated_at)}
                          </span>
                        </div>
                      </div>
                    </div>
                  ) : null}
                </div>

                <div className="px-6 py-3 border-t border-slate-100 dark:border-slate-800 flex justify-end">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setViewDetailId(null)}
                    className="text-xs"
                  >
                    Close
                  </Button>
                </div>
              </div>
            </div>
          )}

          {/* Duplicate Template Modal */}
          {duplicateModalItem && (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4 animate-in fade-in duration-150">
              <div className="w-full max-w-md rounded-xl bg-white dark:bg-slate-900 shadow-2xl border border-slate-200 dark:border-slate-800 overflow-hidden">
                <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 dark:border-slate-800">
                  <h2 className="text-base font-semibold text-slate-800 dark:text-slate-100">
                    Duplicate Template
                  </h2>
                  <button
                    onClick={() => setDuplicateModalItem(null)}
                    className="p-1 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                  >
                    <X className="h-5 w-5" />
                  </button>
                </div>

                <form onSubmit={handleDuplicateSubmit} className="p-6 space-y-4 text-xs">
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                      New Template Name <span className="text-red-500">*</span>
                    </label>
                    <Input
                      type="text"
                      value={duplicateName}
                      onChange={(e) => setDuplicateName(e.target.value)}
                      placeholder="Enter duplicate template name"
                      className="text-xs"
                    />
                  </div>

                  <div className="flex justify-end space-x-2 pt-2">
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => setDuplicateModalItem(null)}
                    >
                      Cancel
                    </Button>
                    <Button
                      type="submit"
                      size="sm"
                      disabled={!duplicateName.trim() || duplicateMutation.isPending}
                      className="bg-blue-600 hover:bg-blue-700 text-white"
                    >
                      {duplicateMutation.isPending ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      ) : (
                        "Duplicate"
                      )}
                    </Button>
                  </div>
                </form>
              </div>
            </div>
          )}

          {/* Soft Delete Confirm Modal */}
          {deleteConfirmItem && (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4 animate-in fade-in duration-150">
              <div className="w-full max-w-md rounded-xl bg-white dark:bg-slate-900 shadow-2xl border border-slate-200 dark:border-slate-800 p-6 space-y-4 text-xs">
                <div className="flex items-center space-x-3 text-red-600">
                  <AlertCircle className="h-6 w-6 shrink-0" />
                  <h3 className="text-base font-semibold text-slate-800 dark:text-slate-100">
                    Delete Rights Template?
                  </h3>
                </div>

                <p className="text-slate-600 dark:text-slate-400">
                  Are you sure you want to delete template{" "}
                  <strong className="text-slate-800 dark:text-slate-200">
                    "{deleteConfirmItem.name}"
                  </strong>
                  ? Soft deleted templates can be restored later.
                </p>

                <div className="flex justify-end space-x-2 pt-3 border-t border-slate-100 dark:border-slate-800">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setDeleteConfirmItem(null)}
                  >
                    Cancel
                  </Button>
                  <Button
                    size="sm"
                    disabled={deleteMutation.isPending}
                    onClick={handleDeleteConfirm}
                    className="bg-red-600 hover:bg-red-700 text-white"
                  >
                    {deleteMutation.isPending ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : (
                      "Delete Template"
                    )}
                  </Button>
                </div>
              </div>
            </div>
          )}

          {/* Audit Logs Modal */}
          {isLogsModalOpen && (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4 animate-in fade-in duration-150">
              <div className="w-full max-w-2xl rounded-xl bg-white dark:bg-slate-900 shadow-2xl border border-slate-200 dark:border-slate-800 overflow-hidden flex flex-col max-h-[85vh]">
                <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 dark:border-slate-800">
                  <div className="flex items-center space-x-2">
                    <History className="h-5 w-5 text-blue-600" />
                    <h2 className="text-base font-semibold text-slate-800 dark:text-slate-100">
                      Rights Templates Audit Logs
                    </h2>
                  </div>
                  <button
                    onClick={() => setIsLogsModalOpen(false)}
                    className="p-1 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                  >
                    <X className="h-5 w-5" />
                  </button>
                </div>

                <div className="p-6 space-y-3 overflow-y-auto flex-1 text-xs">
                  {isLogsLoading ? (
                    <div className="py-8 flex justify-center">
                      <Loader2 className="h-6 w-6 text-blue-600 animate-spin" />
                    </div>
                  ) : logsData && logsData.length > 0 ? (
                    <div className="space-y-2">
                      {logsData.map((log) => (
                        <div
                          key={log.id}
                          className="p-3 border border-slate-100 dark:border-slate-800 rounded-lg bg-slate-50/50 dark:bg-slate-800/30 flex items-start justify-between"
                        >
                          <div className="space-y-0.5">
                            <span className="font-semibold text-slate-800 dark:text-slate-200">
                              {log.action}
                            </span>
                            <p className="text-slate-600 dark:text-slate-400">{log.description}</p>
                          </div>
                          <span className="text-[10px] text-slate-400 shrink-0 ml-4">
                            {formatDate(log.created_at)}
                          </span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="py-8 text-center text-slate-400 italic">
                      No audit log entries recorded yet for rights templates.
                    </div>
                  )}
                </div>

                <div className="px-6 py-3 border-t border-slate-100 dark:border-slate-800 flex justify-end">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setIsLogsModalOpen(false)}
                  >
                    Close
                  </Button>
                </div>
              </div>
            </div>
          )}

          {/* Assign Template Modal */}
          <AssignTemplateModal
            isOpen={isAssignModalOpen}
            onClose={() => setIsAssignModalOpen(false)}
            initialTemplateId={assignModalTemplateId}
          />
        </>
      )}
    </div>
  );
}
