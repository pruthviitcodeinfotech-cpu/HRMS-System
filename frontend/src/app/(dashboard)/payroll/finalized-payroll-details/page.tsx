"use client";

import { useState } from "react";
import { ProtectedRoute } from "@/features/auth";
import { useFinalizedPayrollRuns } from "@/features/payroll";
import { FileCheck2, Search, Download, Mail, Lock, CheckCircle2, AlertCircle } from "lucide-react";

export default function FinalizedPayrollDetailsPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [showPaymentModal, setShowPaymentModal] = useState(false);
  const [selectedRun, setSelectedRun] = useState<any>(null);

  const [paymentForm, setPaymentForm] = useState({
    payment_date: new Date().toISOString().split("T")[0],
    payment_reference: "",
    remarks: "",
  });

  const { data: runsData } = useFinalizedPayrollRuns();
  const finalizedRuns = runsData?.items || [
    {
      id: 101,
      run_code: "RUN-2026-06-HQ",
      payroll_group_name: "Executive & HQ Staff",
      cycle_start_date: "2026-06-01",
      cycle_end_date: "2026-06-30",
      total_employees: 42,
      total_gross: 4620000,
      total_deductions: 520000,
      total_net: 4100000,
      payment_status: "paid",
      finalized_at: "2026-07-02 10:30 AM",
      finalized_by_name: "Admin User",
    },
    {
      id: 102,
      run_code: "RUN-2026-06-OPS",
      payroll_group_name: "Factory & Operations Staff",
      cycle_start_date: "2026-06-01",
      cycle_end_date: "2026-06-30",
      total_employees: 128,
      total_gross: 8960000,
      total_deductions: 1040000,
      total_net: 7920000,
      payment_status: "unpaid",
      finalized_at: "2026-07-03 04:15 PM",
      finalized_by_name: "Finance Controller",
    },
  ];

  const filteredRuns = finalizedRuns.filter((run: any) =>
    (run.run_code || "").toLowerCase().includes(searchQuery.toLowerCase()) ||
    (run.payroll_group_name || "").toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleOpenPayment = (run: any) => {
    setSelectedRun(run);
    setShowPaymentModal(true);
  };

  const handleRecordPayment = (e: React.FormEvent) => {
    e.preventDefault();
    if (!paymentForm.payment_reference) {
      alert("Please enter bank disbursement reference number.");
      return;
    }
    alert(`Bank payment recorded for run ${selectedRun.run_code}.`);
    setShowPaymentModal(false);
  };

  const handleDownloadPdf = (runCode: string) => {
    alert(`Downloading bank disbursement summary & payslips zip for ${runCode}...`);
  };

  const handleEmailSlips = (runCode: string) => {
    alert(`Enqueued payslip emails for all employees under ${runCode}.`);
  };

  return (
    <ProtectedRoute requiredPermission={{ feature: "payroll_processing", action: "read" }}>
      <div className="p-6 space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-5">
          <div>
            <div className="flex items-center gap-2">
              <div className="p-2 rounded-lg bg-cyan-50 dark:bg-cyan-950/40 text-cyan-600 dark:text-cyan-400">
                <FileCheck2 className="w-5 h-5" />
              </div>
              <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
                Finalized Payroll Details
              </h1>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
              Audit locked historical payroll cycles, record bank disbursements, and dispatch employee payslips.
            </p>
          </div>
        </div>

        {/* Search */}
        <div className="flex items-center justify-between bg-white dark:bg-slate-900 p-4 border border-slate-200 dark:border-slate-800 rounded-xl">
          <div className="relative w-full sm:w-80">
            <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
            <input
              type="text"
              placeholder="Search by run code or group name..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-4 py-1.5 text-xs bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>

        {/* Data Table */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden shadow-xs">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-slate-50 dark:bg-slate-800/60 text-slate-500 dark:text-slate-400 text-[11px] uppercase tracking-wider font-semibold border-b border-slate-200 dark:border-slate-800">
                  <th className="py-3 px-4">Run Code & Group</th>
                  <th className="py-3 px-4">Cycle Period</th>
                  <th className="py-3 px-4 text-center">Headcount</th>
                  <th className="py-3 px-4 text-right">Total Net Pay</th>
                  <th className="py-3 px-4 text-center">Payment Status</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800 text-xs">
                {filteredRuns.map((run: any) => (
                  <tr key={run.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/40 transition-colors">
                    <td className="py-3 px-4 font-semibold text-slate-900 dark:text-slate-100">
                      <div className="flex items-center gap-1.5">
                        <Lock className="w-3.5 h-3.5 text-slate-400" />
                        <span>{run.run_code}</span>
                      </div>
                      <div className="text-[10px] font-normal text-slate-500 mt-0.5">{run.payroll_group_name}</div>
                    </td>
                    <td className="py-3 px-4 text-slate-600 dark:text-slate-300 font-mono text-[11px]">
                      {run.cycle_start_date} to {run.cycle_end_date}
                    </td>
                    <td className="py-3 px-4 text-center font-semibold text-slate-700 dark:text-slate-300">
                      {run.total_employees} Employees
                    </td>
                    <td className="py-3 px-4 text-right font-mono font-bold text-cyan-600 dark:text-cyan-400">
                      ₹{run.total_net.toLocaleString()}
                    </td>
                    <td className="py-3 px-4 text-center">
                      {run.payment_status === "paid" ? (
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded text-[10px] font-bold bg-emerald-50 text-emerald-600 dark:bg-emerald-950/40 dark:text-emerald-400 border border-emerald-100 dark:border-emerald-900/50">
                          <CheckCircle2 className="w-3 h-3" /> Paid & Disbursed
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded text-[10px] font-bold bg-amber-50 text-amber-600 dark:bg-amber-950/40 dark:text-amber-400 border border-amber-100 dark:border-amber-900/50">
                          <AlertCircle className="w-3 h-3" /> Disbursement Pending
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-right space-x-2">
                      {run.payment_status === "unpaid" && (
                        <button
                          onClick={() => handleOpenPayment(run)}
                          className="px-2.5 py-1 rounded text-xs font-semibold text-emerald-700 dark:text-emerald-300 bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 hover:bg-emerald-100 transition-colors"
                        >
                          Record Payment
                        </button>
                      )}
                      <button
                        onClick={() => handleDownloadPdf(run.run_code)}
                        className="px-2.5 py-1 rounded text-xs font-semibold text-slate-700 dark:text-slate-300 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 transition-colors"
                        title="Download Summary & Payslips"
                      >
                        <Download className="w-3.5 h-3.5 inline" />
                      </button>
                      <button
                        onClick={() => handleEmailSlips(run.run_code)}
                        className="px-2.5 py-1 rounded text-xs font-semibold text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-950/40 hover:bg-blue-100 transition-colors"
                        title="Email Payslips"
                      >
                        <Mail className="w-3.5 h-3.5 inline" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Modal */}
        {showPaymentModal && selectedRun && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
            <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 max-w-md w-full p-6 space-y-4 shadow-xl">
              <h3 className="text-lg font-bold text-slate-900 dark:text-slate-100">
                Record Bank Payout
              </h3>
              <p className="text-xs text-slate-500">
                Recording disbursement for <span className="font-bold text-slate-800 dark:text-slate-200">{selectedRun.run_code}</span> (₹{selectedRun.total_net.toLocaleString()}).
              </p>
              <form onSubmit={handleRecordPayment} className="space-y-4 text-xs">
                <div>
                  <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    Disbursement Date
                  </label>
                  <input
                    type="date"
                    value={paymentForm.payment_date}
                    onChange={(e) => setPaymentForm({ ...paymentForm, payment_date: e.target.value })}
                    className="w-full p-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg"
                    required
                  />
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    Bank Reference / UTR Number <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. HDFC-NEFT-98402910"
                    value={paymentForm.payment_reference}
                    onChange={(e) => setPaymentForm({ ...paymentForm, payment_reference: e.target.value })}
                    className="w-full p-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg"
                    required
                  />
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    Disbursement Remarks
                  </label>
                  <textarea
                    rows={2}
                    value={paymentForm.remarks}
                    onChange={(e) => setPaymentForm({ ...paymentForm, remarks: e.target.value })}
                    className="w-full p-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg"
                    placeholder="Batch payout notes..."
                  />
                </div>

                <div className="flex justify-end gap-2 pt-2 border-t border-slate-200 dark:border-slate-800">
                  <button
                    type="button"
                    onClick={() => setShowPaymentModal(false)}
                    className="px-4 py-2 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 font-semibold"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-2 rounded-lg bg-emerald-600 text-white font-semibold hover:bg-emerald-700"
                  >
                    Confirm Payout
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </ProtectedRoute>
  );
}
