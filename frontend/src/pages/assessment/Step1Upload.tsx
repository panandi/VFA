import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAssessment } from '../../context/AssessmentContext';
import { FileUpload } from '../../components/FileUpload';
import { api } from '../../services/api';
import toast from 'react-hot-toast';

interface ExtractionStatus {
  total_files: number;
  processed_files: number;
  is_complete: boolean;
  has_errors: boolean;
  extracted_years: number;
  status: 'pending' | 'processing' | 'complete';
}

export function Step1Upload() {
  const { assessment, refreshAssessment } = useAssessment();
  const navigate = useNavigate();
  const [isSaving, setIsSaving] = useState(false);
  const [extractionStatus, setExtractionStatus] = useState<ExtractionStatus | null>(null);
  const [isPolling, setIsPolling] = useState(false);
  const pollingRef = useRef<NodeJS.Timeout | null>(null);

  // Poll for extraction status
  useEffect(() => {
    if (!assessment) return;

    const hasUnprocessedFiles = assessment.financial_statements.some(f => !f.is_processed);

    if (hasUnprocessedFiles && !pollingRef.current) {
      setIsPolling(true);
      pollExtractionStatus();
    }

    return () => {
      if (pollingRef.current) {
        clearTimeout(pollingRef.current);
        pollingRef.current = null;
      }
    };
  }, [assessment?.financial_statements]);

  const pollExtractionStatus = async () => {
    if (!assessment) return;

    try {
      const status = await api.getExtractionStatus(assessment.id);
      setExtractionStatus(status);

      if (status.is_complete) {
        setIsPolling(false);
        refreshAssessment();
        if (status.extracted_years > 0) {
          toast.success(`Extraction complete! Found data for ${status.extracted_years} fiscal year(s)`);
        }
      } else {
        // Continue polling every 1 second (faster since extraction is quick)
        pollingRef.current = setTimeout(pollExtractionStatus, 1000);
      }
    } catch (error) {
      console.error('Polling error:', error);
      pollingRef.current = setTimeout(pollExtractionStatus, 1500);
    }
  };

  if (!assessment) return null;

  const handleResponseChange = async (questionId: string, response: string) => {
    try {
      await api.updateQualitativeResponse(assessment.id, questionId, { response });
      refreshAssessment();
    } catch (error) {
      toast.error('Failed to save response');
    }
  };

  const handleFileUploaded = () => {
    refreshAssessment();
    // Start polling after upload
    if (!pollingRef.current) {
      setIsPolling(true);
      setTimeout(pollExtractionStatus, 1000);
    }
  };

  const handleContinue = async () => {
    if (assessment.financial_statements.length === 0) {
      toast.error('Please upload at least one financial statement');
      return;
    }

    const unanswered = assessment.qualitative_responses.filter((q) => !q.response);
    if (unanswered.length > 0) {
      toast.error('Please answer all questionnaire items');
      return;
    }

    // Check if extraction is still in progress
    if (isPolling) {
      toast.error('Please wait for file processing to complete');
      return;
    }

    setIsSaving(true);
    try {
      await api.updateAssessment(assessment.id, {
        status: 'step1_complete',
        current_step: 2,
      });
      refreshAssessment();
      navigate(`/assessment/${assessment.id}/step2`);
    } catch (error) {
      toast.error('Failed to proceed');
    } finally {
      setIsSaving(false);
    }
  };

  const handleSaveProgress = async () => {
    toast.success('Progress saved');
  };

  // Calculate progress percentage
  const getProgressPercent = () => {
    if (!extractionStatus || extractionStatus.total_files === 0) return 0;
    return Math.round((extractionStatus.processed_files / extractionStatus.total_files) * 100);
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
      {/* Left Column - File Upload */}
      <div>
        <h2 className="text-xl font-semibold text-gray-900 mb-4">
          Upload Vendor's Financial Statements (PDF Only)
        </h2>
        <FileUpload assessmentId={assessment.id} onUploadComplete={handleFileUploaded} />

        {/* Uploaded Files with Progress */}
        {assessment.financial_statements.length > 0 && (
          <div className="mt-6">
            <h3 className="text-sm font-medium text-gray-700 mb-3">Uploaded Files</h3>
            <div className="space-y-3">
              {assessment.financial_statements.map((file) => (
                <div
                  key={file.id}
                  className="bg-white border border-gray-200 rounded-lg p-4"
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center space-x-3">
                      <svg className="w-8 h-8 text-red-500" fill="currentColor" viewBox="0 0 20 20">
                        <path
                          fillRule="evenodd"
                          d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z"
                          clipRule="evenodd"
                        />
                      </svg>
                      <div>
                        <p className="text-sm font-medium text-gray-700">{file.filename}</p>
                        <p className="text-xs text-gray-400">
                          {file.file_size ? `${(file.file_size / 1024 / 1024).toFixed(2)} MB` : ''}
                        </p>
                      </div>
                    </div>
                    <span
                      className={`text-xs px-2 py-1 rounded-full font-medium ${
                        file.is_processed
                          ? 'bg-green-100 text-green-700'
                          : file.processing_status === 'error'
                          ? 'bg-red-100 text-red-700'
                          : 'bg-blue-100 text-blue-700'
                      }`}
                    >
                      {file.is_processed
                        ? '✓ Processed'
                        : file.processing_status === 'error'
                        ? '✗ Error'
                        : 'Extracting...'}
                    </span>
                  </div>

                  {/* Progress Bar for Processing Files */}
                  {!file.is_processed && file.processing_status !== 'error' && (
                    <div className="mt-2">
                      <div className="flex items-center space-x-2">
                        <div className="flex-1 bg-gray-200 rounded-full h-2 overflow-hidden">
                          <div
                            className="bg-blue-500 h-2 rounded-full animate-pulse transition-all duration-300"
                            style={{ width: '100%' }}
                          />
                        </div>
                        <div className="flex items-center space-x-1 text-blue-600">
                          <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                          </svg>
                          <span className="text-xs">AI Processing</span>
                        </div>
                      </div>
                      <p className="text-xs text-gray-500 mt-1">
                        Extracting financial data using AI...
                      </p>
                    </div>
                  )}
                </div>
              ))}
            </div>

            {/* Overall Extraction Status */}
            {extractionStatus && extractionStatus.status === 'processing' && (
              <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-blue-700">
                    Extracting Financial Data
                  </span>
                  <span className="text-sm text-blue-600">
                    {extractionStatus.processed_files}/{extractionStatus.total_files} files
                  </span>
                </div>
                <div className="w-full bg-blue-200 rounded-full h-2.5">
                  <div
                    className="bg-blue-600 h-2.5 rounded-full transition-all duration-500"
                    style={{ width: `${getProgressPercent()}%` }}
                  />
                </div>
                <p className="text-xs text-blue-600 mt-2">
                  Please wait while AI extracts balance sheet, P&L, and cash flow data...
                </p>
              </div>
            )}

            {/* Extraction Complete Status */}
            {extractionStatus && extractionStatus.is_complete && extractionStatus.extracted_years > 0 && (
              <div className="mt-4 p-4 bg-green-50 border border-green-200 rounded-lg">
                <div className="flex items-center space-x-2">
                  <svg className="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <span className="text-sm font-medium text-green-700">
                    Extraction Complete!
                  </span>
                </div>
                <p className="text-xs text-green-600 mt-1">
                  Found financial data for {extractionStatus.extracted_years} fiscal year(s).
                  You can review and edit the data in the next step.
                </p>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Right Column - Questionnaire */}
      <div>
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Vendor Qualitative Assessment</h2>
        <div className="space-y-4">
          {assessment.qualitative_responses.map((question) => (
            <div key={question.id} className="bg-white border border-gray-200 rounded-lg p-4">
              <p className="font-medium text-gray-900 mb-3">
                <span className="text-singtel-red mr-2">{question.question_id}</span>
                {question.question_text}
                <span className="text-red-500 ml-1">*</span>
              </p>
              <div className="flex space-x-6">
                {['yes', 'no', 'n/a'].map((option) => (
                  <label key={option} className="flex items-center cursor-pointer">
                    <input
                      type="radio"
                      name={question.question_id}
                      value={option}
                      checked={question.response === option}
                      onChange={() => handleResponseChange(question.question_id, option)}
                      className="w-4 h-4 text-singtel-red focus:ring-singtel-red"
                    />
                    <span className="ml-2 text-gray-700 capitalize">
                      {option === 'n/a' ? 'N/A' : option.charAt(0).toUpperCase() + option.slice(1)}
                    </span>
                  </label>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Action Buttons */}
      <div className="lg:col-span-2 flex justify-end space-x-4 pt-6 border-t">
        <button
          onClick={handleSaveProgress}
          className="flex items-center px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50"
        >
          <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4"
            />
          </svg>
          Save Progress
        </button>
        <button
          onClick={handleContinue}
          disabled={isSaving || isPolling}
          className="px-6 py-2 bg-singtel-red text-white rounded-lg font-medium hover:bg-singtel-darkred disabled:opacity-50 flex items-center"
        >
          {isPolling ? (
            <>
              <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Processing...
            </>
          ) : isSaving ? (
            'Saving...'
          ) : (
            'Continue to Financial Data'
          )}
        </button>
      </div>
    </div>
  );
}
