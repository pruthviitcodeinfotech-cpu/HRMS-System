"use client";

import React, { useState, useRef, useEffect } from "react";
import {
  Search,
  SlidersHorizontal,
  Plus,
  Edit2,
  Trash2,
  ChevronLeft,
  MoreVertical,
  X,
  Loader2,
  AlertTriangle,
  Upload,
  BookOpen,
  Smartphone,
  Laptop,
  Power,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { toast } from "sonner";
import { useRouter } from "next/navigation";
import {
  useBranches,
  useCreateBranch,
  useUpdateBranch,
  useDeleteBranch,
  useActivateBranch,
  useDeactivateBranch,
  useDebouncedValue,
} from "../hooks";
import { BranchSchema } from "../types";
import { isAxiosError } from "axios";
import { usePermissions } from "@/features/auth";

interface ApiErrorResponse {
  error?: {
    message?: string;
  };
}

const getErrorMessage = (err: unknown, defaultMessage: string): string => {
  if (isAxiosError(err)) {
    const data = err.response?.data as ApiErrorResponse | undefined;
    return data?.error?.message || defaultMessage;
  }
  if (err instanceof Error) {
    return err.message;
  }
  return defaultMessage;
};

// Helper to format ISO datetime to DD-MM-YYYY format
const formatDate = (isoString: string): string => {
  if (!isoString) return "-";
  try {
    const d = new Date(isoString);
    if (isNaN(d.getTime())) return "-";
    const day = String(d.getDate()).padStart(2, "0");
    const month = String(d.getMonth() + 1).padStart(2, "0");
    const year = d.getFullYear();
    return `${day}-${month}-${year}`;
  } catch {
    return "-";
  }
};

export function BranchList() {
  const router = useRouter();
  const { hasPermission } = usePermissions();
  const canCreate = hasPermission("branch", "create");
  const canEdit = hasPermission("branch", "edit");
  const canDelete = hasPermission("branch", "delete");

  const [searchQuery, setSearchQuery] = useState("");
  const debouncedSearch = useDebouncedValue(searchQuery, 400);

  const [sortField, setSortField] = useState<"branch_name" | "created_at">("branch_name");
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("asc");
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  // UI state for Drawer
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [drawerMode, setDrawerMode] = useState<"add" | "edit">("edit");
  const [selectedBranchId, setSelectedBranchId] = useState<string | null>(null);

  // Form Fields State
  const [formName, setFormName] = useState("");
  const [formGstin, setFormGstin] = useState("");
  const [formMobile, setFormMobile] = useState("");
  const [formAddress, setFormAddress] = useState("");
  const [formLandmark, setFormLandmark] = useState("");
  const [formPincode, setFormPincode] = useState("");
  const [formCity, setFormCity] = useState("Surat");
  const [formState, setFormState] = useState("Gujarat");
  const [formCountry, setFormCountry] = useState("India");
  const [formIndustryType, setFormIndustryType] = useState("");
  const [formLatitude, setFormLatitude] = useState<string>("");
  const [formLongitude, setFormLongitude] = useState<string>("");
  const [formAllowedRadius, setFormAllowedRadius] = useState<string>("");

  // Form Validation Errors
  const [errors, setErrors] = useState<Record<string, string>>({});

  // Loading states
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [branchToDelete, setBranchToDelete] = useState<string | null>(null);

  // Active action menu row id
  const [activeMenuId, setActiveMenuId] = useState<number | null>(null);

  // Logo upload state
  const [logoPreview, setLogoPreview] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Interactive help guide
  const [helpOption, setHelpOption] = useState<"phone" | "pc">("phone");

  const actionMenuRef = useRef<HTMLDivElement>(null);

  // React Query query and mutations
  const branchesQuery = useBranches({
    page: currentPage,
    page_size: pageSize,
    search: debouncedSearch.trim() || undefined,
    sort_by: sortField,
    sort_order: sortDirection,
  });

  const createMutation = useCreateBranch();
  const updateMutation = useUpdateBranch();
  const deleteMutation = useDeleteBranch();
  const activateMutation = useActivateBranch();
  const deactivateMutation = useDeactivateBranch();

  const isSaving = createMutation.isPending || updateMutation.isPending;
  const isDeleting = deleteMutation.isPending;
  const isTogglingActive = activateMutation.isPending || deactivateMutation.isPending;
  const isMutationPending = isSaving || isDeleting || isTogglingActive;

  const branches = branchesQuery.data?.items || [];
  const pagination = branchesQuery.data?.pagination;
  const totalRecords = pagination?.total_records || 0;
  const totalPages = pagination?.total_pages || 1;



  // Handle document click to close active dropdown menu
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (actionMenuRef.current && !actionMenuRef.current.contains(event.target as Node)) {
        setActiveMenuId(null);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Handle logo change
  const handleLogoChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      if (file.size > 20 * 1024 * 1024) {
        toast.error("File size exceeds 20 MB limit");
        return;
      }
      setLogoPreview(URL.createObjectURL(file));
      toast.success("Logo uploaded successfully");
    }
  };

  // Open drawer for edit
  const handleEditClick = (branch: BranchSchema) => {
    setDrawerMode("edit");
    setSelectedBranchId(String(branch.branch_id));
    setFormName(branch.branch_name);
    setFormGstin(branch.gstin || "");
    setFormMobile(branch.mobile_number || "");
    setFormAddress(branch.address || "");
    setFormLandmark(branch.landmark || "");
    setFormPincode(branch.pin_code || "");
    setFormCity(branch.city || "Surat");
    setFormState(branch.state || "Gujarat");
    setFormCountry(branch.country || "India");
    setFormIndustryType(branch.industry_type || "");
    setFormLatitude(branch.latitude !== null ? String(branch.latitude) : "");
    setFormLongitude(branch.longitude !== null ? String(branch.longitude) : "");
    setFormAllowedRadius(branch.allowed_radius_meters !== null ? String(branch.allowed_radius_meters) : "");
    setLogoPreview(branch.logo_url || null);
    setErrors({});
    setIsDrawerOpen(true);
    setActiveMenuId(null);
  };

  // Open drawer for create
  const handleAddClick = () => {
    setDrawerMode("add");
    setSelectedBranchId(null);
    setFormName("");
    setFormGstin("");
    setFormMobile("");
    setFormAddress("");
    setFormLandmark("");
    setFormPincode("");
    setFormCity("Surat");
    setFormState("Gujarat");
    setFormCountry("India");
    setFormIndustryType("");
    setFormLatitude("");
    setFormLongitude("");
    setFormAllowedRadius("");
    setLogoPreview(null);
    setErrors({});
    setIsDrawerOpen(true);
  };

  // Form Validation
  const validateForm = () => {
    const newErrors: Record<string, string> = {};
    if (!formName.trim()) {
      newErrors.name = "Location Name is required";
    }
    if (formLatitude !== "" && isNaN(Number(formLatitude))) {
      newErrors.latitude = "Latitude must be a valid number";
    }
    if (formLongitude !== "" && isNaN(Number(formLongitude))) {
      newErrors.longitude = "Longitude must be a valid number";
    }
    if (formAllowedRadius !== "") {
      const radiusNum = Number(formAllowedRadius);
      if (isNaN(radiusNum)) {
        newErrors.allowed_radius = "Allowed Radius must be a valid number";
      } else if (radiusNum > 200) {
        newErrors.allowed_radius = "Allowed Radius cannot exceed 200 meters";
      }
    }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // Form Submit
  const handleSaveDetails = (e: React.FormEvent) => {
    e.preventDefault();
    if (!validateForm()) {
      toast.error("Please resolve the validation errors");
      return;
    }

    const payload = {
      branch_name: formName.trim(),
      allowed_radius_meters: formAllowedRadius ? Number(formAllowedRadius) : null,
      gstin: formGstin.trim() || null,
      mobile_number: formMobile.trim() || null,
      address: formAddress.trim() || null,
      landmark: formLandmark.trim() || null,
      pin_code: formPincode.trim() || null,
      city: formCity || null,
      state: formState || null,
      country: formCountry || null,
      industry_type: formIndustryType || null,
      latitude: formLatitude ? Number(formLatitude) : null,
      longitude: formLongitude ? Number(formLongitude) : null,
      logo_url: logoPreview || null,
    };

    if (drawerMode === "add") {
      createMutation.mutate(payload, {
        onSuccess: () => {
          toast.success("Branch created successfully");
          setIsDrawerOpen(false);
        },
        onError: (err: unknown) => {
          const errMsg = getErrorMessage(err, "Failed to create branch");
          toast.error(errMsg);
        },
      });
    } else {
      if (!selectedBranchId) return;
      updateMutation.mutate(
        { id: Number(selectedBranchId), data: payload },
        {
          onSuccess: () => {
            toast.success("Branch modified successfully");
            setIsDrawerOpen(false);
          },
          onError: (err: unknown) => {
            const errMsg = getErrorMessage(err, "Failed to modify branch");
            toast.error(errMsg);
          },
        }
      );
    }
  };

  // Sorting handler
  const handleSort = (field: "branch_name" | "created_at") => {
    if (sortField === field) {
      setSortDirection(prev => (prev === "asc" ? "desc" : "asc"));
    } else {
      setSortField(field);
      setSortDirection("asc");
    }
  };

  // Delete Branch Logic
  const initiateDelete = (id: string) => {
    setBranchToDelete(id);
    setIsDeleteModalOpen(true);
    setActiveMenuId(null);
  };

  const confirmDelete = () => {
    if (!branchToDelete) return;
    deleteMutation.mutate(Number(branchToDelete), {
      onSuccess: () => {
        toast.success("Branch deleted successfully");
        setIsDeleteModalOpen(false);
        setBranchToDelete(null);
      },
      onError: (err: unknown) => {
        const errMsg = getErrorMessage(err, "Failed to delete branch");
        toast.error(errMsg);
      },
    });
  };

  // Toggle Active/Inactive status
  const handleToggleActive = (branch: BranchSchema) => {
    const mutation = branch.is_active ? deactivateMutation : activateMutation;
    mutation.mutate(branch.branch_id, {
      onSuccess: () => {
        toast.success(`Branch ${branch.is_active ? "deactivated" : "activated"} successfully`);
        setActiveMenuId(null);
      },
      onError: (err: unknown) => {
        const errMsg = getErrorMessage(
          err,
          `Failed to ${branch.is_active ? "deactivate" : "activate"} branch`
        );
        toast.error(errMsg);
      },
    });
  };

  return (
    <div className="space-y-4">
      {/* Upper header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <button
            onClick={() => router.back()}
            className="flex items-center gap-1 text-sm font-semibold text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
          >
            <ChevronLeft className="h-4 w-4" />
            <span>Manage Branch</span>
          </button>
        </div>
        <div className="text-right">
          <span className="text-xs text-muted-foreground bg-muted/30 border border-border px-3 py-1.5 rounded-lg inline-block">
            <span className="font-semibold text-foreground">Note: </span>
            To create a new branch contact{" "}
            <span className="text-primary font-medium hover:underline cursor-pointer">
              Payroll Support Team
            </span>
          </span>
        </div>
      </div>

      {/* Main card */}
      <div className="bg-card border border-border rounded-xl shadow-xs overflow-hidden">
        {/* Toolbar */}
        <div className="p-4 border-b border-border flex flex-col sm:flex-row items-center justify-between gap-4 bg-muted/10">
          <div className="relative w-full sm:max-w-xs">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              type="text"
              value={searchQuery}
              onChange={e => {
                setSearchQuery(e.target.value);
                setCurrentPage(1);
              }}
              placeholder="Search branches..."
              className="pl-9 h-9 text-xs w-full bg-card"
            />
          </div>

          <div className="flex items-center gap-2 w-full sm:w-auto justify-end">
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setSearchQuery("");
                setCurrentPage(1);
                toast.info("Filters cleared");
              }}
              className="gap-1.5 text-xs text-muted-foreground bg-card border-border hover:bg-muted/30"
            >
              <SlidersHorizontal className="h-3.5 w-3.5" />
              Reset Filters
            </Button>

            {/* Direct Add Button for full capability UI */}
            {canCreate && (
              <Button
                variant="primary"
                size="sm"
                onClick={handleAddClick}
                className="gap-1.5 text-xs shadow-xs"
              >
                <Plus className="h-3.5 w-3.5" />
                Add Branch
              </Button>
            )}
          </div>
        </div>

        {/* Table representation */}
        <div className="overflow-x-auto relative min-h-[250px]">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-muted/30 border-b border-border">
                <th
                  onClick={() => handleSort("branch_name")}
                  className="px-6 py-3.5 text-xs font-semibold text-foreground/85 cursor-pointer select-none hover:text-foreground transition-colors"
                >
                  <div className="flex items-center gap-1">
                    Location Name
                    <span className="text-[10px] text-muted-foreground">
                      {sortField === "branch_name" ? (sortDirection === "asc" ? " ⬆" : " ⬇") : " ↕"}
                    </span>
                  </div>
                </th>
                <th className="px-6 py-3.5 text-xs font-semibold text-foreground/85">Status</th>
                <th className="px-6 py-3.5 text-xs font-semibold text-foreground/85 text-center">
                  Allowed Radius (Meter)
                </th>
                <th className="px-6 py-3.5 text-xs font-semibold text-foreground/85 text-center">
                  Assigned Employees
                </th>
                <th
                  onClick={() => handleSort("created_at")}
                  className="px-6 py-3.5 text-xs font-semibold text-foreground/85 cursor-pointer select-none text-center hover:text-foreground transition-colors"
                >
                  <div className="flex items-center justify-center gap-1">
                    Created On
                    <span className="text-[10px] text-muted-foreground">
                      {sortField === "created_at" ? (sortDirection === "asc" ? " ⬆" : " ⬇") : " ↕"}
                    </span>
                  </div>
                </th>
                <th className="px-6 py-3.5 text-xs font-semibold text-foreground/85 text-right">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody>
              {branchesQuery.isLoading ? (
                Array.from({ length: pageSize }).map((_, idx) => (
                  <tr key={idx} className="border-b border-border/60">
                    <td className="px-6 py-4.5">
                      <div className="h-4 w-32 bg-muted/40 rounded animate-pulse" />
                    </td>
                    <td className="px-6 py-4.5">
                      <div className="h-5 w-16 bg-muted/40 rounded-full animate-pulse" />
                    </td>
                    <td className="px-6 py-4.5">
                      <div className="h-4 w-12 bg-muted/40 rounded mx-auto animate-pulse" />
                    </td>
                    <td className="px-6 py-4.5">
                      <div className="h-4 w-8 bg-muted/40 rounded mx-auto animate-pulse" />
                    </td>
                    <td className="px-6 py-4.5">
                      <div className="h-4 w-20 bg-muted/40 rounded mx-auto animate-pulse" />
                    </td>
                    <td className="px-6 py-4.5 flex justify-end">
                      <div className="h-8 w-8 bg-muted/40 rounded-md animate-pulse" />
                    </td>
                  </tr>
                ))
              ) : branchesQuery.isError ? (
                <tr>
                  <td colSpan={6} className="px-6 py-12 text-center">
                    <div className="flex flex-col items-center justify-center space-y-3">
                      <div className="h-12 w-12 rounded-full bg-destructive/10 flex items-center justify-center text-destructive">
                        <AlertTriangle className="h-6 w-6" />
                      </div>
                      <div>
                        <h4 className="text-sm font-semibold text-foreground">Failed to Load Branches</h4>
                        <p className="text-xs text-muted-foreground mt-0.5">
                          {branchesQuery.error instanceof Error
                            ? branchesQuery.error.message
                            : "An error occurred."}
                        </p>
                      </div>
                      <Button variant="outline" size="sm" onClick={() => branchesQuery.refetch()}>
                        Retry
                      </Button>
                    </div>
                  </td>
                </tr>
              ) : branches.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-6 py-12 text-center">
                    <div className="flex flex-col items-center justify-center space-y-3">
                      <div className="h-12 w-12 rounded-full bg-muted/50 flex items-center justify-center text-muted-foreground">
                        <AlertTriangle className="h-6 w-6" />
                      </div>
                      <div>
                        <h4 className="text-sm font-semibold text-foreground">No Branches Found</h4>
                        <p className="text-xs text-muted-foreground mt-0.5">
                          Try adjusting your search query.
                        </p>
                      </div>
                      <Button variant="outline" size="sm" onClick={() => setSearchQuery("")}>
                        Reset Filter
                      </Button>
                    </div>
                  </td>
                </tr>
              ) : (
                branches.map(branch => (
                  <tr
                    key={branch.branch_id}
                    className="border-b border-border/60 hover:bg-muted/5 transition-colors"
                  >
                    <td className="px-6 py-4 text-xs font-medium text-foreground">
                      {branch.branch_name}
                    </td>
                    <td className="px-6 py-4 text-xs">
                      <span
                        className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-bold border border-border/40 ${
                          branch.is_active
                            ? "bg-emerald-500/5 text-emerald-700 dark:text-emerald-400 border-emerald-550/10"
                            : "bg-yellow-500/5 text-yellow-750 dark:text-yellow-450 border-yellow-550/10"
                        }`}
                      >
                        <span
                          className={`h-1.5 w-1.5 rounded-full ${
                            branch.is_active ? "bg-emerald-500" : "bg-yellow-500"
                          }`}
                        />
                        {branch.is_active ? "Active" : "Inactive"}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-xs text-center text-muted-foreground">
                      {branch.allowed_radius_meters !== null ? `${branch.allowed_radius_meters} m` : "-"}
                    </td>
                    <td className="px-6 py-4 text-xs text-center text-foreground font-semibold">
                      {branch.employee_count}
                    </td>
                    <td className="px-6 py-4 text-xs text-center text-muted-foreground">
                      {formatDate(branch.created_at)}
                    </td>
                    <td className="px-6 py-4 text-right relative">
                      {(canEdit || canDelete) && (
                        <div className="flex justify-end items-center gap-1">
                          <button
                            onClick={() =>
                              setActiveMenuId(prev => (prev === branch.branch_id ? null : branch.branch_id))
                            }
                            className="p-1.5 hover:bg-muted rounded-md text-muted-foreground hover:text-foreground cursor-pointer focus:outline-none"
                          >
                            <MoreVertical className="h-4 w-4" />
                          </button>

                          {/* Actions drop menu */}
                          {activeMenuId === branch.branch_id && (
                            <div
                              ref={actionMenuRef}
                              className="absolute right-6 top-10 w-32 bg-card border border-border rounded-lg shadow-lg py-1.5 z-50 animate-in fade-in slide-in-from-top-1 duration-100"
                            >
                              {canEdit && (
                                <button
                                  onClick={() => handleEditClick(branch)}
                                  className="w-full text-left px-3 py-1.5 text-xs text-foreground hover:bg-muted flex items-center gap-2 cursor-pointer"
                                >
                                  <Edit2 className="h-3 w-3 text-muted-foreground" />
                                  Edit
                                </button>
                              )}
                              {canEdit && (
                                <button
                                  onClick={() => handleToggleActive(branch)}
                                  className="w-full text-left px-3 py-1.5 text-xs text-foreground hover:bg-muted flex items-center gap-2 cursor-pointer"
                                >
                                  <Power className="h-3 w-3 text-muted-foreground" />
                                  {branch.is_active ? "Deactivate" : "Activate"}
                                </button>
                              )}
                              {canDelete && (
                                <button
                                  disabled={isMutationPending}
                                  onClick={() => initiateDelete(String(branch.branch_id))}
                                  className="w-full text-left px-3 py-1.5 text-xs text-red-600 hover:bg-red-50 dark:hover:bg-red-950/20 flex items-center gap-2 cursor-pointer"
                                >
                                  <Trash2 className="h-3 w-3 text-red-500" />
                                  Delete
                                </button>
                              )}
                            </div>
                          )}
                        </div>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Footer pagination */}
        <div className="p-4 border-t border-border flex flex-col sm:flex-row items-center justify-between gap-4 bg-muted/5">
          <div className="text-xs text-muted-foreground">
            Showing{" "}
            <span className="font-semibold text-foreground">
              {totalRecords === 0 ? 0 : (currentPage - 1) * pageSize + 1}
            </span>{" "}
            to{" "}
            <span className="font-semibold text-foreground">
              {Math.min(currentPage * pageSize, totalRecords)}
            </span>{" "}
            of <span className="font-semibold text-foreground">{totalRecords}</span> Results
          </div>

          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5">
              <span className="text-xs text-muted-foreground">Page Size:</span>
              <select
                value={pageSize}
                onChange={e => {
                  setPageSize(Number(e.target.value));
                  setCurrentPage(1);
                }}
                className="bg-card border border-border rounded px-2 py-1 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
              >
                {[5, 10, 20, 50].map(size => (
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
                onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
                disabled={currentPage === 1 || totalPages <= 1}
                className="h-8 px-2.5 text-xs"
              >
                Previous
              </Button>
              <div className="h-8 px-3 flex items-center justify-center text-xs font-semibold bg-primary/10 text-primary border border-primary/20 rounded-md">
                {currentPage}
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
                disabled={currentPage === totalPages || totalPages <= 1}
                className="h-8 px-2.5 text-xs"
              >
                Next
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* Drawer: Modify/Add Branch */}
      {isDrawerOpen && (
        <div className="fixed inset-0 z-[100] flex justify-end">
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-black/60 backdrop-blur-xs transition-opacity"
            onClick={() => setIsDrawerOpen(false)}
          />

          {/* Drawer content wrapper */}
          <div className="relative w-full max-w-2xl bg-card border-l border-border h-full shadow-2xl flex flex-col justify-between z-10 animate-in slide-in-from-right duration-250">
            {/* Drawer Header */}
            <div className="p-5 border-b border-border flex items-center justify-between bg-muted/20">
              <h3 className="text-sm font-bold text-foreground">
                {drawerMode === "add" ? "Add Branch" : "Modify Branch"}
              </h3>
              <button
                onClick={() => setIsDrawerOpen(false)}
                className="p-1.5 hover:bg-muted rounded-md text-muted-foreground hover:text-foreground cursor-pointer focus:outline-none"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            {/* Drawer Body Form */}
            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              <form onSubmit={handleSaveDetails} className="space-y-6">
                {/* Branch Details Section */}
                <div className="space-y-4">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                    Branch Details
                  </h4>

                  {/* Logo Upload area */}
                  <div className="space-y-2">
                    <label className="text-xs font-semibold text-foreground/80">Branch Logo</label>
                    <div className="border-2 border-dashed border-border hover:border-primary/50 transition-colors rounded-xl p-4 bg-muted/5 flex items-center gap-4">
                      <div className="h-16 w-16 bg-muted border border-border rounded-lg flex items-center justify-center overflow-hidden shrink-0">
                        {logoPreview ? (
                          // eslint-disable-next-line @next/next/no-img-element
                          <img
                            src={logoPreview}
                            alt="Logo preview"
                            className="h-full w-full object-contain"
                          />
                        ) : (
                          <Upload className="h-6 w-6 text-muted-foreground" />
                        )}
                      </div>
                      <div className="space-y-1">
                        <div className="text-xs text-foreground/80 flex items-center gap-2">
                          <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            onClick={() => fileInputRef.current?.click()}
                            className="h-8 gap-1.5 text-xs text-foreground"
                          >
                            <Upload className="h-3.5 w-3.5" />
                            Logo
                          </Button>
                          <span className="text-muted-foreground text-[11px]">
                            Drag and drop your logo&apos;s PNG, JPG, or SVG files here (max 20 MB), or.{" "}
                            <span
                              onClick={() => fileInputRef.current?.click()}
                              className="text-primary hover:underline cursor-pointer font-medium"
                            >
                              Browse to replace
                            </span>
                          </span>
                        </div>
                        <input
                          ref={fileInputRef}
                          type="file"
                          accept="image/png, image/jpeg, image/svg+xml"
                          className="hidden"
                          onChange={handleLogoChange}
                        />
                      </div>
                    </div>
                  </div>

                  {/* Location Name */}
                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-foreground/80">
                      Location Name <span className="text-red-500">*</span>
                    </label>
                    <Input
                      value={formName}
                      onChange={e => {
                        setFormName(e.target.value);
                        if (e.target.value.trim() && errors.name) {
                          setErrors(prev => {
                            const copy = { ...prev };
                            delete copy.name;
                            return copy;
                          });
                        }
                      }}
                      placeholder="Itcode Infotech"
                      className={`h-10 text-xs w-full bg-card ${
                        errors.name ? "border-red-500 focus-visible:ring-red-500" : ""
                      }`}
                    />
                    {errors.name && <p className="text-[10px] font-semibold text-red-500">{errors.name}</p>}
                  </div>

                  {/* GSTIN & Mobile row */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-1.5">
                      <label className="text-xs font-semibold text-foreground/80">GSTIN</label>
                      <Input
                        value={formGstin}
                        onChange={e => setFormGstin(e.target.value)}
                        placeholder="24AAICI0352E1Z1"
                        className="h-10 text-xs w-full bg-card"
                      />
                    </div>
                    <div className="space-y-1.5">
                      <label className="text-xs font-semibold text-foreground/80">Mobile number</label>
                      <Input
                        value={formMobile}
                        onChange={e => setFormMobile(e.target.value)}
                        placeholder="Please Enter Mobile Number"
                        className="h-10 text-xs w-full bg-card"
                      />
                    </div>
                  </div>

                  {/* Address */}
                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-foreground/80">Address</label>
                    <textarea
                      value={formAddress}
                      onChange={e => setFormAddress(e.target.value)}
                      placeholder="Please Enter Address"
                      rows={3}
                      className="w-full rounded-md border border-input bg-card px-3 py-2 text-xs ring-offset-background placeholder:text-muted-foreground focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                    />
                  </div>

                  {/* Landmark */}
                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-foreground/80">Landmark</label>
                    <Input
                      value={formLandmark}
                      onChange={e => setFormLandmark(e.target.value)}
                      placeholder="Please Enter Landmark"
                      className="h-10 text-xs w-full bg-card"
                    />
                  </div>

                  {/* Pin Code, City, State, Country grid */}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="space-y-1.5">
                      <label className="text-xs font-semibold text-foreground/80">Pin Code</label>
                      <Input
                        value={formPincode}
                        onChange={e => setFormPincode(e.target.value)}
                        placeholder="394105"
                        className="h-10 text-xs w-full bg-card"
                      />
                    </div>
                    <div className="space-y-1.5">
                      <label className="text-xs font-semibold text-foreground/80">City</label>
                      <select
                        value={formCity}
                        onChange={e => setFormCity(e.target.value)}
                        className="w-full rounded-md border border-input bg-card h-10 px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-ring"
                      >
                        <option value="Surat">Surat</option>
                        <option value="Ahmedabad">Ahmedabad</option>
                        <option value="Mumbai">Mumbai</option>
                        <option value="Delhi">Delhi</option>
                        {!["Surat", "Ahmedabad", "Mumbai", "Delhi"].includes(formCity) && formCity && (
                          <option value={formCity}>{formCity}</option>
                        )}
                      </select>
                    </div>
                    <div className="space-y-1.5">
                      <label className="text-xs font-semibold text-foreground/80">State</label>
                      <select
                        value={formState}
                        onChange={e => setFormState(e.target.value)}
                        className="w-full rounded-md border border-input bg-card h-10 px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-ring"
                      >
                        <option value="Gujarat">Gujarat</option>
                        <option value="Maharashtra">Maharashtra</option>
                        <option value="Delhi">Delhi</option>
                        {!["Gujarat", "Maharashtra", "Delhi"].includes(formState) && formState && (
                          <option value={formState}>{formState}</option>
                        )}
                      </select>
                    </div>
                    <div className="space-y-1.5">
                      <label className="text-xs font-semibold text-foreground/80">Country</label>
                      <select
                        value={formCountry}
                        onChange={e => setFormCountry(e.target.value)}
                        className="w-full rounded-md border border-input bg-card h-10 px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-ring"
                      >
                        <option value="India">India</option>
                        <option value="United States">United States</option>
                        {!["India", "United States"].includes(formCountry) && formCountry && (
                          <option value={formCountry}>{formCountry}</option>
                        )}
                      </select>
                    </div>
                  </div>

                  {/* Industry Type */}
                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-foreground/80">Industry Type</label>
                    <select
                      value={formIndustryType}
                      onChange={e => setFormIndustryType(e.target.value)}
                      className="w-full rounded-md border border-input bg-card h-10 px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-ring"
                    >
                      <option value="">Please select industry type</option>
                      <option value="IT">Information Technology</option>
                      <option value="Retail">Retail</option>
                      <option value="Manufacturing">Manufacturing</option>
                    </select>
                  </div>
                </div>

                {/* Geo Fencing Details Section */}
                <div className="space-y-4 border-t border-border pt-4">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                    Geo Fencing Details
                  </h4>

                  {/* Latitude, Longitude, Radius row */}
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="space-y-1.5">
                      <label className="text-xs font-semibold text-foreground/80">
                        Latitude <span className="text-red-500">*</span>
                      </label>
                      <Input
                        value={formLatitude}
                        onChange={e => {
                          setFormLatitude(e.target.value);
                          if (errors.latitude) {
                            setErrors(prev => {
                              const copy = { ...prev };
                              delete copy.latitude;
                              return copy;
                            });
                          }
                        }}
                        placeholder="Please Enter Latitude"
                        className={`h-10 text-xs w-full bg-card ${
                          errors.latitude ? "border-red-500 focus-visible:ring-red-500" : ""
                        }`}
                      />
                      {errors.latitude && (
                        <p className="text-[10px] font-semibold text-red-500">{errors.latitude}</p>
                      )}
                    </div>

                    <div className="space-y-1.5">
                      <label className="text-xs font-semibold text-foreground/80">
                        Longitude <span className="text-red-500">*</span>
                      </label>
                      <Input
                        value={formLongitude}
                        onChange={e => {
                          setFormLongitude(e.target.value);
                          if (errors.longitude) {
                            setErrors(prev => {
                              const copy = { ...prev };
                              delete copy.longitude;
                              return copy;
                            });
                          }
                        }}
                        placeholder="Please Enter Longitude"
                        className={`h-10 text-xs w-full bg-card ${
                          errors.longitude ? "border-red-500 focus-visible:ring-red-500" : ""
                        }`}
                      />
                      {errors.longitude && (
                        <p className="text-[10px] font-semibold text-red-500">{errors.longitude}</p>
                      )}
                    </div>

                    <div className="space-y-1.5">
                      <label className="text-xs font-semibold text-foreground/80">
                        Allowed Radius (max 200 meter) <span className="text-red-500">*</span>
                      </label>
                      <Input
                        value={formAllowedRadius}
                        onChange={e => {
                          setFormAllowedRadius(e.target.value);
                          if (errors.allowed_radius) {
                            setErrors(prev => {
                              const copy = { ...prev };
                              delete copy.allowed_radius;
                              return copy;
                            });
                          }
                        }}
                        placeholder="Please Enter Allowed Radius"
                        className={`h-10 text-xs w-full bg-card ${
                          errors.allowed_radius ? "border-red-500 focus-visible:ring-red-500" : ""
                        }`}
                      />
                      {errors.allowed_radius && (
                        <p className="text-[10px] font-semibold text-red-500">{errors.allowed_radius}</p>
                      )}
                    </div>
                  </div>

                  <p className="text-[10px] text-muted-foreground">
                    This will be used to limit the attendance area from mobile app
                  </p>

                  {/* Help Card Callout */}
                  <div className="bg-primary/5 border border-primary/20 rounded-xl p-4 space-y-3">
                    <div className="flex items-center gap-2 text-xs font-semibold text-primary">
                      <BookOpen className="h-4 w-4" />
                      <span>How to Find Latitude and Longitude of a location</span>
                    </div>

                    <div className="space-y-2">
                      <span className="text-[10px] text-muted-foreground uppercase font-bold tracking-wider">
                        Choose any of Options below
                      </span>

                      <div className="flex gap-2">
                        <button
                          type="button"
                          onClick={() => setHelpOption("phone")}
                          className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg border transition-all cursor-pointer ${
                            helpOption === "phone"
                              ? "bg-primary text-primary-foreground border-primary"
                              : "bg-card text-foreground border-border hover:bg-muted/40"
                          }`}
                        >
                          <Smartphone className="h-3.5 w-3.5" />
                          Android/iPhone
                        </button>
                        <button
                          type="button"
                          onClick={() => setHelpOption("pc")}
                          className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg border transition-all cursor-pointer ${
                            helpOption === "pc"
                              ? "bg-primary text-primary-foreground border-primary"
                              : "bg-card text-foreground border-border hover:bg-muted/40"
                          }`}
                        >
                          <Laptop className="h-3.5 w-3.5" />
                          Laptop/PC
                        </button>
                      </div>
                    </div>

                    {/* Step Content */}
                    <div className="text-[11px] text-foreground/80 leading-relaxed space-y-1">
                      {helpOption === "phone" ? (
                        <>
                          <p>1. Open Google Maps on your phone.</p>
                          <p>
                            2. Touch and hold an area of the map that isn&apos;t labeled to drop a red
                            pin.
                          </p>
                          <p>
                            3. Look in the search box at the top to find the latitude and longitude
                            coordinates.
                          </p>
                        </>
                      ) : (
                        <>
                          <p>1. Open Google Maps on your computer.</p>
                          <p>2. Right-click the exact place or area on the map.</p>
                          <p>
                            3. A pop-up window will show the latitude and longitude at the top of the
                            menu. Click on them to copy automatically.
                          </p>
                        </>
                      )}
                    </div>
                  </div>
                </div>
              </form>
            </div>

            {/* Drawer Footer */}
            <div className="p-4 bg-muted/10 border-t border-border flex items-center justify-end gap-3">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setIsDrawerOpen(false)}
                className="px-5 text-xs h-9"
              >
                Cancel
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={handleSaveDetails}
                className="px-5 text-xs h-9"
                disabled={isSaving}
              >
                {isSaving ? (
                  <>
                    <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
                    Saving...
                  </>
                ) : (
                  "Save Changes"
                )}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {isDeleteModalOpen && (
        <div className="fixed inset-0 z-[110] flex items-center justify-center p-4">
          <div
            className="absolute inset-0 bg-black/60 backdrop-blur-xs"
            onClick={() => setIsDeleteModalOpen(false)}
          />
          <div className="relative w-full max-w-md bg-card border border-border rounded-xl shadow-2xl p-5 z-10 space-y-4 animate-in zoom-in-95 duration-150">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-red-100 dark:bg-red-950/30 text-red-600 rounded-full">
                <AlertTriangle className="h-6 w-6" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-foreground">Delete Branch</h3>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Are you sure you want to delete this branch? This action cannot be undone.
                </p>
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 pt-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setIsDeleteModalOpen(false)}
                className="text-xs h-8 px-4"
              >
                Cancel
              </Button>
              <Button
                variant="destructive"
                size="sm"
                onClick={confirmDelete}
                className="text-xs h-8 px-4 bg-red-600 hover:bg-red-700 text-white"
                disabled={isDeleting}
              >
                {isDeleting ? "Deleting..." : "Delete Branch"}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
