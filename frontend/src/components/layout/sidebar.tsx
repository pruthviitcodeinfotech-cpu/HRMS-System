"use client";

import { useSidebarStore } from "@/lib/stores/sidebar-store";
import { useThemeStore } from "@/lib/stores/theme-store";
import { NavigationMenu } from "./navigation-menu";
import { Menu, LogOut, Sun, Moon } from "lucide-react";
import { useAuth } from "@/features/auth/hooks";

export const Sidebar = () => {
  const { isOpen, toggle } = useSidebarStore();
  const { theme, toggleTheme } = useThemeStore();
  const { logout, user } = useAuth();

  return (
    <aside
      className={`h-screen border-r border-border bg-card flex flex-col justify-between transition-all duration-300 ease-in-out shrink-0 ${
        isOpen ? "w-64" : "w-18"
      }`}
    >
      <div>
        {/* Top Header Logo */}
        <div className="h-16 flex items-center justify-between px-4 border-b border-border">
          {isOpen && (
            <div className="flex items-center space-x-2">
              <div className="h-7 w-7 rounded-md bg-primary flex items-center justify-center text-primary-foreground font-extrabold text-sm">
                H
              </div>
              <span className="font-bold text-base tracking-tight text-foreground">
                HRMS System
              </span>
            </div>
          )}
          {!isOpen && (
            <div className="h-7 w-7 rounded-md bg-primary flex items-center justify-center text-primary-foreground font-extrabold text-sm mx-auto">
              H
            </div>
          )}
          {isOpen && (
            <button
              onClick={toggle}
              className="p-1.5 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
              aria-label="Collapse Sidebar"
            >
              <Menu className="h-5 w-5" />
            </button>
          )}
        </div>

        {/* Navigation Section */}
        <NavigationMenu sidebarOpen={isOpen} />
      </div>

      {/* Footer controls & Profile */}
      <div className="p-3 border-t border-border space-y-2">
        {isOpen && user && (
          <div className="px-2 py-1.5 rounded-lg bg-muted/50 mb-2">
            <p className="text-xs font-semibold text-foreground truncate">{user.email}</p>
            <p className="text-[10px] text-muted-foreground truncate">{user.roles.join(", ")}</p>
          </div>
        )}

        <div className="flex items-center gap-1">
          <button
            onClick={toggleTheme}
            className="flex-1 flex items-center justify-center gap-2 p-2 rounded-lg border border-border hover:bg-muted text-xs font-semibold text-foreground transition-colors cursor-pointer"
            title="Toggle theme"
          >
            {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            {isOpen && <span>Theme</span>}
          </button>

          <button
            onClick={() => {
              void logout();
            }}
            className="flex items-center justify-center p-2 rounded-lg border border-destructive/20 hover:bg-destructive/10 text-destructive transition-colors cursor-pointer"
            title="Sign out"
          >
            <LogOut className="h-4 w-4" />
          </button>
        </div>
      </div>
    </aside>
  );
};
