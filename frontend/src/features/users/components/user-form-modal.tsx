"use client";

import { useState, useEffect } from "react";
import { X, Search, ChevronDown, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useEmployees } from "@/features/employees/hooks";
import { useRightsTemplates } from "../hooks/use-rights-templates";

export interface UserFormData {
  id?: number;
  employee_id?: number | null;
  name: string;
  email: string;
  mobile_number: string;
  password?: string;
  confirm_password?: string;
  is_super_admin: boolean;
  status: "Active" | "Inactive";
  template_id?: number | null;
  template_name?: string;
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

  const [formData, setFormData] = useState<UserFormData>({
    name: "",
    email: "",
    mobile_number: "",
    password: "",
    confirm_password: "",
    is_super_admin: false,
    status: "Active",
    template_id: null,
    employee_id: null,
  });

  const [empSearch, setEmpSearch] = useState("");
  const [isEmpDropdownOpen, setIsEmpDropdownOpen] = useState(false);

  // Live active employees lookup from API
  const { data: employeeData, isLoading: isEmpLoading } = useEmployees({
    status: "active",
    q: empSearch || undefined,
    page: 1,
    page_size: 20,
  });

  // Live rights templates lookup from API
  const { data: templateData } = useRightsTemplates({});
  const templatesList = templateData?.items || [];
  const employeesList = employeeData?.items || [];

  useEffect(() => {
    if (userToEdit) {
      setFormData({
        id: userToEdit.id,
        name: userToEdit.name || "",
        email: userToEdit.email || "",
        mobile_number: userToEdit.mobile_number || "",
        password: "",
        confirm_password: "",
        is_super_admin: userToEdit.is_super_admin ?? false,
        status: userToEdit.status || "Active",
        template_id: userToEdit.template_id ?? null,
        employee_id: userToEdit.employee_id ?? null,
      });
      setEmpSearch(userToEdit.name || "");
    } else {
      setFormData({
        name: "",
        email: "",
        mobile_number: "",
        password: "",
        confirm_password: "",
        is_super_admin: false,
        status: "Active",
        template_id: null,
        employee_id: null,
      });
      setEmpSearch("");
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
        className="w-full max-w-2xl rounded-xl bg-white dark:bg-slate-900 shadow-2xl border border-slate-200 dark:border-slate-800 overflow-hidden flex flex-col max-h-[90vh] animate-in zoom-in-95 duration-150"
        role="dialog"
        aria-modal="true"
        aria-labelledby="user-modal-title"
      >
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/50">
          <div>
            <h2
              id="user-modal-title"
              className="text-base font-bold text-slate-800 dark:text-slate-100"
            >
              {isEditing ? "Edit User" : "Create User"}
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              {isEditing
                ? "Update user account credentials and rights template"
                : "Add a new user account to the HRMS security system"}
            </p>
          </div>
          <button
            onClick={onClose}
            disabled={isLoading}
            aria-label="Close modal"
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-200/60 dark:hover:bg-slate-800 transition-colors cursor-pointer disabled:opacity-50"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Modal Body Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4 overflow-y-auto flex-1 text-xs">
          {/* Employee Searchable Dropdown */}
          <div className="relative">
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
              Select Employee
            </label>
            <div className="relative">
              <Input
                type="text"
                placeholder="Search active employee by name or code..."
                value={empSearch}
                onChange={(e) => {
                  setEmpSearch(e.target.value);
                  setIsEmpDropdownOpen(true);
                }}
                onFocus={() => setIsEmpDropdownOpen(true)}
                className="pr-8 text-xs h-9"
              />
              {isEmpLoading ? (
                <Loader2 className="h-4 w-4 text-slate-400 absolute right-2.5 top-2.5 animate-spin" />
              ) : (
                <Search className="h-4 w-4 text-slate-400 absolute right-2.5 top-2.5 pointer-events-none" />
              )}
            </div>

            {/* Live Searchable Employee Dropdown */}
            {isEmpDropdownOpen && employeesList.length > 0 && (
              <div className="absolute left-0 right-0 top-full mt-1 z-30 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-md shadow-lg max-h-48 overflow-y-auto py-1">
                {employeesList.map((emp) => (
                  <button
                    key={emp.employee_id}
                    type="button"
                    onClick={() => {
                      setFormData({
                        ...formData,
                        employee_id: emp.employee_id,
                        name: emp.employee_name,
                        email: emp.email || formData.email,
                        mobile_number: emp.mobile_number || formData.mobile_number,
                      });
                      setEmpSearch(`${emp.employee_name} (${emp.employee_code})`);
                      setIsEmpDropdownOpen(false);
                    }}
                    className="w-full flex items-center justify-between px-3 py-2 text-xs text-left hover:bg-slate-50 dark:hover:bg-slate-800 cursor-pointer"
                  >
                    <div>
                      <span className="font-semibold text-slate-800 dark:text-slate-100">
                        {emp.employee_name}
                      </span>
                      <span className="text-slate-400 ml-2">({emp.employee_code})</span>
                    </div>
                    <span className="text-[10px] text-blue-600 bg-blue-50 px-2 py-0.5 rounded font-medium">
                      {emp.department_name || "Employee"}
                    </span>
                  </button>
                ))}
              </div>
            )}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {/* User Name */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                User Name / Full Name <span className="text-red-500">*</span>
              </label>
              <Input
                type="text"
                placeholder="Enter user name"
                required
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="text-xs h-9"
              />
            </div>

            {/* Email Address */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Email Address <span className="text-red-500">*</span>
              </label>
              <Input
                type="email"
                placeholder="Enter email address"
                required
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                className="text-xs h-9"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {/* Mobile Number */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Mobile Number <span className="text-red-500">*</span>
              </label>
              <Input
                type="tel"
                placeholder="Enter mobile number"
                required
                value={formData.mobile_number}
                onChange={(e) =>
                  setFormData({ ...formData, mobile_number: e.target.value })
                }
                className="text-xs h-9"
              />
            </div>

            {/* Rights Template Dropdown */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Rights Template
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
                  className="w-full appearance-none bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-md px-3 py-2 pr-8 text-xs font-medium text-slate-700 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 h-9 cursor-pointer"
                >
                  <option value="">Select Rights Template</option>
                  {templatesList.map((tmpl) => (
                    <option key={tmpl.id} value={tmpl.id}>
                      {tmpl.name}
                    </option>
                  ))}
                </select>
                <ChevronDown className="h-3.5 w-3.5 text-slate-500 absolute right-2.5 top-3 pointer-events-none" />
              </div>
            </div>
          </div>

          {/* Password & Confirm Password */}
          {!isEditing && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Password <span className="text-red-500">*</span>
                </label>
                <Input
                  type="password"
                  placeholder="Enter password"
                  required={!isEditing}
                  value={formData.password}
                  onChange={(e) =>
                    setFormData({ ...formData, password: e.target.value })
                  }
                  className="text-xs h-9"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Confirm Password <span className="text-red-500">*</span>
                </label>
                <Input
                  type="password"
                  placeholder="Confirm password"
                  required={!isEditing}
                  value={formData.confirm_password}
                  onChange={(e) =>
                    setFormData({ ...formData, confirm_password: e.target.value })
                  }
                  className="text-xs h-9"
                />
              </div>
            </div>
          )}

          {/* Super Admin Toggle & Status */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2 border-t border-slate-100 dark:border-slate-800">
            {/* Super Admin Toggle */}
            <div className="flex items-center justify-between p-3 border border-slate-200 dark:border-slate-800 rounded-lg bg-slate-50/60 dark:bg-slate-800/40">
              <div>
                <span className="block font-semibold text-slate-800 dark:text-slate-200">
                  Super Admin
                </span>
                <span className="block text-[11px] text-slate-500">
                  Grant full administrative access
                </span>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={formData.is_super_admin}
                  onChange={(e) =>
                    setFormData({ ...formData, is_super_admin: e.target.checked })
                  }
                  className="sr-only peer"
                />
                <div className="w-9 h-5 bg-slate-200 peer-focus:outline-none rounded-full peer dark:bg-slate-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all dark:after:border-slate-600 peer-checked:bg-blue-600"></div>
              </label>
            </div>

            {/* Account Status Radio/Select */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Account Status <span className="text-red-500">*</span>
              </label>
              <div className="flex items-center space-x-3 h-11">
                <label className="flex items-center space-x-2 cursor-pointer">
                  <input
                    type="radio"
                    name="status"
                    value="Active"
                    checked={formData.status === "Active"}
                    onChange={() => setFormData({ ...formData, status: "Active" })}
                    className="h-3.5 w-3.5 text-blue-600"
                  />
                  <span className="text-xs text-slate-700 dark:text-slate-300 font-medium">
                    Active
                  </span>
                </label>

                <label className="flex items-center space-x-2 cursor-pointer">
                  <input
                    type="radio"
                    name="status"
                    value="Inactive"
                    checked={formData.status === "Inactive"}
                    onChange={() => setFormData({ ...formData, status: "Inactive" })}
                    className="h-3.5 w-3.5 text-blue-600"
                  />
                  <span className="text-xs text-slate-700 dark:text-slate-300 font-medium">
                    Inactive
                  </span>
                </label>
              </div>
            </div>
          </div>

          {/* Footer Buttons */}
          <div className="flex items-center justify-end space-x-3 pt-4 border-t border-slate-100 dark:border-slate-800">
            <Button
              type="button"
              variant="outline"
              onClick={onClose}
              disabled={isLoading}
              className="text-xs font-semibold h-9 px-4 cursor-pointer"
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={isLoading}
              className="bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold h-9 px-5 shadow-2xs cursor-pointer flex items-center space-x-1.5"
            >
              {isLoading && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
              <span>{isEditing ? "Save Changes" : "Create User"}</span>
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
