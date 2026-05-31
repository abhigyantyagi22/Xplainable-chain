'use client';

import { ConnectButton } from '@rainbow-me/rainbowkit';
import { useAccount } from 'wagmi';
import Link from 'next/link';
import { Shield, Activity, FileSearch, TrendingUp, Github } from 'lucide-react';
import { ReactNode } from 'react';

export default function Home() {
  const { isConnected } = useAccount();

  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      {/* Header */}
      <header className="container mx-auto px-4 py-6 flex justify-between items-center">
        <div className="flex items-center space-x-2">
          <Shield className="w-8 h-8 text-purple-400" />
          <h1 className="text-2xl font-bold text-white">XAI-Chain</h1>
        </div>
        <div className="flex items-center space-x-4">
          <Link
            href="/dashboard"
            className="text-gray-300 hover:text-white transition"
          >
            Dashboard
          </Link>
          <ConnectButton />
        </div>
      </header>

      {/* Hero Section */}
      <section className="container mx-auto px-4 py-20 text-center">
        <h2 className="text-5xl md:text-6xl font-bold text-white mb-6">
          Explainable AI for
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-pink-600">
            {' '}Blockchain Security
          </span>
        </h2>
        <p className="text-xl text-gray-300 mb-8 max-w-2xl mx-auto">
          Detect malicious transactions with AI. Understand every decision with SHAP explanations.
          Verify everything on-chain.
        </p>
        
        <div className="flex justify-center space-x-4">
          <Link
            href="/analyze"
            className="px-8 py-4 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-semibold transition transform hover:scale-105"
          >
            Analyze Transaction
          </Link>
          <Link
            href="/dashboard"
            className="px-8 py-4 bg-gray-700 hover:bg-gray-600 text-white rounded-lg font-semibold transition transform hover:scale-105"
          >
            View Dashboard
          </Link>
        </div>

        {isConnected && (
          <div className="mt-6 inline-flex items-center px-4 py-2 bg-green-900/50 border border-green-500 rounded-lg">
            <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse mr-2" />
            <span className="text-green-300 text-sm">Wallet Connected</span>
          </div>
        )}
      </section>

      {/* Features */}
      <section className="container mx-auto px-4 py-20">
        {/* Causal XAI Highlight */}
        <div className="mb-12 bg-gradient-to-r from-purple-600 to-blue-600 rounded-2xl p-8 shadow-2xl">
          <div className="flex items-center justify-between">
            <div className="flex-1">
              <div className="inline-block px-3 py-1 bg-white/20 rounded-full text-white text-sm font-semibold mb-3">
                🔬 RESEARCH FEATURE
              </div>
              <h3 className="text-3xl font-bold text-white mb-3">Causal Explainable AI</h3>
              <p className="text-purple-100 text-lg mb-4">
                First-ever causal inference for blockchain fraud detection. Go beyond correlation 
                to identify true cause-and-effect relationships. Detect spurious correlations and confounders.
              </p>
              <Link
                href="/analyze/causal"
                className="inline-block px-8 py-3 bg-white text-purple-600 font-bold rounded-lg hover:bg-purple-50 transition-all transform hover:scale-105"
              >
                Explore Causal XAI →
              </Link>
            </div>
          </div>
        </div>

        <div className="grid md:grid-cols-4 gap-8">
        <Link href="/prevent" className="group">
          <div className="bg-gradient-to-br from-green-600 to-blue-600 rounded-xl p-6 shadow-xl hover:shadow-2xl transition-all transform hover:scale-105 border-2 border-green-400">
            <div className="flex items-center justify-between mb-4">
              <Shield className="w-12 h-12 text-white" />
              <span className="px-3 py-1 bg-white text-green-700 text-xs font-bold rounded-full">NEW</span>
            </div>
            <h3 className="text-xl font-bold text-white mb-2">Check Before Send</h3>
            <p className="text-green-50 text-sm">Prevent fraud by checking BEFORE you sign</p>
            <div className="mt-4 text-white text-xs font-semibold">
              ✅ RECOMMENDED →
            </div>
          </div>
        </Link>
        <FeatureCard
          icon={<Activity className="w-12 h-12 text-purple-400" />}
          title="Real-time Detection"
          description="AI-powered anomaly detection analyzes transactions in seconds"
        />
        <FeatureCard
          icon={<FileSearch className="w-12 h-12 text-pink-400" />}
          title="Explainable AI"
          description="SHAP values show exactly why each transaction was flagged"
        />
        <FeatureCard
          icon={<TrendingUp className="w-12 h-12 text-blue-400" />}
          title="On-Chain Verification"
          description="Explanations stored immutably on Polygon for transparency"
        />
        </div>
      </section>

      {/* Stats */}
      <section className="container mx-auto px-4 py-20">
        <div className="bg-gray-800/50 backdrop-blur-lg rounded-2xl p-8 grid md:grid-cols-4 gap-8 text-center">
          <StatCard label="Detection Accuracy" value="94%" />
          <StatCard label="Avg Analysis Time" value="8s" />
          <StatCard label="Transactions Analyzed" value="1,247" />
          <StatCard label="Gas Cost per Entry" value="0.001 MATIC" />
        </div>
      </section>

      {/* Footer */}
      <footer className="container mx-auto px-4 py-8 border-t border-gray-800">
        <div className="flex justify-between items-center">
          <p className="text-gray-400 text-sm">
            © 2025 XAI-Chain. Built with Next.js, FastAPI, and Web3.
          </p>
          <a
            href="https://github.com/yourusername/xai-chain"
            target="_blank"
            rel="noopener noreferrer"
            className="text-gray-400 hover:text-white transition"
          >
            <Github className="w-6 h-6" />
          </a>
        </div>
      </footer>
    </main>
  );
}

interface FeatureCardProps {
  icon: ReactNode;
  title: string;
  description: string;
}

function FeatureCard({ icon, title, description }: FeatureCardProps) {
  return (
    <div className="bg-gray-800/50 backdrop-blur-lg rounded-xl p-6 hover:bg-gray-800/70 transition transform hover:scale-105">
      <div className="mb-4">{icon}</div>
      <h3 className="text-xl font-bold text-white mb-2">{title}</h3>
      <p className="text-gray-400">{description}</p>
    </div>
  );
}

interface StatCardProps {
  label: string;
  value: string;
}

function StatCard({ label, value }: StatCardProps) {
  return (
    <div>
      <div className="text-4xl font-bold text-purple-400 mb-2">{value}</div>
      <div className="text-gray-400">{label}</div>
    </div>
  );
}
