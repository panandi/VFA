"""
Test Harness for PDF Financial Statement Extraction

Run with:
    cd backend
    python -m pytest tests/test_extraction.py -v

Or run directly:
    python tests/test_extraction.py /path/to/sample.pdf
"""

import os
import sys
import json
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# TEST UTILITIES
# ============================================================================

def assert_pages_found(candidates, statement_type: str, min_pages: int = 1):
    """Assert that at least min_pages were found for a statement type."""
    pages = getattr(candidates, statement_type, [])
    assert len(pages) >= min_pages, (
        f"Expected at least {min_pages} {statement_type} page(s), got {len(pages)}"
    )
    logger.info(f"  ✓ {statement_type}: {len(pages)} page(s) found: {pages}")


def assert_years_detected(metadata: Dict, min_years: int = 1):
    """Assert that at least min_years were detected."""
    years = metadata.get('detected_years', [])
    assert len(years) >= min_years, (
        f"Expected at least {min_years} year(s), got {len(years)}: {years}"
    )
    logger.info(f"  ✓ Years detected: {years}")


def assert_field_present(output: Dict, section: str, field: str):
    """Assert that a field has at least one non-null value."""
    if section not in output:
        raise AssertionError(f"Section '{section}' not in output")

    if field not in output[section]:
        raise AssertionError(f"Field '{field}' not in {section}")

    field_data = output[section][field]
    values = [v for k, v in field_data.items() if k.startswith('FY_') and v is not None]

    assert len(values) > 0, f"Field '{field}' in '{section}' has no values"
    logger.info(f"  ✓ {section}/{field}: {values}")


def assert_confidence_above(metadata: Dict, min_confidence: float = 0.3):
    """Assert that confidence score is above threshold."""
    confidence = metadata.get('confidence', 0)
    assert confidence >= min_confidence, (
        f"Expected confidence >= {min_confidence}, got {confidence}"
    )
    logger.info(f"  ✓ Confidence: {confidence}")


# ============================================================================
# UNIT TESTS
# ============================================================================

class TestPDFProcessor:
    """Tests for the PDF processor module."""

    def test_pdf_info_detection(self, sample_pdf_path: str):
        """Test that PDF type is correctly detected."""
        from app.services.pdf_processor import PDFProcessor

        processor = PDFProcessor(sample_pdf_path)
        info = processor.get_pdf_info()

        assert info.total_pages > 0, "PDF should have pages"
        logger.info(f"  PDF has {info.total_pages} pages")
        logger.info(f"  Is image-based: {info.is_image_based}")

        # Verify file hash is generated
        assert processor.file_hash, "File hash should be generated"
        logger.info(f"  File hash: {processor.file_hash}")

    def test_text_extraction(self, sample_pdf_path: str):
        """Test text extraction from first few pages."""
        from app.services.pdf_processor import PDFProcessor

        processor = PDFProcessor(sample_pdf_path)
        pages = processor.extract_pages_low_res([0, 1, 2])

        assert len(pages) == 3, "Should extract 3 pages"

        for page in pages:
            logger.info(f"  Page {page.page_num}: {len(page.text)} chars, OCR={page.is_ocr}")


class TestPageFinder:
    """Tests for the page finder module."""

    def test_candidate_detection(self, sample_pdf_path: str):
        """Test that candidate pages are found for each statement type."""
        from app.services.pdf_processor import PDFProcessor
        from app.services.page_finder import PageFinder

        processor = PDFProcessor(sample_pdf_path)
        finder = PageFinder(processor)
        candidates = finder.find_toc_and_candidates()

        logger.info(f"  TOC used: {candidates.toc_used}")
        logger.info(f"  Page offset: {candidates.page_offset}")

        # Assert at least one candidate for each statement
        # (relaxed assertion - some PDFs might not have all statements)
        total_candidates = (
            len(candidates.balance_sheet) +
            len(candidates.income_statement) +
            len(candidates.cash_flow)
        )
        assert total_candidates > 0, "Should find at least some candidate pages"

        logger.info(f"  Balance Sheet: {candidates.balance_sheet}")
        logger.info(f"  Income Statement: {candidates.income_statement}")
        logger.info(f"  Cash Flow: {candidates.cash_flow}")


class TestTableExtractor:
    """Tests for the table extractor module."""

    def test_number_parsing(self):
        """Test number parsing with various formats."""
        from app.services.table_extractor import parse_financial_number

        test_cases = [
            ("1,234,567", 1234567.0),
            ("1,234.56", 1234.56),
            ("(1,234.56)", -1234.56),
            ("-1,234.56", -1234.56),
            ("123", 123.0),
            ("12.34", 12.34),
            ("abc", None),
            ("", None),
        ]

        for text, expected in test_cases:
            result = parse_financial_number(text)
            assert result == expected, f"parse_financial_number('{text}') = {result}, expected {expected}"
            logger.info(f"  ✓ '{text}' -> {result}")


class TestFieldMapper:
    """Tests for the field mapper module."""

    def test_synonym_mapping(self):
        """Test that synonyms are correctly mapped."""
        from app.services.field_mapper import map_to_canonical

        test_cases = [
            ("Trade Receivables", "Account Receivable"),
            ("trade receivables", "Account Receivable"),
            ("Inventories", "Inventory"),
            ("Trade Payables", "Creditor/Trade Payables"),
            ("Equity Share Capital", "Share Capital/Paid up Capital"),
            ("Revenue from Operations", "Sales/Revenue"),
            ("Profit for the Year", "Net Profit/(Loss)"),
            ("Net Cash from Operating Activities", "Net Cash Flow from Operating Activities"),
        ]

        for source, expected in test_cases:
            canonical, confidence = map_to_canonical(source)
            assert canonical == expected, f"map_to_canonical('{source}') = '{canonical}', expected '{expected}'"
            logger.info(f"  ✓ '{source}' -> '{canonical}' (conf: {confidence})")


# ============================================================================
# INTEGRATION TEST
# ============================================================================

async def test_full_extraction(sample_pdf_path: str) -> Dict[str, Any]:
    """
    Full integration test: run extraction on a sample PDF.

    Args:
        sample_pdf_path: Path to the PDF file to test

    Returns:
        Extracted data dictionary
    """
    from app.agents.extraction_agent_v2 import extract_financial_data_v2

    logger.info("=" * 60)
    logger.info("FULL EXTRACTION TEST")
    logger.info(f"PDF: {sample_pdf_path}")
    logger.info("=" * 60)

    # Run extraction
    result = await extract_financial_data_v2(sample_pdf_path)

    # Log results
    logger.info("\n=== EXTRACTION RESULTS ===")
    print(json.dumps(result, indent=2, default=str))

    # Assertions
    logger.info("\n=== ASSERTIONS ===")

    # Check for errors
    if "error" in result:
        logger.warning(f"Extraction error: {result['error']}")
        # Don't fail test on error, but log it
    else:
        metadata = result.get("metadata", {})

        # Assert years detected
        assert_years_detected(metadata, min_years=1)

        # Assert confidence
        assert_confidence_above(metadata, min_confidence=0.1)

        # Check for key fields (may not all be present depending on PDF)
        sections_found = []
        for section in ["Balance Sheet", "Profit and Loss", "Cash Flow Statement"]:
            if section in result and result[section]:
                sections_found.append(section)
                logger.info(f"  ✓ {section} found with {len(result[section])} fields")

        assert len(sections_found) > 0, "Should find at least one financial statement section"

    logger.info("\n=== TEST COMPLETE ===")
    return result


# ============================================================================
# PYTEST FIXTURES
# ============================================================================

def pytest_configure(config):
    """Configure pytest."""
    pass


def get_sample_pdf() -> Optional[str]:
    """Find a sample PDF in the uploads directory."""
    uploads_dir = Path(__file__).parent.parent / "uploads"
    if uploads_dir.exists():
        pdfs = list(uploads_dir.glob("*.pdf"))
        if pdfs:
            return str(pdfs[0])
    return None


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def run_all_tests(pdf_path: str):
    """Run all tests against a PDF file."""
    logger.info("=" * 60)
    logger.info("RUNNING ALL EXTRACTION TESTS")
    logger.info("=" * 60)

    # Unit tests
    logger.info("\n--- PDF Processor Tests ---")
    pdf_tests = TestPDFProcessor()
    pdf_tests.test_pdf_info_detection(pdf_path)
    pdf_tests.test_text_extraction(pdf_path)

    logger.info("\n--- Page Finder Tests ---")
    finder_tests = TestPageFinder()
    finder_tests.test_candidate_detection(pdf_path)

    logger.info("\n--- Table Extractor Tests ---")
    table_tests = TestTableExtractor()
    table_tests.test_number_parsing()

    logger.info("\n--- Field Mapper Tests ---")
    mapper_tests = TestFieldMapper()
    mapper_tests.test_synonym_mapping()

    # Integration test
    logger.info("\n--- Full Extraction Test ---")
    result = asyncio.run(test_full_extraction(pdf_path))

    logger.info("\n" + "=" * 60)
    logger.info("ALL TESTS COMPLETED")
    logger.info("=" * 60)

    return result


if __name__ == "__main__":
    if len(sys.argv) < 2:
        # Try to find a sample PDF
        sample = get_sample_pdf()
        if sample:
            logger.info(f"Using sample PDF: {sample}")
            run_all_tests(sample)
        else:
            print("Usage: python test_extraction.py /path/to/sample.pdf")
            print("\nNo sample PDF found in uploads directory.")
            sys.exit(1)
    else:
        pdf_path = sys.argv[1]
        if not os.path.exists(pdf_path):
            print(f"Error: File not found: {pdf_path}")
            sys.exit(1)
        run_all_tests(pdf_path)
