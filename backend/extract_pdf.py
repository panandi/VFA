#!/usr/bin/env python3
"""
Standalone PDF Financial Statement Extraction Script

Usage:
    python extract_pdf.py /path/to/annual_report.pdf [--output output.json] [--verbose]

Example:
    python extract_pdf.py uploads/sample_report.pdf --verbose
"""

import sys
import os
import json
import asyncio
import argparse
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.agents.extraction_agent_v2 import extract_financial_data_v2


def setup_logging(verbose: bool = False):
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def print_summary(result: dict):
    """Print a summary of extraction results."""
    print("\n" + "=" * 60)
    print("EXTRACTION SUMMARY")
    print("=" * 60)

    metadata = result.get("metadata", {})

    print(f"\nPDF Type: {'Image-based (OCR used)' if metadata.get('is_image_based') else 'Text-based'}")
    print(f"TOC Used: {metadata.get('toc_used', False)}")
    print(f"Years Detected: {metadata.get('detected_years', [])}")
    print(f"Scale: {metadata.get('scale', 'Not detected')}")
    print(f"Currency: {metadata.get('currency', 'Not detected')}")
    print(f"Confidence: {metadata.get('confidence', 0):.2%}")

    # Count extracted fields
    for section in ["Balance Sheet", "Profit and Loss", "Cash Flow Statement"]:
        if section in result:
            fields = result[section]
            field_count = len(fields)
            values = sum(
                1 for f in fields.values()
                for k, v in f.items()
                if k.startswith('FY_') and v is not None
            )
            print(f"\n{section}: {field_count} fields, {values} values")

            for field_name, field_data in fields.items():
                for key, value in field_data.items():
                    if key.startswith('FY_') and value is not None:
                        print(f"  {field_name}: {key}={value:,.2f}")
                        break

    # Debug info
    debug = metadata.get("debug", {})
    if debug:
        print(f"\nExtraction time: {debug.get('extraction_time_seconds', 0):.1f}s")
        pages = debug.get("statement_pages", {})
        if pages:
            print(f"Pages used:")
            print(f"  Balance Sheet: {pages.get('balance_sheet', [])}")
            print(f"  Income Statement: {pages.get('profit_and_loss', [])}")
            print(f"  Cash Flow: {pages.get('cash_flow', [])}")


async def main():
    parser = argparse.ArgumentParser(
        description="Extract financial statements from PDF annual reports"
    )
    parser.add_argument(
        "pdf_path",
        help="Path to the PDF file"
    )
    parser.add_argument(
        "--output", "-o",
        help="Output JSON file path (default: print to stdout)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="Only print summary, not full JSON output"
    )

    args = parser.parse_args()

    # Validate input
    if not os.path.exists(args.pdf_path):
        print(f"Error: File not found: {args.pdf_path}")
        sys.exit(1)

    setup_logging(args.verbose)

    print(f"Extracting financial data from: {args.pdf_path}")
    print("This may take a few minutes for scanned PDFs...")

    # Run extraction
    result = await extract_financial_data_v2(args.pdf_path)

    # Handle errors
    if "error" in result:
        print(f"\nError: {result['error']}")
        if not result.get("metadata", {}).get("debug"):
            sys.exit(1)

    # Print summary
    print_summary(result)

    # Output full JSON
    if not args.summary_only:
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(result, f, indent=2, default=str)
            print(f"\nFull results saved to: {args.output}")
        else:
            print("\n" + "=" * 60)
            print("FULL JSON OUTPUT")
            print("=" * 60)
            print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
