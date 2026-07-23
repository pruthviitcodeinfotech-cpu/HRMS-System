import { ProtectedRoute } from "@/features/auth";
import { UserManagementPage } from "@/features/users/components/user-management-page";

export const metadata = {
  title: "Manage Rights Templates | Petpooja Payroll",
  description: "Manage Rights Templates and User Permissions",
};

export default function AllTemplatesPage() {
  return (
    <ProtectedRoute requiredPermission={{ feature: "user_management", action: "read" }}>
      <UserManagementPage />
    </ProtectedRoute>
  );
}
