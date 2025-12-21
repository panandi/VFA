"""
PDF Processing Module with OCR and Rotation Handling

Features:
- Text extraction from text-based PDFs (fast path)
- OCR extraction for image-based PDFs (with caching)
- Automatic rotation detection and correction
- 2-pass approach: low-res for candidate detection, high-res for extraction
- Concurrent processing with ProcessPoolExecutor
"""

import os
import io
import hashlib
import logging
import tempfile
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from functools import lru_cache
import re

import pypdf
from PIL import Image
import fitz  # PyMuPDF - faster than pdf2image

# Lazy import for pytesseract (only when needed)
_tesseract = None

def get_tesseract():
    global _tesseract
    if _tesseract is None:
        import pytesseract
        _tesseract = pytesseract
    return _tesseract

logger = logging.getLogger(__name__)

# Constants
LOW_RES_DPI = 72       # For candidate detection (fast)
HIGH_RES_DPI = 300     # For accurate OCR extraction
MIN_TEXT_LENGTH = 100  # Threshold to determine if page has embedded text
CACHE_DIR = tempfile.gettempdir()


@dataclass
class PageData:
    """Data extracted from a single PDF page."""
    page_num: int  # 0-indexed
    text: str
    orientation: int = 0  # 0, 90, 180, 270 degrees
    is_ocr: bool = False
    word_boxes: List[Dict] = field(default_factory=list)  # For table extraction
    confidence: float = 1.0

    def __hash__(self):
        return hash((self.page_num, self.text[:100] if self.text else ""))


@dataclass
class PDFInfo:
    """Metadata about the PDF."""
    total_pages: int
    is_image_based: bool
    sample_text_lengths: List[int]
    file_hash: str


class PDFProcessor:
    """
    Main PDF processing class with OCR support.

    Usage:
        processor = PDFProcessor(file_path)
        info = processor.get_pdf_info()

        # Low-res pass for candidate detection
        pages = processor.extract_pages_low_res([0, 1, 2, 3])

        # High-res pass for accurate extraction
        pages = processor.extract_pages_high_res([58, 59, 60], detect_tables=True)
    """

    def __init__(self, file_path: str, cache_enabled: bool = True):
        self.file_path = file_path
        self.cache_enabled = cache_enabled
        self._file_hash = None
        self._pdf_info = None
        self._page_cache: Dict[str, PageData] = {}

    @property
    def file_hash(self) -> str:
        """Compute file hash for caching."""
        if self._file_hash is None:
            with open(self.file_path, 'rb') as f:
                self._file_hash = hashlib.md5(f.read(1024 * 1024)).hexdigest()[:16]
        return self._file_hash

    def get_pdf_info(self) -> PDFInfo:
        """
        Analyze PDF to determine if it's text-based or image-based.
        Samples 5 random pages to check for embedded text.
        """
        if self._pdf_info is not None:
            return self._pdf_info

        try:
            with open(self.file_path, 'rb') as f:
                reader = pypdf.PdfReader(f)
                total_pages = len(reader.pages)

                # Sample pages (first, last, and 3 random middle pages)
                sample_indices = [0]
                if total_pages > 1:
                    sample_indices.append(total_pages - 1)
                if total_pages > 4:
                    step = total_pages // 4
                    sample_indices.extend([step, step * 2, step * 3])

                sample_indices = sorted(set(i for i in sample_indices if i < total_pages))[:5]

                text_lengths = []
                for idx in sample_indices:
                    try:
                        text = reader.pages[idx].extract_text() or ""
                        text_lengths.append(len(text.strip()))
                    except Exception:
                        text_lengths.append(0)

                avg_text_len = sum(text_lengths) / len(text_lengths) if text_lengths else 0
                is_image_based = avg_text_len < MIN_TEXT_LENGTH

                logger.info(f"PDF Analysis: {total_pages} pages, avg_text_len={avg_text_len:.0f}, "
                           f"is_image_based={is_image_based}")

                if is_image_based:
                    logger.warning("PDF appears to be image-based (scanned). OCR will be required.")

                self._pdf_info = PDFInfo(
                    total_pages=total_pages,
                    is_image_based=is_image_based,
                    sample_text_lengths=text_lengths,
                    file_hash=self.file_hash
                )
                return self._pdf_info

        except Exception as e:
            logger.error(f"Error analyzing PDF: {e}")
            raise

    def _get_cache_key(self, page_num: int, dpi: int) -> str:
        """Generate cache key for a page."""
        return f"{self.file_hash}_{page_num}_{dpi}"

    def _detect_orientation(self, image: Image.Image) -> int:
        """
        Detect page orientation using Tesseract OSD.
        Returns rotation angle (0, 90, 180, 270).
        """
        try:
            pytesseract = get_tesseract()
            osd = pytesseract.image_to_osd(image, output_type=pytesseract.Output.DICT)
            rotation = osd.get('rotate', 0)
            confidence = osd.get('orientation_conf', 0)

            if confidence > 1.0:  # OSD is reasonably confident
                logger.debug(f"OSD detected rotation: {rotation}° (conf: {confidence})")
                return rotation
            return 0
        except Exception as e:
            logger.debug(f"OSD failed, trying 4-rotation scoring: {e}")
            return self._detect_orientation_by_scoring(image)

    def _detect_orientation_by_scoring(self, image: Image.Image) -> int:
        """
        Fallback orientation detection by scoring OCR results for each rotation.
        """
        pytesseract = get_tesseract()
        best_rotation = 0
        best_score = 0

        # Reduce image size for faster scoring
        small = image.copy()
        small.thumbnail((800, 800))

        for rotation in [0, 90, 180, 270]:
            rotated = small.rotate(-rotation, expand=True) if rotation != 0 else small
            try:
                # Quick OCR to get confidence
                data = pytesseract.image_to_data(
                    rotated,
                    output_type=pytesseract.Output.DICT,
                    config='--psm 6'  # Assume uniform block of text
                )

                # Score based on number of high-confidence words
                confidences = [int(c) for c in data.get('conf', []) if str(c).isdigit() and int(c) > 50]
                score = len(confidences)

                if score > best_score:
                    best_score = score
                    best_rotation = rotation

            except Exception:
                continue

        logger.debug(f"4-rotation scoring: best={best_rotation}° (score: {best_score})")
        return best_rotation

    def _render_page(self, page_num: int, dpi: int = 150) -> Image.Image:
        """
        Render a PDF page to image using PyMuPDF (fitz).
        Much faster than pdf2image.
        """
        doc = fitz.open(self.file_path)
        try:
            page = doc[page_num]

            # Calculate zoom factor for desired DPI
            zoom = dpi / 72.0
            mat = fitz.Matrix(zoom, zoom)

            # Render to pixmap
            pix = page.get_pixmap(matrix=mat)

            # Convert to PIL Image
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            return img

        finally:
            doc.close()

    def _ocr_image(
        self,
        image: Image.Image,
        detect_orientation: bool = True,
        get_word_boxes: bool = False
    ) -> Tuple[str, int, List[Dict], float]:
        """
        Perform OCR on image.

        Returns: (text, rotation, word_boxes, avg_confidence)
        """
        pytesseract = get_tesseract()

        rotation = 0
        if detect_orientation:
            rotation = self._detect_orientation(image)
            if rotation != 0:
                image = image.rotate(-rotation, expand=True)

        word_boxes = []
        avg_confidence = 0.0

        if get_word_boxes:
            # Get detailed OCR data with bounding boxes
            data = pytesseract.image_to_data(
                image,
                output_type=pytesseract.Output.DICT,
                config='--psm 6'  # Assume uniform block of text
            )

            # Build word boxes
            n_boxes = len(data['text'])
            confidences = []
            for i in range(n_boxes):
                text = data['text'][i].strip()
                conf = int(data['conf'][i]) if str(data['conf'][i]).isdigit() else 0

                if text and conf > 0:
                    word_boxes.append({
                        'text': text,
                        'x': data['left'][i],
                        'y': data['top'][i],
                        'width': data['width'][i],
                        'height': data['height'][i],
                        'conf': conf,
                        'block': data['block_num'][i],
                        'line': data['line_num'][i],
                        'word': data['word_num'][i]
                    })
                    if conf > 0:
                        confidences.append(conf)

            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            text = ' '.join(w['text'] for w in word_boxes)
        else:
            # Simple text extraction
            text = pytesseract.image_to_string(image, config='--psm 6')
            avg_confidence = 80.0  # Estimate

        return text, rotation, word_boxes, avg_confidence

    def extract_page_text_only(self, page_num: int) -> PageData:
        """
        Extract text from a page using pypdf (no OCR).
        Fast path for text-based PDFs.
        """
        try:
            with open(self.file_path, 'rb') as f:
                reader = pypdf.PdfReader(f)
                if page_num >= len(reader.pages):
                    return PageData(page_num=page_num, text="", is_ocr=False)

                text = reader.pages[page_num].extract_text() or ""
                return PageData(
                    page_num=page_num,
                    text=text.strip(),
                    is_ocr=False,
                    confidence=1.0
                )
        except Exception as e:
            logger.error(f"Error extracting text from page {page_num}: {e}")
            return PageData(page_num=page_num, text="", is_ocr=False)

    def extract_page_ocr(
        self,
        page_num: int,
        dpi: int = 150,
        detect_orientation: bool = True,
        get_word_boxes: bool = False
    ) -> PageData:
        """
        Extract text from a page using OCR.
        """
        cache_key = self._get_cache_key(page_num, dpi)

        # Check cache
        if self.cache_enabled and cache_key in self._page_cache:
            return self._page_cache[cache_key]

        try:
            # Render page to image
            image = self._render_page(page_num, dpi=dpi)

            # OCR
            text, rotation, word_boxes, confidence = self._ocr_image(
                image,
                detect_orientation=detect_orientation,
                get_word_boxes=get_word_boxes
            )

            page_data = PageData(
                page_num=page_num,
                text=text.strip(),
                orientation=rotation,
                is_ocr=True,
                word_boxes=word_boxes,
                confidence=confidence / 100.0
            )

            # Cache result
            if self.cache_enabled:
                self._page_cache[cache_key] = page_data

            return page_data

        except Exception as e:
            logger.error(f"Error OCR'ing page {page_num}: {e}")
            return PageData(page_num=page_num, text="", is_ocr=True, confidence=0.0)

    def extract_pages_low_res(
        self,
        page_nums: List[int],
        use_ocr: bool = None  # Auto-detect if None
    ) -> List[PageData]:
        """
        Extract pages at low resolution for candidate detection.
        Uses text extraction if PDF is text-based, OCR otherwise.
        """
        if use_ocr is None:
            info = self.get_pdf_info()
            use_ocr = info.is_image_based

        results = []
        for page_num in page_nums:
            if use_ocr:
                page_data = self.extract_page_ocr(
                    page_num,
                    dpi=LOW_RES_DPI,
                    detect_orientation=False,  # Skip for speed in low-res pass
                    get_word_boxes=False
                )
            else:
                page_data = self.extract_page_text_only(page_num)
            results.append(page_data)

        return results

    def extract_pages_high_res(
        self,
        page_nums: List[int],
        use_ocr: bool = None,
        detect_tables: bool = True
    ) -> List[PageData]:
        """
        Extract pages at high resolution for accurate data extraction.
        Includes orientation detection and word bounding boxes for table extraction.
        """
        if use_ocr is None:
            info = self.get_pdf_info()
            use_ocr = info.is_image_based

        results = []
        for page_num in page_nums:
            if use_ocr:
                page_data = self.extract_page_ocr(
                    page_num,
                    dpi=HIGH_RES_DPI,
                    detect_orientation=True,
                    get_word_boxes=detect_tables
                )
            else:
                page_data = self.extract_page_text_only(page_num)
            results.append(page_data)

        return results

    def extract_all_pages_text(self) -> List[PageData]:
        """
        Extract text from all pages (uses appropriate method based on PDF type).
        Used for building page index.
        """
        info = self.get_pdf_info()
        page_nums = list(range(info.total_pages))

        if info.is_image_based:
            logger.info(f"Extracting {info.total_pages} pages via OCR (low-res)...")
            return self.extract_pages_low_res(page_nums, use_ocr=True)
        else:
            logger.info(f"Extracting {info.total_pages} pages via text extraction...")
            return self.extract_pages_low_res(page_nums, use_ocr=False)


def extract_text_from_pdf_smart(file_path: str) -> Tuple[List[PageData], PDFInfo]:
    """
    Convenience function to extract text from a PDF using the appropriate method.

    Returns: (list of PageData, PDFInfo)
    """
    processor = PDFProcessor(file_path)
    info = processor.get_pdf_info()
    pages = processor.extract_all_pages_text()
    return pages, info
