'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';

interface UploadState {
  policy: File | null;
  property_cert: File | null;
  gl_cert: File | null;
}

export default function QCUploadPage() {
  const router = useRouter();
  const [files, setFiles] = useState<UploadState>({
    policy: null,
    property_cert: null,
    gl_cert: null,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFileChange = (field: keyof UploadState, file: File | null) => {
    setFiles((prev) => ({
      ...prev,
      [field]: file,
    }));
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = (e: React.DragEvent, field: keyof UploadState) => {
    e.preventDefault();
    e.stopPropagation();
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile && droppedFile.type === 'application/pdf') {
      handleFileChange(field, droppedFile);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    // Validation
    if (!files.policy || !files.property_cert || !files.gl_cert) {
      setError('Please upload all three PDF files');
      return;
    }

    setLoading(true);

    try {
      const formData = new FormData();
      formData.append('policy_pdf', files.policy);
      formData.append('property_cert_pdf', files.property_cert);
      formData.append('gl_cert_pdf', files.gl_cert);
      formData.append('username', localStorage.getItem('username') || 'qc_user');

      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/upload-qc/`,
        {
          method: 'POST',
          body: formData,
        }
      );

      if (!response.ok) {
        throw new Error('Upload failed');
      }

      const data = await response.json();
      console.log('✅ Upload successful:', data);

      // Redirect to review page with polling for results
      router.push(`/quality-control/review/${data.upload_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
      console.error('Upload error:', err);
    } finally {
      setLoading(false);
    }
  };

  const FileUploadBox = ({
    title,
    icon,
    field,
    file,
  }: {
    title: string;
    icon: string;
    field: keyof UploadState;
    file: File | null;
  }) => (
    <div
      onDragOver={handleDragOver}
      onDrop={(e) => handleDrop(e, field)}
      className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center cursor-pointer hover:border-blue-500 hover:bg-blue-50 transition-all"
    >
      <label className="cursor-pointer block">
        <div className="text-4xl mb-2">{icon}</div>
        <p className="text-lg font-semibold text-gray-700">{title}</p>
        <p className="text-sm text-gray-500 mt-2">Drop PDF here or click to browse</p>
        {file && (
          <p className="text-sm text-green-600 font-medium mt-3">
            ✓ {file.name} ({(file.size / 1024 / 1024).toFixed(2)} MB)
          </p>
        )}
        <input
          type="file"
          accept=".pdf"
          onChange={(e) => handleFileChange(field, e.target.files?.[0] || null)}
          className="hidden"
        />
      </label>
    </div>
  );

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-6">
      <div className="max-w-2xl mx-auto">
        {/* Back to Dashboard Button */}
        <div className="mb-6">
          <button
            onClick={() => router.push('/dashboard')}
            className="flex items-center gap-2 px-4 py-2 bg-white text-gray-700 rounded-lg hover:bg-gray-100 transition-colors shadow-md"
          >
            <span>←</span>
            <span>Back to Dashboard</span>
          </button>
        </div>

        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">
            📋 QC Review System
          </h1>
          <p className="text-lg text-gray-600">
            Upload files for quality control review
          </p>
        </div>

        {/* Error Message */}
        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-6 py-4 rounded-lg mb-6">
            ❌ {error}
          </div>
        )}

        {/* Upload Form */}
        <form onSubmit={handleSubmit} className="space-y-6 bg-white p-8 rounded-lg shadow-lg">
          {/* Policy PDF */}
          <div>
            <FileUploadBox
              title="POLICY PDF"
              icon="📄"
              field="policy"
              file={files.policy}
            />
          </div>

          {/* Property Certificate */}
          <div>
            <FileUploadBox
              title="PROPERTY CERTIFICATE"
              icon="🏠"
              field="property_cert"
              file={files.property_cert}
            />
          </div>

          {/* GL Certificate */}
          <div>
            <FileUploadBox
              title="GL CERTIFICATE"
              icon="⚖️"
              field="gl_cert"
              file={files.gl_cert}
            />
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            disabled={loading || !files.policy || !files.property_cert || !files.gl_cert}
            className={`w-full py-3 px-6 rounded-lg font-semibold text-lg transition-all ${
              loading || !files.policy || !files.property_cert || !files.gl_cert
                ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                : 'bg-blue-600 text-white hover:bg-blue-700 active:scale-95'
            }`}
          >
            {loading ? '⏳ Processing...' : '▶ START QC REVIEW'}
          </button>
        </form>

        {/* Info Box */}
        <div className="mt-8 bg-blue-50 border border-blue-200 rounded-lg p-6">
          <p className="text-gray-700">
            💡 <span className="font-semibold">Tip:</span> All three PDF files are required.
            The system will extract information from the policy and display it alongside the
            certificates for side-by-side comparison.
          </p>
        </div>
      </div>
    </div>
  );
}

