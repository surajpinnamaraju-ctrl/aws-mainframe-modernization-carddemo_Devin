export interface Session {
  token: string;
  user_id: string;
  first_name: string;
  last_name: string;
  user_type: "A" | "U";
}

export interface Account {
  acct_id: number;
  active_status: string;
  curr_bal: string;
  credit_limit: string;
  cash_credit_limit: string;
  open_date: string;
  expiration_date: string;
  reissue_date: string;
  curr_cyc_credit: string;
  curr_cyc_debit: string;
  addr_zip: string;
  group_id: string;
  cust_id?: number;
  cust_first_name?: string;
  cust_last_name?: string;
  card_num?: string;
}

export interface Card {
  card_num: string;
  acct_id: number;
  cvv_cd: number;
  embossed_name: string;
  expiration_date: string;
  active_status: string;
}

export interface Transaction {
  tran_id: string;
  type_cd: string;
  cat_cd: number;
  source: string;
  description: string;
  amount: string;
  merchant_id: number;
  merchant_name: string;
  merchant_city: string;
  merchant_zip: string;
  card_num: string;
  orig_ts: string;
  proc_ts: string;
  type_desc?: string;
  cat_desc?: string;
}

export interface User {
  user_id: string;
  first_name: string;
  last_name: string;
  user_type: "A" | "U";
}

export interface TranType {
  tran_type_cd: string;
  tran_type_desc: string;
}

export interface TranCategory {
  tran_type_cd: string;
  tran_cat_cd: number;
  tran_cat_type_desc: string;
}

export interface Authorization {
  auth_id: string;
  card_num: string;
  acct_id: number;
  merchant_name: string;
  amount: string;
  status: string;
  auth_ts: string;
  expiry_ts: string;
}

export interface ReportLine {
  tran_id: string;
  acct_id: number | null;
  card_num: string;
  type_cd: string;
  type_desc: string;
  cat_cd: number;
  cat_desc: string;
  source: string;
  description: string;
  amount: string;
  orig_ts: string;
}

export interface TransactionReport {
  start_date: string;
  end_date: string;
  lines: ReportLine[];
  account_totals: Record<string, string>;
  grand_total: string;
}

export interface Statement {
  acct_id: number;
  card_num: string;
  cust_name: string;
  address: string[];
  fico_score: number;
  lines: Transaction[];
  total_expenses: string;
}
