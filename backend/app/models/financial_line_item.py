"""
Database model for storing detailed financial line items
Supports hierarchical storage of all extracted data
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class FinancialLineItem(Base):
    """Detailed financial line item with hierarchical structure"""

    __tablename__ = "financial_line_items"

    id = Column(Integer, primary_key=True, index=True)
    assessment_id = Column(Integer, ForeignKey("vendor_assessments.id"), nullable=False)
    fiscal_year = Column(Integer, nullable=False)

    # Line Item Details
    line_item_text = Column(String(500), nullable=False)  # Original text from PDF
    canonical_name = Column(String(200), nullable=True)  # Standardized name
    category = Column(String(50), nullable=False)  # asset, liability, equity, revenue, expense, cashflow

    # Hierarchy
    parent_canonical_name = Column(String(200), nullable=True)  # Parent in hierarchy
    level = Column(Integer, default=0)  # 0=top level, 1=subcategory, 2=detail, etc.

    # Financial Value
    value = Column(Float, nullable=True)  # The actual financial value

    # Statement Type
    statement_type = Column(String(50), nullable=False)  # balance_sheet, income_statement, cash_flow

    # Metadata
    confidence = Column(Float, default=1.0)  # Confidence in the extraction
    is_calculated = Column(Boolean, default=False)  # Whether this was calculated vs extracted
    extraction_method = Column(String(50), default="camelot")  # camelot, llm, manual
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    assessment = relationship("VendorAssessment", back_populates="line_items")

    def __repr__(self):
        return f"<FinancialLineItem(year={self.fiscal_year}, item={self.line_item_text}, value={self.value})>"

    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": self.id,
            "fiscal_year": self.fiscal_year,
            "line_item_text": self.line_item_text,
            "canonical_name": self.canonical_name,
            "category": self.category,
            "parent_canonical_name": self.parent_canonical_name,
            "level": self.level,
            "value": self.value,
            "statement_type": self.statement_type,
            "confidence": self.confidence,
            "is_calculated": self.is_calculated
        }
