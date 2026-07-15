"use client";

import { useSidebarStore } from "@/lib/stores/sidebar-store";
import { useThemeStore } from "@/lib/stores/theme-store";
import { Menu, Bell, ChevronDown, User, ShieldCheck, Sun, Moon } from "lucide-react";
import { useAuth } from "@/features/auth/hooks";

export const Header = () => {
  const { toggle } = useSidebarStore();
  const { theme, toggleTheme } = useThemeStore();
  const { user } = useAuth();

  return (
    <header className="h-16 border-b border-border bg-card text-card-foreground flex items-center justify-between px-6 shrink-0 z-10 shadow-xs transition-colors duration-250">
      {/* Left side: Hamburger, Logo & Org Selector */}
      <div className="flex items-center space-x-6">
        {/* Toggle Sidebar Button */}
        <button
          onClick={toggle}
          className="p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-100 transition-colors cursor-pointer"
          aria-label="Toggle Sidebar"
        >
          <Menu className="h-5 w-5" />
        </button>

        {/* Logo Section */}
        <div className="flex items-center space-x-2">
          <div className="h-8 w-8 rounded-full bg-blue-600 flex items-center justify-center text-white shadow-sm">
            <ShieldCheck className="h-5 w-5" />
          </div>
          <div className="flex flex-col">
            <span className="font-extrabold text-sm tracking-tight text-slate-800 dark:text-slate-100 uppercase leading-none">
              HRMS
            </span>
            <span className="font-semibold text-[10px] tracking-wider text-blue-600 dark:text-blue-400 uppercase leading-none mt-0.5">
              System
            </span>
          </div>
        </div>

        {/* Vertical Divider */}
        <div className="h-6 w-px bg-border hidden md:block" />

        {/* Organization Selector */}
        <div className="relative hidden md:block">
          <button className="flex items-center space-x-2 px-3 py-1.5 border border-border rounded-md bg-slate-50/50 dark:bg-slate-800/40 hover:bg-slate-50 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300 text-xs font-medium transition-all shadow-sm hover:border-slate-300 dark:hover:border-slate-700 cursor-pointer">
            <span>Itcode Infotech (116478)</span>
            <ChevronDown className="h-3 w-3 text-slate-400" />
          </button>
        </div>
      </div>

      {/* Right side: Theme, Notifications & Profile */}
      <div className="flex items-center space-x-3">
        {/* Theme Toggle Option */}
        <button
          onClick={toggleTheme}
          className="p-2 rounded-full hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-100 transition-colors cursor-pointer"
          aria-label="Toggle Theme"
          title={`Switch to ${theme === "light" ? "dark" : "light"} mode`}
        >
          {theme === "light" ? (
            <Moon className="h-5 w-5" />
          ) : (
            <Sun className="h-5 w-5 text-amber-500 fill-amber-50" />
          )}
        </button>

        {/* Notifications Bell */}
        <button
          className="p-2 rounded-full hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-100 transition-colors cursor-pointer relative"
          aria-label="Notifications"
        >
          <Bell className="h-5 w-5" />
          <span className="absolute top-1.5 right-1.5 h-2 w-2 bg-rose-500 rounded-full ring-2 ring-white" />
        </button>

        {/* Divider */}
        <div className="h-6 w-px bg-border" />

        {/* User Profile Section */}
        <button className="flex items-center space-x-2.5 py-1.5 px-2 hover:bg-slate-50 dark:hover:bg-slate-800 rounded-lg transition-colors cursor-pointer text-left">
          <div className="h-8 w-8 rounded-full bg-slate-200 dark:bg-slate-800 text-slate-600 dark:text-slate-300 flex items-center justify-center font-bold text-sm shadow-inner border border-border">
            <User className="h-4.5 w-4.5" />
          </div>
          <div className="hidden sm:block">
            <p className="text-xs font-semibold text-slate-700 dark:text-slate-300">
              {user ? user.email.split("@")[0] : "Balkrushn koladiya"}
            </p>
            <p className="text-[9px] text-slate-400 dark:text-slate-500 capitalize font-medium leading-none mt-0.5">
              {user?.roles[0] || "Admin"}
            </p>
          </div>
          <ChevronDown className="h-3 w-3 text-slate-400" />
        </button>
      </div>
    </header>
  );
};
