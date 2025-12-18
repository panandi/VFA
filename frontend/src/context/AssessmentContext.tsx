import React, { createContext, useContext, useState, ReactNode, useCallback } from 'react';
import { Assessment } from '../types';
import { api } from '../services/api';

interface AssessmentContextType {
  assessment: Assessment | null;
  isLoading: boolean;
  error: string | null;
  loadAssessment: (id: number) => Promise<void>;
  refreshAssessment: () => Promise<void>;
  clearAssessment: () => void;
}

const AssessmentContext = createContext<AssessmentContextType | undefined>(undefined);

export function AssessmentProvider({ children }: { children: ReactNode }) {
  const [assessment, setAssessment] = useState<Assessment | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadAssessment = useCallback(async (id: number) => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.getAssessment(id);
      setAssessment(data);
    } catch (err) {
      setError('Failed to load assessment');
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const refreshAssessment = useCallback(async () => {
    if (assessment?.id) {
      await loadAssessment(assessment.id);
    }
  }, [assessment?.id, loadAssessment]);

  const clearAssessment = useCallback(() => {
    setAssessment(null);
    setError(null);
  }, []);

  return (
    <AssessmentContext.Provider
      value={{
        assessment,
        isLoading,
        error,
        loadAssessment,
        refreshAssessment,
        clearAssessment,
      }}
    >
      {children}
    </AssessmentContext.Provider>
  );
}

export function useAssessment() {
  const context = useContext(AssessmentContext);
  if (context === undefined) {
    throw new Error('useAssessment must be used within an AssessmentProvider');
  }
  return context;
}
