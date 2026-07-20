"use client";

import { useState, useCallback, useEffect } from "react";
import { X } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";

interface LeaveBulkAssignDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  selectedCount: number;
  leaveOptions?: string[];
  onSuccess?: (leaveType: string, isAssigned: boolean) => void;
}

export function LeaveBulkAssignDrawer({
  isOpen,
  onClose,
  selectedCount,
  leaveOptions = ["Comp Off", "Casual Leave", "Sick Leave", "Paid Leave"],
  onSuccess,
}: LeaveBulkAssignDrawerProps) {
  const [chooseLeave, setChooseLeave] = useState<string>("");
  const [assignmentStatus, setAssignmentStatus] = useState<"assign" | "unassign">("assign");
  const [remarks, setRemarks] = useState<string>("");

  const handleClose = useCallback(() => {
    setChooseLeave("");
    setAssignmentStatus("assign");
    setRemarks("");
    onClose();
  }, [onClose]);

  // Handle ESC key press
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen) {
        handleClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, handleClose]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (!chooseLeave) {
      toast.error("Please choose a leave type.");
      return;
    }

    const isAssigned = assignmentStatus === "assign";
    toast.success(
      `Leave "${chooseLeave}" ${isAssigned ? "assigned to" : "unassigned from"} ${selectedCount} employee(s) successfully!`
    );

    if (onSuccess) {
      onSuccess(chooseLeave, isAssigned);
    }
    handleClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-hidden">
      {/* Backdrop overlay */}
      <div
        className="fixed inset-0 bg-slate-900/50 backdrop-blur-xs transition-opacity duration-300"
        onClick={handleClose}
      />

      {/* Slide-over Panel */}
      <div className="fixed inset-y-0 right-0 max-w-full flex pl-10">
        <div className="w-screen max-w-md bg-white dark:bg-slate-900 border-l border-slate-200 dark:border-slate-800 shadow-2xl flex flex-col justify-between">
          {/* Header */}
          <div className="px-6 py-4 border-b border-slate-200 dark:border-slate-800 bg-[#EBF5FF] dark:bg-slate-950 flex items-start justify-between">
            <div>
              <h2 className="text-base font-semibold text-slate-800 dark:text-slate-100">
                Bulk Assign Leave
              </h2>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5 font-medium">
                {selectedCount} Employees Selected
              </p>
            </div>
            <button
              onClick={handleClose}
              className="p-1 rounded-md text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Form Body */}
          <form
            id="bulk-assign-form"
            onSubmit={handleSubmit}
            className="flex-1 overflow-y-auto p-6 space-y-5 text-xs"
          >
            {/* Choose Leave */}
            <div>
              <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1.5">
                Choose Leave<span className="text-red-500">*</span>
              </label>
              <select
                value={chooseLeave}
                onChange={(e) => setChooseLeave(e.target.value)}
                className="w-full h-9 px-3 text-xs bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-md focus:outline-none focus:ring-1 focus:ring-[#0B85C9] text-slate-700 dark:text-slate-300 cursor-pointer"
              >
                <option value="" disabled>
                  Choose Leave
                </option>
                {leaveOptions.map((opt) => (
                  <option key={opt} value={opt}>
                    {opt}
                  </option>
                ))}
              </select>
            </div>

            {/* Assignment Status */}
            <div>
              <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1.5">
                Assignment Action<span className="text-red-500">*</span>
              </label>
              <div className="flex items-center gap-4 pt-1">
                <label className="flex items-center gap-2 text-xs text-slate-700 dark:text-slate-300 cursor-pointer">
                  <input
                    type="radio"
                    name="assignmentStatus"
                    value="assign"
                    checked={assignmentStatus === "assign"}
                    onChange={() => setAssignmentStatus("assign")}
                    className="h-4 w-4 text-[#0B85C9] focus:ring-[#0B85C9] border-slate-300"
                  />
                  Assign Leave
                </label>
                <label className="flex items-center gap-2 text-xs text-slate-700 dark:text-slate-300 cursor-pointer">
                  <input
                    type="radio"
                    name="assignmentStatus"
                    value="unassign"
                    checked={assignmentStatus === "unassign"}
                    onChange={() => setAssignmentStatus("unassign")}
                    className="h-4 w-4 text-[#0B85C9] focus:ring-[#0B85C9] border-slate-300"
                  />
                  Unassign Leave
                </label>
              </div>
            </div>

            {/* Remarks */}
            <div>
              <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1.5">
                Remarks (Optional)
              </label>
              <textarea
                rows={4}
                placeholder="Remarks"
                value={remarks}
                onChange={(e) => setRemarks(e.target.value)}
                className="w-full p-3 text-xs bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-md focus:outline-none focus:ring-1 focus:ring-[#0B85C9] placeholder:text-slate-400 text-slate-700 dark:text-slate-300 resize-none"
              />
            </div>
          </form>

          {/* Sticky Footer */}
          <div className="px-6 py-3.5 border-t border-slate-200 dark:border-slate-800 bg-[#EBF5FF] dark:bg-slate-950 flex items-center justify-end gap-3">
            <button
              type="button"
              onClick={handleClose}
              className="text-xs font-medium text-sky-600 dark:text-sky-400 hover:text-sky-700 cursor-pointer px-3 py-1.5"
            >
              Close
            </button>
            <Button
              type="submit"
              form="bulk-assign-form"
              size="sm"
              className="h-8 px-5 text-xs font-semibold bg-[#0B85C9] hover:bg-[#0974b0] text-white rounded shadow-2xs cursor-pointer"
            >
              Confirm Assignment
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
