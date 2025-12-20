import React from 'react';

interface ProcessingBannerProps {
  processedFiles: number;
  totalFiles: number;
  currentStatus: string;
  extractedYears?: number;
  currentPage?: number;
  totalPages?: number;
  statementType?: string;
  timeRemainingSeconds?: number;
}

export function ProcessingBanner({
  processedFiles,
  totalFiles,
  currentStatus,
  extractedYears,
  currentPage = 0,
  totalPages = 0,
  statementType = '',
  timeRemainingSeconds,
}: ProcessingBannerProps) {
  const percentage = totalFiles > 0 ? Math.round((processedFiles / totalFiles) * 100) : 0;
  const isComplete = processedFiles === totalFiles && totalFiles > 0;

  // Format time remaining
  const formatTimeRemaining = (seconds: number | undefined): string => {
    if (!seconds || seconds <= 0) return '';
    if (seconds < 60) return `${seconds}s`;
    const minutes = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${minutes}m ${secs}s`;
  };

  // Format statement type for display
  const formatStatementType = (type: string): string => {
    if (!type) return '';
    return type.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase());
  };

  return (
    <div className="fixed top-0 left-0 right-0 z-50 bg-white border-b-4 border-blue-500 shadow-lg">
      <div className="max-w-7xl mx-auto px-4 py-4">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center space-x-3">
            {!isComplete ? (
              <svg
                className="animate-spin h-6 w-6 text-blue-600"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                ></circle>
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                ></path>
              </svg>
            ) : (
              <svg
                className="h-6 w-6 text-green-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            )}
            <div>
              <h3 className="text-lg font-semibold text-gray-900">
                {isComplete ? 'Processing Complete!' : 'AI Document Processing'}
              </h3>
              <p className="text-sm text-gray-600">{currentStatus}</p>
              {!isComplete && currentPage > 0 && totalPages > 0 && (
                <p className="text-xs text-blue-600 mt-1">
                  {formatStatementType(statementType)} - Page {currentPage} of {totalPages}
                  {timeRemainingSeconds !== undefined && timeRemainingSeconds > 0 && (
                    <span className="ml-2 text-gray-500">
                      • {formatTimeRemaining(timeRemainingSeconds)} remaining
                    </span>
                  )}
                </p>
              )}
            </div>
          </div>
          <div className="text-right">
            <div className="text-2xl font-bold text-blue-600">{percentage}%</div>
            <div className="text-xs text-gray-500">
              {processedFiles} of {totalFiles} files
            </div>
            {!isComplete && timeRemainingSeconds !== undefined && timeRemainingSeconds > 0 && (
              <div className="text-sm font-medium text-blue-600 mt-1">
                {formatTimeRemaining(timeRemainingSeconds)}
              </div>
            )}
          </div>
        </div>

        {/* Progress Bar */}
        <div className="relative">
          <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
            <div
              className={`h-3 rounded-full transition-all duration-500 ${
                isComplete ? 'bg-green-500' : 'bg-blue-600'
              }`}
              style={{ width: `${percentage}%` }}
            >
              <div className="h-full w-full bg-gradient-to-r from-transparent via-white to-transparent opacity-30 animate-shimmer"></div>
            </div>
          </div>
        </div>

        {/* Extracted Data Info */}
        {isComplete && extractedYears !== undefined && extractedYears > 0 && (
          <div className="mt-3 flex items-center space-x-2 text-sm text-green-700 bg-green-50 px-3 py-2 rounded-lg">
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
              <path
                fillRule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                clipRule="evenodd"
              />
            </svg>
            <span className="font-medium">
              Successfully extracted financial data for {extractedYears} fiscal year(s)
            </span>
          </div>
        )}
      </div>

      <style>{`
        @keyframes shimmer {
          0% {
            transform: translateX(-100%);
          }
          100% {
            transform: translateX(100%);
          }
        }
        .animate-shimmer {
          animation: shimmer 2s infinite;
        }
      `}</style>
    </div>
  );
}
