import React from 'react';

interface Step {
  number: number;
  title: string;
  subtitle?: string;
}

interface StepperProps {
  steps: Step[];
  currentStep: number;
  onStepClick?: (step: number) => void;
}

export function Stepper({ steps, currentStep, onStepClick }: StepperProps) {
  return (
    <div className="w-full py-6">
      <div className="flex items-center justify-between">
        {steps.map((step, index) => (
          <React.Fragment key={step.number}>
            {/* Step Circle */}
            <div
              className={`flex flex-col items-center ${
                onStepClick && step.number < currentStep ? 'cursor-pointer' : ''
              }`}
              onClick={() => {
                if (onStepClick && step.number < currentStep) {
                  onStepClick(step.number);
                }
              }}
            >
              <div
                className={`w-10 h-10 rounded-full flex items-center justify-center text-sm font-medium ${
                  step.number < currentStep
                    ? 'bg-gray-600 text-white'
                    : step.number === currentStep
                    ? 'bg-blue-600 text-white ring-4 ring-blue-100'
                    : 'bg-gray-200 text-gray-500'
                }`}
              >
                {step.number < currentStep ? (
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                    <path
                      fillRule="evenodd"
                      d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                      clipRule="evenodd"
                    />
                  </svg>
                ) : (
                  step.number
                )}
              </div>
              <div className="mt-2 text-center">
                <p
                  className={`text-sm font-medium ${
                    step.number === currentStep ? 'text-blue-600' : 'text-gray-500'
                  }`}
                >
                  {step.title}
                </p>
                {step.subtitle && (
                  <p className="text-xs text-gray-400 mt-0.5">{step.subtitle}</p>
                )}
              </div>
            </div>

            {/* Connector Line */}
            {index < steps.length - 1 && (
              <div className="flex-1 mx-4">
                <div
                  className={`h-1 rounded ${
                    step.number < currentStep ? 'bg-singtel-red' : 'bg-gray-200'
                  }`}
                />
              </div>
            )}
          </React.Fragment>
        ))}
      </div>
    </div>
  );
}
