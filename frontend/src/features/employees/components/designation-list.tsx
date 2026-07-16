"use client";

import React, { useState, useMemo, useEffect, useRef } from "react";
import {
  Search,
  SlidersHorizontal,
  Edit2,
  Trash2,
  MoreVertical,
  X,
  Loader2,
  AlertTriangle,
  ArrowUpDown,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { toast } from "sonner";
import { EmptyState } from "@/components/feedback/empty-state";
import {
  useDesignations,
  useCreateDesignation,
  useUpdateDesignation,
  useDeleteDesignation,
  useDesignationOptions,
  useDebouncedValue,
} from "../hooks";

interface Designation {
  id: number;
  name: string;
  employeeCount: number;
  statusCounts: {
    Active: number;
    Inactive: number;
    Left: number;
    Terminated: number;
  };
}

const EMPLOYEE_STATUS_OPTIONS = ["Active", "Inactive", "Left", "Terminated"];

export function DesignationList() {
  // Search & Filtering Popups State
  const [activeActionRowId, setActiveActionRowId] = useState<number | null>(null);
  const [isNameFilterOpen, setIsNameFilterOpen] = useState(false);
  const [isCountFilterOpen, setIsCountFilterOpen] = useState(false);

  // Filter values
  const [searchQuery, setSearchQuery] = useState("");
  const debouncedSearch = useDebouncedValue(searchQuery, 400);

  const [nameSearchQuery, setNameSearchQuery] = useState("");
  const [selectedNames, setSelectedNames] = useState<string[]>([]);
  const [tempSelectedNames, setTempSelectedNames] = useState<string[]>([]);

  const [countSearchQuery, setCountSearchQuery] = useState("");
  const [selectedStatuses, setSelectedStatuses] = useState<string[]>(EMPLOYEE_STATUS_OPTIONS);
  const [tempSelectedStatuses, setTempSelectedStatuses] = useState<string[]>(EMPLOYEE_STATUS_OPTIONS);

  // Sorting State
  const [sortOrder, setSortOrder] = useState<"asc" | "desc" | null>(null);

  // Pagination State
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  // Drawer (Add / Edit details modal)
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [drawerMode, setDrawerMode] = useState<"add" | "edit">("add");
  const [drawerId, setDrawerId] = useState<number | null>(null);
  const [drawerName, setDrawerName] = useState("");
  const [drawerNameError, setDrawerNameError] = useState("");

  // Delete Confirmation Modal
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [deleteTargetId, setDeleteTargetId] = useState<number | null>(null);

  // Refs for closing popups on click outside
  const actionDropdownRef = useRef<HTMLDivElement>(null);
  const nameFilterDropdownRef = useRef<HTMLDivElement>(null);
  const countFilterDropdownRef = useRef<HTMLDivElement>(null);

  // React Query: Get paginated/filtered/sorted designations
  const designationsQuery = useDesignations({
    page: currentPage,
    page_size: pageSize,
    search: debouncedSearch.trim() || undefined,
    sort_by: sortOrder ? "designation_name" : undefined,
    sort_order: sortOrder || undefined,
  });

  // React Query: Fetch designation name options for the name filter dropdown
  const { data: designationOptions = [] } = useDesignationOptions();

  // React Query: Mutations
  const createMutation = useCreateDesignation();
  const updateMutation = useUpdateDesignation();
  const deleteMutation = useDeleteDesignation();

  const isSaving = createMutation.isPending || updateMutation.isPending;
  const isMutationPending = isSaving || deleteMutation.isPending;

  // Map backend DesignationSchema to local Designation type
  const designations = useMemo<Designation[]>(() => {
    const items = designationsQuery.data?.items ?? [];
    return items.map((item) => ({
      id: item.designation_id,
      name: item.designation_name,
      employeeCount: item.employee_count,
      statusCounts: {
        Active: item.employee_count,
        Inactive: 0,
        Left: 0,
        Terminated: 0,
      },
    }));
  }, [designationsQuery.data?.items]);

  const paginationMeta = designationsQuery.data?.pagination;
  const totalRecords = paginationMeta?.total_records ?? 0;
  const totalPages = paginationMeta?.total_pages ?? 1;

  // Handle click outside to close dropdowns/popovers
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        actionDropdownRef.current &&
        !actionDropdownRef.current.contains(event.target as Node)
      ) {
        setActiveActionRowId(null);
      }
      if (
        nameFilterDropdownRef.current &&
        !nameFilterDropdownRef.current.contains(event.target as Node)
      ) {
        setIsNameFilterOpen(false);
      }
      if (
        countFilterDropdownRef.current &&
        !countFilterDropdownRef.current.contains(event.target as Node)
      ) {
        setIsCountFilterOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Initialize temp variables when opening filters
  const handleOpenNameFilter = () => {
    setTempSelectedNames(selectedNames);
    setIsNameFilterOpen(true);
    setIsCountFilterOpen(false);
  };

  const handleOpenCountFilter = () => {
    setTempSelectedStatuses(selectedStatuses);
    setIsCountFilterOpen(true);
    setIsNameFilterOpen(false);
  };

  // Get all unique names available in designations list
  const allDesignationNames = useMemo(() => {
    if (designationOptions.length > 0) {
      return Array.from(new Set(designationOptions.map((d) => d.designation_name))).sort();
    }
    return Array.from(new Set(designations.map((d) => d.name))).sort();
  }, [designationOptions, designations]);

  // Filter and process designations
  const processedDesignations = useMemo(() => {
    let result = designations.map((d) => {
      // Calculate dynamic count based on checked statuses
      const activeCount = selectedStatuses.includes("Active") ? d.statusCounts.Active : 0;
      const inactiveCount = selectedStatuses.includes("Inactive") ? d.statusCounts.Inactive : 0;
      const leftCount = selectedStatuses.includes("Left") ? d.statusCounts.Left : 0;
      const termCount = selectedStatuses.includes("Terminated") ? d.statusCounts.Terminated : 0;
      
      return {
        ...d,
        calculatedCount: activeCount + inactiveCount + leftCount + termCount,
      };
    });

    // Filter by selected designation names if any are selected (local filtering for UI parity)
    if (selectedNames.length > 0) {
      result = result.filter((d) => selectedNames.includes(d.name));
    }

    return result;
  }, [designations, selectedNames, selectedStatuses]);

  // Toggle sort order
  const handleSortName = () => {
    if (sortOrder === null) setSortOrder("asc");
    else if (sortOrder === "asc") setSortOrder("desc");
    else setSortOrder(null);
  };

  // Actions
  const handleAddClick = () => {
    setDrawerMode("add");
    setDrawerId(null);
    setDrawerName("");
    setDrawerNameError("");
    setIsDrawerOpen(true);
  };

  const handleEditClick = (d: Designation) => {
    setDrawerMode("edit");
    setDrawerId(d.id);
    setDrawerName(d.name);
    setDrawerNameError("");
    setIsDrawerOpen(true);
    setActiveActionRowId(null);
  };

  const handleDeleteClick = (id: number) => {
    setDeleteTargetId(id);
    setIsDeleteModalOpen(true);
    setActiveActionRowId(null);
  };

  const confirmDelete = () => {
    if (deleteTargetId === null) return;
    deleteMutation.mutate(deleteTargetId, {
      onSuccess: () => {
        toast.success("Designation deleted successfully");
        setIsDeleteModalOpen(false);
        setDeleteTargetId(null);
      },
      onError: (err: unknown) => {
        const errMsg = err instanceof Error ? err.message : "Failed to delete designation";
        toast.error(errMsg);
        setIsDeleteModalOpen(false);
        setDeleteTargetId(null);
      },
    });
  };

  const handleSaveDetails = (e: React.FormEvent) => {
    e.preventDefault();
    if (!drawerName.trim()) {
      setDrawerNameError("Please Enter Name");
      return;
    }

    if (drawerMode === "add") {
      createMutation.mutate(
        { designation_name: drawerName.trim() },
        {
          onSuccess: () => {
            toast.success("Designation created successfully");
            setIsDrawerOpen(false);
            setCurrentPage(1);
          },
          onError: (err: unknown) => {
            const errMsg = err instanceof Error ? err.message : "Failed to create designation";
            toast.error(errMsg);
          },
        }
      );
    } else {
      if (drawerId === null) return;
      updateMutation.mutate(
        { id: drawerId, data: { designation_name: drawerName.trim() } },
        {
          onSuccess: () => {
            toast.success("Designation updated successfully");
            setIsDrawerOpen(false);
          },
          onError: (err: unknown) => {
            const errMsg = err instanceof Error ? err.message : "Failed to update designation";
            toast.error(errMsg);
          },
        }
      );
    }
  };

  const resetFilters = () => {
    setSearchQuery("");
    setSelectedNames([]);
    setTempSelectedNames([]);
    setSelectedStatuses(EMPLOYEE_STATUS_OPTIONS);
    setTempSelectedStatuses(EMPLOYEE_STATUS_OPTIONS);
    setNameSearchQuery("");
    setCountSearchQuery("");
    setSortOrder(null);
    setCurrentPage(1);
  };

  // Checkbox toggle for Designation Name
  const handleToggleNameCheckbox = (name: string) => {
    setTempSelectedNames((prev) =>
      prev.includes(name) ? prev.filter((n) => n !== name) : [...prev, name]
    );
  };

  const handleSelectAllNames = (checked: boolean) => {
    if (checked) {
      setTempSelectedNames(allDesignationNames);
    } else {
      setTempSelectedNames([]);
    }
  };

  // Checkbox toggle for Employee Count Status
  const handleToggleStatusCheckbox = (status: string) => {
    setTempSelectedStatuses((prev) =>
      prev.includes(status) ? prev.filter((s) => s !== status) : [...prev, status]
    );
  };

  const handleSelectAllStatuses = (checked: boolean) => {
    if (checked) {
      setTempSelectedStatuses(EMPLOYEE_STATUS_OPTIONS);
    } else {
      setTempSelectedStatuses([]);
    }
  };

  // Apply filters
  const applyNameFilter = () => {
    setSelectedNames(tempSelectedNames);
    setCurrentPage(1);
    setIsNameFilterOpen(false);
  };

  const applyCountFilter = () => {
    setSelectedStatuses(tempSelectedStatuses);
    setCurrentPage(1);
    setIsCountFilterOpen(false);
  };

  // Clear filters
  const clearNameFilter = () => {
    setTempSelectedNames([]);
    setSelectedNames([]);
    setCurrentPage(1);
    setIsNameFilterOpen(false);
  };

  const clearCountFilter = () => {
    setTempSelectedStatuses(EMPLOYEE_STATUS_OPTIONS);
    setSelectedStatuses(EMPLOYEE_STATUS_OPTIONS);
    setCurrentPage(1);
    setIsCountFilterOpen(false);
  };

  // Reload data from query
  const handleReload = () => {
    designationsQuery.refetch();
  };

  return (
    <div className="space-y-4">
      {/* Top Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5 text-lg font-bold text-foreground">
          <span>Designations</span>
          <span className="text-[#0b5cff] font-bold">({totalRecords})</span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleReload}
            className="text-[10px] text-muted-foreground hover:text-foreground px-2 py-1.5 border border-border rounded-md transition-colors cursor-pointer mr-1"
          >
            Reload Data
          </button>
          <Button variant="primary" size="sm" onClick={handleAddClick} className="shadow-xs bg-[#0b5cff] hover:bg-[#094ed9] text-white font-medium text-xs rounded-md h-9 px-4">
            Add New
          </Button>
        </div>
      </div>

      {/* Main Table Card */}
      <div className="bg-card border border-border rounded-xl shadow-xs overflow-hidden">
        
        {/* Toolbar with Search Input */}
        <div className="p-4 border-b border-border flex items-center justify-between gap-4 bg-muted/10">
          <div className="relative w-72">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground/60" />
            <Input
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setCurrentPage(1);
              }}
              placeholder="Search Designation Name..."
              className="pl-9 h-9 text-xs"
            />
          </div>
        </div>

        {/* Table representation */}
        <div className="overflow-x-auto relative min-h-[300px]">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-[#f0f5fa] dark:bg-slate-800/60 border-b border-border">
                {/* Designation Name Column */}
                <th className="px-6 py-4 text-xs font-semibold text-slate-700 dark:text-slate-200 relative select-none">
                  <div className="flex items-center gap-2">
                    <div
                      className="flex items-center gap-1 cursor-pointer hover:text-foreground transition-colors"
                      onClick={handleSortName}
                    >
                      <span>Designation Name</span>
                      <ArrowUpDown className={`h-3 w-3 text-slate-400 ${sortOrder ? "text-[#0b5cff]" : ""}`} />
                    </div>

                    <span className="text-muted-foreground/30 font-normal">|</span>

                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        if (isNameFilterOpen) {
                          setIsNameFilterOpen(false);
                        } else {
                          handleOpenNameFilter();
                        }
                      }}
                      className={`p-1 hover:bg-muted rounded-md transition-colors cursor-pointer ${
                        selectedNames.length > 0 ? "text-[#0b5cff]" : "text-slate-400"
                      }`}
                    >
                      <SlidersHorizontal className="h-3 w-3" />
                    </button>
                  </div>

                  {/* Designation Name Filter Dropdown */}
                  {isNameFilterOpen && (
                    <div
                      ref={nameFilterDropdownRef}
                      className="absolute left-6 top-10 w-56 bg-card border border-border rounded-lg shadow-xl p-3 z-50 space-y-3 animate-in fade-in duration-100 text-left font-normal"
                    >
                      <div className="relative">
                        <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
                        <input
                           type="text"
                          value={nameSearchQuery}
                          onChange={(e) => setNameSearchQuery(e.target.value)}
                          placeholder="Search"
                          className="w-full pl-8 pr-2 py-1.5 text-xs bg-muted/30 border border-border rounded focus:outline-none focus:ring-1 focus:ring-[#0b5cff]"
                        />
                      </div>
                      <div className="space-y-2 max-h-40 overflow-y-auto">
                        <label className="flex items-center gap-2 text-xs font-medium text-foreground cursor-pointer select-none">
                          <input
                            type="checkbox"
                            checked={
                              tempSelectedNames.length === allDesignationNames.length &&
                              allDesignationNames.length > 0
                            }
                            onChange={(e) => handleSelectAllNames(e.target.checked)}
                            className="rounded border-input text-[#0b5cff] focus:ring-[#0b5cff] h-3.5 w-3.5"
                          />
                          Select All
                        </label>
                        <hr className="border-border" />
                        {allDesignationNames
                          .filter((name) =>
                            name.toLowerCase().includes(nameSearchQuery.toLowerCase())
                          )
                          .map((name) => (
                            <label
                              key={name}
                              className="flex items-center gap-2 text-xs text-muted-foreground hover:text-foreground cursor-pointer select-none"
                            >
                              <input
                                type="checkbox"
                                checked={tempSelectedNames.includes(name)}
                                onChange={() => handleToggleNameCheckbox(name)}
                                className="rounded border-input text-[#0b5cff] focus:ring-[#0b5cff] h-3.5 w-3.5"
                              />
                              {name}
                            </label>
                          ))}
                      </div>
                      <div className="flex items-center justify-between pt-1">
                        <button
                          onClick={clearNameFilter}
                          className="text-[10px] font-semibold text-muted-foreground hover:text-foreground px-2 py-1 border border-border rounded cursor-pointer bg-transparent"
                        >
                          Clear
                        </button>
                        <button
                          onClick={applyNameFilter}
                          className="text-[10px] font-semibold bg-[#0b5cff] text-white hover:bg-[#094ed9] px-3 py-1 rounded cursor-pointer border-none"
                        >
                          Apply
                        </button>
                      </div>
                    </div>
                  )}
                </th>

                {/* Employee Count Column */}
                <th className="px-6 py-4 text-xs font-semibold text-slate-700 dark:text-slate-200 relative select-none w-[25%]">
                  <div className="flex items-center gap-1.5">
                    <span>Employee Count</span>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        if (isCountFilterOpen) {
                          setIsCountFilterOpen(false);
                        } else {
                          handleOpenCountFilter();
                        }
                      }}
                      className={`p-1 hover:bg-muted rounded-md transition-colors cursor-pointer ${
                        selectedStatuses.length !== EMPLOYEE_STATUS_OPTIONS.length
                          ? "text-[#0b5cff]"
                          : "text-slate-400"
                      }`}
                    >
                      <SlidersHorizontal className="h-3 w-3" />
                    </button>
                  </div>

                  {/* Employee Count Status Filter Dropdown */}
                  {isCountFilterOpen && (
                    <div
                      ref={countFilterDropdownRef}
                      className="absolute left-6 top-10 w-56 bg-card border border-border rounded-lg shadow-xl p-3 z-50 space-y-3 animate-in fade-in duration-100 text-left font-normal"
                    >
                      <div className="relative">
                        <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
                        <input
                          type="text"
                          value={countSearchQuery}
                          onChange={(e) => setCountSearchQuery(e.target.value)}
                          placeholder="Search"
                          className="w-full pl-8 pr-2 py-1.5 text-xs bg-muted/30 border border-border rounded focus:outline-none focus:ring-1 focus:ring-[#0b5cff]"
                        />
                      </div>
                      <div className="space-y-2">
                        <label className="flex items-center gap-2 text-xs font-medium text-foreground cursor-pointer select-none">
                          <input
                            type="checkbox"
                            checked={tempSelectedStatuses.length === EMPLOYEE_STATUS_OPTIONS.length}
                            onChange={(e) => handleSelectAllStatuses(e.target.checked)}
                            className="rounded border-input text-[#0b5cff] focus:ring-[#0b5cff] h-3.5 w-3.5"
                          />
                          Select All
                        </label>
                        <hr className="border-border" />
                        {EMPLOYEE_STATUS_OPTIONS.filter((s) =>
                          s.toLowerCase().includes(countSearchQuery.toLowerCase())
                        ).map((status) => (
                          <label
                            key={status}
                            className="flex items-center gap-2 text-xs text-muted-foreground hover:text-foreground cursor-pointer select-none"
                          >
                            <input
                              type="checkbox"
                              checked={tempSelectedStatuses.includes(status)}
                              onChange={() => handleToggleStatusCheckbox(status)}
                              className="rounded border-input text-[#0b5cff] focus:ring-[#0b5cff] h-3.5 w-3.5"
                            />
                            {/* Color indicator for employee status */}
                            <span
                              className={`h-1.5 w-1.5 rounded-full ${
                                status === "Active"
                                  ? "bg-emerald-500"
                                  : status === "Inactive"
                                  ? "bg-yellow-500"
                                  : status === "Left"
                                  ? "bg-gray-400"
                                  : "bg-red-500"
                              }`}
                            />
                            {status}
                          </label>
                        ))}
                      </div>
                      <div className="flex items-center justify-between pt-1">
                        <button
                          onClick={clearCountFilter}
                          className="text-[10px] font-semibold text-muted-foreground hover:text-foreground px-2 py-1 border border-border rounded cursor-pointer bg-transparent"
                        >
                          Clear
                        </button>
                        <button
                          onClick={applyCountFilter}
                          className="text-[10px] font-semibold bg-[#0b5cff] text-white hover:bg-[#094ed9] px-3 py-1 rounded cursor-pointer border-none"
                        >
                          Apply
                        </button>
                      </div>
                    </div>
                  )}
                </th>

                {/* Action Column */}
                <th className="px-6 py-4 text-xs font-semibold text-slate-700 dark:text-slate-200 text-center w-[15%]">
                  Action
                </th>
              </tr>
            </thead>
            <tbody>
              {designationsQuery.isLoading ? (
                // Skeletons
                Array.from({ length: pageSize }).map((_, idx) => (
                  <tr key={idx} className="border-b border-border/60">
                    <td className="px-6 py-4.5">
                      <div className="h-4.5 w-48 bg-muted/40 rounded animate-pulse" />
                    </td>
                    <td className="px-6 py-4.5">
                      <div className="h-4.5 w-10 bg-muted/40 rounded animate-pulse" />
                    </td>
                    <td className="px-6 py-4.5 flex justify-center">
                      <div className="h-8 w-8 bg-muted/40 rounded-md animate-pulse" />
                    </td>
                  </tr>
                ))
              ) : designationsQuery.isError ? (
                // Error State
                <tr>
                  <td colSpan={3} className="px-6 py-12 text-center">
                    <div className="flex flex-col items-center justify-center space-y-3">
                      <div className="h-12 w-12 rounded-full bg-destructive/10 flex items-center justify-center text-destructive">
                        <AlertTriangle className="h-6 w-6" />
                      </div>
                      <div>
                        <h4 className="text-sm font-semibold text-foreground">Failed to Load Designations</h4>
                        <p className="text-xs text-muted-foreground mt-0.5">
                          {designationsQuery.error instanceof Error ? designationsQuery.error.message : "An error occurred."}
                        </p>
                      </div>
                      <Button variant="outline" size="sm" onClick={() => designationsQuery.refetch()}>
                        Retry
                      </Button>
                    </div>
                  </td>
                </tr>
              ) : processedDesignations.length === 0 ? (
                // Empty State
                <tr>
                  <td colSpan={3} className="px-6 py-12 text-center">
                    <EmptyState
                      title="No Designations Found"
                      description="Try adjusting your search query or filters."
                      action={
                        <Button variant="outline" size="sm" onClick={resetFilters}>
                          Reset Filters
                        </Button>
                      }
                    />
                  </td>
                </tr>
              ) : (
                // Table Rows
                processedDesignations.map((d) => (
                  <tr
                    key={d.id}
                    className="border-b border-border/60 hover:bg-[#f8fafc]/50 dark:hover:bg-slate-800/10 transition-colors"
                  >
                    <td className="px-6 py-5 text-sm font-medium text-slate-800 dark:text-slate-200">
                      {d.name}
                    </td>
                    <td className="px-6 py-5 text-sm">
                      <span className="underline decoration-1 underline-offset-2 hover:text-[#094ed9] text-[#0b5cff] dark:text-blue-400 font-semibold cursor-pointer">
                        {d.calculatedCount}
                      </span>
                    </td>
                    <td className="px-6 py-5 text-center relative">
                      <button
                        onClick={() =>
                          setActiveActionRowId(activeActionRowId === d.id ? null : d.id)
                        }
                        className="p-1.5 border border-slate-200 dark:border-slate-700 rounded-md bg-white dark:bg-slate-800 transition-colors inline-flex items-center justify-center cursor-pointer text-slate-400 hover:text-slate-600 dark:hover:text-slate-300"
                      >
                        <MoreVertical className="h-4 w-4" />
                      </button>

                      {/* Action Dropdown Menu */}
                      {activeActionRowId === d.id && (
                        <div
                          ref={actionDropdownRef}
                          className="absolute right-12 top-12 w-28 bg-card border border-border rounded-lg shadow-xl py-1.5 z-40 animate-in fade-in duration-100 text-left"
                        >
                          <button
                            onClick={() => handleEditClick(d)}
                            className="w-full flex items-center gap-2 px-3 py-1.5 text-xs font-semibold text-slate-700 dark:text-slate-300 hover:bg-muted/50 transition-colors cursor-pointer text-left border-none bg-transparent"
                          >
                            <Edit2 className="h-3.5 w-3.5 text-slate-500" />
                            Edit
                          </button>
                          <button
                            disabled={isMutationPending}
                            onClick={() => handleDeleteClick(d.id)}
                            className="w-full flex items-center gap-2 px-3 py-1.5 text-xs font-semibold text-red-500 hover:bg-red-50 dark:hover:bg-red-950/20 disabled:opacity-50 transition-colors cursor-pointer text-left border-none bg-transparent"
                          >
                            <Trash2 className="h-3.5 w-3.5 text-red-500" />
                            Delete
                          </button>
                        </div>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Footer Pagination */}
        <div className="p-4 border-t border-border flex flex-col sm:flex-row items-center justify-between gap-4 bg-muted/5 text-xs">
          <div className="text-slate-500">
            Showing <span className="font-semibold text-slate-700 dark:text-slate-300">{totalRecords > 0 ? (currentPage - 1) * pageSize + 1 : 0}</span> to{" "}
            <span className="font-semibold text-slate-700 dark:text-slate-300">
              {Math.min(currentPage * pageSize, totalRecords)}
            </span>{" "}
            of <span className="font-semibold text-slate-700 dark:text-slate-300">{totalRecords}</span> Results
          </div>

          <div className="flex items-center gap-3">
            {/* Page Size Dropdown */}
            <div className="flex items-center gap-1.5">
              <select
                value={pageSize}
                onChange={(e) => {
                  setPageSize(Number(e.target.value));
                  setCurrentPage(1);
                }}
                className="bg-card border border-border rounded-md px-2.5 py-1 text-xs text-foreground cursor-pointer focus:outline-none focus:ring-1 focus:ring-[#0b5cff] h-8"
              >
                {[5, 10, 20, 50].map((size) => (
                  <option key={size} value={size}>
                    {size} / Page
                  </option>
                ))}
              </select>
            </div>

            {/* Prev / Next & Numbers Pagination */}
            <div className="flex items-center gap-1">
              <button
                disabled={currentPage === 1 || designationsQuery.isLoading}
                onClick={() => setCurrentPage((p) => p - 1)}
                className="h-8 px-3 border border-border rounded-md hover:bg-muted disabled:opacity-50 disabled:hover:bg-transparent cursor-pointer disabled:cursor-not-allowed transition-colors text-slate-600 dark:text-slate-300 font-semibold bg-white dark:bg-slate-800"
              >
                Previous
              </button>

              {Array.from({ length: totalPages }).map((_, idx) => (
                <button
                  key={idx}
                  onClick={() => setCurrentPage(idx + 1)}
                  className={`h-8 w-8 flex items-center justify-center rounded-md border text-xs font-semibold cursor-pointer transition-colors ${
                    currentPage === idx + 1
                      ? "bg-[#0b5cff] text-white border-[#0b5cff]"
                      : "border-border hover:bg-muted text-slate-600 dark:text-slate-400 bg-white dark:bg-slate-800"
                  }`}
                >
                  {idx + 1}
                </button>
              ))}

              <button
                disabled={currentPage === totalPages || designationsQuery.isLoading}
                onClick={() => setCurrentPage((p) => p + 1)}
                className="h-8 px-3 border border-border rounded-md hover:bg-muted disabled:opacity-50 disabled:hover:bg-transparent cursor-pointer disabled:cursor-not-allowed transition-colors text-slate-600 dark:text-slate-300 font-semibold bg-white dark:bg-slate-800"
              >
                Next
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Drawer / Sidebar details form */}
      {isDrawerOpen && (
        <div className="fixed inset-0 z-[100] flex justify-end">
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-black/50 backdrop-blur-xs transition-opacity"
            onClick={() => setIsDrawerOpen(false)}
          />

          {/* Drawer content */}
          <div className="relative w-full max-w-md bg-card border-l border-border h-full shadow-2xl flex flex-col justify-between z-10 animate-in slide-in-from-right duration-250">
            {/* Drawer Header */}
            <div>
              <div className="p-5 border-b border-border flex items-center justify-between bg-[#f0f5fa] dark:bg-slate-800/60">
                <h3 className="text-sm font-bold text-foreground">
                  {drawerMode === "add" ? "Add Details" : "Edit Details"}
                </h3>
                <button
                  onClick={() => setIsDrawerOpen(false)}
                  className="p-1.5 hover:bg-muted rounded-md text-muted-foreground hover:text-foreground cursor-pointer focus:outline-none border-none bg-transparent"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              {/* Drawer Body */}
              <form onSubmit={handleSaveDetails} className="p-5 space-y-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                    Name <span className="text-red-550">*</span>
                  </label>
                  <Input
                    value={drawerName}
                    onChange={(e) => {
                      setDrawerName(e.target.value);
                      if (e.target.value.trim()) setDrawerNameError("");
                    }}
                    placeholder="Enter Name"
                    className={`h-10 text-xs w-full ${
                      drawerNameError ? "border-red-500 focus-visible:ring-red-500" : ""
                    }`}
                  />
                  {drawerNameError && (
                    <p className="text-[10px] font-semibold text-red-500">{drawerNameError}</p>
                  )}
                </div>
              </form>
            </div>

            {/* Drawer Footer */}
            <div className="p-4 bg-[#f0f5fa] dark:bg-slate-800/60 border-t border-border flex items-center justify-end gap-3">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setIsDrawerOpen(false)}
                className="px-5 border border-slate-300 dark:border-slate-700 h-9 font-semibold text-xs"
              >
                Close
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={handleSaveDetails}
                className="px-5 bg-[#0b5cff] hover:bg-[#094ed9] text-white h-9 font-semibold text-xs"
                disabled={isSaving}
              >
                {isSaving ? (
                  <>
                    <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
                    Saving...
                  </>
                ) : (
                  "Save Details"
                )}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {isDeleteModalOpen && (
        <div className="fixed inset-0 z-[150] flex items-center justify-center p-4">
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-black/50 backdrop-blur-xs"
            onClick={() => setIsDeleteModalOpen(false)}
          />
          {/* Modal Card */}
          <div className="relative bg-card border border-border rounded-xl shadow-xl w-full max-w-sm p-6 space-y-4 animate-in zoom-in-95 duration-150 z-10">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-full bg-red-100 dark:bg-red-950/30 flex items-center justify-center text-red-500 shrink-0">
                <AlertTriangle className="h-5 w-5" />
              </div>
              <h3 className="text-sm font-bold text-foreground">Delete Designation</h3>
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed">
              Are you sure you want to delete this designation? This action is permanent and cannot
              be undone.
            </p>
            <div className="flex items-center justify-end gap-3 pt-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setIsDeleteModalOpen(false)}
                className="h-9 px-4 text-xs font-semibold"
              >
                Cancel
              </Button>
              <Button
                variant="destructive"
                size="sm"
                disabled={deleteMutation.isPending}
                onClick={confirmDelete}
                className="h-9 px-4 text-xs font-semibold bg-red-600 hover:bg-red-700 text-white"
              >
                {deleteMutation.isPending ? (
                  <>
                    <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
                    Deleting...
                  </>
                ) : (
                  "Delete"
                )}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
