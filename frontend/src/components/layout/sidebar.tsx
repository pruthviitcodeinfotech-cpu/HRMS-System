"use client";

import { useSidebarStore } from "@/lib/stores/sidebar-store";
import { NavigationMenu } from "./navigation-menu";
import { HelpCircle, MessageSquare, ExternalLink } from "lucide-react";

export const Sidebar = () => {
  const { isOpen } = useSidebarStore();

  return (
    <aside
      className={`h-full border-r border-border bg-card flex flex-col justify-between transition-all duration-300 ease-in-out shrink-0 z-10 ${
        isOpen ? "w-64" : "w-16"
      }`}
    >
      <div className="flex-1 flex flex-col overflow-y-auto">
        {/* Navigation Menu */}
        <NavigationMenu sidebarOpen={isOpen} />
      </div>

      {/* Bottom Actions matching Petpooja style */}
      <div className="p-3 border-t border-border flex flex-col space-y-2 bg-slate-50/20 dark:bg-slate-900/10 select-none">
        {/* Call support */}
        <div
          className={`flex items-center text-slate-500 dark:text-slate-400 rounded-lg transition-all ${
            isOpen ? "px-2 py-1.5 space-x-2 text-[10px]" : "p-2.5 justify-center"
          }`}
          title="Call Support: 07969223344"
        >
          <HelpCircle className="h-4.5 w-4.5 shrink-0 text-slate-400 dark:text-slate-500" />
          {isOpen && (
            <span className="truncate font-medium">
              Call Us On:{" "}
              <a
                href="tel:07969223344"
                className="text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 underline font-bold cursor-pointer"
              >
                07969223344
              </a>
            </span>
          )}
        </div>

        {/* WhatsApp support */}
        <a
          href="https://wa.me/07969223344"
          target="_blank"
          rel="noopener noreferrer"
          className={`flex items-center text-slate-500 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800/80 rounded-lg transition-all cursor-pointer ${
            isOpen ? "px-2 py-1.5 space-x-2 text-[10px]" : "p-2.5 justify-center"
          }`}
          title="Contact on Whatsapp"
        >
          <MessageSquare className="h-4.5 w-4.5 shrink-0 text-emerald-500 fill-emerald-50/50 dark:fill-emerald-950/20" />
          {isOpen && (
            <div className="flex items-center space-x-1.5 min-w-0">
              <span className="font-medium text-slate-600 dark:text-slate-300 truncate">Contact on Whatsapp</span>
              <ExternalLink className="h-2.5 w-2.5 text-blue-500 dark:text-blue-400 shrink-0" />
            </div>
          )}
        </a>
      </div>
    </aside>
  );
};
