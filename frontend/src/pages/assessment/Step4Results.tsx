import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAssessment } from '../../context/AssessmentContext';
import { api } from '../../services/api';
import toast from 'react-hot-toast';

interface ConfirmationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onDownload: () => void;
  isDownloading: boolean;
  assessment: any;
  recommendation: any;
  risk: any;
  userName?: string;
}

function ConfirmationModal({
  isOpen,
  onClose,
  onDownload,
  isDownloading,
  assessment,
  recommendation,
  risk,
  userName = 'User',
}: ConfirmationModalProps) {
  if (!isOpen) return null;

  const getRiskColor = (level: string | undefined) => {
    switch (level) {
      case 'low':
        return 'bg-green-50 border-green-300';
      case 'medium':
        return 'bg-yellow-50 border-yellow-300';
      case 'high':
        return 'bg-red-50 border-red-300';
      default:
        return 'bg-gray-50 border-gray-300';
    }
  };

  const getRiskTextColor = (level: string | undefined) => {
    switch (level) {
      case 'low':
        return 'text-green-700';
      case 'medium':
        return 'text-yellow-700';
      case 'high':
        return 'text-red-700';
      default:
        return 'text-gray-700';
    }
  };

  const getRiskLabel = (level: string | undefined) => {
    switch (level) {
      case 'low':
        return 'Low Risk';
      case 'medium':
        return 'Medium Risk';
      case 'high':
        return 'High Risk';
      default:
        return 'Unknown';
    }
  };

  const getRiskDescription = (level: string | undefined) => {
    switch (level) {
      case 'low':
        return 'Safe Zone - Company is financially healthy';
      case 'medium':
        return 'Grey Zone - Some risk, requires monitoring';
      case 'high':
        return 'Distress Zone - High risk of financial distress';
      default:
        return 'Unable to determine risk level';
    }
  };

  const formatRatio = (value: number | undefined | null): string => {
    if (value === undefined || value === null) return '-';
    return value.toFixed(2);
  };

  const formatPercent = (value: number | undefined | null): string => {
    if (value === undefined || value === null) return '-';
    return `${value.toFixed(1)}%`;
  };

  // Generate Report ID
  const reportId = `VFA-${new Date().getFullYear()}-${assessment.id}${Date.now().toString().slice(-8)}`;
  const currentDate = new Date().toLocaleDateString('en-GB');
  const signOffTime = new Date().toLocaleString('en-GB');

  // Get the most recent financial data
  const latestData = assessment.extracted_data?.sort(
    (a: any, b: any) => b.fiscal_year - a.fiscal_year
  )[0];

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-2xl w-full max-w-lg max-h-[85vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="px-5 py-4 border-b flex justify-between items-center">
          <h2 className="text-lg font-semibold text-gray-900">Vendor Financial Assessment Report</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 p-1"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Scrollable Content */}
        <div className="flex-1 overflow-y-auto p-5 space-y-5">
          {/* Title Section */}
          <div className="flex justify-between items-start">
            <div>
              <p className="text-singtel-red font-semibold text-sm">Singtel</p>
              <h3 className="text-xl font-bold text-gray-900 mt-1">
                Vendor Financial<br />Assessment Report
              </h3>
            </div>
            <div className="text-right text-sm text-gray-600">
              <p>Report ID: {reportId}</p>
              <p>Date: {currentDate}</p>
            </div>
          </div>

          {/* Assessment Details */}
          <div className="border-t pt-4">
            <h4 className="font-semibold text-gray-900 mb-3">Assessment Details</h4>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <p className="text-gray-500">Vendor Name:</p>
                <p className="font-medium text-gray-900">{assessment.vendor_name}</p>
              </div>
              <div>
                <p className="text-gray-500">Assessment Date:</p>
                <p className="font-medium text-gray-900">{new Date(assessment.assessment_date).toLocaleDateString('en-GB')}</p>
              </div>
              <div>
                <p className="text-gray-500">Assessed By:</p>
                <p className="font-medium text-gray-900">{userName}</p>
              </div>
              <div>
                <p className="text-gray-500">Sign-off Time:</p>
                <p className="font-medium text-gray-900 bg-yellow-100 px-1 inline-block">{signOffTime}</p>
              </div>
            </div>
          </div>

          {/* Risk Assessment Summary */}
          <div className="border-t pt-4">
            <h4 className="font-semibold text-gray-900 mb-3">Risk Assessment Summary</h4>
            <div className={`rounded-lg border-2 p-4 ${getRiskColor(risk?.risk_level)}`}>
              <div className="flex items-center gap-4">
                <div className="text-3xl font-bold text-gray-900">
                  {risk?.z_score?.toFixed(2) || '-'}
                </div>
                <div>
                  <p className={`font-semibold ${getRiskTextColor(risk?.risk_level)}`}>
                    {getRiskLabel(risk?.risk_level)}
                  </p>
                  <p className="text-sm text-gray-600">Z-Score: {risk?.z_score?.toFixed(2) || '-'}</p>
                </div>
              </div>
              <p className="text-sm text-gray-600 mt-2">
                {getRiskDescription(risk?.risk_level)}
              </p>
            </div>
          </div>

          {/* Key Financial Ratios */}
          <div className="border-t pt-4">
            <h4 className="font-semibold text-gray-900 mb-3">Key Financial Ratios</h4>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between py-1 border-b border-gray-100">
                <span className="text-gray-600">Current Ratio</span>
                <span className="font-medium text-gray-900">{formatRatio(risk?.current_ratio)}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-gray-100">
                <span className="text-gray-600">Quick Ratio</span>
                <span className="font-medium text-gray-900">{formatRatio(risk?.quick_ratio)}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-gray-100">
                <span className="text-gray-600">Debt-to-Equity</span>
                <span className="font-medium text-gray-900">{formatRatio(risk?.debt_to_equity)}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-gray-100">
                <span className="text-gray-600">Debt-to-Assets</span>
                <span className="font-medium text-gray-900">{formatRatio(risk?.debt_to_assets)}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-gray-100">
                <span className="text-gray-600">ROA</span>
                <span className="font-medium text-gray-900">{formatPercent(risk?.roa)}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-gray-100">
                <span className="text-gray-600">ROE</span>
                <span className="font-medium text-gray-900">{formatPercent(risk?.roe)}</span>
              </div>
              <div className="flex justify-between py-1">
                <span className="text-gray-600">Net Margin</span>
                <span className="font-medium text-gray-900">{formatPercent(risk?.net_margin)}</span>
              </div>
            </div>
          </div>

          {/* Recommendation */}
          <div className="border-t pt-4">
            <h4 className="font-semibold text-gray-900 mb-3">Final Recommendation</h4>
            <div className={`rounded-lg p-3 ${
              recommendation?.recommendation_type === 'proceed' ? 'bg-green-50 border border-green-200' :
              recommendation?.recommendation_type === 'proceed_with_mitigation' ? 'bg-yellow-50 border border-yellow-200' :
              recommendation?.recommendation_type === 'do_not_proceed' ? 'bg-red-50 border border-red-200' :
              'bg-gray-50 border border-gray-200'
            }`}>
              <p className={`font-semibold ${
                recommendation?.recommendation_type === 'proceed' ? 'text-green-700' :
                recommendation?.recommendation_type === 'proceed_with_mitigation' ? 'text-yellow-700' :
                recommendation?.recommendation_type === 'do_not_proceed' ? 'text-red-700' :
                'text-gray-700'
              }`}>
                {recommendation?.recommendation_type === 'proceed' && 'Proceed'}
                {recommendation?.recommendation_type === 'proceed_with_mitigation' && 'Proceed with Mitigation'}
                {recommendation?.recommendation_type === 'do_not_proceed' && 'Do Not Proceed'}
                {!recommendation && 'Pending'}
              </p>
            </div>
          </div>
        </div>

        {/* Footer Actions */}
        <div className="px-5 py-4 border-t bg-gray-50 flex justify-between items-center">
          <button
            onClick={onDownload}
            disabled={isDownloading}
            className="flex items-center px-5 py-2.5 bg-yellow-400 hover:bg-yellow-500 text-gray-900 rounded-lg font-medium disabled:opacity-50 transition-colors"
          >
            {isDownloading ? (
              <>
                <svg className="animate-spin -ml-1 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Downloading...
              </>
            ) : (
              <>
                <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
                Download Excel
              </>
            )}
          </button>

          <button
            onClick={onClose}
            className="px-5 py-2.5 bg-gray-200 hover:bg-gray-300 text-gray-700 rounded-lg font-medium transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

export function Step4Results() {
  const { assessment, refreshAssessment } = useAssessment();
  const navigate = useNavigate();
  const [isSigningOff, setIsSigningOff] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const [showConfirmModal, setShowConfirmModal] = useState(false);

  if (!assessment) return null;

  const recommendation = assessment.recommendation;
  const risk = assessment.risk_assessment;

  const handleSignOff = async () => {
    setIsSigningOff(true);
    const loadingToast = toast.loading('Signing off assessment...');
    try {
      await api.signOff(assessment.id);
      refreshAssessment();
      toast.success('Assessment signed off successfully!', { id: loadingToast });
    } catch (error) {
      toast.error('Failed to sign off', { id: loadingToast });
    } finally {
      setIsSigningOff(false);
    }
  };

  const handleDownloadExcel = async () => {
    setIsDownloading(true);
    const loadingToast = toast.loading('Generating Excel report...');
    try {
      const blob = await api.downloadExcel(assessment.id);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `VFA_Report_${assessment.vendor_name?.replace(/\s+/g, '_')}_${new Date().toISOString().split('T')[0]}.xlsx`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      toast.success('Excel report downloaded', { id: loadingToast });
    } catch (error) {
      toast.error('Failed to download Excel report', { id: loadingToast });
    } finally {
      setIsDownloading(false);
    }
  };

  const getRecommendationStyle = (type: string | undefined) => {
    switch (type) {
      case 'proceed':
        return {
          bg: 'bg-green-50 border-green-200',
          icon: 'text-green-600',
          title: 'Proceed',
          titleColor: 'text-green-700',
        };
      case 'proceed_with_mitigation':
        return {
          bg: 'bg-yellow-50 border-yellow-200',
          icon: 'text-yellow-600',
          title: 'Proceed with Mitigation',
          titleColor: 'text-yellow-700',
        };
      case 'do_not_proceed':
        return {
          bg: 'bg-red-50 border-red-200',
          icon: 'text-red-600',
          title: 'Do Not Proceed',
          titleColor: 'text-red-700',
        };
      default:
        return {
          bg: 'bg-gray-50 border-gray-200',
          icon: 'text-gray-600',
          title: 'Pending',
          titleColor: 'text-gray-700',
        };
    }
  };

  const style = getRecommendationStyle(recommendation?.recommendation_type);

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-start">
        <div>
          <h2 className="text-xl font-semibold text-gray-900">Assessment Results & Recommendation</h2>
          <p className="text-gray-500 mt-1">
            AI-generated recommendation for {assessment.vendor_name}
          </p>
        </div>
        {/* Download PDF Button */}
        <button
          onClick={() => setShowConfirmModal(true)}
          className="flex items-center px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50"
        >
          <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          View Report
        </button>
      </div>

      {/* Recommendation Card */}
      <div className={`border-2 rounded-lg p-6 ${style.bg}`}>
        <div className="flex items-start space-x-4">
          <div className={`flex-shrink-0 ${style.icon}`}>
            {recommendation?.recommendation_type === 'proceed' && (
              <svg className="w-12 h-12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            )}
            {recommendation?.recommendation_type === 'proceed_with_mitigation' && (
              <svg className="w-12 h-12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            )}
            {recommendation?.recommendation_type === 'do_not_proceed' && (
              <svg className="w-12 h-12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            )}
            {!recommendation && (
              <svg className="w-12 h-12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            )}
          </div>
          <div className="flex-1">
            <h3 className={`text-2xl font-bold ${style.titleColor}`}>
              {style.title}
            </h3>
            {recommendation?.recommendation_text && (
              <p className="text-gray-700 mt-2">{recommendation.recommendation_text}</p>
            )}
          </div>
        </div>
      </div>

      {/* Summary */}
      {recommendation?.summary && (
        <div className="bg-white border rounded-lg p-6">
          <h3 className="font-semibold text-gray-900 mb-3">Executive Summary</h3>
          <p className="text-gray-700 leading-relaxed">{recommendation.summary}</p>
        </div>
      )}

      {/* Supporting Factors */}
      {recommendation?.supporting_factors && recommendation.supporting_factors.length > 0 && (
        <div className="bg-white border rounded-lg p-6">
          <h3 className="font-semibold text-gray-900 mb-4">Supporting Factors</h3>
          <ul className="space-y-3">
            {recommendation.supporting_factors.map((factor: string, idx: number) => (
              <li key={idx} className="flex items-start space-x-3">
                <span className="flex-shrink-0 w-6 h-6 rounded-full bg-singtel-red text-white flex items-center justify-center text-sm font-medium">
                  {idx + 1}
                </span>
                <span className="text-gray-700">{factor}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Risk Summary */}
      {risk && (
        <div className="bg-white border rounded-lg p-6">
          <h3 className="font-semibold text-gray-900 mb-4">Key Financial Metrics</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center p-4 bg-gray-50 rounded-lg">
              <p className="text-sm text-gray-500">Z-Score</p>
              <p className="text-2xl font-bold text-gray-900">{risk.z_score?.toFixed(2) || '-'}</p>
              <p className={`text-sm font-medium ${
                risk.risk_level === 'low' ? 'text-green-600' :
                risk.risk_level === 'medium' ? 'text-yellow-600' : 'text-red-600'
              }`}>
                {risk.risk_level?.toUpperCase()} RISK
              </p>
            </div>
            <div className="text-center p-4 bg-gray-50 rounded-lg">
              <p className="text-sm text-gray-500">Current Ratio</p>
              <p className="text-2xl font-bold text-gray-900">{risk.current_ratio?.toFixed(2) || '-'}</p>
            </div>
            <div className="text-center p-4 bg-gray-50 rounded-lg">
              <p className="text-sm text-gray-500">Debt-to-Equity</p>
              <p className="text-2xl font-bold text-gray-900">{risk.debt_to_equity?.toFixed(2) || '-'}</p>
            </div>
            <div className="text-center p-4 bg-gray-50 rounded-lg">
              <p className="text-sm text-gray-500">ROE</p>
              <p className="text-2xl font-bold text-gray-900">{risk.roe?.toFixed(1) || '-'}%</p>
            </div>
          </div>
        </div>
      )}

      {/* Sign Off Section */}
      {assessment.status !== 'signed_off' ? (
        <div className="bg-gray-50 border rounded-lg p-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-semibold text-gray-900">Ready to Sign Off?</h3>
              <p className="text-gray-500 text-sm mt-1">
                Review report and sign off to complete the assessment.
              </p>
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={() => setShowConfirmModal(true)}
                className="px-4 py-2 border border-gray-300 rounded-lg font-medium hover:bg-gray-100 flex items-center"
              >
                <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                </svg>
                Download Report
              </button>
              <button
                onClick={handleSignOff}
                disabled={isSigningOff || !recommendation}
                className="px-6 py-2 bg-singtel-red text-white rounded-lg font-medium hover:bg-singtel-darkred disabled:opacity-50 flex items-center"
              >
                {isSigningOff ? (
                  <>
                    <svg className="animate-spin -ml-1 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Signing Off...
                  </>
                ) : (
                  <>
                    <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    Sign Off
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      ) : (
        <div className="bg-green-50 border border-green-200 rounded-lg p-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <div>
                <p className="font-semibold text-green-700">Assessment Completed</p>
                <p className="text-green-600 text-sm">
                  Signed off on {recommendation?.signed_off_at ? new Date(recommendation.signed_off_at).toLocaleDateString() : 'N/A'}
                </p>
              </div>
            </div>
            <button
              onClick={() => setShowConfirmModal(true)}
              className="flex items-center px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
            >
              <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              Download Excel Report
            </button>
          </div>
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex justify-between pt-6 border-t">
        <button
          onClick={() => navigate(`/assessment/${assessment.id}/step3`)}
          className="px-4 py-2 text-gray-600 hover:text-gray-900"
        >
          Back to Ratios
        </button>
        <button
          onClick={() => navigate('/')}
          className="px-6 py-2 border border-gray-300 rounded-lg font-medium hover:bg-gray-50"
        >
          Back to Dashboard
        </button>
      </div>

      {/* Confirmation Modal */}
      <ConfirmationModal
        isOpen={showConfirmModal}
        onClose={() => setShowConfirmModal(false)}
        onDownload={handleDownloadExcel}
        isDownloading={isDownloading}
        assessment={assessment}
        recommendation={recommendation}
        risk={risk}
        userName="Partha"
      />
    </div>
  );
}
