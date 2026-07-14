"use client";

import { useSidebarStore } from "@/lib/stores/sidebar-store";
import { useUIStore } from "@/lib/stores/ui-store";
import { Menu, Bell, User } from "lucide-react";
import { useAuth } from "@/features/auth/hooks";

export const Header = () => {
  const { isOpen, toggle } = useSidebarStore();
  const pageTitle = useUIStore((state) => state.pageTitle);
  const { user } = useAuth();

  return (
    <header className="h-16 border-b border-border bg-card flex items-center justify-between px-6 shrink-0">
      <div className="flex items-center gap-4">
        {!isOpen && (
          <button
            onClick={toggle}
            className="p-1.5 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
            aria-label="Expand Sidebar"
          >
            <Menu className="h-5 w-5" />
          </button>
        )}
        <h2 className="font-bold text-lg tracking-tight text-foreground">{pageTitle}</h2>
      </div>

      <div className="flex items-center space-x-4">
        <button
          className="p-1.5 rounded-full hover:bg-muted text-muted-foreground hover:text-foreground transition-colors cursor-pointer relative"
          aria-label="Notifications"
        >
          <Bell className="h-5 w-5" />
          <span className="absolute top-1 right-1 h-2.5 w-2.5 bg-destructive rounded-full border border-card" />
        </button>

        <div className="flex items-center gap-2 pl-2 border-l border-border">
          <div className="h-8 w-8 rounded-full bg-primary/10 text-primary flex items-center justify-center">
            <User className="h-4.5 w-4.5" />
          </div>
          {user && (
            <div className="hidden md:block text-left">
              <p className="text-xs font-semibold leading-tight text-foreground">
                {user.email.split("@")[0]}
              </p>
              <p className="text-[10px] text-muted-foreground capitalize leading-none mt-0.5">
                {user.roles[0] || "User"}
              </p>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
