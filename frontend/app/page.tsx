'use client';

import Link from 'next/link';
import { useAuth } from '@/context/AuthContext';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

export default function Home() {
  const { isLoggedIn } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (isLoggedIn) {
      router.push('/dashboard');
    }
  }, [isLoggedIn, router]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-900 via-purple-900 to-pink-800 flex flex-col">
      {/* Header */}
      <header className="w-full py-6 px-8">
        <h1 className="text-3xl font-bold text-white tracking-wide">Mckinney and Co</h1>
      </header>

      {/* Main Content - Centered Button */}
      <main className="flex-1 flex items-center justify-center">
        <Link href="/login">
          <button className="px-8 py-4 bg-white text-indigo-900 rounded-full font-semibold text-lg hover:bg-indigo-100 hover:scale-110 transition-all duration-300 shadow-2xl hover:shadow-white/50">
            Click to Continue
          </button>
        </Link>
      </main>
    </div>
  );
}
