"use client";

import React, { useState, useMemo, useEffect, useRef } from "react";
import {
  Search,
  SlidersHorizontal,
  Plus,
  Edit2,
  Trash2,
  ChevronLeft,
  ChevronRight,
  MoreVertical,
  X,
  Loader2,
  AlertTriangle,
  Power,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { toast } from "sonner";
import {
  useDepartments,
  useCreateDepartment,
  useUpdateDepartment,
  useActivateDepartment,
  useDeactivateDepartment,
  useDeleteDepartment,
  useDepartmentOptions,
  useDebouncedValue,
} from "../hooks";
import { DepartmentSchema } from "../types";

export function DepartmentList() {
  // Search & Filtering State
  const [searchQuery, setSearchQuery] = useState("");
  const debouncedSearch = useDebouncedValue(searchQuery, 400);

  // Pagination State
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  // Sorting State
  const [sortOrder, setSortOrder] = useState<"asc" | "desc" | null>(null);

  // UI State: Dropdowns & Modals
  const [activeActionRowId, setActiveActionRowId] = useState<number | null>(null);
  const [isFilterOpen, setIsFilterOpen] = useState(false);
  const [isNameFilterOpen, setIsNameFilterOpen] = useState(false);
  
  // Filter state
  const [filterSearch, setFilterSearch] = useState("");
  const [selectedStatuses, setSelectedStatuses] = useState<string[]>(["Active"]);

  const [nameFilterSearch, setNameFilterSearch] = useState("");
  const [selectedNames, setSelectedNames] = useState<string[]>([]);

  // Drawer (Add / Edit details modal)
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [drawerMode, setDrawerMode] = useState<"add" | "edit">("add");
  const [drawerId, setDrawerId] = useState<number | null>(null);
  const [drawerName, setDrawerName] = useState("");
  const [drawerNameError, setDrawerNameError] = useState("");

  // Refs for closing popups on click outside
  const actionDropdownRef = useRef<HTMLDivElement>(null);
  const filterDropdownRef = useRef<HTMLDivElement>(null);
  const nameFilterDropdownRef = useRef<HTMLDivElement>(null);

  // Map selectedStatuses to is_active query param
  const isActiveParam = useMemo(() => {
    const hasActive = selectedStatuses.includes("Active");
    const hasInactive = selectedStatuses.includes("Inactive");
    if (hasActive && hasInactive) return undefined;
    if (hasActive) return true;
    if (hasInactive) return false;
    return undefined;
  }, [selectedStatuses]);

  // React Query: Get paginated/filtered/sorted departments
  const departmentsQuery = useDepartments({
    page: currentPage,
    page_size: pageSize,
    search: debouncedSearch.trim() || undefined,
    is_active: isActiveParam,
    sort_by: sortOrder ? "dept_name" : undefined,
    sort_order: sortOrder || undefined,
  });

  // React Query: Fetch department name options for the name filter dropdown
  const { data: departmentOptions = [] } = useDepartmentOptions();

  // React Query: Mutations
  const createMutation = useCreateDepartment();
  const updateMutation = useUpdateDepartment();
  const activateMutation = useActivateDepartment();
  const deactivateMutation = useDeactivateDepartment();
  const deleteMutation = useDeleteDepartment();

  const isMutationPending =
    createMutation.isPending ||
    updateMutation.isPending ||
    activateMutation.isPending ||
    deactivateMutation.isPending ||
    deleteMutation.isPending;

  // Reset page when search or status filters change
  useEffect(() => {
    setCurrentPage(1);
  }, [debouncedSearch, selectedStatuses]);

  // Click outside to close dropdowns
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (actionDropdownRef.current && !actionDropdownRef.current.contains(event.target as Node)) {
        setActiveActionRowId(null);
      }
      if (filterDropdownRef.current && !filterDropdownRef.current.contains(event.target as Node)) {
        setIsFilterOpen(false);
      }
      if (nameFilterDropdownRef.current && !nameFilterDropdownRef.current.contains(event.target as Node)) {
        setIsNameFilterOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Department name options from active options
  const allDepartmentNames = useMemo(() => {
    return Array.from(new Set(departmentOptions.map(d => d.dept_name)));
  }, [departmentOptions]);

  // Departments list from the query response
  const departments = departmentsQuery.data?.items ?? [];
  const paginationMeta = departmentsQuery.data?.pagination;
  const totalRecords = paginationMeta?.total_records ?? 0;
  const totalPages = paginationMeta?.total_pages ?? 1;

  // Locally filter by checked names in the Name Filter Dropdown (keeps mock-like UI parity)
  const processedDepartments = useMemo(() => {
    let result = [...departments];
    if (selectedNames.length > 0) {
      result = result.filter((d) => selectedNames.includes(d.dept_name));
    }
    return result;
  }, [departments, selectedNames]);

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

  const handleEditClick = (d: DepartmentSchema) => {
    setDrawerMode("edit");
    setDrawerId(d.dept_id);
    setDrawerName(d.dept_name);
    setDrawerNameError("");
    setIsDrawerOpen(true);
    setActiveActionRowId(null);
  };

  const handleToggleActive = (d: DepartmentSchema) => {
    setActiveActionRowId(null);
    const mutation = d.is_active ? deactivateMutation : activateMutation;
    mutation.mutate(d.dept_id, {
      onSuccess: () => {
        toast.success(`Department ${d.is_active ? "deactivated" : "activated"} successfully`);
      },
      onError: (err: any) => {
        const errMsg = err?.response?.data?.error?.message || `Failed to ${d.is_active ? "deactivate" : "activate"} department`;
        toast.error(errMsg);
      },
    });
  };

  const handleDeleteClick = (id: number) => {
    setActiveActionRowId(null);
    deleteMutation.mutate(id, {
      onSuccess: () => {
        toast.success("Department deleted successfully");
      },
      onError: (err: any) => {
        const errMsg = err?.response?.data?.error?.message || "Failed to delete department";
        toast.error(errMsg);
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
        { dept_name: drawerName.trim() },
        {
          onSuccess: () => {
            toast.success("Department created successfully");
            setIsDrawerOpen(false);
          },
          onError: (err: any) => {
            const errMsg = err?.response?.data?.error?.message || "Failed to create department";
            toast.error(errMsg);
          },
        }
      );
    } else {
      if (drawerId === null) return;
      updateMutation.mutate(
        { id: drawerId, data: { dept_name: drawerName.trim() } },
        {
          onSuccess: () => {
            toast.success("Department updated successfully");
            setIsDrawerOpen(false);
          },
          onError: (err: any) => {
            const errMsg = err?.response?.data?.error?.message || "Failed to update department";
            toast.error(errMsg);
          },
        }
      );
    }
  };

  // Filter statuses
  const filterOptions = ["Active", "Inactive"];

  const handleToggleStatus = (status: string) => {
    if (selectedStatuses.includes(status)) {
      setSelectedStatuses(prev => prev.filter(s => s !== status));
    } else {
      setSelectedStatuses(prev => [...prev, status]);
    }
  };

  const handleSelectAllStatuses = () => {
    if (selectedStatuses.length === filterOptions.length) {
      setSelectedStatuses([]);
    } else {
      setSelectedStatuses(filterOptions);
    }
  };

  return (
    <div className="space-y-4">
      {/* Upper header */}
      <div className="flex items-center justify-between">
        <h1 className="flex items-center gap-1.5 text-xl font-bold tracking-tight text-foreground">
          <span>Departments</span>
          <span className="text-primary font-bold">({totalRecords})</span>
        </h1>
        <Button variant="primary" size="sm" onClick={handleAddClick} className="gap-1.5 shadow-xs">
          <Plus className="h-4 w-4" />
          Add New
        </Button>
      </div>

      {/* Main card */}
      <div className="bg-card border border-border rounded-xl shadow-xs overflow-hidden">
        {/* Toolbar */}
        <div className="p-4 border-b border-border flex items-center justify-between gap-4 bg-muted/10">
          <div className="relative w-72">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by Department Name..."
              className="pl-9 pr-4 h-9 w-full text-xs"
            />
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => {
                departmentsQuery.refetch();
              }}
              className="text-[10px] text-muted-foreground hover:text-foreground px-2 py-1 border border-border rounded-md transition-colors cursor-pointer"
            >
              Reload Data
            </button>
          </div>
        </div>

        {/* Table representation */}
        <div className="overflow-x-auto relative min-h-[300px]">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-muted/30 border-b border-border">
                <th className="px-6 py-3.5 text-xs font-semibold text-foreground/80 relative select-none">
                  <div className="flex items-center gap-2">
                    <div className="flex items-center gap-1 cursor-pointer hover:text-foreground transition-colors" onClick={handleSortName}>
                      <span>Department Name</span>
                      <span className="text-[10px] text-muted-foreground">
                        {sortOrder === "asc" ? "↑" : sortOrder === "desc" ? "↓" : "↕"}
                      </span>
                    </div>
                    
                    <span className="text-muted-foreground/30 font-normal">|</span>
                    
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setIsNameFilterOpen(!isNameFilterOpen);
                      }}
                      className={`p-1 hover:bg-muted rounded-md transition-colors cursor-pointer ${selectedNames.length > 0 ? "text-primary" : "text-muted-foreground"}`}
                    >
                      <SlidersHorizontal className="h-3 w-3" />
                    </button>
                  </div>

                  {/* Department Name Filter Dropdown */}
                  {isNameFilterOpen && (
                    <div ref={nameFilterDropdownRef} className="absolute left-6 top-10 w-56 bg-card border border-border rounded-lg shadow-xl p-3 z-50 space-y-3 animate-in fade-in duration-100 text-left">
                      <div className="relative">
                        <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
                        <input
                          type="text"
                          value={nameFilterSearch}
                          onChange={e => setNameFilterSearch(e.target.value)}
                          placeholder="Search"
                          className="w-full pl-8 pr-2 py-1.5 text-xs bg-muted/30 border border-border rounded focus:outline-none focus:ring-1 focus:ring-primary"
                        />
                      </div>
                      <div className="space-y-2 max-h-40 overflow-y-auto">
                        <label className="flex items-center gap-2 text-xs font-medium text-foreground cursor-pointer select-none">
                          <input
                            type="checkbox"
                            checked={selectedNames.length === allDepartmentNames.length && allDepartmentNames.length > 0}
                            onChange={() => {
                              if (selectedNames.length === allDepartmentNames.length) {
                                setSelectedNames([]);
                              } else {
                                setSelectedNames(allDepartmentNames);
                              }
                            }}
                            className="rounded border-input text-primary focus:ring-primary h-3.5 w-3.5"
                          />
                          Select All
                        </label>
                        <hr className="border-border" />
                        {allDepartmentNames.filter(name => name.toLowerCase().includes(nameFilterSearch.toLowerCase())).map(name => (
                          <label key={name} className="flex items-center gap-2 text-xs text-muted-foreground hover:text-foreground cursor-pointer select-none">
                            <input
                              type="checkbox"
                              checked={selectedNames.includes(name)}
                              onChange={() => {
                                if (selectedNames.includes(name)) {
                                  setSelectedNames(prev => prev.filter(n => n !== name));
                                } else {
                                  setSelectedNames(prev => [...prev, name]);
                                }
                              }}
                              className="rounded border-input text-primary focus:ring-primary h-3.5 w-3.5"
                            />
                            {name}
                          </label>
                        ))}
                      </div>
                      <div className="flex items-center justify-between pt-1">
                        <button
                          onClick={() => {
                            setSelectedNames([]);
                            setIsNameFilterOpen(false);
                          }}
                          className="text-[10px] font-semibold text-muted-foreground hover:text-foreground px-2 py-1 border border-border rounded cursor-pointer"
                        >
                          Clear
                        </button>
                        <button
                          onClick={() => setIsNameFilterOpen(false)}
                          className="text-[10px] font-semibold bg-primary text-primary-foreground hover:bg-primary/95 px-3 py-1 rounded cursor-pointer"
                        >
                          Apply
                        </button>
                      </div>
                    </div>
                  )}
                </th>
                <th className="px-6 py-3.5 text-xs font-semibold text-foreground/80">Status</th>
                <th className="px-6 py-3.5 text-xs font-semibold text-foreground/80 relative select-none">
                  <div className="flex items-center gap-1.5">
                    Employee Count
                    <button
                      onClick={() => setIsFilterOpen(!isFilterOpen)}
                      className={`p-1 hover:bg-muted rounded-md transition-colors ${selectedStatuses.length !== 2 ? "text-primary" : "text-muted-foreground"}`}
                    >
                      <SlidersHorizontal className="h-3 w-3" />
                    </button>
                  </div>

                  {/* Employee Count Status Filter Dropdown */}
                  {isFilterOpen && (
                    <div ref={filterDropdownRef} className="absolute left-6 top-10 w-56 bg-card border border-border rounded-lg shadow-xl p-3 z-50 space-y-3 animate-in fade-in duration-100">
                      <div className="relative">
                        <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
                        <input
                          type="text"
                          value={filterSearch}
                          onChange={e => setFilterSearch(e.target.value)}
                          placeholder="Search"
                          className="w-full pl-8 pr-2 py-1.5 text-xs bg-muted/30 border border-border rounded focus:outline-none focus:ring-1 focus:ring-primary"
                        />
                      </div>
                      <div className="space-y-2">
                        <label className="flex items-center gap-2 text-xs font-medium text-foreground cursor-pointer select-none">
                          <input
                            type="checkbox"
                            checked={selectedStatuses.length === filterOptions.length}
                            onChange={handleSelectAllStatuses}
                            className="rounded border-input text-primary focus:ring-primary h-3.5 w-3.5"
                          />
                          Select All
                        </label>
                        <hr className="border-border" />
                        {filterOptions.filter(f => f.toLowerCase().includes(filterSearch.toLowerCase())).map(status => (
                          <label key={status} className="flex items-center gap-2 text-xs text-muted-foreground hover:text-foreground cursor-pointer select-none">
                            <input
                              type="checkbox"
                              checked={selectedStatuses.includes(status)}
                              onChange={() => handleToggleStatus(status)}
                              className="rounded border-input text-primary focus:ring-primary h-3.5 w-3.5"
                            />
                            {status}
                          </label>
                        ))}
                      </div>
                      <div className="flex items-center justify-between pt-1">
                        <button
                          onClick={() => {
                            setSelectedStatuses(["Active"]);
                            setIsFilterOpen(false);
                          }}
                          className="text-[10px] font-semibold text-muted-foreground hover:text-foreground px-2 py-1 border border-border rounded cursor-pointer"
                        >
                          Clear
                        </button>
                        <button
                          onClick={() => setIsFilterOpen(false)}
                          className="text-[10px] font-semibold bg-primary text-primary-foreground hover:bg-primary/95 px-3 py-1 rounded cursor-pointer"
                        >
                          Apply
                        </button>
                      </div>
                    </div>
                  )}
                </th>
                <th className="px-6 py-3.5 text-xs font-semibold text-foreground/80 text-right">Action</th>
              </tr>
            </thead>
            <tbody>
              {departmentsQuery.isLoading ? (
                Array.from({ length: pageSize }).map((_, idx) => (
                  <tr key={idx} className="border-b border-border/60">
                    <td className="px-6 py-4.5">
                      <div className="h-4 w-40 bg-muted/40 rounded animate-pulse" />
                    </td>
                    <td className="px-6 py-4.5">
                      <div className="h-4.5 w-16 bg-muted/40 rounded-full animate-pulse" />
                    </td>
                    <td className="px-6 py-4.5">
                      <div className="h-4 w-10 bg-muted/40 rounded animate-pulse" />
                    </td>
                    <td className="px-6 py-4.5 flex justify-end">
                      <div className="h-8 w-8 bg-muted/40 rounded-md animate-pulse" />
                    </td>
                  </tr>
                ))
              ) : departmentsQuery.isError ? (
                <tr>
                  <td colSpan={4} className="px-6 py-12 text-center">
                    <div className="flex flex-col items-center justify-center space-y-3">
                      <div className="h-12 w-12 rounded-full bg-destructive/10 flex items-center justify-center text-destructive">
                        <AlertTriangle className="h-6 w-6" />
                      </div>
                      <div>
                        <h4 className="text-sm font-semibold text-foreground">Failed to Load Departments</h4>
                        <p className="text-xs text-muted-foreground mt-0.5">
                          {departmentsQuery.error instanceof Error ? departmentsQuery.error.message : "An error occurred."}
                        </p>
                      </div>
                      <Button variant="outline" size="sm" onClick={() => departmentsQuery.refetch()}>
                        Retry
                      </Button>
                    </div>
                  </td>
                </tr>
              ) : processedDepartments.length === 0 ? (
                <tr>
                  <td colSpan={4} className="px-6 py-12 text-center">
                    <div className="flex flex-col items-center justify-center space-y-3">
                      <div className="h-12 w-12 rounded-full bg-muted/50 flex items-center justify-center text-muted-foreground">
                        <AlertTriangle className="h-6 w-6" />
                      </div>
                      <div>
                        <h4 className="text-sm font-semibold text-foreground">No Departments Found</h4>
                        <p className="text-xs text-muted-foreground mt-0.5">Try adjusting your search query or filters.</p>
                      </div>
                      <Button variant="outline" size="sm" onClick={() => { setSearchQuery(""); setSelectedStatuses(["Active", "Inactive"]); setSelectedNames([]); }}>
                        Reset Filters
                      </Button>
                    </div>
                  </td>
                </tr>
              ) : (
                processedDepartments.map((d) => (
                  <tr key={d.dept_id} className="border-b border-border/60 hover:bg-muted/10 transition-colors">
                    <td className="px-6 py-4.5 text-xs font-medium text-foreground">{d.dept_name}</td>
                    <td className="px-6 py-4.5 text-xs">
                      <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-bold border border-border/40 ${
                        d.is_active 
                          ? "bg-emerald-500/5 text-emerald-700 dark:text-emerald-400 border-emerald-550/10" 
                          : "bg-yellow-500/5 text-yellow-750 dark:text-yellow-450 border-yellow-550/10"
                      }`}>
                        <span className={`h-1.5 w-1.5 rounded-full ${d.is_active ? "bg-emerald-500" : "bg-yellow-500"}`} />
                        {d.is_active ? "Active" : "Inactive"}
                      </span>
                    </td>
                    <td className="px-6 py-4.5 text-xs text-muted-foreground">{d.employee_count}</td>
                    <td className="px-6 py-4.5 text-right relative">
                      <button
                        onClick={() => setActiveActionRowId(activeActionRowId === d.dept_id ? null : d.dept_id)}
                        className="p-1.5 hover:bg-muted border border-border/60 rounded-md transition-colors inline-flex items-center justify-center cursor-pointer text-muted-foreground hover:text-foreground"
                      >
                        <MoreVertical className="h-3.5 w-3.5" />
                      </button>

                      {/* Dropdown Menu */}
                      {activeActionRowId === d.dept_id && (
                        <div ref={actionDropdownRef} className="absolute right-6 top-12 w-32 bg-card border border-border rounded-lg shadow-xl py-1.5 z-50 animate-in fade-in duration-100">
                          <button
                            onClick={() => handleEditClick(d)}
                            className="w-full flex items-center gap-2 px-3 py-1.5 text-xs font-medium text-foreground hover:bg-muted/50 transition-colors cursor-pointer text-left"
                          >
                            <Edit2 className="h-3.5 w-3.5 text-muted-foreground" />
                            Edit
                          </button>
                          <button
                            onClick={() => handleToggleActive(d)}
                            className="w-full flex items-center gap-2 px-3 py-1.5 text-xs font-medium text-foreground hover:bg-muted/50 transition-colors cursor-pointer text-left"
                          >
                            <Power className="h-3.5 w-3.5 text-muted-foreground" />
                            {d.is_active ? "Deactivate" : "Activate"}
                          </button>
                          <button
                            disabled={isMutationPending}
                            onClick={() => handleDeleteClick(d.dept_id)}
                            className="w-full flex items-center gap-2 px-3 py-1.5 text-xs font-medium text-destructive hover:bg-destructive/10 disabled:opacity-50 transition-colors cursor-pointer text-left"
                          >
                            <Trash2 className="h-3.5 w-3.5 text-destructive" />
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

        {/* Footer pagination */}
        <div className="p-4 border-t border-border flex items-center justify-between gap-4 bg-muted/5 text-xs">
          <div className="text-muted-foreground">
            Showing <span className="font-semibold text-foreground">{totalRecords > 0 ? (currentPage - 1) * pageSize + 1 : 0}</span> to{" "}
            <span className="font-semibold text-foreground">
              {Math.min(currentPage * pageSize, totalRecords)}
            </span>{" "}
            of <span className="font-semibold text-foreground">{totalRecords}</span> Results
          </div>

          <div className="flex items-center gap-3">
            {/* Page Size select */}
            <div className="flex items-center gap-1.5">
              <select
                value={pageSize}
                onChange={(e) => {
                  setPageSize(Number(e.target.value));
                  setCurrentPage(1);
                }}
                className="bg-card border border-border rounded px-2.5 py-1 text-xs text-foreground cursor-pointer focus:outline-none focus:ring-1 focus:ring-primary"
              >
                {[5, 10, 20, 50].map((size) => (
                  <option key={size} value={size}>
                    {size} / Page
                  </option>
                ))}
              </select>
            </div>

            {/* Prev / Next buttons */}
            <div className="flex items-center gap-1">
              <button
                disabled={currentPage === 1}
                onClick={() => setCurrentPage((p) => p - 1)}
                className="p-1.5 border border-border rounded-md hover:bg-muted disabled:opacity-50 disabled:hover:bg-transparent cursor-pointer disabled:cursor-not-allowed transition-colors text-muted-foreground"
              >
                <ChevronLeft className="h-3.5 w-3.5" />
              </button>

              {Array.from({ length: totalPages }).map((_, idx) => (
                <button
                  key={idx}
                  onClick={() => setCurrentPage(idx + 1)}
                  className={`h-7 w-7 flex items-center justify-center rounded-md border text-xs font-semibold cursor-pointer transition-colors ${
                    currentPage === idx + 1
                      ? "bg-primary text-primary-foreground border-primary"
                      : "border-border hover:bg-muted text-muted-foreground"
                  }`}
                >
                  {idx + 1}
                </button>
              ))}

              <button
                disabled={currentPage === totalPages}
                onClick={() => setCurrentPage((p) => p + 1)}
                className="p-1.5 border border-border rounded-md hover:bg-muted disabled:opacity-50 disabled:hover:bg-transparent cursor-pointer disabled:cursor-not-allowed transition-colors text-muted-foreground"
              >
                <ChevronRight className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Drawer / Sidebar detail form */}
      {isDrawerOpen && (
        <div className="fixed inset-0 z-[100] flex justify-end">
          {/* Backdrop */}
          <div className="absolute inset-0 bg-black/60 backdrop-blur-xs transition-opacity" onClick={() => setIsDrawerOpen(false)} />

          {/* Drawer content */}
          <div className="relative w-full max-w-md bg-card border-l border-border h-full shadow-2xl flex flex-col justify-between z-10 animate-in slide-in-from-right duration-250">
            {/* Drawer Header */}
            <div>
              <div className="p-5 border-b border-border flex items-center justify-between bg-muted/20">
                <h3 className="text-sm font-bold text-foreground">
                  {drawerMode === "add" ? "Add Details" : "Edit Details"}
                </h3>
                <button
                  onClick={() => setIsDrawerOpen(false)}
                  className="p-1.5 hover:bg-muted rounded-md text-muted-foreground hover:text-foreground cursor-pointer focus:outline-none"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              {/* Drawer Body */}
              <form onSubmit={handleSaveDetails} className="p-5 space-y-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-foreground/80">
                    Name <span className="text-red-550">*</span>
                  </label>
                  <Input
                    value={drawerName}
                    onChange={(e) => {
                      setDrawerName(e.target.value);
                      if (e.target.value.trim()) setDrawerNameError("");
                    }}
                    placeholder="Enter Name"
                    className={`h-10 text-xs w-full ${drawerNameError ? "border-red-500 focus-visible:ring-red-500" : ""}`}
                  />
                  {drawerNameError && (
                    <p className="text-[10px] font-semibold text-red-500">{drawerNameError}</p>
                  )}
                </div>
              </form>
            </div>

            {/* Drawer Footer */}
            <div className="p-4 bg-muted/10 border-t border-border flex items-center justify-end gap-3">
              <Button variant="outline" size="sm" onClick={() => setIsDrawerOpen(false)} className="px-5">
                Close
              </Button>
              <Button variant="primary" size="sm" onClick={handleSaveDetails} className="px-5" disabled={isMutationPending}>
                {isMutationPending ? (
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
    </div>
  );
}
