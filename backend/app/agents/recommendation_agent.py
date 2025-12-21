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

## Z-Score Interpretation Guidelines:

### Overall Z-Score Thresholds:
- Low Risk (Safe Zone): Z-Score > 2.90
- Medium Risk (Grey Zone): Z-Score between 1.23 and 2.90
- High Risk (Distress Zone): Z-Score < 1.23

### Z-Score Components and Their Risk Thresholds:
1. X1 (Working Capital / Total Assets):
   - Low Risk: >= 0.414
   - Medium Risk: > -0.061 and < 0.414
   - High Risk: <= -0.061

2. X2 (Retained Earnings / Total Assets):
   - Low Risk: >= 0.355
   - Medium Risk: > -0.626 and < 0.355
   - High Risk: <= -0.626

3. X3 (EBIT / Total Assets):
   - Low Risk: >= 0.154
   - Medium Risk: > -0.318 and < 0.154
   - High Risk: <= -0.318

4. X4 (Equity / Total Liabilities) - Private Company:
   - Low Risk: >= 2.684
   - Medium Risk: > 0.494 and < 2.684
   - High Risk: <= 0.494

5. X5 (Sales / Total Assets):
   - Low Risk: >= 1.939
   - Medium Risk: > 1.503 and < 1.939
   - High Risk: <= 1.503

## Ratio Risk Level Interpretations:
- "low" = Healthy/Safe
- "medium" = Moderate concern, monitor closely
- "high" = Significant concern
- "inadequate" = Critical concern, immediate action needed

## Recommendation Guidelines:
1. "proceed" - Z-Score > 2.9, majority of ratios show low risk, no major qualitative concerns
2. "proceed_with_mitigation" - Z-Score between 1.23 and 2.9, OR mixed ratio risk levels, OR some qualitative concerns
3. "do_not_proceed" - Z-Score < 1.23, OR multiple ratios showing inadequate/high risk, OR major qualitative red flags

## Key Considerations:
- Weight the Z-Score heavily as the primary indicator of financial distress risk
- Analyze each Z-Score component individually to identify specific areas of concern
- Consider liquidity ratios (Current Ratio > 1.05 is low risk, < 0.5 is inadequate)
- Evaluate profitability metrics (ROA > 6% is low risk, < 2% is inadequate)
- Assess leverage (Debt-to-Equity < 0.38 is low risk, > 2.22 is inadequate)
- Factor in growth trends if available
- Consider qualitative factors (legal disputes, governance, past relationship)

Return ONLY the JSON object, no additional text."""


def format_financial_data(risk_assessment: RiskAssessment) -> str:
    """Format risk assessment data for the AI prompt."""

    # Parse ratios_detail if it's stored as JSON string
    ratios_detail = risk_assessment.ratios_detail
    if isinstance(ratios_detail, str):
        try:
            ratios_detail = json.loads(ratios_detail)
        except:
            ratios_detail = {}

    # Extract component risk levels from ratios_detail if available
    z_score_info = ratios_detail.get("z_score", {}) if ratios_detail else {}
    component_risks = z_score_info.get("component_risks", {})

    data = {
        "z_score": {
            "value": risk_assessment.z_score,
            "risk_level": risk_assessment.risk_level,
            "company_type": risk_assessment.company_type or "private",
            "interpretation": _get_z_score_interpretation(risk_assessment.z_score, risk_assessment.risk_level),
            "components": {
                "x1_working_capital_to_assets": {
                    "value": risk_assessment.z_score_x1,
                    "risk_level": component_risks.get("x1_risk"),
                    "description": "Working Capital / Total Assets - measures liquidity position"
                },
                "x2_retained_earnings_to_assets": {
                    "value": risk_assessment.z_score_x2,
                    "risk_level": component_risks.get("x2_risk"),
                    "description": "Retained Earnings / Total Assets - measures cumulative profitability"
                },
                "x3_ebit_to_assets": {
                    "value": risk_assessment.z_score_x3,
                    "risk_level": component_risks.get("x3_risk"),
                    "description": "EBIT / Total Assets - measures operating efficiency"
                },
                "x4_equity_to_liabilities": {
                    "value": risk_assessment.z_score_x4,
                    "risk_level": component_risks.get("x4_risk"),
                    "description": "Book Value of Equity / Total Liabilities - measures leverage"
                },
                "x5_sales_to_assets": {
                    "value": risk_assessment.z_score_x5,
                    "risk_level": component_risks.get("x5_risk"),
                    "description": "Sales / Total Assets - measures asset utilization"
                }
            }
        },
        "liquidity_ratios": {
            "working_capital_ratio": {
                "value": risk_assessment.working_capital_ratio,
                "risk_level": _get_ratio_risk_from_detail(ratios_detail, "liquidity", "working_capital_ratio")
            },
            "current_ratio": {
                "value": risk_assessment.current_ratio,
                "risk_level": _get_ratio_risk_from_detail(ratios_detail, "liquidity", "current_ratio")
            },
            "quick_ratio": {
                "value": risk_assessment.quick_ratio,
                "risk_level": _get_ratio_risk_from_detail(ratios_detail, "liquidity", "quick_ratio")
            },
            "cash_ratio": {
                "value": risk_assessment.cash_ratio,
                "risk_level": None
            }
        },
        "profitability_ratios": {
            "gross_margin_percent": {
                "value": risk_assessment.gross_margin,
                "risk_level": None
            },
            "operating_margin_percent": {
                "value": risk_assessment.operating_margin,
                "risk_level": None
            },
            "net_margin_percent": {
                "value": risk_assessment.net_margin,
                "risk_level": None
            },
            "roa_percent": {
                "value": risk_assessment.roa,
                "risk_level": _get_ratio_risk_from_detail(ratios_detail, "profitability", "roa")
            },
            "roe_percent": {
                "value": risk_assessment.roe,
                "risk_level": _get_ratio_risk_from_detail(ratios_detail, "profitability", "roe")
            }
        },
        "leverage_ratios": {
            "debt_to_equity": {
                "value": risk_assessment.debt_to_equity,
                "risk_level": _get_ratio_risk_from_detail(ratios_detail, "leverage", "debt_to_equity")
            },
            "debt_to_assets": {
                "value": risk_assessment.debt_to_assets,
                "risk_level": _get_ratio_risk_from_detail(ratios_detail, "leverage", "debt_to_assets")
            },
            "interest_coverage": {
                "value": risk_assessment.interest_coverage,
                "risk_level": None
            },
            "retained_earnings_to_assets": {
                "value": risk_assessment.retained_earnings_to_assets,
                "risk_level": _get_ratio_risk_from_detail(ratios_detail, "leverage", "retained_earnings_to_assets")
            }
        },
        "efficiency_ratios": {
            "asset_turnover": {
                "value": risk_assessment.asset_turnover,
                "risk_level": _get_ratio_risk_from_detail(ratios_detail, "efficiency", "sales_to_assets")
            },
            "inventory_turnover": {
                "value": risk_assessment.inventory_turnover,
                "risk_level": None
            },
            "receivables_turnover": {
                "value": risk_assessment.receivables_turnover,
                "risk_level": _get_ratio_risk_from_detail(ratios_detail, "efficiency", "sales_to_receivables")
            },
            "sales_to_working_capital": {
                "value": risk_assessment.sales_to_working_capital,
                "risk_level": _get_ratio_risk_from_detail(ratios_detail, "efficiency", "sales_to_working_capital")
            },
            "creditors_to_sales": {
                "value": risk_assessment.creditors_to_sales,
                "risk_level": _get_ratio_risk_from_detail(ratios_detail, "efficiency", "creditors_to_sales")
            }
        },
        "growth_ratios": {
            "growth_sales_percent": {
                "value": risk_assessment.growth_sales,
                "risk_level": _get_ratio_risk_from_detail(ratios_detail, "growth", "growth_sales")
            },
            "growth_net_profit_percent": {
                "value": risk_assessment.growth_net_profit,
                "risk_level": _get_ratio_risk_from_detail(ratios_detail, "growth", "growth_net_profit")
            },
            "growth_gross_profit_margin_pp": {
                "value": risk_assessment.growth_gross_profit_margin,
                "risk_level": _get_ratio_risk_from_detail(ratios_detail, "growth", "growth_gross_profit_margin")
            },
            "growth_net_profit_margin_pp": {
                "value": risk_assessment.growth_net_profit_margin,
                "risk_level": _get_ratio_risk_from_detail(ratios_detail, "growth", "growth_net_profit_margin")
            }
        },
        "analysis_metadata": {
            "fiscal_year_analyzed": risk_assessment.fiscal_year_used,
            "previous_fiscal_year": risk_assessment.previous_fiscal_year_used,
            "has_growth_data": risk_assessment.previous_fiscal_year_used is not None
        }
    }
    return json.dumps(data, indent=2, default=str)


def _get_z_score_interpretation(z_score: float, risk_level: str) -> str:
    """Get human-readable interpretation of Z-Score."""
    if z_score is None:
        return "Z-Score could not be calculated due to missing data"

    if z_score > 2.9:
        return f"Z-Score of {z_score:.2f} is in the SAFE ZONE (>2.90), indicating low probability of financial distress within the next two years."
    elif z_score > 1.23:
        return f"Z-Score of {z_score:.2f} is in the GREY ZONE (1.23-2.90), indicating moderate risk. Close monitoring recommended."
    else:
        return f"Z-Score of {z_score:.2f} is in the DISTRESS ZONE (<1.23), indicating high probability of financial distress. Caution strongly advised."


def _get_ratio_risk_from_detail(ratios_detail: Dict, category: str, ratio_name: str) -> str:
    """Extract risk level for a specific ratio from the ratios_detail JSON."""
    if not ratios_detail:
        return None
    try:
        return ratios_detail.get(category, {}).get(ratio_name, {}).get("risk_level")
    except:
        return None


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

FINANCIAL ANALYSIS (with Z-Score components and ratio risk levels):
{financial_data}

QUALITATIVE ASSESSMENT:
{qualitative_data}

Please analyze:
1. The overall Z-Score and its risk level (primary indicator)
2. Each Z-Score component's individual risk level to identify specific areas of concern
3. All financial ratios and their risk levels
4. Growth trends if available
5. Qualitative factors and any red flags

Based on this comprehensive analysis, provide your recommendation with specific supporting factors."""

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
        # Fallback recommendation based on Z-Score and key ratios
        z_score = risk_assessment.z_score or 0
        risk_level = risk_assessment.risk_level or "unknown"

        # Build factors list based on available data
        factors = []

        if z_score > 2.9:
            rec_type = "proceed"
            factors.append(f"Z-Score of {z_score:.2f} is in the Safe Zone (>2.90), indicating low probability of financial distress")
            summary_status = "financially healthy"
        elif z_score >= 1.23:
            rec_type = "proceed_with_mitigation"
            factors.append(f"Z-Score of {z_score:.2f} is in the Grey Zone (1.23-2.90), indicating moderate risk")
            factors.append("Close monitoring and additional due diligence recommended")
            summary_status = "showing moderate financial risk"
        else:
            rec_type = "do_not_proceed"
            factors.append(f"Z-Score of {z_score:.2f} is in the Distress Zone (<1.23), indicating high probability of financial distress")
            factors.append("Significant financial concerns require careful evaluation")
            summary_status = "showing signs of financial distress"

        # Add key ratio insights if available
        if risk_assessment.current_ratio:
            if risk_assessment.current_ratio < 0.5:
                factors.append(f"Current Ratio of {risk_assessment.current_ratio:.2f} is inadequate (below 0.5), indicating severe liquidity concerns")
            elif risk_assessment.current_ratio < 1.0:
                factors.append(f"Current Ratio of {risk_assessment.current_ratio:.2f} is below 1.0, indicating potential liquidity issues")
            elif risk_assessment.current_ratio > 1.05:
                factors.append(f"Current Ratio of {risk_assessment.current_ratio:.2f} indicates adequate liquidity")

        if risk_assessment.debt_to_equity:
            if risk_assessment.debt_to_equity > 2.22:
                factors.append(f"Debt-to-Equity ratio of {risk_assessment.debt_to_equity:.2f} is inadequate, indicating high leverage risk")
            elif risk_assessment.debt_to_equity < 0.38:
                factors.append(f"Debt-to-Equity ratio of {risk_assessment.debt_to_equity:.2f} indicates conservative capital structure")

        factors.append("Note: This is an automated fallback recommendation - full AI analysis unavailable")

        return {
            "recommendation_type": rec_type,
            "recommendation_text": f"Recommendation based on Z-Score and financial ratio analysis",
            "supporting_factors": factors,
            "summary": f"The vendor {assessment.vendor_name} has a Z-Score of {z_score:.2f}, which indicates {risk_level} risk level. The company appears to be {summary_status}. A detailed review of all financial ratios and qualitative factors is recommended for a complete assessment."
        }
