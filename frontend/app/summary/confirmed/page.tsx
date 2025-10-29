'use client';

import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { useEffect, useState } from 'react';
import Link from 'next/link';

export default function ConfirmedPage() {
  const { user, isLoggedIn } = useAuth();
  const router = useRouter();
  const [isHydrated, setIsHydrated] = useState(false);

  useEffect(() => {
    // Mark as hydrated after first render
    setIsHydrated(true);
  }, []);

  useEffect(() => {
    if (!isLoggedIn && isHydrated) {
      router.push('/login');
    }
  }, [isLoggedIn, isHydrated, router]);

  if (!isHydrated) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-indigo-900 via-purple-900 to-pink-800 flex items-center justify-center">
        <p className="text-white">Loading...</p>
      </div>
    );
  }

  if (!isLoggedIn || !user) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-indigo-900 via-purple-900 to-pink-800 flex items-center justify-center">
        <p className="text-white">Redirecting to login...</p>
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
      <main className="flex-1 max-w-6xl mx-auto w-full px-8 py-12 flex items-center justify-center">
        <div className="text-center">
          <div className="text-6xl mb-6">✓</div>
          <h2 className="text-4xl font-bold text-white mb-4">Execution Confirmed!</h2>
          <p className="text-white/80 text-xl mb-8">Your files have been successfully processed and stored.</p>
          <Link href="/dashboard">
            <button className="px-8 py-3 bg-white text-indigo-900 rounded-lg font-semibold hover:bg-white/90 transition-colors">
              Return to Dashboard
            </button>
          </Link>
        </div>
      </main>
    </div>
  );
}
