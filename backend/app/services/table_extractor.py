"""
Table Extraction Module

Reconstructs tables from OCR word bounding boxes by clustering:
- Y coordinates -> rows
- X coordinates -> columns

Handles:
- Multi-column financial statements (current year, previous year)
- Merged cells and headers
- Number parsing (commas, decimals, parentheses for negatives)
"""

import re
import logging
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict
from statistics import median, stdev

logger = logging.getLogger(__name__)


@dataclass
class TableCell:
    """A cell in a reconstructed table."""
    text: str
    row: int
    col: int
    x: int
    y: int
    width: int
    height: int
    is_header: bool = False
    is_number: bool = False
    numeric_value: Optional[float] = None


@dataclass
class TableRow:
    """A row in a reconstructed table."""
    row_num: int
    cells: List[TableCell] = field(default_factory=list)
    y_center: float = 0
    raw_text: str = ""

    def get_label(self) -> str:
        """Get the row label (usually first column)."""
        if self.cells:
            return self.cells[0].text
        return ""

    def get_values(self) -> List[Optional[float]]:
        """Get numeric values from the row."""
        return [c.numeric_value for c in self.cells[1:] if c.is_number]


@dataclass
class ExtractedTable:
    """A fully reconstructed table."""
    rows: List[TableRow] = field(default_factory=list)
    headers: List[str] = field(default_factory=list)
    column_years: List[int] = field(default_factory=list)  # Detected fiscal years
    scale: Optional[str] = None  # 'lakhs', 'crores', 'thousands', 'millions'
    currency: Optional[str] = None  # 'INR', 'USD', etc.
    page_num: int = 0


class TableExtractor:
    """
    Extracts structured tables from OCR word bounding boxes.

    Usage:
        extractor = TableExtractor()
        tables = extractor.extract_tables(word_boxes, page_num=5)
    """

    # Clustering thresholds (in pixels, calibrated for 300 DPI)
    ROW_CLUSTER_THRESHOLD = 15  # Words within this Y distance are same row
    COL_CLUSTER_THRESHOLD = 30  # Words within this X distance might be same column

    # Number patterns
    NUMBER_PATTERN = re.compile(
        r'^[\(\-]?\s*[\d,]+(?:\.\d+)?\s*[\)]?$'
    )

    # Scale detection patterns
    SCALE_PATTERNS = [
        (re.compile(r'(?:₹|rs\.?|inr)\s*in\s*lakhs?', re.I), 'lakhs', 'INR'),
        (re.compile(r'(?:₹|rs\.?|inr)\s*in\s*crores?', re.I), 'crores', 'INR'),
        (re.compile(r'in\s*lakhs?', re.I), 'lakhs', 'INR'),
        (re.compile(r'in\s*crores?', re.I), 'crores', 'INR'),
        (re.compile(r'in\s*thousands?', re.I), 'thousands', None),
        (re.compile(r'in\s*millions?', re.I), 'millions', None),
        (re.compile(r'\(\s*₹\s*\)', re.I), None, 'INR'),
        (re.compile(r'\(\s*\$\s*\)', re.I), None, 'USD'),
    ]

    # Year patterns
    YEAR_PATTERN = re.compile(r'(?:FY\s*)?(?:20)?(\d{2})(?:\s*-\s*(?:20)?(\d{2}))?')

    def __init__(self):
        pass

    def _parse_number(self, text: str) -> Optional[float]:
        """
        Parse a number from text.

        Handles:
        - Commas: 1,234,567
        - Decimals: 1234.56
        - Parentheses for negatives: (1234.56) -> -1234.56
        - Dash for negatives: -1234.56
        """
        if not text:
            return None

        text = text.strip()

        # Check if it's a number
        if not self.NUMBER_PATTERN.match(text):
            return None

        try:
            # Check for negative (parentheses)
            is_negative = text.startswith('(') and text.endswith(')')
            if is_negative:
                text = text[1:-1]

            # Check for negative (dash)
            if text.startswith('-'):
                is_negative = True
                text = text[1:]

            # Remove commas and spaces
            text = text.replace(',', '').replace(' ', '')

            # Parse
            value = float(text)
            return -value if is_negative else value

        except ValueError:
            return None

    def _cluster_by_y(
        self,
        word_boxes: List[Dict],
        threshold: int = None
    ) -> List[List[Dict]]:
        """
        Cluster words into rows by Y coordinate.
        """
        if not word_boxes:
            return []

        threshold = threshold or self.ROW_CLUSTER_THRESHOLD

        # Sort by Y coordinate
        sorted_boxes = sorted(word_boxes, key=lambda w: w['y'])

        rows = []
        current_row = [sorted_boxes[0]]
        current_y = sorted_boxes[0]['y']

        for box in sorted_boxes[1:]:
            if abs(box['y'] - current_y) <= threshold:
                current_row.append(box)
            else:
                # New row
                rows.append(current_row)
                current_row = [box]
                current_y = box['y']

        if current_row:
            rows.append(current_row)

        # Sort words within each row by X coordinate
        for row in rows:
            row.sort(key=lambda w: w['x'])

        return rows

    def _detect_columns(
        self,
        rows: List[List[Dict]]
    ) -> List[int]:
        """
        Detect column boundaries from row data.

        Returns list of X coordinates for column starts.
        """
        # Collect all X positions
        all_x = []
        for row in rows:
            for box in row:
                all_x.append(box['x'])

        if not all_x:
            return []

        # Find clusters of X positions
        all_x.sort()

        # Use histogram-based approach
        min_x, max_x = min(all_x), max(all_x)
        width = max_x - min_x

        if width < 100:  # Too narrow
            return [min_x]

        # Expect 2-5 columns typically
        # First column is label, rest are data columns
        # Estimate column width
        estimated_cols = 3
        col_width = width / estimated_cols

        # Find peaks in X distribution
        columns = [min_x]

        # Simple approach: look for gaps
        prev_x = all_x[0]
        for x in all_x[1:]:
            gap = x - prev_x
            if gap > col_width * 0.5:  # Significant gap
                columns.append(x)
            prev_x = x

        return sorted(set(columns))

    def _assign_columns(
        self,
        row_boxes: List[Dict],
        column_starts: List[int]
    ) -> List[TableCell]:
        """
        Assign words to columns based on X position.
        """
        if not column_starts:
            column_starts = [0]

        cells = []

        for col_idx, col_start in enumerate(column_starts):
            # Find end of this column
            if col_idx + 1 < len(column_starts):
                col_end = column_starts[col_idx + 1]
            else:
                col_end = float('inf')

            # Collect words in this column
            col_words = [
                box for box in row_boxes
                if col_start <= box['x'] < col_end
            ]

            if col_words:
                # Combine words
                text = ' '.join(w['text'] for w in col_words)
                x = min(w['x'] for w in col_words)
                y = min(w['y'] for w in col_words)
                width = max(w['x'] + w['width'] for w in col_words) - x
                height = max(w['height'] for w in col_words)

                # Check if number
                numeric_value = self._parse_number(text)

                cells.append(TableCell(
                    text=text,
                    row=0,  # Will be set later
                    col=col_idx,
                    x=x,
                    y=y,
                    width=width,
                    height=height,
                    is_number=numeric_value is not None,
                    numeric_value=numeric_value
                ))

        return cells

    def _detect_scale_and_currency(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Detect scale (lakhs, crores, etc.) and currency from header text.
        """
        for pattern, scale, currency in self.SCALE_PATTERNS:
            if pattern.search(text):
                return scale, currency
        return None, None

    def _detect_years(self, text: str) -> List[int]:
        """
        Detect fiscal years from header text.
        """
        years = []

        # Look for year patterns
        matches = self.YEAR_PATTERN.findall(text)
        for match in matches:
            year1, year2 = match
            if year1:
                year = int(year1)
                if year < 50:
                    year += 2000
                elif year < 100:
                    year += 1900
                years.append(year)
            if year2:
                year = int(year2)
                if year < 50:
                    year += 2000
                elif year < 100:
                    year += 1900
                years.append(year)

        # Also look for full years
        full_years = re.findall(r'\b(20\d{2})\b', text)
        years.extend(int(y) for y in full_years)

        # Also look for date patterns like "March 31, 2023"
        date_years = re.findall(
            r'(?:march|mar|31st?\s+march)\s*,?\s*(20\d{2})',
            text,
            re.I
        )
        years.extend(int(y) for y in date_years)

        return sorted(set(years), reverse=True)

    def extract_tables(
        self,
        word_boxes: List[Dict],
        page_num: int = 0,
        header_rows: int = 3
    ) -> List[ExtractedTable]:
        """
        Extract tables from OCR word bounding boxes.
        """
        if not word_boxes:
            return []

        # Cluster into rows
        row_clusters = self._cluster_by_y(word_boxes)

        if not row_clusters:
            return []

        # Detect columns
        column_starts = self._detect_columns(row_clusters)

        # Build table
        table = ExtractedTable(page_num=page_num)

        # Process header rows for scale/currency/years
        header_text = ""
        for row_boxes in row_clusters[:header_rows]:
            header_text += " ".join(w['text'] for w in row_boxes) + " "

        scale, currency = self._detect_scale_and_currency(header_text)
        table.scale = scale
        table.currency = currency
        table.column_years = self._detect_years(header_text)

        logger.debug(f"Detected scale={scale}, currency={currency}, years={table.column_years}")

        # Build rows
        for row_idx, row_boxes in enumerate(row_clusters):
            cells = self._assign_columns(row_boxes, column_starts)

            # Update row index in cells
            for cell in cells:
                cell.row = row_idx

            raw_text = " ".join(w['text'] for w in row_boxes)

            table_row = TableRow(
                row_num=row_idx,
                cells=cells,
                y_center=sum(w['y'] for w in row_boxes) / len(row_boxes),
                raw_text=raw_text
            )

            table.rows.append(table_row)

        return [table]

    def extract_from_text(
        self,
        text: str,
        page_num: int = 0
    ) -> Tuple[Optional[str], Optional[str], List[int], str]:
        """
        Extract scale, currency, and years from plain text.

        Returns: (scale, currency, years, cleaned_text)
        """
        scale, currency = self._detect_scale_and_currency(text)
        years = self._detect_years(text)

        return scale, currency, years, text


def reconstruct_table_from_ocr(
    word_boxes: List[Dict],
    page_num: int = 0
) -> List[ExtractedTable]:
    """
    Convenience function to reconstruct tables from OCR output.
    """
    extractor = TableExtractor()
    return extractor.extract_tables(word_boxes, page_num)


def parse_financial_number(text: str) -> Optional[float]:
    """
    Convenience function to parse a financial number.
    """
    extractor = TableExtractor()
    return extractor._parse_number(text)
