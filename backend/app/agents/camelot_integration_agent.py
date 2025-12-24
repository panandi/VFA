"""
Camelot Integration Agent
Connects Camelot table extractor with the database layer
"""

import logging
from typing import Dict, Any, List
from sqlalchemy.orm import Session

from app.services.camelot_extractor import CamelotExtractor
from app.models.assessment import FinancialStatement, ExtractedFinancialData
from app.models.financial_line_item import FinancialLineItem
from app.core.database import SessionLocal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def run_camelot_extraction(assessment_id: int, statement_id: int, file_path: str):
    """Run Camelot table extraction and save results to database"""

    logger.info(f"Starting Camelot extraction for assessment {assessment_id}")
    logger.info(f"File: {file_path}")

    db = SessionLocal()

    try:
        # Update statement status to processing
        statement = db.query(FinancialStatement).filter(
            FinancialStatement.id == statement_id
        ).first()

        if not statement:
            logger.error(f"Statement {statement_id} not found")
            return

        statement.processing_status = "processing"
        db.commit()

        # Run Camelot extraction
        extractor = CamelotExtractor(file_path)
        statements = extractor.extract_all()

        logger.info(f"Extracted {len(statements)} statement types")

        if not statements:
            statement.processing_status = "error"
            statement.error_message = "No tables found in PDF. Ensure the PDF contains text-based tables."
            statement.is_processed = True
            db.commit()
            return

        # Collect all years from all statements
        all_years = set()
        for stmt in statements:
            all_years.update(stmt.years)

        logger.info(f"Detected fiscal years: {sorted(all_years, reverse=True)}")

        # Delete existing line items for this assessment
        db.query(FinancialLineItem).filter(
            FinancialLineItem.assessment_id == assessment_id
        ).delete()

        # Save all extracted line items
        total_items = 0
        for stmt in statements:
            for line_item in stmt.line_items:
                for year, value in line_item.values.items():
                    db_item = FinancialLineItem(
                        assessment_id=assessment_id,
                        fiscal_year=year,
                        line_item_text=line_item.line_item,
                        canonical_name=line_item.canonical_name,
                        category=line_item.category,
                        parent_canonical_name=line_item.parent,
                        level=line_item.level,
                        value=value,
                        statement_type=stmt.statement_type,
                        confidence=line_item.confidence,
                        extraction_method="camelot"
                    )
                    db.add(db_item)
                    total_items += 1

        db.commit()
        logger.info(f"Saved {total_items} line items to database")

        # Populate ExtractedFinancialData for backward compatibility and calculations
        _populate_extracted_data(db, assessment_id, statements)

        # Update statement status to completed
        statement.processing_status = "completed"
        statement.is_processed = True
        statement.error_message = None
        db.commit()

        logger.info(f"Extraction complete for assessment {assessment_id}")

    except Exception as e:
        logger.error(f"Extraction error: {e}")
        import traceback
        traceback.print_exc()

        # Update statement with error
        statement = db.query(FinancialStatement).filter(
            FinancialStatement.id == statement_id
        ).first()

        if statement:
            statement.processing_status = "error"
            statement.error_message = str(e)
            statement.is_processed = True
            db.commit()

    finally:
        db.close()


def _populate_extracted_data(db: Session, assessment_id: int, statements: List):
    """Populate ExtractedFinancialData table for calculations and reporting"""

    # Delete existing extracted data for this assessment
    db.query(ExtractedFinancialData).filter(
        ExtractedFinancialData.assessment_id == assessment_id
    ).delete()

    # Collect all years from statements
    all_years = set()
    for stmt in statements:
        all_years.update(stmt.years)

    # For each fiscal year, aggregate and save data
    for year in all_years:
        # Collect values by canonical name for this year
        data_dict = {}

        for stmt in statements:
            for line_item in stmt.line_items:
                if line_item.canonical_name and year in line_item.values:
                    data_dict[line_item.canonical_name] = line_item.values[year]

        # Create ExtractedFinancialData record with mapped fields
        extracted = ExtractedFinancialData(
            assessment_id=assessment_id,
            fiscal_year=year,
            is_confirmed=False,

            # Balance Sheet - Assets
            total_assets=data_dict.get('total_assets'),
            current_assets=data_dict.get('current_assets'),
            non_current_assets=data_dict.get('non_current_assets'),
            cash_and_equivalents=data_dict.get('cash_and_equivalents'),
            accounts_receivable=data_dict.get('accounts_receivable'),
            inventory=data_dict.get('inventory'),

            # Balance Sheet - Liabilities
            total_liabilities=data_dict.get('total_liabilities'),
            current_liabilities=data_dict.get('current_liabilities'),
            non_current_liabilities=data_dict.get('non_current_liabilities'),
            accounts_payable=data_dict.get('accounts_payable'),

            # Balance Sheet - Equity
            total_equity=data_dict.get('total_equity'),
            retained_earnings=data_dict.get('retained_earnings'),

            # Income Statement
            revenue=data_dict.get('revenue'),
            cost_of_sales=data_dict.get('cost_of_sales'),
            gross_profit=data_dict.get('gross_profit'),
            operating_expenses=data_dict.get('operating_expenses'),
            operating_income=data_dict.get('operating_income'),
            interest_expense=data_dict.get('interest_expense'),
            net_income=data_dict.get('net_income'),
            ebit=data_dict.get('operating_income'),  # EBIT = Operating Income

            # Cash Flow
            operating_cash_flow=data_dict.get('operating_cash_flow'),
            investing_cash_flow=data_dict.get('investing_cash_flow'),
            financing_cash_flow=data_dict.get('financing_cash_flow'),
            net_cash_flow=data_dict.get('net_cash_flow'),

            # Calculate working capital if components are available
            working_capital=(
                data_dict.get('current_assets', 0) - data_dict.get('current_liabilities', 0)
                if data_dict.get('current_assets') and data_dict.get('current_liabilities')
                else None
            )
        )

        db.add(extracted)
        logger.info(f"Created ExtractedFinancialData for fiscal year {year}")

    db.commit()
