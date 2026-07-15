"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, Users, Calendar, Clock, Trees, CreditCard, Settings } from "lucide-react";
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
      permission: { feature: "dashboard", action: "read" },
    },
    {
      href: "/employees",
      label: "Employees",
      icon: Users,
      permission: { feature: "employee", action: "read" },
    },
    {
      href: "/shifts",
      label: "Shifts",
      icon: Calendar,
      permission: { feature: "shift", action: "read" },
    },
    {
      href: "/attendance",
      label: "Attendance",
      icon: Clock,
      permission: { feature: "attendance", action: "read" },
    },
    {
      href: "/leaves",
      label: "Leaves",
      icon: Trees,
      permission: { feature: "leave_request", action: "read" },
    },
    {
      href: "/payroll",
      label: "Payroll",
      icon: CreditCard,
      permission: { feature: "payroll_processing", action: "read" },
    },
    {
      href: "/settings",
      label: "Settings",
      icon: Settings,
      permission: { feature: "settings", action: "read" },
    },
  ] as const;

  const filteredItems = navItems.filter((item) => {
    return hasPermission(item.permission.feature, item.permission.action);
  });

  return (
    <nav className="p-3 space-y-1">
      {filteredItems.map((item) => {
        const Icon = item.icon;
        const isActive = pathname.startsWith(item.href);

        return (
          <Link
            key={item.href}
            href={item.href}
            className={`flex items-center space-x-3 p-2.5 rounded-lg text-sm font-medium transition-colors ${
              isActive
                ? "bg-primary text-primary-foreground font-semibold"
                : "text-muted-foreground hover:bg-muted hover:text-foreground"
            }`}
          >
            <Icon className="h-4.5 w-4.5 shrink-0" />
            {sidebarOpen && <span className="truncate">{item.label}</span>}
          </Link>
        );
      })}
    </nav>
  );
};
