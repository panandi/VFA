import { useState, useEffect } from 'react';
import { api } from '../services/api';
import toast from 'react-hot-toast';

interface LineItem {
  line_item: string;
  canonical_name: string;
  category: string;
  level: number;
  values: { [year: number]: number };
  statement_type: string;
  confidence: number;
  children: LineItem[];
}

interface HierarchicalDataViewProps {
  assessmentId: number;
  activeTab: 'balance_sheet' | 'income_statement' | 'cash_flow';
}

interface TreeNodeProps {
  item: LineItem;
  fiscalYears: number[];
  depth: number;
}

function TreeNode({ item, fiscalYears, depth }: TreeNodeProps) {
  const [isExpanded, setIsExpanded] = useState(depth === 0); // Auto-expand top level
  const hasChildren = item.children && item.children.length > 0;

  const formatNumber = (value: number | undefined | null): string => {
    if (value === undefined || value === null) return '-';
    return value.toLocaleString();
  };

  const getIndentClass = () => {
    const baseIndent = depth * 24;
    return { paddingLeft: `${baseIndent}px` };
  };

  const getLevelStyle = () => {
    switch (depth) {
      case 0:
        return 'font-bold text-gray-900 bg-gray-50';
      case 1:
        return 'font-semibold text-gray-800';
      case 2:
        return 'font-normal text-gray-700';
      default:
        return 'font-normal text-gray-600';
    }
  };

  return (
    <>
      <tr className={`hover:bg-gray-50 ${getLevelStyle()}`}>
        <td className="px-6 py-3 text-sm" style={getIndentClass()}>
          <div className="flex items-center gap-2">
            {hasChildren && (
              <button
                onClick={() => setIsExpanded(!isExpanded)}
                className="text-gray-500 hover:text-gray-700 focus:outline-none"
              >
                <svg
                  className={`w-4 h-4 transition-transform ${isExpanded ? 'rotate-90' : ''}`}
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </button>
            )}
            {!hasChildren && <div className="w-4"></div>}
            <span>{item.line_item}</span>
            {item.confidence < 0.8 && (
              <span className="text-xs text-yellow-600 bg-yellow-100 px-2 py-0.5 rounded">
                {(item.confidence * 100).toFixed(0)}%
              </span>
            )}
          </div>
        </td>
        {fiscalYears.map((year) => (
          <td key={year} className="px-6 py-3 text-sm text-right">
            {formatNumber(item.values[year])}
          </td>
        ))}
      </tr>
      {isExpanded && hasChildren && item.children.map((child, index) => (
        <TreeNode
          key={`${child.canonical_name}-${index}`}
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
        <p className="text-gray-500">Loading hierarchical data...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white border rounded-lg p-12 text-center">
        <p className="text-red-500 mb-4">{error}</p>
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
        <p className="text-gray-500 mb-4">No hierarchical data available.</p>
        <p className="text-gray-400 text-sm">
          This feature requires data extracted using Camelot. Upload a financial statement PDF to get started.
        </p>
      </div>
    );
  }

  const fiscalYears = hierarchicalData.fiscal_years || [];
  const statementData = hierarchicalData.statements[activeTab] || [];

  if (statementData.length === 0) {
    return (
      <div className="bg-white border rounded-lg p-12 text-center">
        <p className="text-gray-500">No data available for this statement type.</p>
      </div>
    );
  }

  return (
    <div className="bg-white border rounded-lg overflow-hidden">
      <table className="w-full">
        <thead className="bg-gray-50 border-b">
          <tr>
            <th className="px-6 py-3 text-left text-sm font-medium text-gray-700">
              Line Item
            </th>
            {fiscalYears.map((year: number) => (
              <th key={year} className="px-6 py-3 text-right text-sm font-medium text-gray-700">
                Dec {year}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200">
          {statementData.map((item: LineItem, index: number) => (
            <TreeNode
              key={`${item.canonical_name}-${index}`}
              item={item}
              fiscalYears={fiscalYears}
              depth={0}
            />
          ))}
        </tbody>
      </table>

      {/* Info Banner */}
      <div className="bg-blue-50 border-t border-blue-200 px-6 py-3">
        <div className="flex items-start gap-2 text-sm text-blue-800">
          <svg className="w-5 h-5 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div>
            <p className="font-medium">Hierarchical View</p>
            <p className="text-blue-700 mt-1">
              This view shows all extracted financial data organized by hierarchy.
              Click the arrows to expand/collapse sections and drill down into details.
              All data from the PDF is preserved and displayed here.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
