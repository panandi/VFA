import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAssessment } from '../../context/AssessmentContext';
import { api } from '../../services/api';
import toast from 'react-hot-toast';

export function Step3Ratios() {
  const { assessment, refreshAssessment } = useAssessment();
  const navigate = useNavigate();
  const [isCalculating, setIsCalculating] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);

  useEffect(() => {
    // Auto-calculate if not already done
    if (assessment && !assessment.risk_assessment) {
      handleCalculate();
    }
  }, [assessment?.id]);

  if (!assessment) return null;

  const handleCalculate = async () => {
    setIsCalculating(true);
    try {
      await api.calculateRatios(assessment.id);
      refreshAssessment();
      toast.success('Ratios calculated successfully');
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to calculate ratios');
    } finally {
      setIsCalculating(false);
    }
  };

  const handleContinue = async () => {
    if (!assessment.risk_assessment) {
      toast.error('Please calculate ratios first');
      return;
    }

    setIsGenerating(true);
    try {
      await api.generateRecommendation(assessment.id);
      refreshAssessment();
      navigate(`/assessment/${assessment.id}/step4`);
    } catch (error) {
      toast.error('Failed to generate recommendation');
    } finally {
      setIsGenerating(false);
    }
  };

  const risk = assessment.risk_assessment;

  const getRiskColor = (level: string | undefined) => {
    switch (level) {
      case 'low':
        return 'text-green-600';
      case 'medium':
        return 'text-yellow-600';
      case 'high':
        return 'text-red-600';
      default:
        return 'text-gray-600';
    }
  };

  const getRiskBgColor = (level: string | undefined) => {
    switch (level) {
      case 'low':
        return 'bg-green-50 border-green-200';
      case 'medium':
        return 'bg-yellow-50 border-yellow-200';
      case 'high':
        return 'bg-red-50 border-red-200';
      default:
        return 'bg-gray-50 border-gray-200';
    }
  };

  const formatPercent = (value: number | undefined | null): string => {
    if (value === undefined || value === null) return '-';
    return `${value.toFixed(1)}%`;
  };

  const formatRatio = (value: number | undefined | null): string => {
    if (value === undefined || value === null) return '-';
    return value.toFixed(3);
  };

  // Z-Score weights differ between public and private companies
  const isPublicCompany = risk?.company_type === 'public';
  const weights = isPublicCompany
    ? { x1: 1.200, x2: 1.400, x3: 3.300, x4: 0.600, x5: 1.000 }
    : { x1: 0.717, x2: 0.847, x3: 3.107, x4: 0.420, x5: 0.998 };

  // Z-Score components for the table
  const zScoreComponents = [
    {
      label: 'Working Capital / Total Assets',
      description: 'X1 - Measures liquid assets',
      value: risk?.z_score_x1,
      weight: weights.x1,
    },
    {
      label: 'Retained Earnings / Total Assets',
      description: 'X2 - Measures profitability',
      value: risk?.z_score_x2,
      weight: weights.x2,
    },
    {
      label: 'EBIT / Total Assets',
      description: 'X3 - Measures operating efficiency',
      value: risk?.z_score_x3,
      weight: weights.x3,
    },
    {
      label: isPublicCompany ? 'Market Value of Equity / Total Liabilities' : 'Book Value of Equity / Total Liabilities',
      description: 'X4 - Measures leverage',
      value: risk?.z_score_x4,
      weight: weights.x4,
    },
    {
      label: 'Sales / Total Assets',
      description: 'X5 - Measures asset turnover',
      value: risk?.z_score_x5,
      weight: weights.x5,
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-start">
        <div>
          <h2 className="text-xl font-semibold text-gray-900">Financial Ratios & Risk Assessment</h2>
          <p className="text-gray-500 mt-1">
            Calculated from confirmed financial data - {assessment.vendor_name}
          </p>
        </div>
        {risk && (
          <button
            onClick={handleCalculate}
            disabled={isCalculating}
            className="px-4 py-2 text-singtel-red border border-singtel-red rounded-lg hover:bg-red-50"
          >
            Recalculate
          </button>
        )}
      </div>

      {!risk ? (
        <div className="bg-white border rounded-lg p-12 text-center">
          <p className="text-gray-500 mb-4">Financial ratios have not been calculated yet.</p>
          <button
            onClick={handleCalculate}
            disabled={isCalculating}
            className="px-6 py-2 bg-singtel-red text-white rounded-lg font-medium hover:bg-singtel-darkred disabled:opacity-50"
          >
            {isCalculating ? 'Calculating...' : 'Calculate Ratios'}
          </button>
        </div>
      ) : (
        <>
          {/* Z-Score Card */}
          <div className={`border rounded-lg p-6 ${getRiskBgColor(risk.risk_level)}`}>
            <div className="flex items-center space-x-8">
              {/* Gauge */}
              <div className="relative w-32 h-32">
                <svg className="w-32 h-32 transform -rotate-90" viewBox="0 0 100 100">
                  <circle
                    className="text-gray-200"
                    strokeWidth="10"
                    stroke="currentColor"
                    fill="transparent"
                    r="40"
                    cx="50"
                    cy="50"
                  />
                  <circle
                    className={getRiskColor(risk.risk_level)}
                    strokeWidth="10"
                    strokeLinecap="round"
                    stroke="currentColor"
                    fill="transparent"
                    r="40"
                    cx="50"
                    cy="50"
                    strokeDasharray={`${Math.min((risk.z_score || 0) / 5 * 251, 251)} 251`}
                  />
                </svg>
                <div className="absolute inset-0 flex items-center justify-center">
                  <span className="text-3xl font-bold text-gray-900">
                    {risk.z_score?.toFixed(3) || '-'}
                  </span>
                </div>
              </div>

              {/* Risk Info */}
              <div>
                <h3 className="text-lg font-medium text-gray-700">Risk of Financial Distress (Z-Score)</h3>
                <p className={`text-xl font-bold mt-1 ${getRiskColor(risk.risk_level)}`}>
                  {risk.risk_level === 'low' && 'Low Risk - Company is financially healthy'}
                  {risk.risk_level === 'medium' && 'Medium Risk - Gray zone, monitor closely'}
                  {risk.risk_level === 'high' && 'High Risk - Financial distress likely'}
                </p>
                <div className="flex space-x-6 mt-4 text-sm text-gray-900">
                  <span className="flex items-center">
                    <span className="w-3 h-3 rounded-full bg-green-500 mr-2"></span>
                    &gt; 2.9: Low Risk
                  </span>
                  <span className="flex items-center">
                    <span className="w-3 h-3 rounded-full bg-yellow-500 mr-2"></span>
                    1.23 - 2.9: Medium Risk
                  </span>
                  <span className="flex items-center">
                    <span className="w-3 h-3 rounded-full bg-red-500 mr-2"></span>
                    &lt; 1.23: High Risk
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Z-Score Components */}
          <div className="bg-white border rounded-lg overflow-hidden">
            <div className="px-6 py-4 border-b bg-gray-50">
              <h3 className="font-semibold text-gray-900">Z-Score Components</h3>
            </div>
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-sm font-medium text-gray-700">Component</th>
                  <th className="px-6 py-3 text-right text-sm font-medium text-gray-700">Ratio Value</th>
                  <th className="px-6 py-3 text-right text-sm font-medium text-gray-700">Weight</th>
                  <th className="px-6 py-3 text-right text-sm font-medium text-gray-700">Weighted Value</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {zScoreComponents.map((comp, idx) => (
                  <tr key={idx} className="hover:bg-gray-50">
                    <td className="px-6 py-4">
                      <p className="text-sm font-medium text-gray-900">{comp.label}</p>
                      <p className="text-xs text-gray-500">{comp.description}</p>
                    </td>
                    <td className="px-6 py-4 text-right text-sm text-gray-700">
                      {formatRatio(comp.value)}
                    </td>
                    <td className="px-6 py-4 text-right text-sm text-gray-700">{comp.weight}</td>
                    <td className="px-6 py-4 text-right text-sm font-medium text-gray-900">
                      {comp.value !== undefined && comp.value !== null
                        ? (comp.value * comp.weight).toFixed(3)
                        : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Other Ratios */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Liquidity Ratios */}
            <div className="bg-white border rounded-lg overflow-hidden">
              <div className="px-6 py-4 border-b bg-gray-50">
                <h3 className="font-semibold text-gray-900">Liquidity Ratios</h3>
              </div>
              <div className="p-6 space-y-4">
                <div className="flex justify-between">
                  <span className="text-gray-600">Current Ratio</span>
                  <span className="font-medium text-gray-900">{formatRatio(risk.current_ratio)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Quick Ratio</span>
                  <span className="font-medium text-gray-900">{formatRatio(risk.quick_ratio)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Cash Ratio</span>
                  <span className="font-medium text-gray-900">{formatRatio(risk.cash_ratio)}</span>
                </div>
              </div>
            </div>

            {/* Profitability Ratios */}
            <div className="bg-white border rounded-lg overflow-hidden">
              <div className="px-6 py-4 border-b bg-gray-50">
                <h3 className="font-semibold text-gray-900">Profitability Ratios</h3>
              </div>
              <div className="p-6 space-y-4">
                <div className="flex justify-between">
                  <span className="text-gray-600">ROA</span>
                  <span className="font-medium text-gray-900">{formatPercent(risk.roa)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">ROE</span>
                  <span className="font-medium text-gray-900">{formatPercent(risk.roe)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Gross Margin</span>
                  <span className="font-medium text-gray-900">{formatPercent(risk.gross_margin)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Net Margin</span>
                  <span className="font-medium text-gray-900">{formatPercent(risk.net_margin)}</span>
                </div>
              </div>
            </div>

            {/* Leverage Ratios */}
            <div className="bg-white border rounded-lg overflow-hidden">
              <div className="px-6 py-4 border-b bg-gray-50">
                <h3 className="font-semibold text-gray-900">Leverage Ratios</h3>
              </div>
              <div className="p-6 space-y-4">
                <div className="flex justify-between">
                  <span className="text-gray-600">Debt-to-Equity</span>
                  <span className="font-medium text-gray-900">{formatRatio(risk.debt_to_equity)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Debt-to-Assets</span>
                  <span className="font-medium text-gray-900">{formatRatio(risk.debt_to_assets)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Interest Coverage</span>
                  <span className="font-medium text-gray-900">{formatRatio(risk.interest_coverage)}</span>
                </div>
              </div>
            </div>

            {/* Efficiency Ratios */}
            <div className="bg-white border rounded-lg overflow-hidden">
              <div className="px-6 py-4 border-b bg-gray-50">
                <h3 className="font-semibold text-gray-900">Efficiency Ratios</h3>
              </div>
              <div className="p-6 space-y-4">
                <div className="flex justify-between">
                  <span className="text-gray-600">Asset Turnover</span>
                  <span className="font-medium text-gray-900">{formatRatio(risk.asset_turnover)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Inventory Turnover</span>
                  <span className="font-medium text-gray-900">{formatRatio(risk.inventory_turnover)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Receivables Turnover</span>
                  <span className="font-medium text-gray-900">{formatRatio(risk.receivables_turnover)}</span>
                </div>
              </div>
            </div>
          </div>
        </>
      )}

      {/* Action Buttons */}
      <div className="flex justify-between pt-6 border-t">
        <button
          onClick={() => navigate(`/assessment/${assessment.id}/step2`)}
          className="px-4 py-2 text-gray-600 hover:text-gray-900"
        >
          Back to Financial Data
        </button>
        <button
          onClick={handleContinue}
          disabled={isGenerating || !risk}
          className="px-6 py-2 bg-singtel-red text-white rounded-lg font-medium hover:bg-singtel-darkred disabled:opacity-50"
        >
          {isGenerating ? 'Generating Recommendation...' : 'Generate AI Recommendation'}
        </button>
      </div>
    </div>
  );
}
