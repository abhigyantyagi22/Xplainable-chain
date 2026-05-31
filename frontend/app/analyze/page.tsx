'use client';

import { useState } from 'react';
import { ConnectButton } from '@rainbow-me/rainbowkit';
import { useAccount } from 'wagmi';
import Link from 'next/link';
import { Shield, ArrowLeft, Loader2, AlertTriangle, CheckCircle, ShieldAlert } from 'lucide-react';
import { apiPost } from '@/lib/api';

export default function AnalyzePage() {
  const { isConnected } = useAccount();
  const [txHash, setTxHash]   = useState('');
  const [network, setNetwork] = useState<'ethereum' | 'polygon' | 'polygon-amoy'>('ethereum');
  const [loading, setLoading] = useState(false);
  const [result, setResult]   = useState<any>(null);
  const [error, setError]     = useState('');

  const analyzeTx = async () => {
    if (!txHash) { setError('Please enter a transaction hash'); return; }
    setLoading(true); setError(''); setResult(null);
    try {
      const data = await apiPost('/api/analyze/', { tx_hash: txHash, network });
      setResult(data);
    } catch (err: any) {
      setError(err.message || 'Failed to analyze transaction');
    } finally {
      setLoading(false);
    }
  };

  const screening = result?.explanation?.screening;
  const isOFAC    = screening?.source === 'ofac';

  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      <header className="container mx-auto px-4 py-6 flex justify-between items-center">
        <div className="flex items-center space-x-4">
          <Link href="/" className="text-gray-300 hover:text-white transition">
            <ArrowLeft className="w-6 h-6" />
          </Link>
          <Shield className="w-8 h-8 text-purple-400" />
          <h1 className="text-2xl font-bold text-white">Analyze Transaction</h1>
        </div>
        <ConnectButton />
      </header>

      <section className="container mx-auto px-4 py-12 max-w-4xl">
        <div className="mb-6 bg-gradient-to-r from-purple-600 to-blue-600 rounded-xl p-6 shadow-lg">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-xl font-bold text-white mb-2">Causal Explainable AI</h3>
              <p className="text-purple-100 text-sm">Go beyond correlation with causal inference.</p>
            </div>
            <Link
              href="/analyze/causal"
              className="px-6 py-3 bg-white text-purple-600 font-semibold rounded-lg hover:bg-purple-50 transition-colors whitespace-nowrap"
            >
              Try Causal XAI →
            </Link>
          </div>
        </div>

        <div className="bg-gray-800/50 backdrop-blur-lg rounded-2xl p-8">
          <h2 className="text-3xl font-bold text-white mb-6">Transaction Analysis</h2>

          <div className="space-y-6">
            <div>
              <label className="block text-gray-300 mb-2 font-medium">Blockchain Network</label>
              <select
                value={network}
                onChange={(e) => setNetwork(e.target.value as any)}
                className="w-full px-4 py-3 bg-gray-900 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-purple-500"
              >
                <option value="ethereum">Ethereum Mainnet</option>
                <option value="polygon">Polygon Mainnet</option>
                <option value="polygon-amoy">Polygon Amoy Testnet</option>
              </select>
            </div>

            <div>
              <label className="block text-gray-300 mb-2 font-medium">Transaction Hash</label>
              <input
                type="text"
                value={txHash}
                onChange={(e) => setTxHash(e.target.value)}
                placeholder="0x5c504ed432cb51138bcf09aa5e8a410dd4a1e204ef84bfed1be16dfba1b22060"
                className="w-full px-4 py-3 bg-gray-900 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-purple-500"
              />
            </div>

            <button
              onClick={analyzeTx}
              disabled={loading || !isConnected}
              className="w-full px-6 py-4 bg-purple-600 hover:bg-purple-700 disabled:bg-gray-700 disabled:cursor-not-allowed text-white rounded-lg font-semibold transition flex items-center justify-center space-x-2"
            >
              {loading ? (
                <><Loader2 className="w-5 h-5 animate-spin" /><span>Analyzing...</span></>
              ) : (
                <span>Analyze Transaction</span>
              )}
            </button>

            {!isConnected && (
              <p className="text-yellow-400 text-sm text-center">
                Please connect your wallet to analyze transactions
              </p>
            )}

            {error && (
              <div className="p-4 bg-red-900/20 border border-red-500 rounded-lg flex items-start space-x-3">
                <AlertTriangle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
                <p className="text-red-300">{error}</p>
              </div>
            )}

            {result && (
              <div className="space-y-4">
                {/* OFAC / enrichment screening badge */}
                {screening?.flagged && (
                  <div className="p-4 bg-red-950/60 border-2 border-red-500 rounded-lg flex items-start space-x-3">
                    <ShieldAlert className="w-6 h-6 text-red-400 flex-shrink-0 mt-0.5" />
                    <div>
                      <p className="text-red-300 font-semibold">
                        {isOFAC ? 'OFAC Sanctioned Address' : 'Threat Intelligence Flag'}
                      </p>
                      <p className="text-red-400 text-sm mt-1">{screening.detail}</p>
                      <p className="text-red-500 text-xs mt-1 uppercase tracking-wide">
                        Source: {screening.source} — ML inference skipped
                      </p>
                    </div>
                  </div>
                )}

                {/* Main result */}
                <div className={`p-6 rounded-lg border ${
                  result.is_malicious ? 'bg-red-900/20 border-red-500' : 'bg-green-900/20 border-green-500'
                }`}>
                  <div className="flex items-center space-x-3 mb-4">
                    {result.is_malicious
                      ? <AlertTriangle className="w-8 h-8 text-red-400" />
                      : <CheckCircle className="w-8 h-8 text-green-400" />}
                    <div>
                      <h3 className="text-2xl font-bold text-white">
                        {result.is_malicious ? 'Malicious Transaction' : 'Legitimate Transaction'}
                      </h3>
                      <p className="text-sm text-gray-300">Risk Score: {result.risk_score}/100</p>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4 mt-4">
                    <div>
                      <p className="text-gray-400 text-sm">Fraud Probability:</p>
                      <p className="text-white font-semibold">{(result.confidence * 100).toFixed(1)}%</p>
                    </div>
                    <div>
                      <p className="text-gray-400 text-sm">Transaction Hash:</p>
                      <p className="text-white font-mono text-xs truncate">{result.tx_hash}</p>
                    </div>
                    {result.ipfs_hash && (
                      <div>
                        <p className="text-gray-400 text-sm">IPFS Storage:</p>
                        <p className="text-purple-400 font-mono text-xs">{result.ipfs_hash}</p>
                      </div>
                    )}
                    {result.blockchain_hash && (
                      <div>
                        <p className="text-gray-400 text-sm">On-chain Hash:</p>
                        <p className="text-purple-400 font-mono text-xs truncate">{result.blockchain_hash}</p>
                      </div>
                    )}
                  </div>

                  {/* Top SHAP features */}
                  {result.explanation?.top_features?.length > 0 && (
                    <div className="mt-4 pt-4 border-t border-gray-700">
                      <p className="text-gray-400 text-sm mb-2">Top Risk Factors (SHAP):</p>
                      <div className="space-y-1">
                        {result.explanation.top_features.slice(0, 3).map((f: any) => (
                          <div key={f.feature} className="flex justify-between text-sm">
                            <span className="text-gray-300">{f.feature}</span>
                            <span className={f.importance > 0 ? 'text-red-400' : 'text-green-400'}>
                              {f.importance > 0 ? '+' : ''}{(f.importance * 100).toFixed(1)}%
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </section>
    </main>
  );
}
