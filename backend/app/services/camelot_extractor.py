"""
Camelot-Based Financial Data Extractor (No LLM)
Extracts ALL financial data from PDFs using table detection
"""

import camelot
import pandas as pd
import re
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field

from app.services.financial_taxonomy import taxonomy

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ExtractedLineItem:
    """Represents a single extracted financial line item"""
    line_item: str  # Original text
    canonical_name: Optional[str]  # Matched canonical name
    category: str  # asset, liability, equity, revenue, expense, cashflow
    parent: Optional[str]  # Parent in hierarchy
    level: int  # Hierarchy level
    values: Dict[int, float] = field(default_factory=dict)  # {year: value}
    confidence: float = 1.0


@dataclass
class ExtractedStatement:
    """Represents an extracted financial statement"""
    statement_type: str  # "balance_sheet", "income_statement", "cash_flow"
    years: List[int]
    line_items: List[ExtractedLineItem]
    raw_tables: List[pd.DataFrame] = field(default_factory=list)


class CamelotExtractor:
    """Extract financial data using Camelot"""

    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.statements: List[ExtractedStatement] = []

    def extract_all(self) -> List[ExtractedStatement]:
        """Extract all financial data from PDF"""
        logger.info("=" * 70)
        logger.info(f"  CAMELOT TABLE EXTRACTOR")
        logger.info("=" * 70)
        logger.info(f"PDF File: {self.pdf_path}")
        logger.info("")

        # Step 1: Extract all tables from PDF
        logger.info(">>> Step 1: Extracting tables from PDF...")
        logger.info("-" * 70)
        tables = self._extract_tables()

        if len(tables) == 0:
            logger.warning("[NO TABLES FOUND] PDF appears to be image-based or has no tables")
            logger.info("  Camelot requires text-based PDFs with extractable tables")
            return []

        logger.info(f"[SUCCESS] Extracted {len(tables)} tables from PDF")
        logger.info("")

        # Step 2: Classify tables by statement type
        logger.info(">>> Step 2: Classifying tables by statement type...")
        logger.info("-" * 70)
        classified = self._classify_tables(tables)

        for stmt_type, table_list in classified.items():
            count = len(table_list)
            if count > 0:
                logger.info(f"  - {stmt_type}: {count} table(s)")
        logger.info("")

        # Step 3: Process each statement type
        logger.info(">>> Step 3: Processing and matching line items...")
        logger.info("-" * 70)
        for statement_type, table_list in classified.items():
            if len(table_list) > 0:
                logger.info(f"  Processing {statement_type}...")
                statement = self._process_statement(statement_type, table_list)
                if statement:
                    self.statements.append(statement)
                    logger.info(f"    [OK] {len(statement.line_items)} line items extracted")

        logger.info("")
        logger.info("=" * 70)
        logger.info(f"  CAMELOT EXTRACTION SUMMARY")
        logger.info("=" * 70)
        logger.info(f"Statements extracted: {len(self.statements)}")
        for stmt in self.statements:
            logger.info(f"  - {stmt.statement_type}: {len(stmt.line_items)} items, Years: {stmt.years}")
        logger.info("=" * 70)
        logger.info("")

        return self.statements

    def _extract_tables(self) -> List[camelot.core.Table]:
        """Extract all tables from PDF using Camelot"""
        try:
            # Try lattice mode first (works best for tables with borders)
            logger.info("  Trying LATTICE mode (for tables with borders)...")
            tables_lattice = camelot.read_pdf(
                self.pdf_path,
                pages='all',
                flavor='lattice',
                split_text=True
            )

            logger.info(f"  Lattice mode: {len(tables_lattice)} table(s) found")

            # If few tables found, try stream mode (works for borderless tables)
            if len(tables_lattice) < 3:
                logger.info("  Few tables found, trying STREAM mode (for borderless tables)...")
                tables_stream = camelot.read_pdf(
                    self.pdf_path,
                    pages='all',
                    flavor='stream',
                    edge_tol=50
                )
                logger.info(f"  Stream mode: {len(tables_stream)} table(s) found")

                # Combine results
                logger.info("  Combining and deduplicating results...")
                all_tables = list(tables_lattice) + list(tables_stream)
                deduplicated = self._deduplicate_tables(all_tables)
                logger.info(f"  After deduplication: {len(deduplicated)} unique table(s)")
                return deduplicated

            return list(tables_lattice)

        except Exception as e:
            logger.error(f"[ERROR] Camelot extraction failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []

    def _deduplicate_tables(self, tables: List[camelot.core.Table]) -> List[camelot.core.Table]:
        """Remove duplicate tables"""
        unique_tables = []
        seen_hashes = set()

        for table in tables:
            # Create hash of table content
            df = table.df
            content_hash = hash(df.to_string())

            if content_hash not in seen_hashes:
                unique_tables.append(table)
                seen_hashes.add(content_hash)

        return unique_tables

    def _classify_tables(self, tables: List[camelot.core.Table]) -> Dict[str, List[pd.DataFrame]]:
        """Classify tables by financial statement type"""
        classified = {
            "balance_sheet": [],
            "income_statement": [],
            "cash_flow": []
        }

        for table in tables:
            df = table.df
            statement_type = self._identify_statement_type(df)

            if statement_type:
                classified[statement_type].append(df)

        return classified

    def _identify_statement_type(self, df: pd.DataFrame) -> Optional[str]:
        """Identify which financial statement this table belongs to"""
        # Convert all cells to lowercase for matching
        df_str = df.to_string().lower()

        # Balance Sheet keywords
        bs_keywords = [
            "balance sheet", "statement of financial position",
            "total assets", "total liabilities",
            "shareholders equity", "stockholders equity"
        ]

        # Income Statement keywords
        is_keywords = [
            "income statement", "profit and loss", "profit & loss",
            "statement of comprehensive income", "statement of income",
            "revenue", "net income", "gross profit"
        ]

        # Cash Flow keywords
        cf_keywords = [
            "cash flow", "statement of cash flows",
            "operating activities", "investing activities",
            "financing activities"
        ]

        # Count keyword matches
        bs_count = sum(1 for kw in bs_keywords if kw in df_str)
        is_count = sum(1 for kw in is_keywords if kw in df_str)
        cf_count = sum(1 for kw in cf_keywords if kw in df_str)

        # Return type with most matches (minimum 2 matches required)
        if bs_count >= 2 and bs_count >= is_count and bs_count >= cf_count:
            return "balance_sheet"
        elif is_count >= 2 and is_count >= bs_count and is_count >= cf_count:
            return "income_statement"
        elif cf_count >= 2:
            return "cash_flow"

        return None

    def _process_statement(self, statement_type: str,
                          tables: List[pd.DataFrame]) -> Optional[ExtractedStatement]:
        """Process tables for a specific statement type"""
        if not tables:
            return None

        # Step 1: Identify year columns
        years = self._extract_years(tables[0])
        logger.info(f"{statement_type}: Detected years {years}")

        # Step 2: Extract line items from all tables
        all_line_items = []

        for df in tables:
            line_items = self._extract_line_items(df, years)
            all_line_items.extend(line_items)

        logger.info(f"{statement_type}: Extracted {len(all_line_items)} line items")

        # Step 3: Create statement
        return ExtractedStatement(
            statement_type=statement_type,
            years=years,
            line_items=all_line_items,
            raw_tables=tables
        )

    def _extract_years(self, df: pd.DataFrame) -> List[int]:
        """Extract fiscal years from table headers"""
        years = []

        # Check first few rows for years
        for i in range(min(3, len(df))):
            row = df.iloc[i]

            for cell in row:
                if cell and isinstance(cell, str):
                    # Look for 4-digit years
                    year_matches = re.findall(r'\b(20\d{2}|19\d{2})\b', cell)
                    years.extend([int(y) for y in year_matches])

        # Remove duplicates and sort descending
        years = sorted(list(set(years)), reverse=True)

        return years

    def _extract_line_items(self, df: pd.DataFrame,
                           years: List[int]) -> List[ExtractedLineItem]:
        """Extract individual line items from table"""
        line_items = []

        # Iterate through rows
        for idx, row in df.iterrows():
            # First column is typically the line item name
            line_item_text = str(row[0]).strip()

            # Skip empty or header rows
            if not line_item_text or len(line_item_text) < 3:
                continue

            # Skip if it looks like a year or note reference
            if re.match(r'^(20\d{2}|19\d{2}|note\s+\d+)$', line_item_text, re.I):
                continue

            # Try to match to canonical name
            canonical_name = taxonomy.match_line_item(line_item_text)

            if canonical_name:
                item_info = taxonomy.items[canonical_name]

                # Extract values for each year
                values = {}
                for col_idx in range(1, min(len(row), len(years) + 1)):
                    value = self._parse_number(row[col_idx])
                    if value is not None:
                        year_idx = col_idx - 1
                        if year_idx < len(years):
                            values[years[year_idx]] = value

                if values:  # Only add if we extracted at least one value
                    line_items.append(ExtractedLineItem(
                        line_item=line_item_text,
                        canonical_name=canonical_name,
                        category=item_info.category,
                        parent=item_info.parent,
                        level=item_info.level,
                        values=values,
                        confidence=1.0
                    ))

            else:
                # Store unmatched items too (for review)
                values = {}
                for col_idx in range(1, min(len(row), len(years) + 1)):
                    value = self._parse_number(row[col_idx])
                    if value is not None:
                        year_idx = col_idx - 1
                        if year_idx < len(years):
                            values[years[year_idx]] = value

                if values:
                    line_items.append(ExtractedLineItem(
                        line_item=line_item_text,
                        canonical_name=None,  # Unmatched
                        category="unknown",
                        parent=None,
                        level=0,
                        values=values,
                        confidence=0.5
                    ))

        return line_items

    def _parse_number(self, value: Any) -> Optional[float]:
        """Parse a number from various formats"""
        if value is None or value == '':
            return None

        try:
            # Convert to string and clean
            value_str = str(value).strip()

            # Remove common formatting
            value_str = value_str.replace(',', '')
            value_str = value_str.replace('₹', '')
            value_str = value_str.replace('$', '')
            value_str = value_str.replace('€', '')
            value_str = value_str.strip()

            # Handle parentheses as negative
            if value_str.startswith('(') and value_str.endswith(')'):
                value_str = '-' + value_str[1:-1]

            # Remove any remaining non-numeric characters except . and -
            value_str = re.sub(r'[^\d.-]', '', value_str)

            if value_str and value_str not in ['-', '.']:
                return float(value_str)

        except (ValueError, AttributeError):
            pass

        return None

    def get_hierarchical_data(self) -> Dict[str, Any]:
        """Get data organized hierarchically"""
        result = {
            "balance_sheet": self._build_hierarchy("asset") + self._build_hierarchy("liability") + self._build_hierarchy("equity"),
            "income_statement": self._build_hierarchy("revenue") + self._build_hierarchy("expense"),
            "cash_flow": self._build_hierarchy("cashflow")
        }

        return result

    def _build_hierarchy(self, category: str) -> List[Dict]:
        """Build hierarchical structure for a category"""
        hierarchy = []

        # Get all items of this category
        items = [stmt.line_items for stmt in self.statements]
        flat_items = [item for sublist in items for item in sublist if item.category == category]

        # Group by parent
        root_items = [item for item in flat_items if item.parent is None]

        for root_item in root_items:
            hierarchy.append(self._build_tree(root_item, flat_items))

        return hierarchy

    def _build_tree(self, item: ExtractedLineItem, all_items: List[ExtractedLineItem]) -> Dict:
        """Recursively build tree structure"""
        node = {
            "line_item": item.line_item,
            "canonical_name": item.canonical_name,
            "level": item.level,
            "values": item.values,
            "children": []
        }

        # Find children
        children = [i for i in all_items if i.parent == item.canonical_name]

        for child in children:
            node["children"].append(self._build_tree(child, all_items))

        return node


def extract_financial_data_camelot(pdf_path: str) -> Dict[str, Any]:
    """Main entry point for Camelot extraction"""
    extractor = CamelotExtractor(pdf_path)
    statements = extractor.extract_all()

    return {
        "statements": statements,
        "hierarchical_data": extractor.get_hierarchical_data()
    }
