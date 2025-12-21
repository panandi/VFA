"""
Excel Report Generator for Vendor Financial Assessment.

Generates comprehensive Excel reports with multiple sheets matching the VFA Part 2 (Finance) template.
"""

from io import BytesIO
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side, NamedStyle
from openpyxl.utils import get_column_letter
from openpyxl.chart import BarChart, Reference, PieChart
from openpyxl.chart.label import DataLabelList


# ==================== STYLE DEFINITIONS ====================

# Colors
DARK_BLUE = "1F3864"
LIGHT_BLUE = "4472C4"
YELLOW = "FFD966"
LIGHT_YELLOW = "FFF2CC"
GREEN = "C6EFCE"
DARK_GREEN = "006400"
RED = "FFC7CE"
DARK_RED = "8B0000"
ORANGE = "FFCC99"
GRAY = "F2F2F2"
DARK_GRAY = "404040"
WHITE = "FFFFFF"

# Fills
HEADER_FILL = PatternFill(start_color=DARK_BLUE, end_color=DARK_BLUE, fill_type="solid")
SUBHEADER_FILL = PatternFill(start_color=LIGHT_BLUE, end_color=LIGHT_BLUE, fill_type="solid")
YELLOW_FILL = PatternFill(start_color=YELLOW, end_color=YELLOW, fill_type="solid")
LIGHT_YELLOW_FILL = PatternFill(start_color=LIGHT_YELLOW, end_color=LIGHT_YELLOW, fill_type="solid")
GREEN_FILL = PatternFill(start_color=GREEN, end_color=GREEN, fill_type="solid")
RED_FILL = PatternFill(start_color=RED, end_color=RED, fill_type="solid")
ORANGE_FILL = PatternFill(start_color=ORANGE, end_color=ORANGE, fill_type="solid")
GRAY_FILL = PatternFill(start_color=GRAY, end_color=GRAY, fill_type="solid")

# Fonts
TITLE_FONT = Font(bold=True, size=16, color=WHITE)
HEADER_FONT = Font(bold=True, size=12, color=WHITE)
SUBHEADER_FONT = Font(bold=True, size=11, color=DARK_GRAY)
BOLD_FONT = Font(bold=True, size=10)
NORMAL_FONT = Font(size=10)
SMALL_FONT = Font(size=9)
WHITE_FONT = Font(bold=True, color=WHITE)
LINK_FONT = Font(color="0563C1", underline="single")

# Borders
THIN_BORDER = Border(
    left=Side(style='thin'),
    right=Side(style='thin'),
    top=Side(style='thin'),
    bottom=Side(style='thin')
)

MEDIUM_BORDER = Border(
    left=Side(style='medium'),
    right=Side(style='medium'),
    top=Side(style='medium'),
    bottom=Side(style='medium')
)

# Alignments
CENTER_ALIGN = Alignment(horizontal='center', vertical='center')
LEFT_ALIGN = Alignment(horizontal='left', vertical='center')
RIGHT_ALIGN = Alignment(horizontal='right', vertical='center')
WRAP_ALIGN = Alignment(horizontal='left', vertical='top', wrap_text=True)


def generate_assessment_excel(assessment) -> BytesIO:
    """
    Generate a comprehensive Excel report with multiple sheets.
    """
    wb = Workbook()

    # Remove default sheet
    wb.remove(wb.active)

    # Get data
    extracted_data = sorted(assessment.extracted_data, key=lambda x: x.fiscal_year, reverse=True)
    risk = assessment.risk_assessment
    recommendation = assessment.recommendation
    qualitative = assessment.qualitative_responses
    fiscal_years = [d.fiscal_year for d in extracted_data] if extracted_data else []

    # Create all sheets
    create_summary_sheet(wb, assessment, risk, recommendation, fiscal_years)
    create_financial_data_sheet(wb, assessment, extracted_data, fiscal_years)
    create_ratios_sheet(wb, assessment, risk, fiscal_years)
    create_zscore_sheet(wb, assessment, risk)
    create_qualitative_sheet(wb, assessment, qualitative)
    create_conclusion_sheet(wb, assessment, recommendation, risk)
    create_approval_sheet(wb, assessment, recommendation)

    # Save to buffer
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    return buffer


# ==================== SHEET 1: SUMMARY ====================

def create_summary_sheet(wb: Workbook, assessment, risk, recommendation, fiscal_years):
    """Create the Summary/Overview sheet."""
    ws = wb.create_sheet("Summary", 0)

    # Set column widths
    ws.column_dimensions['A'].width = 5
    ws.column_dimensions['B'].width = 25
    ws.column_dimensions['C'].width = 30
    ws.column_dimensions['D'].width = 20
    ws.column_dimensions['E'].width = 20
    ws.column_dimensions['F'].width = 15

    row = 2

    # Title Header
    ws.merge_cells(f'B{row}:F{row}')
    ws[f'B{row}'] = "VENDOR FINANCIAL ASSESSMENT (VFA)"
    ws[f'B{row}'].font = TITLE_FONT
    ws[f'B{row}'].fill = HEADER_FILL
    ws[f'B{row}'].alignment = CENTER_ALIGN
    row += 1

    ws.merge_cells(f'B{row}:F{row}')
    ws[f'B{row}'] = "Part 2 - Finance Assessment Report"
    ws[f'B{row}'].font = HEADER_FONT
    ws[f'B{row}'].fill = SUBHEADER_FILL
    ws[f'B{row}'].alignment = CENTER_ALIGN
    row += 2

    # Report Information Box
    ws.merge_cells(f'B{row}:C{row}')
    ws[f'B{row}'] = "Report Information"
    ws[f'B{row}'].font = SUBHEADER_FONT
    ws[f'B{row}'].fill = GRAY_FILL
    apply_border_range(ws, f'B{row}:C{row}')
    row += 1

    info_items = [
        ("Report Date", datetime.now().strftime("%d %B %Y")),
        ("Report ID", f"VFA-{datetime.now().year}-{assessment.id:04d}"),
        ("Prepared By", "Finance Team"),
        ("Status", assessment.status.replace("_", " ").title() if assessment.status else "Draft"),
    ]

    for label, value in info_items:
        ws[f'B{row}'] = label
        ws[f'B{row}'].font = BOLD_FONT
        ws[f'C{row}'] = value
        ws[f'C{row}'].font = NORMAL_FONT
        apply_border_range(ws, f'B{row}:C{row}')
        row += 1

    row += 1

    # Vendor Information Box
    ws.merge_cells(f'B{row}:C{row}')
    ws[f'B{row}'] = "Vendor Information"
    ws[f'B{row}'].font = SUBHEADER_FONT
    ws[f'B{row}'].fill = GRAY_FILL
    apply_border_range(ws, f'B{row}:C{row}')
    row += 1

    vendor_items = [
        ("Vendor Name", assessment.vendor_name or "N/A"),
        ("Registration Number", assessment.vendor_registration_number or "N/A"),
        ("Assessment Date", assessment.assessment_date.strftime("%d %B %Y") if assessment.assessment_date else "N/A"),
        ("Fiscal Years Analyzed", ", ".join(str(y) for y in fiscal_years) if fiscal_years else "N/A"),
    ]

    for label, value in vendor_items:
        ws[f'B{row}'] = label
        ws[f'B{row}'].font = BOLD_FONT
        ws[f'C{row}'] = value
        ws[f'C{row}'].font = NORMAL_FONT
        apply_border_range(ws, f'B{row}:C{row}')
        row += 1

    row += 1

    # Risk Assessment Summary Box
    ws.merge_cells(f'B{row}:F{row}')
    ws[f'B{row}'] = "Risk Assessment Summary"
    ws[f'B{row}'].font = HEADER_FONT
    ws[f'B{row}'].fill = HEADER_FILL
    ws[f'B{row}'].alignment = CENTER_ALIGN
    row += 1

    # Z-Score Display
    z_score = risk.z_score if risk else None
    risk_level = risk.risk_level if risk else None

    ws.merge_cells(f'B{row}:C{row+2}')
    ws[f'B{row}'] = f"Z-Score: {z_score:.2f}" if z_score else "Z-Score: N/A"
    ws[f'B{row}'].font = Font(bold=True, size=24)
    ws[f'B{row}'].alignment = CENTER_ALIGN

    # Risk Level with color
    ws.merge_cells(f'D{row}:F{row+2}')
    risk_text = get_risk_label(risk_level)
    ws[f'D{row}'] = risk_text
    ws[f'D{row}'].font = Font(bold=True, size=18)
    ws[f'D{row}'].alignment = CENTER_ALIGN

    if risk_level == 'low':
        ws[f'D{row}'].fill = GREEN_FILL
    elif risk_level == 'medium':
        ws[f'D{row}'].fill = YELLOW_FILL
    else:
        ws[f'D{row}'].fill = RED_FILL

    row += 4

    # Key Metrics Table
    ws.merge_cells(f'B{row}:F{row}')
    ws[f'B{row}'] = "Key Financial Metrics"
    ws[f'B{row}'].font = SUBHEADER_FONT
    ws[f'B{row}'].fill = GRAY_FILL
    apply_border_range(ws, f'B{row}:F{row}')
    row += 1

    # Headers
    headers = ["Metric", "Value", "Status", "Benchmark", "Assessment"]
    for col, header in enumerate(headers, start=2):
        ws.cell(row=row, column=col, value=header)
        ws.cell(row=row, column=col).font = BOLD_FONT
        ws.cell(row=row, column=col).fill = LIGHT_YELLOW_FILL
        ws.cell(row=row, column=col).alignment = CENTER_ALIGN
        ws.cell(row=row, column=col).border = THIN_BORDER
    row += 1

    # Key metrics data
    metrics = [
        ("Current Ratio", risk.current_ratio if risk else None, ">1.0", "current_ratio"),
        ("Quick Ratio", risk.quick_ratio if risk else None, ">0.75", "quick_ratio"),
        ("Debt to Equity", risk.debt_to_equity if risk else None, "<1.5", "debt_to_equity"),
        ("Debt to Assets", risk.debt_to_assets if risk else None, "<0.6", "debt_to_assets"),
        ("ROA", risk.roa if risk else None, ">5%", "roa"),
        ("ROE", risk.roe if risk else None, ">10%", "roe"),
        ("Net Margin", risk.net_margin if risk else None, ">5%", "net_margin"),
    ]

    for metric_name, value, benchmark, ratio_type in metrics:
        ws.cell(row=row, column=2, value=metric_name).border = THIN_BORDER
        ws.cell(row=row, column=2).font = NORMAL_FONT

        # Value
        if value is not None:
            display_val = f"{value:.2f}" if ratio_type not in ['roa', 'roe', 'net_margin'] else f"{value:.1f}%"
        else:
            display_val = "-"
        ws.cell(row=row, column=3, value=display_val).border = THIN_BORDER
        ws.cell(row=row, column=3).alignment = CENTER_ALIGN

        # Status indicator
        indicator, fill = get_risk_indicator(value, ratio_type)
        ws.cell(row=row, column=4, value=indicator).border = THIN_BORDER
        ws.cell(row=row, column=4).alignment = CENTER_ALIGN
        if fill:
            ws.cell(row=row, column=4).fill = fill

        # Benchmark
        ws.cell(row=row, column=5, value=benchmark).border = THIN_BORDER
        ws.cell(row=row, column=5).alignment = CENTER_ALIGN

        # Assessment
        assessment_text = get_assessment_text(value, ratio_type)
        ws.cell(row=row, column=6, value=assessment_text).border = THIN_BORDER
        ws.cell(row=row, column=6).alignment = CENTER_ALIGN

        row += 1

    row += 2

    # Final Recommendation Box
    ws.merge_cells(f'B{row}:F{row}')
    ws[f'B{row}'] = "Final Recommendation"
    ws[f'B{row}'].font = HEADER_FONT
    ws[f'B{row}'].fill = HEADER_FILL
    ws[f'B{row}'].alignment = CENTER_ALIGN
    row += 1

    rec_type = recommendation.recommendation_type if recommendation else None
    rec_text = get_recommendation_display(rec_type)

    ws.merge_cells(f'B{row}:F{row+1}')
    ws[f'B{row}'] = rec_text
    ws[f'B{row}'].font = Font(bold=True, size=14)
    ws[f'B{row}'].alignment = CENTER_ALIGN

    if rec_type == 'proceed':
        ws[f'B{row}'].fill = GREEN_FILL
    elif rec_type == 'proceed_with_mitigation':
        ws[f'B{row}'].fill = YELLOW_FILL
    elif rec_type == 'do_not_proceed':
        ws[f'B{row}'].fill = RED_FILL
    else:
        ws[f'B{row}'].fill = GRAY_FILL

    row += 3

    # Navigation Links
    ws[f'B{row}'] = "Quick Navigation:"
    ws[f'B{row}'].font = BOLD_FONT
    row += 1

    sheets = ["Financial Data", "Ratios Analysis", "Z-Score Analysis", "Qualitative", "Conclusion"]
    for sheet in sheets:
        ws[f'B{row}'] = f"  - {sheet}"
        ws[f'B{row}'].font = LINK_FONT
        ws[f'B{row}'].hyperlink = f"#'{sheet}'!A1"
        row += 1


# ==================== SHEET 2: FINANCIAL DATA ====================

def create_financial_data_sheet(wb: Workbook, assessment, extracted_data, fiscal_years):
    """Create the Financial Data sheet with Balance Sheet, P&L, and Cash Flow."""
    ws = wb.create_sheet("Financial Data", 1)

    # Set column widths
    ws.column_dimensions['A'].width = 5
    ws.column_dimensions['B'].width = 45
    for i, _ in enumerate(fiscal_years):
        col_letter = get_column_letter(3 + i)
        ws.column_dimensions[col_letter].width = 18
    ws.column_dimensions[get_column_letter(3 + len(fiscal_years))].width = 18  # YoY Change

    row = 2

    # Title
    end_col = get_column_letter(3 + len(fiscal_years))
    ws.merge_cells(f'B{row}:{end_col}{row}')
    ws[f'B{row}'] = "Section A: Financial Information"
    ws[f'B{row}'].font = TITLE_FONT
    ws[f'B{row}'].fill = HEADER_FILL
    ws[f'B{row}'].alignment = CENTER_ALIGN
    row += 2

    # Vendor Info
    ws[f'B{row}'] = "Name of Vendor/Tenderer:"
    ws[f'B{row}'].font = BOLD_FONT
    ws[f'C{row}'] = assessment.vendor_name
    ws[f'C{row}'].fill = LIGHT_YELLOW_FILL
    row += 1

    ws[f'B{row}'] = "Reporting Currency:"
    ws[f'B{row}'].font = BOLD_FONT
    ws[f'C{row}'] = "SGD (in '000)"
    ws[f'C{row}'].fill = LIGHT_YELLOW_FILL
    row += 2

    # ========== BALANCE SHEET ==========
    row = create_financial_section(
        ws, row, "BALANCE SHEET", fiscal_years, extracted_data,
        [
            ("Assets", None, True),
            ("Current Assets", "current_assets", False),
            ("  - Cash and Cash Equivalents", "cash_and_equivalents", False),
            ("  - Accounts Receivable", "accounts_receivable", False),
            ("  - Inventory", "inventory", False),
            ("Non-Current Assets", None, False),
            ("Total Assets", "total_assets", True),
            ("", None, False),
            ("Liabilities", None, True),
            ("Current Liabilities", "current_liabilities", False),
            ("  - Accounts Payable", "accounts_payable", False),
            ("Non-Current Liabilities", None, False),
            ("Total Liabilities", "total_liabilities", True),
            ("", None, False),
            ("Equity", None, True),
            ("Retained Earnings", "retained_earnings", False),
            ("Total Equity", "total_equity", True),
            ("", None, False),
            ("Working Capital", "working_capital", True),
        ]
    )

    row += 1

    # ========== PROFIT & LOSS ==========
    row = create_financial_section(
        ws, row, "PROFIT & LOSS STATEMENT", fiscal_years, extracted_data,
        [
            ("Revenue/Sales", "revenue", True),
            ("Cost of Sales/COGS", "cost_of_sales", False),
            ("Gross Profit", "gross_profit", True),
            ("", None, False),
            ("Operating Expenses", "operating_expenses", False),
            ("Operating Income (EBIT)", "ebit", True),
            ("", None, False),
            ("Interest Expense", "interest_expense", False),
            ("Earnings Before Tax (EBT)", "ebt", False),
            ("Tax Expense", "tax_expense", False),
            ("Net Income/(Loss)", "net_income", True),
        ]
    )

    row += 1

    # ========== CASH FLOW ==========
    row = create_financial_section(
        ws, row, "CASH FLOW STATEMENT", fiscal_years, extracted_data,
        [
            ("Operating Activities", None, True),
            ("Net Cash from Operating Activities", "operating_cash_flow", False),
            ("", None, False),
            ("Investing Activities", None, True),
            ("Net Cash from Investing Activities", "investing_cash_flow", False),
            ("", None, False),
            ("Financing Activities", None, True),
            ("Net Cash from Financing Activities", "financing_cash_flow", False),
            ("", None, False),
            ("Net Change in Cash", None, True),
            ("Cash at End of Period", "cash_and_equivalents", True),
        ]
    )


def create_financial_section(ws, start_row, title, fiscal_years, extracted_data, items):
    """Helper to create a financial data section."""
    row = start_row
    end_col = get_column_letter(3 + len(fiscal_years))

    # Section Header
    ws.merge_cells(f'B{row}:{end_col}{row}')
    ws[f'B{row}'] = title
    ws[f'B{row}'].font = HEADER_FONT
    ws[f'B{row}'].fill = SUBHEADER_FILL
    ws[f'B{row}'].alignment = LEFT_ALIGN
    row += 1

    # Year Headers
    ws[f'B{row}'] = "Line Item"
    ws[f'B{row}'].font = BOLD_FONT
    ws[f'B{row}'].fill = YELLOW_FILL
    ws[f'B{row}'].border = THIN_BORDER

    for i, fy in enumerate(fiscal_years):
        col = get_column_letter(3 + i)
        ws[f'{col}{row}'] = f"FY {fy}"
        ws[f'{col}{row}'].font = BOLD_FONT
        ws[f'{col}{row}'].fill = YELLOW_FILL
        ws[f'{col}{row}'].alignment = CENTER_ALIGN
        ws[f'{col}{row}'].border = THIN_BORDER

    # YoY Change column
    if len(fiscal_years) >= 2:
        col = get_column_letter(3 + len(fiscal_years))
        ws[f'{col}{row}'] = "YoY Change"
        ws[f'{col}{row}'].font = BOLD_FONT
        ws[f'{col}{row}'].fill = ORANGE_FILL
        ws[f'{col}{row}'].alignment = CENTER_ALIGN
        ws[f'{col}{row}'].border = THIN_BORDER

    row += 1

    # Data rows
    for label, field, is_bold in items:
        ws[f'B{row}'] = label
        ws[f'B{row}'].font = BOLD_FONT if is_bold else NORMAL_FONT
        ws[f'B{row}'].border = THIN_BORDER

        values = []
        for i, data in enumerate(extracted_data):
            col = get_column_letter(3 + i)
            value = getattr(data, field, None) if field else None
            values.append(value)

            if value is not None:
                ws[f'{col}{row}'] = value
                ws[f'{col}{row}'].number_format = '#,##0'
            else:
                ws[f'{col}{row}'] = "-" if field else ""

            ws[f'{col}{row}'].alignment = RIGHT_ALIGN
            ws[f'{col}{row}'].border = THIN_BORDER
            if is_bold:
                ws[f'{col}{row}'].font = BOLD_FONT

        # YoY Change calculation
        if len(values) >= 2 and values[0] is not None and values[1] is not None and values[1] != 0:
            yoy_change = ((values[0] - values[1]) / abs(values[1])) * 100
            col = get_column_letter(3 + len(fiscal_years))
            ws[f'{col}{row}'] = f"{yoy_change:+.1f}%"
            ws[f'{col}{row}'].alignment = CENTER_ALIGN
            ws[f'{col}{row}'].border = THIN_BORDER
            if yoy_change > 0:
                ws[f'{col}{row}'].fill = GREEN_FILL
            elif yoy_change < 0:
                ws[f'{col}{row}'].fill = RED_FILL

        row += 1

    return row


# ==================== SHEET 3: RATIOS ANALYSIS ====================

def create_ratios_sheet(wb: Workbook, assessment, risk, fiscal_years):
    """Create the Financial Ratios Analysis sheet."""
    ws = wb.create_sheet("Ratios Analysis", 2)

    # Set column widths
    ws.column_dimensions['A'].width = 5
    ws.column_dimensions['B'].width = 40
    ws.column_dimensions['C'].width = 15
    ws.column_dimensions['D'].width = 12
    ws.column_dimensions['E'].width = 15
    ws.column_dimensions['F'].width = 25
    ws.column_dimensions['G'].width = 20

    row = 2

    # Title
    ws.merge_cells(f'B{row}:G{row}')
    ws[f'B{row}'] = "Section B: Financial Assessment - Ratio Analysis"
    ws[f'B{row}'].font = TITLE_FONT
    ws[f'B{row}'].fill = HEADER_FILL
    ws[f'B{row}'].alignment = CENTER_ALIGN
    row += 2

    # Legend
    ws[f'B{row}'] = "Legend:"
    ws[f'B{row}'].font = BOLD_FONT
    row += 1

    legend_items = [
        ("Good", "↑", GREEN_FILL),
        ("Above Average", "↗", LIGHT_YELLOW_FILL),
        ("Below Average", "↘", ORANGE_FILL),
        ("Inadequate", "↓", RED_FILL),
    ]

    col = 2
    for label, arrow, fill in legend_items:
        ws.cell(row=row, column=col, value=f"{arrow} {label}")
        ws.cell(row=row, column=col).fill = fill
        ws.cell(row=row, column=col).border = THIN_BORDER
        ws.cell(row=row, column=col).alignment = CENTER_ALIGN
        col += 1

    row += 2

    # ========== LIQUIDITY RATIOS ==========
    row = create_ratio_section(ws, row, "LIQUIDITY RATIOS", "Measures ability to meet short-term obligations", [
        ("Current Ratio", risk.current_ratio if risk else None, "current_ratio",
         "Current Assets / Current Liabilities", "> 1.0 is healthy"),
        ("Quick Ratio (Acid Test)", risk.quick_ratio if risk else None, "quick_ratio",
         "(Current Assets - Inventory) / Current Liabilities", "> 0.75 is acceptable"),
        ("Cash Ratio", risk.cash_ratio if risk else None, "cash_ratio",
         "Cash / Current Liabilities", "> 0.2 is healthy"),
        ("Working Capital Ratio", risk.working_capital_ratio if risk else None, "working_capital_ratio",
         "Working Capital / Total Assets", "> 0.1 is positive"),
    ])

    row += 1

    # ========== PROFITABILITY RATIOS ==========
    row = create_ratio_section(ws, row, "PROFITABILITY RATIOS", "Measures ability to generate profits", [
        ("Gross Margin", risk.gross_margin if risk else None, None,
         "(Revenue - COGS) / Revenue", "> 20% varies by industry", True),
        ("Net Profit Margin", risk.net_margin if risk else None, None,
         "Net Income / Revenue", "> 5% is healthy", True),
        ("Return on Assets (ROA)", risk.roa if risk else None, "roa",
         "Net Income / Total Assets", "> 5% is good", True),
        ("Return on Equity (ROE)", risk.roe if risk else None, "roe",
         "Net Income / Shareholders' Equity", "> 10% is good", True),
    ])

    row += 1

    # ========== LEVERAGE RATIOS ==========
    row = create_ratio_section(ws, row, "LEVERAGE/SOLVENCY RATIOS", "Measures long-term financial stability", [
        ("Debt to Equity Ratio", risk.debt_to_equity if risk else None, "debt_to_equity",
         "Total Liabilities / Shareholders' Equity", "< 1.5 is acceptable"),
        ("Debt to Assets Ratio", risk.debt_to_assets if risk else None, "debt_to_assets",
         "Total Liabilities / Total Assets", "< 0.6 is healthy"),
        ("Interest Coverage Ratio", risk.interest_coverage if risk else None, None,
         "EBIT / Interest Expense", "> 3.0 is safe"),
        ("Retained Earnings to Assets", risk.retained_earnings_to_assets if risk else None, None,
         "Retained Earnings / Total Assets", "Higher is better"),
    ])

    row += 1

    # ========== EFFICIENCY RATIOS ==========
    row = create_ratio_section(ws, row, "EFFICIENCY RATIOS", "Measures operational effectiveness", [
        ("Asset Turnover", risk.asset_turnover if risk else None, None,
         "Revenue / Total Assets", "Higher indicates efficiency"),
        ("Inventory Turnover", risk.inventory_turnover if risk else None, None,
         "COGS / Average Inventory", "Higher is generally better"),
        ("Receivables Turnover", risk.receivables_turnover if risk else None, None,
         "Revenue / Accounts Receivable", "Higher means faster collection"),
        ("Creditors to Sales", risk.creditors_to_sales if risk else None, None,
         "Accounts Payable / Revenue", "Lower is better"),
    ])

    row += 1

    # ========== GROWTH RATIOS ==========
    if risk:
        row = create_ratio_section(ws, row, "GROWTH INDICATORS", "Year-over-Year Changes", [
            ("Revenue Growth", risk.growth_sales if risk else None, None,
             "Change in Revenue", "Positive growth preferred", True),
            ("Net Profit Growth", risk.growth_net_profit if risk else None, None,
             "Change in Net Income", "Positive growth preferred", True),
            ("Gross Margin Change", risk.growth_gross_profit_margin if risk else None, None,
             "Change in Gross Margin", "Stable or improving", True),
            ("Net Margin Change", risk.growth_net_profit_margin if risk else None, None,
             "Change in Net Margin", "Stable or improving", True),
        ])


def create_ratio_section(ws, start_row, title, description, ratios):
    """Helper to create a ratio analysis section."""
    row = start_row

    # Section Header
    ws.merge_cells(f'B{row}:G{row}')
    ws[f'B{row}'] = title
    ws[f'B{row}'].font = HEADER_FONT
    ws[f'B{row}'].fill = SUBHEADER_FILL
    ws[f'B{row}'].alignment = LEFT_ALIGN
    row += 1

    ws.merge_cells(f'B{row}:G{row}')
    ws[f'B{row}'] = description
    ws[f'B{row}'].font = Font(italic=True, size=9)
    row += 1

    # Column Headers
    headers = ["Ratio Name", "Value", "Status", "Formula", "Benchmark"]
    for col, header in enumerate(headers, start=2):
        ws.cell(row=row, column=col, value=header)
        ws.cell(row=row, column=col).font = BOLD_FONT
        ws.cell(row=row, column=col).fill = YELLOW_FILL
        ws.cell(row=row, column=col).alignment = CENTER_ALIGN
        ws.cell(row=row, column=col).border = THIN_BORDER
    row += 1

    # Data rows
    for item in ratios:
        name, value, ratio_type = item[0], item[1], item[2]
        formula, benchmark = item[3], item[4]
        is_percent = item[5] if len(item) > 5 else False

        ws.cell(row=row, column=2, value=name)
        ws.cell(row=row, column=2).font = NORMAL_FONT
        ws.cell(row=row, column=2).border = THIN_BORDER

        # Value
        if value is not None:
            display_val = f"{value:.1f}%" if is_percent else f"{value:.2f}"
        else:
            display_val = "-"
        ws.cell(row=row, column=3, value=display_val)
        ws.cell(row=row, column=3).alignment = CENTER_ALIGN
        ws.cell(row=row, column=3).border = THIN_BORDER

        # Status with indicator
        indicator, fill = get_risk_indicator(value, ratio_type)
        ws.cell(row=row, column=4, value=indicator)
        ws.cell(row=row, column=4).alignment = CENTER_ALIGN
        ws.cell(row=row, column=4).border = THIN_BORDER
        ws.cell(row=row, column=4).font = Font(size=14)
        if fill:
            ws.cell(row=row, column=4).fill = fill

        # Formula
        ws.cell(row=row, column=5, value=formula)
        ws.cell(row=row, column=5).font = SMALL_FONT
        ws.cell(row=row, column=5).border = THIN_BORDER

        # Benchmark
        ws.cell(row=row, column=6, value=benchmark)
        ws.cell(row=row, column=6).font = SMALL_FONT
        ws.cell(row=row, column=6).border = THIN_BORDER

        row += 1

    return row


# ==================== SHEET 4: Z-SCORE ANALYSIS ====================

def create_zscore_sheet(wb: Workbook, assessment, risk):
    """Create the Z-Score Analysis sheet."""
    ws = wb.create_sheet("Z-Score Analysis", 3)

    # Set column widths
    ws.column_dimensions['A'].width = 5
    ws.column_dimensions['B'].width = 50
    ws.column_dimensions['C'].width = 12
    ws.column_dimensions['D'].width = 15
    ws.column_dimensions['E'].width = 15
    ws.column_dimensions['F'].width = 18
    ws.column_dimensions['G'].width = 20

    row = 2

    # Title
    ws.merge_cells(f'B{row}:G{row}')
    ws[f'B{row}'] = "Risk of Financial Distress - Altman Z-Score Analysis"
    ws[f'B{row}'].font = TITLE_FONT
    ws[f'B{row}'].fill = HEADER_FILL
    ws[f'B{row}'].alignment = CENTER_ALIGN
    row += 2

    # Company Type
    company_type = risk.company_type if risk else 'private'
    ws[f'B{row}'] = "Type of Company:"
    ws[f'B{row}'].font = BOLD_FONT
    ws[f'C{row}'] = "Private Company" if company_type == 'private' else "Public Company"
    ws[f'C{row}'].fill = LIGHT_YELLOW_FILL
    row += 1

    ws[f'B{row}'] = "Fiscal Year Analyzed:"
    ws[f'B{row}'].font = BOLD_FONT
    ws[f'C{row}'] = str(risk.fiscal_year_used) if risk and risk.fiscal_year_used else "N/A"
    ws[f'C{row}'].fill = LIGHT_YELLOW_FILL
    row += 2

    # Z-Score Formula
    ws.merge_cells(f'B{row}:G{row}')
    ws[f'B{row}'] = "Z-Score Formula"
    ws[f'B{row}'].font = SUBHEADER_FONT
    ws[f'B{row}'].fill = GRAY_FILL
    row += 1

    if company_type == 'private':
        formula = "Z-Score = 0.717×X1 + 0.847×X2 + 3.107×X3 + 0.420×X4 + 0.998×X5"
    else:
        formula = "Z-Score = 1.200×X1 + 1.400×X2 + 3.300×X3 + 0.600×X4 + 1.000×X5"

    ws.merge_cells(f'B{row}:G{row}')
    ws[f'B{row}'] = formula
    ws[f'B{row}'].font = Font(bold=True, size=11)
    ws[f'B{row}'].alignment = CENTER_ALIGN
    row += 2

    # Z-Score Components Table
    ws.merge_cells(f'B{row}:G{row}')
    ws[f'B{row}'] = "Z-Score Components"
    ws[f'B{row}'].font = HEADER_FONT
    ws[f'B{row}'].fill = SUBHEADER_FILL
    row += 1

    # Headers
    headers = ["Component", "Variable", "Ratio Value (A)", "Weightage (B)", "Weighted Value (A×B)", "Interpretation"]
    for col, header in enumerate(headers, start=2):
        ws.cell(row=row, column=col, value=header)
        ws.cell(row=row, column=col).font = BOLD_FONT
        ws.cell(row=row, column=col).fill = YELLOW_FILL
        ws.cell(row=row, column=col).alignment = CENTER_ALIGN
        ws.cell(row=row, column=col).border = THIN_BORDER
    row += 1

    # Coefficients
    coefficients = {
        'private': {'x1': 0.717, 'x2': 0.847, 'x3': 3.107, 'x4': 0.420, 'x5': 0.998},
        'public': {'x1': 1.200, 'x2': 1.400, 'x3': 3.300, 'x4': 0.600, 'x5': 1.000}
    }
    coef = coefficients.get(company_type, coefficients['private'])

    components = [
        ("Working Capital / Total Assets", "X1", risk.z_score_x1 if risk else None, coef['x1'],
         "Measures liquidity relative to firm size"),
        ("Retained Earnings / Total Assets", "X2", risk.z_score_x2 if risk else None, coef['x2'],
         "Measures cumulative profitability"),
        ("EBIT / Total Assets", "X3", risk.z_score_x3 if risk else None, coef['x3'],
         "Measures operating efficiency"),
        ("Book Value of Equity / Total Liabilities", "X4", risk.z_score_x4 if risk else None, coef['x4'],
         "Measures financial leverage"),
        ("Sales / Total Assets", "X5", risk.z_score_x5 if risk else None, coef['x5'],
         "Measures asset utilization"),
    ]

    total_weighted = 0
    for desc, var, value, weight, interp in components:
        ws.cell(row=row, column=2, value=desc)
        ws.cell(row=row, column=2).font = NORMAL_FONT
        ws.cell(row=row, column=2).border = THIN_BORDER

        ws.cell(row=row, column=3, value=var)
        ws.cell(row=row, column=3).font = BOLD_FONT
        ws.cell(row=row, column=3).alignment = CENTER_ALIGN
        ws.cell(row=row, column=3).border = THIN_BORDER

        # Ratio Value
        if value is not None:
            ws.cell(row=row, column=4, value=round(value, 4))
        else:
            ws.cell(row=row, column=4, value="N/A")
        ws.cell(row=row, column=4).alignment = CENTER_ALIGN
        ws.cell(row=row, column=4).border = THIN_BORDER

        # Weightage
        ws.cell(row=row, column=5, value=weight)
        ws.cell(row=row, column=5).alignment = CENTER_ALIGN
        ws.cell(row=row, column=5).border = THIN_BORDER

        # Weighted Value
        if value is not None:
            weighted = value * weight
            total_weighted += weighted
            ws.cell(row=row, column=6, value=round(weighted, 4))
            ws.cell(row=row, column=6).fill = ORANGE_FILL
        else:
            ws.cell(row=row, column=6, value="N/A")
        ws.cell(row=row, column=6).alignment = CENTER_ALIGN
        ws.cell(row=row, column=6).border = THIN_BORDER
        ws.cell(row=row, column=6).font = BOLD_FONT

        # Interpretation
        ws.cell(row=row, column=7, value=interp)
        ws.cell(row=row, column=7).font = SMALL_FONT
        ws.cell(row=row, column=7).border = THIN_BORDER

        row += 1

    row += 1

    # Z-Score Result
    ws.merge_cells(f'B{row}:E{row}')
    ws[f'B{row}'] = "CALCULATED Z-SCORE"
    ws[f'B{row}'].font = BOLD_FONT
    ws[f'B{row}'].alignment = RIGHT_ALIGN

    z_score = risk.z_score if risk else None
    ws[f'F{row}'] = round(z_score, 4) if z_score else "N/A"
    ws[f'F{row}'].font = Font(bold=True, size=14)
    ws[f'F{row}'].alignment = CENTER_ALIGN
    ws[f'F{row}'].fill = ORANGE_FILL
    ws[f'F{row}'].border = MEDIUM_BORDER
    row += 2

    # Z-Score Interpretation Table
    ws.merge_cells(f'B{row}:G{row}')
    ws[f'B{row}'] = "Z-Score Interpretation Guide"
    ws[f'B{row}'].font = HEADER_FONT
    ws[f'B{row}'].fill = SUBHEADER_FILL
    row += 1

    # Headers
    ws.cell(row=row, column=2, value="Zone")
    ws.cell(row=row, column=3, value="Private Company")
    ws.cell(row=row, column=4, value="Public Company")
    ws.cell(row=row, column=5, value="Risk Level")
    ws.merge_cells(f'F{row}:G{row}')
    ws.cell(row=row, column=6, value="Interpretation")

    for col in range(2, 7):
        ws.cell(row=row, column=col).font = BOLD_FONT
        ws.cell(row=row, column=col).fill = YELLOW_FILL
        ws.cell(row=row, column=col).alignment = CENTER_ALIGN
        ws.cell(row=row, column=col).border = THIN_BORDER
    row += 1

    zones = [
        ("Safe Zone", "Z > 2.90", "Z > 2.99", "LOW", GREEN_FILL, "Financially healthy, low risk of bankruptcy"),
        ("Grey Zone", "1.23 < Z < 2.90", "1.81 < Z < 2.99", "MEDIUM", YELLOW_FILL, "Caution - requires monitoring"),
        ("Distress Zone", "Z < 1.23", "Z < 1.81", "HIGH", RED_FILL, "High risk of financial distress"),
    ]

    for zone, private_range, public_range, risk_level, fill, interp in zones:
        ws.cell(row=row, column=2, value=zone)
        ws.cell(row=row, column=2).border = THIN_BORDER

        ws.cell(row=row, column=3, value=private_range)
        ws.cell(row=row, column=3).alignment = CENTER_ALIGN
        ws.cell(row=row, column=3).border = THIN_BORDER

        ws.cell(row=row, column=4, value=public_range)
        ws.cell(row=row, column=4).alignment = CENTER_ALIGN
        ws.cell(row=row, column=4).border = THIN_BORDER

        ws.cell(row=row, column=5, value=risk_level)
        ws.cell(row=row, column=5).alignment = CENTER_ALIGN
        ws.cell(row=row, column=5).fill = fill
        ws.cell(row=row, column=5).font = BOLD_FONT
        ws.cell(row=row, column=5).border = THIN_BORDER

        ws.merge_cells(f'F{row}:G{row}')
        ws.cell(row=row, column=6, value=interp)
        ws.cell(row=row, column=6).border = THIN_BORDER

        row += 1

    row += 2

    # Current Assessment Result
    risk_level = risk.risk_level if risk else None

    ws.merge_cells(f'B{row}:G{row}')
    ws[f'B{row}'] = "Current Assessment Result"
    ws[f'B{row}'].font = HEADER_FONT
    ws[f'B{row}'].fill = HEADER_FILL
    row += 1

    ws.merge_cells(f'B{row}:G{row+1}')
    result_text = get_zscore_assessment(z_score, risk_level, company_type)
    ws[f'B{row}'] = result_text
    ws[f'B{row}'].font = Font(bold=True, size=12)
    ws[f'B{row}'].alignment = CENTER_ALIGN

    if risk_level == 'low':
        ws[f'B{row}'].fill = GREEN_FILL
    elif risk_level == 'medium':
        ws[f'B{row}'].fill = YELLOW_FILL
    else:
        ws[f'B{row}'].fill = RED_FILL


# ==================== SHEET 5: QUALITATIVE ASSESSMENT ====================

def create_qualitative_sheet(wb: Workbook, assessment, qualitative):
    """Create the Qualitative Assessment sheet."""
    ws = wb.create_sheet("Qualitative", 4)

    # Set column widths
    ws.column_dimensions['A'].width = 5
    ws.column_dimensions['B'].width = 8
    ws.column_dimensions['C'].width = 60
    ws.column_dimensions['D'].width = 20
    ws.column_dimensions['E'].width = 40

    row = 2

    # Title
    ws.merge_cells(f'B{row}:E{row}')
    ws[f'B{row}'] = "Section C: Qualitative Assessment"
    ws[f'B{row}'].font = TITLE_FONT
    ws[f'B{row}'].fill = HEADER_FILL
    ws[f'B{row}'].alignment = CENTER_ALIGN
    row += 2

    # Instructions
    ws.merge_cells(f'B{row}:E{row}')
    ws[f'B{row}'] = "Please review the following qualitative factors that may impact the vendor's financial stability:"
    ws[f'B{row}'].font = Font(italic=True)
    row += 2

    # Headers
    headers = ["No.", "Question", "Response", "Notes/Comments"]
    cols = [2, 3, 4, 5]
    for col, header in zip(cols, headers):
        ws.cell(row=row, column=col, value=header)
        ws.cell(row=row, column=col).font = BOLD_FONT
        ws.cell(row=row, column=col).fill = YELLOW_FILL
        ws.cell(row=row, column=col).alignment = CENTER_ALIGN
        ws.cell(row=row, column=col).border = THIN_BORDER
    row += 1

    # Questions
    questions = [
        ("1", "Past working relationship with the Singtel Group?", "Q1"),
        ("2", "Any platforms or systems currently supported by vendor?", "Q2"),
        ("3", "Any legal disputes involving the vendor?", "Q3"),
        ("4", "Any material corporate governance issues? (e.g., Fraud, conflict of interest)", "Q4"),
        ("5", "Any qualified audit opinions on financial statements?", "Q5"),
        ("6", "Any going concern or insolvency risk identified?", "Q6"),
        ("7", "Experience with major projects of similar scale?", "Q7"),
        ("8", "Any withholding tax implications? (usually applicable for foreign companies)", "Q8"),
        ("9", "Any support from parent or holding or related company?", "Q9"),
        ("10", "Please elaborate on related party transactions/loans, guarantee and contingent liabilities", "Q10"),
        ("11", "Any customer/territory/product dominance from segmentation of operations?", "Q11"),
    ]

    for q_num, q_text, q_id in questions:
        ws.cell(row=row, column=2, value=q_num)
        ws.cell(row=row, column=2).alignment = CENTER_ALIGN
        ws.cell(row=row, column=2).border = THIN_BORDER

        ws.cell(row=row, column=3, value=q_text)
        ws.cell(row=row, column=3).alignment = WRAP_ALIGN
        ws.cell(row=row, column=3).border = THIN_BORDER

        # Find response
        response = ""
        notes = ""
        for qr in qualitative:
            if qr.question_id == q_id:
                response = qr.response or ""
                notes = qr.notes or ""
                break

        ws.cell(row=row, column=4, value=response if response else "N/A")
        ws.cell(row=row, column=4).alignment = CENTER_ALIGN
        ws.cell(row=row, column=4).border = THIN_BORDER
        ws.cell(row=row, column=4).fill = LIGHT_YELLOW_FILL

        # Color code Yes/No responses
        if response.lower() == 'yes':
            if q_num in ['3', '4', '5', '6']:  # Negative indicators
                ws.cell(row=row, column=4).fill = RED_FILL
            else:
                ws.cell(row=row, column=4).fill = GREEN_FILL
        elif response.lower() == 'no':
            if q_num in ['3', '4', '5', '6']:  # Negative indicators
                ws.cell(row=row, column=4).fill = GREEN_FILL

        ws.cell(row=row, column=5, value=notes if notes else "-")
        ws.cell(row=row, column=5).alignment = WRAP_ALIGN
        ws.cell(row=row, column=5).border = THIN_BORDER

        # Set row height for wrapped text
        ws.row_dimensions[row].height = 30
        row += 1

    row += 2

    # Qualitative Risk Summary
    ws.merge_cells(f'B{row}:E{row}')
    ws[f'B{row}'] = "Qualitative Risk Factors Summary"
    ws[f'B{row}'].font = SUBHEADER_FONT
    ws[f'B{row}'].fill = GRAY_FILL
    row += 1

    # Count concerns
    concerns = []
    for qr in qualitative:
        if qr.response and qr.response.lower() == 'yes':
            if qr.question_id in ['Q3', 'Q4', 'Q5', 'Q6']:
                concerns.append(qr.question_text)

    if concerns:
        ws.merge_cells(f'B{row}:E{row}')
        ws[f'B{row}'] = "Areas of Concern Identified:"
        ws[f'B{row}'].font = BOLD_FONT
        ws[f'B{row}'].fill = RED_FILL
        row += 1
        for concern in concerns:
            ws.merge_cells(f'B{row}:E{row}')
            ws[f'B{row}'] = f"  • {concern}"
            row += 1
    else:
        ws.merge_cells(f'B{row}:E{row}')
        ws[f'B{row}'] = "No significant qualitative concerns identified."
        ws[f'B{row}'].fill = GREEN_FILL


# ==================== SHEET 6: CONCLUSION ====================

# Red font for notes
RED_FONT = Font(color="FF0000", size=9)

def create_conclusion_sheet(wb: Workbook, assessment, recommendation, risk):
    """Create the Conclusion sheet with summary and key findings only."""
    ws = wb.create_sheet("Conclusion", 5)

    # Set column widths to match template
    ws.column_dimensions['A'].width = 5
    ws.column_dimensions['B'].width = 45
    ws.column_dimensions['C'].width = 25
    ws.column_dimensions['D'].width = 20
    ws.column_dimensions['E'].width = 12
    ws.column_dimensions['F'].width = 15
    ws.column_dimensions['G'].width = 15
    ws.column_dimensions['H'].width = 15

    row = 2

    # ==================== SECTION D HEADER ====================
    ws.merge_cells(f'A{row}:H{row}')
    ws[f'A{row}'] = "Section D: Conclusion"
    ws[f'A{row}'].font = TITLE_FONT
    ws[f'A{row}'].fill = HEADER_FILL
    ws[f'A{row}'].alignment = CENTER_ALIGN
    row += 2

    # ==================== SUMMARY OF ASSESSMENT ====================
    ws.merge_cells(f'A{row}:H{row}')
    ws[f'A{row}'] = "Summary of Assessment"
    ws[f'A{row}'].font = WHITE_FONT
    ws[f'A{row}'].fill = HEADER_FILL
    row += 1

    summary_text = recommendation.summary if recommendation and recommendation.summary else "Summary not available."
    ws.merge_cells(f'A{row}:H{row+4}')
    ws[f'A{row}'] = summary_text
    ws[f'A{row}'].alignment = WRAP_ALIGN
    ws[f'A{row}'].border = THIN_BORDER
    ws.row_dimensions[row].height = 60
    row += 6

    # ==================== KEY FINDINGS ====================
    if recommendation and recommendation.supporting_factors:
        ws.merge_cells(f'A{row}:H{row}')
        ws[f'A{row}'] = "Key Findings"
        ws[f'A{row}'].font = WHITE_FONT
        ws[f'A{row}'].fill = HEADER_FILL
        row += 1

        for i, factor in enumerate(recommendation.supporting_factors[:5], 1):
            ws[f'A{row}'] = f"{i}"
            ws[f'A{row}'].alignment = CENTER_ALIGN
            ws.merge_cells(f'B{row}:H{row}')
            ws[f'B{row}'] = factor
            ws[f'B{row}'].alignment = WRAP_ALIGN
            ws.row_dimensions[row].height = 25
            row += 1


# ==================== SHEET 7: APPROVAL ====================

def create_approval_sheet(wb: Workbook, assessment, recommendation):
    """Create the Approval sheet with Risk Mitigation, Final Conclusion, and CFU Finance Approval."""
    ws = wb.create_sheet("Approval", 6)

    # Set column widths to match template
    ws.column_dimensions['A'].width = 5
    ws.column_dimensions['B'].width = 55
    ws.column_dimensions['C'].width = 8
    ws.column_dimensions['D'].width = 20
    ws.column_dimensions['E'].width = 8
    ws.column_dimensions['F'].width = 15
    ws.column_dimensions['G'].width = 15
    ws.column_dimensions['H'].width = 15

    rec_type = recommendation.recommendation_type if recommendation else None
    row = 2

    # ==================== RISK MITIGATION MEASURES ====================
    ws.merge_cells(f'A{row}:H{row}')
    ws[f'A{row}'] = "Risk Mitigation Measures needed (E.g. banker's guarantee, review of parent company)"
    ws[f'A{row}'].font = WHITE_FONT
    ws[f'A{row}'].fill = HEADER_FILL
    row += 2

    if rec_type == 'proceed_with_mitigation':
        ws[f'A{row}'] = "1"
        ws.merge_cells(f'B{row}:H{row}')
        ws[f'B{row}'] = "Payment upon completion of work and no advance payment"
        row += 1

        ws[f'A{row}'] = "2"
        ws.merge_cells(f'B{row}:H{row}')
        ws[f'B{row}'] = f"Recommended to have alternative vendor and backup plan if {assessment.vendor_name} is unable to fulfil its obligations to Singtel"
        ws.row_dimensions[row].height = 30
        row += 1
    elif rec_type == 'do_not_proceed':
        ws.merge_cells(f'A{row}:H{row}')
        ws[f'A{row}'] = "Engagement with this vendor is not recommended due to high financial risk."
        row += 1
    else:
        ws.merge_cells(f'A{row}:H{row}')
        ws[f'A{row}'] = "No specific mitigation measures required - vendor is financially stable."
        row += 1

    row += 2

    # ==================== FINAL CONCLUSION ====================
    ws.merge_cells(f'A{row}:H{row}')
    ws[f'A{row}'] = "Final Conclusion (more than 1 option may apply)"
    ws[f'A{row}'].font = WHITE_FONT
    ws[f'A{row}'].fill = HEADER_FILL
    row += 2

    # Conclusion options with checkbox column
    conclusions = [
        ("proceed", "Proceed without risk mitigation measures (Financially Stable)"),
        ("proceed_with_mitigation", "Proceed with risk mitigation measures (Financially Unstable)"),
        ("do_not_proceed", "Do not proceed (Financially Unstable)"),
    ]

    for code, text in conclusions:
        ws.merge_cells(f'A{row}:D{row}')
        ws[f'A{row}'] = text
        ws[f'A{row}'].font = NORMAL_FONT

        # Checkbox cell
        ws[f'E{row}'] = "V" if rec_type == code else ""
        ws[f'E{row}'].alignment = CENTER_ALIGN
        ws[f'E{row}'].font = Font(bold=True, size=12)
        ws[f'E{row}'].border = MEDIUM_BORDER

        row += 1

    row += 2

    # ==================== CFU FINANCE APPROVAL ====================
    ws.merge_cells(f'A{row}:B{row}')
    ws[f'A{row}'] = "CFU Finance Approval"
    ws[f'A{row}'].font = WHITE_FONT
    ws[f'A{row}'].fill = HEADER_FILL

    ws.merge_cells(f'C{row}:D{row}')
    ws[f'C{row}'] = "Name"
    ws[f'C{row}'].font = WHITE_FONT
    ws[f'C{row}'].fill = HEADER_FILL
    ws[f'C{row}'].alignment = CENTER_ALIGN

    ws.merge_cells(f'E{row}:F{row}')
    ws[f'E{row}'] = "Signature"
    ws[f'E{row}'].font = WHITE_FONT
    ws[f'E{row}'].fill = HEADER_FILL
    ws[f'E{row}'].alignment = CENTER_ALIGN

    ws[f'G{row}'] = "Date"
    ws[f'G{row}'].font = WHITE_FONT
    ws[f'G{row}'].fill = HEADER_FILL
    ws[f'G{row}'].alignment = CENTER_ALIGN

    row += 1

    # Empty row
    row += 1

    # Prepared By row
    ws.merge_cells(f'A{row}:B{row}')
    ws[f'A{row}'] = "Prepared By"
    ws[f'A{row}'].alignment = RIGHT_ALIGN
    ws[f'A{row}'].font = BOLD_FONT

    ws[f'C{row}'] = "*"
    ws[f'C{row}'].font = Font(color="FF0000", bold=True)
    ws[f'C{row}'].alignment = CENTER_ALIGN

    ws[f'D{row}'] = ""  # Name field - editable
    ws[f'D{row}'].fill = LIGHT_YELLOW_FILL
    ws[f'D{row}'].border = THIN_BORDER

    ws.merge_cells(f'E{row}:F{row}')
    ws[f'E{row}'] = ""  # Signature field
    ws[f'E{row}'].border = THIN_BORDER

    ws[f'G{row}'] = datetime.now().strftime("%d-%b-%y")
    ws[f'G{row}'].alignment = CENTER_ALIGN

    row += 1

    # Approved By CFU Finance Director row
    ws.merge_cells(f'A{row}:B{row}')
    ws[f'A{row}'] = "Approved By CFU Finance Director"
    ws[f'A{row}'].alignment = RIGHT_ALIGN
    ws[f'A{row}'].font = BOLD_FONT

    ws[f'C{row}'] = ""
    ws[f'D{row}'] = ""  # Name field - editable
    ws[f'D{row}'].fill = LIGHT_YELLOW_FILL
    ws[f'D{row}'].border = THIN_BORDER

    ws.merge_cells(f'E{row}:F{row}')
    ws[f'E{row}'] = ""  # Signature field
    ws[f'E{row}'].border = THIN_BORDER

    ws[f'G{row}'] = ""
    ws[f'G{row}'].border = THIN_BORDER

    row += 1

    # Approved By BU CFO row
    ws.merge_cells(f'A{row}:B{row}')
    ws[f'A{row}'] = "Approved By BU CFO #"
    ws[f'A{row}'].alignment = RIGHT_ALIGN
    ws[f'A{row}'].font = BOLD_FONT

    ws[f'C{row}'] = ""
    ws[f'D{row}'] = ""  # Name field
    ws[f'D{row}'].border = THIN_BORDER

    ws.merge_cells(f'E{row}:F{row}')
    ws[f'E{row}'] = ""  # Signature field
    ws[f'E{row}'].border = THIN_BORDER

    ws[f'G{row}'] = ""
    ws[f'G{row}'].border = THIN_BORDER

    row += 1

    # ==================== FOOTNOTES ====================
    ws.merge_cells(f'A{row}:H{row}')
    ws[f'A{row}'] = "* Preparer to check with requestor on whether the VFA will be presented in papers that will be submitted to BU MC, GCFO, Procurement Committee, Group MC, FIC or Board."
    ws[f'A{row}'].font = RED_FONT
    ws[f'A{row}'].alignment = WRAP_ALIGN
    ws.row_dimensions[row].height = 30
    row += 1

    ws.merge_cells(f'A{row}:H{row}')
    ws[f'A{row}'] = "# Second approval by BU CFO is required if the VFA is to be presented in papers that will be submitted to BU MC, GCFO, Procurement Committee, Group MC, FIC or Board."
    ws[f'A{row}'].font = RED_FONT
    ws[f'A{row}'].alignment = WRAP_ALIGN
    ws.row_dimensions[row].height = 30
    row += 2

    # Version date
    ws[f'A{row}'] = f"Version date: {datetime.now().strftime('%d %b %Y')}"
    ws[f'A{row}'].font = SMALL_FONT


# ==================== HELPER FUNCTIONS ====================

def apply_border_range(ws, cell_range):
    """Apply border to a range of cells."""
    from openpyxl.utils import range_boundaries
    min_col, min_row, max_col, max_row = range_boundaries(cell_range)
    for row in range(min_row, max_row + 1):
        for col in range(min_col, max_col + 1):
            ws.cell(row=row, column=col).border = THIN_BORDER


def get_risk_indicator(value, ratio_type):
    """Return risk indicator arrow and fill based on value and ratio type."""
    if value is None or ratio_type is None:
        return "-", None

    thresholds = {
        "current_ratio": {"good": 1.05, "above_avg": 0.95, "below_avg": 0.5},
        "quick_ratio": {"good": 0.95, "above_avg": 0.75, "below_avg": 0.3},
        "cash_ratio": {"good": 0.3, "above_avg": 0.2, "below_avg": 0.1},
        "working_capital_ratio": {"good": 0.4, "above_avg": 0.06, "below_avg": 0},
        "roa": {"good": 6, "above_avg": 4, "below_avg": 2},
        "roe": {"good": 11, "above_avg": 9, "below_avg": 5},
        "net_margin": {"good": 8, "above_avg": 5, "below_avg": 2},
        "debt_to_assets": {"good": 0.5, "above_avg": 1.2, "below_avg": 1.5, "inverse": True},
        "debt_to_equity": {"good": 0.38, "above_avg": 0.83, "below_avg": 2.22, "inverse": True},
    }

    config = thresholds.get(ratio_type, {"good": 1, "above_avg": 0.5, "below_avg": 0})
    is_inverse = config.get("inverse", False)

    if is_inverse:
        if value <= config["good"]:
            return "↑", GREEN_FILL
        elif value <= config["above_avg"]:
            return "↗", LIGHT_YELLOW_FILL
        elif value <= config["below_avg"]:
            return "↘", ORANGE_FILL
        else:
            return "↓", RED_FILL
    else:
        if value >= config["good"]:
            return "↑", GREEN_FILL
        elif value >= config["above_avg"]:
            return "↗", LIGHT_YELLOW_FILL
        elif value >= config["below_avg"]:
            return "↘", ORANGE_FILL
        else:
            return "↓", RED_FILL


def get_risk_label(risk_level):
    """Get display label for risk level."""
    labels = {
        'low': 'LOW RISK - Safe Zone',
        'medium': 'MEDIUM RISK - Grey Zone',
        'high': 'HIGH RISK - Distress Zone'
    }
    return labels.get(risk_level, 'UNKNOWN')


def get_recommendation_display(rec_type):
    """Get display text for recommendation type."""
    displays = {
        'proceed': 'PROCEED - Vendor is Financially Stable',
        'proceed_with_mitigation': 'PROCEED WITH CAUTION - Risk Mitigation Required',
        'do_not_proceed': 'DO NOT PROCEED - High Financial Risk'
    }
    return displays.get(rec_type, 'PENDING ASSESSMENT')


def get_assessment_text(value, ratio_type):
    """Get assessment text based on ratio value."""
    if value is None:
        return "N/A"

    indicator, _ = get_risk_indicator(value, ratio_type)
    texts = {
        "↑": "Good",
        "↗": "Acceptable",
        "↘": "Concern",
        "↓": "Poor"
    }
    return texts.get(indicator, "N/A")


def get_zscore_assessment(z_score, risk_level, company_type):
    """Get Z-score assessment text."""
    if z_score is None:
        return "Unable to calculate Z-Score due to insufficient data"

    if risk_level == 'low':
        return f"Z-Score of {z_score:.2f} indicates LOW RISK - Company is in the Safe Zone with strong financial health"
    elif risk_level == 'medium':
        return f"Z-Score of {z_score:.2f} indicates MEDIUM RISK - Company is in the Grey Zone requiring careful monitoring"
    else:
        return f"Z-Score of {z_score:.2f} indicates HIGH RISK - Company is in the Distress Zone with elevated bankruptcy risk"
