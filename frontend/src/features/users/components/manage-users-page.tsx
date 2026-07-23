"use client";

import { useState, useRef, useEffect, useMemo } from "react";
import { useRouter } from "next/navigation";
import {
  MoreVertical,
  ChevronsUpDown,
  Eye,
  Edit2,
  ShieldCheck,
  UserCheck,
  UserX,
  Trash2,
  AlertCircle,
  ChevronDown,
  User,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { PermissionGuard } from "@/features/auth";
import { useUsers } from "../hooks/use-users";

type SortField = "name" | "phone" | "email" | "template";
type SortOrder = "asc" | "desc";

export function ManageUsersPage() {
  const router = useRouter();

  // Search state with debouncing
  const [searchQuery, setSearchQuery] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");

  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  // Sorting state
  const [sortField, setSortField] = useState<SortField>("name");
  const [sortOrder, setSortOrder] = useState<SortOrder>("asc");

  // Active Dropdown Row State
  const [activeActionRowId, setActiveActionRowId] = useState<number | null>(null);
  const actionMenuRef = useRef<HTMLTableCellElement>(null);

  // Debounce search input
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedSearch(searchQuery);
      setCurrentPage(1);
    }, 400);
    return () => clearTimeout(handler);
  }, [searchQuery]);

  // Close dropdown menu on click outside
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

  // React Query Hook - Live Backend API
  const {
    data: paginatedData,
    isLoading,
    isError,
    error,
    refetch,
  } = useUsers({
    page: currentPage,
    page_size: pageSize,
    search: debouncedSearch || undefined,
  });

  const rawUsersList = paginatedData?.items || [];
  const totalRecords = paginatedData?.total_records || rawUsersList.length;
  const totalPages = paginatedData?.total_pages || Math.ceil(totalRecords / pageSize) || 1;

  // Client-side Sorting for Name, Phone, Email, and Template
  const sortedUsers = useMemo(() => {
    return [...rawUsersList].sort((a, b) => {
      let aVal = "";
      let bVal = "";

      if (sortField === "name") {
        aVal = a.name.toLowerCase();
        bVal = b.name.toLowerCase();
      } else if (sortField === "phone") {
        aVal = (a.mobile_number || "").toLowerCase();
        bVal = (b.mobile_number || "").toLowerCase();
      } else if (sortField === "email") {
        aVal = (a.email || "").toLowerCase();
        bVal = (b.email || "").toLowerCase();
      } else if (sortField === "template") {
        aVal = (a.template?.name || "").toLowerCase();
        bVal = (b.template?.name || "").toLowerCase();
      }

      if (aVal < bVal) return sortOrder === "asc" ? -1 : 1;
      if (aVal > bVal) return sortOrder === "asc" ? 1 : -1;
      return 0;
    });
  }, [rawUsersList, sortField, sortOrder]);

  const handleSortToggle = (field: SortField) => {
    if (sortField === field) {
      setSortOrder(sortOrder === "asc" ? "desc" : "asc");
    } else {
      setSortField(field);
      setSortOrder("asc");
    }
  };

  return (
    <div className="p-6 max-w-[1600px] mx-auto space-y-6 animate-in fade-in duration-200">
      {/* Page Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-800 dark:text-slate-100 tracking-tight">
            Manage Users
          </h1>
        </div>

        <div className="flex items-center space-x-3">
          {/* Manage Templates Button */}
          <Button
            type="button"
            variant="outline"
            onClick={() => router.push("/allTemplates")}
            className="bg-white dark:bg-slate-900 border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 text-xs font-semibold px-4 py-2 h-9 rounded-md transition-all cursor-pointer shadow-2xs"
          >
            Manage Templates
          </Button>

          {/* Create User Button */}
          <PermissionGuard permission={{ feature: "user_management", action: "create" }}>
            <Button
              type="button"
              onClick={() => {
                // Trigger Create User action or navigate
              }}
              className="bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold px-4 py-2 h-9 rounded-md shadow-2xs transition-all cursor-pointer"
            >
              Create User
            </Button>
          </PermissionGuard>
        </div>
      </div>

      {/* Error State Alert Banner */}
      {isError && (
        <div className="p-4 bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800 rounded-lg flex items-center justify-between text-xs text-red-700 dark:text-red-300 animate-in fade-in">
          <div className="flex items-center space-x-2">
            <AlertCircle className="h-4 w-4 text-red-500 shrink-0" />
            <span>
              {(error as any)?.message || "Failed to load user list from backend server."}
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

      {/* Data Table Card Container */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg shadow-2xs flex flex-col justify-between min-h-[420px] relative">
        <div className="w-full overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-[#eef6ff] dark:bg-slate-800/80 border-b border-slate-200 dark:border-slate-700/80">
                {/* Column 1: Name */}
                <th className="py-3.5 px-4 text-xs font-semibold text-slate-700 dark:text-slate-200 whitespace-nowrap">
                  <button
                    type="button"
                    onClick={() => handleSortToggle("name")}
                    className="flex items-center space-x-1.5 cursor-pointer select-none hover:text-blue-600 transition-colors"
                  >
                    <span>Name</span>
                    <ChevronsUpDown className="h-3.5 w-3.5 text-slate-400 shrink-0" />
                  </button>
                </th>

                {/* Column 2: Phone Number */}
                <th className="py-3.5 px-4 text-xs font-semibold text-slate-700 dark:text-slate-200 whitespace-nowrap">
                  <button
                    type="button"
                    onClick={() => handleSortToggle("phone")}
                    className="flex items-center space-x-1.5 cursor-pointer select-none hover:text-blue-600 transition-colors"
                  >
                    <span>Phone Number</span>
                    <ChevronsUpDown className="h-3.5 w-3.5 text-slate-400 shrink-0" />
                  </button>
                </th>

                {/* Column 3: Email */}
                <th className="py-3.5 px-4 text-xs font-semibold text-slate-700 dark:text-slate-200 whitespace-nowrap">
                  <button
                    type="button"
                    onClick={() => handleSortToggle("email")}
                    className="flex items-center space-x-1.5 cursor-pointer select-none hover:text-blue-600 transition-colors"
                  >
                    <span>Email</span>
                    <ChevronsUpDown className="h-3.5 w-3.5 text-slate-400 shrink-0" />
                  </button>
                </th>

                {/* Column 4: Super Admin */}
                <th className="py-3.5 px-4 text-xs font-semibold text-slate-700 dark:text-slate-200 whitespace-nowrap">
                  Super Admin
                </th>

                {/* Column 5: Assigned Template */}
                <th className="py-3.5 px-4 text-xs font-semibold text-slate-700 dark:text-slate-200 whitespace-nowrap">
                  <button
                    type="button"
                    onClick={() => handleSortToggle("template")}
                    className="flex items-center space-x-1.5 cursor-pointer select-none hover:text-blue-600 transition-colors"
                  >
                    <span>Assigned Template</span>
                    <ChevronsUpDown className="h-3.5 w-3.5 text-slate-400 shrink-0" />
                  </button>
                </th>

                {/* Column 6: Action */}
                <th className="py-3.5 px-4 text-xs font-semibold text-slate-700 dark:text-slate-200 text-right pr-6 whitespace-nowrap">
                  Action
                </th>
              </tr>
            </thead>

            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {/* Skeleton Loading State */}
              {isLoading &&
                Array.from({ length: 5 }).map((_, idx) => (
                  <tr key={idx} className="animate-pulse">
                    <td className="py-4 px-4"><div className="h-4 bg-slate-200 dark:bg-slate-800 rounded w-36" /></td>
                    <td className="py-4 px-4"><div className="h-4 bg-slate-200 dark:bg-slate-800 rounded w-28" /></td>
                    <td className="py-4 px-4"><div className="h-4 bg-slate-200 dark:bg-slate-800 rounded w-44" /></td>
                    <td className="py-4 px-4"><div className="h-4 bg-slate-200 dark:bg-slate-800 rounded w-12" /></td>
                    <td className="py-4 px-4"><div className="h-4 bg-slate-200 dark:bg-slate-800 rounded w-24" /></td>
                    <td className="py-4 px-4 text-right pr-6"><div className="h-6 bg-slate-200 dark:bg-slate-800 rounded w-8 ml-auto" /></td>
                  </tr>
                ))}

              {/* Empty State */}
              {!isLoading && sortedUsers.length === 0 && (
                <tr>
                  <td colSpan={6} className="py-12 text-center">
                    <div className="flex flex-col items-center justify-center space-y-3">
                      <User className="h-10 w-10 text-slate-300 dark:text-slate-700" />
                      <p className="text-sm font-semibold text-slate-700 dark:text-slate-300">
                        No Users Found
                      </p>
                      <p className="text-xs text-slate-500 max-w-sm">
                        {debouncedSearch
                          ? `No user account matching "${debouncedSearch}" was found.`
                          : "No users exist in the system yet."}
                      </p>
                      {debouncedSearch && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setSearchQuery("")}
                          className="text-xs"
                        >
                          Clear Search
                        </Button>
                      )}
                    </div>
                  </td>
                </tr>
              )}

              {/* Data Rows */}
              {!isLoading &&
                sortedUsers.map((user) => {
                  const phoneText = user.mobile_country_code
                    ? `${user.mobile_country_code}${user.mobile_number}`
                    : user.mobile_number || "-";

                  return (
                    <tr
                      key={user.id}
                      className="hover:bg-slate-50/60 dark:hover:bg-slate-800/40 transition-colors"
                    >
                      {/* Name */}
                      <td className="py-4 px-4 text-xs font-normal text-slate-800 dark:text-slate-100">
                        {user.name}
                      </td>

                      {/* Phone Number */}
                      <td className="py-4 px-4 text-xs text-slate-700 dark:text-slate-300">
                        {phoneText}
                      </td>

                      {/* Email */}
                      <td className="py-4 px-4 text-xs text-slate-700 dark:text-slate-300">
                        {user.email || "-"}
                      </td>

                      {/* Super Admin */}
                      <td className="py-4 px-4 text-xs text-slate-700 dark:text-slate-300">
                        {user.is_super_admin ? "Yes" : "No"}
                      </td>

                      {/* Assigned Template */}
                      <td className="py-4 px-4 text-xs font-normal text-slate-700 dark:text-slate-300">
                        {user.template ? user.template.name : "-"}
                      </td>

                      {/* Action Menu */}
                      <td
                        ref={activeActionRowId === user.id ? actionMenuRef : null}
                        className="py-4 px-4 text-xs text-right pr-6 relative"
                      >
                        <button
                          onClick={() =>
                            setActiveActionRowId(
                              activeActionRowId === user.id ? null : user.id
                            )
                          }
                          className="p-1.5 border border-slate-200 dark:border-slate-700 rounded-md hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 dark:text-slate-400 transition-colors cursor-pointer inline-flex items-center justify-center bg-white dark:bg-slate-900"
                          title="Actions"
                        >
                          <MoreVertical className="h-4 w-4" />
                        </button>

                        {/* Wired 3-Dot Action Menu Dropdown */}
                        {activeActionRowId === user.id && (
                          <div className="absolute right-4 top-full mt-1 z-50 w-48 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-md shadow-xl py-1 text-left animate-in fade-in zoom-in-95 duration-150">
                            {/* View User */}
                            <button
                              onClick={() => setActiveActionRowId(null)}
                              className="w-full flex items-center space-x-2 px-3.5 py-2 text-xs text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors cursor-pointer"
                            >
                              <Eye className="h-3.5 w-3.5 text-slate-400" />
                              <span>View User</span>
                            </button>

                            {/* Edit User */}
                            <button
                              onClick={() => setActiveActionRowId(null)}
                              className="w-full flex items-center space-x-2 px-3.5 py-2 text-xs text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors cursor-pointer"
                            >
                              <Edit2 className="h-3.5 w-3.5 text-slate-400" />
                              <span>Edit User</span>
                            </button>

                            {/* Assign Template */}
                            <button
                              onClick={() => setActiveActionRowId(null)}
                              className="w-full flex items-center space-x-2 px-3.5 py-2 text-xs text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors cursor-pointer"
                            >
                              <ShieldCheck className="h-3.5 w-3.5 text-blue-500" />
                              <span>Assign Template</span>
                            </button>

                            {/* Remove Template */}
                            <button
                              onClick={() => setActiveActionRowId(null)}
                              className="w-full flex items-center space-x-2 px-3.5 py-2 text-xs text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors cursor-pointer"
                            >
                              <X className="h-3.5 w-3.5 text-amber-500" />
                              <span>Remove Template</span>
                            </button>

                            <div className="border-t border-slate-100 dark:border-slate-800 my-1" />

                            {/* Activate */}
                            <button
                              onClick={() => setActiveActionRowId(null)}
                              className="w-full flex items-center space-x-2 px-3.5 py-2 text-xs text-emerald-600 dark:text-emerald-400 hover:bg-emerald-50 dark:hover:bg-emerald-950/30 transition-colors cursor-pointer"
                            >
                              <UserCheck className="h-3.5 w-3.5" />
                              <span>Activate</span>
                            </button>

                            {/* Deactivate */}
                            <button
                              onClick={() => setActiveActionRowId(null)}
                              className="w-full flex items-center space-x-2 px-3.5 py-2 text-xs text-amber-600 dark:text-amber-400 hover:bg-amber-50 dark:hover:bg-amber-950/30 transition-colors cursor-pointer"
                            >
                              <UserX className="h-3.5 w-3.5" />
                              <span>Deactivate</span>
                            </button>

                            {/* Delete */}
                            <button
                              onClick={() => setActiveActionRowId(null)}
                              className="w-full flex items-center space-x-2 px-3.5 py-2 text-xs text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-950/30 transition-colors cursor-pointer"
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
          {/* Record Counter */}
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

          {/* Pagination Controls */}
          <div className="flex items-center space-x-3">
            {/* Page Size Selector */}
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

            {/* Previous & Next Buttons */}
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
    </div>
  );
}
