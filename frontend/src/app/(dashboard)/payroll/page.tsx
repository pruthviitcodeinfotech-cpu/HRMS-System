"use client";

import { ProtectedRoute } from "@/features/auth";
import Link from "next/link";
import {
  SlidersHorizontal,
  PlayCircle,
  FolderTree,
  UserCheck,
  FileCheck2,
  ArrowRight,
  ShieldCheck,
} from "lucide-react";

export default function PayrollPage() {
  const subModules = [
    {
      href: "/payroll/bulk-attendance-adjustments",
      title: "Bulk Attendance Adjustments",
      description: "Manage overtime extra hours, attendance status overrides, and manual penalty deductions prior to payroll processing.",
      icon: SlidersHorizontal,
      iconBg: "bg-amber-50 dark:bg-amber-950/40 text-amber-600 dark:text-amber-400",
      badge: null,
      metric: "Pre-processing",
    },
    {
      href: "/payroll/process-payroll",
      title: "Process Payroll",
      description: "Calculate monthly payroll runs, preview salary slips, trigger recalculations, and lock finalized pay cycles.",
      icon: PlayCircle,
      iconBg: "bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400",
      badge: "New",
      metric: "Core Calculation",
    },
    {
      href: "/payroll/payroll-group",
      title: "Payroll Group",
      description: "Configure salary structures, payment cycles, cutoff days, and customizable payslip column layout rules.",
      icon: FolderTree,
      iconBg: "bg-purple-50 dark:bg-purple-950/40 text-purple-600 dark:text-purple-400",
      badge: null,
      metric: "Salary Structures",
    },
    {
      href: "/payroll/assign-payroll-group",
      title: "Assign Payroll Group",
      description: "Map employees to dedicated payroll groups, track historical group assignments, and configure pay band changes.",
      icon: UserCheck,
      iconBg: "bg-emerald-50 dark:bg-emerald-950/40 text-emerald-600 dark:text-emerald-400",
      badge: null,
      metric: "Employee Mapping",
    },
    {
      href: "/payroll/finalized-payroll-details",
      title: "Finalized Payroll Details",
      description: "Inspect locked historical payroll runs, disburse bank payments, download PDF payslips, and dispatch email slips.",
      icon: FileCheck2,
      iconBg: "bg-cyan-50 dark:bg-cyan-950/40 text-cyan-600 dark:text-cyan-400",
      badge: null,
      metric: "Payout & Audit",
    },
  ];

  return (
    <ProtectedRoute requiredPermission={{ feature: "payroll_processing", action: "read" }}>
      <div className="p-6 space-y-8">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-6">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
                Payroll Management
              </h1>
              <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-blue-100 dark:bg-blue-950 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800">
                v2.0
              </span>
            </div>
            <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
              Select a payroll module below to manage salary structures, attendance pre-adjustments, monthly processing, and payout auditing.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-100 dark:bg-slate-800 text-xs font-medium text-slate-700 dark:text-slate-300">
              <ShieldCheck className="w-4 h-4 text-emerald-500" />
              <span>Audit Ready & Compliance Enforced</span>
            </div>
          </div>
        </div>

        {/* Navigation Hierarchy Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {subModules.map((item) => {
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                className="group relative flex flex-col justify-between p-6 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl hover:border-blue-500 dark:hover:border-blue-500 transition-all duration-200 shadow-xs hover:shadow-md"
              >
                <div>
                  <div className="flex items-center justify-between mb-4">
                    <div className={`w-12 h-12 rounded-xl ${item.iconBg} flex items-center justify-center transition-transform group-hover:scale-105`}>
                      <Icon className="w-6 h-6" />
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-[11px] font-semibold px-2 py-0.5 rounded-md bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400">
                        {item.metric}
                      </span>
                      {item.badge && (
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 border border-blue-100 dark:border-blue-900/50">
                          {item.badge}
                        </span>
                      )}
                    </div>
                  </div>

                  <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                    {item.title}
                  </h2>
                  <p className="text-xs text-slate-500 dark:text-slate-400 mt-2 line-clamp-3 leading-relaxed">
                    {item.description}
                  </p>
                </div>

                <div className="mt-6 pt-4 border-t border-slate-100 dark:border-slate-800/80 flex items-center justify-between text-xs font-semibold text-blue-600 dark:text-blue-400">
                  <span>Open {item.title}</span>
                  <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                </div>
              </Link>
            );
          })}
        </div>
      </div>
    </ProtectedRoute>
  );
}
