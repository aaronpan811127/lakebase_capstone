// Response/request types mirroring backend/models.py

export interface CustomerListItem {
  customer_id: string;
  first_name: string;
  last_name: string;
  email: string;
  country: string;
  segment_id: string;
  lifetime_value: number;
  churn_score: number;
}

export interface CustomerListOut {
  items: CustomerListItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface TransactionOut {
  transaction_id: string;
  product_id: string;
  transaction_date: string | null;
  channel: string | null;
  status: string | null;
  amount: number | null;
}

export interface CustomerDetailOut {
  customer_id: string;
  first_name: string;
  last_name: string;
  email: string;
  phone: string | null;
  country: string | null;
  city: string | null;
  age: number | null;
  gender: string | null;
  signup_date: string | null;
  last_purchase_date: string | null;
  segment_id: string;
  lifetime_value: number;
  churn_score: number;
  recent_transactions: TransactionOut[];
}

export interface CategorySpend {
  category: string;
  spend: number;
}

export interface MetricsOut {
  customer_id: string;
  lifetime_spend: number;
  top_categories: CategorySpend[];
  last_30d_spend: number;
  last_90d_spend: number;
  open_tickets: number;
  avg_csat: number | null;
}

export interface NoteOut {
  note_id: string;
  customer_id: string;
  author_email: string;
  note_text: string;
  created_at: string;
  processed: boolean;
}

export interface SegmentOverrideOut {
  customer_id: string;
  override_segment: string;
  reason: string | null;
  author_email: string;
  created_at: string;
}

export interface ConfigOut {
  databricks_host: string;
  dashboard_id: string;
  genie_space_id: string;
}

export interface MeOut {
  email: string;
  workspace_host: string;
}

export interface RunOut {
  run_id: number;
  state: string;
  result_state: string | null;
  run_page_url: string | null;
  start_time: number | null;
  end_time: number | null;
}

export interface GenieMessageOut {
  conversation_id: string;
  message_id: string;
  status: string | null;
  content: string | null;
  answer_text: string | null;
  query: string | null;
  result_columns: string[] | null;
  result_rows: unknown[][] | null;
}
