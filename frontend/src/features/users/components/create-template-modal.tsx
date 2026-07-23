"use client";

import React, { useState } from "react";
import { X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

interface CreateTemplateModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const MODULE_PERMISSIONS = [
  { id: "employees", name: "Employees" },
  { id: "shifts", name: "Manage Shifts" },
  { id: "leaves", name: "Leaves & Holidays" },
  { id: "approvals", name: "Approval Requests" },
  { id: "payroll", name: "Payroll" },
  { id: "reports", name: "Reports" },
];

export function CreateTemplateModal({ isOpen, onClose }: CreateTemplateModalProps) {
  const [templateName, setTemplateName] = useState("");
  const [selectedPermissions, setSelectedPermissions] = useState<Record<string, boolean>>({
    employees: true,
    leaves: true,
  });

  if (!isOpen) return null;

  const togglePermission = (id: string) => {
    setSelectedPermissions((prev) => ({
      ...prev,
      [id]: !prev[id],
    }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4 animate-in fade-in duration-200">
      <div className="w-full max-w-xl rounded-xl bg-white dark:bg-slate-900 shadow-2xl border border-slate-200 dark:border-slate-800 overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 dark:border-slate-800">
          <h2 className="text-base font-semibold text-slate-800 dark:text-slate-100">
            Create Rights Template
          </h2>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Body Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-5 overflow-y-auto flex-1">
          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
              Template Name <span className="text-red-500">*</span>
            </label>
            <Input
              type="text"
              placeholder="e.g. HR Manager, Shift Supervisor"
              value={templateName}
              onChange={(e) => setTemplateName(e.target.value)}
              className="text-xs"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-2">
              Module Access & Permissions
            </label>
            <div className="space-y-2 border border-slate-200 dark:border-slate-800 rounded-lg p-3 bg-slate-50/50 dark:bg-slate-800/30">
              {MODULE_PERMISSIONS.map((mod) => (
                <label
                  key={mod.id}
                  className="flex items-center justify-between p-2 rounded-md hover:bg-white dark:hover:bg-slate-800 border border-transparent hover:border-slate-200 dark:hover:border-slate-700 cursor-pointer transition-all"
                >
                  <span className="text-xs font-medium text-slate-700 dark:text-slate-200">
                    {mod.name}
                  </span>
                  <input
                    type="checkbox"
                    checked={!!selectedPermissions[mod.id]}
                    onChange={() => togglePermission(mod.id)}
                    className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500 cursor-pointer"
                  />
                </label>
              ))}
            </div>
          </div>

          {/* Footer Buttons */}
          <div className="flex items-center justify-end space-x-3 pt-4 border-t border-slate-100 dark:border-slate-800">
            <Button
              type="button"
              variant="outline"
              onClick={onClose}
              className="text-xs h-9 px-4 border-slate-200 dark:border-slate-700"
            >
              Cancel
            </Button>
            <Button
              type="submit"
              className="text-xs h-9 px-4 bg-blue-600 hover:bg-blue-700 text-white font-medium"
            >
              Save Template
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
