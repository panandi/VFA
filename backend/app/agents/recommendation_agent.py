"""
Recommendation Agent - Agent 2
Generates AI-powered recommendations based on financial analysis.
"""

import json
from typing import Dict, Any, List
from openai import AsyncOpenAI

from app.core.config import settings
from app.models.assessment import VendorAssessment, RiskAssessment, QualitativeResponse


def get_recommendation_prompt() -> str:
    """Get the system prompt for recommendation generation."""
    return """You are a financial risk assessment expert for Singtel's vendor evaluation process.
Based on the provided financial analysis and qualitative assessment data, generate a comprehensive recommendation.

Your response must be a JSON object with the following structure:
{
    "recommendation_type": "proceed" | "proceed_with_mitigation" | "do_not_proceed",
    "recommendation_text": "Brief explanation of the recommendation",
    "supporting_factors": [
        "Factor 1",
        "Factor 2",
        "Factor 3",
        ...
    ],
    "summary": "A comprehensive paragraph summarizing the vendor's financial health and suitability as a business partner"
}

Guidelines for recommendation:
1. "proceed" - Z-Score > 2.9, strong liquidity ratios, no major qualitative concerns
2. "proceed_with_mitigation" - Z-Score between 1.23 and 2.9, OR some qualitative concerns
3. "do_not_proceed" - Z-Score < 1.23, severe financial distress indicators, OR major qualitative red flags

Consider these factors:
- Z-Score and risk level
- Liquidity ratios (Current Ratio > 1.5 is healthy)
- Profitability metrics (positive ROA/ROE)
- Leverage ratios (Debt-to-Equity < 2 is generally acceptable)
- Qualitative factors (legal disputes, governance issues, past relationship)
- Trend analysis (improving vs deteriorating metrics)

Return ONLY the JSON object, no additional text."""


def format_financial_data(risk_assessment: RiskAssessment) -> str:
    """Format risk assessment data for the AI prompt."""
    data = {
        "z_score": {
            "value": risk_assessment.z_score,
            "risk_level": risk_assessment.risk_level,
            "components": {
                "working_capital_to_assets": risk_assessment.z_score_x1,
                "retained_earnings_to_assets": risk_assessment.z_score_x2,
                "ebit_to_assets": risk_assessment.z_score_x3,
                "equity_to_liabilities": risk_assessment.z_score_x4,
                "sales_to_assets": risk_assessment.z_score_x5
            }
        },
        "liquidity_ratios": {
            "current_ratio": risk_assessment.current_ratio,
            "quick_ratio": risk_assessment.quick_ratio,
            "cash_ratio": risk_assessment.cash_ratio
        },
        "profitability_ratios": {
            "gross_margin_percent": risk_assessment.gross_margin,
            "operating_margin_percent": risk_assessment.operating_margin,
            "net_margin_percent": risk_assessment.net_margin,
            "roa_percent": risk_assessment.roa,
            "roe_percent": risk_assessment.roe
        },
        "leverage_ratios": {
            "debt_to_equity": risk_assessment.debt_to_equity,
            "debt_to_assets": risk_assessment.debt_to_assets,
            "interest_coverage": risk_assessment.interest_coverage
        },
        "efficiency_ratios": {
            "asset_turnover": risk_assessment.asset_turnover,
            "inventory_turnover": risk_assessment.inventory_turnover,
            "receivables_turnover": risk_assessment.receivables_turnover
        },
        "fiscal_year_analyzed": risk_assessment.fiscal_year_used
    }
    return json.dumps(data, indent=2, default=str)


def format_qualitative_data(responses: List[QualitativeResponse]) -> str:
    """Format qualitative responses for the AI prompt."""
    formatted = []
    for r in responses:
        formatted.append({
            "question": r.question_text,
            "response": r.response or "Not answered",
            "notes": r.notes or ""
        })
    return json.dumps(formatted, indent=2)


async def generate_recommendation(
    assessment: VendorAssessment,
    risk_assessment: RiskAssessment,
    qualitative_responses: List[QualitativeResponse]
) -> Dict[str, Any]:
    """Generate AI recommendation based on assessment data."""

    financial_data = format_financial_data(risk_assessment)
    qualitative_data = format_qualitative_data(qualitative_responses)

    user_message = f"""Analyze the following vendor assessment data and provide a recommendation:

VENDOR: {assessment.vendor_name}
REGISTRATION: {assessment.vendor_registration_number or 'N/A'}

FINANCIAL ANALYSIS:
{financial_data}

QUALITATIVE ASSESSMENT:
{qualitative_data}

Based on this comprehensive analysis, provide your recommendation."""

    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    try:
        response = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": get_recommendation_prompt()},
                {"role": "user", "content": user_message}
            ],
            temperature=0.3
        )

        content = response.choices[0].message.content

        # Parse JSON from response
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        recommendation = json.loads(content.strip())

        # Validate recommendation type
        valid_types = ["proceed", "proceed_with_mitigation", "do_not_proceed"]
        if recommendation.get("recommendation_type") not in valid_types:
            recommendation["recommendation_type"] = "proceed_with_mitigation"

        return recommendation

    except Exception as e:
        # Fallback recommendation based on Z-Score
        z_score = risk_assessment.z_score or 0

        if z_score > 2.9:
            rec_type = "proceed"
            factors = [
                f"Z-Score of {z_score:.2f} indicates low financial distress risk",
                "Automated fallback recommendation due to processing error"
            ]
        elif z_score >= 1.23:
            rec_type = "proceed_with_mitigation"
            factors = [
                f"Z-Score of {z_score:.2f} indicates moderate risk",
                "Additional due diligence recommended",
                "Automated fallback recommendation due to processing error"
            ]
        else:
            rec_type = "do_not_proceed"
            factors = [
                f"Z-Score of {z_score:.2f} indicates high financial distress risk",
                "Significant financial concerns identified",
                "Automated fallback recommendation due to processing error"
            ]

        return {
            "recommendation_type": rec_type,
            "recommendation_text": f"Recommendation based on Z-Score analysis (AI processing error: {str(e)})",
            "supporting_factors": factors,
            "summary": f"The vendor has a Z-Score of {z_score:.2f}, which indicates {risk_assessment.risk_level or 'unknown'} risk level. Please review the detailed financial ratios for a complete assessment."
        }
