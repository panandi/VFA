import { useState, useEffect } from 'react';
import { api } from '../services/api';
import toast from 'react-hot-toast';

interface DisplayItem {
  name: string;
  level: number;
  is_header: boolean;
  is_total?: boolean;
  section_type: string;
  values: { [year: number]: number };
  source_items: string[];
}

interface AIOrganizedViewProps {
  assessmentId: number;
}

export function AIOrganizedView({ assessmentId }: AIOrganizedViewProps) {
  const [data, setData] = useState<any>(null);
  const [displayItems, setDisplayItems] = useState<DisplayItem[]>([]);
  const [fiscalYears, setFiscalYears] = useState<number[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notes, setNotes] = useState<string[]>([]);
  const [activeSection, setActiveSection] = useState<'all' | 'balance_sheet' | 'income_statement' | 'cash_flow' | 'other'>('all');

  useEffect(() => {
    loadAIOrganizedData();
  }, [assessmentId]);

  const loadAIOrganizedData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await api.getAIOrganizedData(assessmentId);

      if (result.success !== false) {
        setData(result.organized_data);
        setDisplayItems(result.display_items || []);
        setFiscalYears(result.fiscal_years || []);
        // Handle notes from either location
        const allNotes = result.organized_data?.notes || (result as any).notes || [];
        setNotes(allNotes);
      } else {
        setError(result.error || 'Failed to organize data');
      }
    } catch (err: any) {
      console.error('Failed to load AI organized data:', err);
      setError(err.response?.data?.detail || 'Failed to load AI organized data');
      toast.error('Failed to load AI organized data');
    } finally {
      setIsLoading(false);
    }
  };

  const formatNumber = (value: number | undefined | null): string => {
    if (value === undefined || value === null) return '-';
    const formatted = Math.abs(value).toLocaleString('en-US', {
      minimumFractionDigits: 0,
      maximumFractionDigits: 2
    });
    return value < 0 ? `(${formatted})` : formatted;
  };

  const getFilteredItems = (): DisplayItem[] => {
    if (activeSection === 'all') return displayItems;
    return displayItems.filter(item => item.section_type === activeSection);
  };

  const getSectionCounts = () => {
    return {
      balance_sheet: displayItems.filter(i => i.section_type === 'balance_sheet').length,
      income_statement: displayItems.filter(i => i.section_type === 'income_statement').length,
      cash_flow: displayItems.filter(i => i.section_type === 'cash_flow').length,
      other: displayItems.filter(i => i.section_type === 'other').length
    };
  };

  if (isLoading) {
    return (
      <div className="bg-white border rounded-lg p-12 text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-singtel-red mx-auto mb-4"></div>
        <p className="text-gray-500 mb-2">AI is organizing your financial data...</p>
        <p className="text-gray-400 text-sm">This may take a few seconds</p>
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
          onClick={loadAIOrganizedData}
          className="px-4 py-2 bg-singtel-red text-white rounded-lg hover:bg-singtel-darkred"
        >
          Retry
        </button>
      </div>
    );
  }

  if (!displayItems || displayItems.length === 0) {
    return (
      <div className="bg-white border rounded-lg p-12 text-center">
        <div className="text-gray-400 mb-4">
          <svg className="w-12 h-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
        </div>
        <p className="text-gray-500 mb-2">No organized data available</p>
        <p className="text-gray-400 text-sm">
          Upload a PDF with financial tables to extract and organize data.
        </p>
      </div>
    );
  }

  const counts = getSectionCounts();
  const filteredItems = getFilteredItems();

  return (
    <div className="space-y-4">
      {/* Section Filter Tabs */}
      <div className="bg-white border rounded-lg p-2 flex gap-2 flex-wrap">
        <button
          onClick={() => setActiveSection('all')}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            activeSection === 'all'
              ? 'bg-singtel-red text-white'
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          }`}
        >
          All Statements ({displayItems.length})
        </button>
        <button
          onClick={() => setActiveSection('balance_sheet')}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            activeSection === 'balance_sheet'
              ? 'bg-green-600 text-white'
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          }`}
        >
          Balance Sheet ({counts.balance_sheet})
        </button>
        <button
          onClick={() => setActiveSection('income_statement')}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            activeSection === 'income_statement'
              ? 'bg-purple-600 text-white'
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          }`}
        >
          Income Statement ({counts.income_statement})
        </button>
        <button
          onClick={() => setActiveSection('cash_flow')}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            activeSection === 'cash_flow'
              ? 'bg-cyan-600 text-white'
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          }`}
        >
          Cash Flow ({counts.cash_flow})
        </button>
        {counts.other > 0 && (
          <button
            onClick={() => setActiveSection('other')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              activeSection === 'other'
                ? 'bg-gray-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            Other ({counts.other})
          </button>
        )}
      </div>

      {/* Data Table */}
      <div className="bg-white border rounded-lg overflow-hidden shadow-sm">
        {/* Header */}
        <div className="bg-gradient-to-r from-singtel-red to-red-700 px-4 py-3 flex justify-between items-center">
          <div className="text-white">
            <h3 className="font-semibold flex items-center gap-2">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
              AI-Organized Financial Statements
            </h3>
            <p className="text-red-100 text-sm mt-1">
              Data automatically categorized and standardized using AI
            </p>
          </div>
          <button
            onClick={loadAIOrganizedData}
            className="text-white hover:bg-white/20 p-2 rounded transition-colors"
            title="Regenerate"
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
                <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700 min-w-[350px]">
                  Line Item
                </th>
                {fiscalYears.map((year) => (
                  <th key={year} className="px-4 py-3 text-right text-sm font-semibold text-gray-700 min-w-[130px]">
                    FY {year}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filteredItems.map((item, index) => {
                const indent = item.level * 20;

                // Style based on item type - using black text
                let rowClass = 'hover:bg-blue-50 transition-colors';
                let textClass = 'text-black';

                if (item.is_header) {
                  if (item.level === 0) {
                    rowClass = 'bg-gray-200';
                    textClass = 'text-black font-bold text-base';
                  } else {
                    rowClass = 'bg-gray-100';
                    textClass = 'text-black font-semibold';
                  }
                } else if (item.is_total) {
                  rowClass = 'bg-gray-50 font-semibold';
                  textClass = 'text-black font-semibold';
                }

                return (
                  <tr key={`${item.name}-${index}`} className={rowClass}>
                    <td className="px-4 py-2.5 text-sm border-b" style={{ paddingLeft: `${16 + indent}px` }}>
                      <div className="flex items-center gap-2">
                        <span className={textClass}>{item.name}</span>
                        {item.source_items && item.source_items.length > 0 && (
                          <span
                            className="text-xs text-gray-500 cursor-help"
                            title={`Mapped from: ${item.source_items.join(', ')}`}
                          >
                            ({item.source_items.length})
                          </span>
                        )}
                      </div>
                    </td>
                    {fiscalYears.map((year) => (
                      <td
                        key={year}
                        className={`px-4 py-2.5 text-sm text-right border-b tabular-nums text-black ${
                          item.is_total ? 'font-semibold' : ''
                        }`}
                      >
                        {!item.is_header ? formatNumber(item.values[year]) : ''}
                      </td>
                    ))}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Footer info */}
        <div className="bg-green-50 border-t border-green-200 px-4 py-3">
          <div className="flex items-start gap-3 text-sm text-green-800">
            <svg className="w-5 h-5 flex-shrink-0 mt-0.5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div>
              <p className="font-medium">AI-Organized Data</p>
              <p className="text-green-700 mt-1">
                This data has been automatically organized and standardized by AI.
                Line items have been mapped to standard financial terminology.
                Hover over the numbers in parentheses to see the original source items.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Mapping Notes */}
      {notes.length > 0 && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <h4 className="font-medium text-yellow-800 mb-2 flex items-center gap-2">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            AI Mapping Notes
          </h4>
          <ul className="list-disc list-inside text-sm text-yellow-700 space-y-1">
            {notes.map((note: string, i: number) => (
              <li key={i}>{note}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
