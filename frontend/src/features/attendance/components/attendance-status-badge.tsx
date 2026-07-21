"use client";

import React from "react";
import { AlertTriangle } from "lucide-react";
import { AttendanceStatus } from "../types/attendance";

interface AttendanceStatusBadgeProps {
  status: AttendanceStatus;
  hasAnomaly?: boolean;
}

export const AttendanceStatusBadge: React.FC<AttendanceStatusBadgeProps> = ({
  status,
  hasAnomaly = false,
}) => {
  const getBadgeStyle = (statusVal: AttendanceStatus): string => {
    switch (statusVal) {
      case "FD":
      case "Present":
        return "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-400 border-emerald-200/60 dark:border-emerald-800/40";
      case "Absent":
        return "bg-rose-50 text-rose-700 dark:bg-rose-950/40 dark:text-rose-400 border-rose-200/60 dark:border-rose-800/40";
      case "Half Day":
        return "bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-400 border-amber-200/60 dark:border-amber-800/40";
      case "Late":
      case "Early Exit":
      case "Missed Punch":
        return "bg-orange-50 text-orange-700 dark:bg-orange-950/40 dark:text-orange-400 border-orange-200/60 dark:border-orange-800/40";
      case "Weekly Off":
        return "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400 border-slate-200 dark:border-slate-700";
      case "Holiday":
        return "bg-purple-50 text-purple-700 dark:bg-purple-950/40 dark:text-purple-400 border-purple-200/60 dark:border-purple-800/40";
      case "Leave":
        return "bg-sky-50 text-sky-700 dark:bg-sky-950/40 dark:text-sky-400 border-sky-200/60 dark:border-sky-800/40";
      default:
        return "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300 border-slate-200 dark:border-slate-700";
    }
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-xs font-semibold border transition-colors ${getBadgeStyle(
        status
      )}`}
    >
      <span>{status}</span>
      {(hasAnomaly || status === "Absent") && (
        <AlertTriangle className="h-3.5 w-3.5 text-amber-500 fill-amber-500/20 shrink-0" />
      )}
    </span>
  );
};
