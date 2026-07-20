"use client";

import { useCallback, useEffect } from "react";
import { X, Calendar } from "lucide-react";
import { Button } from "@/components/ui/button";
import { HolidayTemplate } from "../types";

interface HolidayViewDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  template: HolidayTemplate | null;
}

export function HolidayViewDrawer({ isOpen, onClose, template }: HolidayViewDrawerProps) {
  const handleClose = useCallback(() => {
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

  if (!isOpen || !template) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-hidden">
      {/* Backdrop Overlay */}
      <div
        className="fixed inset-0 bg-slate-900/50 backdrop-blur-xs transition-opacity duration-300"
        onClick={handleClose}
      />

      {/* Slide-over Drawer Panel */}
      <div className="fixed inset-y-0 right-0 max-w-full flex pl-10">
        <div className="w-screen max-w-md bg-white dark:bg-slate-900 border-l border-slate-200 dark:border-slate-800 shadow-2xl flex flex-col justify-between">
          {/* Header */}
          <div className="px-6 py-4 border-b border-slate-200 dark:border-slate-800 bg-[#EBF5FF] dark:bg-slate-950 flex items-start justify-between">
            <div>
              <h2 className="text-base font-semibold text-slate-800 dark:text-slate-100">
                {template.name}
              </h2>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5 font-medium">
                {template.holidayCount} Holidays Configured
              </p>
            </div>
            <button
              onClick={handleClose}
              className="p-1 rounded-md text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Body Content */}
          <div className="flex-1 overflow-y-auto p-6 space-y-4 text-xs">
            <div className="flex items-center justify-between text-slate-600 dark:text-slate-400 bg-slate-50 dark:bg-slate-950/60 p-3 rounded-md border border-slate-200 dark:border-slate-800">
              <div>
                <p className="text-[11px] font-medium text-slate-400">Assigned Employees</p>
                <p className="text-sm font-bold text-slate-800 dark:text-slate-100 mt-0.5">
                  {template.assignedEmployeesCount}
                </p>
              </div>
              <div>
                <p className="text-[11px] font-medium text-slate-400">Created On</p>
                <p className="text-xs font-semibold text-slate-700 dark:text-slate-300 mt-0.5">
                  {template.createdOn}
                </p>
              </div>
            </div>

            <div className="space-y-3 pt-2">
              <h3 className="text-xs font-bold text-slate-800 dark:text-slate-200 uppercase tracking-wider text-[11px]">
                Holiday Schedule
              </h3>

              <div className="space-y-2.5">
                {template.items.map((item, idx) => (
                  <div
                    key={item.id || idx}
                    className="p-3 bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-md flex items-center justify-between shadow-2xs"
                  >
                    <div className="flex items-center gap-3">
                      <div className="p-2 rounded bg-sky-50 dark:bg-sky-950/40 text-sky-600 dark:text-sky-400">
                        <Calendar className="h-4 w-4" />
                      </div>
                      <div>
                        <p className="font-semibold text-slate-800 dark:text-slate-100 text-xs">
                          {item.name}
                        </p>
                        <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">
                          {item.startDate === item.endDate
                            ? item.startDate
                            : `${item.startDate} to ${item.endDate}`}
                        </p>
                      </div>
                    </div>
                    {item.durationDays && (
                      <span className="text-[11px] font-medium px-2 py-0.5 bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 rounded">
                        {item.durationDays} {item.durationDays === 1 ? "day" : "days"}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Footer */}
          <div className="px-6 py-3.5 border-t border-slate-200 dark:border-slate-800 bg-[#EBF5FF] dark:bg-slate-950 flex items-center justify-end">
            <Button
              variant="outline"
              size="sm"
              onClick={handleClose}
              className="h-8 px-4 text-xs font-semibold bg-white dark:bg-slate-900 border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-200 hover:bg-slate-50 cursor-pointer shadow-2xs"
            >
              Close
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
