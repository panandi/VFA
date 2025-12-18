import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { api } from '../services/api';
import toast from 'react-hot-toast';

interface FileUploadProps {
  assessmentId: number;
  onUploadComplete: () => void;
}

interface UploadingFile {
  name: string;
  progress: number;
  status: 'uploading' | 'completed' | 'error';
}

export function FileUpload({ assessmentId, onUploadComplete }: FileUploadProps) {
  const [uploadingFiles, setUploadingFiles] = useState<UploadingFile[]>([]);

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      for (const file of acceptedFiles) {
        setUploadingFiles((prev) => [
          ...prev,
          { name: file.name, progress: 0, status: 'uploading' },
        ]);

        try {
          await api.uploadFile(assessmentId, file);
          setUploadingFiles((prev) =>
            prev.map((f) =>
              f.name === file.name ? { ...f, progress: 100, status: 'completed' } : f
            )
          );
          toast.success(`${file.name} uploaded successfully`);
        } catch (error) {
          setUploadingFiles((prev) =>
            prev.map((f) => (f.name === file.name ? { ...f, status: 'error' } : f))
          );
          toast.error(`Failed to upload ${file.name}`);
        }
      }
      onUploadComplete();
    },
    [assessmentId, onUploadComplete]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
    },
    multiple: true,
  });

  return (
    <div className="space-y-4">
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
          isDragActive
            ? 'border-blue-500 bg-blue-50'
            : 'border-gray-300 hover:border-gray-400'
        }`}
      >
        <input {...getInputProps()} />
        <div className="flex flex-col items-center">
          <svg
            className="w-12 h-12 text-gray-400 mb-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
            />
          </svg>
          <p className="text-gray-600 font-medium">
            {isDragActive
              ? 'Drop the files here...'
              : "Drag and drop vendor's FS here"}
          </p>
          <p className="text-sm text-gray-400 mt-1">
            Supports multiple PDF uploads. Extraction begins automatically.
          </p>
          <button
            type="button"
            className="mt-4 px-4 py-2 bg-gray-100 text-gray-700 rounded-md text-sm font-medium hover:bg-gray-200"
          >
            Browse Files
          </button>
        </div>
      </div>

      {/* Upload Progress */}
      {uploadingFiles.length > 0 && (
        <div className="space-y-2">
          {uploadingFiles.map((file, index) => (
            <div key={index} className="flex items-center space-x-3 p-3 bg-gray-50 rounded-lg">
              <svg className="w-8 h-8 text-red-500" fill="currentColor" viewBox="0 0 20 20">
                <path
                  fillRule="evenodd"
                  d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z"
                  clipRule="evenodd"
                />
              </svg>
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-700">{file.name}</p>
                <div className="mt-1 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                  <div
                    className={`h-full transition-all duration-300 ${
                      file.status === 'error' ? 'bg-red-500' : 'bg-green-500'
                    }`}
                    style={{ width: `${file.progress}%` }}
                  />
                </div>
              </div>
              {file.status === 'completed' && (
                <svg className="w-5 h-5 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                  <path
                    fillRule="evenodd"
                    d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                    clipRule="evenodd"
                  />
                </svg>
              )}
              {file.status === 'error' && (
                <svg className="w-5 h-5 text-red-500" fill="currentColor" viewBox="0 0 20 20">
                  <path
                    fillRule="evenodd"
                    d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                    clipRule="evenodd"
                  />
                </svg>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
