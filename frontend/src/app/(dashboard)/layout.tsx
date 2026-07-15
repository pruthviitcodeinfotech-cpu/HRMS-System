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
      <div className="flex flex-col h-screen w-screen overflow-hidden bg-background text-foreground font-sans">
        {/* Top Header */}
        <Header />

        {/* Lower workspace: Sidebar + Content */}
        <div className="flex flex-1 overflow-hidden">
          {/* Sidebar */}
          <Sidebar />

          {/* Scrolling view */}
          <div className="flex-1 overflow-y-auto bg-background p-6 flex flex-col justify-between transition-colors duration-250">
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
