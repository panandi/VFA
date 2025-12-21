"""
Financial Calculator for Vendor Financial Assessment.

Implements all financial ratios and Z-Score calculations based on the
Financial Assessment Template specification.
"""

from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum


class CompanyType(str, Enum):
    """Company type for Z-Score calculation."""
    PUBLIC = "public"
    PRIVATE = "private"


class RiskLevel(str, Enum):
    """Risk level classification."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    INADEQUATE = "inadequate"


@dataclass
class RatioBenchmark:
    """Benchmark thresholds for a ratio."""
    inadequate: Optional[Tuple[str, float]] = None  # (operator, value)
    high: Optional[Tuple[str, float, str, float]] = None  # (op1, val1, op2, val2) for range
    medium: Optional[Tuple[str, float, str, float]] = None
    low: Optional[Tuple[str, float]] = None


# =============================================================================
# BENCHMARK DEFINITIONS
# Based on Section 4.1.2.2 - Benchmark used for Ratio calculation
# =============================================================================

RATIO_BENCHMARKS = {
    # Working Capital Ratio: (Current Assets - Current Liabilities) / Total Assets
    "working_capital_ratio": {
        "inadequate": lambda x: x is not None and x < 0.06,
        "high": lambda x: x is not None and (x <= 0 or (x > 0.06 and x <= 0.4)),
        "medium": lambda x: x is not None and x > 0 and x <= 0.4,
        "low": lambda x: x is not None and x > 0.4,
    },
    # Current Ratio: Current Assets / Current Liabilities
    "current_ratio": {
        "inadequate": lambda x: x is not None and x < 0.5,
        "high": lambda x: x is not None and x >= 0.5 and x <= 0.95,
        "medium": lambda x: x is not None and x > 0.95 and x <= 1.05,
        "low": lambda x: x is not None and x > 1.05,
    },
    # Quick Ratio: (Current Assets - Inventory) / Current Liabilities
    "quick_ratio": {
        "inadequate": lambda x: x is not None and x < 0.3,
        "high": lambda x: x is not None and x >= 0.3 and x <= 0.75,
        "medium": lambda x: x is not None and x > 0.75 and x <= 0.95,
        "low": lambda x: x is not None and x > 0.95,
    },
    # Return on Total Assets (ROA): EBIT / Total Assets (as percentage)
    "roa": {
        "inadequate": lambda x: x is not None and x < 2,
        "high": lambda x: x is not None and x >= 2 and x <= 4,
        "medium": lambda x: x is not None and x > 4 and x <= 6,
        "low": lambda x: x is not None and x > 6,
    },
    # Return on Equity (ROE): Net Profit / Equity (as percentage)
    "roe": {
        "inadequate": lambda x: x is not None and x < 5,
        "high": lambda x: x is not None and x >= 5 and x <= 9,
        "medium": lambda x: x is not None and x > 9 and x <= 11,
        "low": lambda x: x is not None and x > 11,
    },
    # Growth in Gross Profit Margin (as percentage points)
    "growth_gross_profit_margin": {
        "inadequate": lambda x: x is not None and x < 0,
        "high": lambda x: x is not None and x >= 0 and x <= 1,
        "medium": lambda x: x is not None and x > 1 and x <= 5,
        "low": lambda x: x is not None and x > 5,
    },
    # Growth in Net Profit Margin (as percentage points)
    "growth_net_profit_margin": {
        "inadequate": lambda x: x is not None and x < -10,
        "high": lambda x: x is not None and x >= -10 and x <= 3,
        "medium": lambda x: x is not None and x > 3 and x <= 3,  # Appears same in spec
        "low": lambda x: x is not None and x > 3,
    },
    # Debt to Assets Ratio: Total Liabilities / Total Assets
    "debt_to_assets": {
        "inadequate": lambda x: x is not None and x > 1.5,
        "high": lambda x: x is not None and x >= 1.2 and x <= 1.5,
        "medium": lambda x: x is not None and x < 1.2 and x > 0.5,
        "low": lambda x: x is not None and x <= 0.5,
    },
    # Debt to Equity Ratio: Total Liabilities / Equity
    "debt_to_equity": {
        "inadequate": lambda x: x is not None and (x > 2.22 or x < 0),
        "high": lambda x: x is not None and x >= 0.83 and x <= 2.22,
        "medium": lambda x: x is not None and x >= 0.38 and x < 0.83,
        "low": lambda x: x is not None and x >= 0 and x < 0.38,
    },
    # Retained Earnings to Total Assets
    "retained_earnings_to_assets": {
        "inadequate": lambda x: x is not None and x < 0,
        "high": lambda x: x is not None and x >= 0 and x <= 1,
        "medium": lambda x: x is not None and x > 1 and x <= 5,
        "low": lambda x: x is not None and x > 5,
    },
    # Sales to Total Assets Ratio (Asset Turnover)
    "sales_to_assets": {
        "inadequate": lambda x: x is not None and x < 0,
        "high": lambda x: x is not None and x >= 0 and x <= 1,
        "medium": lambda x: x is not None and x > 1 and x <= 5,
        "low": lambda x: x is not None and x > 5,
    },
    # Sales to Accounts Receivable Ratio
    "sales_to_receivables": {
        "inadequate": lambda x: x is not None and x < 0,
        "high": lambda x: x is not None and x >= 0 and x <= 1,
        "medium": lambda x: x is not None and x > 1 and x <= 5,
        "low": lambda x: x is not None and x > 5,
    },
    # Sales to Working Capital Ratio
    "sales_to_working_capital": {
        "inadequate": lambda x: x is not None and x < 0,
        "high": lambda x: x is not None and x >= 0 and x <= 1,
        "medium": lambda x: x is not None and x > 1 and x <= 5,
        "low": lambda x: x is not None and x > 5,
    },
    # Creditors to Sales Ratio: Trade Payables / Sales
    "creditors_to_sales": {
        "inadequate": lambda x: x is not None and x > 0.4,
        "high": lambda x: x is not None and x >= 0.3 and x <= 0.4,
        "medium": lambda x: x is not None and x < 0.3 and x >= 0.1,
        "low": lambda x: x is not None and x < 0.1,
    },
    # Growth in Sales (as percentage)
    "growth_sales": {
        "inadequate": lambda x: x is not None and x < 0,
        "high": lambda x: x is not None and x >= 0 and x <= 1,
        "medium": lambda x: x is not None and x > 1 and x <= 5,
        "low": lambda x: x is not None and x > 30,
    },
    # Growth in Net Profit/(Loss) (as percentage)
    "growth_net_profit": {
        "inadequate": lambda x: x is not None and x < 0,
        "high": lambda x: x is not None and x >= 0 and x <= 1,
        "medium": lambda x: x is not None and x > 1 and x <= 5,
        "low": lambda x: x is not None and x > 10,
    },
}


# =============================================================================
# Z-SCORE COEFFICIENTS
# Based on Section 4.1.2.3 - Risk of financial distress calculation
# =============================================================================

Z_SCORE_PUBLIC = {
    "x1": 1.200,  # Working Capital / Total Assets
    "x2": 1.400,  # Retained Earnings / Total Assets
    "x3": 3.300,  # EBIT / Total Assets
    "x4": 0.600,  # Market Value of Equity / Total Liabilities (X4a)
    "x5": 1.000,  # Sales / Total Assets
}

Z_SCORE_PRIVATE = {
    "x1": 0.717,  # Working Capital / Total Assets
    "x2": 0.847,  # Retained Earnings / Total Assets
    "x3": 3.107,  # EBIT / Total Assets
    "x4": 0.420,  # Book Value of Equity / Total Liabilities (X4b)
    "x5": 0.998,  # Sales / Total Assets
}

# Z-Score Risk Benchmarks (Overall)
Z_SCORE_BENCHMARKS = {
    "low": 2.900,      # > 2.900 = Low Risk
    "medium": 1.230,   # > 1.230 = Medium Risk
    "high": 0.000,     # > 0.000 = High Risk
}

# Z-Score Component Benchmarks (from Section 4.1.2.4 page 7)
# Used to assess risk level of each independent variable
Z_COMPONENT_BENCHMARKS = {
    # X1: Working Capital / Total Assets
    "x1": {
        "high": lambda x: x is not None and x <= -0.061,
        "medium": lambda x: x is not None and x > -0.061 and x < 0.414,
        "low": lambda x: x is not None and x >= 0.414,
    },
    # X2: Retained Earnings / Total Assets
    "x2": {
        "high": lambda x: x is not None and x <= -0.626,
        "medium": lambda x: x is not None and x > -0.626 and x < 0.355,
        "low": lambda x: x is not None and x >= 0.355,
    },
    # X3: EBIT / Total Assets
    "x3": {
        "high": lambda x: x is not None and x <= -0.318,
        "medium": lambda x: x is not None and x > -0.318 and x < 0.154,
        "low": lambda x: x is not None and x >= 0.154,
    },
    # X4a: Market Value of Equity / Total Liabilities (Public Companies)
    "x4_public": {
        "high": lambda x: x is not None and x <= 0.401,
        "medium": lambda x: x is not None and x > 0.401 and x < 2.477,
        "low": lambda x: x is not None and x >= 2.477,
    },
    # X4b: Book Value of Equity / Total Liabilities (Private Companies)
    "x4_private": {
        "high": lambda x: x is not None and x <= 0.494,
        "medium": lambda x: x is not None and x > 0.494 and x < 2.684,
        "low": lambda x: x is not None and x >= 2.684,
    },
    # X5: Sales / Total Assets
    "x5": {
        "high": lambda x: x is not None and x <= 1.503,
        "medium": lambda x: x is not None and x > 1.503 and x < 1.939,
        "low": lambda x: x is not None and x >= 1.939,
    },
}


class FinancialCalculator:
    """
    Calculator for financial ratios and Z-Score.

    Implements formulas from Section 4.1.2.1 - Formula used for Financial assessment
    """

    def __init__(
        self,
        current_year_data: Any,
        previous_year_data: Any = None,
        company_type: CompanyType = CompanyType.PRIVATE
    ):
        """
        Initialize calculator with financial data.

        Args:
            current_year_data: ExtractedFinancialData for current fiscal year
            previous_year_data: ExtractedFinancialData for previous fiscal year (for growth calculations)
            company_type: PUBLIC or PRIVATE (affects Z-Score calculation)
        """
        self.current = current_year_data
        self.previous = previous_year_data
        self.company_type = company_type

    @staticmethod
    def safe_divide(numerator: Optional[float], denominator: Optional[float]) -> Optional[float]:
        """Safely divide two numbers, returning None if not possible."""
        if numerator is None or denominator is None or denominator == 0:
            return None
        return numerator / denominator

    @staticmethod
    def get_risk_level(ratio_name: str, value: Optional[float]) -> Optional[str]:
        """Get risk level for a ratio based on benchmarks."""
        if value is None or ratio_name not in RATIO_BENCHMARKS:
            return None

        benchmarks = RATIO_BENCHMARKS[ratio_name]

        # Check in order: low (best) -> medium -> high -> inadequate (worst)
        if benchmarks.get("low") and benchmarks["low"](value):
            return RiskLevel.LOW.value
        if benchmarks.get("medium") and benchmarks["medium"](value):
            return RiskLevel.MEDIUM.value
        if benchmarks.get("high") and benchmarks["high"](value):
            return RiskLevel.HIGH.value
        if benchmarks.get("inadequate") and benchmarks["inadequate"](value):
            return RiskLevel.INADEQUATE.value

        return RiskLevel.HIGH.value  # Default to high if no match

    # =========================================================================
    # WORKING CAPITAL & LIQUIDITY RATIOS
    # =========================================================================

    def calculate_working_capital(self) -> Optional[float]:
        """Working Capital = Current Assets - Current Liabilities"""
        if self.current.working_capital is not None:
            return self.current.working_capital

        current_assets = self.current.current_assets
        current_liabilities = self.current.current_liabilities

        if current_assets is not None and current_liabilities is not None:
            return current_assets - current_liabilities
        return None

    def calculate_working_capital_ratio(self) -> Optional[float]:
        """
        Working Capital Ratio = (Current Assets - Current Liabilities) / Total Assets
        Formula from spec: X1 = (Current Assets - Current Liabilities) / Total Assets
        """
        working_capital = self.calculate_working_capital()
        return self.safe_divide(working_capital, self.current.total_assets)

    def calculate_current_ratio(self) -> Optional[float]:
        """
        Current Ratio = Current Assets / Current Liabilities
        """
        return self.safe_divide(
            self.current.current_assets,
            self.current.current_liabilities
        )

    def calculate_quick_ratio(self) -> Optional[float]:
        """
        Quick Ratio = (Current Assets - Inventory) / Current Liabilities
        """
        if self.current.current_assets is None:
            return None

        inventory = self.current.inventory or 0
        quick_assets = self.current.current_assets - inventory

        return self.safe_divide(quick_assets, self.current.current_liabilities)

    def calculate_cash_ratio(self) -> Optional[float]:
        """
        Cash Ratio = Cash and Equivalents / Current Liabilities
        """
        return self.safe_divide(
            self.current.cash_and_equivalents,
            self.current.current_liabilities
        )

    # =========================================================================
    # PROFITABILITY RATIOS
    # =========================================================================

    def calculate_gross_profit(self) -> Optional[float]:
        """Gross Profit = Revenue - Cost of Sales"""
        if self.current.gross_profit is not None:
            return self.current.gross_profit

        if self.current.revenue is not None and self.current.cost_of_sales is not None:
            return self.current.revenue - self.current.cost_of_sales
        return None

    def calculate_gross_margin(self) -> Optional[float]:
        """Gross Margin = Gross Profit / Revenue (as decimal)"""
        gross_profit = self.calculate_gross_profit()
        return self.safe_divide(gross_profit, self.current.revenue)

    def calculate_net_margin(self) -> Optional[float]:
        """Net Profit Margin = Net Profit / Revenue (as decimal)"""
        return self.safe_divide(self.current.net_income, self.current.revenue)

    def calculate_roa(self) -> Optional[float]:
        """
        Return on Total Assets = EBIT / Total Assets
        Note: Spec uses EBIT, not Net Income
        """
        ebit = self.current.ebit or self.current.operating_income

        # If EBIT not available, estimate from net income + interest
        if ebit is None and self.current.net_income is not None:
            interest = self.current.interest_expense or 0
            ebit = self.current.net_income + interest

        return self.safe_divide(ebit, self.current.total_assets)

    def calculate_roe(self) -> Optional[float]:
        """
        Return on Equity = Net Profit/(Loss) / Equity
        """
        return self.safe_divide(self.current.net_income, self.current.total_equity)

    # =========================================================================
    # LEVERAGE RATIOS
    # =========================================================================

    def calculate_debt_to_assets(self) -> Optional[float]:
        """
        Debt to Assets Ratio = Total Liabilities / Total Assets
        """
        return self.safe_divide(
            self.current.total_liabilities,
            self.current.total_assets
        )

    def calculate_debt_to_equity(self) -> Optional[float]:
        """
        Debt to Equity Ratio = Total Liabilities / Equity
        """
        return self.safe_divide(
            self.current.total_liabilities,
            self.current.total_equity
        )

    def calculate_interest_coverage(self) -> Optional[float]:
        """
        Interest Coverage = EBIT / Interest Expense
        """
        ebit = self.current.ebit or self.current.operating_income
        return self.safe_divide(ebit, self.current.interest_expense)

    def calculate_retained_earnings_to_assets(self) -> Optional[float]:
        """
        Retained Earnings to Total Assets = Retained Earnings / Total Assets
        """
        return self.safe_divide(
            self.current.retained_earnings,
            self.current.total_assets
        )

    # =========================================================================
    # EFFICIENCY/ACTIVITY RATIOS
    # =========================================================================

    def calculate_sales_to_assets(self) -> Optional[float]:
        """
        Sales to Total Assets Ratio = Sales/Revenue / Total Assets
        """
        return self.safe_divide(self.current.revenue, self.current.total_assets)

    def calculate_sales_to_receivables(self) -> Optional[float]:
        """
        Sales to Accounts Receivable Ratio = Sales/Revenue / Accounts Receivable
        """
        return self.safe_divide(
            self.current.revenue,
            self.current.accounts_receivable
        )

    def calculate_sales_to_working_capital(self) -> Optional[float]:
        """
        Sales to Working Capital Ratio = Sales/Revenue / (Current Assets - Current Liabilities)
        """
        working_capital = self.calculate_working_capital()
        return self.safe_divide(self.current.revenue, working_capital)

    def calculate_creditors_to_sales(self) -> Optional[float]:
        """
        Creditors to Sales Ratio = Creditor/Trade Payables / Sales/Revenue
        """
        return self.safe_divide(
            self.current.accounts_payable,
            self.current.revenue
        )

    def calculate_inventory_turnover(self) -> Optional[float]:
        """
        Inventory Turnover = Cost of Sales / Inventory
        """
        return self.safe_divide(self.current.cost_of_sales, self.current.inventory)

    # =========================================================================
    # GROWTH RATIOS (Require previous year data)
    # =========================================================================

    def calculate_growth_sales(self) -> Optional[float]:
        """
        Growth in Sales = (Sales of current FY - Sales of previous FY) / Sales of previous FY
        Returns as percentage (e.g., 10 for 10%)
        """
        if self.previous is None:
            return None

        current_sales = self.current.revenue
        previous_sales = self.previous.revenue

        if current_sales is None or previous_sales is None or previous_sales == 0:
            return None

        return ((current_sales - previous_sales) / previous_sales) * 100

    def calculate_growth_net_profit(self) -> Optional[float]:
        """
        Growth in Net Profit/(Loss)

        If Net Profit/(Loss) is > 0:
            (Net Profit of current FY - Net Profit of previous FY) / Net Profit of previous FY

        If Net Profit/(Loss) is < 0:
            -(Net Profit of current FY - Net Profit of previous FY) / Net Profit of previous FY

        Returns as percentage
        """
        if self.previous is None:
            return None

        current_profit = self.current.net_income
        previous_profit = self.previous.net_income

        if current_profit is None or previous_profit is None or previous_profit == 0:
            return None

        change = current_profit - previous_profit

        # Apply sign adjustment based on whether we're in profit or loss
        if current_profit < 0:
            change = -change

        return (change / abs(previous_profit)) * 100

    def calculate_growth_gross_profit_margin(self) -> Optional[float]:
        """
        Growth in Gross Profit Margin = Gross Margin of current FY - Gross Margin of previous FY

        Where Gross Margin = (Sales/Revenue - Cost of Sales) / Sales/Revenue

        Returns as percentage points
        """
        if self.previous is None:
            return None

        # Current year gross margin
        current_gross_profit = self.calculate_gross_profit()
        current_margin = self.safe_divide(current_gross_profit, self.current.revenue)

        # Previous year gross margin
        prev_gross_profit = self.previous.gross_profit
        if prev_gross_profit is None and self.previous.revenue and self.previous.cost_of_sales:
            prev_gross_profit = self.previous.revenue - self.previous.cost_of_sales
        prev_margin = self.safe_divide(prev_gross_profit, self.previous.revenue)

        if current_margin is None or prev_margin is None:
            return None

        return (current_margin - prev_margin) * 100

    def calculate_growth_net_profit_margin(self) -> Optional[float]:
        """
        Growth in Net Profit Margin = Net Margin of current FY - Net Margin of previous FY

        Where Net Margin = Net Profit/(Loss) / Sales/Revenue

        Returns as percentage points
        """
        if self.previous is None:
            return None

        current_margin = self.safe_divide(self.current.net_income, self.current.revenue)
        prev_margin = self.safe_divide(self.previous.net_income, self.previous.revenue)

        if current_margin is None or prev_margin is None:
            return None

        return (current_margin - prev_margin) * 100

    # =========================================================================
    # Z-SCORE CALCULATION
    # Based on Section 4.1.2.3 - Risk of financial distress calculation
    # =========================================================================

    def calculate_z_score_components(self) -> Dict[str, Optional[float]]:
        """
        Calculate Z-Score independent variables.

        X1 = Working Capital / Total Assets = (Current Assets - Current Liabilities) / Total Assets
        X2 = Retained Earnings / Total Assets
        X3 = EBIT / Total Assets
        X4a = Market Value of Equity / Total Liabilities (for public companies)
        X4b = Book Value of Equity / Total Liabilities (for private companies)
        X5 = Sales/Revenue / Total Assets

        Note: This method includes robust fallback calculations when primary
        fields are missing.
        """
        total_assets = self.current.total_assets
        total_liabilities = self.current.total_liabilities

        # X1: Working Capital / Total Assets
        # Primary: (Current Assets - Current Liabilities) / Total Assets
        # Fallback: Use stored working_capital if available
        x1 = self.calculate_working_capital_ratio()
        if x1 is None and self.current.working_capital is not None:
            x1 = self.safe_divide(self.current.working_capital, total_assets)

        # X2: Retained Earnings / Total Assets
        # Primary: Retained Earnings / Total Assets
        # Fallback: (Total Equity - Share Capital) / Total Assets (approximation)
        x2 = self.calculate_retained_earnings_to_assets()
        if x2 is None and total_assets:
            # Try to estimate from equity components
            total_equity = self.current.total_equity
            if total_equity is None and total_assets and total_liabilities:
                total_equity = total_assets - total_liabilities
            # If we still don't have retained earnings, use a portion of equity
            # This is a rough approximation - in practice, retained earnings is
            # typically 50-80% of total equity for established companies
            if total_equity is not None and self.current.retained_earnings is None:
                # Don't estimate - leave as None to indicate missing data
                pass

        # X3: EBIT / Total Assets
        # Primary: EBIT / Total Assets
        # Fallback 1: Operating Income / Total Assets
        # Fallback 2: (Net Income + Interest Expense) / Total Assets
        x3 = self.calculate_roa()

        # X4: Equity / Total Liabilities
        # Primary: Total Equity / Total Liabilities
        # Fallback: (Total Assets - Total Liabilities) / Total Liabilities
        total_equity = self.current.total_equity
        if total_equity is None and total_assets and total_liabilities:
            total_equity = total_assets - total_liabilities
        x4 = self.safe_divide(total_equity, total_liabilities)

        # X5: Sales / Total Assets
        # Primary: Revenue / Total Assets
        x5 = self.calculate_sales_to_assets()

        return {"x1": x1, "x2": x2, "x3": x3, "x4": x4, "x5": x5}

    def calculate_z_score(self) -> Dict[str, Any]:
        """
        Calculate Altman Z-Score.

        For Public Company:
            Z-Score = 1.200*X1 + 1.400*X2 + 3.300*X3 + 0.600*X4a + 1.000*X5

        For Private Company:
            Z-Score = 0.717*X1 + 0.847*X2 + 3.107*X3 + 0.420*X4b + 0.998*X5

        Benchmarks:
            - Low Risk: Z > 2.900
            - Medium Risk: Z > 1.230
            - High Risk: Z > 0.000
        """
        components = self.calculate_z_score_components()

        # Get coefficients based on company type
        if self.company_type == CompanyType.PUBLIC:
            coefficients = Z_SCORE_PUBLIC
        else:
            coefficients = Z_SCORE_PRIVATE

        # Check if we have minimum required data
        total_assets = self.current.total_assets
        if not total_assets or total_assets == 0:
            return {
                "z_score": None,
                "risk_level": None,
                "company_type": self.company_type.value,
                "components": components,
                "weighted_components": None,
                "error": "Total assets required for Z-Score calculation"
            }

        # Use 0 for missing components
        x1 = components["x1"] or 0
        x2 = components["x2"] or 0
        x3 = components["x3"] or 0
        x4 = components["x4"] or 0
        x5 = components["x5"] or 0

        # Count available components
        available = sum(1 for v in components.values() if v is not None)

        # Calculate Z-Score
        z_score = (
            coefficients["x1"] * x1 +
            coefficients["x2"] * x2 +
            coefficients["x3"] * x3 +
            coefficients["x4"] * x4 +
            coefficients["x5"] * x5
        )

        # Determine risk level
        if z_score > Z_SCORE_BENCHMARKS["low"]:
            risk_level = RiskLevel.LOW.value
        elif z_score > Z_SCORE_BENCHMARKS["medium"]:
            risk_level = RiskLevel.MEDIUM.value
        else:
            risk_level = RiskLevel.HIGH.value

        weighted = {
            "x1_weighted": round(coefficients["x1"] * x1, 4),
            "x2_weighted": round(coefficients["x2"] * x2, 4),
            "x3_weighted": round(coefficients["x3"] * x3, 4),
            "x4_weighted": round(coefficients["x4"] * x4, 4),
            "x5_weighted": round(coefficients["x5"] * x5, 4),
        }

        # Get risk level for each component
        x4_benchmark_key = "x4_public" if self.company_type == CompanyType.PUBLIC else "x4_private"
        component_risks = {
            "x1_risk": self._get_component_risk("x1", components["x1"]),
            "x2_risk": self._get_component_risk("x2", components["x2"]),
            "x3_risk": self._get_component_risk("x3", components["x3"]),
            "x4_risk": self._get_component_risk(x4_benchmark_key, components["x4"]),
            "x5_risk": self._get_component_risk("x5", components["x5"]),
        }

        return {
            "z_score": round(z_score, 3),
            "risk_level": risk_level,
            "company_type": self.company_type.value,
            "components": {k: round(v, 4) if v else None for k, v in components.items()},
            "component_risks": component_risks,
            "weighted_components": weighted,
            "components_available": available,
            "is_estimated": available < 5
        }

    def _get_component_risk(self, component: str, value: Optional[float]) -> Optional[str]:
        """Get risk level for a Z-Score component."""
        if value is None or component not in Z_COMPONENT_BENCHMARKS:
            return None

        benchmarks = Z_COMPONENT_BENCHMARKS[component]

        if benchmarks["low"](value):
            return RiskLevel.LOW.value
        if benchmarks["medium"](value):
            return RiskLevel.MEDIUM.value
        if benchmarks["high"](value):
            return RiskLevel.HIGH.value

        return RiskLevel.HIGH.value

    # =========================================================================
    # COMPREHENSIVE CALCULATIONS
    # =========================================================================

    def calculate_all_ratios(self) -> Dict[str, Any]:
        """
        Calculate all financial ratios with risk levels.

        Returns dictionary with all ratios organized by category.
        """
        # Liquidity Ratios
        working_capital_ratio = self.calculate_working_capital_ratio()
        current_ratio = self.calculate_current_ratio()
        quick_ratio = self.calculate_quick_ratio()
        cash_ratio = self.calculate_cash_ratio()

        # Profitability Ratios (as percentages)
        gross_margin = self.calculate_gross_margin()
        gross_margin_pct = gross_margin * 100 if gross_margin else None

        net_margin = self.calculate_net_margin()
        net_margin_pct = net_margin * 100 if net_margin else None

        roa = self.calculate_roa()
        roa_pct = roa * 100 if roa else None

        roe = self.calculate_roe()
        roe_pct = roe * 100 if roe else None

        # Leverage Ratios
        debt_to_assets = self.calculate_debt_to_assets()
        debt_to_equity = self.calculate_debt_to_equity()
        interest_coverage = self.calculate_interest_coverage()
        retained_earnings_to_assets = self.calculate_retained_earnings_to_assets()

        # Efficiency Ratios
        sales_to_assets = self.calculate_sales_to_assets()
        sales_to_receivables = self.calculate_sales_to_receivables()
        sales_to_working_capital = self.calculate_sales_to_working_capital()
        creditors_to_sales = self.calculate_creditors_to_sales()
        inventory_turnover = self.calculate_inventory_turnover()

        # Growth Ratios (as percentages)
        growth_sales = self.calculate_growth_sales()
        growth_net_profit = self.calculate_growth_net_profit()
        growth_gross_profit_margin = self.calculate_growth_gross_profit_margin()
        growth_net_profit_margin = self.calculate_growth_net_profit_margin()

        return {
            "liquidity": {
                "working_capital_ratio": {
                    "value": round(working_capital_ratio, 4) if working_capital_ratio else None,
                    "risk_level": self.get_risk_level("working_capital_ratio", working_capital_ratio),
                    "formula": "(Current Assets - Current Liabilities) / Total Assets"
                },
                "current_ratio": {
                    "value": round(current_ratio, 4) if current_ratio else None,
                    "risk_level": self.get_risk_level("current_ratio", current_ratio),
                    "formula": "Current Assets / Current Liabilities"
                },
                "quick_ratio": {
                    "value": round(quick_ratio, 4) if quick_ratio else None,
                    "risk_level": self.get_risk_level("quick_ratio", quick_ratio),
                    "formula": "(Current Assets - Inventory) / Current Liabilities"
                },
                "cash_ratio": {
                    "value": round(cash_ratio, 4) if cash_ratio else None,
                    "risk_level": None,  # No benchmark provided
                    "formula": "Cash and Equivalents / Current Liabilities"
                },
            },
            "profitability": {
                "gross_margin": {
                    "value": round(gross_margin_pct, 2) if gross_margin_pct else None,
                    "risk_level": None,
                    "formula": "Gross Profit / Revenue (%)"
                },
                "net_margin": {
                    "value": round(net_margin_pct, 2) if net_margin_pct else None,
                    "risk_level": None,
                    "formula": "Net Profit / Revenue (%)"
                },
                "roa": {
                    "value": round(roa_pct, 2) if roa_pct else None,
                    "risk_level": self.get_risk_level("roa", roa_pct),
                    "formula": "EBIT / Total Assets (%)"
                },
                "roe": {
                    "value": round(roe_pct, 2) if roe_pct else None,
                    "risk_level": self.get_risk_level("roe", roe_pct),
                    "formula": "Net Profit / Equity (%)"
                },
            },
            "leverage": {
                "debt_to_assets": {
                    "value": round(debt_to_assets, 4) if debt_to_assets else None,
                    "risk_level": self.get_risk_level("debt_to_assets", debt_to_assets),
                    "formula": "Total Liabilities / Total Assets"
                },
                "debt_to_equity": {
                    "value": round(debt_to_equity, 4) if debt_to_equity else None,
                    "risk_level": self.get_risk_level("debt_to_equity", debt_to_equity),
                    "formula": "Total Liabilities / Equity"
                },
                "interest_coverage": {
                    "value": round(interest_coverage, 2) if interest_coverage else None,
                    "risk_level": None,
                    "formula": "EBIT / Interest Expense"
                },
                "retained_earnings_to_assets": {
                    "value": round(retained_earnings_to_assets, 4) if retained_earnings_to_assets else None,
                    "risk_level": self.get_risk_level("retained_earnings_to_assets", retained_earnings_to_assets),
                    "formula": "Retained Earnings / Total Assets"
                },
            },
            "efficiency": {
                "sales_to_assets": {
                    "value": round(sales_to_assets, 4) if sales_to_assets else None,
                    "risk_level": self.get_risk_level("sales_to_assets", sales_to_assets),
                    "formula": "Sales/Revenue / Total Assets"
                },
                "sales_to_receivables": {
                    "value": round(sales_to_receivables, 2) if sales_to_receivables else None,
                    "risk_level": self.get_risk_level("sales_to_receivables", sales_to_receivables),
                    "formula": "Sales/Revenue / Accounts Receivable"
                },
                "sales_to_working_capital": {
                    "value": round(sales_to_working_capital, 2) if sales_to_working_capital else None,
                    "risk_level": self.get_risk_level("sales_to_working_capital", sales_to_working_capital),
                    "formula": "Sales/Revenue / Working Capital"
                },
                "creditors_to_sales": {
                    "value": round(creditors_to_sales, 4) if creditors_to_sales else None,
                    "risk_level": self.get_risk_level("creditors_to_sales", creditors_to_sales),
                    "formula": "Trade Payables / Sales/Revenue"
                },
                "inventory_turnover": {
                    "value": round(inventory_turnover, 2) if inventory_turnover else None,
                    "risk_level": None,
                    "formula": "Cost of Sales / Inventory"
                },
            },
            "growth": {
                "growth_sales": {
                    "value": round(growth_sales, 2) if growth_sales else None,
                    "risk_level": self.get_risk_level("growth_sales", growth_sales),
                    "formula": "(Current FY Sales - Previous FY Sales) / Previous FY Sales (%)"
                },
                "growth_net_profit": {
                    "value": round(growth_net_profit, 2) if growth_net_profit else None,
                    "risk_level": self.get_risk_level("growth_net_profit", growth_net_profit),
                    "formula": "Net Profit Growth (%)"
                },
                "growth_gross_profit_margin": {
                    "value": round(growth_gross_profit_margin, 2) if growth_gross_profit_margin else None,
                    "risk_level": self.get_risk_level("growth_gross_profit_margin", growth_gross_profit_margin),
                    "formula": "Current FY Gross Margin - Previous FY Gross Margin (pp)"
                },
                "growth_net_profit_margin": {
                    "value": round(growth_net_profit_margin, 2) if growth_net_profit_margin else None,
                    "risk_level": self.get_risk_level("growth_net_profit_margin", growth_net_profit_margin),
                    "formula": "Current FY Net Margin - Previous FY Net Margin (pp)"
                },
            },
        }

    def calculate_full_assessment(self) -> Dict[str, Any]:
        """
        Calculate complete financial assessment including all ratios and Z-Score.
        """
        ratios = self.calculate_all_ratios()
        z_score = self.calculate_z_score()

        # Count risk levels across all ratios
        risk_counts = {"low": 0, "medium": 0, "high": 0, "inadequate": 0}
        total_ratios = 0

        for category in ratios.values():
            for ratio_data in category.values():
                risk = ratio_data.get("risk_level")
                if risk:
                    total_ratios += 1
                    if risk in risk_counts:
                        risk_counts[risk] += 1

        # Determine overall risk level based on Z-Score and ratio distribution
        overall_risk = z_score.get("risk_level", "high")

        # Adjust if many ratios are inadequate
        if risk_counts["inadequate"] >= 3:
            overall_risk = "inadequate"
        elif risk_counts["high"] + risk_counts["inadequate"] > risk_counts["low"] + risk_counts["medium"]:
            if overall_risk == "low":
                overall_risk = "medium"

        return {
            "z_score": z_score,
            "ratios": ratios,
            "summary": {
                "overall_risk_level": overall_risk,
                "risk_distribution": risk_counts,
                "total_ratios_calculated": total_ratios,
                "company_type": self.company_type.value,
                "has_previous_year_data": self.previous is not None,
            }
        }
