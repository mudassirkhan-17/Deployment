'use client';

import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { useEffect } from 'react';

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
              Logged in as: <span className="font-semibold text-white">{user.email}</span>
            </p>
            <p className="text-white/60 text-sm mt-2">User ID: {user.user_id}</p>
          </div>

          {/* Dashboard Content */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Feature Card 1 */}
            <div className="bg-white/5 border border-white/20 rounded-lg p-6 hover:bg-white/10 transition">
              <h3 className="text-xl font-semibold text-white mb-3">Upload Documents</h3>
              <p className="text-white/70">
                Upload PDF documents for analysis and processing.
              </p>
            </div>

            {/* Feature Card 2 */}
            <div className="bg-white/5 border border-white/20 rounded-lg p-6 hover:bg-white/10 transition">
              <h3 className="text-xl font-semibold text-white mb-3">View History</h3>
              <p className="text-white/70">
                View your previously uploaded and processed documents.
              </p>
            </div>

            {/* Feature Card 3 */}
            <div className="bg-white/5 border border-white/20 rounded-lg p-6 hover:bg-white/10 transition">
              <h3 className="text-xl font-semibold text-white mb-3">API Integration</h3>
              <p className="text-white/70">
                Integrate with our API for automated document processing.
              </p>
            </div>

            {/* Feature Card 4 */}
            <div className="bg-white/5 border border-white/20 rounded-lg p-6 hover:bg-white/10 transition">
              <h3 className="text-xl font-semibold text-white mb-3">Settings</h3>
              <p className="text-white/70">
                Manage your account settings and preferences.
              </p>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
