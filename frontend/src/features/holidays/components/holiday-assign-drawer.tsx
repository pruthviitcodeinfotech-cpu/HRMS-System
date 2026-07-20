"use client";

import { useState, useCallback, useEffect } from "react";
import { X, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export interface HolidayTemplateOption {
  id: number;
  name: string;
}

interface HolidayAssignDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  selectedCount: number;
  templates?: HolidayTemplateOption[];
  onAssignSubmit?: (templateId: number) => Promise<void>;
  isSubmitting?: boolean;
}

export function HolidayAssignDrawer({
  isOpen,
  onClose,
  selectedCount,
  templates = [],
  onAssignSubmit,
  isSubmitting = false,
}: HolidayAssignDrawerProps) {
  const [chosenTemplateId, setChosenTemplateId] = useState<string>("");
  const [effectiveDate, setEffectiveDate] = useState<string>("");
  const [remarks, setRemarks] = useState<string>("");

  const handleClose = useCallback(() => {
    setChosenTemplateId("");
    setEffectiveDate("");
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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!chosenTemplateId) {
      toast.error("Please choose a holiday template.");
      return;
    }

    if (!effectiveDate) {
      toast.error("Please select an effective from date.");
      return;
    }

    if (onAssignSubmit) {
      await onAssignSubmit(Number(chosenTemplateId));
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
                Assign Holiday Template
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
            id="holiday-assign-drawer-form"
            onSubmit={handleSubmit}
            className="flex-1 overflow-y-auto p-6 space-y-5 text-xs"
          >
            {/* Choose Template */}
            <div>
              <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1.5">
                Choose Holiday Template<span className="text-red-500">*</span>
              </label>
              <select
                value={chosenTemplateId}
                onChange={(e) => setChosenTemplateId(e.target.value)}
                className="w-full h-9 px-3 text-xs bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-md focus:outline-none focus:ring-1 focus:ring-[#0B85C9] text-slate-700 dark:text-slate-300 cursor-pointer"
              >
                <option value="" disabled>
                  Choose Template
                </option>
                {templates.map((tmpl) => (
                  <option key={tmpl.id} value={tmpl.id}>
                    {tmpl.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Effective From Date */}
            <div>
              <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1.5">
                Effective From Date<span className="text-red-500">*</span>
              </label>
              <Input
                type="date"
                value={effectiveDate}
                onChange={(e) => setEffectiveDate(e.target.value)}
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
              form="holiday-assign-drawer-form"
              size="sm"
              disabled={isSubmitting}
              className="h-8 px-5 text-xs font-semibold bg-[#0B85C9] hover:bg-[#0974b0] text-white rounded shadow-2xs cursor-pointer disabled:opacity-50"
            >
              {isSubmitting ? (
                <span className="flex items-center gap-1.5">
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  Assigning...
                </span>
              ) : (
                "Assign Template"
              )}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
