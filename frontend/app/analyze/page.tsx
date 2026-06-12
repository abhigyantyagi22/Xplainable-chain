'use client';

import { useState } from 'react';
import { useAccount } from 'wagmi';
import Link from 'next/link';
import { Loader2, AlertTriangle, CheckCircle, ShieldAlert, ArrowRight } from 'lucide-react';
import { apiPost } from '@/lib/api';
import Reveal from '@/components/Reveal';

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
    <div className="mx-auto max-w-3xl px-4 py-12 sm:px-6">
      <div className="mb-2 animate-enter">
        <h1 className="text-3xl font-bold tracking-tight text-slate-900">Analyze a transaction</h1>
        <p className="mt-2 text-slate-600">
          Enter a confirmed transaction hash to assess its fraud risk and see the explanation.
        </p>
      </div>

      {/* Causal AI cross-link */}
      <Link
        href="/analyze/causal"
        className="lift tappable mt-6 flex items-center justify-between rounded-xl border border-slate-200 bg-white p-4 shadow-sm hover:shadow-md"
      >
        <div>
          <p className="text-sm font-semibold text-slate-900">Want deeper insight?</p>
          <p className="text-sm text-slate-600">Try Causal AI to see true cause-and-effect, not just correlation.</p>
        </div>
        <span className="inline-flex items-center gap-1 text-sm font-semibold text-indigo-600">
          Causal AI <ArrowRight className="h-4 w-4" />
        </span>
      </Link>

      {/* Form */}
      <Reveal className="mt-6 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
        <div className="space-y-5">
          <div>
            <label className="mb-1.5 block text-sm font-medium text-slate-700">Blockchain network</label>
            <select
              value={network}
              onChange={(e) => setNetwork(e.target.value as any)}
              className="w-full rounded-lg border border-slate-300 bg-white px-4 py-2.5 text-slate-900 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            >
              <option value="ethereum">Ethereum Mainnet</option>
              <option value="polygon">Polygon Mainnet</option>
              <option value="polygon-amoy">Polygon Amoy Testnet</option>
            </select>
          </div>

          <div>
            <label className="mb-1.5 block text-sm font-medium text-slate-700">Transaction hash</label>
            <input
              type="text"
              value={txHash}
              onChange={(e) => setTxHash(e.target.value)}
              placeholder="0x5c504ed432cb51138bcf09aa5e8a410dd4a1e204ef84bfed1be16dfba1b22060"
              className="w-full rounded-lg border border-slate-300 bg-white px-4 py-2.5 font-mono text-sm text-slate-900 placeholder-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
          </div>

          <button
            onClick={analyzeTx}
            disabled={loading || !isConnected}
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-indigo-600 px-6 py-3 text-sm font-semibold text-white transition-colors hover:bg-indigo-700 disabled:cursor-not-allowed disabled:bg-slate-300"
          >
            {loading ? (
              <><Loader2 className="h-4 w-4 animate-spin" /><span>Analyzing…</span></>
            ) : (
              <span>Analyze transaction</span>
            )}
          </button>

          {!isConnected && (
            <p className="text-center text-sm text-amber-600">
              Connect your wallet to analyze transactions.
            </p>
          )}

          {error && (
            <div className="flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 p-4">
              <AlertTriangle className="mt-0.5 h-5 w-5 flex-shrink-0 text-red-500" />
              <p className="text-sm text-red-700">{error}</p>
            </div>
          )}
        </div>
      </Reveal>

      {/* Result */}
      {result && (
        <Reveal className="mt-6 space-y-4">
          {screening?.flagged && (
            <div className="flex items-start gap-3 rounded-xl border border-red-300 bg-red-50 p-4">
              <ShieldAlert className="mt-0.5 h-6 w-6 flex-shrink-0 text-red-500" />
              <div>
                <p className="font-semibold text-red-800">
                  {isOFAC ? 'OFAC Sanctioned Address' : 'Threat Intelligence Flag'}
                </p>
                <p className="mt-1 text-sm text-red-700">{screening.detail}</p>
                <p className="mt-1 text-xs uppercase tracking-wide text-red-500">
                  Source: {screening.source} — ML inference skipped
                </p>
              </div>
            </div>
          )}

          <div
            className={`rounded-2xl border p-6 ${
              result.is_malicious ? 'border-red-200 bg-red-50' : 'border-emerald-200 bg-emerald-50'
            }`}
          >
            <div className="flex items-center gap-3">
              {result.is_malicious
                ? <AlertTriangle className="h-8 w-8 text-red-500" />
                : <CheckCircle className="h-8 w-8 text-emerald-500" />}
              <div>
                <h3 className="text-xl font-bold text-slate-900">
                  {result.is_malicious ? 'Malicious transaction' : 'Legitimate transaction'}
                </h3>
                <p className="text-sm text-slate-600">Risk score: {result.risk_score}/100</p>
              </div>
            </div>

            <div className="mt-5 grid grid-cols-2 gap-4">
              <div>
                <p className="text-xs text-slate-500">Fraud probability</p>
                <p className="font-semibold text-slate-900">{(result.confidence * 100).toFixed(1)}%</p>
              </div>
              <div>
                <p className="text-xs text-slate-500">Transaction hash</p>
                <p className="truncate font-mono text-xs text-slate-700">{result.tx_hash}</p>
              </div>
              {result.ipfs_hash && (
                <div>
                  <p className="text-xs text-slate-500">IPFS storage</p>
                  <p className="font-mono text-xs text-indigo-600">{result.ipfs_hash}</p>
                </div>
              )}
              {result.blockchain_hash && (
                <div>
                  <p className="text-xs text-slate-500">On-chain hash</p>
                  <p className="truncate font-mono text-xs text-indigo-600">{result.blockchain_hash}</p>
                </div>
              )}
            </div>

            {result.explanation?.top_features?.length > 0 && (
              <div className="mt-5 border-t border-slate-200 pt-4">
                <p className="mb-2 text-xs font-medium text-slate-500">Top risk factors (SHAP)</p>
                <div className="space-y-1.5">
                  {result.explanation.top_features.slice(0, 3).map((f: any) => (
                    <div key={f.feature} className="flex justify-between text-sm">
                      <span className="text-slate-700">{f.feature}</span>
                      <span className={f.importance > 0 ? 'font-medium text-red-600' : 'font-medium text-emerald-600'}>
                        {f.importance > 0 ? '+' : ''}{(f.importance * 100).toFixed(1)}%
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </Reveal>
      )}
    </div>
  );
}
