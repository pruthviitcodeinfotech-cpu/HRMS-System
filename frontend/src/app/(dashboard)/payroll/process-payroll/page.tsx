"use client";

import { useState } from "react";
import { ProtectedRoute } from "@/features/auth";
import { usePayrollGroups } from "@/features/payroll";
import { PlayCircle, RefreshCw, Lock } from "lucide-react";

export default function ProcessPayrollPage() {
  const [selectedGroup, setSelectedGroup] = useState<string>("");
  const [cycleMonth, setCycleMonth] = useState<string>("2026-07");
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [runGenerated, setRunGenerated] = useState<boolean>(true);

  const { data: groupsData } = usePayrollGroups();
  const groups = groupsData?.items || [
    { id: 1, group_name: "Executive & HQ Staff", code: "EXEC-HQ", pay_frequency: "Monthly" },
    { id: 2, group_name: "Factory & Operations Staff", code: "OPS-FAC", pay_frequency: "Monthly" },
  ];

  // Dummy computed rows for display
  const records = [
    {
      id: 1,
      employee_name: "Aarav Sharma",
      employee_code: "EMP-001",
      department: "Engineering",
      basic_salary: 85000,
      gross_earnings: 110000,
      total_deductions: 12500,
      net_payable: 97500,
      paid_days: 31,
      unpaid_days: 0,
      overtime_hours: 4.5,
      status: "draft",
    },
    {
      id: 2,
      employee_name: "Neha Gupta",
      employee_code: "EMP-004",
      department: "Human Resources",
      basic_salary: 65000,
      gross_earnings: 82000,
      total_deductions: 9200,
      net_payable: 72800,
      paid_days: 30,
      unpaid_days: 1,
      overtime_hours: 0,
      status: "draft",
    },
    {
      id: 3,
      employee_name: "Vikram Malhotra",
      employee_code: "EMP-012",
      department: "Finance",
      basic_salary: 92000,
      gross_earnings: 125000,
      total_deductions: 14800,
      net_payable: 110200,
      paid_days: 31,
      unpaid_days: 0,
      overtime_hours: 2.0,
      status: "draft",
    },
  ];

  const handleGenerate = () => {
    setIsProcessing(true);
    setTimeout(() => {
      setIsProcessing(false);
      setRunGenerated(true);
      alert("Payroll calculation run generated successfully.");
    }, 800);
  };

  const handleFinalize = () => {
    if (confirm("Are you sure you want to lock and finalize this payroll run? This will lock all computed entries.")) {
      alert("Payroll run successfully locked & finalized.");
    }
  };

  return (
    <ProtectedRoute requiredPermission={{ feature: "payroll_processing", action: "read" }}>
      <div className="p-6 space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-5">
          <div>
            <div className="flex items-center gap-2">
              <div className="p-2 rounded-lg bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400">
                <PlayCircle className="w-5 h-5" />
              </div>
              <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
                Process Payroll
              </h1>
              <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 border border-blue-100 dark:border-blue-900/50">
                New
              </span>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
              Calculate monthly employee compensation, preview earnings & deductions, and lock period pay runs.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleGenerate}
              disabled={isProcessing}
              className="flex items-center gap-2 px-4 py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-xs transition-all cursor-pointer disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 ${isProcessing ? "animate-spin" : ""}`} />
              <span>{runGenerated ? "Recalculate Run" : "Generate Payroll"}</span>
            </button>

            {runGenerated && (
              <button
                onClick={handleFinalize}
                className="flex items-center gap-2 px-4 py-2 text-xs font-semibold text-emerald-700 dark:text-emerald-300 bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 hover:bg-emerald-100 rounded-lg transition-all cursor-pointer"
              >
                <Lock className="w-4 h-4" />
                <span>Lock & Finalize Run</span>
              </button>
            )}
          </div>
        </div>

        {/* Processing Control Bar */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 bg-white dark:bg-slate-900 p-4 border border-slate-200 dark:border-slate-800 rounded-xl">
          <div>
            <label className="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-1">
              Target Payroll Group
            </label>
            <select
              value={selectedGroup}
              onChange={(e) => setSelectedGroup(e.target.value)}
              className="w-full p-2 text-xs bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-slate-800 dark:text-slate-200"
            >
              <option value="">All Payroll Groups (All Employees)</option>
              {groups.map((g: any) => (
                <option key={g.id} value={g.id}>
                  {g.group_name} ({g.code})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-600 dark:text-slate-400 mb-1">
              Payroll Cycle Period
            </label>
            <input
              type="month"
              value={cycleMonth}
              onChange={(e) => setCycleMonth(e.target.value)}
              className="w-full p-2 text-xs bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-slate-800 dark:text-slate-200"
            />
          </div>

          <div className="flex items-end justify-between p-2 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-800">
            <div>
              <div className="text-[10px] uppercase font-bold text-slate-400">Total Net Payout</div>
              <div className="text-lg font-bold text-blue-600 dark:text-blue-400">₹2,80,500</div>
            </div>
            <div className="text-right">
              <div className="text-[10px] uppercase font-bold text-slate-400">Headcount</div>
              <div className="text-sm font-bold text-slate-700 dark:text-slate-300">3 Employees</div>
            </div>
          </div>
        </div>

        {/* Data Table */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden shadow-xs">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-slate-50 dark:bg-slate-800/60 text-slate-500 dark:text-slate-400 text-[11px] uppercase tracking-wider font-semibold border-b border-slate-200 dark:border-slate-800">
                  <th className="py-3 px-4">Employee</th>
                  <th className="py-3 px-4">Department</th>
                  <th className="py-3 px-4 text-right">Paid Days</th>
                  <th className="py-3 px-4 text-right">Basic Salary</th>
                  <th className="py-3 px-4 text-right">Gross Earnings</th>
                  <th className="py-3 px-4 text-right">Deductions</th>
                  <th className="py-3 px-4 text-right">Net Payable</th>
                  <th className="py-3 px-4 text-center">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800 text-xs">
                {records.map((row) => (
                  <tr key={row.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/40 transition-colors">
                    <td className="py-3 px-4 font-semibold text-slate-900 dark:text-slate-100">
                      <div>{row.employee_name}</div>
                      <div className="text-[10px] font-normal text-slate-400">{row.employee_code}</div>
                    </td>
                    <td className="py-3 px-4 text-slate-600 dark:text-slate-300">
                      {row.department}
                    </td>
                    <td className="py-3 px-4 text-right font-mono text-[11px] text-slate-700 dark:text-slate-300">
                      {row.paid_days} Days
                    </td>
                    <td className="py-3 px-4 text-right font-mono text-[11px] text-slate-600 dark:text-slate-400">
                      ₹{row.basic_salary.toLocaleString()}
                    </td>
                    <td className="py-3 px-4 text-right font-mono text-[11px] font-semibold text-emerald-600 dark:text-emerald-400">
                      ₹{row.gross_earnings.toLocaleString()}
                    </td>
                    <td className="py-3 px-4 text-right font-mono text-[11px] font-semibold text-rose-600 dark:text-rose-400">
                      -₹{row.total_deductions.toLocaleString()}
                    </td>
                    <td className="py-3 px-4 text-right font-mono text-xs font-bold text-blue-600 dark:text-blue-400">
                      ₹{row.net_payable.toLocaleString()}
                    </td>
                    <td className="py-3 px-4 text-center">
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-50 text-amber-600 dark:bg-amber-950/40 dark:text-amber-400 border border-amber-100 dark:border-amber-900/50">
                        Draft Calculated
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </ProtectedRoute>
  );
}
