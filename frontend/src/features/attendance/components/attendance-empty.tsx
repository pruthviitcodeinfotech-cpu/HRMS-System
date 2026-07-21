"use client";

import React from "react";
import { FileQuestion } from "lucide-react";

interface AttendanceEmptyStateProps {
  title?: string;
  message?: string;
  onReset?: () => void;
}

export const AttendanceEmptyState: React.FC<AttendanceEmptyStateProps> = ({
  title = "No Attendance Records Found",
  message = "No attendance activity matches your selected date range or filter criteria.",
  onReset,
}) => {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-4 text-center bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-xs">
      <div className="w-12 h-12 rounded-full bg-slate-100 dark:bg-slate-800 flex items-center justify-center mb-3 text-slate-400 dark:text-slate-500">
        <FileQuestion className="h-6 w-6" />
      </div>
      <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100 mb-1">
        {title}
      </h3>
      <p className="text-xs text-slate-500 dark:text-slate-400 max-w-sm mb-4">
        {message}
      </p>
      {onReset && (
        <button
          type="button"
          onClick={onReset}
          className="px-3.5 py-1.5 text-xs font-semibold text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-950/40 hover:bg-blue-100 dark:hover:bg-blue-900/50 rounded-lg transition-colors cursor-pointer"
        >
          Reset Filters
        </button>
      )}
    </div>
  );
};
