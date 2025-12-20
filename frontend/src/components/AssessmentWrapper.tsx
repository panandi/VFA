import React, { useEffect } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { useAssessment } from '../context/AssessmentContext';
import { Stepper } from './Stepper';
import { AssessmentSkeleton } from './AssessmentSkeleton';

interface Props {
  children: React.ReactNode;
}

const steps = [
  { number: 1, title: 'Upload & Questionnaire', subtitle: 'Financial statements' },
  { number: 2, title: 'Confirm Data', subtitle: 'Review extracted data' },
  { number: 3, title: 'Financial Ratios', subtitle: 'Z-Score & metrics' },
  { number: 4, title: 'Results', subtitle: 'Recommendation' },
];

export function AssessmentWrapper({ children }: Props) {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const { assessment, isLoading, error, loadAssessment } = useAssessment();

  useEffect(() => {
    if (id) {
      loadAssessment(parseInt(id, 10));
    }
  }, [id, loadAssessment]);

  // Determine current step from URL
  const getCurrentStep = () => {
    const path = location.pathname;
    if (path.includes('/step4')) return 4;
    if (path.includes('/step3')) return 3;
    if (path.includes('/step2')) return 2;
    return 1;
  };

  const handleStepClick = (step: number) => {
    if (id && step < getCurrentStep()) {
      navigate(`/assessment/${id}/step${step}`);
    }
  };

  // Initial loading (no assessment data yet)
  if (isLoading && !assessment) {
    return (
      <div className="flex justify-center items-center py-20">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-singtel-red"></div>
      </div>
    );
  }

  if (error || !assessment) {
    return (
      <div className="text-center py-20">
        <p className="text-red-600 mb-4">{error || 'Assessment not found'}</p>
        <button
          onClick={() => navigate('/')}
          className="text-singtel-red hover:underline"
        >
          Back to Dashboard
        </button>
      </div>
    );
  }

  return (
    <div>
      {/* Assessment Header */}
      <div className="mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{assessment.vendor_name}</h1>
            {assessment.vendor_registration_number && (
              <p className="text-gray-500 text-sm">Reg: {assessment.vendor_registration_number}</p>
            )}
          </div>
          <button
            onClick={() => navigate('/')}
            className="text-gray-500 hover:text-gray-700 text-sm"
          >
            &larr; Back to Dashboard
          </button>
        </div>
      </div>

      {/* Stepper */}
      <Stepper
        steps={steps}
        currentStep={getCurrentStep()}
        onStepClick={handleStepClick}
      />

      {/* Content - Keep content visible, don't replace with skeleton */}
      <div className="mt-6">{children}</div>
    </div>
  );
}
