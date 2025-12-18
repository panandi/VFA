"""
Validation Agent - Agent 3
Validates extracted financial data for consistency and accuracy.
"""

from typing import Dict, Any, List, Optional
from app.models.assessment import ExtractedFinancialData


class ValidationAgent:
    """Agent for validating extracted financial data."""

    def __init__(self, extracted_data: List[ExtractedFinancialData]):
        self.data = extracted_data
        self.issues: List[str] = []
        self.warnings: List[str] = []

    def validate_balance_sheet(self, record: ExtractedFinancialData) -> bool:
        """Validate balance sheet equation: Assets = Liabilities + Equity."""
        if not all([record.total_assets, record.total_liabilities, record.total_equity]):
            self.warnings.append(f"Year {record.fiscal_year}: Missing balance sheet components")
            return True  # Can't validate without all components

        expected = record.total_liabilities + record.total_equity
        actual = record.total_assets
        tolerance = actual * 0.05  # 5% tolerance

        if abs(actual - expected) > tolerance:
            self.issues.append(
                f"Year {record.fiscal_year}: Balance sheet mismatch - "
                f"Assets ({actual:,.0f}) != Liabilities + Equity ({expected:,.0f})"
            )
            return False

        return True

    def validate_profit_calculation(self, record: ExtractedFinancialData) -> bool:
        """Validate profit calculations."""
        valid = True

        # Gross Profit = Revenue - Cost of Sales
        if record.revenue and record.cost_of_sales and record.gross_profit:
            expected_gp = record.revenue - record.cost_of_sales
            tolerance = abs(record.gross_profit * 0.05)

            if abs(record.gross_profit - expected_gp) > tolerance:
                self.warnings.append(
                    f"Year {record.fiscal_year}: Gross profit calculation mismatch"
                )

        return valid

    def validate_current_assets(self, record: ExtractedFinancialData) -> bool:
        """Validate current assets components."""
        if record.current_assets:
            # Sum of known current asset components
            known_components = sum(filter(None, [
                record.cash_and_equivalents,
                record.inventory,
                record.accounts_receivable
            ]))

            if known_components > record.current_assets * 1.1:  # 10% tolerance
                self.warnings.append(
                    f"Year {record.fiscal_year}: Current asset components exceed total"
                )

        return True

    def validate_trends(self) -> bool:
        """Validate year-over-year trends for anomalies."""
        if len(self.data) < 2:
            return True

        sorted_data = sorted(self.data, key=lambda x: x.fiscal_year)

        for i in range(1, len(sorted_data)):
            prev = sorted_data[i - 1]
            curr = sorted_data[i]

            # Check for suspicious changes (>200% increase or >80% decrease)
            if prev.revenue and curr.revenue:
                change = (curr.revenue - prev.revenue) / prev.revenue
                if change > 2.0:
                    self.warnings.append(
                        f"Year {curr.fiscal_year}: Revenue increased by {change*100:.0f}%"
                    )
                elif change < -0.8:
                    self.warnings.append(
                        f"Year {curr.fiscal_year}: Revenue decreased by {abs(change)*100:.0f}%"
                    )

        return True

    def validate_required_fields(self, record: ExtractedFinancialData) -> bool:
        """Check that essential fields are present."""
        required = ["total_assets", "total_liabilities", "revenue"]
        missing = []

        for field in required:
            if getattr(record, field) is None:
                missing.append(field)

        if missing:
            self.issues.append(
                f"Year {record.fiscal_year}: Missing required fields: {', '.join(missing)}"
            )
            return False

        return True

    def validate_all(self) -> Dict[str, Any]:
        """Run all validations and return results."""
        self.issues = []
        self.warnings = []

        for record in self.data:
            self.validate_required_fields(record)
            self.validate_balance_sheet(record)
            self.validate_profit_calculation(record)
            self.validate_current_assets(record)

        self.validate_trends()

        # Calculate accuracy score
        total_checks = len(self.data) * 4 + 1  # 4 checks per record + trend check
        failed_checks = len(self.issues)
        accuracy_score = max(0, (total_checks - failed_checks) / total_checks)

        return {
            "is_valid": len(self.issues) == 0,
            "accuracy_score": round(accuracy_score, 2),
            "issues": self.issues,
            "warnings": self.warnings,
            "records_validated": len(self.data)
        }


def validate_extracted_data(data: List[ExtractedFinancialData]) -> Dict[str, Any]:
    """Run validation on extracted financial data."""
    agent = ValidationAgent(data)
    return agent.validate_all()
