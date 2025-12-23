"""
Fast & Cost-Efficient Financial Data Extraction from PDFs
Uses GPT-4o-mini with optimized prompts and smart page filtering.
Improved extraction quality with comprehensive terminology mapping.
"""

import json
import re
import logging
from typing import Dict, Any, List
from datetime import datetime
from openai import AsyncOpenAI
import httpx

import pypdf

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.assessment import FinancialStatement, ExtractedFinancialData

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Comprehensive keywords to identify financial statement pages
FINANCIAL_KEYWORDS = [
    # Balance Sheet
    'balance sheet', 'statement of financial position', 'assets', 'liabilities',
    'equity', 'total assets', 'total liabilities', 'current assets', 'non-current',
    'shareholders equity', 'stockholders equity', 'retained earnings', 'net worth',
    'accounts receivable', 'accounts payable', 'inventory', 'cash and cash equivalents',
    'property plant equipment', 'intangible assets', 'goodwill', 'debtors', 'creditors',
    'trade receivables', 'trade payables', 'short-term debt', 'long-term debt',

    # Income Statement / P&L
    'income statement', 'profit and loss', 'profit & loss', 'p&l', 'statement of income',
    'statement of operations', 'revenue', 'sales', 'turnover', 'cost of sales',
    'cost of goods sold', 'cogs', 'gross profit', 'operating expenses', 'operating income',
    'operating profit', 'ebit', 'ebitda', 'interest expense', 'net income', 'net profit',
    'profit after tax', 'profit before tax', 'earnings', 'expenses', 'depreciation',
    'amortization', 'selling general administrative', 'sga', 'other income',

    # Cash Flow Statement
    'cash flow', 'statement of cash flows', 'cash flows from operating',
    'cash flows from investing', 'cash flows from financing', 'operating activities',
    'investing activities', 'financing activities', 'net cash', 'free cash flow',
    'capital expenditure', 'capex', 'dividends paid', 'proceeds from',

    # General financial terms
    'fiscal year', 'annual report', 'financial statements', 'consolidated',
    'audited', 'unaudited', 'notes to financial', 'in thousands', 'in millions'
]


def extract_relevant_pages(file_path: str, max_pages: int = 20) -> str:
    """Extract pages containing financial data with improved detection."""
    try:
        with open(file_path, "rb") as f:
            reader = pypdf.PdfReader(f)
            total_pages = len(reader.pages)

            logger.info(f"PDF has {total_pages} pages, scanning for financial data...")

            # Score each page by financial keyword density
            page_scores = []
            for i, page in enumerate(reader.pages):
                try:
                    text = page.extract_text() or ""
                    text_lower = text.lower()

                    # Count keyword matches with weighting
                    score = 0
                    for kw in FINANCIAL_KEYWORDS:
                        if kw in text_lower:
                            # Higher weight for key statement identifiers
                            if kw in ['balance sheet', 'income statement', 'cash flow',
                                     'profit and loss', 'statement of financial position']:
                                score += 5
                            elif kw in ['total assets', 'total liabilities', 'revenue',
                                       'net income', 'operating cash flow']:
                                score += 3
                            else:
                                score += 1

                    # Also check for numeric patterns (financial tables)
                    numbers = re.findall(r'\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+\.\d+', text)
                    if len(numbers) > 10:  # Page has many numbers = likely financial table
                        score += 2

                    if score > 0:
                        page_scores.append((i, score, text))
                except:
                    continue

            # Sort by score and take top pages
            page_scores.sort(key=lambda x: x[1], reverse=True)
            selected = page_scores[:max_pages]

            # Sort selected pages by page number for coherent reading
            selected.sort(key=lambda x: x[0])

            if not selected:
                # Fallback: take first 15 pages if no keywords found
                logger.warning("No financial keywords found, using first pages")
                texts = []
                for i in range(min(15, total_pages)):
                    try:
                        text = reader.pages[i].extract_text() or ""
                        if text.strip():
                            texts.append(f"[Page {i+1}]\n{text}")
                    except:
                        continue
                return "\n\n".join(texts)

            logger.info(f"Selected {len(selected)} pages with financial data (scores: {[s[1] for s in selected[:5]]})")

            # Combine selected page texts
            texts = [f"[Page {p[0]+1}]\n{clean_text(p[2])}" for p in selected]
            return "\n\n".join(texts)

    except Exception as e:
        logger.error(f"PDF extraction error: {e}")
        return ""


def clean_text(text: str) -> str:
    """Quick text cleanup."""
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Fix common OCR issues
    text = text.replace('−', '-').replace('–', '-')
    return text.strip()


# Improved system prompt - comprehensive but efficient
SYSTEM_PROMPT = """You are a financial data extraction expert. Extract ALL financial data from Balance Sheet, Income Statement (P&L), and Cash Flow Statement.

OUTPUT FORMAT (JSON):
{
  "fiscal_years": [{
    "year": 2023,
    "data": {
      "total_assets": <number|null>,
      "current_assets": <number|null>,
      "non_current_assets": <number|null>,
      "cash_and_equivalents": <number|null>,
      "inventory": <number|null>,
      "accounts_receivable": <number|null>,
      "total_liabilities": <number|null>,
      "current_liabilities": <number|null>,
      "non_current_liabilities": <number|null>,
      "accounts_payable": <number|null>,
      "total_equity": <number|null>,
      "retained_earnings": <number|null>,
      "revenue": <number|null>,
      "cost_of_sales": <number|null>,
      "gross_profit": <number|null>,
      "operating_expenses": <number|null>,
      "operating_income": <number|null>,
      "ebit": <number|null>,
      "ebitda": <number|null>,
      "interest_expense": <number|null>,
      "net_income": <number|null>,
      "operating_cash_flow": <number|null>,
      "investing_cash_flow": <number|null>,
      "financing_cash_flow": <number|null>
    }
  }]
}

TERMINOLOGY MAPPINGS (use these to find data):
BALANCE SHEET:
- Total Assets = Assets Total, Sum of Assets
- Current Assets = Short-term Assets, Assets due within 1 year
- Cash = Cash and Cash Equivalents, Bank Balances, Liquid Assets
- Inventory = Stock, Inventories, Merchandise, Raw Materials + WIP + Finished Goods
- Accounts Receivable = Trade Receivables, Debtors, Trade Debtors, Amounts Owed by Customers
- Total Liabilities = Liabilities Total, Total Debt
- Current Liabilities = Short-term Liabilities, Amounts due within 1 year
- Accounts Payable = Trade Payables, Creditors, Trade Creditors, Amounts Owed to Suppliers
- Total Equity = Shareholders' Equity, Stockholders' Equity, Net Worth, Capital and Reserves, Net Assets

INCOME STATEMENT (P&L):
- Revenue = Sales, Turnover, Net Sales, Total Revenue, Operating Revenue, Income from Operations
- Cost of Sales = COGS, Cost of Revenue, Cost of Goods Sold, Direct Costs
- Gross Profit = Gross Margin, Sales - COGS
- Operating Expenses = SG&A, Selling/General/Administrative, Overheads
- Operating Income = Operating Profit, EBIT, Profit from Operations
- EBIT = Earnings Before Interest and Tax, Operating Profit
- EBITDA = EBIT + Depreciation + Amortization
- Net Income = Net Profit, Profit After Tax, PAT, Net Earnings, Bottom Line, Profit for the Year

CASH FLOW:
- Operating Cash Flow = Cash from Operations, Net Cash from Operating Activities
- Investing Cash Flow = Cash from Investing, Net Cash used in Investing
- Financing Cash Flow = Cash from Financing, Net Cash from Financing Activities

CRITICAL RULES:
1. SCALE: Check for "in thousands", "in millions", "(000s)", "(m)" - multiply accordingly
2. SIGNS: Cash outflows are usually negative. Keep original signs.
3. YEARS: Extract ALL years shown (comparative statements often have 2-3 years)
4. CALCULATE if not explicit:
   - Gross Profit = Revenue - Cost of Sales
   - Working Capital = Current Assets - Current Liabilities
   - Non-Current = Total - Current
5. NULL if truly not found - don't guess random numbers
6. Look for consolidated statements first, then standalone if no consolidated"""


async def extract_with_llm(text: str) -> Dict[str, Any]:
    """Fast LLM extraction with improved prompts."""
    try:
        # Create HTTP client with SSL verification disabled for corporate proxy
        http_client = httpx.AsyncClient(
            verify=False,
            timeout=httpx.Timeout(60.0, connect=10.0)
        )
        client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            http_client=http_client
        )

        # Allow more text for better context
        if len(text) > 25000:
            text = text[:25000] + "\n[TRUNCATED - more pages available]"

        logger.info(f"Sending {len(text)} chars to {settings.OPENAI_MODEL}")

        response = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Extract ALL financial data from these financial statements. Look carefully for Balance Sheet, P&L/Income Statement, and Cash Flow data:\n\n{text}"}
            ],
            temperature=0,
            max_tokens=2000,  # Slightly higher for multiple years
            response_format={"type": "json_object"}
        )

        content = response.choices[0].message.content
        logger.info(f"Received {len(content)} chars response")

        result = json.loads(content)

        # Log what was found
        years_found = [fy.get('year') for fy in result.get('fiscal_years', [])]
        logger.info(f"Extracted data for years: {years_found}")

        return result

    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error: {e}")
        return {"fiscal_years": []}
    except Exception as e:
        logger.error(f"LLM error: {e}")
        return {"fiscal_years": []}


def calculate_derived_values(data: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate values that can be derived from other fields."""

    # Working capital
    if data.get("working_capital") is None:
        if data.get("current_assets") is not None and data.get("current_liabilities") is not None:
            data["working_capital"] = data["current_assets"] - data["current_liabilities"]

    # Non-current assets
    if data.get("non_current_assets") is None:
        if data.get("total_assets") is not None and data.get("current_assets") is not None:
            data["non_current_assets"] = data["total_assets"] - data["current_assets"]

    # Non-current liabilities
    if data.get("non_current_liabilities") is None:
        if data.get("total_liabilities") is not None and data.get("current_liabilities") is not None:
            data["non_current_liabilities"] = data["total_liabilities"] - data["current_liabilities"]

    # Gross profit
    if data.get("gross_profit") is None:
        if data.get("revenue") is not None and data.get("cost_of_sales") is not None:
            data["gross_profit"] = data["revenue"] - data["cost_of_sales"]

    # EBIT from operating income
    if data.get("ebit") is None and data.get("operating_income") is not None:
        data["ebit"] = data["operating_income"]

    # Operating income from EBIT
    if data.get("operating_income") is None and data.get("ebit") is not None:
        data["operating_income"] = data["ebit"]

    # Net cash flow
    ocf = data.get("operating_cash_flow")
    icf = data.get("investing_cash_flow")
    fcf = data.get("financing_cash_flow")
    if data.get("net_cash_flow") is None and any([ocf, icf, fcf]):
        data["net_cash_flow"] = (ocf or 0) + (icf or 0) + (fcf or 0)

    # Total liabilities from assets and equity (accounting equation)
    if data.get("total_liabilities") is None:
        if data.get("total_assets") is not None and data.get("total_equity") is not None:
            data["total_liabilities"] = data["total_assets"] - data["total_equity"]

    # Total equity from assets and liabilities
    if data.get("total_equity") is None:
        if data.get("total_assets") is not None and data.get("total_liabilities") is not None:
            data["total_equity"] = data["total_assets"] - data["total_liabilities"]

    return data


async def extract_financial_data(file_path: str) -> Dict[str, Any]:
    """Main extraction - optimized for speed and quality."""
    logger.info(f"Extracting from: {file_path}")

    # Get relevant pages (increased to 20 for better coverage)
    text = extract_relevant_pages(file_path, max_pages=20)

    if len(text) < 100:
        return {"error": "PDF empty or unreadable", "fiscal_years": []}

    # Single LLM call with improved prompt
    result = await extract_with_llm(text)

    # Calculate derived values for each year
    for fy in result.get("fiscal_years", []):
        data = fy.get("data", {})
        fy["data"] = calculate_derived_values(data)

        # Log extraction completeness
        filled = sum(1 for v in data.values() if v is not None)
        total = len(data)
        logger.info(f"Year {fy.get('year')}: {filled}/{total} fields extracted")

    return result


async def store_results(
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

        # Store each fiscal year
        for fy in extracted.get("fiscal_years", []):
            data = fy.get("data", {})
            year = fy.get("year") or datetime.now().year

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
                logger.info(f"Updated fiscal year {year}")
            else:
                record = ExtractedFinancialData(
                    assessment_id=assessment_id,
                    fiscal_year=year,
                    is_confirmed=False,
                    **{f: data.get(f) for f in fields}
                )
                db.add(record)
                logger.info(f"Created fiscal year {year}")

        db.commit()
        logger.info(f"Stored results for assessment {assessment_id}")

    except Exception as e:
        db.rollback()
        logger.error(f"DB error: {e}")
        raise
    finally:
        db.close()


async def run_extraction_pipeline(
    assessment_id: int,
    statement_id: int,
    file_path: str
):
    """Main entry point - fast single-pass extraction with quality focus."""
    logger.info(f"=== Extraction: assessment={assessment_id}, statement={statement_id} ===")

    try:
        extracted = await extract_financial_data(file_path)
        error = extracted.get("error", "")

        if error:
            logger.warning(f"Extraction issue: {error}")
        else:
            years = len(extracted.get("fiscal_years", []))
            logger.info(f"Extracted {years} fiscal year(s)")

    except Exception as e:
        logger.error(f"Pipeline error: {e}")
        extracted = {"fiscal_years": []}
        error = str(e)

    await store_results(assessment_id, statement_id, extracted, error)
    logger.info("=== Extraction complete ===")
