"use client";

import React from "react";
import { QueryClientProvider } from "@tanstack/react-query";
import { queryClient } from "@/lib/query-client";
import { ThemeProvider } from "@/providers/theme-provider";
import { LoadingProvider } from "@/providers/loading-provider";
import { AuthProvider } from "@/features/auth";
import { BranchProvider } from "@/context/branch-context";
import { Toaster } from "sonner";

export default function Providers({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <LoadingProvider>
          <AuthProvider>
            <BranchProvider>
              {children}
              <Toaster position="bottom-right" richColors closeButton />
            </BranchProvider>
          </AuthProvider>
        </LoadingProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}
