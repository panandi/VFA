from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, JSON, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class AssessmentStatus(str, enum.Enum):
    """Status of the vendor assessment."""
    DRAFT = "draft"
    STEP1_COMPLETE = "step1_complete"
    STEP2_COMPLETE = "step2_complete"
    STEP3_COMPLETE = "step3_complete"
    COMPLETED = "completed"
    SIGNED_OFF = "signed_off"


class RiskLevel(str, enum.Enum):
    """Risk level classification."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RecommendationType(str, enum.Enum):
    """Recommendation types."""
    PROCEED = "proceed"
    PROCEED_WITH_MITIGATION = "proceed_with_mitigation"
    DO_NOT_PROCEED = "do_not_proceed"


class VendorAssessment(Base):
    """Main vendor assessment record."""

    __tablename__ = "vendor_assessments"

    id = Column(Integer, primary_key=True, index=True)
    vendor_name = Column(String(255), nullable=True)
    vendor_registration_number = Column(String(100), nullable=True)
    assessment_date = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(String(50), default=AssessmentStatus.DRAFT.value)
    current_step = Column(Integer, default=1)

    # Foreign Keys
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    created_by_user = relationship("User", back_populates="assessments")
    financial_statements = relationship("FinancialStatement", back_populates="assessment", cascade="all, delete-orphan")
    extracted_data = relationship("ExtractedFinancialData", back_populates="assessment", cascade="all, delete-orphan")
    qualitative_responses = relationship("QualitativeResponse", back_populates="assessment", cascade="all, delete-orphan")
    risk_assessment = relationship("RiskAssessment", back_populates="assessment", uselist=False, cascade="all, delete-orphan")
    recommendation = relationship("Recommendation", back_populates="assessment", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<VendorAssessment(id={self.id}, vendor={self.vendor_name})>"


class FinancialStatement(Base):
    """Uploaded financial statement PDF metadata."""

    __tablename__ = "financial_statements"

    id = Column(Integer, primary_key=True, index=True)
    assessment_id = Column(Integer, ForeignKey("vendor_assessments.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=True)
    file_type = Column(String(50), default="application/pdf")
    upload_date = Column(DateTime(timezone=True), server_default=func.now())
    is_processed = Column(Boolean, default=False)
    processing_status = Column(String(50), default="pending")
    error_message = Column(Text, nullable=True)

    # Relationships
    assessment = relationship("VendorAssessment", back_populates="financial_statements")

    def __repr__(self):
        return f"<FinancialStatement(id={self.id}, filename={self.filename})>"


class ExtractedFinancialData(Base):
    """AI-extracted financial data from PDFs."""

    __tablename__ = "extracted_financial_data"

    id = Column(Integer, primary_key=True, index=True)
    assessment_id = Column(Integer, ForeignKey("vendor_assessments.id"), nullable=False)

    # Year of the financial data
    fiscal_year = Column(Integer, nullable=False)

    # Balance Sheet Items
    total_assets = Column(Float, nullable=True)
    current_assets = Column(Float, nullable=True)
    non_current_assets = Column(Float, nullable=True)
    total_liabilities = Column(Float, nullable=True)
    current_liabilities = Column(Float, nullable=True)
    non_current_liabilities = Column(Float, nullable=True)
    total_equity = Column(Float, nullable=True)
    retained_earnings = Column(Float, nullable=True)
    working_capital = Column(Float, nullable=True)
    cash_and_equivalents = Column(Float, nullable=True)
    inventory = Column(Float, nullable=True)
    accounts_receivable = Column(Float, nullable=True)
    accounts_payable = Column(Float, nullable=True)

    # Profit & Loss Items
    revenue = Column(Float, nullable=True)
    cost_of_sales = Column(Float, nullable=True)
    gross_profit = Column(Float, nullable=True)
    operating_expenses = Column(Float, nullable=True)
    operating_income = Column(Float, nullable=True)
    ebit = Column(Float, nullable=True)
    ebitda = Column(Float, nullable=True)
    interest_expense = Column(Float, nullable=True)
    net_income = Column(Float, nullable=True)

    # Cash Flow Items
    operating_cash_flow = Column(Float, nullable=True)
    investing_cash_flow = Column(Float, nullable=True)
    financing_cash_flow = Column(Float, nullable=True)
    net_cash_flow = Column(Float, nullable=True)

    # Extraction metadata
    confidence_scores = Column(JSON, nullable=True)
    is_confirmed = Column(Boolean, default=False)
    extraction_date = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    assessment = relationship("VendorAssessment", back_populates="extracted_data")

    def __repr__(self):
        return f"<ExtractedFinancialData(id={self.id}, year={self.fiscal_year})>"


class QualitativeResponse(Base):
    """Qualitative questionnaire responses."""

    __tablename__ = "qualitative_responses"

    id = Column(Integer, primary_key=True, index=True)
    assessment_id = Column(Integer, ForeignKey("vendor_assessments.id"), nullable=False)

    question_id = Column(String(50), nullable=False)
    question_text = Column(Text, nullable=False)
    response = Column(String(20), nullable=True)  # yes, no, n/a
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    assessment = relationship("VendorAssessment", back_populates="qualitative_responses")

    def __repr__(self):
        return f"<QualitativeResponse(id={self.id}, question={self.question_id})>"


class RiskAssessment(Base):
    """Calculated financial ratios and risk scores."""

    __tablename__ = "risk_assessments"

    id = Column(Integer, primary_key=True, index=True)
    assessment_id = Column(Integer, ForeignKey("vendor_assessments.id"), nullable=False, unique=True)

    # Z-Score Components
    z_score = Column(Float, nullable=True)
    z_score_x1 = Column(Float, nullable=True)  # Working Capital / Total Assets
    z_score_x2 = Column(Float, nullable=True)  # Retained Earnings / Total Assets
    z_score_x3 = Column(Float, nullable=True)  # EBIT / Total Assets
    z_score_x4 = Column(Float, nullable=True)  # Book Value of Equity / Total Liabilities
    z_score_x5 = Column(Float, nullable=True)  # Sales / Total Assets

    # Risk Level
    risk_level = Column(String(20), nullable=True)

    # Liquidity Ratios
    current_ratio = Column(Float, nullable=True)
    quick_ratio = Column(Float, nullable=True)
    cash_ratio = Column(Float, nullable=True)

    # Profitability Ratios
    gross_margin = Column(Float, nullable=True)
    operating_margin = Column(Float, nullable=True)
    net_margin = Column(Float, nullable=True)
    roa = Column(Float, nullable=True)  # Return on Assets
    roe = Column(Float, nullable=True)  # Return on Equity

    # Leverage Ratios
    debt_to_equity = Column(Float, nullable=True)
    debt_to_assets = Column(Float, nullable=True)
    interest_coverage = Column(Float, nullable=True)

    # Efficiency Ratios
    asset_turnover = Column(Float, nullable=True)
    inventory_turnover = Column(Float, nullable=True)
    receivables_turnover = Column(Float, nullable=True)

    # Metadata
    calculated_at = Column(DateTime(timezone=True), server_default=func.now())
    fiscal_year_used = Column(Integer, nullable=True)

    # Relationships
    assessment = relationship("VendorAssessment", back_populates="risk_assessment")

    def __repr__(self):
        return f"<RiskAssessment(id={self.id}, z_score={self.z_score})>"


class Recommendation(Base):
    """AI-generated recommendation and commentary."""

    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, index=True)
    assessment_id = Column(Integer, ForeignKey("vendor_assessments.id"), nullable=False, unique=True)

    # Recommendation
    recommendation_type = Column(String(50), nullable=False)
    recommendation_text = Column(Text, nullable=True)

    # Supporting Factors
    supporting_factors = Column(JSON, nullable=True)

    # Summary
    summary = Column(Text, nullable=True)

    # Sign-off
    is_signed_off = Column(Boolean, default=False)
    signed_off_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    signed_off_at = Column(DateTime(timezone=True), nullable=True)

    # Metadata
    generated_at = Column(DateTime(timezone=True), server_default=func.now())
    model_used = Column(String(100), nullable=True)

    # Relationships
    assessment = relationship("VendorAssessment", back_populates="recommendation")

    def __repr__(self):
        return f"<Recommendation(id={self.id}, type={self.recommendation_type})>"
