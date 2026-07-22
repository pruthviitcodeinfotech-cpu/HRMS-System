"use client";

import React, { useState, useMemo } from "react";
import {
  Search,
  ChevronDown,
  FileText,
  Plus,
  Eye,
  Edit2,
  Trash2,
  Lock,
  ChevronLeft,
  ChevronRight,
  X,
  AlertCircle,
  RefreshCw,
  Loader2,
} from "lucide-react";
import { toast } from "sonner";
import { useEmployees } from "@/features/employees/hooks";
import {
  useLoansAdvances,
  useLoanAdvanceLogs,
  useCreateLoanAdvance,
  useUpdateLoanAdvance,
  useCloseLoanAdvance,
  useDeleteLoanAdvance,
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
  // Query / Filter / Pagination State
  const [statusFilter, setStatusFilter] = useState<
    "Active Loan/Advance" | "Closed Loan/Advance" | "All"
  >("Active Loan/Advance");
  const [searchQuery, setSearchQuery] = useState("");
  const [sortField, setSortField] = useState<string>("created_at");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 10;

  // Modal Control States
  const [showAddModal, setShowAddModal] = useState(false);
  const [showViewModal, setShowViewModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showLogsModal, setShowLogsModal] = useState(false);
  const [selectedLoan, setSelectedLoan] = useState<LoanAdvanceSchema | null>(null);
  const [confirmCloseId, setConfirmCloseId] = useState<number | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState<number | null>(null);

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

  // Form State for Edit Loan
  const [editFormData, setEditFormData] = useState({
    name: "",
    principal_amount: 0,
    monthly_installment: 0,
    comment: "",
  });

  // Master Employees from Existing Module (Golden Rule)
  const { data: employeeData } = useEmployees({
    status: "active",
    page: 1,
    page_size: 100,
  });

  const activeEmployees = useMemo(() => {
    return employeeData?.items || [];
  }, [employeeData]);

  // Active Loans/Advances List from Live API
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

  // Logs List from Live API
  const { data: logsResponse, isLoading: isLogsLoading } = useLoanAdvanceLogs(
    { page: 1, page_size: 100 },
    showLogsModal
  );

  // Mutations
  const createMutation = useCreateLoanAdvance();
  const updateMutation = useUpdateLoanAdvance();
  const closeMutation = useCloseLoanAdvance();
  const deleteMutation = useDeleteLoanAdvance();

  const loanItems = loanResponse?.items || [];
  const totalRecords = loanResponse?.pagination.total_records || 0;
  const totalPages = loanResponse?.pagination.total_pages || 1;

  // Selected Employee Info for Add Modal
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

  // Add Loan Form Submit Handler
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

  // Edit Loan Form Submit Handler
  const handleEditSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedLoan) return;

    updateMutation.mutate(
      {
        id: selectedLoan.id,
        payload: {
          name: editFormData.name,
          principal_amount: editFormData.principal_amount,
          monthly_installment: editFormData.monthly_installment,
          comment: editFormData.comment,
        },
      },
      {
        onSuccess: () => {
          toast.success("Loan details updated successfully!");
          setShowEditModal(false);
          setSelectedLoan(null);
        },
        onError: (err: unknown) => {
          toast.error(getErrorMessage(err, "Failed to update Loan details"));
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
    <div className="p-6 space-y-6 max-w-[1600px] mx-auto text-slate-800 dark:text-slate-100">
      {/* 1. Header Toolbar */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        {/* Title + Count Badge */}
        <div className="flex items-center gap-2">
          <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
            Loan & Advance
          </h1>
          <span className="text-xl font-bold text-slate-600 dark:text-slate-400">
            ({totalRecords})
          </span>
        </div>

        {/* Action Controls Toolbar */}
        <div className="flex flex-wrap items-center gap-3">
          {/* Status Dropdown */}
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
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
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
            onClick={() => setShowLogsModal(true)}
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
                Failed to Load Loan Data
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                An error occurred while communicating with the server. Please check your network or retry.
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
        {!isLoading && !isError && loanItems.length === 0 && (
          <div className="p-16 text-center flex flex-col items-center justify-center space-y-3">
            <div className="w-16 h-16 bg-[#eaf4fd] dark:bg-slate-800 rounded-full flex items-center justify-center text-[#0070e0]">
              <Search className="w-8 h-8 stroke-[2.5]" />
            </div>
            <h3 className="text-sm font-bold text-slate-700 dark:text-slate-300">
              No Data Found
            </h3>
            <p className="text-xs text-slate-500 max-w-sm">
              No loan or advance records matched your search query or status filter.
            </p>
          </div>
        )}

        {/* Data Table */}
        {!isLoading && !isError && loanItems.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-[#eaf4fd] dark:bg-slate-800 text-slate-900 dark:text-slate-100 font-bold border-b border-slate-200 dark:border-slate-700">
                  <th
                    onClick={() => toggleSort("employee_code")}
                    className="py-3 px-4 cursor-pointer hover:bg-slate-200/50 dark:hover:bg-slate-700/50 select-none whitespace-nowrap"
                  >

                      Employee ID
                      {sortField === "employee_code" && (
                        <span>{sortOrder === "asc" ? " ↑" : " ↓"}</span>
                      )}
                  </th>
                  <th
                    onClick={() => toggleSort("employee_name")}
                    className="py-3 px-4 cursor-pointer hover:bg-slate-200/50 dark:hover:bg-slate-700/50 select-none whitespace-nowrap"
                  >

                      Employee Name
                      {sortField === "employee_name" && (
                        <span>{sortOrder === "asc" ? " ↑" : " ↓"}</span>
                      )}
                  </th>
                  <th className="py-3 px-4 whitespace-nowrap">Loan Name / Type</th>
                  <th
                    onClick={() => toggleSort("principal_amount")}
                    className="py-3 px-4 text-right cursor-pointer hover:bg-slate-200/50 dark:hover:bg-slate-700/50 select-none whitespace-nowrap"
                  >

                      Principal Amount
                      {sortField === "principal_amount" && (
                        <span>{sortOrder === "asc" ? " ↑" : " ↓"}</span>
                      )}
                  </th>
                  <th
                    onClick={() => toggleSort("total_debit")}
                    className="py-3 px-4 text-right cursor-pointer hover:bg-slate-200/50 dark:hover:bg-slate-700/50 select-none whitespace-nowrap"
                  >

                      Total Debit
                      {sortField === "total_debit" && (
                        <span>{sortOrder === "asc" ? " ↑" : " ↓"}</span>
                      )}
                  </th>
                  <th
                    onClick={() => toggleSort("outstanding_amount")}
                    className="py-3 px-4 text-right cursor-pointer hover:bg-slate-200/50 dark:hover:bg-slate-700/50 select-none whitespace-nowrap"
                  >

                      Outstanding Amount
                      {sortField === "outstanding_amount" && (
                        <span>{sortOrder === "asc" ? " ↑" : " ↓"}</span>
                      )}
                  </th>
                  <th className="py-3 px-4 text-center whitespace-nowrap">Status</th>
                  <th className="py-3 px-4 text-center whitespace-nowrap">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {loanItems.map((item) => (
                  <tr
                    key={item.id}
                    className="hover:bg-slate-50/80 dark:hover:bg-slate-800/40 transition-colors"
                  >
                    <td className="py-3 px-4 font-bold text-slate-900 dark:text-slate-100 whitespace-nowrap">
                      {item.employee_code || `EMP-${item.employee_id}`}
                    </td>
                    <td className="py-3 px-4 whitespace-nowrap font-medium">
                      <div>{item.employee_name || `Employee #${item.employee_id}`}</div>
                      <div className="text-[11px] text-slate-400 font-normal">
                        {item.branch_name || "Head Office"} • {item.department_name || "General"}
                      </div>
                    </td>
                    <td className="py-3 px-4 whitespace-nowrap">
                      <div className="font-semibold text-slate-800 dark:text-slate-200">{item.name}</div>
                      <div className="text-[10px] uppercase tracking-wider font-bold text-slate-400">
                        {item.type}
                      </div>
                    </td>
                    <td className="py-3 px-4 text-right font-medium text-slate-700 dark:text-slate-300 whitespace-nowrap">
                      {formatCurrency(Number(item.principal_amount))}
                    </td>
                    <td className="py-3 px-4 text-right font-medium text-emerald-600 dark:text-emerald-400 whitespace-nowrap">
                      {formatCurrency(Number(item.total_debit))}
                    </td>
                    <td className="py-3 px-4 text-right font-bold text-amber-600 dark:text-amber-400 whitespace-nowrap">
                      {formatCurrency(Number(item.outstanding_amount))}
                    </td>
                    <td className="py-3 px-4 text-center whitespace-nowrap">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                          item.status === "active"
                            ? "bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-400 border border-amber-200 dark:border-amber-900/50"
                            : "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-900/50"
                        }`}
                      >
                        {item.status}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-center whitespace-nowrap">
                      <div className="inline-flex items-center gap-1.5">
                        {/* View Action */}
                        <button
                          type="button"
                          onClick={() => {
                            setSelectedLoan(item);
                            setShowViewModal(true);
                          }}
                          title="View Details"
                          className="p-1 text-slate-500 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-slate-800 rounded transition-colors cursor-pointer"
                        >
                          <Eye className="w-4 h-4" />
                        </button>

                        {/* Edit Action */}
                        <button
                          type="button"
                          onClick={() => {
                            setSelectedLoan(item);
                            setEditFormData({
                              name: item.name,
                              principal_amount: Number(item.principal_amount),
                              monthly_installment: Number(item.monthly_installment),
                              comment: item.comment || "",
                            });
                            setShowEditModal(true);
                          }}
                          title="Edit Loan"
                          className="p-1 text-slate-500 hover:text-amber-600 hover:bg-amber-50 dark:hover:bg-slate-800 rounded transition-colors cursor-pointer"
                        >
                          <Edit2 className="w-4 h-4" />
                        </button>

                        {/* Close Loan Action */}
                        {item.status === "active" && (
                          <button
                            type="button"
                            onClick={() => setConfirmCloseId(item.id)}
                            title="Close Loan"
                            className="p-1 text-slate-500 hover:text-emerald-600 hover:bg-emerald-50 dark:hover:bg-slate-800 rounded transition-colors cursor-pointer"
                          >
                            <Lock className="w-4 h-4" />
                          </button>
                        )}

                        {/* Delete Action */}
                        <button
                          type="button"
                          onClick={() => setConfirmDeleteId(item.id)}
                          title="Delete Record"
                          className="p-1 text-slate-500 hover:text-red-600 hover:bg-red-50 dark:hover:bg-slate-800 rounded transition-colors cursor-pointer"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Footer Pagination Bar */}
        {!isLoading && !isError && loanItems.length > 0 && (
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

      {/* 3. Petpooja Add Loan/Advance Slide-Over Drawer */}
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
              {/* Employee ID / Dropdown */}
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
                  placeholder="e.g. Festival Advance, Bike Loan"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-2 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-blue-500 focus:outline-none"
                />
              </div>

              {/* Type Radio Group */}
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

              {/* Sanctioned Principal Amount */}
              <div>
                <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Principal Amount (₹) <span className="text-red-500">*</span>
                </label>
                <input
                  type="number"
                  required
                  min="1"
                  placeholder="e.g. 50000"
                  value={formData.principal_amount}
                  onChange={(e) =>
                    setFormData({ ...formData, principal_amount: e.target.value })
                  }
                  className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-2 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-blue-500 focus:outline-none"
                />
              </div>

              {/* Monthly Installment Recovery */}
              <div>
                <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Monthly Installment (₹) <span className="text-red-500">*</span>
                </label>
                <input
                  type="number"
                  required
                  min="1"
                  placeholder="e.g. 5000"
                  value={formData.monthly_installment}
                  onChange={(e) =>
                    setFormData({ ...formData, monthly_installment: e.target.value })
                  }
                  className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-2 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-blue-500 focus:outline-none"
                />
                <p className="text-[11px] text-slate-400 mt-1 italic">
                  This will be added to the employee&apos;s total monthly payroll deduction.
                </p>
              </div>

              {/* Transaction / Disbursal Date */}
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

              {/* Comment / Remarks */}
              <div>
                <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Notes / Context
                </label>
                <textarea
                  rows={2}
                  placeholder="Optional remarks..."
                  value={formData.comment}
                  onChange={(e) => setFormData({ ...formData, comment: e.target.value })}
                  className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-2 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-blue-500 focus:outline-none"
                />
              </div>
            </form>

            {/* Footer Actions: Petpooja Soft Blue */}
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

      {/* 4. View Loan Details Modal */}
      {showViewModal && selectedLoan && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xl w-full max-w-xl overflow-hidden">
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-800">
              <div>
                <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">
                  Loan Details — {selectedLoan.name}
                </h3>
                <p className="text-xs text-slate-500 font-medium mt-0.5">
                  {selectedLoan.employee_code} • {selectedLoan.employee_name}
                </p>
              </div>
              <button
                type="button"
                onClick={() => {
                  setShowViewModal(false);
                  setSelectedLoan(null);
                }}
                className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 space-y-4 text-xs">
              {/* Summary Header */}
              <div className="grid grid-cols-3 gap-3 p-3 bg-slate-50 dark:bg-slate-800/60 rounded-lg text-center">
                <div>
                  <p className="text-[11px] text-slate-500">Principal</p>
                  <p className="font-bold text-slate-900 dark:text-slate-100">
                    {formatCurrency(Number(selectedLoan.principal_amount))}
                  </p>
                </div>
                <div>
                  <p className="text-[11px] text-slate-500">Total Debited</p>
                  <p className="font-bold text-emerald-600 dark:text-emerald-400">
                    {formatCurrency(Number(selectedLoan.total_debit))}
                  </p>
                </div>
                <div>
                  <p className="text-[11px] text-slate-500">Outstanding</p>
                  <p className="font-bold text-amber-600 dark:text-amber-400">
                    {formatCurrency(Number(selectedLoan.outstanding_amount))}
                  </p>
                </div>
              </div>

              {/* Information Grid */}
              <div className="grid grid-cols-2 gap-3 text-xs">
                <div>
                  <span className="text-slate-400">Type:</span>{" "}
                  <span className="font-semibold uppercase">{selectedLoan.type}</span>
                </div>
                <div>
                  <span className="text-slate-400">Status:</span>{" "}
                  <span className="font-semibold uppercase">{selectedLoan.status}</span>
                </div>
                <div>
                  <span className="text-slate-400">Monthly Installment:</span>{" "}
                  <span className="font-semibold">{formatCurrency(Number(selectedLoan.monthly_installment))}</span>
                </div>
                <div>
                  <span className="text-slate-400">Disbursal Date:</span>{" "}
                  <span className="font-semibold">{selectedLoan.transaction_date}</span>
                </div>
              </div>

              {selectedLoan.comment && (
                <div className="p-2.5 bg-slate-50 dark:bg-slate-800/40 rounded border border-slate-200 dark:border-slate-800">
                  <span className="text-[11px] text-slate-400 font-semibold block">Notes:</span>
                  <p className="text-slate-700 dark:text-slate-300 mt-0.5">{selectedLoan.comment}</p>
                </div>
              )}
            </div>

            <div className="px-6 py-3 border-t border-slate-200 dark:border-slate-800 flex justify-end">
              <button
                type="button"
                onClick={() => {
                  setShowViewModal(false);
                  setSelectedLoan(null);
                }}
                className="px-4 py-2 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 text-slate-700 dark:text-slate-300 font-semibold text-xs rounded-lg transition-colors cursor-pointer"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 5. Edit Loan Modal */}
      {showEditModal && selectedLoan && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xl w-full max-w-md overflow-hidden">
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-800">
              <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">
                Edit Loan — {selectedLoan.name}
              </h3>
              <button
                type="button"
                onClick={() => {
                  setShowEditModal(false);
                  setSelectedLoan(null);
                }}
                className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleEditSubmit} className="p-6 space-y-4 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Loan Name
                </label>
                <input
                  type="text"
                  required
                  value={editFormData.name}
                  onChange={(e) => setEditFormData({ ...editFormData, name: e.target.value })}
                  className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-2 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-blue-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Principal Amount (₹)
                </label>
                <input
                  type="number"
                  required
                  value={editFormData.principal_amount}
                  onChange={(e) =>
                    setEditFormData({ ...editFormData, principal_amount: Number(e.target.value) })
                  }
                  className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-2 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-blue-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Monthly Installment (₹)
                </label>
                <input
                  type="number"
                  required
                  value={editFormData.monthly_installment}
                  onChange={(e) =>
                    setEditFormData({
                      ...editFormData,
                      monthly_installment: Number(e.target.value),
                    })
                  }
                  className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-2 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-blue-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Notes / Context
                </label>
                <textarea
                  rows={2}
                  value={editFormData.comment}
                  onChange={(e) => setEditFormData({ ...editFormData, comment: e.target.value })}
                  className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-2 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-blue-500 focus:outline-none"
                />
              </div>

              <div className="pt-2 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => {
                    setShowEditModal(false);
                    setSelectedLoan(null);
                  }}
                  className="px-4 py-2 border border-slate-300 dark:border-slate-700 hover:bg-slate-100 text-slate-700 dark:text-slate-300 rounded-lg font-semibold text-xs cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={updateMutation.isPending}
                  className="inline-flex items-center gap-2 px-4 py-2 bg-[#0070e0] hover:bg-blue-700 text-white rounded-lg font-bold text-xs cursor-pointer disabled:opacity-50"
                >
                  {updateMutation.isPending && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  <span>Save Changes</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* 6. View Logs Modal */}
      {showLogsModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xl w-full max-w-3xl overflow-hidden flex flex-col max-h-[85vh]">
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-800">
              <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">
                Loan & Advance Ledger Activity Logs
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
                        <th className="p-2.5">Transaction Type</th>
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
                          <td className="p-2.5 text-right font-bold text-emerald-600">
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

      {/* 7. Close Confirmation Modal */}
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
                Are you sure you want to manually mark this loan as closed?
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

      {/* 8. Delete Confirmation Modal */}
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
