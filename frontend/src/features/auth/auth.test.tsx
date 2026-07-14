import React from "react";
import { render, screen } from "@testing-library/react";
import { AuthContext } from "./context";
import { usePermission } from "./hooks";
import { PermissionGuard } from "./components/permission-guard";
import { expect, test, describe } from "vitest";

// Mock component to check usePermission hook output
const PermissionTester = ({
  feature,
  action,
}: {
  feature: string;
  action: "create" | "read" | "edit" | "delete";
}) => {
  const hasPermission = usePermission(feature, action);
  return <div>{hasPermission ? "HAS_PERMISSION" : "NO_PERMISSION"}</div>;
};

describe("Authentication & RBAC Hook and Guard", () => {
  const mockSuperAdmin = {
    id: "1",
    email: "admin@corp.com",
    orgId: "org-1",
    isSuperAdmin: true,
    isActive: true,
    sessionId: "sid-1",
    roles: ["SuperAdmin"],
    permissions: [],
    branchIds: [],
    departmentIds: [],
  };

  const mockBranchAdmin = {
    id: "2",
    email: "branch@corp.com",
    orgId: "org-1",
    isSuperAdmin: false,
    isActive: true,
    sessionId: "sid-2",
    roles: ["BranchAdmin"],
    permissions: [
      {
        feature_key: "employee",
        can_create: true,
        can_read: true,
        can_edit: false,
        can_delete: false,
      },
    ],
    branchIds: [12],
    departmentIds: [3],
  };

  test("SuperAdmin has permission for any actions", () => {
    const mockContext = {
      user: mockSuperAdmin,
      isAuthenticated: true,
      isLoading: false,
      error: null,
      login: () => {},
      logout: async () => {},
      refresh: async () => {},
    };

    render(
      <AuthContext.Provider value={mockContext}>
        <PermissionTester feature="any_feature" action="delete" />
      </AuthContext.Provider>
    );

    expect(screen.getByText("HAS_PERMISSION")).toBeInTheDocument();
  });

  test("BranchAdmin permissions map correctly", () => {
    const mockContext = {
      user: mockBranchAdmin,
      isAuthenticated: true,
      isLoading: false,
      error: null,
      login: () => {},
      logout: async () => {},
      refresh: async () => {},
    };

    const { rerender } = render(
      <AuthContext.Provider value={mockContext}>
        <PermissionTester feature="employee" action="create" />
      </AuthContext.Provider>
    );
    expect(screen.getByText("HAS_PERMISSION")).toBeInTheDocument();

    rerender(
      <AuthContext.Provider value={mockContext}>
        <PermissionTester feature="employee" action="delete" />
      </AuthContext.Provider>
    );
    expect(screen.getByText("NO_PERMISSION")).toBeInTheDocument();
  });

  test("PermissionGuard displays fallback when user lacks permission", () => {
    const mockContext = {
      user: mockBranchAdmin,
      isAuthenticated: true,
      isLoading: false,
      error: null,
      login: () => {},
      logout: async () => {},
      refresh: async () => {},
    };

    render(
      <AuthContext.Provider value={mockContext}>
        <PermissionGuard
          permission={{ feature: "employee", action: "delete" }}
          fallback={<div>Fallback Content</div>}
        >
          <div>Protected Content</div>
        </PermissionGuard>
      </AuthContext.Provider>
    );

    expect(screen.getByText("Fallback Content")).toBeInTheDocument();
    expect(screen.queryByText("Protected Content")).not.toBeInTheDocument();
  });
});
