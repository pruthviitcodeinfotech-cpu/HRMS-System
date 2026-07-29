"use client";

import { useState, useCallback, useEffect } from "react";
import { X } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAssignLeaveTypes, useAdjustLeaveBalance } from "../hooks";

interface LeaveBulkUpdateDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  selectedCount: number;
  selectedEmployeeIds?: number[];
  leaveTypes?: Array<{ id: number; name: string }>;
  leaveOptions?: string[];
  onSuccess?: (leaveType: string, balanceCount: number) => void;
}

export function LeaveBulkUpdateDrawer({
  isOpen,
  onClose,
  selectedCount,
  selectedEmployeeIds = [],
  leaveTypes = [],
  leaveOptions = ["Comp Off", "Casual Leave", "Sick Leave", "Paid Leave"],
  onSuccess,
}: LeaveBulkUpdateDrawerProps) {
  const [chooseLeave, setChooseLeave] = useState<string>("");
  const [balanceCount, setBalanceCount] = useState<string>("");
  const [remarks, setRemarks] = useState<string>("");
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  const assignMutation = useAssignLeaveTypes();
  const adjustMutation = useAdjustLeaveBalance();

  const handleClose = useCallback(() => {
    setChooseLeave("");
    setBalanceCount("");
    setRemarks("");
    setIsSubmitting(false);
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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!chooseLeave) {
      toast.error("Please choose a leave type.");
      return;
    }

    if (balanceCount === "" || isNaN(Number(balanceCount))) {
      toast.error("Please enter a valid balance count.");
      return;
    }

    if (!selectedEmployeeIds || selectedEmployeeIds.length === 0) {
      toast.error("Please select at least one employee for bulk leave update.");
      return;
    }

    const countNum = Number(balanceCount);
    const matchedType = leaveTypes.find((lt) => lt.name === chooseLeave);
    const leaveTypeId = matchedType?.id;

    if (!leaveTypeId) {
      toast.error(`Leave type "${chooseLeave}" not found.`);
      return;
    }

    setIsSubmitting(true);
    try {
      // 1. Assign leave type to target employees with allocated days
      await assignMutation.mutateAsync({
        employee_ids: selectedEmployeeIds,
        leave_type_ids: [leaveTypeId],
        allocated_days: countNum,
        is_assigned: true,
      });

      // 2. Adjust closing balance to countNum for each target employee
      await Promise.all(
        selectedEmployeeIds.map((empId) =>
          adjustMutation.mutateAsync({
            employeeId: empId,
            data: {
              leave_type_id: leaveTypeId,
              new_balance: countNum,
              cycle_year: new Date().getFullYear(),
              remarks: remarks.trim() || `Bulk leave update to ${countNum}`,
            },
          })
        )
      );

      toast.success(
        `Leave balance for "${chooseLeave}" updated to ${countNum} for ${selectedEmployeeIds.length} employee(s) successfully!`
      );

      if (onSuccess) {
        onSuccess(chooseLeave, countNum);
      }
      handleClose();
    } catch (err: unknown) {
      console.error("Bulk leave update failed:", err);
      const msg = (err as { message?: string })?.message || "Failed to update leave balances.";
      toast.error(msg);
    } finally {
      setIsSubmitting(false);
    }
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
                Bulk Leave Update
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
            id="bulk-update-form"
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

            {/* Leave Balance Count */}
            <div>
              <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1.5">
                New Leave Balance Count<span className="text-red-500">*</span>
              </label>
              <Input
                type="number"
                step="0.5"
                placeholder="Enter Leave Count (e.g. 10)"
                value={balanceCount}
                onChange={(e) => setBalanceCount(e.target.value)}
                className="h-9 text-xs bg-white dark:bg-slate-950 border-slate-300 dark:border-slate-700 focus:ring-[#0B85C9]"
              />
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
              form="bulk-update-form"
              disabled={isSubmitting}
              size="sm"
              className="h-8 px-5 text-xs font-semibold bg-[#0B85C9] hover:bg-[#0974b0] text-white rounded shadow-2xs cursor-pointer disabled:opacity-50"
            >
              {isSubmitting ? "Updating..." : "Update Leave Balance"}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
