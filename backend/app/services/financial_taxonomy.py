"""
Financial Statement Taxonomy - Hierarchical Classification System
Maps all possible financial line items to their hierarchical structure
"""

from typing import Dict, List, Optional, Set
from dataclasses import dataclass
import re


@dataclass
class FinancialItem:
    """Represents a financial line item with its hierarchical position"""
    canonical_name: str
    category: str  # "asset", "liability", "equity", "revenue", "expense", "cashflow"
    parent: Optional[str] = None
    level: int = 0
    keywords: List[str] = None
    patterns: List[str] = None

    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []
        if self.patterns is None:
            self.patterns = []


class FinancialTaxonomy:
    """Complete taxonomy of financial statement items"""

    def __init__(self):
        self.items: Dict[str, FinancialItem] = {}
        self._build_taxonomy()

    def _build_taxonomy(self):
        """Build complete financial taxonomy"""

        # ============================================================
        # BALANCE SHEET - ASSETS
        # ============================================================

        # Level 1: Total Assets
        self._add_item("total_assets", "asset", None, 0, [
            "total assets", "total asset", "assets total"
        ])

        # Level 2: Asset Categories
        self._add_item("current_assets", "asset", "total_assets", 1, [
            "current assets", "current asset", "assets current",
            "short term assets", "short-term assets"
        ])

        self._add_item("non_current_assets", "asset", "total_assets", 1, [
            "non-current assets", "non current assets", "noncurrent assets",
            "fixed assets", "long term assets", "long-term assets"
        ])

        # Level 3: Current Assets Breakdown
        self._add_item("cash_and_equivalents", "asset", "current_assets", 2, [
            "cash and cash equivalents", "cash & cash equivalents",
            "cash and bank", "cash at bank", "bank balance",
            "cash in hand", "cash on hand"
        ])

        self._add_item("accounts_receivable", "asset", "current_assets", 2, [
            "accounts receivable", "trade receivables", "debtors",
            "trade debtors", "sundry debtors", "receivables"
        ])

        self._add_item("inventory", "asset", "current_assets", 2, [
            "inventory", "inventories", "stock", "stocks",
            "raw materials", "work in progress", "finished goods"
        ])

        self._add_item("prepaid_expenses", "asset", "current_assets", 2, [
            "prepaid expenses", "prepayments", "advances"
        ])

        self._add_item("short_term_investments", "asset", "current_assets", 2, [
            "short term investments", "short-term investments",
            "current investments", "marketable securities"
        ])

        self._add_item("other_current_assets", "asset", "current_assets", 2, [
            "other current assets", "other assets current"
        ])

        # Level 3: Non-Current Assets Breakdown
        self._add_item("property_plant_equipment", "asset", "non_current_assets", 2, [
            "property plant and equipment", "property, plant & equipment",
            "ppe", "fixed assets", "tangible assets", "plant and machinery"
        ])

        self._add_item("intangible_assets", "asset", "non_current_assets", 2, [
            "intangible assets", "goodwill", "patents", "trademarks"
        ])

        self._add_item("long_term_investments", "asset", "non_current_assets", 2, [
            "long term investments", "long-term investments",
            "non-current investments"
        ])

        self._add_item("deferred_tax_assets", "asset", "non_current_assets", 2, [
            "deferred tax assets", "deferred tax asset"
        ])

        self._add_item("other_non_current_assets", "asset", "non_current_assets", 2, [
            "other non-current assets", "other non current assets"
        ])

        # ============================================================
        # BALANCE SHEET - LIABILITIES
        # ============================================================

        # Level 1: Total Liabilities
        self._add_item("total_liabilities", "liability", None, 0, [
            "total liabilities", "total liability", "liabilities total"
        ])

        # Level 2: Liability Categories
        self._add_item("current_liabilities", "liability", "total_liabilities", 1, [
            "current liabilities", "current liability", "liabilities current",
            "short term liabilities", "short-term liabilities"
        ])

        self._add_item("non_current_liabilities", "liability", "total_liabilities", 1, [
            "non-current liabilities", "non current liabilities",
            "long term liabilities", "long-term liabilities"
        ])

        # Level 3: Current Liabilities Breakdown
        self._add_item("accounts_payable", "liability", "current_liabilities", 2, [
            "accounts payable", "trade payables", "creditors",
            "trade creditors", "sundry creditors", "payables"
        ])

        self._add_item("short_term_debt", "liability", "current_liabilities", 2, [
            "short term debt", "short-term debt", "short term borrowings",
            "current portion of long term debt", "bank overdraft"
        ])

        self._add_item("accrued_expenses", "liability", "current_liabilities", 2, [
            "accrued expenses", "accruals", "accrued liabilities"
        ])

        self._add_item("provisions", "liability", "current_liabilities", 2, [
            "provisions", "provision for expenses"
        ])

        self._add_item("other_current_liabilities", "liability", "current_liabilities", 2, [
            "other current liabilities", "other payables"
        ])

        # Level 3: Non-Current Liabilities Breakdown
        self._add_item("long_term_debt", "liability", "non_current_liabilities", 2, [
            "long term debt", "long-term debt", "long term borrowings",
            "term loans", "bonds payable", "debentures"
        ])

        self._add_item("deferred_tax_liabilities", "liability", "non_current_liabilities", 2, [
            "deferred tax liabilities", "deferred tax liability"
        ])

        self._add_item("other_non_current_liabilities", "liability", "non_current_liabilities", 2, [
            "other non-current liabilities", "other non current liabilities"
        ])

        # ============================================================
        # BALANCE SHEET - EQUITY
        # ============================================================

        # Level 1: Total Equity
        self._add_item("total_equity", "equity", None, 0, [
            "total equity", "shareholders equity", "shareholders' equity",
            "stockholders equity", "total shareholders funds",
            "net worth", "owners equity"
        ])

        # Level 2: Equity Components
        self._add_item("share_capital", "equity", "total_equity", 1, [
            "share capital", "capital stock", "issued capital",
            "paid up capital", "equity share capital"
        ])

        self._add_item("retained_earnings", "equity", "total_equity", 1, [
            "retained earnings", "accumulated profits", "reserves",
            "revenue reserves", "surplus"
        ])

        self._add_item("other_equity", "equity", "total_equity", 1, [
            "other equity", "other reserves", "capital reserves"
        ])

        # ============================================================
        # INCOME STATEMENT - REVENUE
        # ============================================================

        # Level 1: Revenue
        self._add_item("revenue", "revenue", None, 0, [
            "revenue", "total revenue", "sales", "total sales",
            "turnover", "income from operations", "operating revenue"
        ])

        # Level 2: Revenue Breakdown
        self._add_item("product_revenue", "revenue", "revenue", 1, [
            "product revenue", "product sales", "goods sold"
        ])

        self._add_item("service_revenue", "revenue", "revenue", 1, [
            "service revenue", "service income", "fees earned"
        ])

        self._add_item("other_income", "revenue", "revenue", 1, [
            "other income", "other revenue", "miscellaneous income"
        ])

        # ============================================================
        # INCOME STATEMENT - EXPENSES
        # ============================================================

        # Level 1: Cost of Sales
        self._add_item("cost_of_sales", "expense", None, 0, [
            "cost of sales", "cost of goods sold", "cogs",
            "cost of revenue", "direct costs"
        ])

        # Level 1: Gross Profit
        self._add_item("gross_profit", "revenue", None, 0, [
            "gross profit", "gross margin"
        ])

        # Level 1: Operating Expenses
        self._add_item("operating_expenses", "expense", None, 0, [
            "operating expenses", "operating costs", "opex"
        ])

        # Level 2: Operating Expense Breakdown
        self._add_item("selling_expenses", "expense", "operating_expenses", 1, [
            "selling expenses", "selling costs", "distribution expenses"
        ])

        self._add_item("admin_expenses", "expense", "operating_expenses", 1, [
            "administrative expenses", "admin expenses", "general expenses",
            "general and administrative", "g&a"
        ])

        self._add_item("rd_expenses", "expense", "operating_expenses", 1, [
            "research and development", "r&d expenses", "development costs"
        ])

        self._add_item("depreciation", "expense", "operating_expenses", 1, [
            "depreciation", "depreciation and amortization",
            "amortization"
        ])

        # Level 1: Operating Income
        self._add_item("operating_income", "revenue", None, 0, [
            "operating income", "operating profit", "ebit",
            "earnings before interest and tax"
        ])

        # Level 1: Interest and Tax
        self._add_item("interest_expense", "expense", None, 0, [
            "interest expense", "finance costs", "interest paid"
        ])

        self._add_item("tax_expense", "expense", None, 0, [
            "tax expense", "income tax", "taxation", "provision for tax"
        ])

        # Level 1: Net Income
        self._add_item("net_income", "revenue", None, 0, [
            "net income", "net profit", "profit after tax",
            "net earnings", "bottom line", "pat"
        ])

        # ============================================================
        # CASH FLOW STATEMENT
        # ============================================================

        self._add_item("operating_cash_flow", "cashflow", None, 0, [
            "cash flow from operating activities",
            "operating cash flow", "cash from operations"
        ])

        self._add_item("investing_cash_flow", "cashflow", None, 0, [
            "cash flow from investing activities",
            "investing cash flow", "cash used in investing"
        ])

        self._add_item("financing_cash_flow", "cashflow", None, 0, [
            "cash flow from financing activities",
            "financing cash flow", "cash from financing"
        ])

        self._add_item("net_cash_flow", "cashflow", None, 0, [
            "net increase in cash", "net cash flow",
            "change in cash", "net change in cash"
        ])

    def _add_item(self, canonical_name: str, category: str, parent: Optional[str],
                  level: int, keywords: List[str]):
        """Add item to taxonomy"""
        self.items[canonical_name] = FinancialItem(
            canonical_name=canonical_name,
            category=category,
            parent=parent,
            level=level,
            keywords=[k.lower() for k in keywords]
        )

    def match_line_item(self, text: str) -> Optional[str]:
        """Match a line item text to canonical name"""
        text_lower = text.lower().strip()

        # Remove common prefixes/suffixes
        text_clean = re.sub(r'^(note\s+\d+\s*[-:])?\s*', '', text_lower)
        text_clean = re.sub(r'\s*\([^)]*\)\s*$', '', text_clean)

        # Try exact match first
        for canonical, item in self.items.items():
            for keyword in item.keywords:
                if keyword == text_clean or text_clean.endswith(keyword):
                    return canonical

        # Try partial match
        for canonical, item in self.items.items():
            for keyword in item.keywords:
                if keyword in text_clean:
                    return canonical

        return None

    def get_children(self, canonical_name: str) -> List[str]:
        """Get all direct children of an item"""
        return [
            name for name, item in self.items.items()
            if item.parent == canonical_name
        ]

    def get_hierarchy(self, canonical_name: str) -> Dict:
        """Get full hierarchy for an item"""
        item = self.items.get(canonical_name)
        if not item:
            return {}

        result = {
            "name": canonical_name,
            "category": item.category,
            "level": item.level,
            "children": []
        }

        for child_name in self.get_children(canonical_name):
            result["children"].append(self.get_hierarchy(child_name))

        return result

    def get_all_by_category(self, category: str) -> List[str]:
        """Get all items in a category"""
        return [
            name for name, item in self.items.items()
            if item.category == category
        ]


# Global taxonomy instance
taxonomy = FinancialTaxonomy()
