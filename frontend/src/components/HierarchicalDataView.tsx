import { useState, useEffect } from 'react';
import { api } from '../services/api';
import toast from 'react-hot-toast';

interface LineItem {
  line_item: string;
  canonical_name: string | null;
  category: string;
  level: number;
  values: { [year: number]: number };
  statement_type: string;
  confidence: number;
  children: LineItem[];
}

interface HierarchicalDataViewProps {
  assessmentId: number;
  activeTab: 'balance_sheet' | 'income_statement' | 'cash_flow' | 'other';
}

interface TreeNodeProps {
  item: LineItem;
  fiscalYears: number[];
  depth: number;
}

function TreeNode({ item, fiscalYears, depth }: TreeNodeProps) {
  const [isExpanded, setIsExpanded] = useState(depth < 2); // Auto-expand first 2 levels
  const hasChildren = item.children && item.children.length > 0;

  const formatNumber = (value: number | undefined | null): string => {
    if (value === undefined || value === null) return '-';
    // Format with commas and handle negatives
    const formatted = Math.abs(value).toLocaleString('en-US', {
      minimumFractionDigits: 0,
      maximumFractionDigits: 2
    });
    return value < 0 ? `(${formatted})` : formatted;
  };

  const getIndentClass = () => {
    const baseIndent = depth * 20;
    return { paddingLeft: `${baseIndent}px` };
  };

  const getLevelStyle = () => {
    switch (depth) {
      case 0:
        return 'font-bold text-gray-900 bg-gray-100';
      case 1:
        return 'font-semibold text-gray-800 bg-gray-50';
      case 2:
        return 'font-medium text-gray-700';
      default:
        return 'font-normal text-gray-600';
    }
  };

  const getCategoryBadge = () => {
    const categoryColors: { [key: string]: string } = {
      'asset': 'bg-green-100 text-green-800',
      'liability': 'bg-red-100 text-red-800',
      'equity': 'bg-blue-100 text-blue-800',
      'revenue': 'bg-purple-100 text-purple-800',
      'expense': 'bg-orange-100 text-orange-800',
      'cashflow': 'bg-cyan-100 text-cyan-800',
      'unknown': 'bg-gray-100 text-gray-800'
    };

    if (depth === 0 && item.category) {
      return (
        <span className={`ml-2 px-2 py-0.5 text-xs rounded-full ${categoryColors[item.category] || categoryColors['unknown']}`}>
          {item.category}
        </span>
      );
    }
    return null;
  };

  return (
    <>
      <tr className={`hover:bg-blue-50 transition-colors ${getLevelStyle()}`}>
        <td className="px-4 py-2.5 text-sm border-b" style={getIndentClass()}>
          <div className="flex items-center gap-2">
            {hasChildren ? (
              <button
                onClick={() => setIsExpanded(!isExpanded)}
                className="text-gray-500 hover:text-gray-700 focus:outline-none p-0.5 rounded hover:bg-gray-200"
              >
                <svg
                  className={`w-4 h-4 transition-transform duration-200 ${isExpanded ? 'rotate-90' : ''}`}
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </button>
            ) : (
              <div className="w-5"></div>
            )}
            <span className="flex-1">{item.line_item}</span>
            {getCategoryBadge()}
            {item.confidence < 0.8 && (
              <span className="text-xs text-yellow-600 bg-yellow-100 px-2 py-0.5 rounded" title="Low confidence extraction">
                {(item.confidence * 100).toFixed(0)}%
              </span>
            )}
          </div>
        </td>
        {fiscalYears.map((year) => (
          <td key={year} className="px-4 py-2.5 text-sm text-right border-b tabular-nums">
            {formatNumber(item.values[year])}
          </td>
        ))}
      </tr>
      {isExpanded && hasChildren && item.children.map((child, index) => (
        <TreeNode
          key={`${child.canonical_name || child.line_item}-${index}`}
          item={child}
          fiscalYears={fiscalYears}
          depth={depth + 1}
        />
      ))}
    </>
  );
}

export function HierarchicalDataView({ assessmentId, activeTab }: HierarchicalDataViewProps) {
  const [hierarchicalData, setHierarchicalData] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadHierarchicalData();
  }, [assessmentId]);

  const loadHierarchicalData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.getHierarchicalData(assessmentId);
      setHierarchicalData(data);
    } catch (err: any) {
      console.error('Failed to load hierarchical data:', err);
      setError(err.response?.data?.detail || 'Failed to load hierarchical data');
      toast.error('Failed to load hierarchical data');
    } finally {
      setIsLoading(false);
    }
  };

  if (isLoading) {
    return (
      <div className="bg-white border rounded-lg p-12 text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-singtel-red mx-auto mb-4"></div>
        <p className="text-gray-500">Loading extracted data...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white border rounded-lg p-12 text-center">
        <div className="text-red-500 mb-4">
          <svg className="w-12 h-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <p className="text-red-600 mb-4">{error}</p>
        <button
          onClick={loadHierarchicalData}
          className="px-4 py-2 bg-singtel-red text-white rounded-lg hover:bg-singtel-darkred"
        >
          Retry
        </button>
      </div>
    );
  }

  if (!hierarchicalData || !hierarchicalData.statements) {
    return (
      <div className="bg-white border rounded-lg p-12 text-center">
        <div className="text-gray-400 mb-4">
          <svg className="w-12 h-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
        </div>
        <p className="text-gray-500 mb-2">No extracted data available</p>
        <p className="text-gray-400 text-sm">
          Upload a PDF with financial tables to extract data.
        </p>
      </div>
    );
  }

  const fiscalYears = hierarchicalData.fiscal_years || [];
  const statementData = hierarchicalData.statements[activeTab] || [];

  // Get the statement type label
  const getStatementLabel = () => {
    switch (activeTab) {
      case 'balance_sheet':
        return 'Balance Sheet';
      case 'income_statement':
        return 'Income Statement / P&L';
      case 'cash_flow':
        return 'Cash Flow Statement';
      case 'other':
        return 'Other Financial Data';
      default:
        return 'Financial Data';
    }
  };

  if (statementData.length === 0) {
    return (
      <div className="bg-white border rounded-lg p-12 text-center">
        <div className="text-gray-400 mb-4">
          <svg className="w-12 h-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
        </div>
        <p className="text-gray-500 mb-2">No {getStatementLabel()} data found</p>
        <p className="text-gray-400 text-sm">
          The uploaded PDF may not contain {getStatementLabel()} information.
        </p>
      </div>
    );
  }

  // Count total items including children
  const countItems = (items: LineItem[]): number => {
    return items.reduce((count, item) => {
      return count + 1 + (item.children ? countItems(item.children) : 0);
    }, 0);
  };

  const totalItems = countItems(statementData);

  return (
    <div className="bg-white border rounded-lg overflow-hidden shadow-sm">
      {/* Header with stats */}
      <div className="bg-gray-50 border-b px-4 py-3 flex justify-between items-center">
        <div>
          <h3 className="font-semibold text-gray-900">{getStatementLabel()}</h3>
          <p className="text-sm text-gray-500">
            {totalItems} line items in this section | {hierarchicalData.total_line_items || totalItems} total extracted | {fiscalYears.length} fiscal year{fiscalYears.length !== 1 ? 's' : ''}
          </p>
        </div>
        <button
          onClick={loadHierarchicalData}
          className="text-gray-500 hover:text-gray-700 p-2 rounded hover:bg-gray-100"
          title="Refresh data"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
        </button>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-100 border-b-2 border-gray-200 sticky top-0">
            <tr>
              <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700 min-w-[300px]">
                Line Item
              </th>
              {fiscalYears.map((year: number) => (
                <th key={year} className="px-4 py-3 text-right text-sm font-semibold text-gray-700 min-w-[120px]">
                  FY {year}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {statementData.map((item: LineItem, index: number) => (
              <TreeNode
                key={`${item.canonical_name || item.line_item}-${index}`}
                item={item}
                fiscalYears={fiscalYears}
                depth={0}
              />
            ))}
          </tbody>
        </table>
      </div>

      {/* Footer info */}
      <div className="bg-blue-50 border-t border-blue-200 px-4 py-3">
        <div className="flex items-start gap-3 text-sm text-blue-800">
          <svg className="w-5 h-5 flex-shrink-0 mt-0.5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div>
            <p className="font-medium">Extracted from PDF Tables</p>
            <p className="text-blue-700 mt-1">
              Data extracted using Camelot table detection. Click arrows to expand/collapse hierarchical items.
              Items marked with percentage badges have lower extraction confidence and should be reviewed.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
