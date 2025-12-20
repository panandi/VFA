import React from 'react';

export function AssessmentSkeleton() {
  return (
    <div className="animate-pulse">
      {/* Two-column grid layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Left Column */}
        <div>
          {/* Title skeleton */}
          <div className="h-6 bg-gray-200 rounded w-3/4 mb-4"></div>

          {/* Upload box skeleton */}
          <div className="border-2 border-dashed border-gray-300 rounded-lg p-12 bg-gray-50">
            <div className="flex flex-col items-center space-y-3">
              <div className="h-12 w-12 bg-gray-200 rounded-full"></div>
              <div className="h-4 bg-gray-200 rounded w-48"></div>
              <div className="h-3 bg-gray-200 rounded w-32"></div>
            </div>
          </div>

          {/* File list skeleton */}
          <div className="mt-6 space-y-3">
            <div className="h-4 bg-gray-200 rounded w-32 mb-3"></div>
            {[1, 2].map((i) => (
              <div key={i} className="bg-white border border-gray-200 rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3 flex-1">
                    <div className="h-8 w-8 bg-gray-200 rounded"></div>
                    <div className="flex-1">
                      <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
                      <div className="h-3 bg-gray-200 rounded w-1/4"></div>
                    </div>
                  </div>
                  <div className="h-6 w-20 bg-gray-200 rounded-full"></div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Right Column */}
        <div>
          {/* Title skeleton */}
          <div className="h-6 bg-gray-200 rounded w-3/4 mb-4"></div>

          {/* Question cards skeleton */}
          <div className="space-y-4">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="bg-white border border-gray-200 rounded-lg p-4">
                <div className="h-4 bg-gray-200 rounded w-full mb-3"></div>
                <div className="flex space-x-6">
                  {[1, 2, 3].map((j) => (
                    <div key={j} className="flex items-center space-x-2">
                      <div className="h-4 w-4 bg-gray-200 rounded-full"></div>
                      <div className="h-3 bg-gray-200 rounded w-12"></div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Action buttons skeleton */}
      <div className="lg:col-span-2 flex justify-end space-x-4 pt-6 border-t mt-8">
        <div className="h-10 w-32 bg-gray-200 rounded-lg"></div>
        <div className="h-10 w-48 bg-gray-200 rounded-lg"></div>
      </div>
    </div>
  );
}
