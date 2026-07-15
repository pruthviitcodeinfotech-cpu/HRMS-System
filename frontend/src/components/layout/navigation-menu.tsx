"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Users,
  Calendar,
  Trees,
  CheckSquare,
  CreditCard,
  Briefcase,
  FileBarChart,
  LineChart,
  UserCog,
  History,
  Settings,
  ChevronRight,
} from "lucide-react";
import { usePermissions } from "@/features/auth";

interface NavigationMenuProps {
  sidebarOpen: boolean;
}

export const NavigationMenu = ({ sidebarOpen }: NavigationMenuProps) => {
  const pathname = usePathname();
  const { hasPermission } = usePermissions();

  const navItems = [
    {
      href: "/dashboard",
      label: "Dashboard",
      icon: LayoutDashboard,
      hasChevron: false,
      isNew: false,
      permission: { feature: "dashboard", action: "read" },
    },
    {
      href: "/employees",
      label: "Employees",
      icon: Users,
      hasChevron: true,
      isNew: false,
      permission: { feature: "employee", action: "read" },
    },
    {
      href: "/shifts",
      label: "Manage Shifts",
      icon: Calendar,
      hasChevron: true,
      isNew: false,
      permission: { feature: "shift", action: "read" },
    },
    {
      href: "/leaves",
      label: "Leaves & Holidays",
      icon: Trees,
      hasChevron: true,
      isNew: false,
      permission: { feature: "leave_request", action: "read" },
    },
    {
      href: "/approvals",
      label: "Approval Requests",
      icon: CheckSquare,
      hasChevron: false,
      isNew: false,
      permission: { feature: "approvals", action: "read" },
    },
    {
      href: "/payroll",
      label: "Payroll",
      icon: CreditCard,
      hasChevron: true,
      isNew: true,
      permission: { feature: "payroll_processing", action: "read" },
    },
    {
      href: "/settlements",
      label: "Settlements",
      icon: Briefcase,
      hasChevron: true,
      isNew: true,
      permission: { feature: "settlements", action: "read" },
    },
    {
      href: "/reports",
      label: "Reports",
      icon: FileBarChart,
      hasChevron: true,
      isNew: false,
      permission: { feature: "reports", action: "read" },
    },
    {
      href: "/dynamic-reports",
      label: "Dynamic Reports",
      icon: LineChart,
      hasChevron: false,
      isNew: false,
      permission: { feature: "dynamic_reports", action: "read" },
    },
    {
      href: "/users",
      label: "User Management",
      icon: UserCog,
      hasChevron: true,
      isNew: false,
      permission: { feature: "user_management", action: "read" },
    },
    {
      href: "/activity-logs",
      label: "Activity Logs",
      icon: History,
      hasChevron: false,
      isNew: false,
      permission: { feature: "activity_logs", action: "read" },
    },
    {
      href: "/settings",
      label: "Settings",
      icon: Settings,
      hasChevron: false,
      isNew: false,
      permission: { feature: "settings", action: "read" },
    },
  ] as const;

  const filteredItems = navItems.filter((item) => {
    try {
      return hasPermission(item.permission.feature, item.permission.action);
    } catch {
      return true;
    }
  });

  return (
    <nav className="p-2 space-y-1 mt-1">
      {filteredItems.map((item) => {
        const Icon = item.icon;
        const isActive = pathname.startsWith(item.href) || (item.href === "/dashboard" && pathname === "/");

        return (
          <Link
            key={item.href}
            href={item.href}
            className={`flex items-center justify-between rounded-lg transition-all duration-200 cursor-pointer ${
              sidebarOpen
                ? "px-3 py-2 text-xs font-semibold"
                : "p-2.5 justify-center"
            } ${
              isActive
                ? "bg-blue-600 text-white shadow-xs"
                : "text-slate-600 dark:text-slate-300 hover:text-slate-800 dark:hover:text-slate-100 hover:bg-slate-50 dark:hover:bg-slate-800"
            }`}
            title={item.label}
          >
            <div className="flex items-center space-x-3 min-w-0">
              <Icon className={`h-4.5 w-4.5 shrink-0 ${isActive ? "text-white" : "text-slate-500 dark:text-slate-400"}`} />
              {sidebarOpen && <span className="truncate">{item.label}</span>}
            </div>

            {sidebarOpen && (
              <div className="flex items-center space-x-1.5 shrink-0">
                {item.isNew && (
                  <span className="px-1.5 py-0.5 rounded text-[8px] font-bold uppercase tracking-wider bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 border border-blue-100 dark:border-blue-900/50">
                    New
                  </span>
                )}
                {item.hasChevron && (
                  <ChevronRight className={`h-3 w-3 ${isActive ? "text-white" : "text-slate-400 dark:text-slate-500"}`} />
                )}
              </div>
            )}
          </Link>
        );
      })}
    </nav>
  );
};
