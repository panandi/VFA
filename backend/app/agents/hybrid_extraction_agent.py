"""
Hybrid Extraction Agent
Tries Camelot first (text PDFs), falls back to LLM if needed (image PDFs)
"""

import logging
import time
from typing import Dict, Any
from sqlalchemy.orm import Session

from app.services.camelot_extractor import CamelotExtractor
from app.models.assessment import FinancialStatement
from app.models.financial_line_item import FinancialLineItem
from app.core.database import SessionLocal
from app.agents.camelot_integration_agent import run_camelot_extraction
from app.agents.extraction_agent_v2 import run_extraction_pipeline_v2

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def log_header(message: str):
    """Print a formatted header"""
    logger.info("=" * 80)
    logger.info(f"  {message}")
    logger.info("=" * 80)


def log_step(step_num: str, message: str):
    """Print a formatted step"""
    logger.info("")
    logger.info(f">>> STEP {step_num}: {message}")
    logger.info("-" * 80)


def log_success(message: str):
    """Print a success message"""
    logger.info(f"[SUCCESS] {message}")


def log_warning(message: str):
    """Print a warning message"""
    logger.warning(f"[WARNING] {message}")


def log_error(message: str):
    """Print an error message"""
    logger.error(f"[ERROR] {message}")


def log_info(message: str, indent=0):
    """Print an info message with optional indentation"""
    prefix = "  " * indent
    logger.info(f"{prefix}{message}")


async def run_hybrid_extraction(assessment_id: int, statement_id: int, file_path: str):
    """
    Hybrid extraction: Try Camelot first, fall back to LLM if needed

    - If PDF is text-based: Camelot extracts hierarchical data
    - If PDF is image-based: LLM extracts flat data
    - Populates both tables when possible
    """

    start_time = time.time()

    log_header("HYBRID EXTRACTION AGENT")
    log_info(f"Assessment ID: {assessment_id}")
    log_info(f"Statement ID: {statement_id}")
    log_info(f"File: {file_path}")
    log_info(f"Started at: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    db = SessionLocal()

    try:
        # Update statement status
        log_step("0", "Initializing extraction")
        log_info("Fetching statement from database...", indent=1)

        statement = db.query(FinancialStatement).filter(
            FinancialStatement.id == statement_id
        ).first()

        if not statement:
            log_error(f"Statement {statement_id} not found in database")
            return

        log_success(f"Statement found: {statement.filename}")
        log_info("Updating status to 'processing'...", indent=1)
        statement.processing_status = "processing"
        db.commit()
        log_success("Status updated successfully")

        # STEP 1: Try Camelot extraction
        log_step("1", "Attempting Camelot Extraction (Text-based PDFs)")
        log_info("Camelot is FREE and FAST for text-based PDFs", indent=1)
        log_info("Initializing Camelot extractor...", indent=1)

        camelot_start = time.time()
        extractor = CamelotExtractor(file_path)

        log_info("Scanning PDF for tables...", indent=1)
        statements = extractor.extract_all()
        camelot_time = time.time() - camelot_start

        camelot_success = len(statements) > 0

        log_info(f"Camelot scan completed in {camelot_time:.2f}s", indent=1)
        log_info(f"Found {len(statements)} statement type(s)", indent=1)

        if camelot_success:
            # Camelot succeeded - PDF is text-based
            log_success("Camelot successfully extracted financial data!")
            log_info("PDF Type: TEXT-BASED (digital)", indent=1)
            log_info("Extraction Method: Camelot (No LLM required)", indent=1)
            log_info("Data Format: HIERARCHICAL (tree structure)", indent=1)
            log_info("Cost: $0.00 (FREE)", indent=1)

            log_step("2", "Processing Camelot Results")

            # Show what was extracted
            for stmt in statements:
                log_info(f"Statement Type: {stmt.statement_type}", indent=1)
                log_info(f"  - Years detected: {sorted(stmt.years, reverse=True)}", indent=2)
                log_info(f"  - Line items: {len(stmt.line_items)}", indent=2)

            # Delete existing line items
            log_info("Clearing previous line items (if any)...", indent=1)
            deleted_count = db.query(FinancialLineItem).filter(
                FinancialLineItem.assessment_id == assessment_id
            ).delete()
            log_info(f"Deleted {deleted_count} old line items", indent=1)

            # Save line items from Camelot
            log_info("Saving hierarchical line items to database...", indent=1)
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

                        # Log progress every 50 items
                        if total_items % 50 == 0:
                            log_info(f"  Saved {total_items} items...", indent=2)

            db.commit()
            log_success(f"Saved {total_items} hierarchical line items to database")

            # Also populate ExtractedFinancialData from hierarchical data
            log_step("3", "Creating Flat Data (Backward Compatibility)")
            log_info("Populating ExtractedFinancialData table...", indent=1)

            from app.agents.camelot_integration_agent import _populate_extracted_data
            _populate_extracted_data(db, assessment_id, statements)

            log_success("Flat data table populated successfully")

            # Update statement status
            log_step("4", "Finalizing")
            statement.processing_status = "completed"
            statement.is_processed = True
            statement.error_message = None
            db.commit()

            elapsed = time.time() - start_time
            log_header("EXTRACTION COMPLETE")
            log_success(f"Hybrid extraction finished using CAMELOT")
            log_info(f"Total time: {elapsed:.2f} seconds")
            log_info(f"Line items extracted: {total_items}")
            log_info(f"Hierarchical view: AVAILABLE")
            log_info(f"Flat view: AVAILABLE")

        else:
            # Camelot failed - PDF is image-based, use LLM
            log_warning("Camelot found no financial tables")
            log_info("Reason: PDF appears to be IMAGE-BASED (scanned)", indent=1)
            log_info("Camelot limitation: Cannot read scanned/image PDFs", indent=1)

            log_step("2", "Falling Back to LLM Extraction")
            log_info("PDF Type: IMAGE-BASED (scanned)", indent=1)
            log_info("Extraction Method: LLM with OCR (AI-powered)", indent=1)
            log_info("Data Format: FLAT (table format)", indent=1)
            log_info("Cost: ~$0.10-0.50 per PDF", indent=1)
            log_info("Processing time: 30-60 seconds", indent=1)

            log_info("Closing database connection...", indent=1)
            db.close()  # Close before async call

            log_info("Initiating LLM extraction pipeline...", indent=1)
            llm_start = time.time()

            # Use LLM extraction
            await run_extraction_pipeline_v2(
                assessment_id=assessment_id,
                statement_id=statement_id,
                file_path=file_path
            )

            llm_time = time.time() - llm_start
            elapsed = time.time() - start_time

            log_header("EXTRACTION COMPLETE")
            log_success(f"Hybrid extraction finished using LLM (fallback)")
            log_info(f"LLM extraction time: {llm_time:.2f} seconds")
            log_info(f"Total time: {elapsed:.2f} seconds")
            log_info(f"Hierarchical view: NOT AVAILABLE (image PDF)")
            log_info(f"Flat view: AVAILABLE")
            log_warning("To get hierarchical data, upload a text-based PDF")

    except Exception as e:
        log_error(f"Hybrid extraction failed: {str(e)}")
        log_info("Exception details:", indent=1)

        import traceback
        for line in traceback.format_exc().split('\n'):
            if line.strip():
                log_info(line, indent=2)

        # Update statement with error
        try:
            if not db.is_active:
                db = SessionLocal()

            statement = db.query(FinancialStatement).filter(
                FinancialStatement.id == statement_id
            ).first()

            if statement:
                log_info("Updating statement status to 'error'...", indent=1)
                statement.processing_status = "error"
                statement.error_message = str(e)
                statement.is_processed = True
                db.commit()
                log_success("Error status saved to database")
        except Exception as db_error:
            log_error(f"Failed to update error status: {str(db_error)}")

    finally:
        try:
            if db and db.is_active:
                db.close()
                log_info("Database connection closed")
        except:
            pass

        log_header("HYBRID EXTRACTION AGENT - END")
        log_info("=" * 80)
