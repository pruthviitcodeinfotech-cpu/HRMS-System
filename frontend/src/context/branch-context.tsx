"use client";

import React, { createContext, useContext, useState, useEffect, useMemo } from "react";
import { useAuth } from "@/features/auth";
import { useBranchOptions } from "@/features/employees/hooks";
import { BranchOption } from "@/features/employees/types";

interface BranchContextType {
  selectedBranchId: number | null;
  selectedBranchName: string;
  availableBranches: BranchOption[];
  setSelectedBranchId: (id: number) => void;
  isLoading: boolean;
}

const BranchContext = createContext<BranchContextType | undefined>(undefined);

const LOCAL_STORAGE_KEY = "selected_branch_id";

export const BranchProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user } = useAuth();
  const { data: branchOptions = [], isLoading } = useBranchOptions();

  // Filter available branches according to user permissions
  const availableBranches = useMemo(() => {
    if (!user) return branchOptions;
    
    // SuperAdmin or TenantAdmin or user without specific branch restrictions has access to all branches
    const isSuperOrTenantAdmin =
      user.roles?.some((r) => r.toLowerCase().includes("admin")) ||
      !user.branchIds ||
      user.branchIds.length === 0;

    if (isSuperOrTenantAdmin) {
      return branchOptions;
    }

    return branchOptions.filter((branch) => user.branchIds.includes(branch.branch_id));
  }, [user, branchOptions]);

  // Initial branch ID state from URL or LocalStorage
  const [selectedBranchId, setSelectedBranchIdState] = useState<number | null>(() => {
    if (typeof window === "undefined") return null;
    
    // 1. Priority: URL query parameter
    const params = new URLSearchParams(window.location.search);
    const urlBranchId = params.get("branch_id");
    if (urlBranchId) {
      const parsed = parseInt(urlBranchId, 10);
      if (!isNaN(parsed) && parsed > 0) return parsed;
    }

    // 2. Local Storage
    const stored = localStorage.getItem(LOCAL_STORAGE_KEY);
    if (stored) {
      const parsed = parseInt(stored, 10);
      if (!isNaN(parsed) && parsed > 0) return parsed;
    }

    return null;
  });

  // Automatically select the first branch if unset or invalid when available branches are available
  useEffect(() => {
    if (availableBranches.length > 0) {
      const isValid = selectedBranchId !== null && availableBranches.some((b) => b.branch_id === selectedBranchId);
      if (!isValid) {
        const firstBranchId = availableBranches[0].branch_id;
        setSelectedBranchIdState(firstBranchId);
        localStorage.setItem(LOCAL_STORAGE_KEY, String(firstBranchId));

        if (typeof window !== "undefined") {
          const url = new URL(window.location.href);
          url.searchParams.set("branch_id", String(firstBranchId));
          window.history.replaceState({}, "", url.toString());
        }
      }
    }
  }, [availableBranches, selectedBranchId]);

  const setSelectedBranchId = (id: number) => {
    setSelectedBranchIdState(id);
    localStorage.setItem(LOCAL_STORAGE_KEY, String(id));

    // Update URL query parameter silently without page reload
    if (typeof window !== "undefined") {
      const url = new URL(window.location.href);
      url.searchParams.set("branch_id", String(id));
      window.history.replaceState({}, "", url.toString());

      // Dispatch custom event for forms/components requiring local resets
      window.dispatchEvent(new CustomEvent("branch-changed", { detail: { branchId: id } }));
    }

    // Immediately invalidate and refetch all branch-dependent React Query caches
    import("@/lib/query-client").then(({ queryClient }) => {
      queryClient.invalidateQueries();
    });
  };

  const selectedBranchName = useMemo(() => {
    if (selectedBranchId === null) {
      return availableBranches[0]?.branch_name || "Select Branch";
    }
    const found = availableBranches.find((b) => b.branch_id === selectedBranchId);
    if (found) return found.branch_name;
    const fallbackFound = branchOptions.find((b) => b.branch_id === selectedBranchId);
    return fallbackFound ? fallbackFound.branch_name : `Branch #${selectedBranchId}`;
  }, [selectedBranchId, availableBranches, branchOptions]);

  return (
    <BranchContext.Provider
      value={{
        selectedBranchId,
        selectedBranchName,
        availableBranches,
        setSelectedBranchId,
        isLoading,
      }}
    >
      {children}
    </BranchContext.Provider>
  );
};

export const useBranchContext = (): BranchContextType => {
  const context = useContext(BranchContext);
  if (!context) {
    throw new Error("useBranchContext must be used within a BranchProvider");
  }
  return context;
};
