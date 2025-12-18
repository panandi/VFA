"""PDF Report Generator for Vendor Financial Assessment."""

from io import BytesIO
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

from app.models.assessment import VendorAssessment


def generate_assessment_pdf(assessment: VendorAssessment) -> BytesIO:
    """Generate a PDF report for the assessment."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72
    )

    # Styles
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name='MainTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#ED1C24')
    ))
    styles.add(ParagraphStyle(
        name='SectionTitle',
        parent=styles['Heading2'],
        fontSize=14,
        spaceBefore=20,
        spaceAfter=10,
        textColor=colors.HexColor('#333333')
    ))
    styles.add(ParagraphStyle(
        name='CustomBody',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=8,
        leading=14
    ))
    styles.add(ParagraphStyle(
        name='SmallText',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.gray
    ))

    # Build content
    content = []

    # Title
    content.append(Paragraph("Vendor Financial Assessment Report", styles['MainTitle']))
    content.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#ED1C24')))
    content.append(Spacer(1, 20))

    # Vendor Information
    content.append(Paragraph("Vendor Information", styles['SectionTitle']))
    vendor_data = [
        ["Vendor Name:", assessment.vendor_name or "N/A"],
        ["Registration Number:", assessment.vendor_registration_number or "N/A"],
        ["Assessment Date:", assessment.created_at.strftime("%Y-%m-%d") if assessment.created_at else "N/A"],
        ["Status:", assessment.status.replace("_", " ").title() if assessment.status else "N/A"],
    ]
    vendor_table = Table(vendor_data, colWidths=[2*inch, 4*inch])
    vendor_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    content.append(vendor_table)
    content.append(Spacer(1, 20))

    # Recommendation Section
    if assessment.recommendation:
        rec = assessment.recommendation
        content.append(Paragraph("AI Recommendation", styles['SectionTitle']))

        # Recommendation type with color
        rec_type = rec.recommendation_type or "pending"
        rec_colors = {
            'proceed': colors.HexColor('#16A34A'),
            'proceed_with_mitigation': colors.HexColor('#CA8A04'),
            'do_not_proceed': colors.HexColor('#DC2626')
        }
        rec_color = rec_colors.get(rec_type, colors.gray)

        rec_text = rec_type.replace("_", " ").upper()
        content.append(Paragraph(
            f"<font color='{rec_color.hexval()}'><b>{rec_text}</b></font>",
            styles['CustomBody']
        ))

        if rec.recommendation_text:
            content.append(Spacer(1, 10))
            content.append(Paragraph(rec.recommendation_text, styles['CustomBody']))

        if rec.summary:
            content.append(Spacer(1, 10))
            content.append(Paragraph("<b>Executive Summary:</b>", styles['CustomBody']))
            content.append(Paragraph(rec.summary, styles['CustomBody']))

        if rec.supporting_factors:
            content.append(Spacer(1, 10))
            content.append(Paragraph("<b>Supporting Factors:</b>", styles['CustomBody']))
            for i, factor in enumerate(rec.supporting_factors, 1):
                content.append(Paragraph(f"{i}. {factor}", styles['CustomBody']))

        content.append(Spacer(1, 20))

    # Risk Assessment / Z-Score Section
    if assessment.risk_assessment:
        risk = assessment.risk_assessment
        content.append(Paragraph("Financial Risk Assessment", styles['SectionTitle']))

        # Z-Score
        z_score = risk.z_score
        risk_level = risk.risk_level or "unknown"

        z_data = [
            ["Altman Z-Score:", f"{z_score:.3f}" if z_score else "N/A"],
            ["Risk Level:", risk_level.upper()],
            ["Fiscal Year:", str(risk.fiscal_year_used) if risk.fiscal_year_used else "N/A"],
        ]
        z_table = Table(z_data, colWidths=[2*inch, 2*inch])
        z_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        content.append(z_table)
        content.append(Spacer(1, 10))

        # Z-Score interpretation
        content.append(Paragraph("<b>Z-Score Interpretation:</b>", styles['CustomBody']))
        content.append(Paragraph("* > 2.9: Low Risk (Safe Zone)", styles['CustomBody']))
        content.append(Paragraph("* 1.23 - 2.9: Medium Risk (Gray Zone)", styles['CustomBody']))
        content.append(Paragraph("* < 1.23: High Risk (Distress Zone)", styles['CustomBody']))
        content.append(Spacer(1, 15))

        # Z-Score Components
        content.append(Paragraph("<b>Z-Score Components:</b>", styles['CustomBody']))
        components_data = [
            ["Component", "Value", "Weight", "Weighted"],
            ["X1: Working Capital / Total Assets",
             f"{risk.z_score_x1:.4f}" if risk.z_score_x1 else "-",
             "0.717",
             f"{risk.z_score_x1 * 0.717:.4f}" if risk.z_score_x1 else "-"],
            ["X2: Retained Earnings / Total Assets",
             f"{risk.z_score_x2:.4f}" if risk.z_score_x2 else "-",
             "0.847",
             f"{risk.z_score_x2 * 0.847:.4f}" if risk.z_score_x2 else "-"],
            ["X3: EBIT / Total Assets",
             f"{risk.z_score_x3:.4f}" if risk.z_score_x3 else "-",
             "3.107",
             f"{risk.z_score_x3 * 3.107:.4f}" if risk.z_score_x3 else "-"],
            ["X4: Equity / Total Liabilities",
             f"{risk.z_score_x4:.4f}" if risk.z_score_x4 else "-",
             "0.420",
             f"{risk.z_score_x4 * 0.420:.4f}" if risk.z_score_x4 else "-"],
            ["X5: Sales / Total Assets",
             f"{risk.z_score_x5:.4f}" if risk.z_score_x5 else "-",
             "0.998",
             f"{risk.z_score_x5 * 0.998:.4f}" if risk.z_score_x5 else "-"],
        ]
        comp_table = Table(components_data, colWidths=[2.5*inch, 1.2*inch, 0.8*inch, 1*inch])
        comp_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F3F4F6')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.gray),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ]))
        content.append(comp_table)
        content.append(Spacer(1, 20))

        # Financial Ratios
        content.append(Paragraph("Key Financial Ratios", styles['SectionTitle']))

        ratios_data = [
            ["Ratio", "Value"],
            ["Current Ratio", f"{risk.current_ratio:.3f}" if risk.current_ratio else "-"],
            ["Quick Ratio", f"{risk.quick_ratio:.3f}" if risk.quick_ratio else "-"],
            ["Debt-to-Equity", f"{risk.debt_to_equity:.3f}" if risk.debt_to_equity else "-"],
            ["Debt-to-Assets", f"{risk.debt_to_assets:.3f}" if risk.debt_to_assets else "-"],
            ["ROA", f"{risk.roa:.2f}%" if risk.roa else "-"],
            ["ROE", f"{risk.roe:.2f}%" if risk.roe else "-"],
            ["Gross Margin", f"{risk.gross_margin:.2f}%" if risk.gross_margin else "-"],
            ["Net Margin", f"{risk.net_margin:.2f}%" if risk.net_margin else "-"],
            ["Asset Turnover", f"{risk.asset_turnover:.3f}" if risk.asset_turnover else "-"],
        ]
        ratios_table = Table(ratios_data, colWidths=[3*inch, 1.5*inch])
        ratios_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F3F4F6')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.gray),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ]))
        content.append(ratios_table)
        content.append(Spacer(1, 20))

    # Qualitative Assessment
    if assessment.qualitative_responses:
        content.append(Paragraph("Qualitative Assessment", styles['SectionTitle']))
        qual_data = [["Question", "Response"]]
        for q in assessment.qualitative_responses:
            response = q.response.upper() if q.response else "Not Answered"
            qual_data.append([q.question_text, response])

        qual_table = Table(qual_data, colWidths=[4.5*inch, 1*inch])
        qual_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F3F4F6')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.gray),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (1, 0), (1, -1), 'CENTER'),
        ]))
        content.append(qual_table)
        content.append(Spacer(1, 20))

    # Sign-off Section
    if assessment.recommendation and assessment.recommendation.is_signed_off:
        content.append(Paragraph("Sign-Off", styles['SectionTitle']))
        signoff_data = [
            ["Signed Off:", "Yes"],
            ["Signed Off At:", assessment.recommendation.signed_off_at.strftime("%Y-%m-%d %H:%M") if assessment.recommendation.signed_off_at else "N/A"],
        ]
        signoff_table = Table(signoff_data, colWidths=[2*inch, 3*inch])
        signoff_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        content.append(signoff_table)
        content.append(Spacer(1, 20))

    # Footer
    content.append(Spacer(1, 30))
    content.append(HRFlowable(width="100%", thickness=1, color=colors.gray))
    content.append(Spacer(1, 10))
    content.append(Paragraph(
        f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Vendor Financial Assessment System",
        styles['SmallText']
    ))

    # Build PDF
    doc.build(content)
    buffer.seek(0)
    return buffer
