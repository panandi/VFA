"""
Field Mapper Module

Maps extracted line items to canonical field names using robust synonym matching.

Canonical Fields:
- Balance Sheet: Current Assets, Account Receivable, Inventory, Total Assets,
                 Current Liabilities, Creditor/Trade Payables, Total Liabilities,
                 Share Capital/Paid up Capital, Retained Earnings, Equity
- Profit & Loss: Sales/Revenue, Cost of Sales, EBIT, Net Profit/(Loss)
- Cash Flow: Net Cash Flow from Operating/Investing/Financing Activities,
             Cash and Cash Equivalent at end of fiscal year
"""

import re
import logging
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field as dataclass_field
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


@dataclass
class FieldMapping:
    """A mapping from source text to canonical field."""
    canonical_name: str
    source_text: str
    page_num: int
    value: Optional[float]
    year: Optional[int]
    confidence: float = 1.0
    raw_row_text: str = ""


@dataclass
class ExtractedField:
    """An extracted field with source evidence."""
    value: Optional[float]
    unit: Optional[str]
    source: Dict[str, Any] = dataclass_field(default_factory=dict)


# ============================================================================
# SYNONYM MAPPINGS
# ============================================================================

# Balance Sheet field synonyms
BALANCE_SHEET_SYNONYMS = {
    "Current Assets": [
        "current assets",
        "total current assets",
        "current asset",
    ],
    "Account Receivable": [
        "trade receivables",
        "accounts receivable",
        "account receivable",
        "trade and other receivables",
        "sundry debtors",
        "debtors",
        "receivables",
    ],
    "Inventory": [
        "inventories",
        "inventory",
        "stock in trade",
        "stock-in-trade",
        "finished goods",
        "raw materials and stores",
    ],
    "Total Assets": [
        "total assets",
        "assets total",
        "total",  # When in assets section
        "sum of assets",
    ],
    "Current Liabilities": [
        "current liabilities",
        "total current liabilities",
        "current liability",
    ],
    "Creditor/Trade Payables": [
        "trade payables",
        "trade and other payables",
        "accounts payable",
        "sundry creditors",
        "creditors",
        "payables",
    ],
    "Total Liabilities": [
        "total liabilities",
        "liabilities total",
        "total",  # When in liabilities section
        "sum of liabilities",
    ],
    "Share Capital/Paid up Capital": [
        "equity share capital",
        "share capital",
        "paid up capital",
        "paid-up capital",
        "authorised capital",
        "issued capital",
        "subscribed capital",
        "common stock",
        "ordinary shares",
    ],
    "Retained Earnings": [
        "retained earnings",
        "retained profit",
        "accumulated profits",
        "surplus",
        "profit and loss balance",
        "profit & loss balance",
    ],
    "Equity": [
        "total equity",
        "shareholders equity",
        "shareholders' equity",
        "stockholders equity",
        "net worth",
        "capital and reserves",
        "total equity and liabilities",  # Sometimes combined
        "equity attributable to owners",
    ],
    # Additional Balance Sheet fields
    "Cash and Cash Equivalents": [
        "cash and cash equivalents",
        "cash and bank balances",
        "cash at bank",
        "cash in hand",
        "bank balances",
        "cash",
    ],
    "Non-Current Assets": [
        "non-current assets",
        "non current assets",
        "fixed assets",
        "property plant and equipment",
        "property, plant and equipment",
        "tangible assets",
    ],
    "Non-Current Liabilities": [
        "non-current liabilities",
        "non current liabilities",
        "long-term liabilities",
        "long term borrowings",
        "long-term debt",
    ],
    "Other Equity": [
        "other equity",
        "reserves and surplus",
        "other reserves",
        "capital reserve",
        "securities premium",
    ],
}

# Profit & Loss field synonyms
PROFIT_LOSS_SYNONYMS = {
    "Sales/Revenue": [
        "revenue from operations",
        "revenue",
        "net revenue",
        "sales",
        "net sales",
        "turnover",
        "operating revenue",
        "gross revenue",
        "income from operations",
        "total revenue",
        "total income",
    ],
    "Cost of Sales": [
        "cost of goods sold",
        "cost of materials consumed",
        "cost of sales",
        "cost of revenue",
        "cogs",
        "purchases of stock-in-trade",
        "cost of materials",
        "direct costs",
    ],
    "EBIT": [
        "ebit",
        "operating profit",
        "operating income",
        "profit before interest and tax",
        "profit from operations",
        "earnings before interest and tax",
    ],
    "Net Profit/(Loss)": [
        "net profit",
        "net income",
        "profit for the year",
        "profit for the period",
        "profit after tax",
        "pat",
        "net profit/(loss)",
        "profit/(loss) for the year",
        "net income/(loss)",
        "total comprehensive income",
    ],
    # Additional P&L fields
    "Gross Profit": [
        "gross profit",
        "gross margin",
        "gross income",
    ],
    "Operating Expenses": [
        "operating expenses",
        "total expenses",
        "employee benefit expense",
        "other expenses",
    ],
    "Depreciation": [
        "depreciation",
        "depreciation and amortisation",
        "depreciation and amortization",
        "depreciation expense",
    ],
    "Interest Expense": [
        "finance costs",
        "interest expense",
        "interest paid",
        "borrowing costs",
        "finance charges",
    ],
    "EBITDA": [
        "ebitda",
        "earnings before interest tax depreciation and amortization",
        "operating ebitda",
    ],
}

# Cash Flow field synonyms
CASH_FLOW_SYNONYMS = {
    "Net Cash Flow from Operating Activities": [
        "net cash from operating activities",
        "cash from operations",
        "cash generated from operations",
        "net cash flow from operating activities",
        "operating cash flow",
        "cash flow from operating activities",
        "net cash generated from operating activities",
        "net cash inflow from operating activities",
    ],
    "Net Cash Flow from Investing Activities": [
        "net cash from investing activities",
        "cash used in investing activities",
        "net cash flow from investing activities",
        "investing cash flow",
        "cash flow from investing activities",
        "net cash used in investing activities",
    ],
    "Net Cash Flow from Financing Activities": [
        "net cash from financing activities",
        "cash from financing activities",
        "net cash flow from financing activities",
        "financing cash flow",
        "cash flow from financing activities",
        "net cash used in financing activities",
    ],
    "Cash and Cash Equivalent at end of fiscal year": [
        "cash and cash equivalents at end of year",
        "closing cash and cash equivalents",
        "cash at end of period",
        "cash at end of year",
        "closing balance",
        "cash and cash equivalents at the end of the year",
    ],
    # Additional Cash Flow fields
    "Net Increase in Cash": [
        "net increase in cash",
        "net change in cash",
        "increase in cash and cash equivalents",
        "net cash flow",
    ],
    "Cash at Beginning": [
        "cash at beginning of year",
        "opening cash and cash equivalents",
        "opening balance",
        "cash at beginning of period",
    ],
}


class FieldMapper:
    """
    Maps extracted line items to canonical field names.

    Usage:
        mapper = FieldMapper()
        mapping = mapper.map_field("Trade Receivables", statement_type='balance_sheet')
        # Returns: "Account Receivable"
    """

    def __init__(self):
        # Build reverse lookup: synonym -> canonical name
        self.synonym_lookup = {}

        for synonyms_dict in [BALANCE_SHEET_SYNONYMS, PROFIT_LOSS_SYNONYMS, CASH_FLOW_SYNONYMS]:
            for canonical, synonyms in synonyms_dict.items():
                for syn in synonyms:
                    self.synonym_lookup[syn.lower()] = canonical

    def _normalize_text(self, text: str) -> str:
        """Normalize text for matching."""
        text = text.lower().strip()
        # Remove extra spaces
        text = re.sub(r'\s+', ' ', text)
        # Remove common prefixes/suffixes
        text = re.sub(r'^(i+|[a-z])\.\s*', '', text)  # Remove roman numerals, letters
        text = re.sub(r'^\d+[\.\)]\s*', '', text)  # Remove numbers
        # Remove parenthetical notes
        text = re.sub(r'\s*\([^)]+\)\s*', ' ', text)
        return text.strip()

    def _fuzzy_match(self, text: str, candidates: List[str], threshold: float = 0.8) -> Optional[str]:
        """
        Find best fuzzy match among candidates.
        """
        text = self._normalize_text(text)
        best_match = None
        best_score = 0

        for candidate in candidates:
            score = SequenceMatcher(None, text, candidate.lower()).ratio()
            if score > best_score and score >= threshold:
                best_score = score
                best_match = candidate

        return best_match

    def map_field(
        self,
        source_text: str,
        statement_type: str = None,
        fuzzy: bool = True
    ) -> Tuple[Optional[str], float]:
        """
        Map a source text to its canonical field name.

        Args:
            source_text: The text from the PDF (e.g., "Trade Receivables")
            statement_type: 'balance_sheet', 'income_statement', or 'cash_flow'
            fuzzy: Whether to use fuzzy matching

        Returns: (canonical_name, confidence_score)
        """
        normalized = self._normalize_text(source_text)

        # Direct lookup
        if normalized in self.synonym_lookup:
            return self.synonym_lookup[normalized], 1.0

        # Try partial match
        for syn, canonical in self.synonym_lookup.items():
            if syn in normalized or normalized in syn:
                return canonical, 0.9

        # Fuzzy match
        if fuzzy:
            matched = self._fuzzy_match(
                normalized,
                list(self.synonym_lookup.keys()),
                threshold=0.75
            )
            if matched:
                return self.synonym_lookup[matched], 0.7

        return None, 0.0

    def map_extracted_data(
        self,
        extracted: Dict[str, Any],
        statement_type: str,
        page_num: int = 0
    ) -> Dict[str, ExtractedField]:
        """
        Map extracted data dictionary to canonical field structure.
        """
        result = {}

        for key, value in extracted.items():
            if value is None:
                continue

            canonical, confidence = self.map_field(key, statement_type)

            if canonical:
                result[canonical] = ExtractedField(
                    value=value,
                    unit=None,  # Will be set from metadata
                    source={
                        "page": page_num,
                        "row": key,
                        "confidence": confidence
                    }
                )
            else:
                logger.debug(f"Unmapped field: {key}")

        return result


# Convenience instance
_mapper = FieldMapper()


def map_to_canonical(
    source_text: str,
    statement_type: str = None
) -> Tuple[Optional[str], float]:
    """
    Convenience function to map source text to canonical field name.
    """
    return _mapper.map_field(source_text, statement_type)


def get_synonym_list(statement_type: str) -> Dict[str, List[str]]:
    """
    Get the synonym dictionary for a statement type.
    """
    if statement_type == 'balance_sheet':
        return BALANCE_SHEET_SYNONYMS
    elif statement_type in ['income_statement', 'profit_loss']:
        return PROFIT_LOSS_SYNONYMS
    elif statement_type == 'cash_flow':
        return CASH_FLOW_SYNONYMS
    else:
        return {}


# ============================================================================
# OUTPUT FORMAT BUILDER
# ============================================================================

def build_output_format(
    balance_sheet: Dict[str, Any],
    profit_loss: Dict[str, Any],
    cash_flow: Dict[str, Any],
    metadata: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Build the final output format as specified in requirements.

    Output format:
    {
      "Balance Sheet": {
        "Current Assets": { "<FY>": <number>, "unit": "<unit>", "source": {...} },
        ...
      },
      "Profit and Loss": {...},
      "Cash Flow Statement": {...},
      "metadata": {...}
    }
    """

    def format_field(field_data: Dict, years: List[int]) -> Dict:
        """Format a single field with year values."""
        result = {}
        for year in years:
            year_key = f"FY_{year}"
            result[year_key] = field_data.get(year, None)
        result["unit"] = field_data.get("unit", metadata.get("scale"))
        result["source"] = field_data.get("source", {})
        return result

    years = metadata.get("detected_years", [])

    return {
        "Balance Sheet": {
            key: format_field(value, years)
            for key, value in balance_sheet.items()
        },
        "Profit and Loss": {
            key: format_field(value, years)
            for key, value in profit_loss.items()
        },
        "Cash Flow Statement": {
            key: format_field(value, years)
            for key, value in cash_flow.items()
        },
        "metadata": metadata
    }
