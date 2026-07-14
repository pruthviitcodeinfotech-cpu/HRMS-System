"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, Users, Calendar, Clock, Trees, CreditCard, Settings } from "lucide-react";

interface NavigationMenuProps {
  sidebarOpen: boolean;
}

export const NavigationMenu = ({ sidebarOpen }: NavigationMenuProps) => {
  const pathname = usePathname();

  const navItems = [
    { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
    { href: "/employees", label: "Employees", icon: Users },
    { href: "/shifts", label: "Shifts", icon: Calendar },
    { href: "/attendance", label: "Attendance", icon: Clock },
    { href: "/leaves", label: "Leaves", icon: Trees },
    { href: "/payroll", label: "Payroll", icon: CreditCard },
    { href: "/settings", label: "Settings", icon: Settings },
  ];

  return (
    <nav className="p-3 space-y-1">
      {navItems.map((item) => {
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
