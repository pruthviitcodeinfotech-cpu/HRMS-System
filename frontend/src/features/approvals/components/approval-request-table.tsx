"use client";

import React, { useState, useMemo } from "react";
import {
  Palmtree,
  Calendar,
  ChevronDown,
  ChevronUp,
  X,
  Check,
  ArrowUpDown,
  Inbox,
  CheckCheck,
  XCircle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ApprovalRequest } from "../types";

interface ApprovalRequestTableProps {
  requests: ApprovalRequest[];
  isLoading?: boolean;
  onViewDetails?: (request: ApprovalRequest) => void;
  onApprove: (request: ApprovalRequest) => void;
  onReject: (request: ApprovalRequest) => void;
  // Server-side & Bulk controls
  totalRecords?: number;
  currentPage?: number;
  pageSize?: number;
  onPageChange?: (page: number) => void;
  onPageSizeChange?: (size: number) => void;
  onSortChange?: (field: "type" | "employeeName" | "submittedDate") => void;
  onBulkApprove?: (selectedIds: string[]) => void;
  onBulkReject?: (selectedIds: string[]) => void;
}

export function ApprovalRequestTable({
  requests,
  isLoading = false,
  onViewDetails,
  onApprove,
  onReject,
  totalRecords: externalTotalRecords,
  currentPage: externalCurrentPage,
  pageSize: externalPageSize,
  onPageChange,
  onPageSizeChange,
  onSortChange,
  onBulkApprove,
  onBulkReject,
}: ApprovalRequestTableProps) {
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [expandedRowIds, setExpandedRowIds] = useState<string[]>([]);
  const [localSortField, setLocalSortField] = useState<"type" | "employeeName" | "submittedDate">("submittedDate");
  const [localSortOrder, setLocalSortOrder] = useState<"asc" | "desc">("desc");
  const [localCurrentPage, setLocalCurrentPage] = useState<number>(1);
  const [localPageSize, setLocalPageSize] = useState<number>(10);

  const currentPage = externalCurrentPage ?? localCurrentPage;
  const pageSize = externalPageSize ?? localPageSize;

  // Sorting
  const sortedRequests = useMemo(() => {
    if (onSortChange) return requests; // Managed server-side
    return [...requests].sort((a, b) => {
      let valA = "";
      let valB = "";

      if (localSortField === "type") {
        valA = a.type;
        valB = b.type;
      } else if (localSortField === "employeeName") {
        valA = a.employeeName;
        valB = b.employeeName;
      } else {
        valA = a.submittedDate;
        valB = b.submittedDate;
      }

      valA = valA.toLowerCase();
      valB = valB.toLowerCase();

      if (valA < valB) return localSortOrder === "asc" ? -1 : 1;
      if (valA > valB) return localSortOrder === "asc" ? 1 : -1;
      return 0;
    });
  }, [requests, localSortField, localSortOrder, onSortChange]);

  const handleSort = (field: "type" | "employeeName" | "submittedDate") => {
    if (onSortChange) {
      onSortChange(field);
    } else {
      if (localSortField === field) {
        setLocalSortOrder((prev) => (prev === "asc" ? "desc" : "asc"));
      } else {
        setLocalSortField(field);
        setLocalSortOrder("asc");
      }
    }
  };

  // Pagination
  const totalRecords = externalTotalRecords ?? sortedRequests.length;
  const totalPages = Math.max(1, Math.ceil(totalRecords / pageSize));
  const startIndex = (currentPage - 1) * pageSize;
  const paginatedRequests = useMemo(() => {
    if (externalTotalRecords !== undefined) return requests;
    return sortedRequests.slice(startIndex, startIndex + pageSize);
  }, [requests, sortedRequests, startIndex, pageSize, externalTotalRecords]);

  // Checkbox Selection
  const isAllSelected =
    paginatedRequests.length > 0 &&
    paginatedRequests.every((req) => selectedIds.includes(req.id));

  const toggleSelectAll = () => {
    if (isAllSelected) {
      const pageIds = paginatedRequests.map((r) => r.id);
      setSelectedIds(selectedIds.filter((id) => !pageIds.includes(id)));
    } else {
      const pageIds = paginatedRequests.map((r) => r.id);
      setSelectedIds(Array.from(new Set([...selectedIds, ...pageIds])));
    }
  };

  const toggleSelectRow = (id: string) => {
    if (selectedIds.includes(id)) {
      setSelectedIds(selectedIds.filter((item) => item !== id));
    } else {
      setSelectedIds([...selectedIds, id]);
    }
  };

  const toggleRowExpand = (id: string) => {
    setExpandedRowIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  const handlePageChange = (newPage: number) => {
    if (onPageChange) {
      onPageChange(newPage);
    } else {
      setLocalCurrentPage(newPage);
    }
  };

  const handlePageSizeChange = (newSize: number) => {
    if (onPageSizeChange) {
      onPageSizeChange(newSize);
    } else {
      setLocalPageSize(newSize);
      setLocalCurrentPage(1);
    }
  };

  return (
    <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg shadow-2xs overflow-hidden flex flex-col">
      {/* Bulk Action Header Bar (when items are selected) */}
      {selectedIds.length > 0 && (
        <div className="bg-sky-50 dark:bg-sky-950/60 px-4 py-2.5 border-b border-sky-200 dark:border-sky-800/80 flex items-center justify-between transition-all">
          <div className="text-xs font-semibold text-sky-800 dark:text-sky-200 flex items-center gap-2">
            <span>{selectedIds.length} request(s) selected</span>
          </div>
          <div className="flex items-center gap-2">
            {onBulkReject && (
              <Button
                size="sm"
                variant="destructive"
                onClick={() => {
                  onBulkReject(selectedIds);
                  setSelectedIds([]);
                }}
                className="h-7 px-3 text-xs font-semibold flex items-center gap-1 cursor-pointer"
              >
                <XCircle className="h-3.5 w-3.5" />
                <span>Bulk Reject</span>
              </Button>
            )}
            {onBulkApprove && (
              <Button
                size="sm"
                onClick={() => {
                  onBulkApprove(selectedIds);
                  setSelectedIds([]);
                }}
                className="h-7 px-3 text-xs font-semibold bg-[#0B85C9] hover:bg-[#0974b0] text-white flex items-center gap-1 cursor-pointer"
              >
                <CheckCheck className="h-3.5 w-3.5" />
                <span>Bulk Approve</span>
              </Button>
            )}
          </div>
        </div>
      )}

      {/* Table Scrollable Container */}
      <div className="w-full overflow-x-auto min-h-[380px]">
        <table className="w-full text-left border-collapse text-xs select-none">
          {/* Table Header */}
          <thead className="bg-[#F8FAFC] dark:bg-slate-950 text-slate-700 dark:text-slate-300 font-semibold border-b border-slate-200 dark:border-slate-800">
            <tr>
              <th className="px-4 py-3 w-10 text-center">
                <input
                  type="checkbox"
                  checked={isAllSelected}
                  onChange={toggleSelectAll}
                  className="h-4 w-4 rounded border-slate-300 text-sky-600 focus:ring-sky-500 cursor-pointer"
                />
              </th>

              <th className="px-4 py-3 min-w-[180px]">
                <button
                  onClick={() => handleSort("type")}
                  className="flex items-center gap-1.5 font-bold hover:text-sky-600 dark:hover:text-sky-400 transition-colors cursor-pointer"
                >
                  <span>Type</span>
                  <ArrowUpDown className="h-3 w-3 text-slate-400" />
                </button>
              </th>

              <th className="px-4 py-3 min-w-[220px]">
                <button
                  onClick={() => handleSort("employeeName")}
                  className="flex items-center gap-1.5 font-bold hover:text-sky-600 dark:hover:text-sky-400 transition-colors cursor-pointer"
                >
                  <span>Requested by</span>
                  <ArrowUpDown className="h-3 w-3 text-slate-400" />
                </button>
              </th>

              <th className="px-4 py-3 min-w-[240px]">
                <span className="font-bold">Details</span>
              </th>

              <th className="px-4 py-3 min-w-[180px] text-left">
                <span className="font-bold">Actions</span>
              </th>
            </tr>
          </thead>

          {/* Table Body */}
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60">
            {isLoading ? (
              Array.from({ length: pageSize }).map((_, idx) => (
                <tr key={idx} className="animate-pulse">
                  <td className="px-4 py-4 text-center">
                    <div className="h-4 w-4 bg-slate-200 dark:bg-slate-800 rounded mx-auto" />
                  </td>
                  <td className="px-4 py-4">
                    <div className="flex items-center gap-3">
                      <div className="h-9 w-9 bg-slate-200 dark:bg-slate-800 rounded-full shrink-0" />
                      <div className="space-y-1.5">
                        <div className="h-3.5 w-20 bg-slate-200 dark:bg-slate-800 rounded" />
                        <div className="h-3 w-12 bg-slate-200 dark:bg-slate-800 rounded" />
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-4">
                    <div className="space-y-1.5">
                      <div className="h-3.5 w-28 bg-slate-200 dark:bg-slate-800 rounded" />
                      <div className="h-3 w-36 bg-slate-200 dark:bg-slate-800 rounded" />
                    </div>
                  </td>
                  <td className="px-4 py-4">
                    <div className="h-3.5 w-32 bg-slate-200 dark:bg-slate-800 rounded" />
                  </td>
                  <td className="px-4 py-4">
                    <div className="flex items-center gap-2">
                      <div className="h-8 w-24 bg-slate-200 dark:bg-slate-800 rounded" />
                      <div className="h-8 w-8 bg-slate-200 dark:bg-slate-800 rounded" />
                      <div className="h-8 w-8 bg-slate-200 dark:bg-slate-800 rounded" />
                    </div>
                  </td>
                </tr>
              ))
            ) : totalRecords === 0 ? (
              <tr>
                <td colSpan={5} className="px-6 py-16 text-center">
                  <div className="flex flex-col items-center justify-center space-y-2 text-slate-400">
                    <Inbox className="h-10 w-10 stroke-1 text-slate-300 dark:text-slate-600" />
                    <p className="text-sm font-medium text-slate-600 dark:text-slate-400">
                      No approval requests found
                    </p>
                    <p className="text-xs text-slate-400 dark:text-slate-500">
                      Try adjusting your search criteria or switching status tabs.
                    </p>
                  </div>
                </td>
              </tr>
            ) : (
              paginatedRequests.map((req) => {
                const isLeave = req.type === "Leave";
                const isPending = req.status === "pending";
                const isExpanded = expandedRowIds.includes(req.id);

                return (
                  <React.Fragment key={req.id}>
                    <tr
                      className="hover:bg-slate-50/80 dark:hover:bg-slate-800/40 transition-colors text-slate-700 dark:text-slate-300"
                    >
                      {/* Checkbox */}
                      <td className="px-4 py-3.5 text-center">
                        <input
                          type="checkbox"
                          checked={selectedIds.includes(req.id)}
                          onChange={() => toggleSelectRow(req.id)}
                          className="h-4 w-4 rounded border-slate-300 text-sky-600 focus:ring-sky-500 cursor-pointer"
                        />
                      </td>

                      {/* Type Column */}
                      <td className="px-4 py-3.5">
                        <div className="flex items-center gap-3">
                          <div
                            className={`h-9 w-9 rounded-full flex items-center justify-center shrink-0 ${
                              isLeave
                                ? "bg-[#FEF3C7] text-[#D97706] dark:bg-amber-950/50 dark:text-amber-400"
                                : "bg-[#EBF5FF] text-[#0B85C9] dark:bg-sky-950/50 dark:text-sky-400"
                            }`}
                          >
                            {isLeave ? (
                              <Palmtree className="h-4.5 w-4.5" />
                            ) : (
                              <Calendar className="h-4.5 w-4.5" />
                            )}
                          </div>
                          <div>
                            <div className="font-bold text-slate-800 dark:text-slate-100 text-xs">
                              {req.type}
                            </div>
                            <div className="text-[11px] text-slate-400 dark:text-slate-500 font-medium">
                              {req.subtype}
                            </div>
                          </div>
                        </div>
                      </td>

                      {/* Requested by Column */}
                      <td className="px-4 py-3.5">
                        <div>
                          <div className="font-bold text-slate-800 dark:text-slate-100 text-xs">
                            {req.employeeCode} - {req.employeeName}
                          </div>
                          <div className="text-[11px] text-slate-400 dark:text-slate-500 font-medium">
                            {req.designation} • {req.department}
                          </div>
                        </div>
                      </td>

                      {/* Details Column */}
                      <td className="px-4 py-3.5">
                        {isLeave ? (
                          <div className="flex items-center gap-2 text-xs">
                            <div>
                              <span className="text-[10px] text-slate-400 block">From</span>
                              <span className="font-bold text-slate-800 dark:text-slate-200">
                                {req.details.fromDate || "-"}
                              </span>
                            </div>
                            <div className="text-slate-300 dark:text-slate-700 text-[10px] flex items-center gap-1 px-1">
                              <span>---</span>
                              <span className="text-slate-500 dark:text-slate-400 font-medium">
                                {req.details.totalDays || "1 Day"}
                              </span>
                              <span>---</span>
                            </div>
                            <div>
                              <span className="text-[10px] text-slate-400 block">To</span>
                              <span className="font-bold text-slate-800 dark:text-slate-200">
                                {req.details.toDate || "-"}
                              </span>
                            </div>
                          </div>
                        ) : (
                          <div className="text-xs">
                            <span className="text-[10px] text-slate-400 block">Date</span>
                            <span className="font-bold text-slate-800 dark:text-slate-200">
                              {req.details.date || "-"}
                            </span>
                          </div>
                        )}
                      </td>

                      {/* Actions Column */}
                      <td className="px-4 py-3.5">
                        <div className="flex items-center gap-2">
                          {/* View More / View Less Button */}
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => {
                              toggleRowExpand(req.id);
                              if (onViewDetails) onViewDetails(req);
                            }}
                            className="h-8 px-3 text-xs font-medium bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-50 cursor-pointer flex items-center gap-1 rounded"
                          >
                            <span>{isExpanded ? "View Less" : "View More"}</span>
                            {isExpanded ? (
                              <ChevronUp className="h-3 w-3 text-slate-400" />
                            ) : (
                              <ChevronDown className="h-3 w-3 text-slate-400" />
                            )}
                          </Button>

                          {/* Pending Action Icons */}
                          {isPending ? (
                            <>
                              {/* Reject Button (Red X) */}
                              <button
                                onClick={() => onReject(req)}
                                className="h-8 w-8 rounded border border-red-200 dark:border-red-900/50 bg-white dark:bg-slate-900 text-red-500 hover:bg-red-50 dark:hover:bg-red-950/30 flex items-center justify-center transition-colors cursor-pointer"
                                title="Reject Request"
                              >
                                <X className="h-4 w-4 font-bold" />
                              </button>

                              {/* Approve Button (Green Check) */}
                              <button
                                onClick={() => onApprove(req)}
                                className="h-8 w-8 rounded border border-emerald-200 dark:border-emerald-900/50 bg-white dark:bg-slate-900 text-emerald-600 hover:bg-emerald-50 dark:hover:bg-emerald-950/30 flex items-center justify-center transition-colors cursor-pointer"
                                title="Approve Request"
                              >
                                <Check className="h-4 w-4 font-bold" />
                              </button>
                            </>
                          ) : (
                            <div>
                              {req.status === "approved" ? (
                                <Badge variant="success">Approved</Badge>
                              ) : (
                                <Badge variant="destructive">Rejected</Badge>
                              )}
                            </div>
                          )}
                        </div>
                      </td>
                    </tr>

                    {/* Inline Expandable Sub-Table Row */}
                    {isExpanded && (
                      <tr key={`${req.id}-details`} className="bg-slate-50/60 dark:bg-slate-950/40">
                        <td colSpan={5} className="px-4 py-2">
                          <div className="bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 rounded-md overflow-hidden text-xs shadow-2xs">
                            <div className="grid grid-cols-12 gap-2 bg-[#F8FAFC] dark:bg-slate-950 px-4 py-2 font-semibold text-slate-500 dark:text-slate-400 text-[11px] border-b border-slate-200/80 dark:border-slate-800">
                              <div className="col-span-3">Applied On</div>
                              <div className="col-span-2">{isLeave ? "Days" : "Date / Time"}</div>
                              <div className="col-span-7">Employee&apos;s Reason</div>
                            </div>
                            <div className="grid grid-cols-12 gap-2 px-4 py-3 text-slate-800 dark:text-slate-200 text-xs">
                              <div className="col-span-3 font-medium">{req.submittedDate}</div>
                              <div className="col-span-2 font-medium">
                                {isLeave
                                  ? req.details.totalDays || "1 Day"
                                  : req.details.date || req.details.totalHours || "-"}
                              </div>
                              <div className="col-span-7 text-slate-700 dark:text-slate-300">
                                {req.details.reason || "No reason specified."}
                              </div>
                            </div>
                            {req.remarks && (
                              <div className="px-4 py-2 bg-slate-50 dark:bg-slate-950 border-t border-slate-100 dark:border-slate-800 text-[11px] text-slate-600 dark:text-slate-400 flex items-center justify-between">
                                <span>
                                  Approver Remarks ({req.status === "approved" ? req.approvedBy : req.rejectedBy}):
                                </span>
                                <span className="italic font-medium text-slate-700 dark:text-slate-300">
                                  {req.remarks}
                                </span>
                              </div>
                            )}
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Footer */}
      <div className="px-4 py-3 border-t border-slate-200 dark:border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-slate-600 dark:text-slate-400 bg-white dark:bg-slate-900">
        <div>
          Showing{" "}
          <span className="font-semibold text-slate-800 dark:text-slate-200">
            {totalRecords === 0 ? 0 : startIndex + 1}
          </span>{" "}
          to{" "}
          <span className="font-semibold text-slate-800 dark:text-slate-200">
            {Math.min(startIndex + pageSize, totalRecords)}
          </span>{" "}
          of{" "}
          <span className="font-semibold text-slate-800 dark:text-slate-200">{totalRecords}</span>{" "}
          Results
        </div>

        <div className="flex items-center gap-3">
          {/* Page Size Selector */}
          <select
            value={pageSize}
            onChange={(e) => handlePageSizeChange(Number(e.target.value))}
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
              disabled={currentPage <= 1}
              onClick={() => handlePageChange(Math.max(1, currentPage - 1))}
              className="h-8 px-3 text-xs bg-white dark:bg-slate-900 border-slate-300 dark:border-slate-700 cursor-pointer disabled:opacity-50"
            >
              Previous
            </Button>

            {Array.from({ length: totalPages }).map((_, idx) => {
              const pageNum = idx + 1;
              return (
                <button
                  key={pageNum}
                  onClick={() => handlePageChange(pageNum)}
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
              disabled={currentPage >= totalPages}
              onClick={() => handlePageChange(Math.min(totalPages, currentPage + 1))}
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
