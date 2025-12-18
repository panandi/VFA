import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import { AssessmentListItem } from '../types';
import toast from 'react-hot-toast';

export function Dashboard() {
  const [assessments, setAssessments] = useState<AssessmentListItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [vendorName, setVendorName] = useState('');
  const [registrationNumber, setRegistrationNumber] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    loadAssessments();
  }, []);

  const loadAssessments = async () => {
    try {
      const data = await api.listAssessments();
      setAssessments(data);
    } catch (error) {
      toast.error('Failed to load assessments');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateAssessment = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const assessment = await api.createAssessment(vendorName, registrationNumber);
      toast.success('Assessment created');
      setShowModal(false);
      setVendorName('');
      setRegistrationNumber('');
      navigate(`/assessment/${assessment.id}`);
    } catch (error) {
      toast.error('Failed to create assessment');
    }
  };

  const getStatusBadge = (status: string) => {
    const statusConfig: Record<string, { bg: string; text: string; label: string }> = {
      draft: { bg: 'bg-gray-100', text: 'text-gray-600', label: 'Draft' },
      step1_complete: { bg: 'bg-blue-100', text: 'text-blue-600', label: 'Step 1' },
      step2_complete: { bg: 'bg-blue-100', text: 'text-blue-600', label: 'Step 2' },
      step3_complete: { bg: 'bg-blue-100', text: 'text-blue-600', label: 'Step 3' },
      completed: { bg: 'bg-yellow-100', text: 'text-yellow-600', label: 'Pending Sign-off' },
      signed_off: { bg: 'bg-green-100', text: 'text-green-600', label: 'Completed' },
    };
    const config = statusConfig[status] || statusConfig.draft;
    return (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${config.bg} ${config.text}`}>
        {config.label}
      </span>
    );
  };

  return (
    <>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Vendor Assessments</h1>
            <p className="text-gray-500 mt-1">Manage and review vendor financial assessments</p>
          </div>
          <button
            onClick={() => setShowModal(true)}
            className="px-4 py-2 bg-singtel-red text-white rounded-lg font-medium hover:bg-singtel-darkred transition-colors"
          >
            New Assessment
          </button>
        </div>

        {/* Assessments List */}
        {isLoading ? (
          <div className="flex justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-singtel-red"></div>
          </div>
        ) : assessments.length === 0 ? (
          <div className="bg-white rounded-lg shadow p-12 text-center">
            <svg
              className="w-16 h-16 text-gray-300 mx-auto mb-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
              />
            </svg>
            <h3 className="text-lg font-medium text-gray-900">No assessments yet</h3>
            <p className="text-gray-500 mt-1">Create your first vendor assessment to get started</p>
            <button
              onClick={() => setShowModal(true)}
              className="mt-4 px-4 py-2 bg-singtel-red text-white rounded-lg font-medium hover:bg-singtel-darkred"
            >
              Create Assessment
            </button>
          </div>
        ) : (
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Vendor
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Step
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Created
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {assessments.map((assessment) => (
                  <tr key={assessment.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="font-medium text-gray-900">{assessment.vendor_name}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {getStatusBadge(assessment.status)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-gray-500">
                      {assessment.current_step} / 4
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-gray-500">
                      {new Date(assessment.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right">
                      <button
                        onClick={() => navigate(`/assessment/${assessment.id}`)}
                        className="text-singtel-red hover:text-singtel-darkred font-medium"
                      >
                        {assessment.status === 'signed_off' ? 'View' : 'Continue'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Create Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-md">
            <h2 className="text-xl font-bold text-gray-900 mb-4">New Vendor Assessment</h2>
            <form onSubmit={handleCreateAssessment} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">Vendor Name *</label>
                <input
                  type="text"
                  value={vendorName}
                  onChange={(e) => setVendorName(e.target.value)}
                  required
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-singtel-red focus:border-singtel-red"
                  placeholder="Enter vendor name"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Registration Number
                </label>
                <input
                  type="text"
                  value={registrationNumber}
                  onChange={(e) => setRegistrationNumber(e.target.value)}
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-singtel-red focus:border-singtel-red"
                  placeholder="Optional"
                />
              </div>
              <div className="flex justify-end space-x-3 pt-4">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 text-gray-700 hover:text-gray-900"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-singtel-red text-white rounded-lg font-medium hover:bg-singtel-darkred"
                >
                  Create
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
}
