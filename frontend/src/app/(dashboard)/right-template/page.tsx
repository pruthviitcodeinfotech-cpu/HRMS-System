import { ProtectedRoute } from "@/features/auth";
import { CreateAccessTemplatePage } from "@/features/users/components/create-access-template-page";

export const metadata = {
  title: "Create Access Template | Petpooja Payroll",
  description: "Create or Edit Rights Access Template",
};

export default function RightTemplatePage() {
  return (
    <ProtectedRoute requiredPermission={{ feature: "user_management", action: "create" }}>
      <CreateAccessTemplatePage />
    </ProtectedRoute>
  );
}
