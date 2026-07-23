"use client";

import React, { useState, useCallback } from "react";
import { toast } from "sonner";
import {
  ArrowUp,
  ArrowDown,
  ArrowUpDown,
  ChevronLeft,
  ChevronRight,
  RefreshCw,
  Eye,
  X,
  AlertCircle,
  CheckCircle2,
  Clock,
  Ban,
  FileText,
  SlidersHorizontal,
} from "lucide-react";
import { ProtectedRoute } from "@/features/auth";
import {
  useFinalizedPayroll,
  useFinalizedPayrollDetails,
  usePayPayroll,
  usePayrollGroups,
} from "@/features/payroll/hooks/use-payroll";
import { FinalizedPayrollItem } from "@/features/payroll/types";

// ─── Helpers ─────────────────────────────────────────────────────────────────

function fmtDate(s?: string | null): string {
  if (!s) return "—";
  try {
    return new Date(s).toLocaleDateString("en-IN", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    });
  } catch {
    return s;
  }
}

function fmtDateTime(s?: string | null): string {
  if (!s) return "—";
  try {
    return new Date(s).toLocaleString("en-IN", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return s;
  }
}

function fmtAmount(n?: number | null): string {
  if (n == null) return "—";
  return `₹${Number(n).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

// ─── Status Badge ─────────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, { color: string; icon: React.ReactNode; label: string }> = {
    Draft:     { color: "bg-slate-100 text-slate-600 border-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:border-slate-700", icon: <FileText className="w-3 h-3" />, label: "Draft" },
    Finalized: { color: "bg-blue-50 text-blue-600 border-blue-100 dark:bg-blue-950/40 dark:text-blue-400 dark:border-blue-900/40", icon: <Clock className="w-3 h-3" />, label: "Finalized" },
    Paid:      { color: "bg-emerald-50 text-emerald-600 border-emerald-100 dark:bg-emerald-950/40 dark:text-emerald-400 dark:border-emerald-900/40", icon: <CheckCircle2 className="w-3 h-3" />, label: "Paid" },
    Cancelled: { color: "bg-red-50 text-red-500 border-red-100 dark:bg-red-950/40 dark:text-red-400 dark:border-red-900/40", icon: <Ban className="w-3 h-3" />, label: "Cancelled" },
  };
  const cfg = map[status] ?? map["Finalized"];
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold border ${cfg.color}`}>
      {cfg.icon}
      {cfg.label}
    </span>
  );
}

// ─── Sort Icon ────────────────────────────────────────────────────────────────

function SortIcon({ field, active, order }: { field: string; active: string; order: "asc" | "desc" }) {
  if (active !== field) return <ArrowUpDown className="w-3 h-3 ml-1 opacity-30" />;
  return order === "asc" ? (
    <ArrowUp className="w-3 h-3 ml-1 text-blue-500" />
  ) : (
    <ArrowDown className="w-3 h-3 ml-1 text-blue-500" />
  );
}

// ─── Loading Skeleton ─────────────────────────────────────────────────────────

function TableSkeleton() {
  return (
    <>
      {Array.from({ length: 6 }).map((_, i) => (
        <tr key={i} className="border-b border-slate-100 dark:border-slate-800">
          {Array.from({ length: 9 }).map((_, j) => (
            <td key={j} className="px-3 py-3">
              <div className="h-3 bg-slate-200 dark:bg-slate-700 rounded animate-pulse" style={{ width: `${50 + Math.random() * 40}%` }} />
            </td>
          ))}
        </tr>
      ))}
    </>
  );
}

// ─── Empty State ──────────────────────────────────────────────────────────────

function EmptyState() {
  return (
    <tr>
      <td colSpan={9} className="py-16 text-center">
        <div className="flex flex-col items-center gap-3">
          <div className="w-12 h-12 rounded-full bg-slate-100 dark:bg-slate-800 flex items-center justify-center">
            <svg className="w-6 h-6 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </div>
          <p className="text-sm text-slate-500 dark:text-slate-400">No Data Found</p>
        </div>
      </td>
    </tr>
  );
}

// ─── Error State ──────────────────────────────────────────────────────────────

function ErrorState({ error, onRetry }: { error?: any; onRetry: () => void }) {
  if (typeof window !== "undefined" && error) {
    console.error("[FinalizedPayroll Error Trace]", {
      error,
      message: error?.message,
      statusCode: error?.statusCode || error?.response?.status,
      code: error?.code,
      response: error?.response,
      data: error?.response?.data,
    });
  }

  const errorMessage = error?.message || "Failed to load finalized payroll data.";
  const statusCode = error?.statusCode || error?.response?.status;
  const errorCode = error?.code;

  return (
    <tr>
      <td colSpan={9} className="py-16 text-center">
        <div className="flex flex-col items-center gap-3 max-w-md mx-auto">
          <AlertCircle className="w-8 h-8 text-red-400" />
          <p className="text-sm text-slate-700 dark:text-slate-300 font-medium">{errorMessage}</p>
          {(statusCode || errorCode) && (
            <p className="text-xs text-slate-400 font-mono">
              {statusCode ? `Status: ${statusCode}` : ""} {errorCode ? `(${errorCode})` : ""}
            </p>
          )}
          <button
            onClick={onRetry}
            className="inline-flex items-center gap-1.5 text-xs text-blue-600 hover:text-blue-700 font-medium mt-1"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            Retry
          </button>
        </div>
      </td>
    </tr>
  );
}

// ─── Detail Panel ─────────────────────────────────────────────────────────────

function DetailDrawer({
  id,
  onClose,
}: {
  id: number;
  onClose: () => void;
}) {
  const { data, isLoading, isError, refetch } = useFinalizedPayrollDetails(id);
  const payMutation = usePayPayroll();

  const record = data as FinalizedPayrollItem | undefined;

  const handlePay = async () => {
    if (!record) return;
    try {
      await payMutation.mutateAsync({ id: record.id });
      toast.success("Payroll marked as Paid successfully.");
      refetch();
    } catch {
      toast.error("Failed to mark payroll as paid. Please try again.");
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex">
      {/* Backdrop */}
      <div className="flex-1 bg-black/30 backdrop-blur-sm" onClick={onClose} />

      {/* Panel */}
      <div className="w-full max-w-2xl bg-white dark:bg-slate-900 shadow-2xl flex flex-col overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-800 sticky top-0 bg-white dark:bg-slate-900 z-10">
          <div>
            <h2 className="text-base font-semibold text-slate-900 dark:text-slate-100">Finalized Payroll Details</h2>
            {record && (
              <p className="text-xs text-slate-500 mt-0.5">
                {fmtDate(record.from_date)} — {fmtDate(record.to_date)}
              </p>
            )}
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
          >
            <X className="w-4 h-4 text-slate-500" />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 p-6 space-y-6">
          {isLoading && (
            <div className="space-y-3">
              {Array.from({ length: 8 }).map((_, i) => (
                <div key={i} className="h-4 bg-slate-200 dark:bg-slate-700 rounded animate-pulse" style={{ width: `${60 + i * 5}%` }} />
              ))}
            </div>
          )}

          {isError && (
            <div className="flex flex-col items-center gap-3 py-12">
              <AlertCircle className="w-8 h-8 text-red-400" />
              <p className="text-sm text-slate-600">Failed to load details.</p>
              <button onClick={() => refetch()} className="text-xs text-blue-600 hover:underline">Retry</button>
            </div>
          )}

          {record && (
            <>
              {/* Summary Card */}
              <div className="grid grid-cols-2 gap-4">
                <InfoField label="Payroll Group" value={record.payroll_group_name ?? "—"} />
                <InfoField label="Payroll Module" value={record.payroll_module ?? "—"} />
                <InfoField label="From Date" value={fmtDate(record.from_date)} />
                <InfoField label="To Date" value={fmtDate(record.to_date)} />
                <InfoField label="Status" value={<StatusBadge status={record.status} />} />
                <InfoField label="Employee Count" value={String(record.employee_count)} />
                <InfoField label="Finalized Amount" value={fmtAmount(record.finalized_amount)} highlight />
                <InfoField label="Paid Amount" value={fmtAmount(record.paid_amount)} />
                <InfoField label="Finalized On" value={fmtDateTime(record.finalized_on)} />
                <InfoField label="Paid On" value={fmtDateTime(record.paid_on)} />
                {record.remarks && (
                  <div className="col-span-2">
                    <InfoField label="Remarks" value={record.remarks} />
                  </div>
                )}
              </div>

              {/* Financials */}
              <div>
                <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">Financial Summary</h3>
                <div className="bg-slate-50 dark:bg-slate-800/50 rounded-xl p-4 grid grid-cols-3 gap-4">
                  <AmountCard label="Gross Amount" value={fmtAmount(record.gross_amount)} color="text-slate-700 dark:text-slate-200" />
                  <AmountCard label="Deductions" value={fmtAmount(record.deduction_amount)} color="text-red-600 dark:text-red-400" />
                  <AmountCard label="Net Payable" value={fmtAmount(record.net_payable)} color="text-emerald-600 dark:text-emerald-400" />
                </div>
              </div>

              {/* Employee Snapshots */}
              {record.employees && record.employees.length > 0 && (
                <div>
                  <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">
                    Employee Snapshots ({record.employees.length})
                  </h3>
                  <div className="border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden">
                    <table className="w-full text-xs">
                      <thead>
                        <tr className="bg-slate-50 dark:bg-slate-800/60 text-slate-500 dark:text-slate-400 text-[10px] uppercase font-semibold border-b border-slate-200 dark:border-slate-700">
                          <th className="px-3 py-2 text-left">Employee</th>
                          <th className="px-3 py-2 text-right">Loan</th>
                          <th className="px-3 py-2 text-right">Arrears</th>
                          <th className="px-3 py-2 text-right">Net Salary</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                        {record.employees.map((emp) => (
                          <tr key={emp.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/30">
                            <td className="px-3 py-2">
                              <div className="font-medium text-slate-900 dark:text-slate-100">{emp.employee_name ?? "—"}</div>
                              <div className="text-[10px] text-slate-500">{emp.employee_code ?? ""}</div>
                            </td>
                            <td className="px-3 py-2 text-right text-slate-600 dark:text-slate-300">{fmtAmount(emp.loan_amount)}</td>
                            <td className="px-3 py-2 text-right text-slate-600 dark:text-slate-300">{fmtAmount(emp.arrears_amount)}</td>
                            <td className="px-3 py-2 text-right font-semibold text-emerald-600 dark:text-emerald-400">{fmtAmount(emp.net_salary)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer Actions */}
        {record && record.status === "Finalized" && (
          <div className="px-6 py-4 border-t border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 sticky bottom-0">
            <button
              onClick={handlePay}
              disabled={payMutation.isPending}
              className="w-full py-2.5 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-60 text-white text-sm font-semibold rounded-lg transition-colors flex items-center justify-center gap-2"
            >
              {payMutation.isPending ? (
                <RefreshCw className="w-4 h-4 animate-spin" />
              ) : (
                <CheckCircle2 className="w-4 h-4" />
              )}
              {payMutation.isPending ? "Processing..." : "Mark as Paid"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

function InfoField({ label, value, highlight }: { label: string; value: React.ReactNode; highlight?: boolean }) {
  return (
    <div>
      <dt className="text-[10px] font-medium text-slate-400 uppercase tracking-wider mb-0.5">{label}</dt>
      <dd className={`text-sm font-medium ${highlight ? "text-emerald-600 dark:text-emerald-400" : "text-slate-900 dark:text-slate-100"}`}>{value}</dd>
    </div>
  );
}

function AmountCard({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div className="text-center">
      <div className={`text-base font-bold ${color}`}>{value}</div>
      <div className="text-[10px] text-slate-500 mt-0.5">{label}</div>
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function FinalizedPayrollDetailsPage() {
  // Filter state
  const [filterGroup, setFilterGroup] = useState<string>("");
  const [filterStatus, setFilterStatus] = useState<string>("");
  const [filterFromDate, setFilterFromDate] = useState<string>("");
  const [filterToDate, setFilterToDate] = useState<string>("");
  const [showFilters, setShowFilters] = useState(false);

  // Sort state
  const [sortField, setSortField] = useState<string>("finalized_on");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");

  // Pagination state
  const [page, setPage] = useState(1);
  const [pageSize] = useState(10);

  // Detail drawer state
  const [selectedId, setSelectedId] = useState<number | null>(null);

  // ── Master Data: Payroll Groups (reuse existing module — Golden Rule) ──
  const { data: groupsData } = usePayrollGroups({ page: 1, page_size: 100 });
  const groups: Array<{ id: number; name: string }> = (groupsData as any)?.items ?? [];

  // ── Main Query ────────────────────────────────────────────────────────────
  const queryParams = {
    page,
    page_size: pageSize,
    ...(filterGroup ? { payroll_group_id: Number(filterGroup) } : {}),
    ...(filterStatus ? { status: filterStatus } : {}),
    ...(filterFromDate ? { from_date: filterFromDate } : {}),
    ...(filterToDate ? { to_date: filterToDate } : {}),
  };

  const { data, isLoading, isError, error, refetch } = useFinalizedPayroll(queryParams);

  const items: FinalizedPayrollItem[] = (data as any)?.items ?? [];
  const pagination = (data as any)?.pagination ?? { total_records: 0, total_pages: 1 };

  // ── Sorting ───────────────────────────────────────────────────────────────

  const sortedItems = [...items].sort((a: any, b: any) => {
    const av = a[sortField] ?? "";
    const bv = b[sortField] ?? "";
    if (av < bv) return sortOrder === "asc" ? -1 : 1;
    if (av > bv) return sortOrder === "asc" ? 1 : -1;
    return 0;
  });

  const handleSort = useCallback((field: string) => {
    if (sortField === field) {
      setSortOrder((o) => (o === "asc" ? "desc" : "asc"));
    } else {
      setSortField(field);
      setSortOrder("asc");
    }
  }, [sortField]);

  // ── Filter clear ──────────────────────────────────────────────────────────

  const hasFilters = !!(filterGroup || filterStatus || filterFromDate || filterToDate);

  const clearFilters = () => {
    setFilterGroup("");
    setFilterStatus("");
    setFilterFromDate("");
    setFilterToDate("");
    setPage(1);
  };

  const TH = ({ label, field, className = "" }: { label: string; field?: string; className?: string }) => (
    <th
      className={`px-3 py-3 text-[11px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider whitespace-nowrap ${field ? "cursor-pointer select-none hover:text-slate-700 dark:hover:text-slate-200" : ""} ${className}`}
      onClick={field ? () => handleSort(field) : undefined}
    >
      <span className="inline-flex items-center">
        {label}
        {field && <SortIcon field={field} active={sortField} order={sortOrder} />}
      </span>
    </th>
  );

  return (
    <ProtectedRoute requiredPermission={{ feature: "payroll_record", action: "read" }}>
      <div className="flex flex-col min-h-0">
        {/* ── Page Title ── */}
        <div className="px-6 py-4 border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
          <div className="flex items-center justify-between">
            <h1 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
              Finalized Payroll Details
            </h1>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setShowFilters((v) => !v)}
                className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
                  showFilters || hasFilters
                    ? "bg-blue-50 border-blue-200 text-blue-600 dark:bg-blue-950/40 dark:border-blue-800 dark:text-blue-400"
                    : "bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800"
                }`}
              >
                <SlidersHorizontal className="w-3.5 h-3.5" />
                Filters
                {hasFilters && (
                  <span className="ml-1 w-4 h-4 rounded-full bg-blue-600 text-white text-[9px] font-bold flex items-center justify-center">
                    {[filterGroup, filterStatus, filterFromDate, filterToDate].filter(Boolean).length}
                  </span>
                )}
              </button>
              <button
                onClick={() => refetch()}
                className="p-1.5 rounded-lg border border-slate-200 dark:border-slate-700 text-slate-500 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
                title="Refresh"
              >
                <RefreshCw className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>

        {/* ── Filters Panel ── */}
        {showFilters && (
          <div className="px-6 py-3 bg-slate-50 dark:bg-slate-800/50 border-b border-slate-200 dark:border-slate-800">
            <div className="flex flex-wrap items-end gap-3">
              {/* Payroll Group — reuses existing Payroll Group module */}
              <div className="flex flex-col gap-1 min-w-[180px]">
                <label className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">Payroll Group</label>
                <select
                  value={filterGroup}
                  onChange={(e) => { setFilterGroup(e.target.value); setPage(1); }}
                  className="text-xs px-2.5 py-1.5 border border-slate-200 dark:border-slate-700 rounded-lg bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">All Groups</option>
                  {groups.map((g) => (
                    <option key={g.id} value={g.id}>{g.name}</option>
                  ))}
                </select>
              </div>

              {/* Status */}
              <div className="flex flex-col gap-1 min-w-[140px]">
                <label className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">Status</label>
                <select
                  value={filterStatus}
                  onChange={(e) => { setFilterStatus(e.target.value); setPage(1); }}
                  className="text-xs px-2.5 py-1.5 border border-slate-200 dark:border-slate-700 rounded-lg bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">All Statuses</option>
                  <option value="Draft">Draft</option>
                  <option value="Finalized">Finalized</option>
                  <option value="Paid">Paid</option>
                  <option value="Cancelled">Cancelled</option>
                </select>
              </div>

              {/* From Date */}
              <div className="flex flex-col gap-1 min-w-[140px]">
                <label className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">From Date</label>
                <input
                  type="date"
                  value={filterFromDate}
                  onChange={(e) => { setFilterFromDate(e.target.value); setPage(1); }}
                  className="text-xs px-2.5 py-1.5 border border-slate-200 dark:border-slate-700 rounded-lg bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              {/* To Date */}
              <div className="flex flex-col gap-1 min-w-[140px]">
                <label className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">To Date</label>
                <input
                  type="date"
                  value={filterToDate}
                  onChange={(e) => { setFilterToDate(e.target.value); setPage(1); }}
                  className="text-xs px-2.5 py-1.5 border border-slate-200 dark:border-slate-700 rounded-lg bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              {/* Clear */}
              {hasFilters && (
                <button
                  onClick={clearFilters}
                  className="inline-flex items-center gap-1 text-xs text-slate-500 hover:text-red-500 transition-colors mt-4"
                >
                  <X className="w-3.5 h-3.5" />
                  Clear
                </button>
              )}
            </div>
          </div>
        )}

        {/* ── Table ── */}
        <div className="flex-1 overflow-auto">
          <table className="w-full text-left border-collapse">
            <thead className="sticky top-0 z-10">
              <tr className="bg-slate-50 dark:bg-slate-800/80 border-b border-slate-200 dark:border-slate-700">
                <TH label="From" field="from_date" />
                <TH label="To" field="to_date" />
                <TH label="Finalized Amount" field="finalized_amount" className="text-right" />
                <TH label="Finalized On" field="finalized_on" />
                <TH label="Paid Amount" field="paid_amount" className="text-right" />
                <TH label="Paid On" field="paid_on" />
                <TH label="Payroll Module" field="payroll_module" />
                <TH label="Payroll Group" field="payroll_group_name" />
                <th className="px-3 py-3 text-[11px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800 text-xs">
              {isLoading ? (
                <TableSkeleton />
              ) : isError ? (
                <ErrorState error={error} onRetry={() => refetch()} />
              ) : sortedItems.length === 0 ? (
                <EmptyState />
              ) : (
                sortedItems.map((item) => (
                  <tr
                    key={item.id}
                    className="hover:bg-slate-50/70 dark:hover:bg-slate-800/40 transition-colors"
                  >
                    {/* From */}
                    <td className="px-3 py-3 text-slate-700 dark:text-slate-300 font-medium whitespace-nowrap">
                      {fmtDate(item.from_date)}
                    </td>

                    {/* To */}
                    <td className="px-3 py-3 text-slate-700 dark:text-slate-300 whitespace-nowrap">
                      {fmtDate(item.to_date)}
                    </td>

                    {/* Finalized Amount */}
                    <td className="px-3 py-3 text-right font-semibold text-slate-800 dark:text-slate-100 whitespace-nowrap">
                      {fmtAmount(item.finalized_amount)}
                    </td>

                    {/* Finalized On */}
                    <td className="px-3 py-3 text-slate-600 dark:text-slate-400 whitespace-nowrap">
                      {fmtDate(item.finalized_on)}
                    </td>

                    {/* Paid Amount */}
                    <td className="px-3 py-3 text-right whitespace-nowrap">
                      {item.paid_amount != null ? (
                        <span className="font-semibold text-emerald-600 dark:text-emerald-400">
                          {fmtAmount(item.paid_amount)}
                        </span>
                      ) : (
                        <span className="text-slate-400">—</span>
                      )}
                    </td>

                    {/* Paid On */}
                    <td className="px-3 py-3 text-slate-600 dark:text-slate-400 whitespace-nowrap">
                      {fmtDate(item.paid_on)}
                    </td>

                    {/* Payroll Module */}
                    <td className="px-3 py-3 text-slate-700 dark:text-slate-300 whitespace-nowrap">
                      {item.payroll_module || "—"}
                    </td>

                    {/* Payroll Group */}
                    <td className="px-3 py-3 whitespace-nowrap">
                      <span className="text-slate-700 dark:text-slate-300">
                        {item.payroll_group_name || "—"}
                      </span>
                    </td>

                    {/* Action */}
                    <td className="px-3 py-3 whitespace-nowrap">
                      <button
                        onClick={() => setSelectedId(item.id)}
                        className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-[11px] font-medium text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-950/40 border border-blue-200 dark:border-blue-900/50 transition-colors"
                      >
                        <Eye className="w-3 h-3" />
                        View
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* ── Pagination ── */}
        {!isLoading && !isError && pagination.total_records > 0 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-xs text-slate-500 dark:text-slate-400">
            <span>
              Showing {Math.min((page - 1) * pageSize + 1, pagination.total_records)}–{Math.min(page * pageSize, pagination.total_records)} of {pagination.total_records} records
            </span>
            <div className="flex items-center gap-1">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="p-1.5 rounded-md hover:bg-slate-100 dark:hover:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                <ChevronLeft className="w-3.5 h-3.5" />
              </button>
              {Array.from({ length: pagination.total_pages }, (_, i) => i + 1)
                .filter((p) => p === 1 || p === pagination.total_pages || Math.abs(p - page) <= 1)
                .reduce<(number | "...")[]>((acc, p, idx, arr) => {
                  if (idx > 0 && p - (arr[idx - 1] as number) > 1) acc.push("...");
                  acc.push(p);
                  return acc;
                }, [])
                .map((p, idx) =>
                  p === "..." ? (
                    <span key={`ellipsis-${idx}`} className="px-1">…</span>
                  ) : (
                    <button
                      key={p}
                      onClick={() => setPage(Number(p))}
                      className={`w-7 h-7 rounded-md text-xs font-medium transition-colors ${
                        page === p
                          ? "bg-blue-600 text-white"
                          : "hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-400"
                      }`}
                    >
                      {p}
                    </button>
                  )
                )}
              <button
                onClick={() => setPage((p) => Math.min(pagination.total_pages, p + 1))}
                disabled={page >= pagination.total_pages}
                className="p-1.5 rounded-md hover:bg-slate-100 dark:hover:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Detail Drawer */}
      {selectedId !== null && (
        <DetailDrawer id={selectedId} onClose={() => setSelectedId(null)} />
      )}
    </ProtectedRoute>
  );
}
