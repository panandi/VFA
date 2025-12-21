from pydantic import BaseModel, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import json


class AssessmentStatus(str, Enum):
    DRAFT = "draft"
    STEP1_COMPLETE = "step1_complete"
    STEP2_COMPLETE = "step2_complete"
    STEP3_COMPLETE = "step3_complete"
    COMPLETED = "completed"
    SIGNED_OFF = "signed_off"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RecommendationType(str, Enum):
    PROCEED = "proceed"
    PROCEED_WITH_MITIGATION = "proceed_with_mitigation"
    DO_NOT_PROCEED = "do_not_proceed"


# Assessment Schemas
class AssessmentCreate(BaseModel):
    """Schema for creating a new assessment."""
    vendor_name: str
    vendor_registration_number: Optional[str] = None


class AssessmentUpdate(BaseModel):
    """Schema for updating an assessment."""
    vendor_name: Optional[str] = None
    vendor_registration_number: Optional[str] = None
    status: Optional[str] = None
    current_step: Optional[int] = None


class FinancialStatementResponse(BaseModel):
    """Schema for financial statement response."""
    id: int
    filename: str
    file_size: Optional[int]
    upload_date: datetime
    is_processed: bool
    processing_status: str

    class Config:
        from_attributes = True


class ExtractedDataCreate(BaseModel):
    """Schema for creating extracted financial data."""
    fiscal_year: int
    total_assets: Optional[float] = None
    current_assets: Optional[float] = None
    non_current_assets: Optional[float] = None
    total_liabilities: Optional[float] = None
    current_liabilities: Optional[float] = None
    non_current_liabilities: Optional[float] = None
    total_equity: Optional[float] = None
    retained_earnings: Optional[float] = None
    working_capital: Optional[float] = None
    cash_and_equivalents: Optional[float] = None
    inventory: Optional[float] = None
    accounts_receivable: Optional[float] = None
    accounts_payable: Optional[float] = None
    revenue: Optional[float] = None
    cost_of_sales: Optional[float] = None
    gross_profit: Optional[float] = None
    operating_expenses: Optional[float] = None
    operating_income: Optional[float] = None
    ebit: Optional[float] = None
    ebitda: Optional[float] = None
    interest_expense: Optional[float] = None
    net_income: Optional[float] = None
    operating_cash_flow: Optional[float] = None
    investing_cash_flow: Optional[float] = None
    financing_cash_flow: Optional[float] = None
    net_cash_flow: Optional[float] = None


class ExtractedDataUpdate(BaseModel):
    """Schema for updating extracted financial data (all fields optional for partial updates)."""
    fiscal_year: Optional[int] = None
    total_assets: Optional[float] = None
    current_assets: Optional[float] = None
    non_current_assets: Optional[float] = None
    total_liabilities: Optional[float] = None
    current_liabilities: Optional[float] = None
    non_current_liabilities: Optional[float] = None
    total_equity: Optional[float] = None
    retained_earnings: Optional[float] = None
    working_capital: Optional[float] = None
    cash_and_equivalents: Optional[float] = None
    inventory: Optional[float] = None
    accounts_receivable: Optional[float] = None
    accounts_payable: Optional[float] = None
    revenue: Optional[float] = None
    cost_of_sales: Optional[float] = None
    gross_profit: Optional[float] = None
    operating_expenses: Optional[float] = None
    operating_income: Optional[float] = None
    ebit: Optional[float] = None
    ebitda: Optional[float] = None
    interest_expense: Optional[float] = None
    net_income: Optional[float] = None
    operating_cash_flow: Optional[float] = None
    investing_cash_flow: Optional[float] = None
    financing_cash_flow: Optional[float] = None
    net_cash_flow: Optional[float] = None
    is_confirmed: Optional[bool] = None


class ExtractedDataResponse(ExtractedDataCreate):
    """Schema for extracted data response."""
    id: int
    is_confirmed: bool
    confidence_scores: Optional[Dict[str, Any]] = None  # Can contain nested v2_output
    extraction_date: datetime

    @field_validator('confidence_scores', mode='before')
    @classmethod
    def parse_confidence_scores(cls, v):
        """Handle both JSON string and dict formats for backwards compatibility."""
        if v is None:
            return None
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return {"raw": v}
        return v

    class Config:
        from_attributes = True


class QualitativeResponseCreate(BaseModel):
    """Schema for creating qualitative response."""
    question_id: str
    question_text: str
    response: Optional[str] = None
    notes: Optional[str] = None


class QualitativeResponseUpdate(BaseModel):
    """Schema for updating qualitative response."""
    response: Optional[str] = None
    notes: Optional[str] = None


class QualitativeResponseResponse(BaseModel):
    """Schema for qualitative response."""
    id: int
    question_id: str
    question_text: str
    response: Optional[str]
    notes: Optional[str]

    class Config:
        from_attributes = True


class ZScoreComponents(BaseModel):
    """Z-Score components breakdown."""
    x1: Optional[float] = None  # Working Capital / Total Assets
    x2: Optional[float] = None  # Retained Earnings / Total Assets
    x3: Optional[float] = None  # EBIT / Total Assets
    x4: Optional[float] = None  # Book Value of Equity / Total Liabilities
    x5: Optional[float] = None  # Sales / Total Assets
    x1_weighted: Optional[float] = None
    x2_weighted: Optional[float] = None
    x3_weighted: Optional[float] = None
    x4_weighted: Optional[float] = None
    x5_weighted: Optional[float] = None


class RiskAssessmentResponse(BaseModel):
    """Schema for risk assessment response."""
    id: int
    company_type: Optional[str] = "private"
    z_score: Optional[float]
    risk_level: Optional[str]
    z_score_components: Optional[ZScoreComponents] = None

    # Z-Score individual components (for frontend compatibility)
    z_score_x1: Optional[float] = None  # Working Capital / Total Assets
    z_score_x2: Optional[float] = None  # Retained Earnings / Total Assets
    z_score_x3: Optional[float] = None  # EBIT / Total Assets
    z_score_x4: Optional[float] = None  # Book Value of Equity / Total Liabilities
    z_score_x5: Optional[float] = None  # Sales / Total Assets

    # Liquidity Ratios
    working_capital_ratio: Optional[float] = None
    current_ratio: Optional[float]
    quick_ratio: Optional[float]
    cash_ratio: Optional[float]

    # Profitability Ratios
    gross_margin: Optional[float]
    operating_margin: Optional[float]
    net_margin: Optional[float]
    roa: Optional[float]
    roe: Optional[float]

    # Leverage Ratios
    debt_to_equity: Optional[float]
    debt_to_assets: Optional[float]
    interest_coverage: Optional[float]
    retained_earnings_to_assets: Optional[float] = None

    # Efficiency Ratios
    asset_turnover: Optional[float]
    inventory_turnover: Optional[float]
    receivables_turnover: Optional[float]
    sales_to_working_capital: Optional[float] = None
    creditors_to_sales: Optional[float] = None

    # Growth Ratios
    growth_sales: Optional[float] = None
    growth_net_profit: Optional[float] = None
    growth_gross_profit_margin: Optional[float] = None
    growth_net_profit_margin: Optional[float] = None

    # Full ratios with risk levels
    ratios_detail: Optional[Dict[str, Any]] = None

    calculated_at: datetime
    fiscal_year_used: Optional[int]
    previous_fiscal_year_used: Optional[int] = None

    class Config:
        from_attributes = True


class RecommendationResponse(BaseModel):
    """Schema for recommendation response."""
    id: int
    recommendation_type: str
    recommendation_text: Optional[str]
    supporting_factors: Optional[List[str]]
    summary: Optional[str]
    is_signed_off: bool
    signed_off_at: Optional[datetime]
    generated_at: datetime

    class Config:
        from_attributes = True


class AssessmentResponse(BaseModel):
    """Schema for full assessment response."""
    id: int
    vendor_name: str
    vendor_registration_number: Optional[str]
    assessment_date: datetime
    status: str
    current_step: int
    created_at: datetime
    updated_at: Optional[datetime]
    completed_at: Optional[datetime]

    # Related data
    financial_statements: List[FinancialStatementResponse] = []
    extracted_data: List[ExtractedDataResponse] = []
    qualitative_responses: List[QualitativeResponseResponse] = []
    risk_assessment: Optional[RiskAssessmentResponse] = None
    recommendation: Optional[RecommendationResponse] = None

    class Config:
        from_attributes = True


class AssessmentListResponse(BaseModel):
    """Schema for assessment list item."""
    id: int
    vendor_name: str
    status: str
    current_step: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True
