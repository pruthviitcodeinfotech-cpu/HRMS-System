"use client";

import React from "react";

interface AttendanceLoadingSkeletonProps {
  rows?: number;
}

export const AttendanceLoadingSkeleton: React.FC<AttendanceLoadingSkeletonProps> = ({
  rows = 8,
}) => {
  return (
    <div className="w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden shadow-xs animate-pulse">
      {/* Skeleton Header */}
      <div className="bg-slate-100 dark:bg-slate-800/60 px-4 py-3 border-b border-slate-200 dark:border-slate-800 grid grid-cols-11 gap-4 items-center">
        {Array.from({ length: 11 }).map((_, i) => (
          <div key={i} className="h-3 bg-slate-200 dark:bg-slate-700 rounded-xs" />
        ))}
      </div>

      {/* Skeleton Rows */}
      <div className="divide-y divide-slate-100 dark:divide-slate-800">
        {Array.from({ length: rows }).map((_, rowIndex) => (
          <div
            key={rowIndex}
            className="px-4 py-3.5 grid grid-cols-11 gap-4 items-center"
          >
            <div className="h-3 bg-slate-200 dark:bg-slate-700/80 rounded-xs w-3/4" />
            <div className="h-3 bg-slate-200 dark:bg-slate-700/80 rounded-xs w-5/6" />
            <div className="h-3 bg-slate-200 dark:bg-slate-700/80 rounded-xs w-2/3" />
            <div className="h-3 bg-slate-200 dark:bg-slate-700/80 rounded-xs w-3/4" />
            <div className="h-3 bg-slate-200 dark:bg-slate-700/80 rounded-xs w-1/2" />
            <div className="h-3 bg-slate-200 dark:bg-slate-700/80 rounded-xs w-1/2" />
            <div className="h-3 bg-slate-200 dark:bg-slate-700/80 rounded-xs w-2/3" />
            <div className="h-3 bg-slate-200 dark:bg-slate-700/80 rounded-xs w-2/3" />
            <div className="h-3 bg-slate-200 dark:bg-slate-700/80 rounded-xs w-1/2" />
            <div className="h-3 bg-slate-200 dark:bg-slate-700/80 rounded-xs w-1/3" />
            <div className="h-4 bg-slate-200 dark:bg-slate-700 rounded-xs w-14" />
          </div>
        ))}
      </div>
    </div>
  );
};
