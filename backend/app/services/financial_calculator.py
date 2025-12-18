from typing import Dict, Any, Optional
from app.models.assessment import ExtractedFinancialData


class FinancialCalculator:
    """Calculator for financial ratios and Z-Score."""

    # Z-Score weights for private companies (Altman Z-Score Model)
    Z_WEIGHTS = {
        "x1": 0.717,   # Working Capital / Total Assets
        "x2": 0.847,   # Retained Earnings / Total Assets
        "x3": 3.107,   # EBIT / Total Assets
        "x4": 0.420,   # Book Value of Equity / Total Liabilities
        "x5": 0.998,   # Sales / Total Assets
    }

    def __init__(self, financial_data: ExtractedFinancialData):
        """Initialize with extracted financial data."""
        self.data = financial_data

    def safe_divide(self, numerator: Optional[float], denominator: Optional[float]) -> Optional[float]:
        """Safely divide two numbers, returning None if division is not possible."""
        if numerator is None or denominator is None or denominator == 0:
            return None
        return numerator / denominator

    def calculate_z_score(self) -> Dict[str, Any]:
        """
        Calculate Altman Z-Score for private companies.

        Z = 0.717*X1 + 0.847*X2 + 3.107*X3 + 0.420*X4 + 0.998*X5

        Where:
        X1 = Working Capital / Total Assets
        X2 = Retained Earnings / Total Assets
        X3 = EBIT / Total Assets
        X4 = Book Value of Equity / Total Liabilities
        X5 = Sales / Total Assets

        More robust - will calculate with available data and estimate missing values.
        """
        # Get total assets - required for most calculations
        total_assets = self.data.total_assets
        if not total_assets or total_assets == 0:
            return {
                "z_score": None,
                "risk_level": None,
                "components": {"x1": None, "x2": None, "x3": None, "x4": None, "x5": None},
                "error": "Total assets required for Z-Score calculation"
            }

        # Calculate working capital if not provided
        working_capital = self.data.working_capital
        if working_capital is None:
            current_assets = self.data.current_assets or 0
            current_liabilities = self.data.current_liabilities or 0
            if current_assets > 0 or current_liabilities > 0:
                working_capital = current_assets - current_liabilities

        # Get retained earnings - use 0 if not available (conservative estimate)
        retained_earnings = self.data.retained_earnings
        if retained_earnings is None:
            # Try to estimate from equity - this is an approximation
            # Retained Earnings is typically a significant portion of equity for established companies
            if self.data.total_equity:
                retained_earnings = self.data.total_equity * 0.5  # Conservative estimate
            else:
                retained_earnings = 0

        # Get EBIT - use operating_income if ebit not available
        ebit = self.data.ebit
        if ebit is None:
            ebit = self.data.operating_income
        if ebit is None:
            # Try to estimate from net income + interest
            if self.data.net_income is not None:
                interest = self.data.interest_expense or 0
                ebit = self.data.net_income + interest

        # Get total equity - calculate from assets/liabilities if needed
        total_equity = self.data.total_equity
        if total_equity is None and self.data.total_liabilities:
            total_equity = total_assets - self.data.total_liabilities

        # Get total liabilities - calculate from assets/equity if needed
        total_liabilities = self.data.total_liabilities
        if total_liabilities is None and total_equity:
            total_liabilities = total_assets - total_equity

        # Get revenue/sales
        revenue = self.data.revenue

        # Calculate components
        x1 = self.safe_divide(working_capital, total_assets)
        x2 = self.safe_divide(retained_earnings, total_assets)
        x3 = self.safe_divide(ebit, total_assets)
        x4 = self.safe_divide(total_equity, total_liabilities)
        x5 = self.safe_divide(revenue, total_assets)

        # Use 0 for missing components to still provide a Z-score estimate
        x1_calc = x1 if x1 is not None else 0
        x2_calc = x2 if x2 is not None else 0
        x3_calc = x3 if x3 is not None else 0
        x4_calc = x4 if x4 is not None else 0
        x5_calc = x5 if x5 is not None else 0

        # Count how many components we have data for
        components_available = sum(1 for c in [x1, x2, x3, x4, x5] if c is not None)

        # Calculate Z-Score if we have at least 3 key components
        if components_available >= 3:
            z_score = (
                self.Z_WEIGHTS["x1"] * x1_calc +
                self.Z_WEIGHTS["x2"] * x2_calc +
                self.Z_WEIGHTS["x3"] * x3_calc +
                self.Z_WEIGHTS["x4"] * x4_calc +
                self.Z_WEIGHTS["x5"] * x5_calc
            )
        else:
            z_score = None

        # Determine risk level
        if z_score is not None:
            if z_score > 2.9:
                risk_level = "low"
            elif z_score >= 1.23:
                risk_level = "medium"
            else:
                risk_level = "high"
        else:
            risk_level = None

        return {
            "z_score": round(z_score, 3) if z_score is not None else None,
            "risk_level": risk_level,
            "components": {
                "x1": round(x1, 4) if x1 is not None else None,
                "x2": round(x2, 4) if x2 is not None else None,
                "x3": round(x3, 4) if x3 is not None else None,
                "x4": round(x4, 4) if x4 is not None else None,
                "x5": round(x5, 4) if x5 is not None else None,
            },
            "weighted_components": {
                "x1_weighted": round(x1_calc * self.Z_WEIGHTS["x1"], 4),
                "x2_weighted": round(x2_calc * self.Z_WEIGHTS["x2"], 4),
                "x3_weighted": round(x3_calc * self.Z_WEIGHTS["x3"], 4),
                "x4_weighted": round(x4_calc * self.Z_WEIGHTS["x4"], 4),
                "x5_weighted": round(x5_calc * self.Z_WEIGHTS["x5"], 4),
            },
            "components_available": components_available,
            "is_estimated": components_available < 5
        }

    def calculate_liquidity_ratios(self) -> Dict[str, Optional[float]]:
        """Calculate liquidity ratios."""
        # Current Ratio = Current Assets / Current Liabilities
        current_ratio = self.safe_divide(
            self.data.current_assets,
            self.data.current_liabilities
        )

        # Quick Ratio = (Current Assets - Inventory) / Current Liabilities
        quick_assets = None
        if self.data.current_assets is not None:
            inventory = self.data.inventory or 0
            quick_assets = self.data.current_assets - inventory
        quick_ratio = self.safe_divide(quick_assets, self.data.current_liabilities)

        # Cash Ratio = Cash / Current Liabilities
        cash_ratio = self.safe_divide(
            self.data.cash_and_equivalents,
            self.data.current_liabilities
        )

        return {
            "current_ratio": round(current_ratio, 3) if current_ratio else None,
            "quick_ratio": round(quick_ratio, 3) if quick_ratio else None,
            "cash_ratio": round(cash_ratio, 3) if cash_ratio else None,
        }

    def calculate_profitability_ratios(self) -> Dict[str, Optional[float]]:
        """Calculate profitability ratios."""
        # Gross Margin = Gross Profit / Revenue
        gross_profit = self.data.gross_profit
        if gross_profit is None and self.data.revenue and self.data.cost_of_sales:
            gross_profit = self.data.revenue - self.data.cost_of_sales

        gross_margin = self.safe_divide(gross_profit, self.data.revenue)

        # Operating Margin = Operating Income / Revenue
        operating_income = self.data.operating_income or self.data.ebit
        operating_margin = self.safe_divide(operating_income, self.data.revenue)

        # Net Margin = Net Income / Revenue
        net_margin = self.safe_divide(self.data.net_income, self.data.revenue)

        # ROA = Net Income / Total Assets
        roa = self.safe_divide(self.data.net_income, self.data.total_assets)

        # ROE = Net Income / Total Equity
        roe = self.safe_divide(self.data.net_income, self.data.total_equity)

        return {
            "gross_margin": round(gross_margin * 100, 2) if gross_margin else None,
            "operating_margin": round(operating_margin * 100, 2) if operating_margin else None,
            "net_margin": round(net_margin * 100, 2) if net_margin else None,
            "roa": round(roa * 100, 2) if roa else None,
            "roe": round(roe * 100, 2) if roe else None,
        }

    def calculate_leverage_ratios(self) -> Dict[str, Optional[float]]:
        """Calculate leverage ratios."""
        # Debt-to-Equity = Total Liabilities / Total Equity
        debt_to_equity = self.safe_divide(
            self.data.total_liabilities,
            self.data.total_equity
        )

        # Debt-to-Assets = Total Liabilities / Total Assets
        debt_to_assets = self.safe_divide(
            self.data.total_liabilities,
            self.data.total_assets
        )

        # Interest Coverage = EBIT / Interest Expense
        ebit = self.data.ebit or self.data.operating_income
        interest_coverage = self.safe_divide(ebit, self.data.interest_expense)

        return {
            "debt_to_equity": round(debt_to_equity, 3) if debt_to_equity else None,
            "debt_to_assets": round(debt_to_assets, 3) if debt_to_assets else None,
            "interest_coverage": round(interest_coverage, 2) if interest_coverage else None,
        }

    def calculate_efficiency_ratios(self) -> Dict[str, Optional[float]]:
        """Calculate efficiency ratios."""
        # Asset Turnover = Revenue / Total Assets
        asset_turnover = self.safe_divide(self.data.revenue, self.data.total_assets)

        # Inventory Turnover = Cost of Sales / Inventory
        inventory_turnover = self.safe_divide(self.data.cost_of_sales, self.data.inventory)

        # Receivables Turnover = Revenue / Accounts Receivable
        receivables_turnover = self.safe_divide(
            self.data.revenue,
            self.data.accounts_receivable
        )

        return {
            "asset_turnover": round(asset_turnover, 3) if asset_turnover else None,
            "inventory_turnover": round(inventory_turnover, 2) if inventory_turnover else None,
            "receivables_turnover": round(receivables_turnover, 2) if receivables_turnover else None,
        }

    def calculate_all_ratios(self) -> Dict[str, Dict[str, Optional[float]]]:
        """Calculate all financial ratios."""
        return {
            "liquidity": self.calculate_liquidity_ratios(),
            "profitability": self.calculate_profitability_ratios(),
            "leverage": self.calculate_leverage_ratios(),
            "efficiency": self.calculate_efficiency_ratios(),
        }
