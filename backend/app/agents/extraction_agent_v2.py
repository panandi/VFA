"""
Financial Data Extraction Agent v2

Major improvements over v1:
- 2-pass approach: low-res candidate detection, high-res extraction
- OCR support for image-based/scanned PDFs
- Automatic rotation detection and correction
- TOC parsing to jump directly to statement pages
- Shared page index (scan once, route to multiple statement types)
- Source evidence (page number + raw row text) for each field
- Robust synonym mapping to canonical fields
- Better debugging and logging

Usage:
    from app.agents.extraction_agent_v2 import run_extraction_pipeline_v2
    await run_extraction_pipeline_v2(assessment_id, statement_id, file_path)
"""

import json
import re
import logging
import asyncio
import time
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime
from dataclasses import dataclass, field, asdict
from openai import AsyncOpenAI
import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.assessment import FinancialStatement, ExtractedFinancialData

# New modules
from app.services.pdf_processor import PDFProcessor, PDFInfo, PageData
from app.services.page_finder import PageFinder, CandidatePages
from app.services.table_extractor import TableExtractor
from app.services.field_mapper import (
    FieldMapper, map_to_canonical,
    BALANCE_SHEET_SYNONYMS, PROFIT_LOSS_SYNONYMS, CASH_FLOW_SYNONYMS
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global progress tracking
extraction_progress = {}


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class ExtractionMetadata:
    """Metadata about the extraction process."""
    company: Optional[str] = None
    currency: Optional[str] = None
    scale: Optional[str] = None  # 'lakhs', 'crores', 'thousands', 'millions'
    detected_years: List[int] = field(default_factory=list)
    confidence: float = 0.0
    is_image_based: bool = False
    toc_used: bool = False
    debug: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SourceEvidence:
    """Source evidence for an extracted value."""
    page: int
    row: str
    confidence: float = 1.0


@dataclass
class ExtractedValue:
    """A single extracted value with source evidence."""
    value: Optional[float]
    source: Optional[SourceEvidence] = None


# ============================================================================
# LLM PROMPTS
# ============================================================================

EXTRACTION_SYSTEM_PROMPT = """You are a financial data extraction expert. Extract financial data from the provided text.

IMPORTANT RULES:
1. Extract ALL fiscal years shown in the data (usually 2-3 comparative years)
2. Look for scale indicators: "₹ in lakhs", "₹ in crores", "in thousands", "in millions"
3. Handle negative numbers in parentheses: (1,234.56) = -1234.56
4. Use exact terminology mappings provided
5. Return null for fields not found - NEVER guess
6. Include page numbers from [Page N] markers in source evidence
7. Prefer consolidated statements over standalone if both exist

TERMINOLOGY MAPPINGS:
- Trade Receivables / Debtors / Sundry Debtors → Account Receivable
- Inventories / Stock-in-Trade → Inventory
- Trade Payables / Sundry Creditors → Creditor/Trade Payables
- Equity Share Capital / Paid-up Capital → Share Capital/Paid up Capital
- Other Equity / Reserves & Surplus → may contain Retained Earnings (note in debug if not explicit)
- Revenue from Operations / Sales / Turnover → Sales/Revenue
- Profit for the Year / PAT / Net Profit → Net Profit/(Loss)

Return ONLY valid JSON in this exact format:"""

BALANCE_SHEET_PROMPT = EXTRACTION_SYSTEM_PROMPT + """
{
  "statement_type": "balance_sheet",
  "scale": "<lakhs|crores|thousands|millions|null>",
  "currency": "<INR|USD|null>",
  "fiscal_years": [
    {
      "year": 2023,
      "data": {
        "Current Assets": {"value": <number|null>, "source_row": "<exact row text>", "page": <page_num>},
        "Account Receivable": {"value": <number|null>, "source_row": "<exact row text>", "page": <page_num>},
        "Inventory": {"value": <number|null>, "source_row": "<exact row text>", "page": <page_num>},
        "Total Assets": {"value": <number|null>, "source_row": "<exact row text>", "page": <page_num>},
        "Current Liabilities": {"value": <number|null>, "source_row": "<exact row text>", "page": <page_num>},
        "Creditor/Trade Payables": {"value": <number|null>, "source_row": "<exact row text>", "page": <page_num>},
        "Total Liabilities": {"value": <number|null>, "source_row": "<exact row text>", "page": <page_num>},
        "Share Capital/Paid up Capital": {"value": <number|null>, "source_row": "<exact row text>", "page": <page_num>},
        "Retained Earnings": {"value": <number|null>, "source_row": "<exact row text>", "page": <page_num>},
        "Equity": {"value": <number|null>, "source_row": "<exact row text>", "page": <page_num>},
        "Cash and Cash Equivalents": {"value": <number|null>, "source_row": "<exact row text>", "page": <page_num>}
      },
      "debug_notes": "<any notes about Other Equity, missing fields, etc.>"
    }
  ]
}"""

INCOME_STATEMENT_PROMPT = EXTRACTION_SYSTEM_PROMPT + """
{
  "statement_type": "income_statement",
  "scale": "<lakhs|crores|thousands|millions|null>",
  "currency": "<INR|USD|null>",
  "fiscal_years": [
    {
      "year": 2023,
      "data": {
        "Sales/Revenue": {"value": <number|null>, "source_row": "<exact row text>", "page": <page_num>},
        "Cost of Sales": {"value": <number|null>, "source_row": "<exact row text>", "page": <page_num>},
        "Gross Profit": {"value": <number|null>, "source_row": "<exact row text>", "page": <page_num>},
        "EBIT": {"value": <number|null>, "source_row": "<exact row text>", "page": <page_num>},
        "Net Profit/(Loss)": {"value": <number|null>, "source_row": "<exact row text>", "page": <page_num>},
        "Interest Expense": {"value": <number|null>, "source_row": "<exact row text>", "page": <page_num>},
        "Depreciation": {"value": <number|null>, "source_row": "<exact row text>", "page": <page_num>}
      },
      "debug_notes": "<any notes>"
    }
  ]
}"""

CASH_FLOW_PROMPT = EXTRACTION_SYSTEM_PROMPT + """
{
  "statement_type": "cash_flow",
  "scale": "<lakhs|crores|thousands|millions|null>",
  "currency": "<INR|USD|null>",
  "fiscal_years": [
    {
      "year": 2023,
      "data": {
        "Net Cash Flow from Operating Activities": {"value": <number|null>, "source_row": "<exact row text>", "page": <page_num>},
        "Net Cash Flow from Investing Activities": {"value": <number|null>, "source_row": "<exact row text>", "page": <page_num>},
        "Net Cash Flow from Financing Activities": {"value": <number|null>, "source_row": "<exact row text>", "page": <page_num>},
        "Cash and Cash Equivalent at end of fiscal year": {"value": <number|null>, "source_row": "<exact row text>", "page": <page_num>}
      },
      "debug_notes": "<any notes>"
    }
  ]
}"""


# ============================================================================
# EXTRACTION FUNCTIONS
# ============================================================================

def update_progress(
    assessment_id: int,
    stage: str,
    current: int = 0,
    total: int = 0,
    statement_type: str = ""
):
    """Update global progress tracker."""
    if assessment_id:
        extraction_progress[assessment_id] = {
            'stage': stage,
            'current_page': current,
            'total_pages': total,
            'statement_type': statement_type,
            'timestamp': time.time()
        }


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(Exception),
    reraise=True
)
async def extract_with_llm(
    client: AsyncOpenAI,
    text: str,
    prompt: str,
    statement_type: str
) -> Dict[str, Any]:
    """Extract data using LLM with retry logic."""
    try:
        logger.info(f"Calling LLM for {statement_type} ({len(text)} chars)...")

        response = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"Extract {statement_type} data:\n\n{text}"}
            ],
            temperature=0,
            max_tokens=2000,
            response_format={"type": "json_object"}
        )

        content = response.choices[0].message.content
        result = json.loads(content)

        years = [fy.get('year') for fy in result.get('fiscal_years', [])]
        logger.info(f"  ✓ {statement_type}: extracted {len(years)} year(s): {years}")

        return result

    except json.JSONDecodeError as e:
        logger.error(f"  ✗ {statement_type} JSON parse error: {e}")
        raise
    except Exception as e:
        logger.error(f"  ✗ {statement_type} extraction error: {e}")
        raise


class ExtractionPipelineV2:
    """
    Main extraction pipeline with 2-pass approach.
    """

    def __init__(self, file_path: str, assessment_id: int = None):
        self.file_path = file_path
        self.assessment_id = assessment_id
        self.processor = PDFProcessor(file_path)
        self.finder = PageFinder(self.processor)
        self.table_extractor = TableExtractor()
        self.field_mapper = FieldMapper()

        # Create HTTP client with SSL verification disabled for corporate proxy
        http_client = httpx.AsyncClient(
            verify=False,
            timeout=httpx.Timeout(60.0, connect=10.0)
        )
        self.client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            http_client=http_client
        )

        # Results
        self.pdf_info: Optional[PDFInfo] = None
        self.candidates: Optional[CandidatePages] = None
        self.metadata = ExtractionMetadata()

    def _progress_callback(self, current: int, total: int, stage: str):
        """Callback for progress updates."""
        update_progress(
            self.assessment_id,
            stage=stage,
            current=current,
            total=total
        )
        if current % 10 == 0 or current == total:
            logger.info(f"  [{current}/{total}] {stage}...")

    async def run(self) -> Dict[str, Any]:
        """
        Run the full extraction pipeline.

        Returns structured JSON with:
        - Balance Sheet data
        - Profit and Loss data
        - Cash Flow Statement data
        - Metadata (company, currency, scale, years, confidence, debug)
        """
        logger.info("=" * 80)
        logger.info(f"EXTRACTION PIPELINE V2: {self.file_path}")
        logger.info("=" * 80)

        start_time = time.time()

        # ===== PASS 0: Analyze PDF =====
        logger.info("\n=== PASS 0: PDF Analysis ===")
        self.pdf_info = self.processor.get_pdf_info()
        self.metadata.is_image_based = self.pdf_info.is_image_based

        logger.info(f"  Total pages: {self.pdf_info.total_pages}")
        logger.info(f"  Is image-based (needs OCR): {self.pdf_info.is_image_based}")

        if self.pdf_info.is_image_based:
            logger.warning("  ⚠ PDF has no text layer - OCR will be used (slower)")

        # ===== PASS A: Find Candidate Pages =====
        logger.info("\n=== PASS A: Candidate Detection ===")
        update_progress(self.assessment_id, 'scanning', 0, self.pdf_info.total_pages)

        self.candidates = self.finder.find_toc_and_candidates(
            progress_callback=self._progress_callback
        )
        self.metadata.toc_used = self.candidates.toc_used

        if self.candidates.toc_used:
            logger.info("  ✓ Using TOC-based page selection")
        else:
            logger.info("  ℹ Using keyword-based page selection (no TOC found)")

        # Log candidate pages
        logger.info(f"  Balance Sheet pages: {self.candidates.balance_sheet}")
        logger.info(f"  Income Statement pages: {self.candidates.income_statement}")
        logger.info(f"  Cash Flow pages: {self.candidates.cash_flow}")

        # Check if we found any candidates
        if not any([
            self.candidates.balance_sheet,
            self.candidates.income_statement,
            self.candidates.cash_flow
        ]):
            logger.error("  ✗ No financial statement pages found!")
            return {
                "error": "No financial data found in PDF",
                "metadata": asdict(self.metadata)
            }

        # ===== PASS B: High-Res Extraction =====
        logger.info("\n=== PASS B: High-Res Extraction ===")
        update_progress(self.assessment_id, 'extracting')

        # Get unique candidate pages
        all_candidate_pages = sorted(set(
            self.candidates.balance_sheet +
            self.candidates.income_statement +
            self.candidates.cash_flow
        ))

        logger.info(f"  Extracting {len(all_candidate_pages)} unique candidate pages...")

        # Extract text from candidate pages (high-res if OCR needed)
        page_texts = {}
        if self.pdf_info.is_image_based:
            pages = self.processor.extract_pages_high_res(
                all_candidate_pages,
                detect_tables=True
            )
        else:
            pages = self.processor.extract_pages_low_res(all_candidate_pages)

        for page in pages:
            page_texts[page.page_num] = page.text
            logger.info(f"    Page {page.page_num}: {len(page.text)} chars")

        # Build combined text for each statement type
        def build_statement_text(page_nums: List[int]) -> str:
            texts = []
            for pn in sorted(page_nums):
                if pn in page_texts and page_texts[pn]:
                    texts.append(f"[Page {pn}]\n{page_texts[pn]}")
            return "\n\n".join(texts)

        bs_text = build_statement_text(self.candidates.balance_sheet)
        is_text = build_statement_text(self.candidates.income_statement)
        cf_text = build_statement_text(self.candidates.cash_flow)

        # ===== LLM Extraction (Parallel) =====
        logger.info("\n=== LLM Extraction (Parallel) ===")
        update_progress(self.assessment_id, 'llm_extraction')

        tasks = []
        if bs_text:
            tasks.append(extract_with_llm(
                self.client, bs_text, BALANCE_SHEET_PROMPT, "Balance Sheet"
            ))
        else:
            tasks.append(asyncio.coroutine(lambda: {"fiscal_years": []})())
            logger.warning("  ⚠ No Balance Sheet text to extract")

        if is_text:
            tasks.append(extract_with_llm(
                self.client, is_text, INCOME_STATEMENT_PROMPT, "Income Statement"
            ))
        else:
            tasks.append(asyncio.coroutine(lambda: {"fiscal_years": []})())
            logger.warning("  ⚠ No Income Statement text to extract")

        if cf_text:
            tasks.append(extract_with_llm(
                self.client, cf_text, CASH_FLOW_PROMPT, "Cash Flow"
            ))
        else:
            tasks.append(asyncio.coroutine(lambda: {"fiscal_years": []})())
            logger.warning("  ⚠ No Cash Flow text to extract")

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        bs_result = results[0] if not isinstance(results[0], Exception) else {"fiscal_years": []}
        is_result = results[1] if not isinstance(results[1], Exception) else {"fiscal_years": []}
        cf_result = results[2] if not isinstance(results[2], Exception) else {"fiscal_years": []}

        for i, (name, result) in enumerate([
            ("Balance Sheet", results[0]),
            ("Income Statement", results[1]),
            ("Cash Flow", results[2])
        ]):
            if isinstance(result, Exception):
                logger.error(f"  ✗ {name} extraction failed: {result}")

        # ===== Merge Results =====
        logger.info("\n=== Merging Results ===")
        final_output = self._merge_results(bs_result, is_result, cf_result)

        # Add debug info
        self.metadata.debug = {
            "statement_pages": {
                "balance_sheet": self.candidates.balance_sheet,
                "profit_and_loss": self.candidates.income_statement,
                "cash_flow": self.candidates.cash_flow
            },
            "toc_entries": [
                {"title": e.title, "page": e.printed_page, "type": e.statement_type}
                for e in self.finder.toc_entries
            ] if self.finder.toc_entries else [],
            "page_offset": self.candidates.page_offset,
            "extraction_time_seconds": round(time.time() - start_time, 2)
        }

        final_output["metadata"] = asdict(self.metadata)

        # Calculate confidence
        self._calculate_confidence(final_output)

        elapsed = time.time() - start_time
        logger.info(f"\n=== EXTRACTION COMPLETE ({elapsed:.1f}s) ===")
        logger.info(f"  Years detected: {self.metadata.detected_years}")
        logger.info(f"  Confidence: {self.metadata.confidence:.2f}")

        return final_output

    def _merge_results(
        self,
        bs_result: Dict,
        is_result: Dict,
        cf_result: Dict
    ) -> Dict[str, Any]:
        """Merge results from all three statement extractions."""

        # Collect all years
        all_years = set()
        for result in [bs_result, is_result, cf_result]:
            for fy in result.get('fiscal_years', []):
                if fy.get('year'):
                    all_years.add(fy['year'])

        self.metadata.detected_years = sorted(all_years, reverse=True)

        # Collect scale/currency from first non-null
        for result in [bs_result, is_result, cf_result]:
            if result.get('scale') and not self.metadata.scale:
                self.metadata.scale = result['scale']
            if result.get('currency') and not self.metadata.currency:
                self.metadata.currency = result['currency']

        # Build output structure
        output = {
            "Balance Sheet": {},
            "Profit and Loss": {},
            "Cash Flow Statement": {},
        }

        # Helper to extract field data
        def extract_field(result: Dict, field_name: str) -> Dict:
            field_data = {}
            for fy in result.get('fiscal_years', []):
                year = fy.get('year')
                if not year:
                    continue

                data = fy.get('data', {})
                if field_name in data:
                    field_info = data[field_name]
                    if isinstance(field_info, dict):
                        field_data[f"FY_{year}"] = field_info.get('value')
                        if 'source_row' in field_info:
                            field_data['source'] = {
                                'page': field_info.get('page', 0),
                                'row': field_info.get('source_row', '')
                            }
                    else:
                        field_data[f"FY_{year}"] = field_info

            field_data['unit'] = self.metadata.scale
            return field_data

        # Balance Sheet fields
        bs_fields = [
            "Current Assets", "Account Receivable", "Inventory", "Total Assets",
            "Current Liabilities", "Creditor/Trade Payables", "Total Liabilities",
            "Share Capital/Paid up Capital", "Retained Earnings", "Equity",
            "Cash and Cash Equivalents"
        ]
        for field in bs_fields:
            field_data = extract_field(bs_result, field)
            if any(v is not None for k, v in field_data.items() if k.startswith('FY_')):
                output["Balance Sheet"][field] = field_data

        # P&L fields
        pl_fields = [
            "Sales/Revenue", "Cost of Sales", "Gross Profit", "EBIT",
            "Net Profit/(Loss)", "Interest Expense", "Depreciation"
        ]
        for field in pl_fields:
            field_data = extract_field(is_result, field)
            if any(v is not None for k, v in field_data.items() if k.startswith('FY_')):
                output["Profit and Loss"][field] = field_data

        # Cash Flow fields
        cf_fields = [
            "Net Cash Flow from Operating Activities",
            "Net Cash Flow from Investing Activities",
            "Net Cash Flow from Financing Activities",
            "Cash and Cash Equivalent at end of fiscal year"
        ]
        for field in cf_fields:
            field_data = extract_field(cf_result, field)
            if any(v is not None for k, v in field_data.items() if k.startswith('FY_')):
                output["Cash Flow Statement"][field] = field_data

        return output

    def _calculate_confidence(self, output: Dict):
        """Calculate overall extraction confidence."""
        total_fields = 0
        filled_fields = 0

        # Critical fields
        critical_fields = [
            ("Balance Sheet", "Total Assets"),
            ("Balance Sheet", "Total Liabilities"),
            ("Balance Sheet", "Equity"),
            ("Profit and Loss", "Sales/Revenue"),
            ("Profit and Loss", "Net Profit/(Loss)"),
            ("Cash Flow Statement", "Net Cash Flow from Operating Activities"),
        ]

        critical_found = 0
        for section, field in critical_fields:
            if section in output and field in output[section]:
                field_data = output[section][field]
                if any(v is not None for k, v in field_data.items() if k.startswith('FY_')):
                    critical_found += 1

        # Count all fields
        for section in ["Balance Sheet", "Profit and Loss", "Cash Flow Statement"]:
            if section in output:
                for field, data in output[section].items():
                    total_fields += 1
                    if any(v is not None for k, v in data.items() if k.startswith('FY_')):
                        filled_fields += 1

        # Weighted confidence: 70% critical, 30% completeness
        critical_score = critical_found / len(critical_fields) if critical_fields else 0
        completeness_score = filled_fields / total_fields if total_fields > 0 else 0

        self.metadata.confidence = round(0.7 * critical_score + 0.3 * completeness_score, 2)


# ============================================================================
# LEGACY FIELD CONVERSION
# ============================================================================

def convert_to_legacy_format(output: Dict) -> Dict:
    """
    Convert new output format to legacy format expected by database.

    Legacy format uses snake_case field names like:
    - total_assets, current_assets, revenue, net_income, etc.
    """
    field_mapping = {
        # Balance Sheet
        "Current Assets": "current_assets",
        "Account Receivable": "accounts_receivable",
        "Inventory": "inventory",
        "Total Assets": "total_assets",
        "Current Liabilities": "current_liabilities",
        "Creditor/Trade Payables": "accounts_payable",
        "Total Liabilities": "total_liabilities",
        "Share Capital/Paid up Capital": "share_capital",
        "Retained Earnings": "retained_earnings",
        "Equity": "total_equity",
        "Cash and Cash Equivalents": "cash_and_equivalents",
        # P&L
        "Sales/Revenue": "revenue",
        "Cost of Sales": "cost_of_sales",
        "Gross Profit": "gross_profit",
        "EBIT": "ebit",
        "Net Profit/(Loss)": "net_income",
        "Interest Expense": "interest_expense",
        "Depreciation": "depreciation",
        # Cash Flow
        "Net Cash Flow from Operating Activities": "operating_cash_flow",
        "Net Cash Flow from Investing Activities": "investing_cash_flow",
        "Net Cash Flow from Financing Activities": "financing_cash_flow",
        "Cash and Cash Equivalent at end of fiscal year": "net_cash_flow",
    }

    # Collect data by year
    years_data = {}
    metadata = output.get("metadata", {})
    detected_years = metadata.get("detected_years", [])

    for year in detected_years:
        years_data[year] = {}

    # Extract values for each year
    for section in ["Balance Sheet", "Profit and Loss", "Cash Flow Statement"]:
        if section not in output:
            continue
        for field_name, field_data in output[section].items():
            legacy_name = field_mapping.get(field_name)
            if not legacy_name:
                continue

            for key, value in field_data.items():
                if key.startswith("FY_"):
                    year = int(key.replace("FY_", ""))
                    if year in years_data:
                        years_data[year][legacy_name] = value

    # Build fiscal_years structure
    fiscal_years = []
    for year in sorted(years_data.keys(), reverse=True):
        fiscal_years.append({
            "year": year,
            "data": years_data[year],
            "confidence": metadata.get("confidence", 0.0)
        })

    return {"fiscal_years": fiscal_years}


# ============================================================================
# DATABASE STORAGE
# ============================================================================

def derive_missing_fields(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Derive missing fields that can be calculated from other fields.
    This ensures Z-Score components can be calculated even when some
    fields aren't explicitly extracted.
    """
    derived = data.copy()

    # 1. Working Capital = Current Assets - Current Liabilities
    if derived.get('working_capital') is None:
        ca = derived.get('current_assets')
        cl = derived.get('current_liabilities')
        if ca is not None and cl is not None:
            derived['working_capital'] = ca - cl
            logger.info(f"  Derived working_capital: {derived['working_capital']}")

    # 2. Non-Current Assets = Total Assets - Current Assets
    if derived.get('non_current_assets') is None:
        ta = derived.get('total_assets')
        ca = derived.get('current_assets')
        if ta is not None and ca is not None:
            derived['non_current_assets'] = ta - ca
            logger.info(f"  Derived non_current_assets: {derived['non_current_assets']}")

    # 3. Non-Current Liabilities = Total Liabilities - Current Liabilities
    if derived.get('non_current_liabilities') is None:
        tl = derived.get('total_liabilities')
        cl = derived.get('current_liabilities')
        if tl is not None and cl is not None:
            derived['non_current_liabilities'] = tl - cl
            logger.info(f"  Derived non_current_liabilities: {derived['non_current_liabilities']}")

    # 4. Total Equity = Total Assets - Total Liabilities (if not extracted)
    if derived.get('total_equity') is None:
        ta = derived.get('total_assets')
        tl = derived.get('total_liabilities')
        if ta is not None and tl is not None:
            derived['total_equity'] = ta - tl
            logger.info(f"  Derived total_equity: {derived['total_equity']}")

    # 5. Retained Earnings estimation (if not extracted)
    # Retained Earnings ≈ Total Equity - Share Capital
    # This is a common approximation when RE isn't explicitly stated
    if derived.get('retained_earnings') is None:
        te = derived.get('total_equity')
        sc = derived.get('share_capital')
        if te is not None and sc is not None:
            derived['retained_earnings'] = te - sc
            logger.info(f"  Derived retained_earnings (from equity - share_capital): {derived['retained_earnings']}")

    # 6. Gross Profit = Revenue - Cost of Sales
    if derived.get('gross_profit') is None:
        rev = derived.get('revenue')
        cos = derived.get('cost_of_sales')
        if rev is not None and cos is not None:
            derived['gross_profit'] = rev - cos
            logger.info(f"  Derived gross_profit: {derived['gross_profit']}")

    # 7. EBIT estimation (if not extracted)
    # EBIT ≈ Net Income + Interest Expense (simplified - ignores tax)
    # Better: EBIT = Operating Income
    if derived.get('ebit') is None:
        if derived.get('operating_income') is not None:
            derived['ebit'] = derived['operating_income']
            logger.info(f"  Derived ebit from operating_income: {derived['ebit']}")
        else:
            ni = derived.get('net_income')
            ie = derived.get('interest_expense') or 0
            if ni is not None:
                # Note: This is approximate. Actual EBIT = Net Income + Interest + Tax
                derived['ebit'] = ni + ie
                logger.info(f"  Derived ebit (approx: net_income + interest): {derived['ebit']}")

    # 8. EBITDA = EBIT + Depreciation + Amortization
    if derived.get('ebitda') is None:
        ebit = derived.get('ebit')
        dep = derived.get('depreciation') or 0
        if ebit is not None:
            derived['ebitda'] = ebit + dep
            logger.info(f"  Derived ebitda: {derived['ebitda']}")

    return derived


async def store_results_v2(
    assessment_id: int,
    statement_id: int,
    extracted: Dict[str, Any],
    error: str = ""
):
    """Store extracted data in database."""
    db = SessionLocal()
    try:
        # Update statement status
        statement = db.query(FinancialStatement).filter(
            FinancialStatement.id == statement_id
        ).first()

        if statement:
            statement.is_processed = True
            statement.processing_status = "completed" if not error else "error"
            if error:
                statement.error_message = error

        # Convert to legacy format for DB storage
        legacy = convert_to_legacy_format(extracted)

        # Store each fiscal year
        for fy in legacy.get("fiscal_years", []):
            data = fy.get("data", {})
            year = fy.get("year") or datetime.now().year
            confidence = fy.get("confidence", 0.0)

            # IMPORTANT: Derive missing fields before storage
            logger.info(f"Deriving missing fields for FY {year}...")
            data = derive_missing_fields(data)

            # Check existing
            existing = db.query(ExtractedFinancialData).filter(
                ExtractedFinancialData.assessment_id == assessment_id,
                ExtractedFinancialData.fiscal_year == year
            ).first()

            fields = [
                'total_assets', 'current_assets', 'non_current_assets',
                'total_liabilities', 'current_liabilities', 'non_current_liabilities',
                'total_equity', 'retained_earnings', 'working_capital',
                'cash_and_equivalents', 'inventory', 'accounts_receivable',
                'accounts_payable', 'revenue', 'cost_of_sales', 'gross_profit',
                'operating_expenses', 'operating_income', 'ebit', 'ebitda',
                'interest_expense', 'net_income', 'operating_cash_flow',
                'investing_cash_flow', 'financing_cash_flow', 'net_cash_flow'
            ]

            if existing:
                for field in fields:
                    if data.get(field) is not None:
                        setattr(existing, field, data.get(field))

                # Store full output as JSON in confidence_scores field
                # Note: SQLAlchemy JSON column handles serialization, don't use json.dumps
                existing.confidence_scores = {
                    "overall": confidence,
                    "v2_output": extracted,
                    "derived_fields": [k for k in data.keys() if k not in fy.get("data", {})]
                }
                logger.info(f"Updated fiscal year {year} (confidence: {confidence})")
            else:
                record = ExtractedFinancialData(
                    assessment_id=assessment_id,
                    fiscal_year=year,
                    is_confirmed=False,
                    confidence_scores={
                        "overall": confidence,
                        "v2_output": extracted,
                        "derived_fields": [k for k in data.keys() if k not in fy.get("data", {})]
                    },
                    **{f: data.get(f) for f in fields}
                )
                db.add(record)
                logger.info(f"Created fiscal year {year} (confidence: {confidence})")

        db.commit()
        logger.info(f"✓ Results stored for assessment {assessment_id}")

    except Exception as e:
        db.rollback()
        logger.error(f"DB error: {e}")
        raise
    finally:
        db.close()


# ============================================================================
# MAIN ENTRY POINTS
# ============================================================================

async def extract_financial_data_v2(
    file_path: str,
    assessment_id: int = None
) -> Dict[str, Any]:
    """
    Main extraction function using v2 pipeline.

    Returns structured JSON with Balance Sheet, P&L, Cash Flow, and metadata.
    """
    pipeline = ExtractionPipelineV2(file_path, assessment_id)
    return await pipeline.run()


async def run_extraction_pipeline_v2(
    assessment_id: int,
    statement_id: int,
    file_path: str
):
    """
    V2 pipeline entry point for background task.
    """
    logger.info("=" * 80)
    logger.info("EXTRACTION PIPELINE V2")
    logger.info(f"Assessment ID: {assessment_id} | Statement ID: {statement_id}")
    logger.info(f"File: {file_path}")
    logger.info("=" * 80)

    update_progress(assessment_id, 'starting')

    try:
        extracted = await extract_financial_data_v2(file_path, assessment_id)
        error = extracted.get("error", "")

        if error:
            logger.warning(f"Extraction issue: {error}")

    except Exception as e:
        logger.error(f"Pipeline error: {e}")
        extracted = {"error": str(e), "metadata": {"confidence": 0}}
        error = str(e)

    # Store results
    await store_results_v2(assessment_id, statement_id, extracted, error)

    # Mark complete
    update_progress(assessment_id, 'complete')

    logger.info("=" * 80)
    logger.info("✓ EXTRACTION PIPELINE V2 COMPLETE")
    logger.info("=" * 80)
