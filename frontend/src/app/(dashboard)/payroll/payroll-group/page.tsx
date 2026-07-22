"use client";

import { useState } from "react";
import { ProtectedRoute } from "@/features/auth";
import { usePayrollGroups } from "@/features/payroll";
import { FolderTree, Plus, Search, CheckCircle2 } from "lucide-react";

export default function PayrollGroupPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [showAddModal, setShowAddModal] = useState(false);

  const [formData, setFormData] = useState({
    group_name: "",
    code: "",
    pay_frequency: "Monthly",
    cutoff_day: "25",
    pay_day: "30",
    description: "",
  });

  const { data: groupsData } = usePayrollGroups();
  const groups = groupsData?.items || [
    {
      id: 1,
      group_name: "Executive & HQ Staff",
      code: "EXEC-HQ",
      pay_frequency: "Monthly",
      cutoff_day: 25,
      pay_day: 30,
      description: "Standard executive salary structure with pf and medical allowances.",
      is_active: true,
      employee_count: 42,
    },
    {
      id: 2,
      group_name: "Factory & Operations Staff",
      code: "OPS-FAC",
      pay_frequency: "Monthly",
      cutoff_day: 20,
      pay_day: 28,
      description: "Overtime-eligible operational staff pay band with shift allowance.",
      is_active: true,
      employee_count: 128,
    },
    {
      id: 3,
      group_name: "Contract & Retainer Consultants",
      code: "CONSULT-RET",
      pay_frequency: "Bi-Weekly",
      cutoff_day: 15,
      pay_day: 18,
      description: "Retainer payout schedule with TDS deduction.",
      is_active: true,
      employee_count: 14,
    },
  ];

  const filteredGroups = groups.filter((g: any) =>
    (g.group_name || "").toLowerCase().includes(searchQuery.toLowerCase()) ||
    (g.code || "").toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleCreateGroup = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.group_name || !formData.code) {
      alert("Please specify Group Name and Code.");
      return;
    }
    alert("Payroll group created successfully.");
    setShowAddModal(false);
    setFormData({
      group_name: "",
      code: "",
      pay_frequency: "Monthly",
      cutoff_day: "25",
      pay_day: "30",
      description: "",
    });
  };

  return (
    <ProtectedRoute requiredPermission={{ feature: "payroll_processing", action: "read" }}>
      <div className="p-6 space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-5">
          <div>
            <div className="flex items-center gap-2">
              <div className="p-2 rounded-lg bg-purple-50 dark:bg-purple-950/40 text-purple-600 dark:text-purple-400">
                <FolderTree className="w-5 h-5" />
              </div>
              <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
                Payroll Groups
              </h1>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
              Configure organizational salary structures, pay frequencies, attendance cutoff days, and disbursement schedules.
            </p>
          </div>

          <button
            onClick={() => setShowAddModal(true)}
            className="flex items-center justify-center gap-2 px-4 py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-xs transition-all cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            <span>Create Group</span>
          </button>
        </div>

        {/* Search */}
        <div className="flex items-center justify-between bg-white dark:bg-slate-900 p-4 border border-slate-200 dark:border-slate-800 rounded-xl">
          <div className="relative w-full sm:w-80">
            <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
            <input
              type="text"
              placeholder="Search by group name or code..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-4 py-1.5 text-xs bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>

        {/* Group Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredGroups.map((group: any) => (
            <div
              key={group.id}
              className="p-5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl space-y-4 shadow-xs hover:border-purple-300 dark:hover:border-purple-800 transition-all"
            >
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">
                    {group.group_name}
                  </h3>
                  <span className="inline-block mt-0.5 px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
                    {group.code}
                  </span>
                </div>

                <span className="flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded bg-emerald-50 text-emerald-600 dark:bg-emerald-950/40 dark:text-emerald-400 border border-emerald-100 dark:border-emerald-900/50">
                  <CheckCircle2 className="w-3 h-3" /> Active
                </span>
              </div>

              <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed min-h-[36px]">
                {group.description || "Standard organization payroll group configuration."}
              </p>

              <div className="grid grid-cols-2 gap-2 pt-3 border-t border-slate-100 dark:border-slate-800/80 text-xs">
                <div className="p-2 rounded-lg bg-slate-50 dark:bg-slate-800/50">
                  <div className="text-[10px] font-semibold text-slate-400">Frequency</div>
                  <div className="font-semibold text-slate-700 dark:text-slate-300">{group.pay_frequency}</div>
                </div>
                <div className="p-2 rounded-lg bg-slate-50 dark:bg-slate-800/50">
                  <div className="text-[10px] font-semibold text-slate-400">Cutoff / Pay Day</div>
                  <div className="font-semibold text-slate-700 dark:text-slate-300">
                    {group.cutoff_day}th / {group.pay_day}th
                  </div>
                </div>
              </div>

              <div className="flex items-center justify-between text-xs pt-1">
                <span className="text-slate-500 dark:text-slate-400 font-medium">Mapped Employees</span>
                <span className="font-bold text-purple-600 dark:text-purple-400 bg-purple-50 dark:bg-purple-950/40 px-2 py-0.5 rounded border border-purple-100 dark:border-purple-900/50">
                  {group.employee_count || 0} Members
                </span>
              </div>
            </div>
          ))}
        </div>

        {/* Modal */}
        {showAddModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
            <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 max-w-md w-full p-6 space-y-4 shadow-xl">
              <h3 className="text-lg font-bold text-slate-900 dark:text-slate-100">
                Create Payroll Group
              </h3>
              <form onSubmit={handleCreateGroup} className="space-y-4 text-xs">
                <div>
                  <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    Group Name <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. Senior Leadership & Executive"
                    value={formData.group_name}
                    onChange={(e) => setFormData({ ...formData, group_name: e.target.value })}
                    className="w-full p-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg"
                    required
                  />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                      Code <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="text"
                      placeholder="EXEC-01"
                      value={formData.code}
                      onChange={(e) => setFormData({ ...formData, code: e.target.value })}
                      className="w-full p-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg uppercase"
                      required
                    />
                  </div>

                  <div>
                    <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                      Pay Frequency
                    </label>
                    <select
                      value={formData.pay_frequency}
                      onChange={(e) => setFormData({ ...formData, pay_frequency: e.target.value })}
                      className="w-full p-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg"
                    >
                      <option value="Monthly">Monthly</option>
                      <option value="Bi-Weekly">Bi-Weekly</option>
                      <option value="Weekly">Weekly</option>
                    </select>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                      Monthly Cutoff Day
                    </label>
                    <input
                      type="number"
                      min="1"
                      max="31"
                      value={formData.cutoff_day}
                      onChange={(e) => setFormData({ ...formData, cutoff_day: e.target.value })}
                      className="w-full p-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg"
                    />
                  </div>

                  <div>
                    <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                      Monthly Pay Day
                    </label>
                    <input
                      type="number"
                      min="1"
                      max="31"
                      value={formData.pay_day}
                      onChange={(e) => setFormData({ ...formData, pay_day: e.target.value })}
                      className="w-full p-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg"
                    />
                  </div>
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    Description
                  </label>
                  <textarea
                    rows={2}
                    value={formData.description}
                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                    className="w-full p-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg"
                    placeholder="Structure rules and pay component applicability..."
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
                    Create Group
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
