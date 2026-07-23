"use client";

import React, { useState, useMemo, useEffect, Fragment } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  ChevronLeft,
  ChevronDown,
  ChevronRight,
  Search,
  Loader2,
  AlertCircle,
  X,
  CheckCircle2,
  XCircle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  usePermissionCatalog,
  useCreateRightsTemplate,
  useUpdateRightsTemplate,
  useReplaceTemplatePermissions,
  useRightsTemplateDetail,
} from "../hooks/use-rights-templates";
import { PermissionCatalogItem, TemplatePermissionInput } from "../types";

export function CreateAccessTemplatePage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const templateIdParam = searchParams.get("id");
  const templateId = templateIdParam ? parseInt(templateIdParam, 10) : null;

  // React Query Hooks
  const { data: catalogData = [], isLoading: isCatalogLoading } = usePermissionCatalog();
  const { data: detailData, isLoading: isDetailLoading } = useRightsTemplateDetail(templateId || undefined);

  const createMutation = useCreateRightsTemplate();
  const updateMutation = useUpdateRightsTemplate();
  const replacePermissionsMutation = useReplaceTemplatePermissions();

  // Form State
  const [templateName, setTemplateName] = useState("");
  const [description, setDescription] = useState("");
  const [isActiveStatus, setIsActiveStatus] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedPermissions, setSelectedPermissions] = useState<Record<string, boolean>>({});

  // Form dirty state tracking & validation
  const [isDirty, setIsDirty] = useState(false);
  const [showUnsavedModal, setShowUnsavedModal] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);

  // Collapsible category state
  const [expandedCategories, setExpandedCategories] = useState<Record<string, boolean>>({});

  // Group catalog items by parent_feature_key
  const groupedCatalog = useMemo(() => {
    const groups: Record<string, PermissionCatalogItem[]> = {};
    catalogData.forEach((item) => {
      const parentKey = item.parent_feature_key || "General Management";
      if (!groups[parentKey]) {
        groups[parentKey] = [];
      }
      groups[parentKey].push(item);
    });
    return groups;
  }, [catalogData]);

  // Set initial expanded categories
  useEffect(() => {
    if (Object.keys(groupedCatalog).length > 0) {
      const initialExpanded: Record<string, boolean> = {};
      Object.keys(groupedCatalog).forEach((groupKey) => {
        initialExpanded[groupKey] = true;
      });
      setExpandedCategories((prev) => ({ ...initialExpanded, ...prev }));
    }
  }, [groupedCatalog]);

  // Populate form if editing
  useEffect(() => {
    if (detailData) {
      setTemplateName(detailData.name || "");
      setDescription(detailData.description || "");
      setIsActiveStatus(!detailData.is_deleted);
      if (detailData.permissions && Array.isArray(detailData.permissions)) {
        const nextState: Record<string, boolean> = {};
        detailData.permissions.forEach((perm) => {
          if (perm.can_create) nextState[`${perm.feature_key}_create`] = true;
          if (perm.can_read) nextState[`${perm.feature_key}_read`] = true;
          if (perm.can_edit) nextState[`${perm.feature_key}_edit`] = true;
          if (perm.can_delete) nextState[`${perm.feature_key}_delete`] = true;
        });
        setSelectedPermissions(nextState);
      }
    }
  }, [detailData]);

  // Total possible permission keys count
  const allPossibleKeys = useMemo(() => {
    const keys: string[] = [];
    catalogData.forEach((item) => {
      const actions = item.supported_actions || ["create", "read", "edit", "delete"];
      actions.forEach((act) => {
        keys.push(`${item.feature_key}_${act}`);
      });
    });
    return keys;
  }, [catalogData]);

  const selectedCount = useMemo(() => {
    return Object.values(selectedPermissions).filter(Boolean).length;
  }, [selectedPermissions]);

  const isAllSelected = useMemo(() => {
    if (allPossibleKeys.length === 0) return false;
    return allPossibleKeys.every((key) => !!selectedPermissions[key]);
  }, [allPossibleKeys, selectedPermissions]);

  // Toggle category expand/collapse
  const toggleCategoryExpand = (catId: string) => {
    setExpandedCategories((prev) => ({
      ...prev,
      [catId]: !prev[catId],
    }));
  };

  // Toggle individual permission checkbox
  const togglePermission = (featureKey: string, action: string) => {
    setIsDirty(true);
    setValidationError(null);
    const key = `${featureKey}_${action}`;
    setSelectedPermissions((prev) => ({
      ...prev,
      [key]: !prev[key],
    }));
  };

  // Toggle feature row (all supported actions)
  const toggleFeatureRow = (item: PermissionCatalogItem) => {
    setIsDirty(true);
    setValidationError(null);
    const actions = item.supported_actions || ["create", "read", "edit", "delete"];
    const allChecked = actions.every((action) => !!selectedPermissions[`${item.feature_key}_${action}`]);

    setSelectedPermissions((prev) => {
      const next = { ...prev };
      actions.forEach((action) => {
        next[`${item.feature_key}_${action}`] = !allChecked;
      });
      return next;
    });
  };

  // Toggle entire column (e.g. all Read, all Create, all Edit, all Delete)
  const toggleColumnAction = (actionName: string) => {
    setIsDirty(true);
    setValidationError(null);
    const colKeys: string[] = [];
    catalogData.forEach((item) => {
      const actions = item.supported_actions || ["create", "read", "edit", "delete"];
      if (actions.includes(actionName)) {
        colKeys.push(`${item.feature_key}_${actionName}`);
      }
    });

    const allColChecked = colKeys.length > 0 && colKeys.every((key) => !!selectedPermissions[key]);

    setSelectedPermissions((prev) => {
      const next = { ...prev };
      colKeys.forEach((key) => {
        next[key] = !allColChecked;
      });
      return next;
    });
  };

  // Toggle select all / clear all
  const toggleSelectAll = () => {
    setIsDirty(true);
    setValidationError(null);
    if (isAllSelected) {
      setSelectedPermissions({});
    } else {
      const next: Record<string, boolean> = {};
      allPossibleKeys.forEach((key) => {
        next[key] = true;
      });
      setSelectedPermissions(next);
    }
  };

  const handleClearAll = () => {
    setIsDirty(true);
    setValidationError(null);
    setSelectedPermissions({});
  };

  // Filter catalog by search query
  const filteredGroupedCatalog = useMemo(() => {
    if (!searchQuery.trim()) return groupedCatalog;
    const query = searchQuery.toLowerCase();

    const filtered: Record<string, PermissionCatalogItem[]> = {};
    Object.entries(groupedCatalog).forEach(([groupName, items]) => {
      const matchingItems = items.filter(
        (item) =>
          item.feature_label.toLowerCase().includes(query) ||
          item.feature_key.toLowerCase().includes(query) ||
          groupName.toLowerCase().includes(query)
      );
      if (matchingItems.length > 0) {
        filtered[groupName] = matchingItems;
      }
    });
    return filtered;
  }, [groupedCatalog, searchQuery]);

  // Construct TemplatePermissionInput[]
  const buildPermissionPayloads = (): TemplatePermissionInput[] => {
    const payloads: TemplatePermissionInput[] = [];

    catalogData.forEach((item) => {
      const canCreate = !!selectedPermissions[`${item.feature_key}_create`];
      const canRead = !!selectedPermissions[`${item.feature_key}_read`];
      const canEdit = !!selectedPermissions[`${item.feature_key}_edit`];
      const canDelete = !!selectedPermissions[`${item.feature_key}_delete`];

      if (canCreate || canRead || canEdit || canDelete) {
        payloads.push({
          feature_key: item.feature_key,
          feature_label: item.feature_label,
          parent_feature_key: item.parent_feature_key,
          can_create: canCreate,
          can_read: canRead,
          can_edit: canEdit,
          can_delete: canDelete,
        });
      }
    });

    return payloads;
  };

  const isSaving =
    createMutation.isPending ||
    updateMutation.isPending ||
    replacePermissionsMutation.isPending;

  // Validation check before save
  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setValidationError(null);

    const trimmedName = templateName.trim();
    if (!trimmedName) {
      setValidationError("Template Name is required.");
      return;
    }

    if (selectedCount === 0) {
      setValidationError("Please select at least one permission.");
      return;
    }

    const permissionsPayload = buildPermissionPayloads();

    try {
      if (templateId) {
        await updateMutation.mutateAsync({
          id: templateId,
          data: { name: trimmedName, description: description.trim(), is_deleted: !isActiveStatus },
        });
        await replacePermissionsMutation.mutateAsync({
          id: templateId,
          permissions: permissionsPayload,
        });
      } else {
        await createMutation.mutateAsync({
          name: trimmedName,
          description: description.trim(),
          permissions: permissionsPayload,
        });
      }
      setIsDirty(false);
      router.push("/allTemplates");
    } catch (err: any) {
      setValidationError(err?.message || "Failed to save rights template. Please check inputs.");
    }
  };

  const handleCancelClick = () => {
    if (isDirty) {
      setShowUnsavedModal(true);
    } else {
      router.push("/allTemplates");
    }
  };

  return (
    <div className="p-6 max-w-[1600px] mx-auto space-y-6 animate-in fade-in duration-200 bg-slate-50/50 dark:bg-slate-950 min-h-screen">
      {/* Header Bar */}
      <div className="flex items-center justify-between bg-white dark:bg-slate-900 px-6 py-4 rounded-xl border border-slate-200 dark:border-slate-800 shadow-2xs">
        <div className="flex items-center space-x-3">
          <button
            onClick={handleCancelClick}
            className="p-1.5 rounded-lg text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-100 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer"
            title="Go Back"
          >
            <ChevronLeft className="h-5 w-5" />
          </button>
          <div>
            <h1 className="text-lg font-bold text-slate-800 dark:text-slate-100 tracking-tight">
              {templateId ? "Edit Rights Template" : "Create Rights Template"}
            </h1>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Configure feature access control and CRUD permission matrix
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          <Button
            type="button"
            variant="outline"
            onClick={handleCancelClick}
            className="text-xs h-9 px-4 border-slate-200 dark:border-slate-700"
          >
            Cancel
          </Button>

          <Button
            onClick={handleSave}
            disabled={!templateName.trim() || isSaving}
            className={`text-xs font-semibold px-6 py-2 h-9 rounded-md transition-all ${
              templateName.trim() && !isSaving
                ? "bg-blue-600 hover:bg-blue-700 text-white shadow-2xs cursor-pointer"
                : "bg-slate-200 dark:bg-slate-800 text-slate-400 dark:text-slate-600 cursor-not-allowed border border-slate-200 dark:border-slate-800"
            }`}
          >
            {isSaving ? (
              <div className="flex items-center space-x-2">
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                <span>Saving...</span>
              </div>
            ) : (
              "Save Template"
            )}
          </Button>
        </div>
      </div>

      {/* Validation Error Alert Banner */}
      {validationError && (
        <div className="p-4 bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800 rounded-lg flex items-center justify-between text-xs text-red-700 dark:text-red-300 animate-in fade-in duration-150">
          <div className="flex items-center space-x-2">
            <AlertCircle className="h-4 w-4 text-red-500 shrink-0" />
            <span className="font-semibold">{validationError}</span>
          </div>
          <button
            onClick={() => setValidationError(null)}
            className="text-red-400 hover:text-red-600"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      )}

      {/* Main Card Container */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-2xs p-6 space-y-6">
        {/* Loading Indicator */}
        {(isCatalogLoading || isDetailLoading) && (
          <div className="py-6 flex items-center justify-center space-x-2 text-xs text-blue-600 animate-pulse">
            <Loader2 className="h-5 w-5 animate-spin" />
            <span>Loading permission catalog and template metadata...</span>
          </div>
        )}

        {/* Template Info Fields */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pb-6 border-b border-slate-100 dark:border-slate-800">
          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
              Template Name <span className="text-red-500">*</span>
            </label>
            <Input
              type="text"
              placeholder="e.g. Product Team, Branch Manager"
              value={templateName}
              onChange={(e) => {
                setTemplateName(e.target.value);
                setIsDirty(true);
                setValidationError(null);
              }}
              className="text-xs bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-700 h-9"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
              Description <span className="text-slate-400 font-normal">(Optional)</span>
            </label>
            <Input
              type="text"
              placeholder="Enter brief description of this role"
              value={description}
              onChange={(e) => {
                setDescription(e.target.value);
                setIsDirty(true);
              }}
              className="text-xs bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-700 h-9"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
              Status
            </label>
            <button
              type="button"
              onClick={() => {
                setIsActiveStatus(!isActiveStatus);
                setIsDirty(true);
              }}
              className={`h-9 px-4 rounded-md text-xs font-semibold flex items-center space-x-2 border transition-all cursor-pointer ${
                isActiveStatus
                  ? "bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 border-emerald-200 dark:border-emerald-900"
                  : "bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 border-slate-200 dark:border-slate-700"
              }`}
            >
              {isActiveStatus ? (
                <>
                  <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                  <span>Active</span>
                </>
              ) : (
                <>
                  <XCircle className="h-4 w-4 text-slate-400" />
                  <span>Inactive</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Toolbar Bar: Bulk Matrix Controls + Search + Counter */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pt-2">
          <div className="flex items-center space-x-4">
            <label className="flex items-center space-x-2 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={isAllSelected}
                onChange={toggleSelectAll}
                className="h-4 w-4 rounded border-slate-300 dark:border-slate-700 text-blue-600 focus:ring-blue-500 cursor-pointer"
              />
              <span className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                Select All
              </span>
            </label>

            <button
              type="button"
              onClick={handleClearAll}
              className="text-xs font-semibold text-slate-500 hover:text-slate-800 dark:hover:text-slate-200 transition-colors cursor-pointer underline"
            >
              Clear All
            </button>
          </div>

          <div className="flex items-center space-x-3 w-full sm:w-auto justify-between sm:justify-end">
            <div className="relative w-full sm:w-64">
              <Search className="h-3.5 w-3.5 text-slate-400 absolute left-3 top-2.5 pointer-events-none" />
              <Input
                type="text"
                placeholder="Search modules & permissions..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-8 text-xs bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-700 h-8 rounded-md"
              />
            </div>

            <div className="px-3 py-1 bg-slate-100 dark:bg-slate-800 text-blue-600 dark:text-blue-400 font-semibold text-xs rounded-full shrink-0 border border-slate-200 dark:border-slate-700">
              {selectedCount} Selected
            </div>
          </div>
        </div>

        {/* Dynamic Permissions Table Matrix */}
        <div className="border border-slate-200 dark:border-slate-800 rounded-lg overflow-hidden">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-50 dark:bg-slate-800/80 border-b border-slate-200 dark:border-slate-700/80 text-slate-700 dark:text-slate-300 text-xs font-semibold">
                <th className="py-3 px-4">Module / Feature Name</th>
                
                {/* Column Action Controls */}
                <th className="py-3 px-4 text-center w-28">
                  <button
                    type="button"
                    onClick={() => toggleColumnAction("create")}
                    className="hover:text-blue-600 transition-colors cursor-pointer inline-flex items-center space-x-1"
                    title="Toggle all Create permissions"
                  >
                    <span>Create</span>
                  </button>
                </th>

                <th className="py-3 px-4 text-center w-28">
                  <button
                    type="button"
                    onClick={() => toggleColumnAction("read")}
                    className="hover:text-blue-600 transition-colors cursor-pointer inline-flex items-center space-x-1"
                    title="Toggle all Read/View permissions"
                  >
                    <span>Read (View)</span>
                  </button>
                </th>

                <th className="py-3 px-4 text-center w-28">
                  <button
                    type="button"
                    onClick={() => toggleColumnAction("edit")}
                    className="hover:text-blue-600 transition-colors cursor-pointer inline-flex items-center space-x-1"
                    title="Toggle all Edit permissions"
                  >
                    <span>Edit</span>
                  </button>
                </th>

                <th className="py-3 px-4 text-center w-28 pr-6">
                  <button
                    type="button"
                    onClick={() => toggleColumnAction("delete")}
                    className="hover:text-blue-600 transition-colors cursor-pointer inline-flex items-center space-x-1"
                    title="Toggle all Delete permissions"
                  >
                    <span>Delete</span>
                  </button>
                </th>
              </tr>
            </thead>

            <tbody className="divide-y divide-slate-100 dark:divide-slate-800 text-xs">
              {Object.entries(filteredGroupedCatalog).map(([groupName, items]) => {
                const isExpanded = expandedCategories[groupName] ?? true;

                // Group check state
                const groupKeys: string[] = [];
                items.forEach((item) => {
                  const actions = item.supported_actions || ["create", "read", "edit", "delete"];
                  actions.forEach((act) => {
                    groupKeys.push(`${item.feature_key}_${act}`);
                  });
                });
                const isGroupChecked = groupKeys.length > 0 && groupKeys.every((key) => !!selectedPermissions[key]);

                const toggleGroupCheck = () => {
                  setIsDirty(true);
                  setValidationError(null);
                  setSelectedPermissions((prev) => {
                    const next = { ...prev };
                    groupKeys.forEach((key) => {
                      next[key] = !isGroupChecked;
                    });
                    return next;
                  });
                };

                return (
                  <Fragment key={groupName}>
                    {/* Category Header Row */}
                    <tr className="bg-slate-50/80 dark:bg-slate-800/50 border-b border-slate-200 dark:border-slate-800">
                      <td colSpan={5} className="py-2.5 px-4">
                        <div className="flex items-center space-x-3">
                          <button
                            type="button"
                            onClick={() => toggleCategoryExpand(groupName)}
                            className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors cursor-pointer"
                          >
                            {isExpanded ? (
                              <ChevronDown className="h-4 w-4" />
                            ) : (
                              <ChevronRight className="h-4 w-4" />
                            )}
                          </button>

                          <label className="flex items-center space-x-2 cursor-pointer select-none">
                            <input
                              type="checkbox"
                              checked={isGroupChecked}
                              onChange={toggleGroupCheck}
                              className="h-4 w-4 rounded border-slate-300 dark:border-slate-700 text-blue-600 focus:ring-blue-500 cursor-pointer"
                            />
                            <span className="font-bold text-slate-800 dark:text-slate-100 uppercase tracking-wider text-[11px]">
                              {groupName.replace(/_/g, " ")}
                            </span>
                          </label>
                        </div>
                      </td>
                    </tr>

                    {/* Sub-Features Rows */}
                    {isExpanded &&
                      items.map((item) => {
                        const supported = item.supported_actions || ["create", "read", "edit", "delete"];
                        const isRowAllChecked = supported.every(
                          (act) => !!selectedPermissions[`${item.feature_key}_${act}`]
                        );

                        return (
                          <tr
                            key={item.feature_key}
                            className="hover:bg-slate-50/50 dark:hover:bg-slate-800/30 transition-colors"
                          >
                            {/* Feature Name */}
                            <td className="py-3 px-4 pl-10 font-medium text-slate-700 dark:text-slate-300">
                              <label className="flex items-center space-x-2 cursor-pointer select-none">
                                <input
                                  type="checkbox"
                                  checked={isRowAllChecked}
                                  onChange={() => toggleFeatureRow(item)}
                                  className="h-4 w-4 rounded border-slate-300 dark:border-slate-700 text-blue-600 focus:ring-blue-500 cursor-pointer"
                                />
                                <span>{item.feature_label}</span>
                              </label>
                            </td>

                            {/* Create Checkbox */}
                            <td className="py-3 px-4 text-center">
                              {supported.includes("create") ? (
                                <input
                                  type="checkbox"
                                  checked={!!selectedPermissions[`${item.feature_key}_create`]}
                                  onChange={() => togglePermission(item.feature_key, "create")}
                                  className="h-4 w-4 rounded border-slate-300 dark:border-slate-700 text-blue-600 focus:ring-blue-500 cursor-pointer"
                                />
                              ) : (
                                <span className="text-slate-300 dark:text-slate-700 font-mono">-</span>
                              )}
                            </td>

                            {/* Read Checkbox */}
                            <td className="py-3 px-4 text-center">
                              {supported.includes("read") ? (
                                <input
                                  type="checkbox"
                                  checked={!!selectedPermissions[`${item.feature_key}_read`]}
                                  onChange={() => togglePermission(item.feature_key, "read")}
                                  className="h-4 w-4 rounded border-slate-300 dark:border-slate-700 text-blue-600 focus:ring-blue-500 cursor-pointer"
                                />
                              ) : (
                                <span className="text-slate-300 dark:text-slate-700 font-mono">-</span>
                              )}
                            </td>

                            {/* Edit Checkbox */}
                            <td className="py-3 px-4 text-center">
                              {supported.includes("edit") ? (
                                <input
                                  type="checkbox"
                                  checked={!!selectedPermissions[`${item.feature_key}_edit`]}
                                  onChange={() => togglePermission(item.feature_key, "edit")}
                                  className="h-4 w-4 rounded border-slate-300 dark:border-slate-700 text-blue-600 focus:ring-blue-500 cursor-pointer"
                                />
                              ) : (
                                <span className="text-slate-300 dark:text-slate-700 font-mono">-</span>
                              )}
                            </td>

                            {/* Delete Checkbox */}
                            <td className="py-3 px-4 text-center pr-6">
                              {supported.includes("delete") ? (
                                <input
                                  type="checkbox"
                                  checked={!!selectedPermissions[`${item.feature_key}_delete`]}
                                  onChange={() => togglePermission(item.feature_key, "delete")}
                                  className="h-4 w-4 rounded border-slate-300 dark:border-slate-700 text-blue-600 focus:ring-blue-500 cursor-pointer"
                                />
                              ) : (
                                <span className="text-slate-300 dark:text-slate-700 font-mono">-</span>
                              )}
                            </td>
                          </tr>
                        );
                      })}
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Unsaved Changes Confirmation Modal */}
      {showUnsavedModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4 animate-in fade-in duration-150">
          <div className="w-full max-w-md rounded-xl bg-white dark:bg-slate-900 shadow-2xl border border-slate-200 dark:border-slate-800 p-6 space-y-4 text-xs">
            <div className="flex items-center space-x-3 text-amber-600">
              <AlertCircle className="h-6 w-6 shrink-0" />
              <h3 className="text-base font-semibold text-slate-800 dark:text-slate-100">
                Unsaved Changes
              </h3>
            </div>

            <p className="text-slate-600 dark:text-slate-400">
              You have unsaved changes in this template. Are you sure you want to discard your changes and leave?
            </p>

            <div className="flex justify-end space-x-2 pt-3 border-t border-slate-100 dark:border-slate-800">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowUnsavedModal(false)}
              >
                Keep Editing
              </Button>
              <Button
                size="sm"
                onClick={() => {
                  setShowUnsavedModal(false);
                  router.push("/allTemplates");
                }}
                className="bg-red-600 hover:bg-red-700 text-white"
              >
                Discard Changes
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
