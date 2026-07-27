"use client";

import React, { useState, useMemo, useEffect, useRef } from "react";
import {
  Search,
  ChevronDown,
  FileText,
  Plus,
  Edit2,
  Trash2,
  Lock,
  X,
  AlertCircle,
  RefreshCw,
  Loader2,
  MoreVertical,
  Info,
  ArrowUpDown,
} from "lucide-react";
import { toast } from "sonner";
import { useRouter } from "next/navigation";
import { useEmployees } from "@/features/employees/hooks";
import {
  useLoansAdvances,
  useLoanAdvanceLogs,
  useLoanAdvanceDetails,
  useCreateLoanAdvance,
  useCloseLoanAdvance,
  useDeleteLoanAdvance,
  useActiveLoansForEmployee,
  useSubmitLoanTransaction,
  useLoanTransactions,
  useUpdateInstallment,
} from "../hooks/use-loan-advance";
import { LoanAdvanceSchema } from "../types";

const formatCurrency = (val: number): string => {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2,
  }).format(val || 0);
};

const getErrorMessage = (err: unknown, fallback: string): string => {
  return (err as { response?: { data?: { message?: string } } })?.response?.data?.message || fallback;
};

export const LoanAdvanceView: React.FC = () => {
  const router = useRouter();
  // Filter & Pagination State
  const [statusFilter, setStatusFilter] = useState<
    "Active Loan/Advance" | "Closed Loan/Advance" | "All"
  >("Active Loan/Advance");
  const [searchQuery, setSearchQuery] = useState("");
  const [sortField, setSortField] = useState<string>("created_at");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  // Reset page when filter or search changes
  useEffect(() => {
    setCurrentPage(1);
  }, [statusFilter, searchQuery]);

  // Active Row 3-Dots Action Popover ID
  const [actionMenuOpenId, setActionMenuOpenId] = useState<number | null>(null);

  // Modal Control States
  const [showAddModal, setShowAddModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showDebitModal, setShowDebitModal] = useState(false);
  const [showLogsModal, setShowLogsModal] = useState(false);
  const [showItemLogsModal, setShowItemLogsModal] = useState(false);

  const [selectedLoan, setSelectedLoan] = useState<LoanAdvanceSchema | null>(null);
  const [confirmCloseId, setConfirmCloseId] = useState<number | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState<number | null>(null);

  // Phase 1 & 3 — Debit Amount Drawer Form State & Touched flags
  const [debitSelectLoanId, setDebitSelectLoanId] = useState("");
  const [debitComment, setDebitComment] = useState("");
  const [debitCommentTouched, setDebitCommentTouched] = useState(false);
  const [debitAmount, setDebitAmount] = useState("");
  const [debitAmountTouched, setDebitAmountTouched] = useState(false);
  const [debitDate, setDebitDate] = useState(() => new Date().toISOString().split("T")[0]);

  // Phase 1 — Transaction Logs Drawer UI State
  const [txLogFilter, setTxLogFilter] = useState("All");
  const [txLogPage, setTxLogPage] = useState(1);

  // Edit Installment Drawer State (Phase 1 Edit Installment UI)
  const [editSelectLoanId, setEditSelectLoanId] = useState<string>("");
  const [editNewInstallment, setEditNewInstallment] = useState<string>("");
  const [editNewInstallmentTouched, setEditNewInstallmentTouched] = useState<boolean>(false);
  const editSelectRef = useRef<HTMLSelectElement | null>(null);

  // Phase 5 — UX Polish: Ref & Focus first input on drawer open
  const firstSelectRef = useRef<HTMLSelectElement | null>(null);
  const txFilterSelectRef = useRef<HTMLSelectElement | null>(null);

  useEffect(() => {
    if (!showDebitModal) return;
    const timer = setTimeout(() => {
      firstSelectRef.current?.focus();
    }, 50);
    return () => clearTimeout(timer);
  }, [showDebitModal]);

  useEffect(() => {
    if (!showItemLogsModal) return;
    const timer = setTimeout(() => {
      txFilterSelectRef.current?.focus();
    }, 50);
    return () => clearTimeout(timer);
  }, [showItemLogsModal]);

  useEffect(() => {
    if (!showEditModal) return;
    const timer = setTimeout(() => {
      editSelectRef.current?.focus();
    }, 50);
    return () => clearTimeout(timer);
  }, [showEditModal]);
  // Form State for Add Loan / Advance
  const [formData, setFormData] = useState({
    employee_id: "",
    name: "",
    type: "loan" as "loan" | "advance",
    principal_amount: "",
    monthly_installment: "",
    transaction_date: new Date().toISOString().split("T")[0],
    comment: "",
  });

  // Reusing existing Employees module (Single Source of Truth per AGENTS.md rule)
  const { data: employeeData } = useEmployees({
    status: "active",
    page: 1,
    page_size: 100,
  });

  const activeEmployees = useMemo(() => {
    return employeeData?.items || [];
  }, [employeeData]);

  // Active Loans/Advances List Query
  const apiStatus =
    statusFilter === "Active Loan/Advance"
      ? "active"
      : statusFilter === "Closed Loan/Advance"
      ? "closed"
      : "all";

  const {
    data: loanResponse,
    isLoading,
    isError,
    refetch,
  } = useLoansAdvances({
    page: currentPage,
    page_size: pageSize,
    status: apiStatus,
    search: searchQuery || undefined,
    sort_by: sortField,
    sort_order: sortOrder,
  });

  // Org-wide Logs Query
  const { data: logsResponse, isLoading: isLogsLoading } = useLoanAdvanceLogs(
    { page: 1, page_size: 100 },
    showLogsModal
  );

  // Selected Loan Details Query (for single item transaction logs)
  const { data: itemDetailsData } = useLoanAdvanceDetails(
    showItemLogsModal && selectedLoan ? selectedLoan.id : null
  );

  // Active loans for selected employee (Phase 2 integration)
  const {
    data: activeLoansForEmp,
    isLoading: isActiveLoansLoading,
    isError: isEditLoansError,
    refetch: refetchEditLoans,
  } = useActiveLoansForEmployee(
    (showDebitModal || showEditModal || showItemLogsModal) && selectedLoan
      ? selectedLoan.employee_id
      : null
  );

  // Mutations
  const createMutation = useCreateLoanAdvance();
  const closeMutation = useCloseLoanAdvance();
  const deleteMutation = useDeleteLoanAdvance();
  const submitDebitMutation = useSubmitLoanTransaction();
  const updateInstallmentMutation = useUpdateInstallment();

  const loanItems = loanResponse?.items || [];
  const totalRecords = loanResponse?.pagination.total_records || 0;
  const totalPages = loanResponse?.pagination.total_pages || 1;

  // Active loans list for Debit Drawer dropdown
  const availableLoansList = useMemo(() => {
    if (activeLoansForEmp && activeLoansForEmp.length > 0) {
      return activeLoansForEmp;
    }
    if (selectedLoan) {
      return [selectedLoan];
    }
    return loanItems;
  }, [activeLoansForEmp, selectedLoan, loanItems]);

  // Active / all loans list for Transaction Logs Drawer dropdown filter
  const txFilterLoansList = useMemo(() => {
    const list = activeLoansForEmp && activeLoansForEmp.length > 0 ? activeLoansForEmp : availableLoansList;
    if (selectedLoan && !list.some((l) => l.id === selectedLoan.id)) {
      return [selectedLoan, ...list];
    }
    return list;
  }, [activeLoansForEmp, availableLoansList, selectedLoan]);

  // Phase 3 — Filter API loan_id computation
  const selectedTxLoanId = useMemo(() => {
    if (txLogFilter === "All" || !txLogFilter) return undefined;
    const parsedId = Number(txLogFilter);
    if (!isNaN(parsedId)) return parsedId;
    const found = txFilterLoansList.find((ln) => ln.name === txLogFilter);
    return found ? found.id : undefined;
  }, [txLogFilter, txFilterLoansList]);

  const {
    data: txLogsData,
    isLoading: isTxLogsLoading,
    isError: isTxLogsError,
    refetch: refetchTxLogs,
  } = useLoanTransactions(
    {
      employee_id: selectedLoan ? selectedLoan.employee_id : undefined,
      loan_id: selectedTxLoanId,
      page: txLogPage,
      page_size: 10,
    },
    showItemLogsModal && !!selectedLoan
  );

  // Selected loan object in Debit Drawer
  const selectedDebitLoanObj = useMemo(() => {
    if (!debitSelectLoanId) return null;
    return availableLoansList.find((ln) => ln.id === Number(debitSelectLoanId)) || null;
  }, [debitSelectLoanId, availableLoansList]);

  // Selected loan object in Edit Installment Drawer
  const selectedEditLoanObj = useMemo(() => {
    if (!editSelectLoanId) return null;
    return availableLoansList.find((ln) => ln.id === Number(editSelectLoanId)) || null;
  }, [editSelectLoanId, availableLoansList]);

  const editNewInstallmentNum = Number(editNewInstallment) || 0;
  const editOutstandingAmount = selectedEditLoanObj ? Number(selectedEditLoanObj.outstanding_amount) : 0;

  const isEditLoanClosed = useMemo(() => {
    if (!selectedEditLoanObj) return false;
    return selectedEditLoanObj.status === "closed" || (selectedEditLoanObj.status as string) === "cancelled";
  }, [selectedEditLoanObj]);

  const isEditLoanCompleted = useMemo(() => {
    if (!selectedEditLoanObj) return false;
    return editOutstandingAmount <= 0;
  }, [selectedEditLoanObj, editOutstandingAmount]);

  const isEditExceedingOutstanding = useMemo(() => {
    if (!selectedEditLoanObj || !editNewInstallment) return false;
    return editNewInstallmentNum > editOutstandingAmount;
  }, [selectedEditLoanObj, editNewInstallment, editNewInstallmentNum, editOutstandingAmount]);

  const isEditInstallmentValid = useMemo(() => {
    return (
      Boolean(editSelectLoanId) &&
      Boolean(selectedEditLoanObj) &&
      !isEditLoanClosed &&
      !isEditLoanCompleted &&
      Boolean(editNewInstallment) &&
      editNewInstallmentNum > 0 &&
      !isEditExceedingOutstanding
    );
  }, [
    editSelectLoanId,
    selectedEditLoanObj,
    isEditLoanClosed,
    isEditLoanCompleted,
    editNewInstallment,
    editNewInstallmentNum,
    isEditExceedingOutstanding,
  ]);

  // Phase 3 Validation calculations
  const debitAmountNum = Number(debitAmount) || 0;

  const isAmountExceeding = useMemo(() => {
    if (!selectedDebitLoanObj || !debitAmount) return false;
    return debitAmountNum > Number(selectedDebitLoanObj.outstanding_amount);
  }, [selectedDebitLoanObj, debitAmount, debitAmountNum]);

  const isLoanClosed = useMemo(() => {
    return selectedDebitLoanObj?.status === "closed";
  }, [selectedDebitLoanObj]);

  // Phase 3 — Form Validation logic
  const isDebitFormValid = useMemo(() => {
    return (
      Boolean(debitSelectLoanId) &&
      Boolean(selectedDebitLoanObj) &&
      !isLoanClosed &&
      Boolean(debitComment.trim()) &&
      Boolean(debitAmount) &&
      debitAmountNum > 0 &&
      !isAmountExceeding &&
      Boolean(debitDate)
    );
  }, [
    debitSelectLoanId,
    selectedDebitLoanObj,
    isLoanClosed,
    debitComment,
    debitAmount,
    debitAmountNum,
    isAmountExceeding,
    debitDate,
  ]);



  // Keyboard Access: ESC key closes Drawers
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        if (showDebitModal) {
          setShowDebitModal(false);
          setSelectedLoan(null);
        }
        if (showItemLogsModal) {
          setShowItemLogsModal(false);
          setSelectedLoan(null);
        }
        if (showEditModal) {
          setShowEditModal(false);
          setSelectedLoan(null);
        }
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [showDebitModal, showItemLogsModal, showEditModal]);

  // Selected Employee Info in Add Modal
  const selectedEmpObj = useMemo(() => {
    if (!formData.employee_id) return null;
    return activeEmployees.find(
      (emp) => emp.employee_id === Number(formData.employee_id)
    );
  }, [formData.employee_id, activeEmployees]);

  // Handle Sort Toggle
  const toggleSort = (field: string) => {
    if (sortField === field) {
      setSortOrder((prev) => (prev === "asc" ? "desc" : "asc"));
    } else {
      setSortField(field);
      setSortOrder("asc");
    }
  };

  // Submit Handler: Add Loan / Advance
  const handleAddSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.employee_id) {
      toast.error("Please select an employee");
      return;
    }
    if (!formData.name.trim()) {
      toast.error("Please enter Loan/Advance Name");
      return;
    }

    const principal = Number(formData.principal_amount);
    const installment = Number(formData.monthly_installment);

    if (!principal || principal <= 0) {
      toast.error("Please enter a valid Amount");
      return;
    }

    if (!installment || installment <= 0) {
      toast.error("Please enter a valid Monthly Installment");
      return;
    }

    if (installment > principal) {
      toast.error("Monthly installment cannot exceed principal amount");
      return;
    }

    createMutation.mutate(
      {
        employee_id: Number(formData.employee_id),
        name: formData.name,
        type: formData.type,
        principal_amount: principal,
        monthly_installment: installment,
        transaction_date: formData.transaction_date,
        comment: formData.comment,
      },
      {
        onSuccess: () => {
          toast.success(`${formData.type === "loan" ? "Loan" : "Advance"} created successfully!`);
          setShowAddModal(false);
          setFormData({
            employee_id: "",
            name: "",
            type: "loan",
            principal_amount: "",
            monthly_installment: "",
            transaction_date: new Date().toISOString().split("T")[0],
            comment: "",
          });
        },
        onError: (err: unknown) => {
          toast.error(getErrorMessage(err, "Failed to create Loan/Advance"));
        },
      }
    );
  };

  // Submit Handler: Edit Installment Save (Phase 3 Backend Integration)
  const handleEditSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!editSelectLoanId || !editNewInstallment || editNewInstallmentNum <= 0) return;

    updateInstallmentMutation.mutate(
      {
        loanId: Number(editSelectLoanId),
        installmentAmount: editNewInstallmentNum,
      },
      {
        onSuccess: () => {
          toast.success("Installment updated successfully");
          setShowEditModal(false);
          setSelectedLoan(null);
          setEditSelectLoanId("");
          setEditNewInstallment("");
          setEditNewInstallmentTouched(false);
        },
        onError: (err: unknown) => {
          toast.error(getErrorMessage(err, "Failed to update installment"));
        },
      }
    );
  };

  // Close Loan Handler
  const handleCloseLoan = (id: number) => {
    closeMutation.mutate(id, {
      onSuccess: () => {
        toast.success("Loan closed successfully!");
        setConfirmCloseId(null);
      },
      onError: (err: unknown) => {
        toast.error(getErrorMessage(err, "Failed to close Loan"));
      },
    });
  };

  // Delete Loan Handler
  const handleDeleteLoan = (id: number) => {
    deleteMutation.mutate(id, {
      onSuccess: () => {
        toast.success("Loan record deleted!");
        setConfirmDeleteId(null);
      },
      onError: (err: unknown) => {
        toast.error(getErrorMessage(err, "Failed to delete Loan record"));
      },
    });
  };

  return (
    <div className="p-6 space-y-6 max-w-[1600px] mx-auto text-slate-800 dark:text-slate-100 font-sans">
      {/* 1. Petpooja Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        {/* Title + Count */}
        <div className="flex items-center gap-2">
          <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
            Loan & Advance
          </h1>
          <span className="text-xl font-bold text-slate-700 dark:text-slate-300">
            ({totalRecords})
          </span>
        </div>

        {/* Action Controls Toolbar */}
        <div className="flex flex-wrap items-center gap-3">
          {/* Status Dropdown Filter */}
          <div className="relative">
            <select
              aria-label="Filter Loan Status"
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(
                  e.target.value as "Active Loan/Advance" | "Closed Loan/Advance" | "All"
                );
                setCurrentPage(1);
              }}
              className="appearance-none bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 hover:border-slate-400 rounded-lg px-3.5 py-2 pr-9 text-xs font-semibold text-slate-700 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 shadow-xs cursor-pointer"
            >
              <option value="Active Loan/Advance">Active Loan/Advance</option>
              <option value="Closed Loan/Advance">Closed Loan/Advance</option>
              <option value="All">All</option>
            </select>
            <ChevronDown className="w-3.5 h-3.5 text-slate-500 absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none" />
          </div>

          {/* Search Box */}
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
            <input
              type="text"
              placeholder="Search Employee..."
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setCurrentPage(1);
              }}
              className="bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg pl-9 pr-3 py-1.5 text-xs font-medium text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 w-44 sm:w-56 shadow-xs"
            />
          </div>

          {/* View Logs Button */}
          <button
            type="button"
            onClick={() => router.push("/settlements/loan-arrears-log?module=Loan%20%26%20Advance")}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 rounded-lg text-xs font-semibold transition-colors cursor-pointer shadow-xs"
          >
            <FileText className="w-3.5 h-3.5 text-slate-500" />
            <span>View Logs</span>
          </button>

          {/* Add Loan/Advance Primary Blue Button */}
          <button
            type="button"
            onClick={() => setShowAddModal(true)}
            className="inline-flex items-center gap-1.5 px-4 py-2 bg-[#0070e0] hover:bg-blue-700 text-white rounded-lg text-xs font-bold transition-colors cursor-pointer shadow-xs"
          >
            <Plus className="w-4 h-4 stroke-[3]" />
            <span>Add Loan/Advance</span>
          </button>
        </div>
      </div>

      {/* 2. Main Data Table Container */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-xs overflow-hidden">
        {/* Loading Skeleton */}
        {isLoading && (
          <div className="p-6 space-y-4">
            <div className="h-10 bg-slate-100 dark:bg-slate-800 rounded-lg animate-pulse" />
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
                Failed to Load Loan Data
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                An error occurred while communicating with the server. Please retry.
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

        {/* Empty State */}
        {!isLoading && !isError && loanItems.length === 0 && (
          <div className="p-16 text-center flex flex-col items-center justify-center space-y-3">
            <div className="w-16 h-16 bg-[#eaf4fd] dark:bg-slate-800 rounded-full flex items-center justify-center text-[#0070e0]">
              <Search className="w-8 h-8 stroke-[2.5]" />
            </div>
            <h3 className="text-sm font-bold text-slate-700 dark:text-slate-300">
              No Data Found
            </h3>
            <p className="text-xs text-slate-500 max-w-sm">
              No loan or advance records found matching your active filter.
            </p>
          </div>
        )}

        {/* Petpooja Styled Data Table */}
        {!isLoading && !isError && loanItems.length > 0 && (
          <div className="overflow-x-auto min-h-[320px]">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-[#eaf4fd] dark:bg-slate-800/90 text-slate-900 dark:text-slate-100 font-bold border-b border-slate-200 dark:border-slate-700">
                  <th
                    onClick={() => toggleSort("employee_code")}
                    className="py-3.5 px-4 cursor-pointer hover:bg-blue-100/50 dark:hover:bg-slate-700/50 select-none whitespace-nowrap"
                  >
                    <div className="flex items-center gap-1.5">
                      <span>Employee ID</span>
                      <ArrowUpDown className="w-3.5 h-3.5 text-slate-400" />
                    </div>
                  </th>
                  <th
                    onClick={() => toggleSort("employee_name")}
                    className="py-3.5 px-4 cursor-pointer hover:bg-blue-100/50 dark:hover:bg-slate-700/50 select-none whitespace-nowrap"
                  >
                    <div className="flex items-center gap-1.5">
                      <span>Employee Name</span>
                      <ArrowUpDown className="w-3.5 h-3.5 text-slate-400" />
                    </div>
                  </th>
                  <th className="py-3.5 px-4 whitespace-nowrap">
                    <div className="flex items-center gap-1.5">
                      <span>Loan Count</span>
                      <Info className="w-3.5 h-3.5 text-slate-400" />
                    </div>
                  </th>
                  <th
                    onClick={() => toggleSort("principal_amount")}
                    className="py-3.5 px-4 text-right cursor-pointer hover:bg-blue-100/50 dark:hover:bg-slate-700/50 select-none whitespace-nowrap"
                  >
                    Total Amount
                  </th>
                  <th
                    onClick={() => toggleSort("total_debit")}
                    className="py-3.5 px-4 text-right cursor-pointer hover:bg-blue-100/50 dark:hover:bg-slate-700/50 select-none whitespace-nowrap"
                  >
                    Total Debit
                  </th>
                  <th
                    onClick={() => toggleSort("outstanding_amount")}
                    className="py-3.5 px-4 text-right cursor-pointer hover:bg-blue-100/50 dark:hover:bg-slate-700/50 select-none whitespace-nowrap"
                  >
                    Outstanding Amount
                  </th>
                  <th className="py-3.5 px-4 text-center whitespace-nowrap">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {loanItems.map((item) => (
                  <tr
                    key={item.id}
                    className="hover:bg-slate-50/80 dark:hover:bg-slate-800/40 transition-colors"
                  >
                    {/* Employee ID */}
                    <td className="py-3.5 px-4 font-semibold text-slate-800 dark:text-slate-200 whitespace-nowrap">
                      {item.employee_code || item.employee_id}
                    </td>

                    {/* Employee Name */}
                    <td className="py-3.5 px-4 font-semibold text-slate-900 dark:text-slate-100 whitespace-nowrap">
                      {item.employee_name || `Employee #${item.employee_id}`}
                    </td>

                    {/* Loan Count */}
                    <td className="py-3.5 px-4 text-slate-700 dark:text-slate-300 font-medium whitespace-nowrap">
                      1
                    </td>

                    {/* Total Amount */}
                    <td className="py-3.5 px-4 text-right font-medium text-slate-800 dark:text-slate-200 whitespace-nowrap">
                      {Number(item.principal_amount).toLocaleString("en-IN", {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2,
                      })}
                    </td>

                    {/* Total Debit */}
                    <td className="py-3.5 px-4 text-right font-medium text-slate-800 dark:text-slate-200 whitespace-nowrap">
                      {Number(item.total_debit).toLocaleString("en-IN", {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2,
                      })}
                    </td>

                    {/* Outstanding Amount */}
                    <td className="py-3.5 px-4 text-right font-semibold text-slate-900 dark:text-slate-100 whitespace-nowrap">
                      {Number(item.outstanding_amount).toLocaleString("en-IN", {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2,
                      })}
                    </td>

                    {/* Action Dropdown Menu */}
                    <td className="py-3.5 px-4 text-center whitespace-nowrap relative">
                      <button
                        type="button"
                        onClick={() =>
                          setActionMenuOpenId(actionMenuOpenId === item.id ? null : item.id)
                        }
                        className="p-1.5 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-300 transition-colors cursor-pointer"
                      >
                        <MoreVertical className="w-4 h-4" />
                      </button>

                      {/* Dropdown Menu Popup matching Petpooja */}
                      {actionMenuOpenId === item.id && (
                        <>
                          <div
                            className="fixed inset-0 z-10"
                            onClick={() => setActionMenuOpenId(null)}
                          />
                          <div className="absolute right-4 top-11 z-20 w-44 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl shadow-lg py-1.5 text-left animate-in fade-in-50 zoom-in-95">
                            {/* 1. Debit Amount Action */}
                            <button
                              type="button"
                              onClick={() => {
                                setSelectedLoan(item);
                                setDebitSelectLoanId(String(item.id));
                                setDebitComment("");
                                setDebitAmount("");
                                setDebitDate(new Date().toISOString().split("T")[0]);
                                setShowDebitModal(true);
                                setActionMenuOpenId(null);
                              }}
                              className="w-full px-3.5 py-2 text-xs font-medium text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-700/70 flex items-center gap-2 cursor-pointer"
                            >
                              <Edit2 className="w-3.5 h-3.5 text-slate-500" />
                              <span>Debit Amount</span>
                            </button>

                            {/* 2. Transaction Logs Action */}
                            <button
                              type="button"
                              onClick={() => {
                                setSelectedLoan(item);
                                setShowItemLogsModal(true);
                                setActionMenuOpenId(null);
                              }}
                              className="w-full px-3.5 py-2 text-xs font-medium text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-700/70 flex items-center gap-2 cursor-pointer"
                            >
                              <FileText className="w-3.5 h-3.5 text-slate-500" />
                              <span>Transaction Logs</span>
                            </button>

                            {/* 3. Edit Installment Action */}
                            <button
                              type="button"
                              onClick={() => {
                                setSelectedLoan(item);
                                setEditSelectLoanId(String(item.id));
                                setEditNewInstallment("");
                                setEditNewInstallmentTouched(false);
                                setShowEditModal(true);
                                setActionMenuOpenId(null);
                              }}
                              className="w-full px-3.5 py-2 text-xs font-medium text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-700/70 flex items-center gap-2 cursor-pointer"
                            >
                              <Edit2 className="w-3.5 h-3.5 text-slate-500" />
                              <span>Edit Installment</span>
                            </button>
                          </div>
                        </>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Petpooja Styled Footer Pagination Bar */}
        {!isLoading && !isError && loanItems.length > 0 && (
          <div className="px-4 py-3 border-t border-slate-200 dark:border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs">
            <div className="text-slate-600 dark:text-slate-400 font-medium">
              Showing {(currentPage - 1) * pageSize + 1} to{" "}
              {Math.min(currentPage * pageSize, totalRecords)} of {totalRecords} Results
            </div>

            <div className="flex items-center gap-3">
              {/* Page size dropdown matching Petpooja */}
              <div className="relative">
                <select
                  aria-label="Rows per page"
                  value={pageSize}
                  onChange={(e) => {
                    setPageSize(Number(e.target.value));
                    setCurrentPage(1);
                  }}
                  className="appearance-none bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg pl-3 pr-8 py-1.5 text-xs font-semibold text-slate-700 dark:text-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer shadow-xs"
                >
                  <option value={10}>10 / Page</option>
                  <option value={25}>25 / Page</option>
                  <option value={50}>50 / Page</option>
                </select>
                <ChevronDown className="w-3.5 h-3.5 text-slate-500 absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
              </div>

              {/* Pagination buttons */}
              <div className="flex items-center gap-1">
                <button
                  type="button"
                  disabled={currentPage === 1}
                  onClick={() => setCurrentPage((prev) => Math.max(prev - 1, 1))}
                  className="px-3 py-1.5 border border-slate-300 dark:border-slate-700 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800 font-medium disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer transition-colors text-slate-700 dark:text-slate-300"
                >
                  Previous
                </button>

                <button
                  type="button"
                  className="px-3 py-1.5 bg-[#0070e0] text-white font-bold rounded-lg cursor-default shadow-xs"
                >
                  {currentPage}
                </button>

                <button
                  type="button"
                  disabled={currentPage >= totalPages}
                  onClick={() => setCurrentPage((prev) => Math.min(prev + 1, totalPages))}
                  className="px-3 py-1.5 border border-slate-300 dark:border-slate-700 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800 font-medium disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer transition-colors text-slate-700 dark:text-slate-300"
                >
                  Next
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* 3. Add Loan/Advance Modal / Drawer */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 overflow-hidden bg-slate-900/50 backdrop-blur-xs flex justify-end">
          <div className="w-full max-w-lg bg-white dark:bg-slate-900 shadow-2xl h-full flex flex-col justify-between overflow-hidden animate-in slide-in-from-right duration-200">
            {/* Header: Petpooja Soft Blue */}
            <div className="px-6 py-4 bg-[#eaf4fd] dark:bg-slate-800 flex items-center justify-between border-b border-slate-200 dark:border-slate-700">
              <h2 className="text-base font-bold text-slate-900 dark:text-slate-100">
                Add Loan/Advance
              </h2>
              <button
                type="button"
                onClick={() => setShowAddModal(false)}
                className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Scrollable Form Body */}
            <form id="add-loan-form" onSubmit={handleAddSubmit} className="p-6 space-y-4 text-xs overflow-y-auto flex-1">
              {/* Employee Selection */}
              <div>
                <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Employee <span className="text-red-500">*</span>
                </label>
                <select
                  required
                  value={formData.employee_id}
                  onChange={(e) =>
                    setFormData({ ...formData, employee_id: e.target.value })
                  }
                  className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-2 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-blue-500 focus:outline-none cursor-pointer font-medium"
                >
                  <option value="">Select Employee...</option>
                  {activeEmployees.map((emp) => (
                    <option key={emp.employee_id} value={emp.employee_id}>
                      {emp.employee_code} - {emp.employee_name} ({emp.department_name || "General"})
                    </option>
                  ))}
                </select>

                {selectedEmpObj && (
                  <div className="mt-1.5 p-2 bg-slate-50 dark:bg-slate-800/80 rounded border border-slate-200 dark:border-slate-700 text-[11px] text-slate-600 dark:text-slate-300 flex justify-between">
                    <span>Code: <strong>{selectedEmpObj.employee_code}</strong></span>
                    <span>Dept: <strong>{selectedEmpObj.department_name || "General"}</strong></span>
                  </div>
                )}
              </div>

              {/* Loan Name */}
              <div>
                <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Loan/Advance Name <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Festival Advance, Personal Loan"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-2 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-blue-500 focus:outline-none"
                />
              </div>

              {/* Type Selection */}
              <div>
                <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-2">
                  Type <span className="text-red-500">*</span>
                </label>
                <div className="flex items-center gap-6">
                  <label className="flex items-center gap-2 cursor-pointer font-medium">
                    <input
                      type="radio"
                      name="type"
                      value="loan"
                      checked={formData.type === "loan"}
                      onChange={() => setFormData({ ...formData, type: "loan" })}
                      className="w-4 h-4 text-[#0070e0] focus:ring-blue-500"
                    />
                    <span>Loan</span>
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer font-medium">
                    <input
                      type="radio"
                      name="type"
                      value="advance"
                      checked={formData.type === "advance"}
                      onChange={() => setFormData({ ...formData, type: "advance" })}
                      className="w-4 h-4 text-[#0070e0] focus:ring-blue-500"
                    />
                    <span>Salary Advance</span>
                  </label>
                </div>
              </div>

              {/* Principal Amount */}
              <div>
                <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Principal Amount (₹) <span className="text-red-500">*</span>
                </label>
                <input
                  type="number"
                  required
                  min="1"
                  placeholder="e.g. 10000"
                  value={formData.principal_amount}
                  onChange={(e) =>
                    setFormData({ ...formData, principal_amount: e.target.value })
                  }
                  className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-2 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-blue-500 focus:outline-none"
                />
              </div>

              {/* Monthly Installment */}
              <div>
                <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Monthly Installment (₹) <span className="text-red-500">*</span>
                </label>
                <input
                  type="number"
                  required
                  min="1"
                  placeholder="e.g. 1000"
                  value={formData.monthly_installment}
                  onChange={(e) =>
                    setFormData({ ...formData, monthly_installment: e.target.value })
                  }
                  className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-2 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-blue-500 focus:outline-none"
                />
                <p className="text-[11px] text-slate-400 mt-1 italic">
                  This monthly amount will be recovered during monthly payroll processing.
                </p>
              </div>

              {/* Disbursal Date */}
              <div>
                <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Disbursal Date <span className="text-red-500">*</span>
                </label>
                <input
                  type="date"
                  required
                  value={formData.transaction_date}
                  onChange={(e) =>
                    setFormData({ ...formData, transaction_date: e.target.value })
                  }
                  className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-2 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-blue-500 focus:outline-none"
                />
              </div>

              {/* Remarks */}
              <div>
                <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Notes / Remarks
                </label>
                <textarea
                  rows={2}
                  placeholder="Optional notes..."
                  value={formData.comment}
                  onChange={(e) => setFormData({ ...formData, comment: e.target.value })}
                  className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-2 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-blue-500 focus:outline-none"
                />
              </div>
            </form>

            {/* Footer Actions */}
            <div className="px-6 py-4 bg-[#eaf4fd] dark:bg-slate-800 flex items-center justify-end gap-3 border-t border-slate-200 dark:border-slate-700">
              <button
                type="button"
                onClick={() => setShowAddModal(false)}
                className="px-4 py-2 border border-slate-300 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 rounded-lg font-semibold text-xs transition-colors cursor-pointer"
              >
                Cancel
              </button>

              <button
                type="submit"
                form="add-loan-form"
                disabled={createMutation.isPending}
                className="inline-flex items-center gap-2 px-5 py-2 bg-[#0070e0] hover:bg-blue-700 text-white rounded-lg font-bold text-xs transition-colors cursor-pointer disabled:opacity-50"
              >
                {createMutation.isPending && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                <span>Save Loan Record</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 4. PHASE 1 & 5 — Debit Amount Right-Side Drawer (Accessibility & UX Polished) */}
      {showDebitModal && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="debit-drawer-title"
          className="fixed inset-0 z-50 overflow-hidden bg-slate-900/40 backdrop-blur-xs flex justify-end animate-in fade-in duration-200"
        >
          {/* Backdrop Click Listener */}
          <div
            className="absolute inset-0 cursor-pointer"
            aria-hidden="true"
            onClick={() => {
              setShowDebitModal(false);
              setSelectedLoan(null);
            }}
          />

          {/* Drawer Container Panel */}
          <div className="relative w-full max-w-md sm:max-w-lg bg-white dark:bg-slate-900 shadow-2xl h-full flex flex-col justify-between overflow-hidden z-10 animate-in slide-in-from-right duration-200">
            {/* Header: Petpooja Soft Blue */}
            <div className="px-6 py-4 bg-[#eaf4fd] dark:bg-slate-800 flex items-center justify-between border-b border-slate-200 dark:border-slate-700">
              <div>
                <h2 id="debit-drawer-title" className="text-base font-bold text-slate-900 dark:text-slate-100">
                  Add Debit
                </h2>
                {selectedLoan?.employee_name && (
                  <p className="text-xs text-slate-600 dark:text-slate-400 mt-0.5 font-medium">
                    {selectedLoan.employee_name}
                  </p>
                )}
              </div>
              <button
                type="button"
                aria-label="Close drawer"
                onClick={() => {
                  setShowDebitModal(false);
                  setSelectedLoan(null);
                }}
                className="text-slate-500 hover:text-slate-700 dark:hover:text-slate-200 cursor-pointer p-1 rounded-lg transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Scrollable Form Body */}
            <form
              id="debit-drawer-form"
              onSubmit={(e) => {
                e.preventDefault();
                if (!isDebitFormValid || submitDebitMutation.isPending) return;

                const targetLoanId = Number(debitSelectLoanId);
                const amt = Number(debitAmount);

                submitDebitMutation.mutate(
                  {
                    loan_id: targetLoanId,
                    transaction_type: "DEBIT",
                    amount: amt,
                    comment: debitComment,
                    transaction_date: debitDate,
                  },
                  {
                    onSuccess: () => {
                      toast.success(`Debit added successfully for ${selectedLoan?.employee_name || "Employee"}`);
                      setShowDebitModal(false);
                      setSelectedLoan(null);
                      setDebitComment("");
                      setDebitAmount("");
                      setDebitSelectLoanId("");
                      setDebitCommentTouched(false);
                      setDebitAmountTouched(false);
                      refetch();
                    },
                    onError: (err: unknown) => {
                      toast.error(getErrorMessage(err, "Failed to submit debit transaction"));
                    },
                  }
                );
              }}
              className="p-6 space-y-5 text-xs overflow-y-auto flex-1 font-sans"
            >
              {/* Select Loan/Advance */}
              <div>
                <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                  Select Loan/Advance <span className="text-red-500 font-bold">*</span>
                </label>
                <div className="relative">
                  <select
                    ref={firstSelectRef}
                    required
                    aria-required="true"
                    aria-label="Select Loan or Advance"
                    value={debitSelectLoanId}
                    onChange={(e) => setDebitSelectLoanId(e.target.value)}
                    className={`w-full appearance-none bg-white dark:bg-slate-800 border ${
                      isLoanClosed
                        ? "border-red-500 focus:ring-red-500"
                        : "border-slate-300 dark:border-slate-700 focus:ring-blue-500"
                    } hover:border-slate-400 rounded-lg px-3.5 py-2.5 pr-9 text-xs font-normal text-slate-800 dark:text-slate-200 focus:ring-2 focus:outline-none cursor-pointer`}
                  >
                    <option value="">Select a loan/advance</option>
                    {isActiveLoansLoading ? (
                      <option value="" disabled>Loading active loans...</option>
                    ) : (
                      availableLoansList.map((ln) => (
                        <option key={ln.id} value={ln.id}>
                          {ln.name} (Outstanding: {formatCurrency(Number(ln.outstanding_amount))}, Installment: {formatCurrency(Number(ln.monthly_installment))})
                        </option>
                      ))
                    )}
                  </select>
                  <ChevronDown className="w-4 h-4 text-slate-400 absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none" />
                </div>
                {isLoanClosed && (
                  <p className="text-[11px] font-semibold text-red-500 mt-1 flex items-center gap-1">
                    <AlertCircle className="w-3.5 h-3.5" />
                    <span>Cannot debit a closed loan. Please select an active loan.</span>
                  </p>
                )}
              </div>

              {/* Comment */}
              <div>
                <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                  Comment <span className="text-red-500 font-bold">*</span>
                </label>
                <input
                  type="text"
                  required
                  placeholder="Enter Comment"
                  value={debitComment}
                  onBlur={() => setDebitCommentTouched(true)}
                  onChange={(e) => setDebitComment(e.target.value)}
                  className={`w-full bg-white dark:bg-slate-800 border ${
                    debitCommentTouched && !debitComment.trim()
                      ? "border-red-500 focus:ring-red-500"
                      : "border-slate-300 dark:border-slate-700 focus:ring-blue-500"
                  } hover:border-slate-400 rounded-lg px-3.5 py-2.5 text-xs text-slate-900 dark:text-slate-100 placeholder:text-slate-400 focus:ring-2 focus:outline-none`}
                />
                {debitCommentTouched && !debitComment.trim() && (
                  <p className="text-[11px] font-semibold text-red-500 mt-1 flex items-center gap-1">
                    <AlertCircle className="w-3.5 h-3.5" />
                    <span>Comment is required.</span>
                  </p>
                )}
              </div>

              {/* Debit Amount */}
              <div>
                <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                  Debit Amount <span className="text-red-500 font-bold">*</span>
                </label>
                <input
                  type="number"
                  required
                  min="1"
                  placeholder="Enter Amount"
                  value={debitAmount}
                  onBlur={() => setDebitAmountTouched(true)}
                  onChange={(e) => setDebitAmount(e.target.value)}
                  className={`w-full bg-white dark:bg-slate-800 border ${
                    (debitAmountTouched && debitAmountNum <= 0) || isAmountExceeding
                      ? "border-red-500 focus:ring-red-500"
                      : "border-slate-300 dark:border-slate-700 focus:ring-blue-500"
                  } hover:border-slate-400 rounded-lg px-3.5 py-2.5 text-xs text-slate-900 dark:text-slate-100 placeholder:text-slate-400 focus:ring-2 focus:outline-none`}
                />
                {debitAmountTouched && debitAmountNum <= 0 && (
                  <p className="text-[11px] font-semibold text-red-500 mt-1 flex items-center gap-1">
                    <AlertCircle className="w-3.5 h-3.5" />
                    <span>Debit amount must be greater than zero.</span>
                  </p>
                )}
                {isAmountExceeding && (
                  <p className="text-[11px] font-semibold text-red-500 mt-1 flex items-center gap-1">
                    <AlertCircle className="w-3.5 h-3.5" />
                    <span>
                      Debit amount cannot exceed outstanding amount (
                      {formatCurrency(Number(selectedDebitLoanObj?.outstanding_amount || 0))}
                      )
                    </span>
                  </p>
                )}
              </div>

              {/* Transaction Date */}
              <div>
                <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                  Transaction Date <span className="text-red-500 font-bold">*</span>
                </label>
                <div className="relative">
                  <input
                    type="date"
                    required
                    value={debitDate}
                    onChange={(e) => setDebitDate(e.target.value)}
                    className="w-full bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 hover:border-slate-400 rounded-lg px-3.5 py-2.5 text-xs text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-blue-500 focus:outline-none"
                  />
                </div>
              </div>
            </form>

            {/* Footer Actions */}
            <div className="px-6 py-3.5 bg-[#eaf4fd] dark:bg-slate-800 flex items-center justify-end gap-3 border-t border-slate-200 dark:border-slate-700">
              <button
                type="button"
                onClick={() => {
                  setShowDebitModal(false);
                  setSelectedLoan(null);
                }}
                className="px-4 py-2 border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-700 hover:bg-slate-50 dark:hover:bg-slate-600 text-slate-700 dark:text-slate-200 rounded-lg font-semibold text-xs transition-colors cursor-pointer"
              >
                Close
              </button>

              <button
                type="submit"
                form="debit-drawer-form"
                disabled={!isDebitFormValid || submitDebitMutation.isPending}
                className="inline-flex items-center gap-2 px-5 py-2 bg-[#0070e0] hover:bg-blue-700 disabled:bg-[#cbd5e1] dark:disabled:bg-slate-700 disabled:text-slate-400 disabled:cursor-not-allowed text-white font-bold text-xs rounded-lg transition-colors cursor-pointer shadow-xs"
              >
                {submitDebitMutation.isPending && (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                )}
                <span>Save Details</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 5. PHASE 1 — Edit Installment Right-Side Drawer (Matches Reference Screenshot Exactly) */}
      {showEditModal && selectedLoan && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="edit-installment-drawer-title"
          className="fixed inset-0 z-50 overflow-hidden bg-slate-900/40 backdrop-blur-xs flex justify-end animate-in fade-in duration-200"
        >
          {/* Backdrop Click Listener */}
          <div
            className="absolute inset-0 cursor-pointer"
            aria-hidden="true"
            onClick={() => {
              setShowEditModal(false);
              setSelectedLoan(null);
            }}
          />

          {/* Drawer Container Panel */}
          <div className="relative w-full max-w-md bg-white dark:bg-slate-900 shadow-2xl h-full flex flex-col justify-between overflow-hidden z-10 animate-in slide-in-from-right duration-200 font-sans">
            {/* Header: Petpooja Soft Blue */}
            <div className="px-6 py-4 bg-[#eaf4fd] dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 flex items-center justify-between">
              <div>
                <h2 id="edit-installment-drawer-title" className="text-base font-bold text-slate-900 dark:text-slate-100">
                  Edit Installment
                </h2>
                <p className="text-xs text-slate-600 dark:text-slate-400 mt-0.5 font-medium">
                  {selectedLoan.employee_name}
                </p>
              </div>
              <button
                type="button"
                aria-label="Close drawer"
                onClick={() => {
                  setShowEditModal(false);
                  setSelectedLoan(null);
                }}
                className="text-slate-500 hover:text-slate-700 dark:hover:text-slate-200 cursor-pointer p-1 rounded-lg transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Main Drawer Form Body */}
            <form
              id="edit-installment-drawer-form"
              onSubmit={(e) => {
                e.preventDefault();
                handleEditSubmit(e);
              }}
              className="p-6 flex-1 overflow-y-auto space-y-5 text-xs"
            >
              {/* 1. Select Loan * */}
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="block font-semibold text-slate-700 dark:text-slate-300">
                    Select Loan <span className="text-red-500 font-bold">*</span>
                  </label>
                  {isActiveLoansLoading && (
                    <span className="flex items-center gap-1 text-[11px] text-blue-600 font-medium">
                      <Loader2 className="w-3 h-3 animate-spin" /> Loading loans...
                    </span>
                  )}
                </div>
                <div className="relative">
                  <select
                    ref={editSelectRef}
                    required
                    disabled={isActiveLoansLoading}
                    value={editSelectLoanId}
                    onChange={(e) => setEditSelectLoanId(e.target.value)}
                    className="w-full appearance-none bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 hover:border-slate-400 rounded-lg px-3.5 py-2.5 pr-9 text-xs text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-blue-500 focus:outline-none cursor-pointer disabled:opacity-60"
                  >
                    <option value="">
                      {availableLoansList.filter((ln) => ln.status === "active").length === 0
                        ? "No active loans found"
                        : "Select an active loan"}
                    </option>
                    {availableLoansList
                      .filter((ln) => ln.status === "active")
                      .map((ln) => (
                        <option key={ln.id} value={ln.id.toString()}>
                          {ln.name}
                        </option>
                      ))}
                  </select>
                  <ChevronDown className="w-4 h-4 text-slate-400 absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none" />
                </div>
                {isEditLoansError && (
                  <div className="mt-1.5 flex items-center justify-between text-[11px] text-red-500">
                    <span className="flex items-center gap-1 font-medium">
                      <AlertCircle className="w-3.5 h-3.5" /> Failed to load active loans
                    </span>
                    <button
                      type="button"
                      onClick={() => refetchEditLoans()}
                      className="text-blue-600 font-semibold hover:underline cursor-pointer"
                    >
                      Retry
                    </button>
                  </div>
                )}
              </div>

              {/* 2. Outstanding Amount (Read-only) */}
              <div>
                <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                  Outstanding Amount
                </label>
                <input
                  type="text"
                  readOnly
                  disabled
                  value={
                    selectedEditLoanObj
                      ? formatCurrency(Number(selectedEditLoanObj.outstanding_amount))
                      : "₹ 0.00"
                  }
                  className="w-full bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 rounded-lg px-3.5 py-2.5 text-xs text-slate-600 dark:text-slate-400 font-medium cursor-not-allowed"
                />
              </div>

              {/* 3. Current Installment (Read-only) */}
              <div>
                <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                  Current Installment
                </label>
                <input
                  type="text"
                  readOnly
                  disabled
                  value={
                    selectedEditLoanObj
                      ? formatCurrency(Number(selectedEditLoanObj.monthly_installment))
                      : "₹ 0.00"
                  }
                  className="w-full bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 rounded-lg px-3.5 py-2.5 text-xs text-slate-600 dark:text-slate-400 font-medium cursor-not-allowed"
                />
              </div>

              {/* 4. New Installment * */}
              <div>
                <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                  New Installment <span className="text-red-500 font-bold">*</span>
                </label>
                <input
                  type="number"
                  required
                  min="1"
                  disabled={isEditLoanClosed || isEditLoanCompleted || updateInstallmentMutation.isPending}
                  placeholder="Enter new installment amount"
                  value={editNewInstallment}
                  onBlur={() => setEditNewInstallmentTouched(true)}
                  onChange={(e) => setEditNewInstallment(e.target.value)}
                  className={`w-full bg-white dark:bg-slate-800 border ${
                    (editNewInstallmentTouched && editNewInstallmentNum <= 0) || isEditExceedingOutstanding
                      ? "border-red-500 focus:ring-red-500"
                      : "border-slate-300 dark:border-slate-700 focus:ring-blue-500"
                  } hover:border-slate-400 rounded-lg px-3.5 py-2.5 text-xs text-slate-900 dark:text-slate-100 placeholder:text-slate-400 focus:ring-2 focus:outline-none disabled:opacity-60 disabled:cursor-not-allowed`}
                />
                {isEditLoanClosed && (
                  <p className="text-[11px] font-semibold text-amber-600 dark:text-amber-400 mt-1.5 flex items-center gap-1">
                    <AlertCircle className="w-3.5 h-3.5" />
                    <span>Cannot edit a closed or cancelled loan.</span>
                  </p>
                )}
                {isEditLoanCompleted && !isEditLoanClosed && (
                  <p className="text-[11px] font-semibold text-amber-600 dark:text-amber-400 mt-1.5 flex items-center gap-1">
                    <AlertCircle className="w-3.5 h-3.5" />
                    <span>Loan already completed</span>
                  </p>
                )}
                {isEditExceedingOutstanding && (
                  <p className="text-[11px] font-semibold text-red-500 mt-1 flex items-center gap-1">
                    <AlertCircle className="w-3.5 h-3.5" />
                    <span>
                      New installment cannot exceed outstanding amount ({formatCurrency(editOutstandingAmount)}).
                    </span>
                  </p>
                )}
                {editNewInstallmentTouched && editNewInstallmentNum <= 0 && !isEditExceedingOutstanding && (
                  <p className="text-[11px] font-semibold text-red-500 mt-1 flex items-center gap-1">
                    <AlertCircle className="w-3.5 h-3.5" />
                    <span>New installment amount must be greater than zero.</span>
                  </p>
                )}
              </div>
            </form>

            {/* Footer Actions */}
            <div className="px-6 py-3.5 bg-[#eaf4fd] dark:bg-slate-800 flex items-center justify-end gap-3 border-t border-slate-200 dark:border-slate-700">
              <button
                type="button"
                onClick={() => {
                  setShowEditModal(false);
                  setSelectedLoan(null);
                }}
                className="px-4 py-2 border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-700 hover:bg-slate-50 dark:hover:bg-slate-600 text-slate-700 dark:text-slate-200 rounded-lg font-semibold text-xs transition-colors cursor-pointer"
              >
                Close
              </button>

              <button
                type="submit"
                form="edit-installment-drawer-form"
                disabled={!isEditInstallmentValid || updateInstallmentMutation.isPending}
                className="inline-flex items-center gap-2 px-5 py-2 bg-[#0070e0] hover:bg-blue-700 disabled:bg-[#cbd5e1] dark:disabled:bg-slate-700 disabled:text-slate-400 disabled:cursor-not-allowed text-white font-bold text-xs rounded-lg transition-colors cursor-pointer shadow-xs"
              >
                {updateInstallmentMutation.isPending && (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                )}
                <span>Save</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 6. PHASE 1 — Transaction Logs Right-Side Drawer (Matches Screenshot Exactly) */}
      {showItemLogsModal && selectedLoan && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="logs-drawer-title"
          className="fixed inset-0 z-50 overflow-hidden bg-slate-900/40 backdrop-blur-xs flex justify-end animate-in fade-in duration-200"
        >
          {/* Backdrop Click Listener */}
          <div
            className="absolute inset-0 cursor-pointer"
            aria-hidden="true"
            onClick={() => {
              setShowItemLogsModal(false);
              setSelectedLoan(null);
            }}
          />

          {/* Drawer Container Panel */}
          <div className="relative w-full max-w-lg sm:max-w-xl bg-white dark:bg-slate-900 shadow-2xl h-full flex flex-col justify-between overflow-hidden z-10 animate-in slide-in-from-right duration-200 font-sans">
            {/* Header: Petpooja Soft Blue */}
            <div className="px-6 py-4 bg-[#eaf4fd] dark:bg-slate-800 flex items-center justify-between border-b border-slate-200 dark:border-slate-700">
              <div>
                <h2 id="logs-drawer-title" className="text-base font-bold text-slate-900 dark:text-slate-100">
                  Transaction Logs
                </h2>
                {selectedLoan?.employee_name && (
                  <p className="text-xs text-slate-600 dark:text-slate-400 mt-0.5 font-medium">
                    {selectedLoan.employee_name}
                  </p>
                )}
              </div>
              <button
                type="button"
                aria-label="Close drawer"
                onClick={() => {
                  setShowItemLogsModal(false);
                  setSelectedLoan(null);
                }}
                className="text-slate-500 hover:text-slate-700 dark:hover:text-slate-200 cursor-pointer p-1 rounded-lg transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Main Drawer Content */}
            <div className="p-6 flex-1 overflow-y-auto flex flex-col space-y-5 text-xs">
              {/* Top Filter */}
              <div>
                <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                  Loan/Advance
                </label>
                <div className="relative max-w-xs">
                  <select
                    ref={txFilterSelectRef}
                    value={txLogFilter}
                    onChange={(e) => {
                      setTxLogFilter(e.target.value);
                      setTxLogPage(1);
                    }}
                    className="w-full appearance-none bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 hover:border-slate-400 rounded-lg px-3.5 py-2 pr-9 text-xs font-normal text-slate-800 dark:text-slate-200 focus:ring-2 focus:ring-blue-500 focus:outline-none cursor-pointer"
                  >
                    <option value="All">All</option>
                    {txFilterLoansList.map((ln) => (
                      <option key={ln.id} value={ln.id.toString()}>
                        {ln.name}
                      </option>
                    ))}
                  </select>
                  <ChevronDown className="w-4 h-4 text-slate-400 absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none" />
                </div>
              </div>

              {/* State Renderers */}
              {isTxLogsLoading ? (
                <div className="space-y-2 py-4">
                  {[...Array(4)].map((_, i) => (
                    <div key={i} className="h-10 bg-slate-100 dark:bg-slate-800 rounded animate-pulse" />
                  ))}
                </div>
              ) : isTxLogsError ? (
                <div className="py-12 text-center space-y-3">
                  <AlertCircle className="w-8 h-8 text-red-500 mx-auto" />
                  <p className="font-semibold text-slate-700 dark:text-slate-300">Failed to load transaction logs from server</p>
                  <button
                    type="button"
                    onClick={() => refetchTxLogs()}
                    className="px-3 py-1.5 bg-[#0070e0] text-white font-semibold rounded-lg shadow-xs hover:bg-blue-700 cursor-pointer"
                  >
                    Retry
                  </button>
                </div>
              ) : (txLogsData?.items || itemDetailsData?.transactions || []).length === 0 ? (
                <div className="py-16 text-center text-slate-400">
                  <FileText className="w-10 h-10 mx-auto text-slate-300 mb-2" />
                  <p className="font-semibold text-slate-600 dark:text-slate-400">No Transactions Found</p>
                </div>
              ) : (
                <div className="border border-slate-200 dark:border-slate-800 rounded-lg overflow-hidden flex-1">
                  <table className="w-full border-collapse text-left text-xs">
                    <thead>
                      <tr className="bg-[#eaf4fd] dark:bg-slate-800/80 font-bold text-slate-800 dark:text-slate-200 border-b border-slate-200 dark:border-slate-700">
                        <th className="p-3">Transaction Date</th>
                        <th className="p-3">Loan/Advance</th>
                        <th className="p-3 text-right">Amount</th>
                        <th className="p-3">Comment</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 dark:divide-slate-800 bg-white dark:bg-slate-900">
                      {(txLogsData?.items || itemDetailsData?.transactions || []).map((tx) => {
                        const isDebitType =
                          tx.transaction_type?.toLowerCase() === "debit" ||
                          tx.transaction_type?.toLowerCase() === "dr";
                        return (
                          <tr key={tx.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/40">
                            <td className="p-3 font-medium whitespace-nowrap text-slate-700 dark:text-slate-300">
                              {tx.transaction_date}
                            </td>
                            <td className="p-3 text-slate-700 dark:text-slate-300">
                              {selectedLoan.name}
                            </td>
                            <td className="p-3 text-right whitespace-nowrap">
                              <span
                                className={
                                  isDebitType
                                    ? "text-red-500 font-bold"
                                    : "text-emerald-600 font-bold"
                                }
                              >
                                {formatCurrency(Number(tx.amount))} {isDebitType ? "Dr" : "Cr"}
                              </span>
                            </td>
                            <td className="p-3 text-slate-500">
                              {tx.remarks || "--"}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {/* Summary Section Banner (Sticky panel) */}
            <div className="shrink-0 px-6 py-3 bg-[#e2e8f0]/80 dark:bg-slate-800/80 border-t border-b border-slate-200 dark:border-slate-700 flex items-center justify-between text-xs font-semibold text-slate-800 dark:text-slate-200">
              <div>
                Total Amount: <span className="font-bold">{formatCurrency(Number(txLogsData?.total_amount ?? selectedLoan.principal_amount))}</span>
              </div>
              <div>
                Outstanding Amount: <span className="font-bold">{formatCurrency(Number(txLogsData?.outstanding_amount ?? selectedLoan.outstanding_amount))}</span>
              </div>
            </div>

            {/* Footer Actions & Pagination (Sticky panel) */}
            <div className="shrink-0 px-6 py-3 bg-[#eaf4fd] dark:bg-slate-800 border-t border-slate-200 dark:border-slate-700 flex items-center justify-between text-xs text-slate-700 dark:text-slate-300">
              <span className="font-semibold">
                Total Records: {txLogsData?.pagination.total_records ?? (itemDetailsData?.transactions || []).length}
              </span>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  aria-label="Previous page"
                  disabled={isTxLogsLoading || txLogPage <= 1}
                  onClick={() => setTxLogPage((p) => Math.max(1, p - 1))}
                  className="w-7 h-7 bg-[#59a5e8] hover:bg-[#389be8] disabled:opacity-50 text-white rounded flex items-center justify-center font-bold transition-colors cursor-pointer"
                >
                  &lt;
                </button>
                <span className="font-medium text-slate-800 dark:text-slate-200">
                  Page {txLogPage} of {txLogsData?.pagination.total_pages || 1}
                </span>
                <button
                  type="button"
                  aria-label="Next page"
                  disabled={isTxLogsLoading || txLogPage >= (txLogsData?.pagination.total_pages || 1)}
                  onClick={() => setTxLogPage((p) => p + 1)}
                  className="w-7 h-7 bg-[#59a5e8] hover:bg-[#389be8] disabled:opacity-50 text-white rounded flex items-center justify-center font-bold transition-colors cursor-pointer"
                >
                  &gt;
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 7. Org-wide View Logs Modal */}
      {showLogsModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xl w-full max-w-3xl overflow-hidden flex flex-col max-h-[85vh]">
            <div className="flex items-center justify-between px-6 py-4 bg-[#eaf4fd] dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700">
              <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">
                Loan & Advance Activity Logs
              </h3>
              <button
                type="button"
                onClick={() => setShowLogsModal(false)}
                className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 overflow-y-auto space-y-3 flex-1 text-xs">
              {isLogsLoading ? (
                <div className="space-y-2 py-4">
                  {[...Array(4)].map((_, i) => (
                    <div key={i} className="h-10 bg-slate-100 dark:bg-slate-800 rounded animate-pulse" />
                  ))}
                </div>
              ) : (logsResponse?.items || []).length === 0 ? (
                <p className="text-center py-8 text-slate-400 font-medium">
                  No activity or ledger transactions recorded yet.
                </p>
              ) : (
                <div className="border border-slate-200 dark:border-slate-800 rounded-lg overflow-hidden">
                  <table className="w-full border-collapse text-left text-xs">
                    <thead>
                      <tr className="bg-slate-100 dark:bg-slate-800 font-semibold">
                        <th className="p-2.5">Date</th>
                        <th className="p-2.5">Type</th>
                        <th className="p-2.5 text-right">Amount</th>
                        <th className="p-2.5">Source</th>
                        <th className="p-2.5">Remarks</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
                      {(logsResponse?.items || []).map((log) => (
                        <tr key={log.id}>
                          <td className="p-2.5 font-medium whitespace-nowrap">{log.transaction_date}</td>
                          <td className="p-2.5 uppercase font-bold text-slate-700 dark:text-slate-300">
                            {log.transaction_type}
                          </td>
                          <td className="p-2.5 text-right font-bold text-slate-900 dark:text-slate-100">
                            {formatCurrency(Number(log.amount))}
                          </td>
                          <td className="p-2.5 text-slate-500 uppercase">{log.source}</td>
                          <td className="p-2.5 text-slate-600 dark:text-slate-400">
                            {log.remarks || "-"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            <div className="px-6 py-3 border-t border-slate-200 dark:border-slate-800 flex justify-end">
              <button
                type="button"
                onClick={() => setShowLogsModal(false)}
                className="px-4 py-2 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 text-slate-700 dark:text-slate-300 font-semibold text-xs rounded-lg transition-colors cursor-pointer"
              >
                Close Logs
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 8. Close Confirmation Modal */}
      {confirmCloseId && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xl w-full max-w-sm p-6 text-center space-y-4">
            <div className="w-12 h-12 bg-amber-50 dark:bg-amber-950/40 rounded-full flex items-center justify-center text-amber-600 mx-auto">
              <Lock className="w-6 h-6" />
            </div>
            <div>
              <h3 className="font-bold text-slate-900 dark:text-slate-100 text-sm">
                Confirm Close Loan
              </h3>
              <p className="text-xs text-slate-500 mt-1">
                Are you sure you want to mark this loan as closed?
              </p>
            </div>
            <div className="flex justify-center gap-2">
              <button
                type="button"
                onClick={() => setConfirmCloseId(null)}
                className="px-4 py-2 border border-slate-300 dark:border-slate-700 hover:bg-slate-100 text-slate-700 dark:text-slate-300 rounded-lg font-semibold text-xs cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={closeMutation.isPending}
                onClick={() => handleCloseLoan(confirmCloseId)}
                className="inline-flex items-center gap-1.5 px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white rounded-lg font-bold text-xs cursor-pointer disabled:opacity-50"
              >
                {closeMutation.isPending && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                <span>Confirm Close</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 9. Delete Confirmation Modal */}
      {confirmDeleteId && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xl w-full max-w-sm p-6 text-center space-y-4">
            <div className="w-12 h-12 bg-red-50 dark:bg-red-950/40 rounded-full flex items-center justify-center text-red-600 mx-auto">
              <Trash2 className="w-6 h-6" />
            </div>
            <div>
              <h3 className="font-bold text-slate-900 dark:text-slate-100 text-sm">
                Confirm Delete Record
              </h3>
              <p className="text-xs text-slate-500 mt-1">
                This action will remove the loan record permanently. Proceed?
              </p>
            </div>
            <div className="flex justify-center gap-2">
              <button
                type="button"
                onClick={() => setConfirmDeleteId(null)}
                className="px-4 py-2 border border-slate-300 dark:border-slate-700 hover:bg-slate-100 text-slate-700 dark:text-slate-300 rounded-lg font-semibold text-xs cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={deleteMutation.isPending}
                onClick={() => handleDeleteLoan(confirmDeleteId)}
                className="inline-flex items-center gap-1.5 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg font-bold text-xs cursor-pointer disabled:opacity-50"
              >
                {deleteMutation.isPending && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                <span>Delete Record</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
