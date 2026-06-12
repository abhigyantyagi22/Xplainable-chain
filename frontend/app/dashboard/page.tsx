'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { TrendingUp, AlertTriangle, Activity, Clock, Zap, ShieldCheck } from 'lucide-react';
import { apiGet } from '@/lib/api';
import Reveal from '@/components/Reveal';

export default function DashboardPage() {
  const [stats, setStats]           = useState<any>(null);
  const [transactions, setTransactions] = useState<any[]>([]);
  const [metrics, setMetrics]        = useState<any>(null);
  const [alert, setAlert]            = useState<any>(null);
  const [loading, setLoading]        = useState(true);

  useEffect(() => { fetchDashboardData(); }, []);

  const fetchDashboardData = async () => {
    try {
      const data: any = await apiGet('/api/audit/');
      const trail = data.audit_trail || [];
      setTransactions(trail);

      const totalTx    = trail.length;
      const malicious  = trail.filter((tx: any) => tx.is_malicious).length;
      const avgRisk    = totalTx > 0
        ? trail.reduce((s: number, tx: any) => s + tx.risk_score, 0) / totalTx
        : 0;
      setStats({ total: totalTx, malicious, legitimate: totalTx - malicious, avgRisk: avgRisk.toFixed(1) });

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
    <div className="mx-auto max-w-6xl px-4 py-12 sm:px-6">
      <div className="mb-8 animate-enter">
        <h1 className="text-3xl font-bold tracking-tight text-slate-900">Dashboard</h1>
        <p className="mt-2 text-slate-600">Analysis history and live system metrics.</p>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <div className="flex items-center gap-2 text-slate-500">
            <Activity className="h-5 w-5 animate-pulse" />
            Loading dashboard…
          </div>
        </div>
      ) : (
        <>
          {/* Stats */}
          <Reveal className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard icon={<Activity className="h-5 w-5" />} label="Total analyzed" value={stats?.total ?? 0} tone="indigo" />
            <StatCard icon={<AlertTriangle className="h-5 w-5" />} label="Malicious" value={stats?.malicious ?? 0} tone="red" />
            <StatCard icon={<ShieldCheck className="h-5 w-5" />} label="Legitimate" value={stats?.legitimate ?? 0} tone="emerald" />
            <StatCard icon={<TrendingUp className="h-5 w-5" />} label="Avg risk" value={stats?.avgRisk ?? 0} tone="slate" />
          </Reveal>

          {/* Live metrics */}
          {metrics && (
            <Reveal className="mt-8 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <h2 className="flex items-center gap-2 text-lg font-semibold text-slate-900">
                <Zap className="h-5 w-5 text-amber-500" />
                Live metrics
                {alert?.triggered && (
                  <span className="ml-2 rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700">
                    Drift alert
                  </span>
                )}
              </h2>

              <div className="mt-4 grid grid-cols-2 gap-4 md:grid-cols-4">
                <MetricTile label="Requests (1h)" value={metrics.request_stats?.last_1h?.requests ?? '—'} />
                <MetricTile
                  label="Fraud rate (24h)"
                  value={metrics.analysis_24h?.fraud_rate != null ? `${(metrics.analysis_24h.fraud_rate * 100).toFixed(1)}%` : '—'}
                />
                <MetricTile
                  label="p95 latency"
                  value={metrics.request_stats?.last_1h?.p95_ms != null ? `${metrics.request_stats.last_1h.p95_ms}ms` : '—'}
                />
                <MetricTile
                  label="Errors (1h)"
                  value={metrics.request_stats?.last_1h?.errors ?? 0}
                  danger={(metrics.request_stats?.last_1h?.errors ?? 0) > 0}
                />
              </div>

              {alert?.triggered && (
                <div className="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                  {alert.message}
                </div>
              )}
            </Reveal>
          )}

          {/* Transaction list */}
          <Reveal className="mt-8 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
            <h2 className="flex items-center gap-2 text-xl font-bold text-slate-900">
              <Clock className="h-5 w-5 text-slate-400" />
              Recent transactions
            </h2>

            {transactions.length === 0 ? (
              <div className="py-12 text-center">
                <p className="text-slate-500">No transactions analyzed yet.</p>
                <Link
                  href="/analyze"
                  className="tappable mt-4 inline-block rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700"
                >
                  Analyze your first transaction
                </Link>
              </div>
            ) : (
              <div className="mt-4 space-y-3">
                {transactions.map((tx, idx) => (
                  <div
                    key={idx}
                    className={`rounded-xl border-l-4 bg-slate-50 p-5 ${
                      tx.is_malicious ? 'border-red-400' : 'border-emerald-400'
                    }`}
                  >
                    <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                      <div className="flex-1">
                        <div className="mb-2 flex items-center gap-3">
                          <span
                            className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                              tx.is_malicious ? 'bg-red-100 text-red-700' : 'bg-emerald-100 text-emerald-700'
                            }`}
                          >
                            {tx.is_malicious ? 'Malicious' : 'Legitimate'}
                          </span>
                          <span className="text-sm text-slate-500">Risk: {tx.risk_score}/100</span>
                        </div>
                        <p className="truncate font-mono text-sm text-slate-700">{tx.tx_hash}</p>
                        <p className="mt-1 text-xs text-slate-400">{new Date(tx.timestamp).toLocaleString()}</p>
                      </div>

                      <div className="flex items-center gap-6 text-sm">
                        <div>
                          <span className="text-slate-400">Confidence</span>
                          <span className="ml-2 font-semibold text-slate-900">{(tx.confidence * 100).toFixed(1)}%</span>
                        </div>
                        <div>
                          <span className="text-slate-400">IPFS</span>
                          <span className="ml-2 font-mono text-indigo-600">{tx.ipfs_hash?.substring(0, 12)}…</span>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Reveal>
        </>
      )}
    </div>
  );
}

const toneStyles: Record<string, { bg: string; text: string }> = {
  indigo: { bg: 'bg-indigo-50', text: 'text-indigo-600' },
  red: { bg: 'bg-red-50', text: 'text-red-600' },
  emerald: { bg: 'bg-emerald-50', text: 'text-emerald-600' },
  slate: { bg: 'bg-slate-100', text: 'text-slate-600' },
};

function StatCard({ icon, label, value, tone }: { icon: React.ReactNode; label: string; value: React.ReactNode; tone: string }) {
  const s = toneStyles[tone] ?? toneStyles.slate;
  return (
    <div className="lift rounded-xl border border-slate-200 bg-white p-5 shadow-sm hover:shadow-md">
      <div className="flex items-center gap-2">
        <span className={`inline-flex h-9 w-9 items-center justify-center rounded-lg ${s.bg} ${s.text}`}>{icon}</span>
        <h3 className="text-sm font-medium text-slate-500">{label}</h3>
      </div>
      <p className="mt-3 text-3xl font-bold text-slate-900">{value}</p>
    </div>
  );
}

function MetricTile({ label, value, danger }: { label: string; value: React.ReactNode; danger?: boolean }) {
  return (
    <div className="rounded-lg bg-slate-50 p-3 text-center">
      <p className="mb-1 text-xs text-slate-500">{label}</p>
      <p className={`text-xl font-bold ${danger ? 'text-red-600' : 'text-slate-900'}`}>{value}</p>
    </div>
  );
}
