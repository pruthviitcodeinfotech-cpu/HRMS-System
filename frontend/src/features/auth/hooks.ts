import { useContext } from "react";
import { AuthContext } from "./context";

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};

export const usePermission = (feature: string, action: "create" | "read" | "edit" | "delete") => {
  const { user } = useAuth();

  if (!user) return false;
  if (user.isSuperAdmin) return true;

  const permission = user.permissions.find((p) => p.feature_key === feature);
  if (!permission) return false;

  switch (action) {
    case "create":
      return permission.can_create;
    case "read":
      return permission.can_read;
    case "edit":
      return permission.can_edit;
    case "delete":
      return permission.can_delete;
    default:
      return false;
  }
};
