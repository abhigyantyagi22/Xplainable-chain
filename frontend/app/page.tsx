'use client';

import Link from 'next/link';
import {
  Activity,
  FileSearch,
  TrendingUp,
  ArrowRight,
  GitBranch,
  ShieldCheck,
} from 'lucide-react';
import { ReactNode } from 'react';
import Reveal from '@/components/Reveal';

export default function Home() {
  return (
    <div>
      {/* Hero */}
      <section className="mx-auto max-w-6xl px-4 pb-20 pt-16 sm:px-6 sm:pt-24">
        <div className="mx-auto max-w-3xl text-center animate-enter">
          <span className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-medium text-slate-600">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
            Live on Polygon Amoy
          </span>
          <h1 className="mt-6 text-4xl font-bold tracking-tight text-slate-900 sm:text-5xl md:text-6xl">
            Explainable AI for
            <span className="text-indigo-600"> blockchain security</span>
          </h1>
          <p className="mx-auto mt-6 max-w-2xl text-lg leading-relaxed text-slate-600">
            Detect malicious transactions with machine learning, understand every
            decision through SHAP and causal analysis, and verify the results on-chain.
          </p>
          <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <Link
              href="/prevent"
              className="tappable inline-flex w-full items-center justify-center gap-2 rounded-lg bg-indigo-600 px-6 py-3 text-sm font-semibold text-white hover:bg-indigo-700 hover:shadow-lg hover:shadow-indigo-600/20 sm:w-auto"
            >
              Check a transaction
              <ArrowRight className="h-4 w-4" />
            </Link>
            <Link
              href="/dashboard"
              className="tappable inline-flex w-full items-center justify-center rounded-lg border border-slate-300 bg-white px-6 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-100 sm:w-auto"
            >
              View dashboard
            </Link>
          </div>
        </div>
      </section>

      {/* Primary highlight: Check Before Send */}
      <section className="mx-auto max-w-6xl px-4 sm:px-6">
        <Reveal>
          <Link href="/prevent" className="group block">
            <div className="lift tappable overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm hover:shadow-md">
              <div className="flex flex-col gap-6 p-8 md:flex-row md:items-center md:justify-between md:p-10">
                <div className="max-w-2xl">
                  <div className="flex items-center gap-3">
                    <span className="inline-flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-50 text-emerald-600">
                      <ShieldCheck className="h-5 w-5" />
                    </span>
                    <span className="rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-semibold text-emerald-700">
                      Recommended
                    </span>
                  </div>
                  <h2 className="mt-4 text-2xl font-bold text-slate-900">Check Before Send</h2>
                  <p className="mt-2 text-slate-600">
                    Prevent fraud before it happens. Scan any transaction and get an instant risk
                    assessment with a full explanation — all before you sign and send.
                  </p>
                </div>
                <span className="inline-flex shrink-0 items-center gap-2 rounded-lg bg-slate-900 px-5 py-3 text-sm font-semibold text-white transition-colors group-hover:bg-slate-800">
                  Check a transaction
                  <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
                </span>
              </div>
            </div>
          </Link>
        </Reveal>
      </section>

      {/* Causal AI highlight */}
      <section className="mx-auto max-w-6xl px-4 pt-6 sm:px-6">
        <Reveal>
          <div className="overflow-hidden rounded-2xl bg-slate-900 shadow-sm">
            <div className="flex flex-col gap-6 p-8 md:flex-row md:items-center md:justify-between md:p-10">
              <div className="max-w-2xl">
                <span className="inline-flex h-10 w-10 items-center justify-center rounded-lg bg-white/10 text-indigo-300">
                  <GitBranch className="h-5 w-5" />
                </span>
                <h2 className="mt-4 text-2xl font-bold text-white">Causal Explainable AI</h2>
                <p className="mt-2 text-slate-300">
                  Go beyond correlation. Identify true cause-and-effect relationships in fraud
                  detection, and reveal the spurious correlations that confounders create.
                </p>
              </div>
              <Link
                href="/analyze/causal"
                className="tappable inline-flex shrink-0 items-center gap-2 rounded-lg bg-white px-5 py-3 text-sm font-semibold text-slate-900 hover:bg-slate-100"
              >
                Explore Causal AI
                <ArrowRight className="h-4 w-4" />
              </Link>
            </div>
          </div>
        </Reveal>
      </section>

      {/* Feature grid */}
      <section className="mx-auto max-w-6xl px-4 pt-16 sm:px-6">
        <div className="grid gap-6 md:grid-cols-3">
          <Reveal delay={0}>
            <FeatureCard
              icon={<Activity className="h-5 w-5" />}
              title="Real-time detection"
              description="AI-powered anomaly detection analyzes transactions in seconds."
            />
          </Reveal>
          <Reveal delay={120}>
            <FeatureCard
              icon={<FileSearch className="h-5 w-5" />}
              title="Explainable AI"
              description="SHAP values show exactly why each transaction was flagged."
            />
          </Reveal>
          <Reveal delay={240}>
            <FeatureCard
              icon={<TrendingUp className="h-5 w-5" />}
              title="On-chain verification"
              description="Explanations stored immutably on Polygon for transparency."
            />
          </Reveal>
        </div>
      </section>

      {/* Stats */}
      <section className="mx-auto max-w-6xl px-4 pt-16 sm:px-6">
        <Reveal>
          <div className="rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
            <div className="grid grid-cols-2 gap-8 text-center md:grid-cols-4">
              <StatCard label="Detection accuracy" value="94%" />
              <StatCard label="Avg analysis time" value="8s" />
              <StatCard label="Transactions analyzed" value="1,247" />
              <StatCard label="Gas cost per entry" value="0.001 MATIC" />
            </div>
          </div>
        </Reveal>
      </section>
    </div>
  );
}

interface FeatureCardProps {
  icon: ReactNode;
  title: string;
  description: string;
}

function FeatureCard({ icon, title, description }: FeatureCardProps) {
  return (
    <div className="lift h-full rounded-xl border border-slate-200 bg-white p-6 shadow-sm hover:shadow-md">
      <span className="inline-flex h-10 w-10 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600">
        {icon}
      </span>
      <h3 className="mt-4 text-base font-semibold text-slate-900">{title}</h3>
      <p className="mt-1.5 text-sm leading-relaxed text-slate-600">{description}</p>
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
      <div className="text-3xl font-bold text-slate-900">{value}</div>
      <div className="mt-1 text-sm text-slate-500">{label}</div>
    </div>
  );
}
