'use client';

import Link from 'next/link';

export default function Home() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-900 via-purple-900 to-pink-800 flex flex-col">
      {/* Header */}
      <header className="w-full py-6 px-8">
        <h1 className="text-3xl font-bold text-white tracking-wide">Mckinney and Co</h1>
      </header>

      {/* Main Content - Centered Button */}
      <main className="flex-1 flex items-center justify-center">
        <Link href="/homepage">
          <button className="px-8 py-4 bg-white text-indigo-900 rounded-full font-semibold text-lg hover:bg-indigo-100 hover:scale-110 transition-all duration-300 shadow-2xl hover:shadow-white/50">
            Click to Continue
          </button>
        </Link>
      </main>
    </div>
  );
}
