export interface User {
  id: number;
  email: string;
  full_name: string;
  initials?: string;
  is_active: boolean;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface Assessment {
  id: number;
  vendor_name: string;
  vendor_registration_number?: string;
  assessment_date: string;
  status: AssessmentStatus;
  current_step: number;
  created_at: string;
  updated_at?: string;
  completed_at?: string;
  signed_off_at?: string;
  financial_statements: FinancialStatement[];
  extracted_data: ExtractedData[];
  qualitative_responses: QualitativeResponse[];
  risk_assessment?: RiskAssessment;
  recommendation?: Recommendation;
}

export interface AssessmentListItem {
  id: number;
  vendor_name: string;
  status: AssessmentStatus;
  current_step: number;
  created_at: string;
  updated_at?: string;
}

export type AssessmentStatus =
  | 'draft'
  | 'step1_complete'
  | 'step2_complete'
  | 'step3_complete'
  | 'completed'
  | 'signed_off';

export interface FinancialStatement {
  id: number;
  filename: string;
  file_size?: number;
  upload_date: string;
  is_processed: boolean;
  processing_status: string;
}

export interface ExtractedData {
  id: number;
  fiscal_year: number;
  is_confirmed: boolean;
  confidence_scores?: Record<string, number>;
  extraction_date: string;
  // Balance Sheet
  total_assets?: number;
  current_assets?: number;
  non_current_assets?: number;
  total_liabilities?: number;
  current_liabilities?: number;
  non_current_liabilities?: number;
  total_equity?: number;
  retained_earnings?: number;
  working_capital?: number;
  cash_and_equivalents?: number;
  inventory?: number;
  accounts_receivable?: number;
  accounts_payable?: number;
  // P&L
  revenue?: number;
  cost_of_sales?: number;
  gross_profit?: number;
  operating_expenses?: number;
  operating_income?: number;
  ebit?: number;
  ebitda?: number;
  interest_expense?: number;
  net_income?: number;
  // Cash Flow
  operating_cash_flow?: number;
  investing_cash_flow?: number;
  financing_cash_flow?: number;
  net_cash_flow?: number;
}

export interface QualitativeResponse {
  id: number;
  question_id: string;
  question_text: string;
  response?: 'yes' | 'no' | 'n/a';
  notes?: string;
}

export interface RiskAssessment {
  id: number;
  z_score?: number;
  risk_level?: 'low' | 'medium' | 'high';
  z_score_components?: ZScoreComponents;
  // Z-Score component values
  z_score_x1?: number;
  z_score_x2?: number;
  z_score_x3?: number;
  z_score_x4?: number;
  z_score_x5?: number;
  // Liquidity
  current_ratio?: number;
  quick_ratio?: number;
  cash_ratio?: number;
  // Profitability
  gross_margin?: number;
  operating_margin?: number;
  net_margin?: number;
  roa?: number;
  roe?: number;
  // Leverage
  debt_to_equity?: number;
  debt_to_assets?: number;
  interest_coverage?: number;
  // Efficiency
  asset_turnover?: number;
  inventory_turnover?: number;
  receivables_turnover?: number;
  calculated_at: string;
  fiscal_year_used?: number;
}

export interface ZScoreComponents {
  x1?: number;
  x2?: number;
  x3?: number;
  x4?: number;
  x5?: number;
  x1_weighted?: number;
  x2_weighted?: number;
  x3_weighted?: number;
  x4_weighted?: number;
  x5_weighted?: number;
}

export interface Recommendation {
  id: number;
  recommendation_type: 'proceed' | 'proceed_with_mitigation' | 'do_not_proceed';
  recommendation_text?: string;
  supporting_factors?: string[];
  summary?: string;
  is_signed_off: boolean;
  signed_off_at?: string;
  generated_at: string;
}
