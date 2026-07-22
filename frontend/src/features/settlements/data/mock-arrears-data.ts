import { ArrearsSchema, ArrearsTransactionSchema } from "../types";

export interface ArrearsDetail {
  id: number;
  reason: string;
  effectiveDate: string;
  arrearsCreated: number;
  arrearsPaid: number;
  outstandingArrears: number;
  status: "paid" | "partial" | "pending";
}

export interface EmployeeArrearsSummary {
  id: number;
  employeeId: number;
  employeeCode: string;
  employeeName: string;
  department: string;
  designation: string;
  branch: string;
  arrearsCreated: number;
  arrearsPaid: number;
  outstandingArrears: number;
  arrearsCount: number;
  records: ArrearsDetail[];
}

export interface ArrearsAuditLog {
  id: number;
  timestamp: string;
  employeeName: string;
  employeeCode: string;
  action: string;
  amount: number;
  performedBy: string;
  remarks: string;
}

export const FALLBACK_MOCK_ARREARS: ArrearsSchema[] = [
  {
    id: 1,
    org_id: 1,
    employee_id: 101,
    employee_code: "EMP-1001",
    employee_name: "Balkrushn Koladiya",
    department_name: "Engineering",
    designation_name: "Senior Software Engineer",
    branch_name: "Surat HQ",
    arrears_created: 275450.75,
    arrears_paid: 150000.00,
    outstanding_arrears: 125450.75,
    created_at: "2026-07-01T10:00:00Z",
    updated_at: "2026-07-20T14:30:00Z",
  },
  {
    id: 2,
    org_id: 1,
    employee_id: 102,
    employee_code: "EMP-1002",
    employee_name: "Pruthvi Patel",
    department_name: "Human Resources",
    designation_name: "HR Manager",
    branch_name: "Ahmedabad Branch",
    arrears_created: 48750.50,
    arrears_paid: 48750.50,
    outstanding_arrears: 0.00,
    created_at: "2026-07-02T11:15:00Z",
    updated_at: "2026-07-18T09:40:00Z",
  },
  {
    id: 3,
    org_id: 1,
    employee_id: 103,
    employee_code: "EMP-1003",
    employee_name: "Jignesh Parmar",
    department_name: "Operations",
    designation_name: "Operations Lead",
    branch_name: "Mumbai Central",
    arrears_created: 162300.25,
    arrears_paid: 42300.25,
    outstanding_arrears: 120000.00,
    created_at: "2026-07-05T08:20:00Z",
    updated_at: "2026-07-19T16:00:00Z",
  },
  {
    id: 4,
    org_id: 1,
    employee_id: 104,
    employee_code: "EMP-1004",
    employee_name: "Anjali Sharma",
    department_name: "Finance",
    designation_name: "Senior Accountant",
    branch_name: "Surat HQ",
    arrears_created: 0.00,
    arrears_paid: 0.00,
    outstanding_arrears: 0.00,
    created_at: "2026-07-06T09:00:00Z",
    updated_at: "2026-07-06T09:00:00Z",
  },
  {
    id: 5,
    org_id: 1,
    employee_id: 105,
    employee_code: "EMP-1005",
    employee_name: "Rahul Mehta",
    department_name: "Engineering",
    designation_name: "DevOps Specialist",
    branch_name: "Bangalore Hub",
    arrears_created: 85000.00,
    arrears_paid: 25000.00,
    outstanding_arrears: 60000.00,
    created_at: "2026-07-08T14:10:00Z",
    updated_at: "2026-07-21T10:15:00Z",
  },
  {
    id: 6,
    org_id: 1,
    employee_id: 106,
    employee_code: "EMP-1006",
    employee_name: "Sneha Desai",
    department_name: "Marketing",
    designation_name: "Marketing Specialist",
    branch_name: "Surat HQ",
    arrears_created: 18450.80,
    arrears_paid: 18450.80,
    outstanding_arrears: 0.00,
    created_at: "2026-07-10T12:00:00Z",
    updated_at: "2026-07-20T16:45:00Z",
  },
  {
    id: 7,
    org_id: 1,
    employee_id: 107,
    employee_code: "EMP-1007",
    employee_name: "Vikas Joshi",
    department_name: "Engineering",
    designation_name: "QA Engineer",
    branch_name: "Ahmedabad Branch",
    arrears_created: 34500.00,
    arrears_paid: 14500.00,
    outstanding_arrears: 20000.00,
    created_at: "2026-07-12T15:30:00Z",
    updated_at: "2026-07-21T11:20:00Z",
  },
  {
    id: 8,
    org_id: 1,
    employee_id: 108,
    employee_code: "EMP-1008",
    employee_name: "Pooja Shah",
    department_name: "Human Resources",
    designation_name: "HR Executive",
    branch_name: "Surat HQ",
    arrears_created: 12800.00,
    arrears_paid: 0.00,
    outstanding_arrears: 12800.00,
    created_at: "2026-07-14T09:45:00Z",
    updated_at: "2026-07-14T09:45:00Z",
  },
  {
    id: 9,
    org_id: 1,
    employee_id: 109,
    employee_code: "EMP-1009",
    employee_name: "Amit Trivedi",
    department_name: "Operations",
    designation_name: "Logistics Officer",
    branch_name: "Mumbai Central",
    arrears_created: 55000.00,
    arrears_paid: 55000.00,
    outstanding_arrears: 0.00,
    created_at: "2026-07-15T11:00:00Z",
    updated_at: "2026-07-22T12:00:00Z",
  },
  {
    id: 10,
    org_id: 1,
    employee_id: 110,
    employee_code: "EMP-1010",
    employee_name: "Kavita Rao",
    department_name: "Finance",
    designation_name: "Tax Consultant",
    branch_name: "Bangalore Hub",
    arrears_created: 32500.60,
    arrears_paid: 16250.30,
    outstanding_arrears: 16250.30,
    created_at: "2026-07-16T13:20:00Z",
    updated_at: "2026-07-21T15:40:00Z",
  },
];

export const FALLBACK_MOCK_LOGS: ArrearsTransactionSchema[] = [
  {
    id: 1,
    org_id: 1,
    employee_arrears_id: 1,
    employee_id: 101,
    employee_code: "EMP-1001",
    employee_name: "Balkrushn Koladiya",
    branch_name: "HQ Branch",
    transaction_date: "2026-07-20",
    transaction_type: "credit",
    amount: 75450.75,
    outstanding_before: 50000.00,
    outstanding_after: 125450.75,
    comment: "Retrospective Technical Lead Allowance created",
    source: "manual",
    created_at: "2026-07-20T14:30:12Z",
  },
  {
    id: 2,
    org_id: 1,
    employee_arrears_id: 2,
    employee_id: 102,
    employee_code: "EMP-1002",
    employee_name: "Pruthvi Patel",
    branch_name: "East Branch",
    transaction_date: "2026-07-18",
    transaction_type: "debit",
    amount: 48750.50,
    outstanding_before: 48750.50,
    outstanding_after: 0.00,
    comment: "Full settlement via July Payroll",
    source: "payroll",
    created_at: "2026-07-18T11:15:45Z",
  },
  {
    id: 3,
    org_id: 1,
    employee_arrears_id: 3,
    employee_id: 103,
    employee_code: "EMP-1003",
    employee_name: "Jignesh Parmar",
    branch_name: "South Branch",
    transaction_date: "2026-07-19",
    transaction_type: "debit",
    amount: 42300.25,
    outstanding_before: 162300.25,
    outstanding_after: 120000.00,
    comment: "Partial payment processed via bank transfer",
    source: "manual",
    created_at: "2026-07-19T16:00:00Z",
  },
  {
    id: 4,
    org_id: 1,
    employee_arrears_id: 4,
    employee_id: 105,
    employee_code: "EMP-1005",
    employee_name: "Rahul Mehta",
    branch_name: "West Branch",
    transaction_date: "2026-07-15",
    transaction_type: "credit",
    amount: 25000.00,
    outstanding_before: 0.00,
    outstanding_after: 25000.00,
    comment: "DevOps On-Call Special Allowance",
    source: "manual",
    created_at: "2026-07-15T10:00:00Z",
  },
  {
    id: 5,
    org_id: 1,
    employee_arrears_id: 5,
    employee_id: 107,
    employee_code: "EMP-1007",
    employee_name: "Vikas Joshi",
    branch_name: "East Branch",
    transaction_date: "2026-07-12",
    transaction_type: "debit",
    amount: 14500.00,
    outstanding_before: 34500.00,
    outstanding_after: 20000.00,
    comment: "Partial reimbursement deduction",
    source: "payroll",
    created_at: "2026-07-12T15:30:00Z",
  },
];
