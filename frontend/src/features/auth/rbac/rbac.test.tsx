import { checkPermission, checkRole } from "./helpers";
import { expect, test, describe } from "vitest";

describe("RBAC Helper Functions", () => {
  const permissions = [
    {
      feature_key: "payroll",
      can_create: true,
      can_read: true,
      can_edit: false,
      can_delete: false,
    },
  ];

  test("checkPermission evaluates correctly", () => {
    expect(checkPermission(permissions, "payroll", "create")).toBe(true);
    expect(checkPermission(permissions, "payroll", "delete")).toBe(false);
    expect(checkPermission(permissions, "missing_feature", "read")).toBe(false);
  });

  test("checkPermission bypasses checks for SuperAdmin", () => {
    expect(checkPermission(permissions, "any_feature", "delete", true)).toBe(true);
  });

  test("checkRole matches single roles correctly", () => {
    const roles = ["BranchAdmin", "Manager"];
    expect(checkRole(roles, "BranchAdmin")).toBe(true);
    expect(checkRole(roles, "SuperAdmin")).toBe(false);
  });

  test("checkRole matches any in multiple roles correctly", () => {
    const roles = ["BranchAdmin", "Manager"];
    expect(checkRole(roles, ["SuperAdmin", "Manager"])).toBe(true);
    expect(checkRole(roles, ["SuperAdmin", "Developer"])).toBe(false);
  });

  test("checkRole bypasses checks for SuperAdmin", () => {
    expect(checkRole([], "Manager", true)).toBe(true);
  });
});
