"use client";

import { ApprovalStatus } from "../types";

interface ApprovalStatusTabsProps {
  activeTab: ApprovalStatus;
  counts: Record<ApprovalStatus, number>;
  onTabChange: (status: ApprovalStatus) => void;
}

export function ApprovalStatusTabs({
  activeTab,
  counts,
  onTabChange,
}: ApprovalStatusTabsProps) {
  const tabs: { key: ApprovalStatus; label: string }[] = [
    { key: "pending", label: "Pending" },
    { key: "approved", label: "Approved" },
    { key: "rejected", label: "Rejected" },
  ];

  return (
    <div className="border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 px-6 pt-3">
      <div className="flex items-center gap-8 text-sm">
        {tabs.map((tab) => {
          const isActive = activeTab === tab.key;
          const count = counts[tab.key] || 0;

          return (
            <button
              key={tab.key}
              onClick={() => onTabChange(tab.key)}
              className={`pb-3 flex items-center gap-2 font-medium transition-all cursor-pointer relative ${
                isActive
                  ? "text-[#0B85C9] dark:text-sky-400 font-semibold border-b-2 border-[#0B85C9] dark:border-sky-400 -mb-[1px]"
                  : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200"
              }`}
            >
              <span>{tab.label}</span>
              <span
                className={`px-2 py-0.5 text-xs font-semibold rounded-full ${
                  isActive
                    ? "bg-[#EBF5FF] text-[#0B85C9] dark:bg-sky-950/60 dark:text-sky-400 border border-sky-200 dark:border-sky-800"
                    : "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400"
                }`}
              >
                {count}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
