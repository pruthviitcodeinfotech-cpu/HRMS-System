"use client";

import { useState } from "react";
import { ArrowUpDown, MoreVertical, Trash2, Edit2, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { LeaveTypeSchema } from "../types";

interface LeaveCreateTableProps {
  leaves: LeaveTypeSchema[];
  totalRecords: number;
  currentPage: number;
  pageSize: number;
  sortOrder: "asc" | "desc";
  isLoading?: boolean;
  isError?: boolean;
  onPageChange: (page: number) => void;
  onPageSizeChange: (size: number) => void;
  onToggleSort: () => void;
  onEditLeave: (leave: LeaveTypeSchema) => void;
  onDeleteLeave: (id: number) => void;
}

export function LeaveCreateTable({
  leaves,
  totalRecords,
  currentPage,
  pageSize,
  sortOrder,
  isLoading = false,
  isError = false,
  onPageChange,
  onPageSizeChange,
  onToggleSort,
  onEditLeave,
  onDeleteLeave,
}: LeaveCreateTableProps) {
  const [activeMenuId, setActiveMenuId] = useState<number | null>(null);

  const totalPages = Math.max(1, Math.ceil(totalRecords / pageSize));
  const startIndex = (currentPage - 1) * pageSize;

  const formatDate = (dateString?: string | null) => {
    if (!dateString) return "-";
    try {
      const d = new Date(dateString);
      if (isNaN(d.getTime())) return dateString;
      const day = String(d.getDate()).padStart(2, "0");
      const month = d.toLocaleString("en-US", { month: "short" });
      const year = d.getFullYear();
      return `${day} ${month} ${year}`;
    } catch {
      return dateString;
    }
  };

  const formatAutoAllocation = (item: LeaveTypeSchema) => {
    if (item.auto_allocation_count === null || item.auto_allocation_count === undefined || item.auto_allocation_count === 0) {
      return "-";
    }
    if (item.name.toUpperCase() === "LWP") return "-";
    const periodStr =
      item.allocation_frequency === "yearly"
        ? "Every Calendar Year"
        : "Every Month";
    return `${periodStr} ${item.auto_allocation_count}`;
  };

  const formatCarryForward = (item: LeaveTypeSchema) => {
    if (item.carry_forward_count === null || item.carry_forward_count === undefined || item.carry_forward_count === 0) {
      return "-";
    }
    if (item.name.toUpperCase() === "LWP") return "-";
    const periodStr =
      item.carry_forward_frequency === "yearly"
        ? "End Of Every Calendar Year"
        : "End Of Every Month";
    return `${periodStr} ${item.carry_forward_count}`;
  };

  return (
    <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg shadow-2xs overflow-hidden flex flex-col">
      {/* Table Container */}
      <div className="w-full overflow-x-auto min-h-[320px]">
        <table className="w-full text-left border-collapse text-xs select-none">
          {/* Table Header */}
          <thead className="bg-[#EBF5FF] dark:bg-slate-950 text-slate-700 dark:text-slate-300 font-semibold border-b border-slate-200 dark:border-slate-800">
            <tr>
              <th className="px-4 py-3 min-w-[160px]">
                <button
                  onClick={onToggleSort}
                  className="flex items-center gap-1.5 font-bold hover:text-sky-600 dark:hover:text-sky-400 transition-colors cursor-pointer"
                >
                  <span>Leave Name</span>
                  <ArrowUpDown className="h-3 w-3 text-slate-400" />
                  <span className="text-[10px] text-slate-400 uppercase">({sortOrder})</span>
                </button>
              </th>
              <th className="px-4 py-3 min-w-[120px] font-bold">Alias</th>
              <th className="px-4 py-3 min-w-[200px] font-bold">Auto Allocation</th>
              <th className="px-4 py-3 min-w-[220px] font-bold">Carry Forward</th>
              <th className="px-4 py-3 min-w-[140px] font-bold">Created On</th>
              <th className="px-4 py-3 w-16 text-center font-bold">Action</th>
            </tr>
          </thead>

          {/* Table Body */}
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60">
            {isLoading ? (
              Array.from({ length: 4 }).map((_, idx) => (
                <tr key={idx} className="animate-pulse">
                  <td className="px-4 py-3.5"><div className="h-3.5 w-24 bg-slate-200 dark:bg-slate-800 rounded" /></td>
                  <td className="px-4 py-3.5"><div className="h-3.5 w-12 bg-slate-200 dark:bg-slate-800 rounded" /></td>
                  <td className="px-4 py-3.5"><div className="h-3.5 w-36 bg-slate-200 dark:bg-slate-800 rounded" /></td>
                  <td className="px-4 py-3.5"><div className="h-3.5 w-40 bg-slate-200 dark:bg-slate-800 rounded" /></td>
                  <td className="px-4 py-3.5"><div className="h-3.5 w-20 bg-slate-200 dark:bg-slate-800 rounded" /></td>
                  <td className="px-4 py-3.5 text-center"><div className="h-4 w-4 bg-slate-200 dark:bg-slate-800 rounded mx-auto" /></td>
                </tr>
              ))
            ) : isError ? (
              <tr>
                <td colSpan={6} className="px-6 py-16 text-center text-red-500 dark:text-red-400">
                  <AlertCircle className="h-8 w-8 mx-auto mb-2 opacity-80" />
                  <p className="text-sm font-medium">Failed to load leave types from backend.</p>
                  <p className="text-xs mt-1 text-slate-500">Please verify your connection and try refreshing.</p>
                </td>
              </tr>
            ) : totalRecords === 0 ? (
              <tr>
                <td colSpan={6} className="px-6 py-16 text-center text-slate-400 dark:text-slate-500">
                  <p className="text-sm font-medium">No leaves configured yet.</p>
                  <p className="text-xs mt-1">Click &quot;Create New Leave&quot; button above to add a new leave policy.</p>
                </td>
              </tr>
            ) : (
              leaves.map((item) => (
                <tr
                  key={item.id}
                  className="hover:bg-slate-50/70 dark:hover:bg-slate-800/40 transition-colors text-slate-700 dark:text-slate-300"
                >
                  <td className="px-4 py-3.5 font-medium text-slate-800 dark:text-slate-100">
                    {item.name}
                  </td>
                  <td className="px-4 py-3.5 text-slate-600 dark:text-slate-400">
                    {item.alias || "-"}
                  </td>
                  <td className="px-4 py-3.5 text-slate-600 dark:text-slate-400">
                    {formatAutoAllocation(item)}
                  </td>
                  <td className="px-4 py-3.5 text-slate-600 dark:text-slate-400">
                    {formatCarryForward(item)}
                  </td>
                  <td className="px-4 py-3.5 text-slate-500 dark:text-slate-400">
                    {formatDate(item.created_at)}
                  </td>
                  <td className="px-4 py-3.5 text-center relative">
                    <button
                      onClick={() =>
                        setActiveMenuId((prev) => (prev === item.id ? null : item.id))
                      }
                      className="p-1 rounded hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 transition-colors cursor-pointer"
                    >
                      <MoreVertical className="h-4 w-4" />
                    </button>

                    {/* Context Action Menu */}
                    {activeMenuId === item.id && (
                      <div className="absolute right-4 top-10 z-30 w-32 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-md shadow-lg py-1 text-left">
                        <button
                          onClick={() => {
                            onEditLeave(item);
                            setActiveMenuId(null);
                          }}
                          className="w-full px-3 py-1.5 text-xs text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 flex items-center gap-2 cursor-pointer"
                        >
                          <Edit2 className="h-3.5 w-3.5 text-slate-400" />
                          <span>Edit</span>
                        </button>
                        <button
                          onClick={() => {
                            onDeleteLeave(item.id);
                            setActiveMenuId(null);
                          }}
                          className="w-full px-3 py-1.5 text-xs text-red-600 hover:bg-red-50 dark:hover:bg-red-950/30 flex items-center gap-2 cursor-pointer"
                        >
                          <Trash2 className="h-3.5 w-3.5 text-red-500" />
                          <span>Delete</span>
                        </button>
                      </div>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Footer */}
      <div className="px-4 py-3 border-t border-slate-200 dark:border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-slate-600 dark:text-slate-400">
        <div>
          Showing <span className="font-semibold text-slate-800 dark:text-slate-200">{totalRecords === 0 ? 0 : startIndex + 1}</span> to{" "}
          <span className="font-semibold text-slate-800 dark:text-slate-200">
            {Math.min(startIndex + pageSize, totalRecords)}
          </span>{" "}
          of <span className="font-semibold text-slate-800 dark:text-slate-200">{totalRecords}</span> Results
        </div>

        <div className="flex items-center gap-3">
          {/* 10 / Page Selector */}
          <select
            value={pageSize}
            onChange={(e) => {
              onPageSizeChange(Number(e.target.value));
            }}
            className="h-8 px-2 text-xs bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded cursor-pointer focus:outline-none"
          >
            <option value={10}>10 / Page</option>
            <option value={20}>20 / Page</option>
            <option value={50}>50 / Page</option>
          </select>

          {/* Page Buttons */}
          <div className="flex items-center gap-1">
            <Button
              variant="outline"
              size="sm"
              disabled={currentPage <= 1 || isLoading}
              onClick={() => onPageChange(Math.max(1, currentPage - 1))}
              className="h-8 px-3 text-xs bg-white dark:bg-slate-900 border-slate-300 dark:border-slate-700 cursor-pointer disabled:opacity-50"
            >
              Previous
            </Button>

            {Array.from({ length: totalPages }).map((_, idx) => {
              const pageNum = idx + 1;
              return (
                <button
                  key={pageNum}
                  onClick={() => onPageChange(pageNum)}
                  disabled={isLoading}
                  className={`h-8 w-8 text-xs font-medium rounded transition-colors cursor-pointer ${
                    currentPage === pageNum
                      ? "bg-[#0B85C9] text-white"
                      : "bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800"
                  }`}
                >
                  {pageNum}
                </button>
              );
            })}

            <Button
              variant="outline"
              size="sm"
              disabled={currentPage >= totalPages || isLoading}
              onClick={() => onPageChange(Math.min(totalPages, currentPage + 1))}
              className="h-8 px-3 text-xs bg-white dark:bg-slate-900 border-slate-300 dark:border-slate-700 cursor-pointer disabled:opacity-50"
            >
              Next
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
