'use client';

import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { useEffect } from 'react';
import Link from 'next/link';

export default function DashboardPage() {
  const { user, isLoggedIn, logout } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoggedIn) {
      router.push('/login');
    }
  }, [isLoggedIn, router]);

  const handleLogout = () => {
    logout();
    router.push('/');
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
          <button
            onClick={handleLogout}
            className="px-6 py-2 bg-red-500 hover:bg-red-600 text-white rounded-lg font-semibold transition-colors"
          >
            Logout
          </button>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-7xl mx-auto w-full px-8 py-12">
        <div className="bg-white/10 backdrop-blur-md rounded-2xl p-8 border border-white/20">
          {/* Welcome Section */}
          <div className="mb-8">
            <h2 className="text-4xl font-bold text-white mb-2">Welcome!</h2>
            <p className="text-white/80 text-lg">
              Logged in as: <span className="font-semibold text-white">{user.username}</span>
            </p>
          </div>

          {/* Dashboard Content - Reordered per requirements */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Card 1: Convenience Store E-FORM (Agent Application Form) - CLICKABLE */}
            <Link href="/cstore">
              <div className="bg-gradient-to-br from-white/10 to-white/5 border border-white/30 rounded-lg p-6 hover:from-white/15 hover:to-white/10 transition cursor-pointer h-full">
                <h3 className="text-xl font-semibold text-white mb-3">🏪 Convenience Store E-FORM ( Agent Application Form )</h3>
                <p className="text-white/70">
                  Complete insurance application form with automated data prefill from property databases.
                </p>
                <div className="mt-4 text-white/60 text-sm flex items-center gap-2">
                  <span>Click to start →</span>
                </div>
              </div>
            </Link>

            {/* Card 2: Convenience Store E-FORM (Client Application Form) - CLICKABLE */}
            <Link href="/client-form">
              <div className="bg-gradient-to-br from-white/10 to-white/5 border border-white/30 rounded-lg p-6 hover:from-white/15 hover:to-white/10 transition cursor-pointer h-full">
                <h3 className="text-xl font-semibold text-white mb-3">📋 Convenience Store E-FORM ( Client Application Form )</h3>
                <p className="text-white/70">
                  Complete insurance application form with automated data prefill and CRM integration.
                </p>
                <div className="mt-4 text-white/60 text-sm flex items-center gap-2">
                  <span>Click to start →</span>
                </div>
              </div>
            </Link>

            {/* Card 3: Cover Sheet - CLICKABLE (External Link) */}
            <a 
              href="https://carrier-submission-tracker-system-for-insurance-production.up.railway.app/login" 
              target="_blank" 
              rel="noopener noreferrer"
            >
              <div className="bg-gradient-to-br from-white/10 to-white/5 border border-white/30 rounded-lg p-6 hover:from-white/15 hover:to-white/10 transition cursor-pointer h-full">
                <h3 className="text-xl font-semibold text-white mb-3">📄 Cover Sheet</h3>
                <p className="text-white/70">
                  Get help and support for your insurance document analysis.
                </p>
                <div className="mt-4 text-white/60 text-sm flex items-center gap-2">
                  <span>Click to start →</span>
                </div>
              </div>
            </a>

            {/* Card 4: Generate Summary - CLICKABLE */}
            <Link href="/summary">
              <div className="bg-gradient-to-br from-white/10 to-white/5 border border-white/30 rounded-lg p-6 hover:from-white/15 hover:to-white/10 transition cursor-pointer h-full">
                <h3 className="text-xl font-semibold text-white mb-3">📝 Generate Summary</h3>
                <p className="text-white/70">
                  Upload insurance documents and get AI-powered summaries with key information extraction.
                </p>
                <div className="mt-4 text-white/60 text-sm flex items-center gap-2">
                  <span>Click to start →</span>
                </div>
              </div>
            </Link>

            {/* Card 5: Quality Control / Comparison sheet - CLICKABLE */}
            <Link href="/quality-control">
              <div className="bg-gradient-to-br from-white/10 to-white/5 border border-white/30 rounded-lg p-6 hover:from-white/15 hover:to-white/10 transition cursor-pointer h-full">
                <h3 className="text-xl font-semibold text-white mb-3">✅ Quality Control / Comparison sheet</h3>
                <p className="text-white/70">
                  Manage your account settings and preferences.
                </p>
                <div className="mt-4 text-white/60 text-sm flex items-center gap-2">
                  <span>Click to start →</span>
                </div>
              </div>
            </Link>
          </div>
        </div>
      </main>
    </div>
  );
}
