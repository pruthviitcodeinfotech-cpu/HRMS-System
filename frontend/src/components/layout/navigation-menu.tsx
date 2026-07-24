"use client";

import { useState, useEffect, useMemo } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Users,
  Calendar,
  Palmtree,
  CheckSquare,
  CreditCard,
  FileBarChart,
  LineChart,
  UserCog,
  History,
  Settings,
  ChevronRight,
  Receipt,
} from "lucide-react";
import { usePermissions } from "@/features/auth";

interface NavigationMenuProps {
  sidebarOpen: boolean;
}

export const NavigationMenu = ({ sidebarOpen }: NavigationMenuProps) => {
  const pathname = usePathname();
  const { hasPermission } = usePermissions();

  // Expanded sub-menus tracking state
  const [expandedItems, setExpandedItems] = useState<Record<string, boolean>>({
    Employees: true, // Default open per the user request reference screenshot
    "Leaves & Holidays": true,
    Reports: true,
    Settlements: true,
    Payroll: true,
    "User Management": true,
  });

  const toggleExpand = (label: string) => {
    setExpandedItems((prev) => ({
      ...prev,
      [label]: !prev[label],
    }));
  };

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
      features: ["employee", "department", "designation", "branch", "attendance_punch"],
      items: [
        { href: "/employees", label: "Employees", permission: { feature: "employee", action: "read" } },
        { href: "/employees/departments", label: "Departments", permission: { feature: "department", action: "read" } },
        { href: "/employees/designations", label: "Designations", permission: { feature: "designation", action: "read" } },
        { href: "/employees/attendance-permission", label: "Attendance Permission", permission: { feature: "attendance_punch", action: "read" } },
        { href: "/employees/manage-branch", label: "Manage Branch", permission: { feature: "branch", action: "read" } },
      ],
    },
    {
      href: "/shifts",
      label: "Manage Shifts",
      icon: Calendar,
      hasChevron: true,
      isNew: false,
      permission: { feature: "shift", action: "read" },
      features: ["shift", "shift_assignment", "weekoff", "roster"],
      items: [
        { href: "/shifts", label: "Shifts", permission: { feature: "shift", action: "read" } },
        { href: "/shifts/assignments", label: "Shift Assignment", permission: { feature: "shift_assignment", action: "read" } },
        { href: "/shifts/week-off", label: "Week Off", permission: { feature: "weekoff", action: "read" } },
        { href: "/shifts/roster", label: "Roster", permission: { feature: "roster", action: "read" } },
      ],
    },
    {
      href: "/leaves",
      label: "Leaves & Holidays",
      icon: Palmtree,
      hasChevron: true,
      isNew: false,
      permission: { feature: "leave_request", action: "read" },
      features: ["leave_type", "leave_config", "leave_balance", "leave_request", "holiday"],
      items: [
        { href: "/leaves/create", label: "Leave Create", permission: { feature: "leave_request", action: "create" } },
        { href: "/leaves/assign", label: "Leave Assign", permission: { feature: "leave_type", action: "read" } },
        { href: "/leaves/balance", label: "Leave Balance", permission: { feature: "leave_balance", action: "read" } },
        { href: "/leaves/holidays/create", label: "Holiday Create", permission: { feature: "holiday", action: "create" } },
        { href: "/leaves/holidays/assign", label: "Holiday Assign", permission: { feature: "holiday", action: "edit" } },
      ],
    },
    {
      href: "/approvals",
      label: "Approval Requests",
      icon: CheckSquare,
      hasChevron: false,
      isNew: false,
      permission: { feature: "approval", action: "read" },
    },
    {
      href: "/payroll",
      label: "Payroll",
      icon: CreditCard,
      hasChevron: true,
      isNew: true,
      permission: { feature: "payroll_processing", action: "read" },
      features: ["payroll_config", "payroll_group", "payroll_cycle", "payroll_processing", "payroll_record", "payroll_adjustment"],
      items: [
        { href: "/payroll/bulk-attendance-adjustments", label: "Bulk Attendance Adjustments", permission: { feature: "payroll_adjustment", action: "read" } },
        { href: "/payroll/process-payroll", label: "Process Payroll", isNew: true, permission: { feature: "payroll_processing", action: "read" } },
        { href: "/payroll/payroll-group", label: "Payroll Group", permission: { feature: "payroll_group", action: "read" } },
        { href: "/payroll/assign-payroll-group", label: "Assign Payroll Group", permission: { feature: "payroll_group", action: "edit" } },
        { href: "/payroll/finalized-payroll-details", label: "Finalized Payroll Details", permission: { feature: "payroll_record", action: "read" } },
      ],
    },
    {
      href: "/settlements",
      label: "Settlements",
      icon: Receipt,
      hasChevron: true,
      isNew: true,
      permission: { feature: "settlement", action: "read" },
      features: ["settlement", "loan_advance", "arrears"],
      items: [
        { href: "/settlements/loan-advance", label: "Loan & Advance", isNew: true, permission: { feature: "loan_advance", action: "read" } },
        { href: "/settlements/arrears", label: "Arrears", isNew: true, permission: { feature: "arrears", action: "read" } },
      ],
    },
    {
      href: "/reports",
      label: "Reports",
      icon: FileBarChart,
      hasChevron: true,
      isNew: false,
      permission: { feature: "reports", action: "read" },
      features: ["reports", "attendance"],
      items: [
        { href: "/reports/attendance-master", label: "Attendance Master", permission: { feature: "reports", action: "read" } },
        { href: "/reports/shift-wise", label: "Shift Wise Report", permission: { feature: "reports", action: "read" } },
        { href: "/reports/daily-punch", label: "Daily Punch Report", permission: { feature: "reports", action: "read" } },
        { href: "/reports/working-hours", label: "Working Hours Report", permission: { feature: "reports", action: "read" } },
        { href: "/reports/muster", label: "Muster Report", permission: { feature: "reports", action: "read" } },
        { href: "/reports/branch-wise-punch", label: "Branch Wise Punch Report", permission: { feature: "reports", action: "read" } },
        { href: "/reports/leave-taken", label: "Leave Taken Report", permission: { feature: "reports", action: "read" } },
        { href: "/reports/employee-day-wise-master", label: "Employee Day Wise Master", permission: { feature: "reports", action: "read" } },
      ],
    },
    {
      href: "/dynamic-reports",
      label: "Dynamic Reports",
      icon: LineChart,
      hasChevron: false,
      isNew: false,
      permission: { feature: "reports", action: "read" },
    },
    {
      href: "/users",
      label: "User Management",
      icon: UserCog,
      hasChevron: true,
      isNew: false,
      permission: { feature: "user_management", action: "read" },
      features: ["user_management", "role_management", "access_management"],
      items: [
        { href: "/allTemplates", label: "Rights Templates", permission: { feature: "role_management", action: "read" } },
        { href: "/users", label: "Manage Users", permission: { feature: "user_management", action: "read" } },
      ],
    },
    {
      href: "/activity-logs",
      label: "Activity Logs",
      icon: History,
      hasChevron: false,
      isNew: false,
      permission: { feature: "audit", action: "read" },
    },
    {
      href: "/settings",
      label: "Settings",
      icon: Settings,
      hasChevron: false,
      isNew: false,
      permission: { feature: "settings", action: "read" },
    },
  ];

  // Auto-expand hierarchy when path matches any of the children
  useEffect(() => {
    navItems.forEach((item) => {
      if ("items" in item && Array.isArray(item.items)) {
        const hasActiveChild = item.items.some((child: any) => pathname === child.href);
        if (hasActiveChild) {
          setExpandedItems((prev) => ({
            ...prev,
            [item.label]: true,
          }));
        }
      }
    });
  }, [pathname]);

  const filteredItems = useMemo(() => {
    return navItems
      .map((item) => {
        try {
          const hasParentPerm =
            "features" in item && Array.isArray((item as any).features)
              ? (item as any).features.some((f: string) => hasPermission(f, "read"))
              : hasPermission(item.permission.feature, item.permission.action as any);

          if (!hasParentPerm) {
            return null;
          }

          if ("items" in item && Array.isArray((item as any).items)) {
            const visibleSubItems = (item as any).items.filter((subItem: any) => {
              if (subItem.permission) {
                return hasPermission(subItem.permission.feature, subItem.permission.action);
              }
              return true;
            });

            if (visibleSubItems.length === 0) {
              return null;
            }

            return {
              ...item,
              items: visibleSubItems,
            };
          }

          return item;
        } catch {
          return item;
        }
      })
      .filter((item): item is NonNullable<typeof item> => item !== null);
  }, [hasPermission]);

  return (
    <nav className="p-2 space-y-1 mt-1">
      {filteredItems.map((item: any) => {
        const Icon = item.icon;
        const hasChildren = "items" in item && Array.isArray(item.items);

        // Parent is active if current path starts with parent href OR matches any child href
        const isParentActive = hasChildren
          ? pathname.startsWith(item.href) || item.items.some((child: any) => pathname === child.href)
          : pathname.startsWith(item.href) || (item.href === "/dashboard" && pathname === "/");

        const isExpanded = expandedItems[item.label] ?? false;

        return (
          <div key={item.href} className="space-y-1">
            {/* MenuItem Wrapper (Button for expandables, Link for flat links) */}
            {hasChildren ? (
              <button
                onClick={() => toggleExpand(item.label)}
                className={`w-full flex items-center justify-between rounded-lg transition-all duration-200 cursor-pointer ${
                  sidebarOpen ? "px-3 py-2 text-xs font-semibold" : "p-2.5 justify-center"
                } ${
                  isParentActive
                    ? "bg-blue-600 text-white shadow-xs"
                    : "text-slate-600 dark:text-slate-300 hover:text-slate-800 dark:hover:text-slate-100 hover:bg-slate-50 dark:hover:bg-slate-800"
                }`}
                title={item.label}
              >
                <div className="flex items-center space-x-3 min-w-0">
                  <Icon
                    className={`h-4.5 w-4.5 shrink-0 ${isParentActive ? "text-white" : "text-slate-500 dark:text-slate-400"}`}
                  />
                  {sidebarOpen && <span className="truncate">{item.label}</span>}
                </div>

                {sidebarOpen && (
                  <div className="flex items-center space-x-1.5 shrink-0">
                    {item.isNew && (
                      <span className="px-1.5 py-0.5 rounded text-[8px] font-bold uppercase tracking-wider bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 border border-blue-100 dark:border-blue-900/50">
                        New
                      </span>
                    )}
                    <ChevronRight
                      className={`h-3.5 w-3.5 transition-transform duration-200 ${
                        isParentActive ? "text-white" : "text-slate-400 dark:text-slate-500"
                      } ${isExpanded ? "rotate-90" : ""}`}
                    />
                  </div>
                )}
              </button>
            ) : (
              <Link
                href={item.href}
                className={`flex items-center justify-between rounded-lg transition-all duration-200 cursor-pointer ${
                  sidebarOpen ? "px-3 py-2 text-xs font-semibold" : "p-2.5 justify-center"
                } ${
                  isParentActive
                    ? "bg-blue-600 text-white shadow-xs"
                    : "text-slate-600 dark:text-slate-300 hover:text-slate-800 dark:hover:text-slate-100 hover:bg-slate-50 dark:hover:bg-slate-800"
                }`}
                title={item.label}
              >
                <div className="flex items-center space-x-3 min-w-0">
                  <Icon
                    className={`h-4.5 w-4.5 shrink-0 ${isParentActive ? "text-white" : "text-slate-500 dark:text-slate-400"}`}
                  />
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
                      <ChevronRight
                        className={`h-3 w-3 ${isParentActive ? "text-white" : "text-slate-400 dark:text-slate-500"}`}
                      />
                    )}
                  </div>
                )}
              </Link>
            )}

            {/* Collapsible Hierarchy Thread Sub-Links */}
            {hasChildren && isExpanded && sidebarOpen && (
              <div className="pl-4 ml-4.5 border-l border-slate-200 dark:border-slate-800 flex flex-col space-y-1 py-1">
                {item.items.map((subItem: any) => {
                  const isSubActive = pathname === subItem.href;
                  const isSubNew = "isNew" in subItem && subItem.isNew;
                  return (
                    <Link
                      key={subItem.href}
                      href={subItem.href}
                      className={`flex items-center justify-between py-1.5 px-3 text-xs font-semibold rounded-md transition-all duration-150 cursor-pointer ${
                        isSubActive
                          ? "text-blue-600 dark:text-blue-400 font-bold bg-blue-50/40 dark:bg-blue-950/10"
                          : "text-slate-600 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-100 hover:bg-slate-50 dark:hover:bg-slate-800/40"
                      }`}
                    >
                      <span className="truncate">{subItem.label}</span>
                      {isSubNew && (
                        <span className="px-1.5 py-0.5 rounded text-[8px] font-bold uppercase tracking-wider bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 border border-blue-100 dark:border-blue-900/50 shrink-0 ml-2">
                          New
                        </span>
                      )}
                    </Link>
                  );
                })}
              </div>
            )}
          </div>
        );
      })}
    </nav>
  );
};
