import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAssessment } from '../../context/AssessmentContext';
import { api } from '../../services/api';
import { ExtractedData } from '../../types';
import toast from 'react-hot-toast';

type TabType = 'balance_sheet' | 'profit_loss' | 'cash_flow';

export function Step2Confirm() {
  const { assessment, refreshAssessment } = useAssessment();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<TabType>('profit_loss');
  const [isConfirming, setIsConfirming] = useState(false);
  const [editingCell, setEditingCell] = useState<{ id: number; field: string } | null>(null);

  if (!assessment) return null;

  const sortedData = [...assessment.extracted_data].sort((a, b) => b.fiscal_year - a.fiscal_year);

  const formatNumber = (value: number | undefined | null): string => {
    if (value === undefined || value === null) return '-';
    return value.toLocaleString();
  };

  const handleCellEdit = async (dataId: number, field: string, value: string) => {
    const numValue = parseFloat(value.replace(/,/g, ''));
    if (isNaN(numValue)) {
      toast.error('Please enter a valid number');
      return;
    }

    try {
      await api.updateFinancialData(assessment.id, dataId, { [field]: numValue });
      refreshAssessment();
      setEditingCell(null);
      toast.success('Value updated');
    } catch (error) {
      toast.error('Failed to update value');
    }
  };

  const handleConfirm = async () => {
    if (sortedData.length === 0) {
      toast.error('No financial data available to confirm');
      return;
    }

    setIsConfirming(true);
    try {
      await api.confirmFinancialData(assessment.id);
      refreshAssessment();
      navigate(`/assessment/${assessment.id}/step3`);
    } catch (error) {
      toast.error('Failed to confirm data');
    } finally {
      setIsConfirming(false);
    }
  };

  const balanceSheetFields = [
    { key: 'total_assets', label: 'Total Assets' },
    { key: 'current_assets', label: 'Current Assets' },
    { key: 'non_current_assets', label: 'Non-Current Assets' },
    { key: 'cash_and_equivalents', label: 'Cash & Equivalents' },
    { key: 'inventory', label: 'Inventory' },
    { key: 'accounts_receivable', label: 'Accounts Receivable' },
    { key: 'total_liabilities', label: 'Total Liabilities' },
    { key: 'current_liabilities', label: 'Current Liabilities' },
    { key: 'non_current_liabilities', label: 'Non-Current Liabilities' },
    { key: 'accounts_payable', label: 'Accounts Payable' },
    { key: 'total_equity', label: 'Total Equity' },
    { key: 'retained_earnings', label: 'Retained Earnings' },
    { key: 'working_capital', label: 'Working Capital' },
  ];

  const profitLossFields = [
    { key: 'revenue', label: 'Revenue (Sales)' },
    { key: 'cost_of_sales', label: 'Cost of Sales' },
    { key: 'gross_profit', label: 'Gross Profit' },
    { key: 'operating_expenses', label: 'Operating Expenses' },
    { key: 'operating_income', label: 'Operating Income' },
    { key: 'ebit', label: 'EBIT' },
    { key: 'ebitda', label: 'EBITDA' },
    { key: 'interest_expense', label: 'Interest Expense' },
    { key: 'net_income', label: 'Net Income' },
  ];

  const cashFlowFields = [
    { key: 'operating_cash_flow', label: 'Operating Cash Flow' },
    { key: 'investing_cash_flow', label: 'Investing Cash Flow' },
    { key: 'financing_cash_flow', label: 'Financing Cash Flow' },
    { key: 'net_cash_flow', label: 'Net Cash Flow' },
  ];

  const getActiveFields = () => {
    switch (activeTab) {
      case 'balance_sheet':
        return balanceSheetFields;
      case 'profit_loss':
        return profitLossFields;
      case 'cash_flow':
        return cashFlowFields;
    }
  };

  const renderCell = (data: ExtractedData, field: string) => {
    const value = data[field as keyof ExtractedData] as number | undefined;
    const confidence = data.confidence_scores?.[field];
    const isLowConfidence = confidence !== undefined && confidence < 0.8;
    const isEditing = editingCell?.id === data.id && editingCell?.field === field;

    if (isEditing) {
      return (
        <input
          type="text"
          defaultValue={value?.toString() || ''}
          className="w-full px-2 py-1 border rounded focus:outline-none focus:ring-2 focus:ring-singtel-red"
          autoFocus
          onBlur={(e) => handleCellEdit(data.id, field, e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              handleCellEdit(data.id, field, (e.target as HTMLInputElement).value);
            } else if (e.key === 'Escape') {
              setEditingCell(null);
            }
          }}
        />
      );
    }

    return (
      <div
        className={`cursor-pointer hover:bg-gray-100 px-2 py-1 rounded ${
          isLowConfidence ? 'bg-yellow-50 border border-yellow-300' : ''
        }`}
        onClick={() => setEditingCell({ id: data.id, field })}
        title={isLowConfidence ? `Low confidence: ${((confidence || 0) * 100).toFixed(0)}%` : 'Click to edit'}
      >
        {formatNumber(value)}
      </div>
    );
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-gray-900">Confirm Extracted Financial Data</h2>
        <p className="text-gray-500 mt-1">
          Review extracted values and verify accuracy. Highlighted items require your confirmation.
        </p>
      </div>

      {/* Tabs */}
      <div className="flex space-x-2">
        <button
          onClick={() => setActiveTab('balance_sheet')}
          className={`px-6 py-2 rounded-full font-medium transition-colors ${
            activeTab === 'balance_sheet'
              ? 'bg-gray-200 text-gray-900'
              : 'text-gray-500 hover:bg-gray-100'
          }`}
        >
          Balance Sheet
        </button>
        <button
          onClick={() => setActiveTab('profit_loss')}
          className={`px-6 py-2 rounded-full font-medium transition-colors ${
            activeTab === 'profit_loss'
              ? 'bg-singtel-red text-white'
              : 'text-gray-500 hover:bg-gray-100'
          }`}
        >
          Profit & Loss
        </button>
        <button
          onClick={() => setActiveTab('cash_flow')}
          className={`px-6 py-2 rounded-full font-medium transition-colors ${
            activeTab === 'cash_flow'
              ? 'bg-gray-200 text-gray-900'
              : 'text-gray-500 hover:bg-gray-100'
          }`}
        >
          Cash Flow
        </button>
      </div>

      {/* Data Table */}
      {sortedData.length === 0 ? (
        <div className="bg-white border rounded-lg p-12 text-center">
          <p className="text-gray-500">No financial data extracted yet. Please wait for processing to complete.</p>
          <button
            onClick={refreshAssessment}
            className="mt-4 px-4 py-2 text-singtel-red hover:underline"
          >
            Refresh
          </button>
        </div>
      ) : (
        <div className="bg-white border rounded-lg overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-sm font-medium text-gray-700">Item</th>
                {sortedData.map((data) => (
                  <th key={data.id} className="px-6 py-3 text-right text-sm font-medium text-gray-700">
                    Dec {data.fiscal_year}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {getActiveFields().map((field) => (
                <tr key={field.key} className="hover:bg-gray-50">
                  <td className="px-6 py-4 text-sm text-gray-900 font-medium">{field.label}</td>
                  {sortedData.map((data) => (
                    <td key={data.id} className="px-6 py-4 text-sm text-gray-700 text-right">
                      {renderCell(data, field.key)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex justify-between pt-6 border-t">
        <button
          onClick={() => navigate(`/assessment/${assessment.id}`)}
          className="px-4 py-2 text-gray-600 hover:text-gray-900"
        >
          Back
        </button>
        <button
          onClick={handleConfirm}
          disabled={isConfirming || sortedData.length === 0}
          className="px-6 py-2 bg-singtel-red text-white rounded-lg font-medium hover:bg-singtel-darkred disabled:opacity-50"
        >
          {isConfirming ? 'Confirming...' : 'Confirm & Calculate Ratios'}
        </button>
      </div>
    </div>
  );
}
