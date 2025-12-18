import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { AuthProvider } from './context/AuthContext';
import { AssessmentProvider } from './context/AssessmentContext';
import { ProtectedRoute } from './components/ProtectedRoute';
import { Layout } from './components/Layout';
import { AssessmentWrapper } from './components/AssessmentWrapper';
import { Login } from './pages/Login';
import { Register } from './pages/Register';
import { Dashboard } from './pages/Dashboard';
import { Step1Upload } from './pages/assessment/Step1Upload';
import { Step2Confirm } from './pages/assessment/Step2Confirm';
import { Step3Ratios } from './pages/assessment/Step3Ratios';
import { Step4Results } from './pages/assessment/Step4Results';

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AssessmentProvider>
          <Toaster position="top-right" />
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route
              path="/"
              element={
                <ProtectedRoute>
                  <Layout>
                    <Dashboard />
                  </Layout>
                </ProtectedRoute>
              }
            />
            {/* Assessment Routes - Step 1 (default when clicking Continue) */}
            <Route
              path="/assessment/:id"
              element={
                <ProtectedRoute>
                  <Layout>
                    <AssessmentWrapper>
                      <Step1Upload />
                    </AssessmentWrapper>
                  </Layout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/assessment/:id/step1"
              element={
                <ProtectedRoute>
                  <Layout>
                    <AssessmentWrapper>
                      <Step1Upload />
                    </AssessmentWrapper>
                  </Layout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/assessment/:id/step2"
              element={
                <ProtectedRoute>
                  <Layout>
                    <AssessmentWrapper>
                      <Step2Confirm />
                    </AssessmentWrapper>
                  </Layout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/assessment/:id/step3"
              element={
                <ProtectedRoute>
                  <Layout>
                    <AssessmentWrapper>
                      <Step3Ratios />
                    </AssessmentWrapper>
                  </Layout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/assessment/:id/step4"
              element={
                <ProtectedRoute>
                  <Layout>
                    <AssessmentWrapper>
                      <Step4Results />
                    </AssessmentWrapper>
                  </Layout>
                </ProtectedRoute>
              }
            />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </AssessmentProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
