"""
Smart Page Finder Module

Features:
- TOC (Table of Contents) parsing to jump directly to statement pages
- Keyword-based page scoring for fallback detection
- Shared page index (score once, route to multiple statement types)
- Page offset calculation (printed page number vs PDF page index)
"""

import re
import logging
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass, field
from collections import defaultdict

from app.services.pdf_processor import PDFProcessor, PageData, PDFInfo

logger = logging.getLogger(__name__)


# ============================================================================
# KEYWORD DEFINITIONS
# ============================================================================

# Statement title keywords (high weight)
BALANCE_SHEET_TITLES = [
    'balance sheet',
    'statement of financial position',
    'statement of assets and liabilities',
    'consolidated balance sheet',
    'standalone balance sheet',
]

INCOME_STATEMENT_TITLES = [
    'statement of profit and loss',
    'profit and loss',
    'income statement',
    'statement of income',
    'statement of operations',
    'consolidated statement of profit',
    'standalone statement of profit',
]

CASH_FLOW_TITLES = [
    'cash flow statement',
    'statement of cash flows',
    'cash flow',
    'consolidated cash flow',
    'standalone cash flow',
]

# Content keywords (lower weight)
BALANCE_SHEET_KEYWORDS = [
    'total assets', 'total liabilities', 'shareholders equity', 'stockholders equity',
    'current assets', 'non-current assets', 'fixed assets', 'property plant equipment',
    'current liabilities', 'non-current liabilities', 'long-term debt',
    'retained earnings', 'share capital', 'equity share capital', 'reserves and surplus',
    'trade receivables', 'inventories', 'trade payables', 'cash and cash equivalents',
    'as at', 'as on',  # Common date indicators in balance sheets
]

INCOME_STATEMENT_KEYWORDS = [
    'revenue from operations', 'sales', 'turnover', 'net sales',
    'cost of goods sold', 'cost of materials consumed', 'cost of revenue',
    'gross profit', 'gross margin',
    'operating expenses', 'employee benefit expenses', 'depreciation',
    'operating income', 'operating profit', 'ebit', 'ebitda',
    'profit before tax', 'profit after tax', 'net profit', 'net income',
    'earnings per share', 'eps', 'basic eps', 'diluted eps',
    'for the year ended',  # Common date indicator in P&L
]

CASH_FLOW_KEYWORDS = [
    'operating activities', 'cash from operations', 'cash generated from operations',
    'investing activities', 'capital expenditure', 'purchase of fixed assets',
    'financing activities', 'proceeds from borrowings', 'repayment of borrowings',
    'net increase in cash', 'net decrease in cash', 'cash at beginning',
    'cash at end', 'cash and cash equivalents at end',
]

# TOC detection keywords
TOC_KEYWORDS = [
    'contents', 'table of contents', 'index', 'sr. no.', 'particulars',
    'page no', 'page number', 'pages'
]


@dataclass
class TOCEntry:
    """A single entry from the table of contents."""
    title: str
    printed_page: int
    statement_type: Optional[str] = None  # 'balance_sheet', 'income_statement', 'cash_flow'


@dataclass
class PageScore:
    """Score for a single page across all statement types."""
    page_num: int
    text: str
    text_length: int
    balance_sheet_score: int = 0
    income_statement_score: int = 0
    cash_flow_score: int = 0
    is_financial_page: bool = False
    matched_keywords: Dict[str, List[str]] = field(default_factory=dict)


@dataclass
class CandidatePages:
    """Candidate pages for each statement type."""
    balance_sheet: List[int] = field(default_factory=list)
    income_statement: List[int] = field(default_factory=list)
    cash_flow: List[int] = field(default_factory=list)
    toc_used: bool = False
    page_offset: int = 0  # PDF page - printed page


class PageFinder:
    """
    Finds relevant pages for financial statements.

    Strategy:
    1. Try to parse TOC from first 10 pages
    2. If TOC found, jump to listed pages (with offset calculation)
    3. If no TOC, fall back to keyword scanning all pages
    """

    def __init__(self, processor: PDFProcessor):
        self.processor = processor
        self.pdf_info: Optional[PDFInfo] = None
        self.page_index: Dict[int, PageScore] = {}
        self.toc_entries: List[TOCEntry] = []
        self.page_offset: int = 0

    def _score_text_for_keywords(
        self,
        text: str,
        title_keywords: List[str],
        content_keywords: List[str],
        title_weight: int = 20,
        content_weight: int = 2
    ) -> Tuple[int, List[str]]:
        """
        Score text for keyword matches.
        Title keywords get higher weight than content keywords.
        """
        text_lower = text.lower()
        score = 0
        matched = []

        # Check title keywords (high weight)
        for kw in title_keywords:
            if kw in text_lower:
                score += title_weight
                matched.append(f"TITLE:{kw}")

        # Check content keywords (lower weight)
        for kw in content_keywords:
            if kw in text_lower:
                score += content_weight
                matched.append(kw)

        # Bonus for high numeric density (financial tables have many numbers)
        numbers = re.findall(r'\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+\.\d+', text)
        if len(numbers) > 20:
            score += 10
            matched.append(f"NUMERIC_DENSITY:{len(numbers)}")

        return score, matched

    def _parse_toc_from_text(self, text: str) -> List[TOCEntry]:
        """
        Parse table of contents entries from text.

        Looks for patterns like:
        - "Balance Sheet ... 58"
        - "Statement of Profit and Loss....59"
        - "Cash Flow Statement 60"
        """
        entries = []
        text_lower = text.lower()

        # Check if this looks like a TOC page
        toc_score = sum(1 for kw in TOC_KEYWORDS if kw in text_lower)
        if toc_score < 2:
            return entries

        # Pattern: title followed by dots/spaces and page number
        # Handles: "Balance Sheet .......... 58" or "Balance Sheet 58"
        toc_pattern = re.compile(
            r'([A-Za-z][A-Za-z\s&\-\(\)]+?)\s*[\.…\-\s]{2,}\s*(\d{1,3})',
            re.MULTILINE
        )

        for match in toc_pattern.finditer(text):
            title = match.group(1).strip()
            page_num = int(match.group(2))

            # Skip very short titles or very high page numbers
            if len(title) < 5 or page_num > 500:
                continue

            # Determine statement type
            title_lower = title.lower()
            statement_type = None

            if any(kw in title_lower for kw in ['balance sheet', 'financial position', 'assets and liabilities']):
                statement_type = 'balance_sheet'
            elif any(kw in title_lower for kw in ['profit and loss', 'profit & loss', 'income statement', 'statement of profit']):
                statement_type = 'income_statement'
            elif any(kw in title_lower for kw in ['cash flow', 'cash flows']):
                statement_type = 'cash_flow'

            entries.append(TOCEntry(
                title=title,
                printed_page=page_num,
                statement_type=statement_type
            ))

        # Log found entries
        if entries:
            logger.info(f"Found {len(entries)} TOC entries")
            for entry in entries:
                if entry.statement_type:
                    logger.info(f"  TOC: '{entry.title}' -> page {entry.printed_page} ({entry.statement_type})")

        return entries

    def _calculate_page_offset(self, pages: List[PageData]) -> int:
        """
        Calculate offset between printed page numbers and PDF page indices.

        Strategy: Look for explicit page numbers like "Page 1" or "1" in footer/header
        on the first few content pages after TOC.
        """
        # Common patterns for page numbers
        page_patterns = [
            re.compile(r'^\s*page\s+(\d+)\s*$', re.IGNORECASE | re.MULTILINE),
            re.compile(r'^\s*-?\s*(\d{1,3})\s*-?\s*$', re.MULTILINE),  # Just number, possibly with dashes
            re.compile(r'\|\s*(\d{1,3})\s*$', re.MULTILINE),  # Number at end with pipe
        ]

        for page_data in pages:
            # Skip very short pages (likely blank or mostly images)
            if len(page_data.text) < 50:
                continue

            for pattern in page_patterns:
                matches = pattern.findall(page_data.text)
                if matches:
                    try:
                        printed_num = int(matches[-1])  # Use last match (usually footer)
                        if 1 <= printed_num <= 200:  # Reasonable page number
                            offset = page_data.page_num - printed_num
                            logger.info(f"Detected page offset: PDF page {page_data.page_num} = printed page {printed_num} (offset={offset})")
                            return offset
                    except ValueError:
                        continue

        logger.warning("Could not detect page offset, assuming offset=0")
        return 0

    def find_toc_and_candidates(
        self,
        toc_search_pages: int = 15,
        progress_callback=None
    ) -> CandidatePages:
        """
        PASS A: Find candidate pages using TOC or keyword scanning.

        1. Scan first N pages for TOC
        2. If TOC found, extract statement pages
        3. If no TOC, scan all pages with keyword scoring
        """
        self.pdf_info = self.processor.get_pdf_info()
        total_pages = self.pdf_info.total_pages

        logger.info(f"=== PASS A: Candidate Detection ({total_pages} pages) ===")

        candidates = CandidatePages()

        # Step 1: Try to find TOC in first N pages
        logger.info(f"Step 1: Scanning pages 0-{min(toc_search_pages, total_pages)} for TOC...")
        toc_pages = self.processor.extract_pages_low_res(
            list(range(min(toc_search_pages, total_pages)))
        )

        for page_data in toc_pages:
            entries = self._parse_toc_from_text(page_data.text)
            if entries:
                self.toc_entries.extend(entries)

        # Step 2: If TOC found, calculate offset and jump to pages
        if self.toc_entries:
            logger.info(f"Step 2: TOC found with {len(self.toc_entries)} entries")

            # Calculate page offset
            self.page_offset = self._calculate_page_offset(toc_pages)
            candidates.page_offset = self.page_offset
            candidates.toc_used = True

            # Convert printed pages to PDF pages
            for entry in self.toc_entries:
                if entry.statement_type:
                    pdf_page = entry.printed_page + self.page_offset

                    # Add ±2 page buffer for safety
                    page_range = [
                        p for p in range(max(0, pdf_page - 2), min(total_pages, pdf_page + 3))
                    ]

                    if entry.statement_type == 'balance_sheet':
                        candidates.balance_sheet.extend(page_range)
                    elif entry.statement_type == 'income_statement':
                        candidates.income_statement.extend(page_range)
                    elif entry.statement_type == 'cash_flow':
                        candidates.cash_flow.extend(page_range)

            # Deduplicate and sort
            candidates.balance_sheet = sorted(set(candidates.balance_sheet))
            candidates.income_statement = sorted(set(candidates.income_statement))
            candidates.cash_flow = sorted(set(candidates.cash_flow))

            logger.info(f"  Balance Sheet candidates: pages {candidates.balance_sheet}")
            logger.info(f"  Income Statement candidates: pages {candidates.income_statement}")
            logger.info(f"  Cash Flow candidates: pages {candidates.cash_flow}")

            return candidates

        # Step 3: No TOC found - fall back to keyword scanning all pages
        logger.info("Step 2: No TOC found, falling back to keyword scanning...")
        return self._keyword_scan_all_pages(progress_callback)

    def _keyword_scan_all_pages(
        self,
        progress_callback=None,
        max_candidates: int = 8
    ) -> CandidatePages:
        """
        Scan all pages with keyword scoring (fallback when no TOC).
        Builds a shared page index and routes pages to statement types.
        """
        total_pages = self.pdf_info.total_pages
        candidates = CandidatePages(toc_used=False)

        # Extract all pages (uses OCR if needed)
        logger.info(f"Scanning all {total_pages} pages for keywords...")
        all_pages = self.processor.extract_all_pages_text()

        # Score each page for all statement types at once
        for i, page_data in enumerate(all_pages):
            if progress_callback:
                progress_callback(i + 1, total_pages, 'scanning')

            text = page_data.text

            # Score for balance sheet
            bs_score, bs_matched = self._score_text_for_keywords(
                text, BALANCE_SHEET_TITLES, BALANCE_SHEET_KEYWORDS
            )

            # Score for income statement
            is_score, is_matched = self._score_text_for_keywords(
                text, INCOME_STATEMENT_TITLES, INCOME_STATEMENT_KEYWORDS
            )

            # Score for cash flow
            cf_score, cf_matched = self._score_text_for_keywords(
                text, CASH_FLOW_TITLES, CASH_FLOW_KEYWORDS
            )

            # Store in page index
            self.page_index[page_data.page_num] = PageScore(
                page_num=page_data.page_num,
                text=text,
                text_length=len(text),
                balance_sheet_score=bs_score,
                income_statement_score=is_score,
                cash_flow_score=cf_score,
                is_financial_page=(bs_score > 0 or is_score > 0 or cf_score > 0),
                matched_keywords={
                    'balance_sheet': bs_matched,
                    'income_statement': is_matched,
                    'cash_flow': cf_matched
                }
            )

            # Log high-scoring pages
            if bs_score >= 20 or is_score >= 20 or cf_score >= 20:
                logger.info(f"  Page {page_data.page_num}: BS={bs_score}, IS={is_score}, CF={cf_score}")

        # Select top candidates for each statement type
        all_scores = list(self.page_index.values())

        # Balance sheet candidates
        bs_pages = sorted(all_scores, key=lambda x: x.balance_sheet_score, reverse=True)
        candidates.balance_sheet = [
            p.page_num for p in bs_pages[:max_candidates] if p.balance_sheet_score > 0
        ]

        # Income statement candidates
        is_pages = sorted(all_scores, key=lambda x: x.income_statement_score, reverse=True)
        candidates.income_statement = [
            p.page_num for p in is_pages[:max_candidates] if p.income_statement_score > 0
        ]

        # Cash flow candidates
        cf_pages = sorted(all_scores, key=lambda x: x.cash_flow_score, reverse=True)
        candidates.cash_flow = [
            p.page_num for p in cf_pages[:max_candidates] if p.cash_flow_score > 0
        ]

        logger.info(f"=== Candidate Selection Complete ===")
        logger.info(f"  Balance Sheet: {len(candidates.balance_sheet)} pages {candidates.balance_sheet}")
        logger.info(f"  Income Statement: {len(candidates.income_statement)} pages {candidates.income_statement}")
        logger.info(f"  Cash Flow: {len(candidates.cash_flow)} pages {candidates.cash_flow}")

        return candidates

    def get_page_text(self, page_num: int) -> str:
        """Get cached text for a page (if already scanned)."""
        if page_num in self.page_index:
            return self.page_index[page_num].text
        return ""

    def get_debug_info(self) -> Dict:
        """Get debug information about the page finding process."""
        return {
            'total_pages': self.pdf_info.total_pages if self.pdf_info else 0,
            'is_image_based': self.pdf_info.is_image_based if self.pdf_info else False,
            'toc_entries': [
                {'title': e.title, 'page': e.printed_page, 'type': e.statement_type}
                for e in self.toc_entries
            ],
            'page_offset': self.page_offset,
            'high_scoring_pages': {
                'balance_sheet': [
                    {'page': p.page_num, 'score': p.balance_sheet_score}
                    for p in self.page_index.values()
                    if p.balance_sheet_score >= 10
                ],
                'income_statement': [
                    {'page': p.page_num, 'score': p.income_statement_score}
                    for p in self.page_index.values()
                    if p.income_statement_score >= 10
                ],
                'cash_flow': [
                    {'page': p.page_num, 'score': p.cash_flow_score}
                    for p in self.page_index.values()
                    if p.cash_flow_score >= 10
                ],
            }
        }


def find_financial_statement_pages(
    file_path: str,
    progress_callback=None
) -> Tuple[CandidatePages, Dict]:
    """
    Convenience function to find candidate pages for all statement types.

    Returns: (CandidatePages, debug_info)
    """
    processor = PDFProcessor(file_path)
    finder = PageFinder(processor)
    candidates = finder.find_toc_and_candidates(progress_callback=progress_callback)
    debug_info = finder.get_debug_info()

    return candidates, debug_info
