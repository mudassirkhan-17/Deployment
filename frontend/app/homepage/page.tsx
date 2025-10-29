export default function HomePage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-900 via-purple-900 to-pink-800 flex flex-col">
      {/* Header */}
      <header className="w-full py-6 px-8">
        <h1 className="text-3xl font-bold text-white tracking-wide">Mckinney and Co</h1>
      </header>

      {/* Main Content */}
      <main className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-4xl font-bold text-white mb-4">Welcome to Homepage</h2>
          <p className="text-white/80 text-lg">This is your homepage content</p>
        </div>
      </main>
    </div>
  );
}

