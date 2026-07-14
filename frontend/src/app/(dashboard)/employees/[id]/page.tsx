interface EmployeeDetailPageProps {
  params: Promise<{ id: string }>;
}

export default async function EmployeeDetailPage({ params }: EmployeeDetailPageProps) {
  const resolvedParams = await params;
  return (
    <div>
      <h1 className="text-3xl font-bold mb-2">Employee Profile</h1>
      <p className="font-mono text-sm text-foreground/75">Employee ID: {resolvedParams.id}</p>
    </div>
  );
}
