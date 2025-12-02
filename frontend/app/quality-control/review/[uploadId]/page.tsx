'use client';

import { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import PDFViewer from '@/components/PDFViewer';
import ExtractedFieldsDisplay from '@/components/ExtractedFieldsDisplay';

interface QCResult {
  upload_id: string;
  data: {
    llm_results?: {
      coverage_types?: {
        GL?: Record<string, any>;
        PROPERTY?: Record<string, any>;
      };
    };
    flagged_results?: {
      property?: Record<string, any>;
      gl?: Record<string, any>;
    };
    certificates: {
      property: string | null;
      gl: string | null;
    };
  };
}

export default function QCReviewPage() {
  const params = useParams();
  const uploadId = params.uploadId as string;

  const [selectedCert, setSelectedCert] = useState<'property' | 'gl'>('property');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<QCResult | null>(null);
  const [pollCount, setPollCount] = useState(0);

  // Polling function to check for results
  useEffect(() => {
    const fetchResults = async () => {
      try {
        const response = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/qc-results/${uploadId}`
        );

        if (!response.ok) {
          if (response.status === 404 && pollCount < 60) {
            // Still processing, keep polling (max 2 minutes)
            setTimeout(() => setPollCount((p) => p + 1), 2000);
            return;
          }
          throw new Error('Failed to fetch results');
        }

        const data = await response.json();
        console.log('API Response:', data);
        console.log('LLM Results:', data.data?.llm_results);
        console.log('Flagged Results:', data.data?.flagged_results);
        
        if (data.success && data.data.llm_results) {
          // Wait for BOTH llm_results AND flagged_results before displaying
          // flagged_results takes longer because it needs certificate extraction + comparison
          if (data.data.flagged_results && Object.keys(data.data.flagged_results).length > 0) {
            console.log('✅ Both LLM and flagged results ready!');
            setResults(data);
            setLoading(false);
          } else if (pollCount < 120) {
            // Keep polling up to 4 minutes for flagged results (certificate extraction is slow)
            console.log(`⏳ Waiting for flagged results... (poll ${pollCount + 1}/120)`);
            setTimeout(() => setPollCount((p) => p + 1), 2000);
          } else {
            // Timeout - show LLM results without comparison
            console.log('⚠️  Timeout waiting for flagged results, using LLM data');
            setResults(data);
            setLoading(false);
          }
        } else if (pollCount < 120) {
          // Still waiting for initial results
          console.log(`⏳ Waiting for initial results... (poll ${pollCount + 1}/120)`);
          setTimeout(() => setPollCount((p) => p + 1), 2000);
        } else {
          // Complete timeout
          setError('Processing timeout - no results available');
          setLoading(false);
        }
      } catch (err) {
        if (pollCount < 60) {
          // Retry on error
          setTimeout(() => setPollCount((p) => p + 1), 2000);
        } else {
          setError(err instanceof Error ? err.message : 'Failed to load results');
          setLoading(false);
        }
      }
    };

    fetchResults();
  }, [uploadId, pollCount]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-blue-600 mx-auto mb-6"></div>
          <p className="text-gray-700 font-semibold text-lg">
            ⏳ Processing your documents...
          </p>
          <p className="text-gray-500 text-sm mt-2">
            This may take a minute or two. Please wait.
          </p>
          <div className="mt-6 bg-blue-50 p-4 rounded-lg max-w-md mx-auto">
            <p className="text-sm text-blue-700">
              💡 The system is performing OCR extraction and LLM analysis on your policy PDF.
            </p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center p-4">
        <div className="bg-white rounded-lg shadow-lg p-8 max-w-md text-center">
          <p className="text-red-600 font-bold text-lg mb-2">❌ Error</p>
          <p className="text-gray-600">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="mt-6 px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  if (!results) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="text-center">
          <p className="text-gray-600 font-semibold">No results available</p>
        </div>
      </div>
    );
  }

  const certificates = results.data.certificates || { property: null, gl: null };
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  const pdfUrl = selectedCert === 'property' 
    ? (certificates.property ? `${apiUrl}${certificates.property}` : null)
    : (certificates.gl ? `${apiUrl}${certificates.gl}` : null);

  // Use flagged results if available (color-coded), otherwise fall back to raw LLM results
  let propertyData = null;
  let glData = null;
  let isFlagged = false;

  console.log('🔍 Data check:', {
    hasFlaggedResults: !!results.data.flagged_results,
    flaggedResults: results.data.flagged_results,
    llmResults: results.data.llm_results
  });

  if (results.data.flagged_results && Object.keys(results.data.flagged_results).length > 0) {
    // Use flagged results (with color codes)
    console.log('✅ Using flagged results (color-coded)');
    propertyData = results.data.flagged_results.property || null;
    glData = results.data.flagged_results.gl || null;
    isFlagged = true;
  } else {
    // Fall back to raw LLM results if flagged not available yet
    console.log('⚠️  Flagged results not available, falling back to raw LLM');
    const llmData: any = results.data.llm_results || {};
    const llmResults = llmData.coverage_types || llmData;
    propertyData = llmResults.PROPERTY || null;
    glData = llmResults.GL || null;
    isFlagged = false;
  }
  
  // Check if certificates exist and are not null/empty
  const hasCertificates = Boolean(
    (certificates.property && certificates.property !== 'null') || 
    (certificates.gl && certificates.gl !== 'null')
  );

  console.log('QC Review Debug:', {
    certificates,
    hasCertificates,
    pdfUrl,
    selectedCert,
    isFlagged,
    propertyData,
    glData,
    rawData: results.data
  });

  return (
    <div className="h-screen bg-gray-100 flex flex-col">
            {/* Header */}
            <div className="bg-white border-b border-gray-200 shadow-sm p-4">
              <div className="max-w-7xl mx-auto flex justify-between items-center">
                <div>
                  <h1 className="text-2xl font-bold text-gray-900">📋 QC Review</h1>
                  <p className="text-sm text-gray-600 mt-1">
                    Upload ID: <code className="bg-gray-100 px-2 py-1 rounded">{uploadId}</code>
                  </p>
                </div>
                <div className="flex gap-3">
                  <button
                    onClick={() => window.location.href = '/dashboard'}
                    className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 font-medium transition-colors"
                  >
                    🏠 Dashboard
                  </button>
                  <button
                    onClick={() => window.location.href = '/quality-control'}
                    className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 font-medium transition-colors"
                  >
                    ← New Upload
                  </button>
                </div>
              </div>
            </div>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* LEFT PANEL: PDF Viewer (or placeholder) */}
        {hasCertificates ? (
          <div className="w-1/2 flex flex-col border-r border-gray-200">
            {/* Certificate Toggle */}
            <div className="bg-white border-b border-gray-200 p-4 flex gap-3">
              <button
                onClick={() => setSelectedCert('property')}
                className={`px-6 py-2 rounded-lg font-semibold transition-all flex items-center gap-2 ${
                  selectedCert === 'property'
                    ? 'bg-blue-600 text-white shadow-md'
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
              >
                🏠 PROPERTY
              </button>
              <button
                onClick={() => setSelectedCert('gl')}
                className={`px-6 py-2 rounded-lg font-semibold transition-all flex items-center gap-2 ${
                  selectedCert === 'gl'
                    ? 'bg-green-600 text-white shadow-md'
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
              >
                ⚖️ GL
              </button>
            </div>

            {/* PDF Viewer */}
            <div className="flex-1 overflow-hidden">
              {pdfUrl ? (
                <PDFViewer key={selectedCert} url={pdfUrl} />
              ) : (
                <div className="h-full flex items-center justify-center bg-gray-50">
                  <p className="text-gray-500">Certificate PDF not available</p>
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="w-1/2 flex flex-col border-r border-gray-200 bg-blue-50 items-center justify-center">
            <div className="text-center">
              <p className="text-xl text-blue-700 font-semibold mb-2">📄 No Certificates Uploaded</p>
              <p className="text-blue-600">Certificates are optional. Review extracted data on the right.</p>
            </div>
          </div>
        )}

        {/* RIGHT PANEL: Extracted Data */}
        <div className={`${hasCertificates ? 'w-1/2' : 'w-full'} overflow-y-auto bg-white p-6`}>
          <div className="max-w-2xl space-y-6">
            {/* Color Legend (if flagged) */}
            {isFlagged && (
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-sm">
                <p className="font-semibold text-blue-900 mb-2">🎨 Color Legend:</p>
                <div className="space-y-1 text-blue-800">
                  <p><span className="text-green-700 font-bold">🟢 Green</span> = Matches Certificate</p>
                  <p><span className="text-red-700 font-bold">🔴 Red</span> = Mismatch with Certificate</p>
                  <p><span className="text-gray-700 font-bold">⚫ Black</span> = Not in Certificate</p>
                </div>
              </div>
            )}

            {/* Property Data */}
            <ExtractedFieldsDisplay
              data={propertyData}
              title="📊 PROPERTY COVERAGE DATA"
              color="blue"
              isFlagged={isFlagged}
            />

            {/* GL Data */}
            <ExtractedFieldsDisplay
              data={glData}
              title="📊 GL COVERAGE DATA"
              color="green"
              isFlagged={isFlagged}
            />
          </div>
        </div>
      </div>
    </div>
  );
}

