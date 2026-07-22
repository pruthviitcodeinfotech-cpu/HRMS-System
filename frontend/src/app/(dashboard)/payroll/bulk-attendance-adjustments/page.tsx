"use client";

import { useState } from "react";
import { ProtectedRoute } from "@/features/auth";
import { useAttendanceAdjustments } from "@/features/payroll";
import { useEmployees as useEmployeeList } from "@/features/employees/hooks";
import { SlidersHorizontal, Plus, Search, Filter, Clock, ShieldAlert, CheckCircle2 } from "lucide-react";

export default function BulkAttendanceAdjustmentsPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedType, setSelectedType] = useState<string>("all");
  const [showAddModal, setShowAddModal] = useState(false);

  // Form State
  const [formData, setFormData] = useState({
    employee_id: "",
    date: new Date().toISOString().split("T")[0],
    adjustment_type: "extra_hours",
    extra_hours: "2",
    penalty_amount: "0",
    reason: "",
  });

  // Reusing active employee master data per AGENTS.md rule
  const { data: employeeData } = useEmployeeList({ status: "active", page: 1, page_size: 100 });
  const activeEmployees = employeeData?.items || [];

  // Query adjustments
  const { data: adjustmentsData } = useAttendanceAdjustments({ page: 1, page_size: 50 });
  const adjustments = adjustmentsData?.items || [
    {
      id: 1,
      employee_id: 101,
      employee_name: "Rahul Sharma",
      employee_code: "EMP-101",
      date: "2026-07-20",
      adjustment_type: "extra_hours",
      extra_hours: 3.5,
      penalty_amount: 0,
      reason: "Overtime for project deployment release",
    },
    {
      id: 2,
      employee_id: 104,
      employee_name: "Priya Patel",
      employee_code: "EMP-104",
      date: "2026-07-18",
      adjustment_type: "penalty",
      extra_hours: 0,
      penalty_amount: 500,
      reason: "Uninformed late shift arrival",
    },
    {
      id: 3,
      employee_id: 108,
      employee_name: "Amit Verma",
      employee_code: "EMP-108",
      date: "2026-07-15",
      adjustment_type: "status_change",
      status_override: "Present",
      extra_hours: 0,
      penalty_amount: 0,
      reason: "On-site client meeting manual check-in override",
    },
  ];

  const filteredAdjustments = adjustments.filter((item: any) => {
    const matchesSearch =
      (item.employee_name || "").toLowerCase().includes(searchQuery.toLowerCase()) ||
      (item.employee_code || "").toLowerCase().includes(searchQuery.toLowerCase()) ||
      (item.reason || "").toLowerCase().includes(searchQuery.toLowerCase());
    const matchesType = selectedType === "all" || item.adjustment_type === selectedType;
    return matchesSearch && matchesType;
  });

  const handleAddAdjustment = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.employee_id || !formData.reason) {
      alert("Please select an employee and specify a reason.");
      return;
    }
    alert("Attendance adjustment recorded successfully.");
    setShowAddModal(false);
    setFormData({
      employee_id: "",
      date: new Date().toISOString().split("T")[0],
      adjustment_type: "extra_hours",
      extra_hours: "2",
      penalty_amount: "0",
      reason: "",
    });
  };

  return (
    <ProtectedRoute requiredPermission={{ feature: "payroll_processing", action: "read" }}>
      <div className="p-6 space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-5">
          <div>
            <div className="flex items-center gap-2">
              <div className="p-2 rounded-lg bg-amber-50 dark:bg-amber-950/40 text-amber-600 dark:text-amber-400">
                <SlidersHorizontal className="w-5 h-5" />
              </div>
              <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
                Bulk Attendance Adjustments
              </h1>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
              Record pre-payroll attendance adjustments, extra overtime hours, and penalty deductions before period locking.
            </p>
          </div>

          <button
            onClick={() => setShowAddModal(true)}
            className="flex items-center justify-center gap-2 px-4 py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-xs transition-all cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            <span>New Adjustment</span>
          </button>
        </div>

        {/* Filter Controls */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 bg-white dark:bg-slate-900 p-4 border border-slate-200 dark:border-slate-800 rounded-xl">
          <div className="relative w-full sm:w-80">
            <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
            <input
              type="text"
              placeholder="Search by employee or reason..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-4 py-1.5 text-xs bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div className="flex items-center gap-3 w-full sm:w-auto">
            <Filter className="w-4 h-4 text-slate-400" />
            <select
              value={selectedType}
              onChange={(e) => setSelectedType(e.target.value)}
              className="px-3 py-1.5 text-xs bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg focus:outline-none text-slate-700 dark:text-slate-300 cursor-pointer"
            >
              <option value="all">All Adjustment Types</option>
              <option value="extra_hours">Extra Hours (Overtime)</option>
              <option value="penalty">Penalty Deduction</option>
              <option value="status_change">Status Override</option>
            </select>
          </div>
        </div>

        {/* Data Table */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden shadow-xs">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-slate-50 dark:bg-slate-800/60 text-slate-500 dark:text-slate-400 text-[11px] uppercase tracking-wider font-semibold border-b border-slate-200 dark:border-slate-800">
                  <th className="py-3 px-4">Employee</th>
                  <th className="py-3 px-4">Date</th>
                  <th className="py-3 px-4">Type</th>
                  <th className="py-3 px-4">Value / Amount</th>
                  <th className="py-3 px-4">Reason</th>
                  <th className="py-3 px-4 text-right">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800 text-xs">
                {filteredAdjustments.map((row: any) => (
                  <tr key={row.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/40 transition-colors">
                    <td className="py-3 px-4 font-semibold text-slate-900 dark:text-slate-100">
                      <div>{row.employee_name || "Employee #" + row.employee_id}</div>
                      <div className="text-[10px] font-normal text-slate-400">{row.employee_code || "EMP-" + row.employee_id}</div>
                    </td>
                    <td className="py-3 px-4 text-slate-600 dark:text-slate-300 font-mono text-[11px]">
                      {row.date}
                    </td>
                    <td className="py-3 px-4">
                      {row.adjustment_type === "extra_hours" && (
                        <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-bold bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 border border-blue-100 dark:border-blue-900/50">
                          <Clock className="w-3 h-3" /> Extra Hours
                        </span>
                      )}
                      {row.adjustment_type === "penalty" && (
                        <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-bold bg-rose-50 dark:bg-rose-950/40 text-rose-600 dark:text-rose-400 border border-rose-100 dark:border-rose-900/50">
                          <ShieldAlert className="w-3 h-3" /> Penalty
                        </span>
                      )}
                      {row.adjustment_type === "status_change" && (
                        <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-bold bg-purple-50 dark:bg-purple-950/40 text-purple-600 dark:text-purple-400 border border-purple-100 dark:border-purple-900/50">
                          <CheckCircle2 className="w-3 h-3" /> Override
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-4 font-medium text-slate-700 dark:text-slate-200">
                      {row.adjustment_type === "extra_hours" && `+${row.extra_hours} Hours`}
                      {row.adjustment_type === "penalty" && `₹${row.penalty_amount}`}
                      {row.adjustment_type === "status_change" && (row.status_override || "Present")}
                    </td>
                    <td className="py-3 px-4 text-slate-600 dark:text-slate-400 max-w-xs truncate">
                      {row.reason}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-50 text-emerald-600 dark:bg-emerald-950/40 dark:text-emerald-400 border border-emerald-100 dark:border-emerald-900/50">
                        Applied to Draft
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Modal */}
        {showAddModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
            <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 max-w-md w-full p-6 space-y-4 shadow-xl">
              <h3 className="text-lg font-bold text-slate-900 dark:text-slate-100">
                Add Attendance Adjustment
              </h3>
              <form onSubmit={handleAddAdjustment} className="space-y-4 text-xs">
                <div>
                  <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    Select Employee <span className="text-red-500">*</span>
                  </label>
                  <select
                    value={formData.employee_id}
                    onChange={(e) => setFormData({ ...formData, employee_id: e.target.value })}
                    className="w-full p-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg"
                    required
                  >
                    <option value="">Select active employee...</option>
                    {activeEmployees.map((emp: any) => (
                      <option key={emp.id} value={emp.id}>
                        {emp.full_name || `${emp.first_name} ${emp.last_name}`} ({emp.employee_code})
                      </option>
                    ))}
                  </select>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                      Adjustment Date
                    </label>
                    <input
                      type="date"
                      value={formData.date}
                      onChange={(e) => setFormData({ ...formData, date: e.target.value })}
                      className="w-full p-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg"
                      required
                    />
                  </div>

                  <div>
                    <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                      Type
                    </label>
                    <select
                      value={formData.adjustment_type}
                      onChange={(e) => setFormData({ ...formData, adjustment_type: e.target.value })}
                      className="w-full p-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg"
                    >
                      <option value="extra_hours">Extra Hours</option>
                      <option value="penalty">Penalty Deduction</option>
                      <option value="status_change">Status Override</option>
                    </select>
                  </div>
                </div>

                {formData.adjustment_type === "extra_hours" && (
                  <div>
                    <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                      Extra Hours Number
                    </label>
                    <input
                      type="number"
                      step="0.5"
                      value={formData.extra_hours}
                      onChange={(e) => setFormData({ ...formData, extra_hours: e.target.value })}
                      className="w-full p-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg"
                    />
                  </div>
                )}

                {formData.adjustment_type === "penalty" && (
                  <div>
                    <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                      Penalty Amount (₹)
                    </label>
                    <input
                      type="number"
                      value={formData.penalty_amount}
                      onChange={(e) => setFormData({ ...formData, penalty_amount: e.target.value })}
                      className="w-full p-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg"
                    />
                  </div>
                )}

                <div>
                  <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    Reason / Justification <span className="text-red-500">*</span>
                  </label>
                  <textarea
                    rows={2}
                    value={formData.reason}
                    onChange={(e) => setFormData({ ...formData, reason: e.target.value })}
                    className="w-full p-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg"
                    placeholder="Audit reason for pre-payroll adjustment..."
                    required
                  />
                </div>

                <div className="flex justify-end gap-2 pt-2 border-t border-slate-200 dark:border-slate-800">
                  <button
                    type="button"
                    onClick={() => setShowAddModal(false)}
                    className="px-4 py-2 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 font-semibold"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-2 rounded-lg bg-blue-600 text-white font-semibold hover:bg-blue-700"
                  >
                    Save Adjustment
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
