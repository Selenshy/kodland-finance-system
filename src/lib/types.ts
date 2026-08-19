export type Role = "admin" | "accountant" | "viewer";

export type User = {
  id: number;
  account_id: number;
  email: string;
  full_name: string;
  is_active: boolean;
  global_role: Role;
  entity_ids: number[] | null;
};

export type LegalEntity = {
  id: number;
  account_id: number;
  name: string;
  country: string;
  functional_currency: string;
};

export type AccountType = "asset" | "liability" | "equity" | "income" | "expense";
export type CfCategory = "operating" | "investing" | "financing";

export type ChartOfAccount = {
  id: number;
  legal_entity_id: number;
  code: string;
  name: string;
  parent_id: number | null;
  account_type: AccountType;
  report_line: string;
  is_cash: boolean;
  cf_category: CfCategory | null;
  cf_line: string;
  is_postable: boolean;
  is_active: boolean;
};

export type Dimension = {
  id: number;
  legal_entity_id: number;
  name: string;
  is_active: boolean;
};

export type Currency = { code: string; name: string };

export type FxRate = {
  id: number;
  rate_date: string;
  currency_from: string;
  currency_to: string;
  rate: number;
  source: string;
};

export type EntryDirection = "debit" | "credit";

export type JournalLine = {
  id: number;
  account_id: number;
  direction: EntryDirection;
  transaction_currency: string;
  transaction_amount: number;
  local_currency_amount: number;
  usd_amount: number;
  fx_rate_to_local: number;
  fx_rate_to_usd: number;
  cost_center_id: number | null;
  counterparty_id: number | null;
  project_id: number | null;
  memo: string;
};

export type JournalEntry = {
  id: number;
  legal_entity_id: number;
  entry_date: string;
  description: string;
  import_batch_id: number | null;
  lines: JournalLine[];
};

export type OpeningBalance = {
  id: number;
  legal_entity_id: number;
  account_id: number;
  as_of_date: string;
  local_currency_amount: number;
  usd_amount: number;
};

export type ReportLine = { code: string; label: string; amount: number; is_subtotal: boolean };
export type ReportSection = { title: string; lines: ReportLine[]; total: number };
export type Report = {
  report_type: string;
  legal_entity_ids: number[];
  period_start: string;
  period_end: string;
  currency: string;
  sections: ReportSection[];
  check_ok: boolean | null;
};

export type ImportUploadResult = {
  upload_token: string;
  columns: string[];
  preview_rows: Record<string, unknown>[];
  total_rows: number;
};

export type ImportRowError = { row_number: number; message: string };

export type ImportValidateResult = {
  valid_rows: number;
  invalid_rows: number;
  errors: ImportRowError[];
  can_commit: boolean;
};

export type ImportCommitResult = {
  import_batch_id: number;
  entries_created: number;
  lines_created: number;
  error_count: number;
  errors: ImportRowError[];
};

export type ImportMappingTemplate = {
  id: number;
  legal_entity_id: number | null;
  name: string;
  target_kind: string;
  column_mapping: Record<string, string>;
};

export type AuditLogEntry = {
  id: number;
  entity_type: string;
  entity_id: number;
  field: string;
  old_value: string | null;
  new_value: string | null;
  changed_by_user_id: number | null;
  changed_at: string;
};
