'use client';

import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { useEffect, useState } from 'react';
import Link from 'next/link';

interface CarrierData {
  id: number;
  name: string;
  propertyPDF: { file: File | null; name: string };
  liabilityPDF: { file: File | null; name: string };
}

export default function SummaryPage() {
  const { user, isLoggedIn } = useAuth();
  const router = useRouter();
  const [carriers, setCarriers] = useState<CarrierData[]>([
    { id: 1, name: '', propertyPDF: { file: null, name: '' }, liabilityPDF: { file: null, name: '' } }
  ]);
  const [nextId, setNextId] = useState(2);
  const [isExecuting, setIsExecuting] = useState(false);

  useEffect(() => {
    if (!isLoggedIn) {
      router.push('/login');
    }
  }, [isLoggedIn, router]);

  const addCarrier = () => {
    const newCarrier: CarrierData = {
      id: nextId,
      name: '',
      propertyPDF: { file: null, name: '' },
      liabilityPDF: { file: null, name: '' }
    };
    setCarriers([...carriers, newCarrier]);
    setNextId(nextId + 1);
  };

  const removeCarrier = (id: number) => {
    if (carriers.length > 1) {
      setCarriers(carriers.filter(c => c.id !== id));
    } else {
      alert('You must have at least one carrier');
    }
  };

  const handleNameChange = (id: number, value: string) => {
    setCarriers(carriers.map(c => (c.id === id ? { ...c, name: value } : c)));
  };

  const handleFileUpload = (id: number, type: 'property' | 'liability', file: File) => {
    setCarriers(
      carriers.map(c => {
        if (c.id === id) {
          if (type === 'property') {
            return { ...c, propertyPDF: { file, name: file.name } };
          } else {
            return { ...c, liabilityPDF: { file, name: file.name } };
          }
        }
        return c;
      })
    );
  };

  const handleExecute = () => {
    // Validate all carriers have names and files
    const isValid = carriers.every(
      c => c.name.trim() && c.propertyPDF.file && c.liabilityPDF.file
    );

    if (!isValid) {
      alert('Please fill in all carrier names and upload both PDFs for each carrier');
      return;
    }

    setIsExecuting(true);

    // Log data to console for now
    const submitData = carriers.map(c => ({
      carrierName: c.name,
      propertyPDF: c.propertyPDF.name,
      liabilityPDF: c.liabilityPDF.name,
      propertySize: c.propertyPDF.file?.size,
      liabilitySize: c.liabilityPDF.file?.size
    }));

    console.log('Submitting Carriers:', submitData);
    alert(`Successfully submitted ${carriers.length} carrier(s)!\nCheck console for details.`);

    setIsExecuting(false);
  };

  if (!isLoggedIn || !user) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-indigo-900 via-purple-900 to-pink-800 flex items-center justify-center">
        <p className="text-white">Loading...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-900 via-purple-900 to-pink-800 flex flex-col">
      {/* Header */}
      <header className="bg-black/20 backdrop-blur-md border-b border-white/10">
        <div className="max-w-7xl mx-auto px-8 py-6 flex justify-between items-center">
          <h1 className="text-3xl font-bold text-white">Mckinney and Co</h1>
          <Link href="/dashboard">
            <button className="px-6 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg font-semibold transition-colors">
              Back to Dashboard
            </button>
          </Link>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-6xl mx-auto w-full px-8 py-12">
        <div className="space-y-8">
          {/* Title Section */}
          <div className="text-center">
            <h2 className="text-4xl font-bold text-white mb-2">Multi-Carrier Quote Upload</h2>
            <p className="text-white/80">Upload insurance quotes for multiple carriers and lines</p>
          </div>

          {/* Carriers Container */}
          <div className="space-y-6">
            {carriers.map((carrier, index) => (
              <div key={carrier.id} className="bg-white/10 backdrop-blur-md rounded-2xl p-8 border border-white/20">
                {/* Carrier Header */}
                <div className="flex justify-between items-center mb-6">
                  <h3 className="text-2xl font-bold text-white">Carrier {index + 1}</h3>
                  {carriers.length > 1 && (
                    <button
                      onClick={() => removeCarrier(carrier.id)}
                      className="px-4 py-2 bg-red-500/20 hover:bg-red-500/30 border border-red-500/50 text-red-200 rounded-lg font-semibold transition-colors"
                    >
                      ✕ Remove
                    </button>
                  )}
                </div>

                {/* Carrier Name Input */}
                <div className="mb-8">
                  <label className="block text-white font-medium mb-3">Carrier Name</label>
                  <input
                    type="text"
                    value={carrier.name}
                    onChange={(e) => handleNameChange(carrier.id, e.target.value)}
                    placeholder="e.g., State Farm, Allstate, GEICO"
                    className="w-full px-4 py-3 rounded-lg bg-white/20 border border-white/30 text-white placeholder-white/60 focus:outline-none focus:ring-2 focus:ring-white/50"
                  />
                </div>

                {/* PDF Upload Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* Property PDF */}
                  <div>
                    <label className="block text-white font-medium mb-3">Property PDF</label>
                    <div className="relative">
                      <input
                        type="file"
                        accept=".pdf"
                        onChange={(e) => {
                          if (e.target.files?.[0]) {
                            handleFileUpload(carrier.id, 'property', e.target.files[0]);
                          }
                        }}
                        className="absolute inset-0 opacity-0 cursor-pointer"
                      />
                      <div className="border-2 border-dashed border-white/30 rounded-xl p-8 hover:border-white/50 transition cursor-pointer bg-white/5 hover:bg-white/10">
                        <div className="text-center">
                          {carrier.propertyPDF.file ? (
                            <>
                              <p className="text-green-300 font-medium">✓ {carrier.propertyPDF.name}</p>
                              <p className="text-white/60 text-sm mt-1">{(carrier.propertyPDF.file.size / 1024).toFixed(2)} KB</p>
                            </>
                          ) : (
                            <>
                              <p className="text-white/80 font-medium">📄 Click to upload PDF</p>
                              <p className="text-white/60 text-sm mt-1">Property Quote</p>
                            </>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* General Liability PDF */}
                  <div>
                    <label className="block text-white font-medium mb-3">General Liability PDF</label>
                    <div className="relative">
                      <input
                        type="file"
                        accept=".pdf"
                        onChange={(e) => {
                          if (e.target.files?.[0]) {
                            handleFileUpload(carrier.id, 'liability', e.target.files[0]);
                          }
                        }}
                        className="absolute inset-0 opacity-0 cursor-pointer"
                      />
                      <div className="border-2 border-dashed border-white/30 rounded-xl p-8 hover:border-white/50 transition cursor-pointer bg-white/5 hover:bg-white/10">
                        <div className="text-center">
                          {carrier.liabilityPDF.file ? (
                            <>
                              <p className="text-green-300 font-medium">✓ {carrier.liabilityPDF.name}</p>
                              <p className="text-white/60 text-sm mt-1">{(carrier.liabilityPDF.file.size / 1024).toFixed(2)} KB</p>
                            </>
                          ) : (
                            <>
                              <p className="text-white/80 font-medium">📄 Click to upload PDF</p>
                              <p className="text-white/60 text-sm mt-1">General Liability Quote</p>
                            </>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Upload Status */}
                <div className="mt-6 flex gap-4 text-sm">
                  <div className="flex items-center gap-2">
                    <span className={carrier.name.trim() ? '✓ text-green-300' : '○ text-white/60'}>Carrier Name</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={carrier.propertyPDF.file ? '✓ text-green-300' : '○ text-white/60'}>Property PDF</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={carrier.liabilityPDF.file ? '✓ text-green-300' : '○ text-white/60'}>Liability PDF</span>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Action Buttons */}
          <div className="flex gap-4">
            <button
              onClick={addCarrier}
              className="flex-1 px-6 py-3 bg-white/20 hover:bg-white/30 text-white rounded-lg font-semibold transition-colors border border-white/30"
            >
              + Add More Carrier
            </button>
            <button
              onClick={handleExecute}
              disabled={isExecuting}
              className="flex-1 px-6 py-3 bg-white text-indigo-900 rounded-lg font-semibold hover:bg-white/90 transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {isExecuting ? (
                <>
                  <span className="animate-spin">⏳</span>
                  Executing...
                </>
              ) : (
                <>
                  <span>✓</span>
                  Execute
                </>
              )}
            </button>
          </div>

          {/* Summary Stats */}
          <div className="bg-white/5 backdrop-blur-md rounded-2xl p-6 border border-white/20">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="text-center">
                <p className="text-white/60 text-sm mb-1">Total Carriers</p>
                <p className="text-3xl font-bold text-white">{carriers.length}</p>
              </div>
              <div className="text-center">
                <p className="text-white/60 text-sm mb-1">Complete Carriers</p>
                <p className="text-3xl font-bold text-green-300">
                  {carriers.filter(c => c.name.trim() && c.propertyPDF.file && c.liabilityPDF.file).length}
                </p>
              </div>
              <div className="text-center">
                <p className="text-white/60 text-sm mb-1">Total Files Uploaded</p>
                <p className="text-3xl font-bold text-white">
                  {carriers.reduce((acc, c) => acc + (c.propertyPDF.file ? 1 : 0) + (c.liabilityPDF.file ? 1 : 0), 0)}
                </p>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
