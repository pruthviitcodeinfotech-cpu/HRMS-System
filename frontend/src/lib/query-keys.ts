export const QUERY_KEYS = {
  auth: {
    session: ["auth", "session"] as const,
    profile: ["auth", "profile"] as const,
  },
  employees: {
    list: (filters?: Record<string, unknown>) => ["employees", "list", filters || {}] as const,
    detail: (id: string) => ["employees", "detail", id] as const,
  },
  payroll: {
    runs: (filters?: Record<string, unknown>) => ["payroll", "runs", filters || {}] as const,
    payslip: (id: string) => ["payroll", "payslip", id] as const,
  },
  attendance: {
    records: (filters?: Record<string, unknown>) =>
      ["attendance", "records", filters || {}] as const,
  },
  leaves: {
    requests: (filters?: Record<string, unknown>) => ["leaves", "requests", filters || {}] as const,
  },
  shifts: {
    list: (filters?: Record<string, unknown>) => ["shifts", "list", filters || {}] as const,
  },
} as const;
