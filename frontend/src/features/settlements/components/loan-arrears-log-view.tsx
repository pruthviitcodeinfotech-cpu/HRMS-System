"use client";

import React, { useState, useMemo } from "react";
import {
  Calendar,
  ChevronDown,
  FileSpreadsheet,
  FileText,
  ChevronLeft,
  ChevronRight,
  AlertCircle,
  RefreshCw,
  Search,
} from "lucide-react";
import { toast } from "sonner";
import { useBranches } from "@/features/employees/hooks";
import jsPDF from "jspdf";
import autoTable from "jspdf-autotable";
import { useArrearsLogs } from "../hooks/use-arrears";

const formatCurrency = (val: number): string => {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2,
  }).format(val || 0);
};

export const LoanArrearsLogView: React.FC = () => {
  // Input Filter Controls
  const [dateFrom, setDateFrom] = useState("2026-07-01");
  const [dateTo, setDateTo] = useState("2026-07-22");
  const [selectedBranch, setSelectedBranch] = useState("");
  const [typeFilter, setTypeFilter] = useState<"All" | "Loan" | "Arrears">("All");

  // Applied Filter State (updates on Search click)
  const [appliedFilters, setAppliedFilters] = useState({
    dateFrom: "2026-07-01",
    dateTo: "2026-07-22",
    selectedBranch: "",
    typeFilter: "All" as "All" | "Loan" | "Arrears",
  });

  // Sorting & Pagination
  const [sortField, setSortField] = useState("transaction_date");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 10;

  // Master Branch Options
  const { data: branchData } = useBranches({ page: 1, page_size: 100 });
  const branchList = branchData?.items || [];

  // Live Query for Arrears Activity & Ledger Logs
  const {
    data: logsData,
    isLoading,
    isError,
    refetch,
  } = useArrearsLogs({
    page: currentPage,
    page_size: pageSize,
    date_from: dateFrom || undefined,
    date_to: dateTo || undefined,
    sort_by: sortField,
    sort_order: sortOrder,
  });

  const rawLogs = useMemo(() => logsData?.items || [], [logsData]);

  // Search Click Handler
  const handleSearch = () => {
    setAppliedFilters({
      dateFrom,
      dateTo,
      selectedBranch,
      typeFilter,
    });
    setCurrentPage(1);
    toast.success("Filters applied successfully!");
  };

  // Filtered Logs Calculation
  const filteredLogs = useMemo(() => {
    return rawLogs.filter((log) => {
      // 1. Date Range Filter
      if (appliedFilters.dateFrom && log.transaction_date < appliedFilters.dateFrom) {
        return false;
      }
      if (appliedFilters.dateTo && log.transaction_date > appliedFilters.dateTo) {
        return false;
      }

      // 2. Type Filter
      if (appliedFilters.typeFilter === "Arrears") {
        if (
          log.transaction_type !== "credit" &&
          log.transaction_type !== "debit" &&
          log.transaction_type !== "adjustment"
        ) {
          return false;
        }
      } else if (appliedFilters.typeFilter === "Loan") {
        if (
          log.transaction_type !== "disbursement" &&
          log.transaction_type !== "repayment"
        ) {
          return false;
        }
      }

      // 3. Branch Filter
      if (appliedFilters.selectedBranch) {
        if (log.branch_name && log.branch_name !== appliedFilters.selectedBranch) {
          return false;
        }
      }

      return true;
    });
  }, [rawLogs, appliedFilters]);

  const totalRecords = filteredLogs.length;
  const totalPages = Math.ceil(totalRecords / pageSize) || 1;
  const paginatedLogs = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return filteredLogs.slice(start, start + pageSize);
  }, [filteredLogs, currentPage, pageSize]);

  const toggleSort = (field: string) => {
    if (sortField === field) {
      setSortOrder((prev) => (prev === "asc" ? "desc" : "asc"));
    } else {
      setSortField(field);
      setSortOrder("asc");
    }
  };

  // Real CSV Export Handler
  const handleExportExcel = () => {
    if (filteredLogs.length === 0) {
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

    const rows = filteredLogs.map((log) => [
      log.employee_code || `EMP-${log.employee_id}`,
      `"${log.employee_name || ""}"`,
      log.transaction_date,
      log.transaction_type === "credit" || log.transaction_type === "debit" ? "Arrears" : "Loan",
      log.source || "Manual",
      log.amount,
      "-",
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
    toast.success("Loan & Arrears Log exported to CSV successfully!");
  };

  // Real PDF Direct File Download Export Handler
  const handleExportPDF = () => {
    if (filteredLogs.length === 0) {
      toast.error("No log entries to export.");
      return;
    }

    try {
      const doc = new jsPDF({ orientation: "landscape" });

      // Document Title Header
      doc.setFontSize(16);
      doc.setTextColor(0, 112, 224); // Petpooja Blue #0070e0
      doc.text("Loan & Arrears Log Report", 14, 18);

      // Metadata Subtitle
      doc.setFontSize(9);
      doc.setTextColor(100, 116, 139);
      doc.text(
        `Generated Date: ${new Date().toLocaleDateString("en-IN")} | Total Records: ${filteredLogs.length}`,
        14,
        25
      );

      // Table Headers & Rows
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

      const tableRows = filteredLogs.map((log) => [
        log.employee_code || `EMP-${log.employee_id}`,
        log.employee_name || `Employee #${log.employee_id}`,
        log.transaction_date,
        log.transaction_type === "credit" || log.transaction_type === "debit"
          ? "ARREARS"
          : "LOAN",
        log.source || "Manual",
        `Rs. ${log.amount.toLocaleString("en-IN", { minimumFractionDigits: 2 })}`,
        "-",
        log.comment || "-",
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
      toast.success("Loan & Arrears Log PDF downloaded successfully!");
    } catch {
      toast.error("Failed to generate PDF download.");
    }
  };

  return (
    <div className="p-6 space-y-6 max-w-[1600px] mx-auto text-slate-800 dark:text-slate-100">
      {/* Header Title */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
          Loan & Arrears Log
        </h1>
      </div>

      {/* Filter Toolbar (Matches Petpooja UI) */}
      <div className="bg-white dark:bg-slate-900 p-4 border border-slate-200 dark:border-slate-800 rounded-xl shadow-xs flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-3">
          {/* Date Range Selector */}
          <div className="flex items-center bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-700 dark:text-slate-200">
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

          {/* Branch Dropdown */}
          <div className="relative">
            <select
              aria-label="Choose Branch"
              value={selectedBranch}
              onChange={(e) => setSelectedBranch(e.target.value)}
              className="appearance-none bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 hover:border-slate-400 rounded-lg px-3.5 py-2 pr-9 text-xs font-semibold text-slate-700 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer min-w-[160px]"
            >
              <option value="">Choose Branch</option>
              {branchList.map((b) => (
                <option key={b.branch_id} value={b.branch_name}>
                  {b.branch_name}
                </option>
              ))}
            </select>
            <ChevronDown className="w-3.5 h-3.5 text-slate-500 absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none" />
          </div>

          {/* Type Filter Dropdown */}
          <div className="relative">
            <select
              aria-label="Filter Type"
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value as "All" | "Loan" | "Arrears")}
              className="appearance-none bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 hover:border-slate-400 rounded-lg px-3.5 py-2 pr-9 text-xs font-semibold text-slate-700 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer min-w-[120px]"
            >
              <option value="All">All Types</option>
              <option value="Arrears">Arrears</option>
              <option value="Loan">Loan</option>
            </select>
            <ChevronDown className="w-3.5 h-3.5 text-slate-500 absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none" />
          </div>

          {/* Primary Blue Search Button */}
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
        {/* Loading Skeleton View */}
        {isLoading && (
          <div className="p-6 space-y-4">
            <div className="h-8 bg-slate-100 dark:bg-slate-800 rounded-lg animate-pulse" />
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-12 bg-slate-50 dark:bg-slate-800/50 rounded-lg animate-pulse" />
            ))}
          </div>
        )}

        {/* Error State View */}
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
                An error occurred while fetching loan and arrears logs. Please retry.
              </p>
            </div>
            <button
              type="button"
              onClick={() => refetch()}
              className="inline-flex items-center gap-2 px-4 py-2 bg-[#0070e0] hover:bg-blue-700 text-white text-xs font-bold rounded-lg transition-colors cursor-pointer"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Retry</span>
            </button>
          </div>
        )}

        {/* Empty State View */}
        {!isLoading && !isError && paginatedLogs.length === 0 && (
          <div className="p-16 text-center flex flex-col items-center justify-center space-y-3">
            <div className="w-16 h-16 bg-[#eaf4fd] dark:bg-slate-800 rounded-full flex items-center justify-center text-[#0070e0]">
              <Search className="w-8 h-8 stroke-[2.5]" />
            </div>
            <h3 className="text-sm font-bold text-slate-700 dark:text-slate-300">
              No Data Found
            </h3>
            <p className="text-xs text-slate-500 max-w-sm">
              No loan or arrears log entries found matching your selected date range and filters.
            </p>
          </div>
        )}

        {/* Data Table */}
        {!isLoading && !isError && paginatedLogs.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-[#eaf4fd] dark:bg-slate-800 text-slate-900 dark:text-slate-100 font-bold border-b border-slate-200 dark:border-slate-700">
                  <th
                    onClick={() => toggleSort("employee_id")}
                    className="py-3 px-4 cursor-pointer hover:bg-slate-200/50 dark:hover:bg-slate-700/50 select-none whitespace-nowrap"
                  >

                      Employee ID ↕
                      {sortField === "employee_id" && (
                        <span>{sortOrder === "asc" ? " ↑" : " ↓"}</span>
                      )}
                  </th>
                  <th
                    onClick={() => toggleSort("employee_name")}
                    className="py-3 px-4 cursor-pointer hover:bg-slate-200/50 dark:hover:bg-slate-700/50 select-none whitespace-nowrap"
                  >

                      Employee Name ↕
                      {sortField === "employee_name" && (
                        <span>{sortOrder === "asc" ? " ↑" : " ↓"}</span>
                      )}
                  </th>
                  <th
                    onClick={() => toggleSort("transaction_date")}
                    className="py-3 px-4 cursor-pointer hover:bg-slate-200/50 dark:hover:bg-slate-700/50 select-none whitespace-nowrap"
                  >

                      Transaction Date ↕
                      {sortField === "transaction_date" && (
                        <span>{sortOrder === "asc" ? " ↑" : " ↓"}</span>
                      )}
                  </th>
                  <th
                    onClick={() => toggleSort("transaction_type")}
                    className="py-3 px-4 cursor-pointer hover:bg-slate-200/50 dark:hover:bg-slate-700/50 select-none whitespace-nowrap"
                  >

                      Type ↕
                      {sortField === "transaction_type" && (
                        <span>{sortOrder === "asc" ? " ↑" : " ↓"}</span>
                      )}
                  </th>
                  <th
                    onClick={() => toggleSort("source")}
                    className="py-3 px-4 cursor-pointer hover:bg-slate-200/50 dark:hover:bg-slate-700/50 select-none whitespace-nowrap"
                  >

                      Transaction ↕
                      {sortField === "source" && (
                        <span>{sortOrder === "asc" ? " ↑" : " ↓"}</span>
                      )}
                  </th>
                  <th className="py-3 px-4 text-right whitespace-nowrap">Amount</th>
                  <th className="py-3 px-4 text-center whitespace-nowrap">Installment</th>
                  <th className="py-3 px-4 whitespace-nowrap">Comment</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {paginatedLogs.map((log) => (
                  <tr
                    key={log.id}
                    className="hover:bg-slate-50/80 dark:hover:bg-slate-800/40 transition-colors"
                  >
                    <td className="py-3 px-4 font-bold text-slate-900 dark:text-slate-100 whitespace-nowrap">
                      {log.employee_code || `EMP-${log.employee_id}`}
                    </td>
                    <td className="py-3 px-4 whitespace-nowrap font-medium">
                      <div>{log.employee_name || `Employee #${log.employee_id}`}</div>
                    </td>
                    <td className="py-3 px-4 whitespace-nowrap text-slate-600 dark:text-slate-300">
                      {log.transaction_date}
                    </td>
                    <td className="py-3 px-4 whitespace-nowrap">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                          log.transaction_type === "credit" || log.transaction_type === "debit"
                            ? "bg-blue-50 text-blue-700 dark:bg-blue-950/40 dark:text-blue-400"
                            : "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-400"
                        }`}
                      >
                        {log.transaction_type === "credit" || log.transaction_type === "debit"
                          ? "ARREARS"
                          : "LOAN"}
                      </span>
                    </td>
                    <td className="py-3 px-4 whitespace-nowrap font-semibold text-slate-700 dark:text-slate-300 capitalize">
                      {log.source || "Manual"}
                    </td>
                    <td className="py-3 px-4 text-right font-bold text-emerald-600 dark:text-emerald-400 whitespace-nowrap">
                      {formatCurrency(log.amount)}
                    </td>
                    <td className="py-3 px-4 text-center text-slate-600 dark:text-slate-400 whitespace-nowrap">
                      -
                    </td>
                    <td className="py-3 px-4 text-slate-600 dark:text-slate-400">
                      {log.comment || "-"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Footer Pagination Bar */}
        {!isLoading && !isError && paginatedLogs.length > 0 && (
          <div className="px-4 py-3 border-t border-slate-200 dark:border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs">
            <div className="text-slate-500">
              Showing {(currentPage - 1) * pageSize + 1} to{" "}
              {Math.min(currentPage * pageSize, totalRecords)} of {totalRecords} records
            </div>

            <div className="flex items-center gap-2">
              <button
                type="button"
                disabled={currentPage === 1}
                onClick={() => setCurrentPage((prev) => Math.max(prev - 1, 1))}
                className="p-1.5 border border-slate-300 dark:border-slate-700 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>

              <span className="font-semibold text-slate-700 dark:text-slate-300 px-2">
                Page {currentPage} of {totalPages}
              </span>

              <button
                type="button"
                disabled={currentPage >= totalPages}
                onClick={() => setCurrentPage((prev) => Math.min(prev + 1, totalPages))}
                className="p-1.5 border border-slate-300 dark:border-slate-700 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
