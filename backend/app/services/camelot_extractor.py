"""
Camelot-Based Financial Data Extractor
Extracts financial data from PDF tables using Camelot library
Uses aggressive extraction with multiple strategies
"""

import camelot
import pandas as pd
import re
import logging
import warnings
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from pathlib import Path
import fitz  # PyMuPDF for page count

# Suppress camelot's image-based page warnings
warnings.filterwarnings('ignore', message='.*image-based.*camelot only works on text-based.*')

from app.services.financial_taxonomy import taxonomy

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ExtractedLineItem:
    """Represents a single extracted financial line item"""
    line_item: str
    canonical_name: Optional[str]
    category: str
    parent: Optional[str]
    level: int
    values: Dict[int, float] = field(default_factory=dict)
    confidence: float = 1.0
    source_page: Optional[int] = None


@dataclass
class ExtractedStatement:
    """Represents an extracted financial statement"""
    statement_type: str
    years: List[int]
    line_items: List[ExtractedLineItem]
    raw_tables: List[pd.DataFrame] = field(default_factory=list)


class CamelotExtractor:
    """Extract financial data using Camelot table detection with multiple strategies"""

    # Keywords for statement type detection
    BALANCE_SHEET_KEYWORDS = [
        "balance sheet", "statement of financial position", "financial position",
        "total assets", "total liabilities", "shareholders equity", "stockholders equity",
        "shareholder's equity", "stockholder's equity", "shareholders' equity",
        "net assets", "equity and liabilities", "assets and liabilities",
        "non-current assets", "non current assets", "fixed assets", "current assets",
        "current liabilities", "non-current liabilities", "non current liabilities",
        "property plant", "plant and equipment", "intangible assets", "tangible assets",
        "trade receivables", "trade payables", "inventories", "inventory",
        "cash and cash equivalents", "cash and bank", "bank balances",
        "share capital", "reserves and surplus", "retained earnings",
        "long term borrowings", "short term borrowings", "borrowings",
        "deferred tax", "provisions", "other equity",
        "sources of funds", "application of funds",
        "sundry debtors", "sundry creditors",
        "loans and advances", "deposits",
        "capital work in progress", "goodwill",
    ]

    INCOME_STATEMENT_KEYWORDS = [
        "income statement", "profit and loss", "profit & loss", "p&l",
        "statement of comprehensive income", "statement of income",
        "statement of profit", "statement of operations",
        "revenue from operations", "other income", "finance costs",
        "cost of goods sold", "cost of sales", "cost of revenue",
        "operating expenses", "administrative expenses", "selling expenses",
        "depreciation", "amortization", "depreciation and amortization",
        "interest expense", "interest income", "tax expense", "income tax",
        "earnings before", "ebit", "ebitda", "profit before tax", "profit after tax",
        "basic eps", "diluted eps", "earnings per share",
        "turnover", "sales", "gross sales", "net sales",
        "manufacturing expenses", "employee benefit", "employee cost",
        "exceptional items", "extraordinary items",
        "for the year ended", "for the period ended",
        "total revenue", "total income", "net profit", "net loss",
        "gross profit", "operating profit", "net income",
    ]

    CASH_FLOW_KEYWORDS = [
        "cash flow", "cash flows", "statement of cash flows", "cash flow statement",
        "operating activities", "investing activities", "financing activities",
        "cash from operations", "cash used in", "cash generated",
        "net cash", "cash and cash equivalents",
        "increase in cash", "decrease in cash",
        "beginning cash", "ending cash", "opening cash", "closing cash",
        "working capital changes", "changes in working capital",
        "purchase of", "sale of", "proceeds from",
        "dividends paid", "interest paid", "taxes paid",
        "cash flow from", "cash flow used",
    ]

    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.statements: List[ExtractedStatement] = []
        self.all_tables: List[pd.DataFrame] = []
        self.unclassified_tables: List[pd.DataFrame] = []
        self.page_count = self._get_page_count()

    def _get_page_count(self) -> int:
        """Get total number of pages in PDF"""
        try:
            doc = fitz.open(self.pdf_path)
            count = len(doc)
            doc.close()
            return count
        except:
            return 100  # Default fallback

    def extract_all(self) -> List[ExtractedStatement]:
        """Extract all financial data from PDF tables using multiple strategies"""
        logger.info("=" * 70)
        logger.info("  CAMELOT TABLE EXTRACTOR (Enhanced)")
        logger.info("=" * 70)
        logger.info(f"PDF File: {self.pdf_path}")
        logger.info(f"Total Pages: {self.page_count}")
        logger.info("")

        # Step 1: Find pages likely to contain financial statements
        logger.info(">>> Step 1: Scanning PDF for financial statement pages...")
        logger.info("-" * 70)
        financial_pages = self._find_financial_pages()
        logger.info(f"  Found {len(financial_pages)} potential financial statement pages: {financial_pages[:20]}...")

        # Step 2: Extract tables using multiple strategies
        logger.info("\n>>> Step 2: Extracting tables with Camelot...")
        logger.info("-" * 70)

        all_extracted_tables = []

        # Strategy 1: Target financial pages with both modes
        if financial_pages:
            pages_str = ','.join(map(str, financial_pages[:30]))  # Limit to first 30 pages
            logger.info(f"  Targeting pages: {pages_str}")

            # Try lattice mode on target pages
            tables = self._extract_with_lattice(pages_str)
            all_extracted_tables.extend(tables)
            logger.info(f"  Lattice mode on target pages: {len(tables)} table(s)")

            # Try stream mode on target pages
            tables = self._extract_with_stream(pages_str)
            all_extracted_tables.extend(tables)
            logger.info(f"  Stream mode on target pages: {len(tables)} table(s)")

        # Strategy 2: Also try first 20 pages (where financial statements usually are)
        first_pages = ','.join(map(str, range(1, min(21, self.page_count + 1))))
        logger.info(f"\n  Also trying first 20 pages...")

        tables = self._extract_with_lattice(first_pages)
        all_extracted_tables.extend(tables)
        logger.info(f"  Lattice mode on first pages: {len(tables)} table(s)")

        tables = self._extract_with_stream(first_pages)
        all_extracted_tables.extend(tables)
        logger.info(f"  Stream mode on first pages: {len(tables)} table(s)")

        # Strategy 3: Full document scan with stream (catches borderless tables)
        logger.info(f"\n  Full document stream scan...")
        tables = self._extract_with_stream('all')
        all_extracted_tables.extend(tables)
        logger.info(f"  Stream mode full scan: {len(tables)} table(s)")

        # Deduplicate all tables
        logger.info(f"\n  Total tables before dedup: {len(all_extracted_tables)}")
        unique_tables = self._deduplicate_tables(all_extracted_tables)
        logger.info(f"  After dedup: {len(unique_tables)} unique table(s)")

        self.all_tables = [t.df for t in unique_tables]

        if len(unique_tables) == 0:
            logger.warning("[NO TABLES FOUND] PDF may be image-based or have no tables")
            return []

        # Debug: Show tables found
        for i, table in enumerate(unique_tables[:10]):
            df = table.df
            logger.info(f"\n  Table {i+1} (Page {table.page}, {len(df)} rows x {len(df.columns)} cols):")
            for j in range(min(3, len(df))):
                row_text = ' | '.join(str(cell)[:30] for cell in df.iloc[j])
                logger.info(f"    Row {j}: {row_text[:100]}...")

        # Step 3: Classify tables by statement type
        logger.info("\n>>> Step 3: Classifying tables...")
        logger.info("-" * 70)
        classified = self._classify_tables(unique_tables)

        for stmt_type, table_list in classified.items():
            if len(table_list) > 0:
                logger.info(f"  - {stmt_type}: {len(table_list)} table(s)")

        if self.unclassified_tables:
            logger.info(f"  - unclassified: {len(self.unclassified_tables)} table(s)")

        # Step 4: Extract line items from tables
        logger.info("\n>>> Step 4: Extracting line items...")
        logger.info("-" * 70)

        for statement_type, table_list in classified.items():
            if len(table_list) > 0:
                statement = self._process_statement(statement_type, table_list)
                if statement and statement.line_items:
                    self.statements.append(statement)
                    logger.info(f"  {statement_type}: {len(statement.line_items)} items")
                    # Log some sample items
                    for item in statement.line_items[:5]:
                        logger.info(f"    - {item.line_item}: {item.values}")

        # Process unclassified tables (might contain financial data)
        if self.unclassified_tables:
            statement = self._process_unclassified_tables()
            if statement and statement.line_items:
                self.statements.append(statement)
                logger.info(f"  unclassified: {len(statement.line_items)} items")

        self._log_summary()
        return self.statements

    def _find_financial_pages(self) -> List[int]:
        """Scan PDF to find pages containing financial statements"""
        financial_pages = []

        try:
            doc = fitz.open(self.pdf_path)

            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text().lower()

                # Check for financial statement indicators
                bs_score = sum(1 for kw in self.BALANCE_SHEET_KEYWORDS if kw in text)
                is_score = sum(1 for kw in self.INCOME_STATEMENT_KEYWORDS if kw in text)
                cf_score = sum(1 for kw in self.CASH_FLOW_KEYWORDS if kw in text)

                # If page has multiple financial keywords, it's likely a financial statement
                if bs_score >= 3 or is_score >= 3 or cf_score >= 2:
                    financial_pages.append(page_num + 1)  # Camelot uses 1-based pages
                    logger.info(f"    Page {page_num + 1}: BS={bs_score}, IS={is_score}, CF={cf_score}")

            doc.close()

        except Exception as e:
            logger.warning(f"  Could not scan pages: {e}")
            # Fallback: return all pages
            return list(range(1, min(self.page_count + 1, 51)))

        return financial_pages

    def _extract_with_lattice(self, pages: str) -> List:
        """Extract tables using lattice mode (for bordered tables)"""
        try:
            tables = camelot.read_pdf(
                self.pdf_path,
                pages=pages,
                flavor='lattice',
                split_text=True,
                line_scale=40,
                process_background=True
            )
            return list(tables)
        except Exception as e:
            logger.warning(f"  Lattice extraction failed: {e}")
            return []

    def _extract_with_stream(self, pages: str) -> List:
        """Extract tables using stream mode (for borderless tables)"""
        try:
            tables = camelot.read_pdf(
                self.pdf_path,
                pages=pages,
                flavor='stream',
                edge_tol=100,
                row_tol=15,
                column_tol=10
            )
            return list(tables)
        except Exception as e:
            logger.warning(f"  Stream extraction failed: {e}")
            return []

    def _deduplicate_tables(self, tables: List) -> List:
        """Remove duplicate tables based on content and page"""
        unique = []
        seen_hashes = set()
        seen_content = set()

        for table in tables:
            df = table.df

            # Skip very small tables
            if len(df) < 3 or len(df.columns) < 2:
                continue

            # Skip tables that are mostly empty
            non_empty_cells = sum(1 for col in df.columns for val in df[col] if str(val).strip())
            total_cells = len(df) * len(df.columns)
            if non_empty_cells < total_cells * 0.3:
                continue

            # Create hash of table content
            content_str = df.to_string()
            h = hash(content_str)

            # Also create a simplified content key (first column values)
            first_col_key = '|'.join(str(v).strip()[:50] for v in df.iloc[:, 0] if str(v).strip())

            if h not in seen_hashes and first_col_key not in seen_content:
                unique.append(table)
                seen_hashes.add(h)
                if first_col_key:
                    seen_content.add(first_col_key)

        return unique

    def _classify_tables(self, tables: List) -> Dict[str, List[pd.DataFrame]]:
        """Classify tables by statement type based on keywords"""
        classified = {
            "balance_sheet": [],
            "income_statement": [],
            "cash_flow": []
        }

        for table in tables:
            df = table.df
            stmt_type = self._identify_statement_type(df)

            if stmt_type:
                classified[stmt_type].append(df)
            elif self._has_financial_data(df):
                # Try to guess based on content
                guessed_type = self._guess_statement_type_from_content(df)
                if guessed_type:
                    classified[guessed_type].append(df)
                else:
                    self.unclassified_tables.append(df)

        return classified

    def _guess_statement_type_from_content(self, df: pd.DataFrame) -> Optional[str]:
        """Guess statement type based on line item content"""
        text = df.to_string().lower()

        # Count specific line item patterns
        asset_patterns = ['cash', 'receivable', 'inventory', 'property', 'equipment', 'investment']
        liability_patterns = ['payable', 'borrowing', 'loan', 'debt', 'provision']
        income_patterns = ['revenue', 'sales', 'income', 'expense', 'profit', 'cost']

        asset_count = sum(1 for p in asset_patterns if p in text)
        liability_count = sum(1 for p in liability_patterns if p in text)
        income_count = sum(1 for p in income_patterns if p in text)

        if asset_count >= 2 or liability_count >= 2:
            return "balance_sheet"
        elif income_count >= 2:
            return "income_statement"

        return None

    def _has_financial_data(self, df: pd.DataFrame) -> bool:
        """Check if table contains financial numbers"""
        count = 0
        for col in df.columns:
            for cell in df[col]:
                if self._parse_number(cell) is not None:
                    count += 1
                    if count >= 5:
                        return True
        return False

    def _identify_statement_type(self, df: pd.DataFrame) -> Optional[str]:
        """Identify statement type from table content"""
        df_str = df.to_string().lower()

        bs_count = sum(1 for kw in self.BALANCE_SHEET_KEYWORDS if kw in df_str)
        is_count = sum(1 for kw in self.INCOME_STATEMENT_KEYWORDS if kw in df_str)
        cf_count = sum(1 for kw in self.CASH_FLOW_KEYWORDS if kw in df_str)

        # Need at least 2 keyword matches for confident classification
        if bs_count >= 2 and bs_count >= is_count and bs_count >= cf_count:
            return "balance_sheet"
        elif is_count >= 2 and is_count >= bs_count and is_count >= cf_count:
            return "income_statement"
        elif cf_count >= 2:
            return "cash_flow"

        # Fallback: check if any keywords match with lower threshold
        if bs_count >= 1:
            return "balance_sheet"
        elif is_count >= 1:
            return "income_statement"
        elif cf_count >= 1:
            return "cash_flow"

        return None

    def _process_statement(self, stmt_type: str, tables: List[pd.DataFrame]) -> Optional[ExtractedStatement]:
        """Process tables for a specific statement type"""
        if not tables:
            return None

        # Extract years from all tables
        years = set()
        for df in tables:
            years.update(self._extract_years(df))

        years = sorted(list(years), reverse=True)
        if not years:
            years = self._extract_years_aggressive(tables)

        if not years:
            # Default to recent years if none found
            years = [2024, 2023]

        logger.info(f"    Years found for {stmt_type}: {years}")

        # Extract line items from all tables
        items = []
        for df in tables:
            extracted = self._extract_line_items(df, years)
            items.extend(extracted)
            logger.info(f"    Extracted {len(extracted)} items from table")

        # Deduplicate items
        items = self._deduplicate_line_items(items)

        if not items:
            return None

        return ExtractedStatement(
            statement_type=stmt_type,
            years=years,
            line_items=items,
            raw_tables=tables
        )

    def _deduplicate_line_items(self, items: List[ExtractedLineItem]) -> List[ExtractedLineItem]:
        """Remove duplicate line items, keeping the one with most values"""
        seen = {}

        for item in items:
            key = item.line_item.lower().strip()
            key = re.sub(r'\s+', ' ', key)

            if key in seen:
                # Keep the one with more values
                if len(item.values) > len(seen[key].values):
                    seen[key] = item
            else:
                seen[key] = item

        return list(seen.values())

    def _process_unclassified_tables(self) -> Optional[ExtractedStatement]:
        """Process unclassified tables"""
        if not self.unclassified_tables:
            return None

        years = set()
        for df in self.unclassified_tables:
            years.update(self._extract_years(df))

        years = sorted(list(years), reverse=True)
        if not years:
            years = self._extract_years_aggressive(self.unclassified_tables)

        items = []
        for df in self.unclassified_tables:
            items.extend(self._extract_line_items(df, years))

        items = self._deduplicate_line_items(items)

        if not items:
            return None

        return ExtractedStatement(
            statement_type="unclassified",
            years=years,
            line_items=items,
            raw_tables=self.unclassified_tables
        )

    def _extract_years(self, df: pd.DataFrame) -> List[int]:
        """Extract fiscal years from table headers and first rows"""
        years = []
        current_year = 2025

        # Check all cells in first 5 rows
        for i in range(min(5, len(df))):
            for cell in df.iloc[i]:
                if cell and isinstance(cell, str):
                    # Look for year patterns: 2023, 2023-24, FY2023, Mar 2023, etc.
                    matches = re.findall(r'\b(20\d{2}|19\d{2})\b', cell)
                    years.extend([int(y) for y in matches])

                    # Also check for FY patterns like "2023-24"
                    fy_matches = re.findall(r'(\d{4})-(\d{2})\b', cell)
                    for fy in fy_matches:
                        years.append(int(fy[0]))

        # Check column names/headers
        for col in df.columns:
            col_str = str(col)
            matches = re.findall(r'\b(20\d{2}|19\d{2})\b', col_str)
            years.extend([int(y) for y in matches])

        # Filter valid years (within reasonable range)
        years = [y for y in set(years) if current_year - 20 <= y <= current_year + 1]
        return sorted(years, reverse=True)

    def _extract_years_aggressive(self, tables: List[pd.DataFrame]) -> List[int]:
        """Aggressively search for years in all table content"""
        years = set()
        current_year = 2025

        for df in tables:
            text = df.to_string()
            matches = re.findall(r'\b(20\d{2}|19\d{2})\b', text)
            years.update([int(y) for y in matches])

        years = [y for y in years if current_year - 20 <= y <= current_year + 1]
        return sorted(list(years), reverse=True)[:5]  # Return top 5 years

    def _extract_line_items(self, df: pd.DataFrame, years: List[int]) -> List[ExtractedLineItem]:
        """Extract financial line items from a table"""
        items = []
        numeric_cols = self._find_numeric_columns(df)

        if not numeric_cols:
            logger.info(f"      No numeric columns found in table")
            return []

        logger.info(f"      Numeric columns: {numeric_cols}, Years: {years}")

        for idx, row in df.iterrows():
            # Get text from first column (description)
            text = str(row.iloc[0]).strip() if len(row) > 0 else ""

            # Skip empty or invalid rows
            if not text or len(text) < 3:
                continue

            # Skip header rows
            if re.match(r'^(20\d{2}|19\d{2}|note\s*\d+|\d+|sr\.?\s*no\.?|s\.?\s*no\.?)$', text, re.I):
                continue
            if text.lower() in ['particulars', 'description', 'item', 'note', 'notes', 'sr', 'no',
                               'sr.no', 'sr. no.', 'schedule', 'amount', 'total', '']:
                continue

            # Skip rows that are just numbers
            if re.match(r'^[\d,.\s()-]+$', text):
                continue

            # Match to taxonomy
            canonical = taxonomy.match_line_item(text)

            # Extract numeric values
            values = {}
            for i, col_idx in enumerate(numeric_cols):
                if col_idx < len(row):
                    val = self._parse_number(row.iloc[col_idx])
                    if val is not None:
                        if i < len(years):
                            values[years[i]] = val
                        else:
                            # Assign to estimated year
                            values[2020 - i] = val

            if not values:
                continue

            if canonical:
                info = taxonomy.items[canonical]
                items.append(ExtractedLineItem(
                    line_item=text,
                    canonical_name=canonical,
                    category=info.category,
                    parent=info.parent,
                    level=info.level,
                    values=values,
                    confidence=1.0
                ))
            else:
                items.append(ExtractedLineItem(
                    line_item=text,
                    canonical_name=None,
                    category=self._guess_category(text),
                    parent=None,
                    level=0,
                    values=values,
                    confidence=0.7
                ))

        return items

    def _find_numeric_columns(self, df: pd.DataFrame) -> List[int]:
        """Find columns that contain numeric data"""
        cols = []
        for col_idx in range(1, len(df.columns)):
            count = 0
            for row_idx in range(len(df)):
                if self._parse_number(df.iloc[row_idx, col_idx]) is not None:
                    count += 1
            # Column should have at least 20% numeric values
            if count > len(df) * 0.2:
                cols.append(col_idx)
        return cols

    def _guess_category(self, text: str) -> str:
        """Guess category based on text content"""
        t = text.lower()

        if any(kw in t for kw in ['asset', 'receivable', 'inventory', 'cash', 'bank', 'investment',
                                   'property', 'plant', 'equipment', 'prepaid', 'deposit', 'loan given']):
            return 'asset'
        if any(kw in t for kw in ['liability', 'payable', 'borrowing', 'loan', 'debt', 'provision',
                                   'accrued', 'deferred', 'creditor']):
            return 'liability'
        if any(kw in t for kw in ['equity', 'capital', 'reserve', 'surplus', 'retained', 'share']):
            return 'equity'
        if any(kw in t for kw in ['revenue', 'income', 'sales', 'turnover', 'receipt']):
            return 'revenue'
        if any(kw in t for kw in ['expense', 'cost', 'depreciation', 'amortization', 'interest',
                                   'tax', 'salary', 'wage', 'rent', 'payment']):
            return 'expense'
        if any(kw in t for kw in ['cash flow', 'operating', 'investing', 'financing']):
            return 'cashflow'

        return 'unknown'

    def _parse_number(self, value: Any) -> Optional[float]:
        """Parse number from various formats including Indian number system"""
        if value is None or value == '' or pd.isna(value):
            return None

        try:
            s = str(value).strip()
            if not s or s in ['-', '--', '---', '–', '—', 'nil', 'Nil', 'NIL', '*', '**']:
                return None

            # Remove currency symbols and formatting
            s = s.replace(',', '').replace('₹', '').replace('$', '').replace('€', '')
            s = s.replace('Rs.', '').replace('Rs', '').replace('INR', '').replace('Lacs', '')
            s = s.replace('Lakhs', '').replace('Crores', '').replace('Cr', '').replace('L', '')
            s = s.replace("'", '').replace(' ', '').strip()

            # Handle parentheses as negative
            if s.startswith('(') and s.endswith(')'):
                s = '-' + s[1:-1]

            # Remove non-numeric chars except . and -
            s = re.sub(r'[^\d.-]', '', s)

            if s and s not in ['-', '.', '-.']:
                num = float(s)
                # Filter out year-like numbers
                if 1900 < abs(num) < 2100 and abs(num) == int(abs(num)):
                    return None
                return num

        except (ValueError, AttributeError):
            pass

        return None

    def _log_summary(self):
        """Log extraction summary"""
        logger.info("")
        logger.info("=" * 70)
        logger.info("  EXTRACTION SUMMARY")
        logger.info("=" * 70)
        logger.info(f"Method: Camelot Table Extraction (Enhanced)")
        logger.info(f"Statements: {len(self.statements)}")

        total_items = 0
        all_years = set()
        for stmt in self.statements:
            logger.info(f"  - {stmt.statement_type}: {len(stmt.line_items)} items, Years: {stmt.years}")
            total_items += len(stmt.line_items)
            all_years.update(stmt.years)

        logger.info(f"Total Line Items: {total_items}")
        logger.info(f"Fiscal Years: {sorted(all_years, reverse=True)}")
        logger.info("=" * 70)

    def get_hierarchical_data(self) -> Dict[str, Any]:
        """Get hierarchical data structure for frontend display"""
        return {
            "balance_sheet": self._build_hierarchy("asset") + self._build_hierarchy("liability") + self._build_hierarchy("equity"),
            "income_statement": self._build_hierarchy("revenue") + self._build_hierarchy("expense"),
            "cash_flow": self._build_hierarchy("cashflow")
        }

    def _build_hierarchy(self, category: str) -> List[Dict]:
        """Build hierarchy for a category"""
        items = []
        for stmt in self.statements:
            for item in stmt.line_items:
                if item.category == category:
                    items.append(item)

        root_items = [i for i in items if i.parent is None]
        return [self._build_tree(i, items) for i in root_items]

    def _build_tree(self, item: ExtractedLineItem, all_items: List[ExtractedLineItem]) -> Dict:
        """Build tree node for hierarchical view"""
        children = [i for i in all_items if i.parent == item.canonical_name]
        return {
            "line_item": item.line_item,
            "canonical_name": item.canonical_name,
            "category": item.category,
            "level": item.level,
            "values": item.values,
            "confidence": item.confidence,
            "children": [self._build_tree(c, all_items) for c in children]
        }


def extract_financial_data_camelot(pdf_path: str) -> Dict[str, Any]:
    """Main entry point for extraction"""
    extractor = CamelotExtractor(pdf_path)
    statements = extractor.extract_all()
    return {
        "statements": statements,
        "hierarchical_data": extractor.get_hierarchical_data()
    }
