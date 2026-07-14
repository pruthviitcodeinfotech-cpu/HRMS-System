"use client";

import React from "react";
import { ProtectedRoute } from "@/features/auth";
import { Sidebar } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";
import { Footer } from "@/components/layout/footer";
import { Breadcrumb } from "@/components/layout/breadcrumb";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <ProtectedRoute>
      <div className="flex h-screen w-screen overflow-hidden bg-background text-foreground font-sans">
        {/* Sidebar */}
        <Sidebar />

        {/* Workspace content */}
        <div className="flex-1 flex flex-col h-full overflow-hidden">
          {/* Header */}
          <Header />

          {/* Scrolling view */}
          <div className="flex-1 overflow-y-auto p-6 flex flex-col justify-between">
            <div>
              <Breadcrumb />
              <main className="w-full">{children}</main>
            </div>
            <Footer />
          </div>
        </div>
      </div>
    </ProtectedRoute>
  );
}
