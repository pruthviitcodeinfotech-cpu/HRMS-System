"use client";

import { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { useSidebarStore } from "@/lib/stores/sidebar-store";
import { useThemeStore } from "@/lib/stores/theme-store";
import { Menu, ChevronDown, User, ShieldCheck, Sun, Moon, LogOut, Building2, Check } from "lucide-react";
import { useAuth } from "@/features/auth/hooks";
import { useBranchContext } from "@/context/branch-context";
import { NotificationDropdown } from "@/features/notifications/components/notification-dropdown";

export const Header = () => {
  const { toggle } = useSidebarStore();
  const { theme, toggleTheme } = useThemeStore();
  const { user, logout } = useAuth();
  const { selectedBranchId, selectedBranchName, availableBranches, setSelectedBranchId } = useBranchContext();

  const [isProfileOpen, setIsProfileOpen] = useState(false);
  const [isBranchOpen, setIsBranchOpen] = useState(false);

  const dropdownRef = useRef<HTMLDivElement>(null);
  const branchDropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsProfileOpen(false);
      }
      if (branchDropdownRef.current && !branchDropdownRef.current.contains(event.target as Node)) {
        setIsBranchOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleLogout = async () => {
    try {
      await logout();
    } catch (error) {
      console.error("Logout failed:", error);
    }
  };

  return (
    <header className="h-16 border-b border-border bg-card text-card-foreground flex items-center justify-between px-6 shrink-0 z-40 shadow-xs transition-colors duration-250">
      {/* Left side: Hamburger, Logo & Org/Branch Selector */}
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

        {/* Branch Selector */}
        <div className="relative hidden md:block" ref={branchDropdownRef}>
          <button
            onClick={() => setIsBranchOpen(!isBranchOpen)}
            className="flex items-center space-x-2 px-3 py-1.5 border border-border rounded-md bg-slate-50/50 dark:bg-slate-800/40 hover:bg-slate-50 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300 text-xs font-medium transition-all shadow-sm hover:border-slate-300 dark:hover:border-slate-700 cursor-pointer"
          >
            <Building2 className="h-3.5 w-3.5 text-blue-600 dark:text-blue-400" />
            <span className="font-semibold">{selectedBranchName}</span>
            <ChevronDown className={`h-3 w-3 text-slate-400 transition-transform duration-200 ${isBranchOpen ? "rotate-180" : ""}`} />
          </button>

          {isBranchOpen && (
            <div className="absolute left-0 mt-2 w-64 rounded-xl border border-border bg-card dark:bg-slate-900 text-card-foreground shadow-2xl py-1.5 z-50 animate-in fade-in slide-in-from-top-2 duration-150 origin-top-left dark:border-slate-800 ring-1 ring-black/5 dark:ring-white/10">
              <div className="px-3 py-1.5 border-b border-border dark:border-slate-800 mb-1">
                <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400 dark:text-slate-400">
                  Select Branch
                </p>
              </div>

              <div className="max-h-60 overflow-y-auto py-1">
                {availableBranches.map((branch) => {
                  const isSelected = selectedBranchId === branch.branch_id;
                  return (
                    <button
                      key={branch.branch_id}
                      onClick={() => {
                        setSelectedBranchId(branch.branch_id);
                        setIsBranchOpen(false);
                      }}
                      className={`w-full flex items-center justify-between px-3 py-2 text-xs font-medium transition-colors hover:bg-slate-100 dark:hover:bg-slate-800/80 cursor-pointer ${
                        isSelected ? "text-blue-600 dark:text-blue-400 font-bold bg-blue-50/50 dark:bg-blue-950/40" : "text-slate-700 dark:text-slate-300"
                      }`}
                    >
                      <span className="truncate">{branch.branch_name}</span>
                      {isSelected && <Check className="h-4 w-4 text-blue-600 dark:text-blue-400 shrink-0 ml-2" />}
                    </button>
                  );
                })}
              </div>
            </div>
          )}
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

        {/* Notifications Bell Dropdown */}
        <NotificationDropdown />

        {/* Divider */}
        <div className="h-6 w-px bg-border" />

        {/* User Profile Section */}
        <div className="relative" ref={dropdownRef}>
          <button
            onClick={() => setIsProfileOpen(!isProfileOpen)}
            className="flex items-center space-x-2.5 py-1.5 px-2 hover:bg-slate-50 dark:hover:bg-slate-800 rounded-lg transition-colors cursor-pointer text-left"
          >
            <div className="h-8 w-8 rounded-full bg-slate-200 dark:bg-slate-800 text-slate-600 dark:text-slate-300 flex items-center justify-center font-bold text-sm shadow-inner border border-border">
              <User className="h-4.5 w-4.5" />
            </div>
            <div className="hidden sm:block">
              <p className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                {user ? user.email.split("@")[0] : "User"}
              </p>
              <p className="text-[9px] text-slate-400 dark:text-slate-500 capitalize font-medium leading-none mt-0.5">
                {user?.roles[0] || "Admin"}
              </p>
            </div>
            <ChevronDown className={`h-3 w-3 text-slate-400 transition-transform duration-200 ${isProfileOpen ? "rotate-180" : ""}`} />
          </button>

          {isProfileOpen && (
            <div className="absolute right-0 mt-2 w-56 rounded-xl border border-border bg-card text-card-foreground shadow-lg py-1.5 z-50 animate-in fade-in slide-in-from-top-2 duration-150 origin-top-right">
              <div className="px-4 py-2 border-b border-border">
                <p className="text-xs font-semibold text-slate-800 dark:text-slate-200 truncate">
                  {user ? user.email.split("@")[0] : "User"}
                </p>
                <p className="text-[10px] text-slate-400 dark:text-slate-500 truncate mt-0.5">
                  {user?.email || "admin@itcode.com"}
                </p>
              </div>
              
              <div className="py-1">
                <Link
                  href="/profile"
                  onClick={() => setIsProfileOpen(false)}
                  className="w-full flex items-center space-x-2.5 px-4 py-2.5 text-xs text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors text-left font-medium cursor-pointer"
                >
                  <User className="h-4 w-4" />
                  <span>User Profile</span>
                </Link>
                <button
                  onClick={handleLogout}
                  className="w-full flex items-center space-x-2.5 px-4 py-2.5 text-xs text-rose-600 dark:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-950/30 transition-colors text-left font-medium cursor-pointer"
                >
                  <LogOut className="h-4 w-4" />
                  <span>Log Out</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
