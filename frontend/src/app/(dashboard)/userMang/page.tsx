import { ProtectedRoute } from "@/features/auth";
import { ManageUsersPage } from "@/features/users/components/manage-users-page";

export const metadata = {
  title: "Manage Users | Petpooja Payroll",
  description: "Manage Users and Access Rights",
};

export default function UserMangPage() {
  return (
    <ProtectedRoute requiredPermission={{ feature: "user_management", action: "read" }}>
      <ManageUsersPage />
    </ProtectedRoute>
  );
}
