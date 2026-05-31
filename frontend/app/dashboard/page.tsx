'use client';

import { useState, useEffect } from 'react';
import { ConnectButton } from '@rainbow-me/rainbowkit';
import Link from 'next/link';
import { Shield, ArrowLeft, TrendingUp, AlertTriangle, Activity, Clock, Zap } from 'lucide-react';
import { apiGet } from '@/lib/api';

export default function DashboardPage() {
  const [stats, setStats]           = useState<any>(null);
  const [transactions, setTransactions] = useState<any[]>([]);
  const [metrics, setMetrics]        = useState<any>(null);
  const [alert, setAlert]            = useState<any>(null);
  const [loading, setLoading]        = useState(true);

  useEffect(() => { fetchDashboardData(); }, []);

  const fetchDashboardData = async () => {
    try {
      // Audit trail
      const data: any = await apiGet('/api/audit/');
      const trail = data.audit_trail || [];
      setTransactions(trail);

      const totalTx    = trail.length;
      const malicious  = trail.filter((tx: any) => tx.is_malicious).length;
      const avgRisk    = totalTx > 0
        ? trail.reduce((s: number, tx: any) => s + tx.risk_score, 0) / totalTx
        : 0;
      setStats({ total: totalTx, malicious, legitimate: totalTx - malicious, avgRisk: avgRisk.toFixed(1) });

      // Live metrics (best-effort — no crash if unavailable)
      try {
        const m: any = await apiGet('/api/metrics');
        setMetrics(m);
        setAlert(m.alert);
      } catch { /* metrics unavailable — silently skip */ }
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      {/* Header */}
      <header className="container mx-auto px-4 py-6 flex justify-between items-center">
        <div className="flex items-center space-x-4">
          <Link href="/" className="text-gray-300 hover:text-white transition">
            <ArrowLeft className="w-6 h-6" />
          </Link>
          <Shield className="w-8 h-8 text-purple-400" />
          <h1 className="text-2xl font-bold text-white">Dashboard</h1>
        </div>
        <ConnectButton />
      </header>

      {/* Main Content */}
      <section className="container mx-auto px-4 py-12">
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="text-white text-xl">Loading dashboard...</div>
          </div>
        ) : (
          <>
            {/* Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-12">
              <div className="bg-gray-800/50 backdrop-blur-lg rounded-xl p-6">
                <div className="flex items-center space-x-3 mb-2">
                  <Activity className="w-8 h-8 text-blue-400" />
                  <h3 className="text-gray-400 font-medium">Total Analyzed</h3>
                </div>
                <p className="text-4xl font-bold text-white">{stats?.total || 0}</p>
              </div>

              <div className="bg-gray-800/50 backdrop-blur-lg rounded-xl p-6">
                <div className="flex items-center space-x-3 mb-2">
                  <AlertTriangle className="w-8 h-8 text-red-400" />
                  <h3 className="text-gray-400 font-medium">Malicious</h3>
                </div>
                <p className="text-4xl font-bold text-red-400">{stats?.malicious || 0}</p>
              </div>

              <div className="bg-gray-800/50 backdrop-blur-lg rounded-xl p-6">
                <div className="flex items-center space-x-3 mb-2">
                  <Shield className="w-8 h-8 text-green-400" />
                  <h3 className="text-gray-400 font-medium">Legitimate</h3>
                </div>
                <p className="text-4xl font-bold text-green-400">{stats?.legitimate || 0}</p>
              </div>

              <div className="bg-gray-800/50 backdrop-blur-lg rounded-xl p-6">
                <div className="flex items-center space-x-3 mb-2">
                  <TrendingUp className="w-8 h-8 text-purple-400" />
                  <h3 className="text-gray-400 font-medium">Avg Risk</h3>
                </div>
                <p className="text-4xl font-bold text-white">{stats?.avgRisk || 0}</p>
              </div>
            </div>

            {/* Live Metrics Panel */}
            {metrics && (
              <div className="bg-gray-800/50 backdrop-blur-lg rounded-2xl p-6 mb-8">
                <h2 className="text-xl font-bold text-white mb-4 flex items-center space-x-2">
                  <Zap className="w-5 h-5 text-yellow-400" />
                  <span>Live Metrics</span>
                  {alert?.triggered && (
                    <span className="ml-3 px-2 py-0.5 text-xs bg-red-500 text-white rounded-full animate-pulse">
                      DRIFT ALERT
                    </span>
                  )}
                </h2>

                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                  <div className="bg-gray-900/50 rounded-lg p-3 text-center">
                    <p className="text-gray-400 text-xs mb-1">Requests (1h)</p>
                    <p className="text-white font-bold text-xl">{metrics.request_stats?.last_1h?.requests ?? '—'}</p>
                  </div>
                  <div className="bg-gray-900/50 rounded-lg p-3 text-center">
                    <p className="text-gray-400 text-xs mb-1">Fraud Rate (24h)</p>
                    <p className="text-orange-400 font-bold text-xl">
                      {metrics.analysis_24h?.fraud_rate != null
                        ? `${(metrics.analysis_24h.fraud_rate * 100).toFixed(1)}%`
                        : '—'}
                    </p>
                  </div>
                  <div className="bg-gray-900/50 rounded-lg p-3 text-center">
                    <p className="text-gray-400 text-xs mb-1">p95 Latency</p>
                    <p className="text-blue-400 font-bold text-xl">
                      {metrics.request_stats?.last_1h?.p95_ms != null
                        ? `${metrics.request_stats.last_1h.p95_ms}ms`
                        : '—'}
                    </p>
                  </div>
                  <div className="bg-gray-900/50 rounded-lg p-3 text-center">
                    <p className="text-gray-400 text-xs mb-1">Errors (1h)</p>
                    <p className={`font-bold text-xl ${(metrics.request_stats?.last_1h?.errors ?? 0) > 0 ? 'text-red-400' : 'text-green-400'}`}>
                      {metrics.request_stats?.last_1h?.errors ?? 0}
                    </p>
                  </div>
                </div>

                {alert?.triggered && (
                  <div className="p-3 bg-red-900/30 border border-red-500 rounded-lg text-sm text-red-300">
                    {alert.message}
                  </div>
                )}
              </div>
            )}

            {/* Transaction List */}
            <div className="bg-gray-800/50 backdrop-blur-lg rounded-2xl p-8">
              <h2 className="text-3xl font-bold text-white mb-6 flex items-center space-x-3">
                <Clock className="w-8 h-8 text-purple-400" />
                <span>Recent Transactions</span>
              </h2>

              {transactions.length === 0 ? (
                <div className="text-center py-12">
                  <p className="text-gray-400 text-lg">No transactions analyzed yet</p>
                  <Link 
                    href="/analyze"
                    className="inline-block mt-4 px-6 py-3 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-semibold transition"
                  >
                    Analyze Your First Transaction
                  </Link>
                </div>
              ) : (
                <div className="space-y-4">
                  {transactions.map((tx, idx) => (
                    <div 
                      key={idx}
                      className={`p-6 rounded-lg border-l-4 ${
                        tx.is_malicious 
                          ? 'bg-red-900/20 border-red-500' 
                          : 'bg-green-900/20 border-green-500'
                      }`}
                    >
                      <div className="flex flex-col md:flex-row md:items-center md:justify-between space-y-4 md:space-y-0">
                        <div className="flex-1">
                          <div className="flex items-center space-x-3 mb-2">
                            <span className={`px-3 py-1 rounded-full text-xs font-semibold ${
                              tx.is_malicious 
                                ? 'bg-red-500 text-white' 
                                : 'bg-green-500 text-white'
                            }`}>
                              {tx.is_malicious ? 'Malicious' : 'Legitimate'}
                            </span>
                            <span className="text-gray-400 text-sm">
                              Risk: {tx.risk_score}/100
                            </span>
                          </div>
                          <p className="text-white font-mono text-sm mb-1">
                            {tx.tx_hash}
                          </p>
                          <p className="text-gray-400 text-xs">
                            {new Date(tx.timestamp).toLocaleString()}
                          </p>
                        </div>

                        <div className="flex items-center space-x-6 text-sm">
                          <div>
                            <span className="text-gray-400">Confidence:</span>
                            <span className="text-white ml-2 font-semibold">
                              {(tx.confidence * 100).toFixed(1)}%
                            </span>
                          </div>
                          <div>
                            <span className="text-gray-400">IPFS:</span>
                            <span className="text-purple-400 ml-2 font-mono">
                              {tx.ipfs_hash?.substring(0, 12)}...
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </>
        )}
      </section>
    </main>
  );
}
