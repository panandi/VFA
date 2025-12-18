import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAssessment } from '../../context/AssessmentContext';
import { api } from '../../services/api';
import toast from 'react-hot-toast';

export function Step4Results() {
  const { assessment, refreshAssessment } = useAssessment();
  const navigate = useNavigate();
  const [isSigningOff, setIsSigningOff] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const [acknowledged, setAcknowledged] = useState(false);

  if (!assessment) return null;

  const recommendation = assessment.recommendation;
  const risk = assessment.risk_assessment;

  const handleSignOff = async () => {
    if (!acknowledged) {
      toast.error('Please acknowledge the assessment before signing off');
      return;
    }

    setIsSigningOff(true);
    try {
      await api.signOff(assessment.id);
      refreshAssessment();
      toast.success('Assessment signed off successfully');
    } catch (error) {
      toast.error('Failed to sign off');
    } finally {
      setIsSigningOff(false);
    }
  };

  const handleDownloadPdf = async () => {
    setIsDownloading(true);
    try {
      const blob = await api.downloadPdf(assessment.id);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `VFA_Report_${assessment.vendor_name?.replace(/\s+/g, '_')}_${new Date().toISOString().split('T')[0]}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      toast.success('PDF downloaded successfully');
    } catch (error) {
      toast.error('Failed to download PDF');
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
          onClick={handleDownloadPdf}
          disabled={isDownloading}
          className="flex items-center px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 disabled:opacity-50"
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
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              Download PDF
            </>
          )}
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
            {recommendation.supporting_factors.map((factor, idx) => (
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

      {/* Acknowledgment and Sign Off Section */}
      {assessment.status !== 'signed_off' ? (
        <div className="bg-gray-50 border rounded-lg p-6 space-y-4">
          {/* Acknowledgment Checkbox */}
          <div className="flex items-start space-x-3">
            <div className="flex items-center h-5">
              <input
                id="acknowledge"
                type="checkbox"
                checked={acknowledged}
                onChange={(e) => setAcknowledged(e.target.checked)}
                className="w-4 h-4 text-singtel-red border-gray-300 rounded focus:ring-singtel-red"
              />
            </div>
            <label htmlFor="acknowledge" className="text-sm text-gray-700">
              <span className="font-medium">I acknowledge</span> that I have reviewed all the financial data,
              risk assessment, and AI-generated recommendation for this vendor assessment.
              I understand that this assessment is based on the provided financial statements
              and qualitative responses, and I take responsibility for the final decision.
            </label>
          </div>

          {/* Sign Off Button */}
          <div className="flex items-center justify-between pt-4 border-t border-gray-200">
            <div>
              <h3 className="font-semibold text-gray-900">Ready to Sign Off?</h3>
              <p className="text-gray-500 text-sm mt-1">
                Once signed off, this assessment will be marked as complete.
              </p>
            </div>
            <button
              onClick={handleSignOff}
              disabled={isSigningOff || !recommendation || !acknowledged}
              className={`px-6 py-2 rounded-lg font-medium transition-colors ${
                acknowledged
                  ? 'bg-singtel-red text-white hover:bg-singtel-darkred'
                  : 'bg-gray-300 text-gray-500 cursor-not-allowed'
              } disabled:opacity-50`}
            >
              {isSigningOff ? 'Signing Off...' : 'Sign Off Assessment'}
            </button>
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
              onClick={handleDownloadPdf}
              disabled={isDownloading}
              className="flex items-center px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
            >
              {isDownloading ? (
                'Downloading...'
              ) : (
                <>
                  <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  Download Final Report
                </>
              )}
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
    </div>
  );
}
