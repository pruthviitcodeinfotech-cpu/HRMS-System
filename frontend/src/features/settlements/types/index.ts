export type LoanAdvanceType = "loan" | "advance";
export type LoanAdvanceStatus = "active" | "closed";
export type TransactionType = "disbursement" | "repayment" | "adjustment" | "write_off" | "credit" | "debit";
export type TransactionSource = "payroll" | "manual" | "system";

export interface LoanAdvanceTransactionSchema {
  id: number;
  loan_advance_id: number;
  transaction_date: string;
  transaction_type: TransactionType;
  amount: number;
  source: TransactionSource;
  payroll_run_id?: number | null;
  remarks?: string | null;
  created_at: string;
}

export interface LoanAdvanceSchema {
  id: number;
  org_id: number;
  employee_id: number;
  employee_code?: string;
  employee_name?: string;
  department_name?: string;
  designation_name?: string;
  branch_name?: string;
  name: string;
  type: LoanAdvanceType;
  principal_amount: number;
  monthly_installment: number;
  total_debit: number;
  outstanding_amount: number;
  transaction_date: string;
  status: LoanAdvanceStatus;
  comment?: string | null;
  created_at: string;
  updated_at: string;
}

export interface LoanAdvanceDetailsSchema extends LoanAdvanceSchema {
  transactions: LoanAdvanceTransactionSchema[];
}

export interface PaginationMeta {
  page: number;
  page_size: number;
  total_records: number;
  total_pages: number;
  has_next: boolean;
  has_previous: boolean;
}

export interface LoanAdvanceListResponse {
  items: LoanAdvanceSchema[];
  pagination: PaginationMeta;
}

export interface LoanAdvanceTransactionListResponse {
  items: LoanAdvanceTransactionSchema[];
  pagination: PaginationMeta;
}

export interface LoanAdvanceListParams {
  page?: number;
  page_size?: number;
  employee_id?: number;
  type?: LoanAdvanceType;
  status?: "active" | "closed" | "all";
  search?: string;
  sort_by?: string;
  sort_order?: "asc" | "desc";
  date_from?: string;
  date_to?: string;
}

export interface LoanAdvanceLogsParams {
  page?: number;
  page_size?: number;
  employee_id?: number;
  transaction_type?: TransactionType;
  source?: TransactionSource;
  date_from?: string;
  date_to?: string;
  sort_by?: string;
  sort_order?: "asc" | "desc";
}

export interface LoanAdvanceCreatePayload {
  employee_id: number;
  name: string;
  type: LoanAdvanceType;
  principal_amount: number;
  monthly_installment: number;
  transaction_date: string;
  comment?: string;
}

export interface LoanAdvanceUpdatePayload {
  name?: string;
  principal_amount?: number;
  monthly_installment?: number;
  comment?: string;
}

// ============================================================================
// Arrears Module Interfaces
// ============================================================================

export interface ArrearsTransactionSchema {
  id: number;
  org_id: number;
  employee_arrears_id: number;
  employee_id: number;
  employee_code?: string;
  employee_name?: string;
  transaction_date: string;
  transaction_type: TransactionType;
  amount: number;
  outstanding_before: number;
  outstanding_after: number;
  comment?: string | null;
  source: TransactionSource;
  created_at: string;
}

export interface ArrearsSchema {
  id: number;
  org_id: number;
  employee_id: number;
  employee_code?: string;
  employee_name?: string;
  department_name?: string;
  designation_name?: string;
  branch_name?: string;
  arrears_created: number;
  arrears_paid: number;
  outstanding_arrears: number;
  created_at: string;
  updated_at: string;
}

export interface ArrearsDetailsSchema extends ArrearsSchema {
  transactions: ArrearsTransactionSchema[];
}

export interface ArrearsListResponse {
  items: ArrearsSchema[];
  pagination: PaginationMeta;
}

export interface ArrearsTransactionListResponse {
  items: ArrearsTransactionSchema[];
  pagination: PaginationMeta;
}

export interface ArrearsListParams {
  page?: number;
  page_size?: number;
  employee_id?: number;
  min_outstanding?: number;
  branch_id?: number;
  dept_id?: number;
  search?: string;
  sort_by?: string;
  sort_order?: "asc" | "desc";
}

export interface ArrearsLogsParams {
  page?: number;
  page_size?: number;
  employee_id?: number;
  transaction_type?: TransactionType;
  source?: TransactionSource;
  date_from?: string;
  date_to?: string;
  sort_by?: string;
  sort_order?: "asc" | "desc";
}

export interface ArrearsCreatePayload {
  employee_id: number;
  amount: number;
  transaction_date: string;
  comment?: string;
}

export interface ArrearsUpdatePayload {
  amount?: number;
  comment?: string;
}

export interface ArrearsPayPayload {
  amount: number;
  transaction_date: string;
  comment?: string;
}
