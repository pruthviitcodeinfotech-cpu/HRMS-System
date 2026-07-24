"use client";

import React, { useState, useEffect, useMemo } from "react";
import { ChevronDown, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useBranchOptions, useDepartmentOptions } from "@/features/employees/hooks";
import { useRightsTemplates } from "../hooks/use-rights-templates";

export interface UserFormData {
  id?: number;
  employee_id?: number | null;
  name: string;
  email: string;
  mobile_country_code?: string;
  mobile_number: string;
  password?: string;
  confirm_password?: string;
  is_super_admin: boolean;
  status?: "Active" | "Inactive";
  template_id?: number | null;
  template_name?: string;
  branch_ids?: number[];
  department_ids?: number[];
  add_custom_rights?: boolean;
}

interface UserFormModalProps {
  isOpen: boolean;
  onClose: () => void;
  userToEdit?: UserFormData | null;
  onSave?: (data: UserFormData) => void;
  isLoading?: boolean;
}

export function UserFormModal({
  isOpen,
  onClose,
  userToEdit,
  onSave,
  isLoading = false,
}: UserFormModalProps) {
  const isEditing = Boolean(userToEdit);

  // Form State matching screenshot requirements
  const [formData, setFormData] = useState<UserFormData>({
    name: "",
    email: "",
    mobile_country_code: "+91",
    mobile_number: "",
    password: "",
    confirm_password: "",
    is_super_admin: false,
    status: "Active",
    template_id: null,
    employee_id: null,
    branch_ids: [],
    department_ids: [],
    add_custom_rights: false,
  });

  // Master Data hooks (Golden Rule: Reuse existing modules)
  const { data: branchOptions = [], isLoading: isBranchesLoading } = useBranchOptions();
  const { data: departmentOptions = [], isLoading: isDeptsLoading } = useDepartmentOptions();
  const { data: templateData } = useRightsTemplates({
    page: 1,
    page_size: 100,
  });

  const templatesList = templateData?.items || [];

  useEffect(() => {
    if (userToEdit) {
      setFormData({
        id: userToEdit.id,
        employee_id: userToEdit.employee_id ?? null,
        name: userToEdit.name || "",
        email: userToEdit.email || "",
        mobile_country_code: userToEdit.mobile_country_code || "+91",
        mobile_number: userToEdit.mobile_number || "",
        password: "",
        confirm_password: "",
        is_super_admin: userToEdit.is_super_admin ?? false,
        status: userToEdit.status || "Active",
        template_id: userToEdit.template_id ?? null,
        branch_ids: userToEdit.branch_ids || [],
        department_ids: userToEdit.department_ids || [],
        add_custom_rights: userToEdit.add_custom_rights ?? false,
      });
    } else {
      setFormData({
        name: "",
        email: "",
        mobile_country_code: "+91",
        mobile_number: "",
        password: "",
        confirm_password: "",
        is_super_admin: false,
        status: "Active",
        template_id: null,
        employee_id: null,
        branch_ids: [],
        department_ids: [],
        add_custom_rights: false,
      });
    }
  }, [userToEdit, isOpen]);

  // Handle ESC key press
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen && !isLoading) {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose, isLoading]);

  // Branch Selection Toggles
  const selectedBranchIds = formData.branch_ids || [];
  const allBranchIds = useMemo(() => branchOptions.map((b) => b.branch_id), [branchOptions]);
  const isAllBranchesSelected =
    allBranchIds.length > 0 && allBranchIds.every((id) => selectedBranchIds.includes(id));

  const toggleBranch = (branchId: number) => {
    setFormData((prev) => {
      const current = prev.branch_ids || [];
      const updated = current.includes(branchId)
        ? current.filter((id) => id !== branchId)
        : [...current, branchId];
      return { ...prev, branch_ids: updated };
    });
  };

  const toggleAllBranches = () => {
    if (isAllBranchesSelected) {
      setFormData((prev) => ({ ...prev, branch_ids: [] }));
    } else {
      setFormData((prev) => ({ ...prev, branch_ids: [...allBranchIds] }));
    }
  };

  // Department Selection Toggles
  const selectedDepartmentIds = formData.department_ids || [];
  const allDepartmentIds = useMemo(() => departmentOptions.map((d) => d.dept_id), [departmentOptions]);
  const isAllDepartmentsSelected =
    allDepartmentIds.length > 0 &&
    allDepartmentIds.every((id) => selectedDepartmentIds.includes(id));

  const toggleDepartment = (deptId: number) => {
    setFormData((prev) => {
      const current = prev.department_ids || [];
      const updated = current.includes(deptId)
        ? current.filter((id) => id !== deptId)
        : [...current, deptId];
      return { ...prev, department_ids: updated };
    });
  };

  const toggleAllDepartments = () => {
    if (isAllDepartmentsSelected) {
      setFormData((prev) => ({ ...prev, department_ids: [] }));
    } else {
      setFormData((prev) => ({ ...prev, department_ids: [...allDepartmentIds] }));
    }
  };

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (onSave) {
      onSave(formData);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4 animate-in fade-in duration-200">
      <div
        className="w-full max-w-5xl rounded-xl bg-white dark:bg-slate-900 shadow-2xl border border-slate-200 dark:border-slate-800 overflow-hidden flex flex-col max-h-[92vh] animate-in zoom-in-95 duration-150"
        role="dialog"
        aria-modal="true"
        aria-labelledby="user-modal-title"
      >
        {/* Modal Top Bar */}
        <div className="flex items-center justify-between px-6 py-3.5 border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
          <div className="flex items-center space-x-2">
            <button
              type="button"
              onClick={onClose}
              className="text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 font-medium text-sm flex items-center gap-1 cursor-pointer"
            >
              <span>&lt;</span>
              <span className="font-semibold text-slate-800 dark:text-slate-100 text-sm">
                {isEditing ? "Edit User" : "Create User"}
              </span>
            </button>
          </div>

          <div className="flex items-center space-x-3">
            <Button
              type="button"
              variant="outline"
              onClick={onClose}
              disabled={isLoading}
              className="text-xs font-semibold h-8 px-4 border-slate-200 dark:border-slate-700"
            >
              Cancel
            </Button>
            <Button
              type="submit"
              form="create-user-form"
              disabled={isLoading}
              className="bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold h-8 px-6 shadow-2xs cursor-pointer flex items-center space-x-1.5"
            >
              {isLoading && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
              <span>{isEditing ? "Save" : "Create"}</span>
            </Button>
          </div>
        </div>

        {/* Modal Form Body - 2-Card Layout matching screenshot */}
        <form
          id="create-user-form"
          onSubmit={handleSubmit}
          className="p-6 overflow-y-auto flex-1 text-xs bg-slate-50/50 dark:bg-slate-950/40"
        >
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
            {/* Card 1: User Details */}
            <div className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800 shadow-2xs space-y-4">
              <h3 className="text-sm font-bold text-slate-800 dark:text-slate-100 border-b border-slate-100 dark:border-slate-800 pb-3">
                User Details
              </h3>

              {/* Name */}
              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                  Name <span className="text-red-500">*</span>
                </label>
                <Input
                  type="text"
                  placeholder="Enter Name"
                  required
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="text-xs h-9 bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-700"
                />
              </div>

              {/* Mobile Number */}
              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                  Mobile Number <span className="text-red-500">*</span>
                </label>
                <div className="flex items-center gap-2">
                  <select
                    value={formData.mobile_country_code || "+91"}
                    onChange={(e) => setFormData({ ...formData, mobile_country_code: e.target.value })}
                    className="w-20 h-9 rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-2 text-xs font-medium text-slate-700 dark:text-slate-200 focus:outline-none cursor-pointer shrink-0"
                  >
                    <option value="+91">+91</option>
                    <option value="+1">+1</option>
                    <option value="+44">+44</option>
                    <option value="+971">+971</option>
                  </select>
                  <Input
                    type="tel"
                    placeholder="Enter Mobile Number"
                    required
                    value={formData.mobile_number}
                    onChange={(e) => setFormData({ ...formData, mobile_number: e.target.value })}
                    className="text-xs h-9 bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-700 flex-1"
                  />
                </div>
              </div>

              {/* Email */}
              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                  Email <span className="text-red-500">*</span>
                </label>
                <Input
                  type="email"
                  placeholder="Enter Email"
                  required
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  className="text-xs h-9 bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-700"
                />
              </div>

              {/* Password (for new user creation) */}
              {!isEditing && (
                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                    Initial Password
                  </label>
                  <Input
                    type="password"
                    placeholder="Enter initial password (optional)"
                    value={formData.password}
                    onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                    className="text-xs h-9 bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-700"
                  />
                </div>
              )}

              {/* Is User Super Admin? Toggle Switch */}
              <div className="pt-2 flex items-center space-x-3">
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formData.is_super_admin}
                    onChange={(e) => setFormData({ ...formData, is_super_admin: e.target.checked })}
                    className="sr-only peer"
                  />
                  <div className="w-9 h-5 bg-slate-200 peer-focus:outline-none rounded-full peer dark:bg-slate-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all dark:after:border-slate-600 peer-checked:bg-blue-600"></div>
                </label>
                <span className="font-semibold text-slate-700 dark:text-slate-300 text-xs">
                  Is User Super Admin?
                </span>
              </div>
            </div>

            {/* Card 2: Assign Rights */}
            <div className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800 shadow-2xs space-y-4">
              <h3 className="text-sm font-bold text-slate-800 dark:text-slate-100 border-b border-slate-100 dark:border-slate-800 pb-3">
                Assign Rights
              </h3>

              {/* Access Template */}
              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                  Access Template
                </label>
                <div className="relative">
                  <select
                    value={formData.template_id || ""}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        template_id: e.target.value ? Number(e.target.value) : null,
                      })
                    }
                    className="w-full appearance-none rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 pr-8 text-xs font-medium text-slate-700 dark:text-slate-200 focus:outline-none h-9 cursor-pointer"
                  >
                    <option value="">Select Access Template</option>
                    {templatesList.map((tmpl) => (
                      <option key={tmpl.id} value={tmpl.id}>
                        {tmpl.name}
                      </option>
                    ))}
                  </select>
                  <ChevronDown className="h-4 w-4 text-slate-400 absolute right-2.5 top-2.5 pointer-events-none" />
                </div>
              </div>

              {/* Select Punch In Branches */}
              <div className="space-y-2 pt-1">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                    Select Punch In Branches
                  </label>
                  <label className="flex items-center space-x-1.5 cursor-pointer text-[11px] text-slate-600 dark:text-slate-400 select-none">
                    <input
                      type="checkbox"
                      checked={isAllBranchesSelected}
                      onChange={toggleAllBranches}
                      className="h-3.5 w-3.5 rounded border-slate-300 text-blue-600 focus:ring-blue-500 cursor-pointer"
                    />
                    <span>Select All</span>
                  </label>
                </div>

                <div className="flex flex-wrap gap-2 min-h-10 p-2 rounded-lg border border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/20">
                  {isBranchesLoading ? (
                    <span className="text-slate-400 italic">Loading branches...</span>
                  ) : branchOptions.length === 0 ? (
                    <span className="text-slate-400 italic">No branches available.</span>
                  ) : (
                    branchOptions.map((b) => {
                      const isSelected = selectedBranchIds.includes(b.branch_id);
                      return (
                        <button
                          key={b.branch_id}
                          type="button"
                          onClick={() => toggleBranch(b.branch_id)}
                          className={`px-3 py-1 rounded-md text-xs font-medium border transition-all cursor-pointer ${
                            isSelected
                              ? "bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 border-blue-300 dark:border-blue-700 shadow-2xs"
                              : "bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 border-slate-200 dark:border-slate-700 hover:border-slate-300"
                          }`}
                        >
                          {b.branch_name}
                        </button>
                      );
                    })
                  )}
                </div>
              </div>

              {/* Select Departments */}
              <div className="space-y-2 pt-1">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                    Select Departments
                  </label>
                  <label className="flex items-center space-x-1.5 cursor-pointer text-[11px] text-slate-600 dark:text-slate-400 select-none">
                    <input
                      type="checkbox"
                      checked={isAllDepartmentsSelected}
                      onChange={toggleAllDepartments}
                      className="h-3.5 w-3.5 rounded border-slate-300 text-blue-600 focus:ring-blue-500 cursor-pointer"
                    />
                    <span>Select All</span>
                  </label>
                </div>

                <div className="flex flex-wrap gap-2 max-h-36 overflow-y-auto p-2 rounded-lg border border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/20">
                  {isDeptsLoading ? (
                    <span className="text-slate-400 italic">Loading departments...</span>
                  ) : departmentOptions.length === 0 ? (
                    <span className="text-slate-400 italic">No departments available.</span>
                  ) : (
                    departmentOptions.map((d) => {
                      const isSelected = selectedDepartmentIds.includes(d.dept_id);
                      return (
                        <button
                          key={d.dept_id}
                          type="button"
                          onClick={() => toggleDepartment(d.dept_id)}
                          className={`px-3 py-1 rounded-md text-xs font-medium border transition-all cursor-pointer ${
                            isSelected
                              ? "bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 border-blue-300 dark:border-blue-700 shadow-2xs"
                              : "bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 border-slate-200 dark:border-slate-700 hover:border-slate-300"
                          }`}
                        >
                          {d.dept_name}
                        </button>
                      );
                    })
                  )}
                </div>
              </div>

              {/* Add custom rights to the user */}
              <div className="pt-2">
                <label className="flex items-center space-x-2 cursor-pointer select-none">
                  <input
                    type="checkbox"
                    checked={formData.add_custom_rights || false}
                    onChange={(e) =>
                      setFormData({ ...formData, add_custom_rights: e.target.checked })
                    }
                    className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500 cursor-pointer"
                  />
                  <span className="text-xs font-medium text-slate-700 dark:text-slate-300">
                    Add custom rights to the user
                  </span>
                </label>
              </div>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}
