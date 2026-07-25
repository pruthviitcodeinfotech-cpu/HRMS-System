"use client";

import React, { useState, useMemo, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import {
  Calendar,
  ChevronDown,
  FileSpreadsheet,
  FileText,
  AlertCircle,
  RefreshCw,
  Search,
} from "lucide-react";
import { toast } from "sonner";
import { useBranches } from "@/features/employees/hooks";
import jsPDF from "jspdf";
import autoTable from "jspdf-autotable";
import { useLoanTransactions } from "../hooks/use-loan-advance";
import { useArrearsLogs } from "../hooks/use-arrears";

const formatCurrency = (val: number): string => {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2,
  }).format(val || 0);
};

const formatDateReadable = (dateStr: string): string => {
  if (!dateStr) return "-";
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return dateStr;
    return d.toLocaleDateString("en-GB", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    });
  } catch {
    return dateStr;
  }
};

export const LoanArrearsLogView: React.FC = () => {
  const searchParams = useSearchParams();
  const paramModule = searchParams.get("module");

  const todayStr = new Date().toISOString().split("T")[0];
  const firstDayOfMonth = new Date(new Date().getFullYear(), new Date().getMonth(), 1)
    .toISOString()
    .split("T")[0];

  const defaultModule: "Loan & Advance" | "Arrears" | "All" =
    paramModule === "Arrears"
      ? "Arrears"
      : paramModule === "Loan & Advance"
      ? "Loan & Advance"
      : "All";

  // Input Filter Controls
  const [dateFrom, setDateFrom] = useState(firstDayOfMonth);
  const [dateTo, setDateTo] = useState(todayStr);
  const [selectedBranchId, setSelectedBranchId] = useState<string>("");
  const [moduleFilter, setModuleFilter] = useState<"Loan & Advance" | "Arrears" | "All">(
    defaultModule
  );

  // Sync state if query param changes
  useEffect(() => {
    if (paramModule === "Arrears") {
      setModuleFilter("Arrears");
      setAppliedFilters((prev) => ({ ...prev, moduleFilter: "Arrears" }));
    } else if (paramModule === "Loan & Advance") {
      setModuleFilter("Loan & Advance");
      setAppliedFilters((prev) => ({ ...prev, moduleFilter: "Loan & Advance" }));
    }
  }, [paramModule]);

  // Applied Filter State (triggers API query update on Search click)
  const [appliedFilters, setAppliedFilters] = useState({
    dateFrom: firstDayOfMonth,
    dateTo: todayStr,
    branchId: "",
    moduleFilter: defaultModule,
  });

  // Sorting & Pagination State
  const [sortField, setSortField] = useState("transaction_date");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  // Master Branch Options (Single Source of Truth per AGENTS.md rule)
  const { data: branchData } = useBranches({ page: 1, page_size: 100 });
  const branchList = branchData?.items || [];

  // 1. Live Query for Loans & Advances
  const isLoanActive =
    appliedFilters.moduleFilter === "Loan & Advance" || appliedFilters.moduleFilter === "All";
  const {
    data: loanLogsData,
    isLoading: isLoanLoading,
    isError: isLoanError,
    refetch: refetchLoan,
  } = useLoanTransactions(
    {
      page: currentPage,
      page_size: pageSize,
      date_from: appliedFilters.dateFrom || undefined,
      date_to: appliedFilters.dateTo || undefined,
      branch_id: appliedFilters.branchId ? Number(appliedFilters.branchId) : undefined,
      sort_by: sortField,
      sort_order: sortOrder,
    },
    isLoanActive
  );

  // 2. Live Query for Arrears Logs
  const isArrearsActive =
    appliedFilters.moduleFilter === "Arrears" || appliedFilters.moduleFilter === "All";
  const {
    data: arrearsLogsData,
    isLoading: isArrearsLoading,
    isError: isArrearsError,
    refetch: refetchArrears,
  } = useArrearsLogs(
    {
      page: currentPage,
      page_size: pageSize,
      date_from: appliedFilters.dateFrom || undefined,
      date_to: appliedFilters.dateTo || undefined,
      sort_by: sortField,
      sort_order: sortOrder,
    },
    isArrearsActive
  );

  const isLoading = isLoanActive && isArrearsActive ? isLoanLoading || isArrearsLoading : isLoanActive ? isLoanLoading : isArrearsLoading;
  const isError = isLoanActive && isArrearsActive ? isLoanError && isArrearsError : isLoanActive ? isLoanError : isArrearsError;

  const rawLogs = useMemo(() => {
    if (appliedFilters.moduleFilter === "Arrears") {
      const items = arrearsLogsData?.items || [];
      return items.map((item: any) => ({
        id: item.id || `arr-${Math.random()}`,
        employee_id: item.employee_id,
        employee_code: item.employee_code || item.employee_id ? `EMP-${item.employee_id}` : "-",
        employee_name: item.employee_name || `Employee #${item.employee_id}`,
        transaction_date: item.transaction_date,
        type_label: "Arrears",
        transaction_type: item.transaction_type || "Debit",
        amount: Number(item.amount || 0),
        installment_amount: null,
        comment: item.comment || item.remarks || "--",
      }));
    }

    if (appliedFilters.moduleFilter === "Loan & Advance") {
      const items = loanLogsData?.items || [];
      return items.map((item: any) => ({
        id: item.id,
        employee_id: item.employee_id,
        employee_code: item.employee_code || `EMP-${item.employee_id}`,
        employee_name: item.employee_name || `Employee #${item.employee_id}`,
        transaction_date: item.transaction_date,
        type_label: item.type_label ? item.type_label.charAt(0).toUpperCase() + item.type_label.slice(1) : "Loan",
        transaction_type: item.transaction_type ? item.transaction_type.charAt(0).toUpperCase() + item.transaction_type.slice(1) : "Debit",
        amount: Number(item.amount || 0),
        installment_amount: item.installment_amount ? Number(item.installment_amount) : null,
        comment: item.comment || item.remarks || "--",
      }));
    }

    // Merge both for "All"
    const loanItems = (loanLogsData?.items || []).map((item: any) => ({
      id: `loan-${item.id}`,
      employee_id: item.employee_id,
      employee_code: item.employee_code || `EMP-${item.employee_id}`,
      employee_name: item.employee_name || `Employee #${item.employee_id}`,
      transaction_date: item.transaction_date,
      type_label: item.type_label ? item.type_label.charAt(0).toUpperCase() + item.type_label.slice(1) : "Loan",
      transaction_type: item.transaction_type ? item.transaction_type.charAt(0).toUpperCase() + item.transaction_type.slice(1) : "Debit",
      amount: Number(item.amount || 0),
      installment_amount: item.installment_amount ? Number(item.installment_amount) : null,
      comment: item.comment || item.remarks || "--",
    }));

    const arrearsItems = (arrearsLogsData?.items || []).map((item: any) => ({
      id: `arr-${item.id}`,
      employee_id: item.employee_id,
      employee_code: item.employee_code || `EMP-${item.employee_id}`,
      employee_name: item.employee_name || `Employee #${item.employee_id}`,
      transaction_date: item.transaction_date,
      type_label: "Arrears",
      transaction_type: item.transaction_type || "Debit",
      amount: Number(item.amount || 0),
      installment_amount: null,
      comment: item.comment || item.remarks || "--",
    }));

    const combined = [...loanItems, ...arrearsItems];
    combined.sort((a, b) => (a.transaction_date < b.transaction_date ? 1 : -1));
    return combined;
  }, [appliedFilters.moduleFilter, loanLogsData, arrearsLogsData]);

  const totalRecords =
    appliedFilters.moduleFilter === "Arrears"
      ? arrearsLogsData?.pagination?.total_records || rawLogs.length
      : appliedFilters.moduleFilter === "Loan & Advance"
      ? loanLogsData?.pagination?.total_records || rawLogs.length
      : rawLogs.length;

  const totalPages = Math.ceil(totalRecords / pageSize) || 1;

  // Search Click Handler
  const handleSearch = () => {
    setAppliedFilters({
      dateFrom,
      dateTo,
      branchId: selectedBranchId,
      moduleFilter,
    });
    setCurrentPage(1);
    toast.success("Log filters applied successfully!");
  };

  const toggleSort = (field: string) => {
    if (sortField === field) {
      setSortOrder((prev) => (prev === "asc" ? "desc" : "asc"));
    } else {
      setSortField(field);
      setSortOrder("asc");
    }
  };

  // Real Excel/CSV Export Handler
  const handleExportExcel = () => {
    if (rawLogs.length === 0) {
      toast.error("No log entries to export.");
      return;
    }

    const headers = [
      "Employee ID",
      "Employee Name",
      "Transaction Date",
      "Type",
      "Transaction",
      "Amount",
      "Installment",
      "Comment",
    ];

    const rows = rawLogs.map((log) => [
      log.employee_code || log.employee_id,
      `"${log.employee_name || ""}"`,
      log.transaction_date,
      log.type_label,
      log.transaction_type,
      log.amount,
      log.installment_amount ? log.installment_amount : "-",
      `"${log.comment || ""}"`,
    ]);

    const csvContent = [headers.join(","), ...rows.map((r) => r.join(","))].join("\n");
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute(
      "download",
      `loan_and_arrears_log_${new Date().toISOString().split("T")[0]}.csv`
    );
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    toast.success("Log exported to CSV successfully!");
  };

  // Real PDF Export Handler
  const handleExportPDF = () => {
    if (rawLogs.length === 0) {
      toast.error("No log entries to export.");
      return;
    }

    try {
      const doc = new jsPDF({ orientation: "landscape" });

      doc.setFontSize(16);
      doc.setTextColor(0, 112, 224); // Petpooja Blue #0070e0
      doc.text("Loan & Arrears Log Report", 14, 18);

      doc.setFontSize(9);
      doc.setTextColor(100, 116, 139);
      doc.text(
        `Period: ${formatDateReadable(appliedFilters.dateFrom)} to ${formatDateReadable(appliedFilters.dateTo)} | Total Records: ${totalRecords}`,
        14,
        25
      );

      const tableHeaders = [
        [
          "Employee ID",
          "Employee Name",
          "Transaction Date",
          "Type",
          "Transaction",
          "Amount (INR)",
          "Installment",
          "Comment",
        ],
      ];

      const tableRows = rawLogs.map((log) => [
        log.employee_code || String(log.employee_id),
        log.employee_name || `Employee #${log.employee_id}`,
        formatDateReadable(log.transaction_date),
        log.type_label,
        log.transaction_type,
        `Rs. ${Number(log.amount || 0).toLocaleString("en-IN", { minimumFractionDigits: 2 })}`,
        log.installment_amount ? `Rs. ${Number(log.installment_amount).toLocaleString("en-IN", { minimumFractionDigits: 2 })}` : "--",
        log.comment || "--",
      ]);

      autoTable(doc, {
        head: tableHeaders,
        body: tableRows,
        startY: 30,
        styles: { fontSize: 8, cellPadding: 3 },
        headStyles: {
          fillColor: [0, 112, 224],
          textColor: [255, 255, 255],
          fontStyle: "bold",
        },
        alternateRowStyles: { fillColor: [248, 250, 252] },
      });

      doc.save(`loan_and_arrears_log_${new Date().toISOString().split("T")[0]}.pdf`);
      toast.success("Log PDF downloaded successfully!");
    } catch {
      toast.error("Failed to generate PDF download.");
    }
  };

  return (
    <div className="p-6 space-y-5 max-w-[1600px] mx-auto text-slate-800 dark:text-slate-100 font-sans">
      {/* Header Title */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
          {appliedFilters.moduleFilter === "Arrears"
            ? "Arrears Log"
            : appliedFilters.moduleFilter === "Loan & Advance"
            ? "Loan & Advance Log"
            : "Arrears Log"}
        </h1>
      </div>

      {/* Filter Toolbar (Matches Petpooja UI Screenshot Exactly) */}
      <div className="bg-white dark:bg-slate-900 p-4 border border-slate-200 dark:border-slate-800 rounded-xl shadow-xs flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-3">
          {/* 1. Date Range Picker */}
          <div className="flex items-center bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 hover:border-slate-400 rounded-lg px-3 py-1.5 text-xs text-slate-700 dark:text-slate-200 shadow-xs">
            <Calendar className="w-3.5 h-3.5 text-slate-400 mr-2" />
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              className="bg-transparent focus:outline-none text-xs font-medium cursor-pointer"
            />
            <span className="mx-2 text-slate-400">—</span>
            <input
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              className="bg-transparent focus:outline-none text-xs font-medium cursor-pointer"
            />
          </div>

          {/* 2. Choose Branch Dropdown */}
          <div className="relative">
            <select
              aria-label="Choose Branch"
              value={selectedBranchId}
              onChange={(e) => setSelectedBranchId(e.target.value)}
              className="appearance-none bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 hover:border-slate-400 rounded-lg px-3.5 py-2 pr-9 text-xs font-medium text-slate-700 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer min-w-[150px] shadow-xs"
            >
              <option value="">Choose Branch</option>
              {branchList.map((b) => (
                <option key={b.branch_id} value={b.branch_id.toString()}>
                  {b.branch_name}
                </option>
              ))}
            </select>
            <ChevronDown className="w-3.5 h-3.5 text-slate-500 absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none" />
          </div>

          {/* 3. Module Dropdown */}
          <div className="relative">
            <select
              aria-label="Filter Module"
              value={moduleFilter}
              onChange={(e) =>
                setModuleFilter(e.target.value as "Loan & Advance" | "Arrears" | "All")
              }
              className="appearance-none bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 hover:border-slate-400 rounded-lg px-3.5 py-2 pr-9 text-xs font-medium text-slate-700 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer min-w-[140px] shadow-xs"
            >
              <option value="Loan & Advance">Loan & Advance</option>
              <option value="Arrears">Arrears</option>
              <option value="All">All</option>
            </select>
            <ChevronDown className="w-3.5 h-3.5 text-slate-500 absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none" />
          </div>

          {/* 4. Primary Blue Search Button */}
          <button
            type="button"
            onClick={handleSearch}
            className="px-5 py-2 bg-[#0070e0] hover:bg-blue-700 text-white rounded-lg text-xs font-bold transition-colors cursor-pointer shadow-xs"
          >
            Search
          </button>
        </div>

        {/* Right Export Action Buttons */}
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleExportExcel}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 rounded-lg text-xs font-semibold transition-colors cursor-pointer shadow-xs"
          >
            <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-600" />
            <span>Export Excel</span>
          </button>

          <button
            type="button"
            onClick={handleExportPDF}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 rounded-lg text-xs font-semibold transition-colors cursor-pointer shadow-xs"
          >
            <FileText className="w-3.5 h-3.5 text-red-500" />
            <span>Export PDF</span>
          </button>
        </div>
      </div>

      {/* Main Data Table Container */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-xs overflow-hidden">
        {/* Loading Skeleton */}
        {isLoading && (
          <div className="p-6 space-y-4">
            <div className="h-8 bg-slate-100 dark:bg-slate-800 rounded-lg animate-pulse" />
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-12 bg-slate-50 dark:bg-slate-800/50 rounded-lg animate-pulse" />
            ))}
          </div>
        )}

        {/* Error State */}
        {!isLoading && isError && (
          <div className="p-12 text-center flex flex-col items-center justify-center space-y-4">
            <div className="w-14 h-14 bg-red-50 dark:bg-red-950/40 rounded-full flex items-center justify-center text-red-500">
              <AlertCircle className="w-7 h-7" />
            </div>
            <div className="space-y-1">
              <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">
                Failed to Load Log Data
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                An error occurred while fetching log entries. Please retry.
              </p>
            </div>
            <button
              type="button"
              onClick={() => {
                if (isLoanActive) refetchLoan();
                if (isArrearsActive) refetchArrears();
              }}
              className="inline-flex items-center gap-2 px-4 py-2 bg-[#0070e0] hover:bg-blue-700 text-white text-xs font-bold rounded-lg transition-colors cursor-pointer"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Retry</span>
            </button>
          </div>
        )}

        {/* Empty State */}
        {!isLoading && !isError && rawLogs.length === 0 && (
          <div className="p-16 text-center flex flex-col items-center justify-center space-y-3">
            <div className="w-16 h-16 bg-[#eaf4fd] dark:bg-slate-800 rounded-full flex items-center justify-center text-[#0070e0]">
              <Search className="w-8 h-8 stroke-[2.5]" />
            </div>
            <h3 className="text-sm font-bold text-slate-700 dark:text-slate-300">
              No Data Found
            </h3>
            <p className="text-xs text-slate-500 max-w-sm">
              No log entries found matching your selected date range and filters.
            </p>
          </div>
        )}

        {/* Data Table (Matches Reference Screenshot Headers & Layout) */}
        {!isLoading && !isError && rawLogs.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-[#eaf4fd] dark:bg-slate-800/90 text-slate-900 dark:text-slate-100 font-bold border-b border-slate-200 dark:border-slate-700">
                  <th
                    onClick={() => toggleSort("employee_id")}
                    className="py-3 px-4 cursor-pointer hover:bg-slate-200/50 dark:hover:bg-slate-700/50 select-none whitespace-nowrap"
                  >
                    <div className="flex items-center gap-1">
                      <span>Employee ID</span>
                      <span className="text-[10px] text-slate-400">↕</span>
                    </div>
                  </th>
                  <th
                    onClick={() => toggleSort("employee_name")}
                    className="py-3 px-4 cursor-pointer hover:bg-slate-200/50 dark:hover:bg-slate-700/50 select-none whitespace-nowrap"
                  >
                    <div className="flex items-center gap-1">
                      <span>Employee Name</span>
                      <span className="text-[10px] text-slate-400">↕</span>
                    </div>
                  </th>
                  <th
                    onClick={() => toggleSort("transaction_date")}
                    className="py-3 px-4 cursor-pointer hover:bg-slate-200/50 dark:hover:bg-slate-700/50 select-none whitespace-nowrap"
                  >
                    <div className="flex items-center gap-1">
                      <span>Transaction Date</span>
                      <span className="text-[10px] text-slate-400">↕</span>
                    </div>
                  </th>
                  <th
                    onClick={() => toggleSort("type_label")}
                    className="py-3 px-4 cursor-pointer hover:bg-slate-200/50 dark:hover:bg-slate-700/50 select-none whitespace-nowrap"
                  >
                    <div className="flex items-center gap-1">
                      <span>Type</span>
                      <span className="text-[10px] text-slate-400">↕</span>
                    </div>
                  </th>
                  <th
                    onClick={() => toggleSort("transaction_type")}
                    className="py-3 px-4 cursor-pointer hover:bg-slate-200/50 dark:hover:bg-slate-700/50 select-none whitespace-nowrap"
                  >
                    <div className="flex items-center gap-1">
                      <span>Transaction</span>
                      <span className="text-[10px] text-slate-400">↕</span>
                    </div>
                  </th>
                  <th className="py-3 px-4 whitespace-nowrap">Amount</th>
                  <th className="py-3 px-4 whitespace-nowrap">Installment</th>
                  <th className="py-3 px-4 whitespace-nowrap">Comment</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {rawLogs.map((log) => (
                  <tr
                    key={log.id}
                    className="hover:bg-slate-50/80 dark:hover:bg-slate-800/40 transition-colors"
                  >
                    {/* 1. Employee ID */}
                    <td className="py-3 px-4 font-semibold text-slate-900 dark:text-slate-100 whitespace-nowrap">
                      {log.employee_code || log.employee_id}
                    </td>
                    {/* 2. Employee Name */}
                    <td className="py-3 px-4 whitespace-nowrap font-medium text-slate-800 dark:text-slate-200">
                      {log.employee_name || `Employee #${log.employee_id}`}
                    </td>
                    {/* 3. Transaction Date */}
                    <td className="py-3 px-4 whitespace-nowrap text-slate-600 dark:text-slate-300">
                      {formatDateReadable(log.transaction_date)}
                    </td>
                    {/* 4. Type */}
                    <td className="py-3 px-4 whitespace-nowrap text-slate-700 dark:text-slate-300 capitalize font-medium">
                      {log.type_label}
                    </td>
                    {/* 5. Transaction (Debit / Credit) */}
                    <td className="py-3 px-4 whitespace-nowrap font-medium capitalize text-slate-700 dark:text-slate-300">
                      {log.transaction_type}
                    </td>
                    {/* 6. Amount */}
                    <td className="py-3 px-4 font-semibold text-slate-900 dark:text-slate-100 whitespace-nowrap">
                      {formatCurrency(Number(log.amount || 0))}
                    </td>
                    {/* 7. Installment */}
                    <td className="py-3 px-4 text-slate-600 dark:text-slate-400 whitespace-nowrap">
                      {log.installment_amount && Number(log.installment_amount) > 0
                        ? formatCurrency(Number(log.installment_amount))
                        : "--"}
                    </td>
                    {/* 8. Comment */}
                    <td className="py-3 px-4 text-slate-600 dark:text-slate-400 max-w-xs truncate">
                      {log.comment || "--"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Footer Pagination Bar */}
        {!isLoading && !isError && rawLogs.length > 0 && (
          <div className="px-4 py-3 border-t border-slate-200 dark:border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs">
            <div className="text-slate-500 font-medium">
              Showing {(currentPage - 1) * pageSize + 1} to{" "}
              {Math.min(currentPage * pageSize, totalRecords)} of {totalRecords} Results
            </div>

            <div className="flex items-center gap-3">
              {/* Page Size Selector */}
              <div className="relative">
                <select
                  aria-label="Records per page"
                  value={pageSize}
                  onChange={(e) => {
                    setPageSize(Number(e.target.value));
                    setCurrentPage(1);
                  }}
                  className="appearance-none bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-1.5 pr-8 text-xs font-semibold text-slate-700 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer"
                >
                  <option value={10}>10 / Page</option>
                  <option value={25}>25 / Page</option>
                  <option value={50}>50 / Page</option>
                  <option value={100}>100 / Page</option>
                </select>
                <ChevronDown className="w-3.5 h-3.5 text-slate-500 absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
              </div>

              {/* Previous Button */}
              <button
                type="button"
                disabled={currentPage === 1}
                onClick={() => setCurrentPage((prev) => Math.max(prev - 1, 1))}
                className="px-3 py-1.5 border border-slate-300 dark:border-slate-700 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer font-medium text-slate-700 dark:text-slate-300"
              >
                Previous
              </button>

              {/* Active Page Number */}
              <span className="w-7 h-7 flex items-center justify-center bg-[#0070e0] text-white font-bold rounded-lg text-xs">
                {currentPage}
              </span>

              {/* Next Button */}
              <button
                type="button"
                disabled={currentPage >= totalPages}
                onClick={() => setCurrentPage((prev) => Math.min(prev + 1, totalPages))}
                className="px-3 py-1.5 border border-slate-300 dark:border-slate-700 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer font-medium text-slate-700 dark:text-slate-300"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
