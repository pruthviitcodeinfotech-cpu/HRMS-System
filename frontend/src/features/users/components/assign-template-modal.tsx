"use client";

import React, { useState, useMemo } from "react";
import { X, Search, ShieldCheck, Users, Check, AlertCircle, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useRightsTemplates } from "../hooks/use-rights-templates";
import { useUsers, useBulkAssignRole } from "../hooks/use-users";

interface AssignTemplateModalProps {
  isOpen: boolean;
  onClose: () => void;
  initialTemplateId?: number | null;
}

export function AssignTemplateModal({
  isOpen,
  onClose,
  initialTemplateId,
}: AssignTemplateModalProps) {
  // Query active users (Master Data Reuse - User / RBAC Module)
  const { data: usersData, isLoading: isUsersLoading } = useUsers({
    is_active: true,
    page: 1,
    page_size: 200,
  });

  // Query active templates (Master Data Reuse)
  const { data: templatesData } = useRightsTemplates({
    page: 1,
    page_size: 100,
  });

  const bulkAssignMutation = useBulkAssignRole();

  // Selected State
  const [selectedTemplateId, setSelectedTemplateId] = useState<number | null>(
    initialTemplateId || null
  );
  const [selectedUserIds, setSelectedUserIds] = useState<number[]>([]);
  const [searchUserQuery, setSearchUserQuery] = useState("");
  const [showConfirm, setShowConfirm] = useState(false);

  // Sync initial template when prop changes
  React.useEffect(() => {
    if (initialTemplateId) {
      setSelectedTemplateId(initialTemplateId);
    }
  }, [initialTemplateId]);

  const activeUsers = usersData?.items || [];
  const activeTemplates = templatesData?.items || [];

  const selectedTemplateObj = useMemo(() => {
    return activeTemplates.find((t) => t.id === selectedTemplateId);
  }, [activeTemplates, selectedTemplateId]);

  // Filter users by search
  const filteredUsers = useMemo(() => {
    if (!searchUserQuery.trim()) return activeUsers;
    const query = searchUserQuery.toLowerCase();
    return activeUsers.filter(
      (u) =>
        u.name.toLowerCase().includes(query) ||
        (u.email && u.email.toLowerCase().includes(query)) ||
        (u.mobile_number && u.mobile_number.includes(query))
    );
  }, [activeUsers, searchUserQuery]);

  const toggleUserSelection = (userId: number) => {
    setSelectedUserIds((prev) =>
      prev.includes(userId) ? prev.filter((id) => id !== userId) : [...prev, userId]
    );
  };

  const toggleSelectAllFiltered = () => {
    const filteredIds = filteredUsers.map((u) => u.id);
    const allSelected = filteredIds.every((id) => selectedUserIds.includes(id));

    if (allSelected) {
      setSelectedUserIds((prev) => prev.filter((id) => !filteredIds.includes(id)));
    } else {
      setSelectedUserIds((prev) => Array.from(new Set([...prev, ...filteredIds])));
    }
  };

  if (!isOpen) return null;

  const handleConfirmAssign = () => {
    if (!selectedTemplateId || selectedUserIds.length === 0) return;
    bulkAssignMutation.mutate(
      {
        userIds: selectedUserIds,
        templateId: selectedTemplateId,
      },
      {
        onSuccess: () => {
          setShowConfirm(false);
          setSelectedUserIds([]);
          onClose();
        },
      }
    );
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4 animate-in fade-in duration-200">
      <div className="w-full max-w-2xl rounded-xl bg-white dark:bg-slate-900 shadow-2xl border border-slate-200 dark:border-slate-800 overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 dark:border-slate-800">
          <div className="flex items-center space-x-2.5">
            <ShieldCheck className="h-5 w-5 text-blue-600" />
            <h2 className="text-base font-semibold text-slate-800 dark:text-slate-100">
              Assign Rights Template to Users
            </h2>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="p-6 space-y-5 overflow-y-auto flex-1 text-xs">
          {/* Step 1: Select Rights Template */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
              Select Rights Template <span className="text-red-500">*</span>
            </label>
            <select
              value={selectedTemplateId || ""}
              onChange={(e) => setSelectedTemplateId(Number(e.target.value) || null)}
              className="w-full h-9 rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 text-xs text-slate-700 dark:text-slate-200 focus:outline-none cursor-pointer"
            >
              <option value="">-- Choose Rights Template --</option>
              {activeTemplates.map((template) => (
                <option key={template.id} value={template.id}>
                  {template.name} ({template.assigned_user_count || 0} assigned)
                </option>
              ))}
            </select>
          </div>

          {/* Step 2: User Multi-selection */}
          <div className="space-y-3 pt-2 border-t border-slate-100 dark:border-slate-800">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 flex items-center space-x-1.5">
                <Users className="h-4 w-4 text-blue-600" />
                <span>Select Users ({selectedUserIds.length} Selected)</span>
              </label>

              <div className="flex items-center space-x-2">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={toggleSelectAllFiltered}
                  className="text-[11px] h-7 px-2.5"
                >
                  {filteredUsers.length > 0 &&
                  filteredUsers.every((u) => selectedUserIds.includes(u.id))
                    ? "Deselect All"
                    : "Select All Filtered"}
                </Button>
              </div>
            </div>

            {/* User Search Bar */}
            <div className="relative">
              <Search className="h-3.5 w-3.5 text-slate-400 absolute left-3 top-2.5 pointer-events-none" />
              <Input
                type="text"
                placeholder="Search users by name, email, or mobile..."
                value={searchUserQuery}
                onChange={(e) => setSearchUserQuery(e.target.value)}
                className="pl-8 text-xs bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-700 h-8 rounded-md"
              />
            </div>

            {/* User List */}
            <div className="border border-slate-200 dark:border-slate-800 rounded-lg max-h-56 overflow-y-auto divide-y divide-slate-100 dark:divide-slate-800 bg-slate-50/50 dark:bg-slate-800/20">
              {isUsersLoading ? (
                <div className="py-8 flex justify-center items-center text-slate-400 space-x-2">
                  <Loader2 className="h-4 w-4 animate-spin text-blue-600" />
                  <span>Loading users list...</span>
                </div>
              ) : filteredUsers.length === 0 ? (
                <div className="py-6 text-center text-slate-400 italic">
                  No active users found matching query.
                </div>
              ) : (
                filteredUsers.map((u) => {
                  const isChecked = selectedUserIds.includes(u.id);
                  return (
                    <label
                      key={u.id}
                      className="flex items-center justify-between p-2.5 px-3 hover:bg-white dark:hover:bg-slate-800 cursor-pointer transition-colors"
                    >
                      <div className="flex items-center space-x-3">
                        <input
                          type="checkbox"
                          checked={isChecked}
                          onChange={() => toggleUserSelection(u.id)}
                          className="h-4 w-4 rounded border-slate-300 dark:border-slate-700 text-blue-600 focus:ring-blue-500 cursor-pointer"
                        />
                        <div>
                          <span className="font-semibold text-slate-800 dark:text-slate-200 block">
                            {u.name}{" "}
                            <span className="text-slate-400 font-normal">({u.email})</span>
                          </span>
                          <span className="text-[10px] text-slate-400 block">
                            Template: {u.template ? u.template.name : "None"} • Phone: {u.mobile_number}
                          </span>
                        </div>
                      </div>

                      {isChecked && <Check className="h-4 w-4 text-blue-600" />}
                    </label>
                  );
                })
              )}
            </div>
          </div>
        </div>

        {/* Footer Actions */}
        <div className="px-6 py-4 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between bg-slate-50/50 dark:bg-slate-900/50">
          <div className="text-xs text-slate-500">
            {selectedTemplateObj ? (
              <span>
                Assigning template <strong className="text-slate-800 dark:text-slate-200">"{selectedTemplateObj.name}"</strong> to <strong className="text-blue-600 font-bold">{selectedUserIds.length}</strong> user(s)
              </span>
            ) : (
              <span className="italic">Please select a rights template to continue.</span>
            )}
          </div>

          <div className="flex items-center space-x-3">
            <Button
              type="button"
              variant="outline"
              onClick={onClose}
              className="text-xs h-9 px-4 border-slate-200 dark:border-slate-700"
            >
              Cancel
            </Button>
            <Button
              type="button"
              disabled={!selectedTemplateId || selectedUserIds.length === 0}
              onClick={() => setShowConfirm(true)}
              className="text-xs h-9 px-5 bg-blue-600 hover:bg-blue-700 text-white font-semibold shadow-2xs"
            >
              Assign Template
            </Button>
          </div>
        </div>
      </div>

      {/* Assignment Confirmation Dialog */}
      {showConfirm && (
        <div className="fixed inset-0 z-60 flex items-center justify-center bg-black/50 backdrop-blur-xs p-4 animate-in fade-in duration-150">
          <div className="w-full max-w-md rounded-xl bg-white dark:bg-slate-900 shadow-2xl border border-slate-200 dark:border-slate-800 p-6 space-y-4 text-xs">
            <div className="flex items-center space-x-3 text-blue-600">
              <AlertCircle className="h-6 w-6 shrink-0" />
              <h3 className="text-base font-semibold text-slate-800 dark:text-slate-100">
                Confirm Assignment
              </h3>
            </div>

            <p className="text-slate-600 dark:text-slate-400">
              Are you sure you want to assign Rights Template{" "}
              <strong className="text-slate-800 dark:text-slate-200">
                "{selectedTemplateObj?.name}"
              </strong>{" "}
              to <strong className="text-blue-600">{selectedUserIds.length}</strong> selected user(s)? Existing permissions will be updated immediately.
            </p>

            <div className="flex justify-end space-x-2 pt-3 border-t border-slate-100 dark:border-slate-800">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowConfirm(false)}
              >
                Cancel
              </Button>
              <Button
                size="sm"
                disabled={bulkAssignMutation.isPending}
                onClick={handleConfirmAssign}
                className="bg-blue-600 hover:bg-blue-700 text-white"
              >
                {bulkAssignMutation.isPending ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  "Confirm & Assign"
                )}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
