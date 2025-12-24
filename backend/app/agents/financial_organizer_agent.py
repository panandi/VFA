"""
Financial Data Organizer Agent (Enhanced v2)
Uses AI to categorize, standardize, and organize extracted financial data
into proper financial statement format with standard terminology.
Optimized for maximum data retention with efficient token usage.
"""

import json
import logging
import re
from typing import Dict, List, Any, Optional
from openai import OpenAI
from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = OpenAI(api_key=settings.OPENAI_API_KEY)


def compress_number(val: Any) -> str:
    """Compress number to shortest representation"""
    if val is None:
        return ""
    try:
        num = float(val)
        if num == 0:
            return "0"
        # Use K/M/B suffixes for large numbers
        if abs(num) >= 1_000_000_000:
            return f"{num/1_000_000_000:.1f}B"
        elif abs(num) >= 1_000_000:
            return f"{num/1_000_000:.1f}M"
        elif abs(num) >= 1_000:
            return f"{num/1_000:.1f}K"
        else:
            return f"{num:.0f}"
    except:
        return str(val)[:10]


def decompress_number(val_str: str) -> float:
    """Convert compressed number back to full value"""
    if not val_str or val_str == "":
        return 0
    try:
        val_str = str(val_str).strip().upper()
        multiplier = 1
        if val_str.endswith('B'):
            multiplier = 1_000_000_000
            val_str = val_str[:-1]
        elif val_str.endswith('M'):
            multiplier = 1_000_000
            val_str = val_str[:-1]
        elif val_str.endswith('K'):
            multiplier = 1_000
            val_str = val_str[:-1]
        return float(val_str) * multiplier
    except:
        return 0


async def organize_financial_data(line_items: List[Dict], fiscal_years: List[int]) -> Dict[str, Any]:
    """
    Use AI to organize and standardize extracted financial data.
    Enhanced version that retains more data with efficient processing.
    """
    logger.info(f"Organizing {len(line_items)} line items for years {fiscal_years}")

    if not line_items:
        return {"success": False, "error": "No line items to organize", "organized_data": None}

    # Sort years descending and keep all of them
    all_years = sorted(fiscal_years, reverse=True)
    # For display, use up to 5 most recent years
    display_years = all_years[:5]
    logger.info(f"Processing years: {display_years}")

    # Smart consolidation - merge duplicates intelligently
    consolidated = {}
    for item in line_items:
        line_text = item.get('line_item', '').strip()
        if not line_text or len(line_text) < 2:
            continue

        # Skip obvious noise
        noise_patterns = ['particulars', 'note no', 'schedule', 'amount in', 'rs.', 'inr',
                         'as at', 'for the year', 'previous year', 'current year']
        if any(p in line_text.lower() for p in noise_patterns):
            continue

        # Normalize key - remove special chars, extra spaces
        key = re.sub(r'[^a-z0-9\s]', '', line_text.lower())
        key = ' '.join(key.split())[:50]

        if not key or len(key) < 2:
            continue

        if key not in consolidated:
            consolidated[key] = {
                'line_item': line_text[:80],
                'values': {},
                'category': item.get('category', 'unknown'),
                'statement_type': item.get('statement_type', 'unknown')
            }

        # Merge values - prioritize non-zero values
        for year, val in item.get('values', {}).items():
            if year in display_years:
                existing = consolidated[key]['values'].get(year)
                if existing is None or existing == 0:
                    consolidated[key]['values'][year] = val
                elif val != 0 and existing != val:
                    # Keep the larger absolute value
                    if abs(float(val or 0)) > abs(float(existing or 0)):
                        consolidated[key]['values'][year] = val

    # Remove items with no values
    consolidated = {k: v for k, v in consolidated.items() if any(v['values'].values())}

    items_list = list(consolidated.values())
    logger.info(f"Consolidated to {len(items_list)} unique items")

    # Group items by statement type for balanced processing
    by_type = {'balance_sheet': [], 'income_statement': [], 'cash_flow': [], 'other': []}
    for item in items_list:
        stmt = item.get('statement_type', 'other')
        if stmt not in by_type:
            stmt = 'other'
        by_type[stmt].append(item)

    logger.info(f"Items by type: BS={len(by_type['balance_sheet'])}, IS={len(by_type['income_statement'])}, CF={len(by_type['cash_flow'])}, Other={len(by_type['other'])}")

    # Build ultra-compact data format
    # Format: "item_name|y1:v1,y2:v2|type"
    lines = []
    year_abbrev = {y: f"Y{i}" for i, y in enumerate(display_years)}

    for item in items_list:
        name = item['line_item'][:60]
        vals = []
        for y in display_years:
            v = item['values'].get(y)
            if v is not None and v != 0:
                vals.append(f"{year_abbrev[y]}:{compress_number(v)}")
        if vals:
            stmt = item['statement_type'][:2].upper()  # BS, IS, CF, OT
            lines.append(f"{name}|{','.join(vals)}|{stmt}")

    data_text = "\n".join(lines)

    # Year mapping for prompt
    year_map = ", ".join([f"{abbr}={year}" for year, abbr in year_abbrev.items()])

    prompt = f"""Organize financial data into standard statements. Year codes: {year_map}

DATA (format: name|values|type):
{data_text}

Return JSON:
{{"balance_sheet":{{"assets":[],"liabilities":[],"equity":[]}},"income_statement":[],"cash_flow":[],"notes":[]}}

Each item: {{"name":"Standard Name","values":{{year:number}},"level":0-2,"is_total":bool,"is_header":bool,"sources":["original"]}}

Map terms: Sundry Debtors→Accounts Receivable, Trade Payables→Accounts Payable, Stock→Inventory,
Fixed Assets→PPE, Reserves→Retained Earnings, Revenue from Ops→Revenue, PAT→Net Income.
Levels: 0=totals, 1=category, 2=detail. Include ALL items. Return valid JSON only."""

    # Estimate tokens
    estimated_tokens = len(prompt) // 3  # More accurate for mixed content
    logger.info(f"Estimated tokens: {estimated_tokens}, data lines: {len(lines)}")

    # Always use gpt-4o for better context and quality
    model = "gpt-4o"
    max_tokens = 8000

    # For very large datasets, increase output tokens
    if len(lines) > 200:
        max_tokens = 12000

    logger.info(f"Using model: {model}")

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a financial data expert. Organize raw financial data into standard statements. Return valid JSON only, no markdown."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=max_tokens
        )

        result_text = response.choices[0].message.content.strip()
        logger.info(f"AI Response length: {len(result_text)}")

        # Clean up response
        if "```json" in result_text:
            result_text = result_text.split("```json")[1]
        if "```" in result_text:
            result_text = result_text.split("```")[0]
        result_text = result_text.strip()

        # Parse JSON
        organized_data = json.loads(result_text)

        # Convert compressed values back to full numbers
        organized_data = decompress_values(organized_data, display_years)

        logger.info("Successfully organized financial data")

        # Count items
        bs = organized_data.get('balance_sheet', {})
        total_bs = len(bs.get('assets', [])) + len(bs.get('liabilities', [])) + len(bs.get('equity', []))
        total_is = len(organized_data.get('income_statement', []))
        total_cf = len(organized_data.get('cash_flow', []))
        logger.info(f"Organized items: BS={total_bs}, IS={total_is}, CF={total_cf}")

        display_items = create_display_items(organized_data, display_years)

        return {
            "success": True,
            "organized_data": organized_data,
            "display_items": display_items,
            "fiscal_years": display_years,
            "total_source_items": len(line_items),
            "processed_items": len(items_list),
            "model_used": model
        }

    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error: {e}")
        logger.error(f"Response: {result_text[:500] if result_text else 'empty'}")

        # Fallback to intelligent grouping
        display_items = create_smart_fallback(items_list, display_years)

        return {
            "success": True,
            "organized_data": None,
            "display_items": display_items,
            "fiscal_years": display_years,
            "total_source_items": len(line_items),
            "notes": ["AI parsing failed, showing categorized extracted data"]
        }

    except Exception as e:
        logger.error(f"AI organization failed: {e}")
        import traceback
        traceback.print_exc()

        display_items = create_smart_fallback(items_list, display_years)

        return {
            "success": True,
            "organized_data": None,
            "display_items": display_items,
            "fiscal_years": display_years,
            "error": str(e),
            "notes": ["AI organization failed, showing categorized extracted data"]
        }


def decompress_values(data: Dict, years: List[int]) -> Dict:
    """Convert any compressed values back to full numbers"""
    def process_item(item):
        if isinstance(item, dict) and 'values' in item:
            new_values = {}
            for k, v in item.get('values', {}).items():
                # Handle year codes like Y0, Y1
                year = k
                if isinstance(k, str) and k.startswith('Y'):
                    try:
                        idx = int(k[1:])
                        if idx < len(years):
                            year = years[idx]
                    except:
                        pass
                # Decompress value
                if isinstance(v, str):
                    new_values[year] = decompress_number(v)
                else:
                    new_values[year] = v
            item['values'] = new_values
        return item

    def process_list(items):
        return [process_item(item) for item in items if isinstance(item, dict)]

    # Process balance sheet
    if 'balance_sheet' in data and isinstance(data['balance_sheet'], dict):
        bs = data['balance_sheet']
        if 'assets' in bs:
            bs['assets'] = process_list(bs['assets'])
        if 'liabilities' in bs:
            bs['liabilities'] = process_list(bs['liabilities'])
        if 'equity' in bs:
            bs['equity'] = process_list(bs['equity'])

    # Process income statement
    if 'income_statement' in data:
        data['income_statement'] = process_list(data['income_statement'])

    # Process cash flow
    if 'cash_flow' in data:
        data['cash_flow'] = process_list(data['cash_flow'])

    return data


def create_display_items(organized_data: Dict, fiscal_years: List[int]) -> List[Dict]:
    """Convert organized data into flat display items for frontend."""
    display_items = []

    def add_item(name: str, data: Dict, section_type: str):
        item = {
            "name": name,
            "level": data.get("level", 0),
            "is_header": data.get("is_header", False),
            "is_total": data.get("is_total", False),
            "section_type": section_type,
            "values": data.get("values", {}),
            "source_items": data.get("sources", [])
        }
        display_items.append(item)

    def process_items(items: List, section_type: str):
        for item in items:
            if isinstance(item, dict) and "name" in item:
                add_item(item["name"], item, section_type)

    # Balance Sheet
    display_items.append({
        "name": "BALANCE SHEET",
        "level": 0, "is_header": True, "is_total": False,
        "section_type": "balance_sheet", "values": {}, "source_items": []
    })

    bs = organized_data.get("balance_sheet", {})
    if isinstance(bs, dict):
        if bs.get("assets"):
            display_items.append({
                "name": "ASSETS", "level": 0, "is_header": True,
                "section_type": "balance_sheet", "values": {}, "source_items": []
            })
            process_items(bs["assets"], "balance_sheet")

        if bs.get("liabilities"):
            display_items.append({
                "name": "LIABILITIES", "level": 0, "is_header": True,
                "section_type": "balance_sheet", "values": {}, "source_items": []
            })
            process_items(bs["liabilities"], "balance_sheet")

        if bs.get("equity"):
            display_items.append({
                "name": "EQUITY", "level": 0, "is_header": True,
                "section_type": "balance_sheet", "values": {}, "source_items": []
            })
            process_items(bs["equity"], "balance_sheet")

    # Income Statement
    display_items.append({
        "name": "INCOME STATEMENT",
        "level": 0, "is_header": True, "is_total": False,
        "section_type": "income_statement", "values": {}, "source_items": []
    })
    inc = organized_data.get("income_statement", [])
    if isinstance(inc, list):
        process_items(inc, "income_statement")

    # Cash Flow
    display_items.append({
        "name": "CASH FLOW STATEMENT",
        "level": 0, "is_header": True, "is_total": False,
        "section_type": "cash_flow", "values": {}, "source_items": []
    })
    cf = organized_data.get("cash_flow", [])
    if isinstance(cf, list):
        process_items(cf, "cash_flow")

    return display_items


def create_smart_fallback(items_list: List[Dict], fiscal_years: List[int]) -> List[Dict]:
    """
    Create intelligently grouped display items when AI fails.
    Groups by statement type and applies basic categorization.
    """
    display_items = []

    # Keywords for smart categorization
    asset_keywords = ['asset', 'cash', 'bank', 'receivable', 'debtor', 'inventory', 'stock',
                     'investment', 'property', 'equipment', 'plant', 'fixed', 'intangible']
    liability_keywords = ['liability', 'payable', 'creditor', 'loan', 'borrowing', 'debt',
                         'provision', 'accrued', 'deferred']
    equity_keywords = ['equity', 'capital', 'reserve', 'surplus', 'retained', 'share']
    revenue_keywords = ['revenue', 'sales', 'income', 'turnover', 'receipt']
    expense_keywords = ['expense', 'cost', 'depreciation', 'amortization', 'interest',
                       'salary', 'wage', 'rent', 'utility']

    # Group by statement type
    by_type = {'balance_sheet': [], 'income_statement': [], 'cash_flow': [], 'other': []}

    for item in items_list:
        stmt = item.get('statement_type', 'other')
        if stmt not in by_type:
            stmt = 'other'
        by_type[stmt].append(item)

    # Process Balance Sheet with sub-categorization
    if by_type['balance_sheet']:
        display_items.append({
            "name": "BALANCE SHEET", "level": 0, "is_header": True,
            "section_type": "balance_sheet", "values": {}, "source_items": []
        })

        assets, liabilities, equity, other_bs = [], [], [], []
        for item in by_type['balance_sheet']:
            name_lower = item.get('line_item', '').lower()
            if any(k in name_lower for k in asset_keywords):
                assets.append(item)
            elif any(k in name_lower for k in liability_keywords):
                liabilities.append(item)
            elif any(k in name_lower for k in equity_keywords):
                equity.append(item)
            else:
                other_bs.append(item)

        if assets:
            display_items.append({
                "name": "ASSETS", "level": 0, "is_header": True,
                "section_type": "balance_sheet", "values": {}, "source_items": []
            })
            for item in assets:
                display_items.append({
                    "name": item.get('line_item', 'Unknown'),
                    "level": 1, "is_header": False, "is_total": False,
                    "section_type": "balance_sheet",
                    "values": {y: item.get('values', {}).get(y) for y in fiscal_years},
                    "source_items": []
                })

        if liabilities:
            display_items.append({
                "name": "LIABILITIES", "level": 0, "is_header": True,
                "section_type": "balance_sheet", "values": {}, "source_items": []
            })
            for item in liabilities:
                display_items.append({
                    "name": item.get('line_item', 'Unknown'),
                    "level": 1, "is_header": False, "is_total": False,
                    "section_type": "balance_sheet",
                    "values": {y: item.get('values', {}).get(y) for y in fiscal_years},
                    "source_items": []
                })

        if equity:
            display_items.append({
                "name": "EQUITY", "level": 0, "is_header": True,
                "section_type": "balance_sheet", "values": {}, "source_items": []
            })
            for item in equity:
                display_items.append({
                    "name": item.get('line_item', 'Unknown'),
                    "level": 1, "is_header": False, "is_total": False,
                    "section_type": "balance_sheet",
                    "values": {y: item.get('values', {}).get(y) for y in fiscal_years},
                    "source_items": []
                })

        if other_bs:
            display_items.append({
                "name": "OTHER BALANCE SHEET ITEMS", "level": 0, "is_header": True,
                "section_type": "balance_sheet", "values": {}, "source_items": []
            })
            for item in other_bs:
                display_items.append({
                    "name": item.get('line_item', 'Unknown'),
                    "level": 1, "is_header": False, "is_total": False,
                    "section_type": "balance_sheet",
                    "values": {y: item.get('values', {}).get(y) for y in fiscal_years},
                    "source_items": []
                })

    # Process Income Statement
    if by_type['income_statement']:
        display_items.append({
            "name": "INCOME STATEMENT", "level": 0, "is_header": True,
            "section_type": "income_statement", "values": {}, "source_items": []
        })

        revenues, expenses, other_is = [], [], []
        for item in by_type['income_statement']:
            name_lower = item.get('line_item', '').lower()
            if any(k in name_lower for k in revenue_keywords):
                revenues.append(item)
            elif any(k in name_lower for k in expense_keywords):
                expenses.append(item)
            else:
                other_is.append(item)

        for item in revenues + other_is + expenses:
            display_items.append({
                "name": item.get('line_item', 'Unknown'),
                "level": 1, "is_header": False, "is_total": False,
                "section_type": "income_statement",
                "values": {y: item.get('values', {}).get(y) for y in fiscal_years},
                "source_items": []
            })

    # Process Cash Flow
    if by_type['cash_flow']:
        display_items.append({
            "name": "CASH FLOW STATEMENT", "level": 0, "is_header": True,
            "section_type": "cash_flow", "values": {}, "source_items": []
        })
        for item in by_type['cash_flow']:
            display_items.append({
                "name": item.get('line_item', 'Unknown'),
                "level": 1, "is_header": False, "is_total": False,
                "section_type": "cash_flow",
                "values": {y: item.get('values', {}).get(y) for y in fiscal_years},
                "source_items": []
            })

    # Process Other
    if by_type['other']:
        display_items.append({
            "name": "OTHER FINANCIAL DATA", "level": 0, "is_header": True,
            "section_type": "other", "values": {}, "source_items": []
        })
        for item in by_type['other']:
            display_items.append({
                "name": item.get('line_item', 'Unknown'),
                "level": 1, "is_header": False, "is_total": False,
                "section_type": "other",
                "values": {y: item.get('values', {}).get(y) for y in fiscal_years},
                "source_items": []
            })

    return display_items


# Backward compatibility
def create_display_structure(organized_data: Dict) -> List[Dict]:
    return create_display_items(organized_data, [])


def create_fallback_display(line_items: List[Dict], fiscal_years: List[int]) -> List[Dict]:
    """Legacy fallback function"""
    return create_smart_fallback(line_items, fiscal_years)
