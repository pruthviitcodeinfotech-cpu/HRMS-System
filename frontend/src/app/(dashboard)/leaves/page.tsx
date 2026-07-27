"use client";

import { useState } from "react";
import Link from "next/link";
import { ProtectedRoute } from "@/features/auth";
import { useLeaveRequests, useLeaveTypes } from "@/features/leaves/hooks";
import { Skeleton } from "@/components/feedback/skeleton";
import { EmptyState } from "@/components/feedback/empty-state";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Clock,
  CheckCircle2,
  XCircle,
  AlertCircle,
  ArrowRight,
  Search,
  BookOpen,
  UserCheck,
  Scale,
  Sun,
} from "lucide-react";

export default function LeavesPage() {
  const [page, setPage] = useState(1);
  const [pageSize] = useState(10);
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [searchQuery, setSearchQuery] = useState<string>("");

  const { data: requestsData, isLoading, isError, error } = useLeaveRequests({
    page,
    page_size: pageSize,
    status: statusFilter || undefined,
  });

  const { data: leaveTypesData } = useLeaveTypes({ page_size: 50 });

  const requests = requestsData?.items || [];
  const pagination = requestsData?.pagination;

  return (
    <ProtectedRoute requiredPermission={{ feature: "leave_request", action: "read" }}>
      <div className="p-6 space-y-6 max-w-7xl mx-auto">
        {/* Page Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100">
              Leave Management Overview
            </h1>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
              Review employee leave requests, configure leave policies, manage balances, and set holiday calendars.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Link href="/leaves/create">
              <Button size="sm" variant="outline" className="gap-2 text-xs">
                <BookOpen className="h-3.5 w-3.5" />
                Leave Policies
              </Button>
            </Link>
            <Link href="/leaves/assign">
              <Button size="sm" variant="outline" className="gap-2 text-xs">
                <UserCheck className="h-3.5 w-3.5" />
                Assign Leaves
              </Button>
            </Link>
            <Link href="/leaves/balance">
              <Button size="sm" variant="outline" className="gap-2 text-xs">
                <Scale className="h-3.5 w-3.5" />
                Leave Balances
              </Button>
            </Link>
            <Link href="/leaves/holidays/create">
              <Button size="sm" className="gap-2 text-xs">
                <Sun className="h-3.5 w-3.5" />
                Holidays
              </Button>
            </Link>
          </div>
        </div>

        {/* Quick Metrics / Leave Types */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-card p-4 rounded-xl border border-border space-y-2 shadow-xs">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-500">Configured Policies</span>
              <BookOpen className="h-4 w-4 text-blue-600" />
            </div>
            <p className="text-2xl font-bold text-slate-800 dark:text-slate-100">
              {leaveTypesData?.pagination?.total_records ?? leaveTypesData?.items?.length ?? 0}
            </p>
            <Link href="/leaves/create" className="text-[11px] text-blue-600 hover:underline inline-flex items-center gap-1">
              Manage types <ArrowRight className="h-3 w-3" />
            </Link>
          </div>

          <div className="bg-card p-4 rounded-xl border border-border space-y-2 shadow-xs">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-amber-600">Pending Requests</span>
              <Clock className="h-4 w-4 text-amber-500" />
            </div>
            <p className="text-2xl font-bold text-amber-600">
              {requests.filter((r: { status: string }) => r.status === "pending").length}
            </p>
            <span className="text-[11px] text-slate-400">Awaiting approval</span>
          </div>

          <div className="bg-card p-4 rounded-xl border border-border space-y-2 shadow-xs">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-emerald-600">Approved Leaves</span>
              <CheckCircle2 className="h-4 w-4 text-emerald-500" />
            </div>
            <p className="text-2xl font-bold text-emerald-600">
              {requests.filter((r: { status: string }) => r.status === "approved").length}
            </p>
            <span className="text-[11px] text-slate-400">Current cycle</span>
          </div>

          <div className="bg-card p-4 rounded-xl border border-border space-y-2 shadow-xs">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-rose-600">Rejected / Cancelled</span>
              <XCircle className="h-4 w-4 text-rose-500" />
            </div>
            <p className="text-2xl font-bold text-rose-600">
              {requests.filter((r: { status: string }) => r.status === "rejected" || r.status === "cancelled").length}
            </p>
            <span className="text-[11px] text-slate-400">Declined requests</span>
          </div>
        </div>

        {/* Filters & Search */}
        <div className="bg-card p-4 rounded-xl border border-border space-y-4 shadow-xs">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
            <div className="flex items-center gap-3 w-full sm:w-auto">
              <div className="relative flex-1 sm:w-64">
                <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-slate-400" />
                <Input
                  type="text"
                  placeholder="Search requests..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-8 text-xs h-9"
                />
              </div>

              <select
                value={statusFilter}
                onChange={(e) => {
                  setStatusFilter(e.target.value);
                  setPage(1);
                }}
                className="h-9 text-xs rounded-md border border-input bg-background px-3 py-1 font-medium text-slate-700 dark:text-slate-200"
              >
                <option value="">All Statuses</option>
                <option value="pending">Pending</option>
                <option value="approved">Approved</option>
                <option value="rejected">Rejected</option>
                <option value="cancelled">Cancelled</option>
              </select>
            </div>
          </div>

          {/* Loading State */}
          {isLoading && (
            <div className="space-y-3 pt-2">
              <Skeleton className="h-10 w-full rounded-lg" />
              <Skeleton className="h-10 w-full rounded-lg" />
              <Skeleton className="h-10 w-full rounded-lg" />
            </div>
          )}

          {/* Error State */}
          {isError && (
            <div className="p-4 bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 rounded-lg text-center text-xs text-rose-600 dark:text-rose-400">
              <AlertCircle className="h-5 w-5 mx-auto mb-1 text-rose-500" />
              {error instanceof Error ? error.message : "Failed to load leave requests."}
            </div>
          )}

          {/* Empty State */}
          {!isLoading && !isError && requests.length === 0 && (
            <EmptyState
              title="No Leave Requests Found"
              description="There are no leave requests matching the selected filters."
            />
          )}

          {/* Requests Table */}
          {!isLoading && !isError && requests.length > 0 && (
            <div className="overflow-x-auto rounded-lg border border-slate-200 dark:border-slate-800">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 text-slate-500 dark:text-slate-400 font-semibold">
                  <tr>
                    <th className="p-3">ID</th>
                    <th className="p-3">Employee ID</th>
                    <th className="p-3">Leave Type</th>
                    <th className="p-3">Dates</th>
                    <th className="p-3">Duration</th>
                    <th className="p-3">Reason</th>
                    <th className="p-3">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                  {requests.map((req: {
                    id: number;
                    employee_id: number;
                    start_date: string;
                    end_date: string;
                    duration_days: number;
                    reason?: string | null;
                    status: string;
                    leave_type?: { name: string } | null;
                  }) => (
                    <tr key={req.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-900/50">
                      <td className="p-3 font-semibold text-slate-700 dark:text-slate-300">#{req.id}</td>
                      <td className="p-3 font-mono text-slate-600 dark:text-slate-400">Emp #{req.employee_id}</td>
                      <td className="p-3 font-medium text-slate-800 dark:text-slate-200">
                        {req.leave_type?.name || "Leave"}
                      </td>
                      <td className="p-3 text-slate-600 dark:text-slate-400">
                        {req.start_date} to {req.end_date}
                      </td>
                      <td className="p-3 font-semibold text-slate-700 dark:text-slate-300">
                        {req.duration_days} day(s)
                      </td>
                      <td className="p-3 text-slate-500 truncate max-w-xs">{req.reason || "-"}</td>
                      <td className="p-3">
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold capitalize ${
                            req.status === "approved"
                              ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-400"
                              : req.status === "rejected"
                              ? "bg-rose-50 text-rose-700 dark:bg-rose-950/40 dark:text-rose-400"
                              : "bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-400"
                          }`}
                        >
                          {req.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Pagination Footer */}
          {pagination && pagination.total_pages > 1 && (
            <div className="flex items-center justify-between text-xs pt-2">
              <span className="text-slate-500">
                Page {pagination.page} of {pagination.total_pages} ({pagination.total_records} records)
              </span>
              <div className="flex items-center gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  disabled={!pagination.has_previous}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  className="h-8 text-xs"
                >
                  Previous
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  disabled={!pagination.has_next}
                  onClick={() => setPage((p) => p + 1)}
                  className="h-8 text-xs"
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>
    </ProtectedRoute>
  );
}
