"use client";

import { useState, useRef, useEffect, useMemo } from "react";
import { useRouter } from "next/navigation";
import {
  Search,
  RotateCw,
  MoreVertical,
  ChevronsUpDown,
  Eye,
  Edit2,
  ShieldCheck,
  UserCheck,
  UserX,
  Trash2,
  AlertTriangle,
  ChevronDown,
  User,
  X,
  Plus,
  RefreshCw,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

import { useAuth } from "@/features/auth/hooks";

// React Query Hooks & API Services
import {
  useUsers,
  useCreateUser,
  useUpdateUser,
  useDeleteUser,
  useActivateUser,
  useDeactivateUser,
  useAssignUserRole,
  useRemoveUserRole,
} from "../hooks/use-users";
import { useDepartmentOptions, useDesignationOptions } from "@/features/employees/hooks";
import { useRightsTemplates } from "../hooks/use-rights-templates";

// Dialog Components
import { UserFormModal, UserFormData } from "./user-form-modal";
import { ViewUserModal } from "./view-user-modal";
import {
  DeleteUserDialog,
  ToggleUserStatusDialog,
  AssignTemplateDialog,
  RemoveTemplateDialog,
} from "./user-action-dialogs";
import { UserSummary } from "../services/user-service";

type SortField = "name" | "phone" | "email" | "template";
type SortOrder = "asc" | "desc";

const STATUS_OPTIONS = ["All", "Active", "Inactive"];

export function ManageUsersPage() {
  const router = useRouter();
  const { user: currentUser } = useAuth();

  // Search & Filter State
  const [searchQuery, setSearchQuery] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");

  const [selectedDept, setSelectedDept] = useState("All Departments");
  const [selectedDesig, setSelectedDesig] = useState("All Designations");
  const [selectedTemplate, setSelectedTemplate] = useState("All Templates");
  const [selectedStatus, setSelectedStatus] = useState("All");

  // Pagination State
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  // Sorting State
  const [sortField, setSortField] = useState<SortField>("name");
  const [sortOrder, setSortOrder] = useState<SortOrder>("asc");

  // Kebab Action Menu Row State
  const [activeActionRowId, setActiveActionRowId] = useState<number | null>(null);
  const actionMenuRef = useRef<HTMLTableCellElement>(null);

  // Modal & Dialog Visibility States
  const [isFormModalOpen, setIsFormModalOpen] = useState(false);
  const [userToEdit, setUserToEdit] = useState<UserFormData | null>(null);

  const [isViewModalOpen, setIsViewModalOpen] = useState(false);
  const [viewUserId, setViewUserId] = useState<number | null>(null);

  const [isDeleteOpen, setIsDeleteOpen] = useState(false);
  const [isToggleStatusOpen, setIsToggleStatusOpen] = useState(false);
  const [toggleStatusAction, setToggleStatusAction] = useState<"activate" | "deactivate">("activate");
  const [isAssignTemplateOpen, setIsAssignTemplateOpen] = useState(false);
  const [isRemoveTemplateOpen, setIsRemoveTemplateOpen] = useState(false);

  const [targetUser, setTargetUser] = useState<UserSummary | null>(null);

  // Debounce search query
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedSearch(searchQuery);
      setCurrentPage(1);
    }, 400);
    return () => clearTimeout(handler);
  }, [searchQuery]);

  // Close kebab dropdown menu on click outside
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

  // Compute status filter param
  const isActiveParam =
    selectedStatus === "Active" ? true : selectedStatus === "Inactive" ? false : undefined;

  // React Query Hook - Live Backend API GET /api/v1/users
  const {
    data: paginatedData,
    isLoading,
    isError,
    error,
    refetch,
    isFetching,
  } = useUsers({
    page: currentPage,
    page_size: pageSize,
    search: debouncedSearch || undefined,
    is_active: isActiveParam,
  });

  // Live Master Data Lookups
  const { data: departmentOptions } = useDepartmentOptions();
  const { data: designationOptions } = useDesignationOptions();
  const { data: templateData } = useRightsTemplates({});

  const rawUsersList = paginatedData?.items || [];
  const totalRecords = paginatedData?.pagination?.total_records ?? paginatedData?.total_records ?? rawUsersList.length;
  const totalPages = paginatedData?.pagination?.total_pages ?? paginatedData?.total_pages ?? (Math.ceil(totalRecords / pageSize) || 1);

  // React Query Mutations for User Actions
  const createUserMutation = useCreateUser();
  const updateUserMutation = useUpdateUser();
  const deleteUserMutation = useDeleteUser();
  const activateUserMutation = useActivateUser();
  const deactivateUserMutation = useDeactivateUser();
  const assignRoleMutation = useAssignUserRole();
  const removeRoleMutation = useRemoveUserRole();

  // Client-side Sorting & Filtering by department/designation/template
  const filteredAndSortedUsers = useMemo(() => {
    let result = [...rawUsersList];

    // Filter by Template if selected
    if (selectedTemplate !== "All Templates") {
      result = result.filter((u) => u.template?.name === selectedTemplate);
    }

    // Sort by field
    return result.sort((a, b) => {
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
  }, [rawUsersList, selectedTemplate, sortField, sortOrder]);

  const handleSortToggle = (field: SortField) => {
    if (sortField === field) {
      setSortOrder(sortOrder === "asc" ? "desc" : "asc");
    } else {
      setSortField(field);
      setSortOrder("asc");
    }
  };

  const handleResetFilters = () => {
    setSearchQuery("");
    setSelectedDept("All Departments");
    setSelectedDesig("All Designations");
    setSelectedTemplate("All Templates");
    setSelectedStatus("All");
  };

  // Handlers for Opening Modals
  const handleOpenCreateModal = () => {
    setUserToEdit(null);
    setIsFormModalOpen(true);
  };

  const handleOpenEditModal = (user: UserSummary) => {
    setUserToEdit({
      id: user.id,
      name: user.name,
      email: user.email,
      mobile_number: user.mobile_number,
      is_super_admin: user.is_super_admin,
      status: user.is_active ? "Active" : "Inactive",
      template_id: user.template?.id || null,
      employee_id: user.employee_id || null,
    });
    setIsFormModalOpen(true);
    setActiveActionRowId(null);
  };

  const handleOpenViewModal = (user: UserSummary) => {
    setViewUserId(user.id);
    setIsViewModalOpen(true);
    setActiveActionRowId(null);
  };

  const handleOpenDeleteDialog = (user: UserSummary) => {
    setTargetUser(user);
    setIsDeleteOpen(true);
    setActiveActionRowId(null);
  };

  const handleOpenToggleStatusDialog = (user: UserSummary, action: "activate" | "deactivate") => {
    setTargetUser(user);
    setToggleStatusAction(action);
    setIsToggleStatusOpen(true);
    setActiveActionRowId(null);
  };

  const handleOpenAssignTemplateDialog = (user: UserSummary) => {
    setTargetUser(user);
    setIsAssignTemplateOpen(true);
    setActiveActionRowId(null);
  };

  const handleOpenRemoveTemplateDialog = (user: UserSummary) => {
    setTargetUser(user);
    setIsRemoveTemplateOpen(true);
    setActiveActionRowId(null);
  };

  // Save Create or Edit User
  const handleSaveUserForm = async (data: UserFormData) => {
    if (data.id) {
      // Edit User (PATCH /api/v1/users/{id})
      await updateUserMutation.mutateAsync({
        id: data.id,
        data: {
          name: data.name,
          email: data.email,
          mobile_country_code: data.mobile_country_code || "+91",
          mobile_number: data.mobile_number,
          is_super_admin: data.is_super_admin,
        },
      });

      // Update / Assign Rights Template if selected
      if (data.template_id) {
        await assignRoleMutation.mutateAsync({
          userId: data.id,
          templateId: data.template_id,
        });
      } else {
        try {
          await removeRoleMutation.mutateAsync(data.id);
        } catch {
          // Ignore if no role was assigned previously
        }
      }
    } else {
      // Create User (POST /api/v1/users)
      const res = await createUserMutation.mutateAsync({
        name: data.name,
        email: data.email,
        mobile_country_code: data.mobile_country_code || "+91",
        mobile_number: data.mobile_number,
        password: data.password || "Password@123",
        is_super_admin: data.is_super_admin,
        employee_id: data.employee_id || undefined,
      });

      // If a Rights Template was selected in the form, assign it immediately
      if (data.template_id && res?.data?.id) {
        await assignRoleMutation.mutateAsync({
          userId: res.data.id,
          templateId: data.template_id,
        });
      }
    }
    setIsFormModalOpen(false);
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
          <Button
            type="button"
            onClick={handleOpenCreateModal}
            className="bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold px-4 py-2 h-9 rounded-md shadow-2xs transition-all cursor-pointer"
          >
            Create User
          </Button>
        </div>
      </div>

      {/* Toolbar: Search Input + Filter Dropdowns + Action Buttons */}
      <div className="bg-white dark:bg-slate-900 p-4 border border-slate-200 dark:border-slate-800 rounded-lg shadow-2xs space-y-3">
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 items-center">
          {/* Search Bar Input */}
          <div className="relative lg:col-span-2">
            <Search className="h-4 w-4 text-slate-400 absolute left-3 top-2.5 pointer-events-none" />
            <Input
              type="text"
              placeholder="Search by Name, Phone Number or Email"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              aria-label="Search by Name, Phone Number or Email"
              className="pl-9 pr-8 text-xs bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-700 h-9 rounded-md focus-visible:ring-2 focus-visible:ring-blue-500"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery("")}
                aria-label="Clear search input"
                className="absolute right-2.5 top-2.5 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 cursor-pointer"
              >
                <X className="h-4 w-4" />
              </button>
            )}
          </div>

          {/* Department Filter */}
          <div>
            <div className="relative">
              <select
                value={selectedDept}
                onChange={(e) => setSelectedDept(e.target.value)}
                aria-label="Department Filter"
                className="w-full appearance-none bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-md px-3 py-2 pr-8 text-xs font-medium text-slate-700 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer"
              >
                <option value="All Departments">All Departments</option>
                {departmentOptions?.map((dept: any) => (
                  <option key={dept.id || dept.dept_name} value={dept.dept_name}>
                    {dept.dept_name}
                  </option>
                ))}
              </select>
              <ChevronDown className="h-3.5 w-3.5 text-slate-500 absolute right-2.5 top-2.5 pointer-events-none" />
            </div>
          </div>

          {/* Designation Filter */}
          <div>
            <div className="relative">
              <select
                value={selectedDesig}
                onChange={(e) => setSelectedDesig(e.target.value)}
                aria-label="Designation Filter"
                className="w-full appearance-none bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-md px-3 py-2 pr-8 text-xs font-medium text-slate-700 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer"
              >
                <option value="All Designations">All Designations</option>
                {designationOptions?.map((desig: any) => (
                  <option key={desig.id || desig.designation_name} value={desig.designation_name}>
                    {desig.designation_name}
                  </option>
                ))}
              </select>
              <ChevronDown className="h-3.5 w-3.5 text-slate-500 absolute right-2.5 top-2.5 pointer-events-none" />
            </div>
          </div>

          {/* Rights Template Filter */}
          <div>
            <div className="relative">
              <select
                value={selectedTemplate}
                onChange={(e) => setSelectedTemplate(e.target.value)}
                aria-label="Rights Template Filter"
                className="w-full appearance-none bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-md px-3 py-2 pr-8 text-xs font-medium text-slate-700 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer"
              >
                <option value="All Templates">All Templates</option>
                {templateData?.items?.map((tmpl) => (
                  <option key={tmpl.id} value={tmpl.name}>
                    {tmpl.name}
                  </option>
                ))}
              </select>
              <ChevronDown className="h-3.5 w-3.5 text-slate-500 absolute right-2.5 top-2.5 pointer-events-none" />
            </div>
          </div>

          {/* Status Filter */}
          <div>
            <div className="relative">
              <select
                value={selectedStatus}
                onChange={(e) => setSelectedStatus(e.target.value)}
                aria-label="Status Filter"
                className="w-full appearance-none bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-md px-3 py-2 pr-8 text-xs font-medium text-slate-700 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer"
              >
                {STATUS_OPTIONS.map((opt) => (
                  <option key={opt} value={opt}>
                    {opt}
                  </option>
                ))}
              </select>
              <ChevronDown className="h-3.5 w-3.5 text-slate-500 absolute right-2.5 top-2.5 pointer-events-none" />
            </div>
          </div>
        </div>

        {/* Action Buttons Row */}
        <div className="flex items-center justify-between pt-2 border-t border-slate-100 dark:border-slate-800">
          <div className="flex items-center space-x-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => refetch()}
              disabled={isFetching}
              aria-label="Refresh Data"
              className="bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 text-xs font-semibold px-3 py-1.5 h-8 rounded-md hover:bg-slate-50 dark:hover:bg-slate-800 cursor-pointer"
            >
              <RotateCw className={`h-3.5 w-3.5 mr-1.5 text-slate-500 ${isFetching ? "animate-spin" : ""}`} />
              <span>Refresh</span>
            </Button>

            <Button
              type="button"
              variant="outline"
              onClick={handleResetFilters}
              aria-label="Reset Filters"
              className="bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 text-xs font-semibold px-3 py-1.5 h-8 rounded-md hover:bg-slate-50 dark:hover:bg-slate-800 cursor-pointer"
            >
              <RefreshCw className="h-3.5 w-3.5 mr-1.5 text-slate-500" />
              <span>Reset Filters</span>
            </Button>
          </div>
        </div>
      </div>

      {/* ERROR STATE VIEW */}
      {isError && (
        <div className="p-6 bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900 rounded-lg flex flex-col items-center justify-center text-center space-y-3 animate-in fade-in py-12">
          <div className="p-3 bg-red-100 dark:bg-red-900/50 rounded-full text-red-600 dark:text-red-300">
            <AlertTriangle className="h-8 w-8" />
          </div>
          <div>
            <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">
              Unable to load users.
            </h3>
            <p className="text-xs text-slate-600 dark:text-slate-400 mt-1 max-w-sm">
              {(error as any)?.message || "Something went wrong while loading data."}
            </p>
          </div>
          <Button
            type="button"
            onClick={() => refetch()}
            className="bg-red-600 hover:bg-red-700 text-white text-xs font-semibold px-4 py-2 h-8 rounded-md shadow-2xs cursor-pointer"
          >
            Retry
          </Button>
        </div>
      )}

      {/* SKELETON LOADING STATE VIEW */}
      {isLoading && (
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg shadow-2xs overflow-hidden">
          <div className="w-full overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-[#eef6ff] dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700">
                  <th className="py-3.5 px-4"><div className="h-4 bg-slate-200 dark:bg-slate-700 rounded w-20 animate-pulse" /></th>
                  <th className="py-3.5 px-4"><div className="h-4 bg-slate-200 dark:bg-slate-700 rounded w-28 animate-pulse" /></th>
                  <th className="py-3.5 px-4"><div className="h-4 bg-slate-200 dark:bg-slate-700 rounded w-32 animate-pulse" /></th>
                  <th className="py-3.5 px-4"><div className="h-4 bg-slate-200 dark:bg-slate-700 rounded w-24 animate-pulse" /></th>
                  <th className="py-3.5 px-4"><div className="h-4 bg-slate-200 dark:bg-slate-700 rounded w-32 animate-pulse" /></th>
                  <th className="py-3.5 px-4 text-right pr-6"><div className="h-4 bg-slate-200 dark:bg-slate-700 rounded w-12 ml-auto animate-pulse" /></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {Array.from({ length: 6 }).map((_, idx) => (
                  <tr key={idx} className="animate-pulse">
                    <td className="py-4 px-4"><div className="h-4 bg-slate-200 dark:bg-slate-800 rounded w-36" /></td>
                    <td className="py-4 px-4"><div className="h-4 bg-slate-200 dark:bg-slate-800 rounded w-28" /></td>
                    <td className="py-4 px-4"><div className="h-4 bg-slate-200 dark:bg-slate-800 rounded w-48" /></td>
                    <td className="py-4 px-4"><div className="h-4 bg-slate-200 dark:bg-slate-800 rounded w-12" /></td>
                    <td className="py-4 px-4"><div className="h-4 bg-slate-200 dark:bg-slate-800 rounded w-24" /></td>
                    <td className="py-4 px-4 text-right pr-6"><div className="h-6 bg-slate-200 dark:bg-slate-800 rounded w-8 ml-auto" /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* EMPTY STATE VIEW */}
      {!isLoading && !isError && filteredAndSortedUsers.length === 0 && (
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg shadow-2xs p-12 text-center flex flex-col items-center justify-center space-y-4">
          <div className="p-4 bg-blue-50 dark:bg-blue-950/40 rounded-full text-blue-600 dark:text-blue-400">
            <User className="h-10 w-10" />
          </div>
          <div className="space-y-1">
            <h3 className="text-base font-bold text-slate-800 dark:text-slate-100">
              No Users Found
            </h3>
            <p className="text-xs text-slate-500 max-w-sm">
              {debouncedSearch
                ? `No user account matching "${debouncedSearch}" was found.`
                : "No users match your current search or filters."}
            </p>
          </div>
          <div className="flex items-center space-x-3 pt-2">
            <Button
              type="button"
              onClick={handleResetFilters}
              variant="outline"
              className="text-xs h-8 px-3 border-slate-200 dark:border-slate-700"
            >
              Clear Search
            </Button>
            <Button
              type="button"
              onClick={handleOpenCreateModal}
              className="bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold h-8 px-4 cursor-pointer"
            >
              <Plus className="h-3.5 w-3.5 mr-1" />
              Create User
            </Button>
          </div>
        </div>
      )}

      {/* NORMAL LIVE TABLE VIEW */}
      {!isLoading && !isError && filteredAndSortedUsers.length > 0 && (
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg shadow-2xs flex flex-col justify-between min-h-[450px] relative">
          <div className="w-full overflow-x-auto pb-48">
            <table className="w-full text-left border-collapse">
              {/* Sticky Header */}
              <thead className="sticky top-0 z-10 bg-[#eef6ff] dark:bg-slate-800 shadow-2xs">
                <tr className="border-b border-slate-200 dark:border-slate-700/80">
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

              {/* Dynamic Table Body */}
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800 pb-48">
                {filteredAndSortedUsers.map((user, idx) => {
                  const phoneText = user.mobile_country_code
                    ? `${user.mobile_country_code}${user.mobile_number}`
                    : user.mobile_number || "-";

                  const isNearBottom =
                    idx > 1 && idx >= filteredAndSortedUsers.length - 2;

                  return (
                    <tr
                      key={user.id}
                      className={`hover:bg-slate-50/80 dark:hover:bg-slate-800/50 transition-colors ${
                        activeActionRowId === user.id ? "relative z-30" : ""
                      }`}
                    >
                      {/* Name */}
                      <td className="py-4 px-4 text-xs font-normal text-slate-800 dark:text-slate-100">
                        {user.name}
                      </td>

                      {/* Phone Number */}
                      <td className="py-4 px-4 text-xs text-slate-700 dark:text-slate-300 font-normal">
                        {phoneText}
                      </td>

                      {/* Email */}
                      <td className="py-4 px-4 text-xs text-slate-700 dark:text-slate-300 font-normal">
                        {user.email || "-"}
                      </td>

                      {/* Super Admin */}
                      <td className="py-4 px-4 text-xs text-slate-700 dark:text-slate-300 font-normal">
                        {user.is_super_admin ? "Yes" : "No"}
                      </td>

                      {/* Assigned Template */}
                      <td className="py-4 px-4 text-xs font-normal text-slate-700 dark:text-slate-300">
                        {user.template ? user.template.name : "-"}
                      </td>

                      {/* Action Dropdown Menu */}
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
                          aria-label={`Actions for ${user.name}`}
                          className="p-1.5 border border-slate-200 dark:border-slate-700 rounded-md hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 dark:text-slate-400 transition-colors cursor-pointer inline-flex items-center justify-center bg-white dark:bg-slate-900 focus-visible:ring-2 focus-visible:ring-blue-500"
                          title="Actions"
                        >
                          <MoreVertical className="h-4 w-4" />
                        </button>

                        {/* Action Dropdown Items */}
                        {activeActionRowId === user.id && (
                          <div
                            className={`absolute right-4 z-50 w-48 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700/90 rounded-lg shadow-2xl py-1 text-left animate-in fade-in zoom-in-95 duration-150 ${
                              isNearBottom ? "bottom-full mb-1" : "top-full mt-1"
                            }`}
                          >
                            {/* 1. View User */}
                            <button
                              onClick={() => handleOpenViewModal(user)}
                              className="w-full flex items-center space-x-2 px-3.5 py-2 text-xs text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors cursor-pointer"
                            >
                              <Eye className="h-3.5 w-3.5 text-slate-400" />
                              <span>View User</span>
                            </button>

                            {/* Super Admin Protection Check */}
                            {user.is_super_admin && !currentUser?.isSuperAdmin ? (
                              <div className="px-3.5 py-2 text-[11px] text-amber-600 dark:text-amber-400 font-medium bg-amber-50 dark:bg-amber-950/30 border-t border-b border-amber-100 dark:border-amber-900/40 my-1">
                                Super Admin Account (Protected)
                              </div>
                            ) : (
                              <>
                                {/* 2. Edit User */}
                                <button
                                  onClick={() => handleOpenEditModal(user)}
                                  className="w-full flex items-center space-x-2 px-3.5 py-2 text-xs text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors cursor-pointer"
                                >
                                  <Edit2 className="h-3.5 w-3.5 text-slate-400" />
                                  <span>Edit User</span>
                                </button>

                                {/* 3. Assign Template */}
                                <button
                                  onClick={() => handleOpenAssignTemplateDialog(user)}
                                  className="w-full flex items-center space-x-2 px-3.5 py-2 text-xs text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors cursor-pointer"
                                >
                                  <ShieldCheck className="h-3.5 w-3.5 text-blue-500" />
                                  <span>Assign Template</span>
                                </button>

                                {/* 4. Remove Template */}
                                <button
                                  onClick={() => handleOpenRemoveTemplateDialog(user)}
                                  className="w-full flex items-center space-x-2 px-3.5 py-2 text-xs text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors cursor-pointer"
                                >
                                  <X className="h-3.5 w-3.5 text-amber-500" />
                                  <span>Remove Template</span>
                                </button>

                                <div className="border-t border-slate-100 dark:border-slate-800 my-1" />

                                {/* 5. Activate / Deactivate */}
                                {!user.is_active ? (
                                  <button
                                    onClick={() => handleOpenToggleStatusDialog(user, "activate")}
                                    className="w-full flex items-center space-x-2 px-3.5 py-2 text-xs text-emerald-600 dark:text-emerald-400 hover:bg-emerald-50 dark:hover:bg-emerald-950/30 transition-colors cursor-pointer"
                                  >
                                    <UserCheck className="h-3.5 w-3.5" />
                                    <span>Activate</span>
                                  </button>
                                ) : (
                                  <button
                                    onClick={() => handleOpenToggleStatusDialog(user, "deactivate")}
                                    className="w-full flex items-center space-x-2 px-3.5 py-2 text-xs text-amber-600 dark:text-amber-400 hover:bg-amber-50 dark:hover:bg-amber-950/30 transition-colors cursor-pointer"
                                  >
                                    <UserX className="h-3.5 w-3.5" />
                                    <span>Deactivate</span>
                                  </button>
                                )}

                                {/* 6. Delete */}
                                <button
                                  onClick={() => handleOpenDeleteDialog(user)}
                                  className="w-full flex items-center space-x-2 px-3.5 py-2 text-xs text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-950/30 transition-colors cursor-pointer"
                                >
                                  <Trash2 className="h-3.5 w-3.5" />
                                  <span>Delete User</span>
                                </button>
                              </>
                            )}
                          </div>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Bottom Pagination UI */}
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
                  aria-label="Page Size Selector"
                  className="appearance-none bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-md px-3 py-1 pr-8 text-xs font-medium text-slate-700 dark:text-slate-200 cursor-pointer focus:outline-none focus:ring-2 focus:ring-blue-500 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
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
                  aria-label="Previous Page"
                  className="px-3 py-1 border border-slate-200 dark:border-slate-800 rounded-md text-slate-700 dark:text-slate-300 disabled:text-slate-300 dark:disabled:text-slate-600 bg-white dark:bg-slate-900 text-xs font-medium cursor-pointer disabled:cursor-not-allowed"
                >
                  Previous
                </button>

                <button
                  aria-label={`Page ${currentPage}`}
                  className="px-2.5 py-1 bg-blue-600 text-white rounded-md text-xs font-bold shadow-2xs"
                >
                  {currentPage}
                </button>

                <button
                  disabled={currentPage >= totalPages || isLoading}
                  onClick={() => setCurrentPage((p) => Math.min(p + 1, totalPages))}
                  aria-label="Next Page"
                  className="px-3 py-1 border border-slate-200 dark:border-slate-800 rounded-md text-slate-700 dark:text-slate-300 disabled:text-slate-300 dark:disabled:text-slate-600 bg-white dark:bg-slate-900 text-xs font-medium cursor-pointer disabled:cursor-not-allowed"
                >
                  Next
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* LIVE MODALS & DIALOGS WIRED TO BACKEND API MUTATIONS */}

      {/* 1 & 2. Create / Edit User Modal */}
      <UserFormModal
        isOpen={isFormModalOpen}
        onClose={() => setIsFormModalOpen(false)}
        userToEdit={userToEdit}
        isLoading={createUserMutation.isPending || updateUserMutation.isPending}
        onSave={handleSaveUserForm}
      />

      {/* 3. View User Details Modal */}
      <ViewUserModal
        isOpen={isViewModalOpen}
        onClose={() => setIsViewModalOpen(false)}
        userId={viewUserId}
      />

      {/* 4. Delete Confirmation Dialog */}
      <DeleteUserDialog
        isOpen={isDeleteOpen}
        onClose={() => setIsDeleteOpen(false)}
        userName={targetUser?.name}
        isLoading={deleteUserMutation.isPending}
        onConfirm={async () => {
          if (targetUser) {
            await deleteUserMutation.mutateAsync(targetUser.id);
            setIsDeleteOpen(false);
          }
        }}
      />

      {/* 5. Activate / Deactivate Dialog */}
      <ToggleUserStatusDialog
        isOpen={isToggleStatusOpen}
        onClose={() => setIsToggleStatusOpen(false)}
        userName={targetUser?.name}
        actionType={toggleStatusAction}
        isLoading={activateUserMutation.isPending || deactivateUserMutation.isPending}
        onConfirm={async () => {
          if (targetUser) {
            if (toggleStatusAction === "activate") {
              await activateUserMutation.mutateAsync(targetUser.id);
            } else {
              await deactivateUserMutation.mutateAsync(targetUser.id);
            }
            setIsToggleStatusOpen(false);
          }
        }}
      />

      {/* 6. Assign Rights Template Dialog */}
      <AssignTemplateDialog
        isOpen={isAssignTemplateOpen}
        onClose={() => setIsAssignTemplateOpen(false)}
        userName={targetUser?.name}
        currentTemplate={targetUser?.template?.name || "-"}
        isLoading={assignRoleMutation.isPending}
        onAssignTemplate={async (templateId) => {
          if (targetUser) {
            await assignRoleMutation.mutateAsync({
              userId: targetUser.id,
              templateId: templateId,
            });
            setIsAssignTemplateOpen(false);
          }
        }}
      />

      {/* 7. Remove Rights Template Dialog */}
      <RemoveTemplateDialog
        isOpen={isRemoveTemplateOpen}
        onClose={() => setIsRemoveTemplateOpen(false)}
        userName={targetUser?.name}
        isLoading={removeRoleMutation.isPending}
        onConfirm={async () => {
          if (targetUser) {
            await removeRoleMutation.mutateAsync(targetUser.id);
            setIsRemoveTemplateOpen(false);
          }
        }}
      />
    </div>
  );
}
