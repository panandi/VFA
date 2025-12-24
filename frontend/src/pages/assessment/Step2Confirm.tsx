import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAssessment } from '../../context/AssessmentContext';
import { api } from '../../services/api';
import { ExtractedData } from '../../types';
import toast from 'react-hot-toast';
import { HierarchicalDataView } from '../../components/HierarchicalDataView';
import { AIOrganizedView } from '../../components/AIOrganizedView';

type TabType = 'balance_sheet' | 'profit_loss' | 'cash_flow';
type ViewMode = 'flat' | 'hierarchical' | 'ai_organized';

interface AddYearModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (year: number) => void;
  existingYears: number[];
}

function AddYearModal({ isOpen, onClose, onSubmit, existingYears }: AddYearModalProps) {
  const [year, setYear] = useState(new Date().getFullYear());
  const [error, setError] = useState('');

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (existingYears.includes(year)) {
      setError(`Fiscal year ${year} already exists`);
      return;
    }
    onSubmit(year);
    onClose();
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-96 max-w-full mx-4">
        <h3 className="text-lg font-semibold mb-4">Add New Fiscal Year</h3>
        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Fiscal Year
            </label>
            <input
              type="number"
              value={year}
              onChange={(e) => {
                setYear(parseInt(e.target.value));
                setError('');
              }}
              min={1900}
              max={2100}
              className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-singtel-red"
              autoFocus
            />
            {error && <p className="text-red-500 text-sm mt-1">{error}</p>}
          </div>
          <div className="flex justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-gray-600 hover:text-gray-900"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 bg-singtel-red text-white rounded-lg hover:bg-singtel-darkred"
            >
              Add Year
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export function Step2Confirm() {
  const { assessment, refreshAssessment } = useAssessment();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<TabType>('profit_loss');
  const [viewMode, setViewMode] = useState<ViewMode>('hierarchical'); // Default to hierarchical
  const [isConfirming, setIsConfirming] = useState(false);
  const [editingCell, setEditingCell] = useState<{ id: number; field: string } | null>(null);
  const [showAddYearModal, setShowAddYearModal] = useState(false);
  const [isAddingYear, setIsAddingYear] = useState(false);

  if (!assessment) return null;

  const sortedData = [...assessment.extracted_data].sort((a, b) => b.fiscal_year - a.fiscal_year);
  const existingYears = sortedData.map(d => d.fiscal_year);

  const formatNumber = (value: number | undefined | null): string => {
    if (value === undefined || value === null) return '-';
    return value.toLocaleString();
  };

  const handleCellEdit = async (dataId: number, field: string, value: string, fieldLabel: string) => {
    // Allow empty string to clear the value
    if (value.trim() === '' || value === '-') {
      const loadingToast = toast.loading('Clearing value...');
      try {
        await api.updateFinancialData(assessment.id, dataId, { [field]: null });
        refreshAssessment();
        setEditingCell(null);
        toast.success(`${fieldLabel} cleared`, { id: loadingToast });
      } catch (error) {
        toast.error('Failed to clear value', { id: loadingToast });
      }
      return;
    }

    const numValue = parseFloat(value.replace(/,/g, ''));
    if (isNaN(numValue)) {
      toast.error('Please enter a valid number');
      return;
    }

    const loadingToast = toast.loading('Saving...');
    try {
      await api.updateFinancialData(assessment.id, dataId, { [field]: numValue });
      refreshAssessment();
      setEditingCell(null);
      toast.success(`${fieldLabel} updated`, { id: loadingToast });
    } catch (error) {
      toast.error('Failed to update value', { id: loadingToast });
    }
  };

  const handleAddYear = async (year: number) => {
    setIsAddingYear(true);
    const loadingToast = toast.loading(`Adding fiscal year ${year}...`);
    try {
      await api.createFinancialData(assessment.id, { fiscal_year: year });
      refreshAssessment();
      toast.success(`Fiscal year ${year} added successfully`, { id: loadingToast });
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to add fiscal year', { id: loadingToast });
    } finally {
      setIsAddingYear(false);
    }
  };

  const handleDeleteYear = async (dataId: number, year: number) => {
    if (!confirm(`Are you sure you want to delete fiscal year ${year}? This action cannot be undone.`)) {
      return;
    }

    const loadingToast = toast.loading(`Deleting fiscal year ${year}...`);
    try {
      await api.deleteFinancialData(assessment.id, dataId);
      refreshAssessment();
      toast.success(`Fiscal year ${year} deleted successfully`, { id: loadingToast });
    } catch (error) {
      toast.error('Failed to delete fiscal year', { id: loadingToast });
    }
  };

  const handleConfirm = async () => {
    if (sortedData.length === 0) {
      toast.error('No financial data available to confirm');
      return;
    }

    setIsConfirming(true);
    const loadingToast = toast.loading('Confirming financial data...');
    try {
      await api.confirmFinancialData(assessment.id);
      refreshAssessment();
      toast.success('Financial data confirmed! Proceeding to ratios...', { id: loadingToast });
      navigate(`/assessment/${assessment.id}/step3`);
    } catch (error) {
      toast.error('Failed to confirm data', { id: loadingToast });
    } finally {
      setIsConfirming(false);
    }
  };

  const handleRefresh = () => {
    toast.promise(
      refreshAssessment(),
      {
        loading: 'Refreshing data...',
        success: 'Data refreshed',
        error: 'Failed to refresh data',
      }
    );
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

  const renderCell = (data: ExtractedData, field: string, fieldLabel: string) => {
    const value = data[field as keyof ExtractedData] as number | undefined;
    const confidence = data.confidence_scores?.[field];
    const isLowConfidence = confidence !== undefined && confidence < 0.8;
    const isEditing = editingCell?.id === data.id && editingCell?.field === field;

    if (isEditing) {
      return (
        <input
          type="text"
          defaultValue={value?.toString() || ''}
          className="w-full px-2 py-1 border rounded focus:outline-none focus:ring-2 focus:ring-singtel-red text-right"
          autoFocus
          onBlur={(e) => handleCellEdit(data.id, field, e.target.value, fieldLabel)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              handleCellEdit(data.id, field, (e.target as HTMLInputElement).value, fieldLabel);
            } else if (e.key === 'Escape') {
              setEditingCell(null);
              toast('Edit cancelled', { icon: '✖️' });
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
        title={isLowConfidence ? `Low confidence: ${((confidence || 0) * 100).toFixed(0)}% - Click to edit` : 'Click to edit'}
      >
        {formatNumber(value)}
      </div>
    );
  };

  // Convert tab type to statement type for hierarchical view
  const getStatementType = (tab: TabType): 'balance_sheet' | 'income_statement' | 'cash_flow' => {
    if (tab === 'profit_loss') return 'income_statement';
    return tab as 'balance_sheet' | 'cash_flow';
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-start">
        <div>
          <h2 className="text-xl font-semibold text-gray-900">Confirm Extracted Financial Data</h2>
          <p className="text-gray-500 mt-1">
            {viewMode === 'ai_organized'
              ? 'AI-organized view with standardized financial terminology and proper categorization.'
              : viewMode === 'hierarchical'
              ? 'View all extracted financial data organized by hierarchy. Expand sections to see details.'
              : 'Review and edit extracted values. Click any cell to edit. Highlighted items have low confidence.'
            }
          </p>
        </div>
        <div className="flex items-center gap-2">
          {/* View Mode Toggle */}
          <div className="flex bg-gray-100 rounded-lg p-1">
            <button
              onClick={() => setViewMode('ai_organized')}
              className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors flex items-center gap-1 ${
                viewMode === 'ai_organized'
                  ? 'bg-gradient-to-r from-singtel-red to-red-600 text-white shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
              AI Organized
            </button>
            <button
              onClick={() => setViewMode('hierarchical')}
              className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                viewMode === 'hierarchical'
                  ? 'bg-white text-singtel-red shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              Hierarchical
            </button>
            <button
              onClick={() => setViewMode('flat')}
              className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                viewMode === 'flat'
                  ? 'bg-white text-singtel-red shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              Flat
            </button>
          </div>

          {viewMode === 'flat' && (
            <button
              onClick={() => setShowAddYearModal(true)}
              disabled={isAddingYear}
              className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 font-medium flex items-center gap-2"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              Add Fiscal Year
            </button>
          )}
        </div>
      </div>

      {/* Tabs - Hidden in AI Organized mode */}
      {viewMode !== 'ai_organized' && (
        <div className="flex space-x-2">
          <button
            onClick={() => setActiveTab('balance_sheet')}
            className={`px-6 py-2 rounded-full font-medium transition-colors ${
              activeTab === 'balance_sheet'
                ? 'bg-singtel-red text-white'
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
                ? 'bg-singtel-red text-white'
                : 'text-gray-500 hover:bg-gray-100'
            }`}
          >
            Cash Flow
          </button>
        </div>
      )}

      {/* Data View - AI Organized, Hierarchical, or Flat */}
      {viewMode === 'ai_organized' ? (
        <AIOrganizedView assessmentId={assessment.id} />
      ) : viewMode === 'hierarchical' ? (
        <HierarchicalDataView
          assessmentId={assessment.id}
          activeTab={getStatementType(activeTab)}
        />
      ) : (
        // Flat View (Original)
        sortedData.length === 0 ? (
          <div className="bg-white border rounded-lg p-12 text-center">
            <p className="text-gray-500 mb-4">No financial data available.</p>
            <p className="text-gray-400 text-sm mb-4">
              You can add fiscal years manually or wait for PDF processing to complete.
            </p>
            <div className="flex justify-center gap-4">
              <button
                onClick={() => setShowAddYearModal(true)}
                className="px-4 py-2 bg-singtel-red text-white rounded-lg hover:bg-singtel-darkred"
              >
                Add Fiscal Year
              </button>
              <button
                onClick={handleRefresh}
                className="px-4 py-2 text-singtel-red hover:underline"
              >
                Refresh
              </button>
            </div>
          </div>
        ) : (
          <div className="bg-white border rounded-lg overflow-hidden">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-sm font-medium text-gray-700">Item</th>
                  {sortedData.map((data) => (
                    <th key={data.id} className="px-6 py-3 text-right text-sm font-medium text-gray-700">
                      <div className="flex items-center justify-end gap-2">
                        <span>Dec {data.fiscal_year}</span>
                        <button
                          onClick={() => handleDeleteYear(data.id, data.fiscal_year)}
                          className="text-gray-400 hover:text-red-500 p-1"
                          title={`Delete fiscal year ${data.fiscal_year}`}
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                        </button>
                      </div>
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
                        {renderCell(data, field.key, field.label)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )
      )}

      {/* Legend - Only show in flat view */}
      {viewMode === 'flat' && (
        <div className="flex items-center gap-4 text-sm text-gray-500">
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 bg-yellow-50 border border-yellow-300 rounded"></div>
            <span>Low confidence value - review recommended</span>
          </div>
          <div className="flex items-center gap-2">
            <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
            </svg>
            <span>Click any cell to edit</span>
          </div>
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

      {/* Add Year Modal */}
      <AddYearModal
        isOpen={showAddYearModal}
        onClose={() => setShowAddYearModal(false)}
        onSubmit={handleAddYear}
        existingYears={existingYears}
      />
    </div>
  );
}
