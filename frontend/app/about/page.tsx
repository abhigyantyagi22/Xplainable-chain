import Link from 'next/link';
import {
  ShieldCheck,
  FileSearch,
  GitBranch,
  Ban,
  Link2,
  AlertTriangle,
  EyeOff,
  Clock,
  Activity,
  ArrowRight,
  Database,
  Cpu,
  Boxes,
} from 'lucide-react';
import Reveal from '@/components/Reveal';

export const metadata = {
  title: 'About — Block Sight',
  description: 'What Block Sight is, the problems it solves, and how it works.',
};

const problems = [
  {
    icon: AlertTriangle,
    title: 'Transactions are irreversible',
    text: 'Once you sign and send funds to a scammer, they are gone — there are no chargebacks on a blockchain.',
  },
  {
    icon: EyeOff,
    title: 'Fraud tools are black boxes',
    text: 'Most flag a transaction as “risky” without saying why, so users can neither trust nor act on the verdict.',
  },
  {
    icon: Clock,
    title: 'Checks come too late',
    text: 'By the time a transaction is reviewed, it is usually already confirmed and permanently on-chain.',
  },
  {
    icon: GitBranch,
    title: 'Correlation isn’t causation',
    text: 'Naïve models latch onto spurious patterns created by confounders — patterns that can be gamed or misread.',
  },
];

const solutions = [
  {
    icon: ShieldCheck,
    title: 'Check before you send',
    text: 'Screen a transaction and get a risk score with guidance to lower it — before you ever sign in MetaMask.',
  },
  {
    icon: FileSearch,
    title: 'Transparent explanations',
    text: 'SHAP values show exactly which features drove each decision, in plain language you can act on.',
  },
  {
    icon: GitBranch,
    title: 'Causal, not just correlated',
    text: 'Causal inference and CC-SHAP isolate true cause-and-effect, expose spurious correlations, and propose counterfactual fixes.',
  },
  {
    icon: Ban,
    title: 'Threat-intelligence screening',
    text: 'Known-scam and OFAC-sanctioned addresses are caught instantly, before any machine-learning model runs.',
  },
  {
    icon: Link2,
    title: 'Verifiable on-chain',
    text: 'High-risk explanations are pinned to IPFS and anchored on Polygon, creating a tamper-proof audit trail.',
  },
  {
    icon: Activity,
    title: 'Real-time monitoring',
    text: 'A live dashboard tracks analyses, fraud rate, latency, and model-drift alerts as they happen.',
  },
];

const steps = [
  {
    n: '01',
    title: 'Detect',
    text: 'A gradient-boosted model scores the transaction’s fraud risk in seconds.',
  },
  {
    n: '02',
    title: 'Explain',
    text: 'SHAP and causal analysis surface the why behind the score — not just the what.',
  },
  {
    n: '03',
    title: 'Verify',
    text: 'The explanation is pinned to IPFS and its hash recorded on-chain for independent verification.',
  },
];

const stack = [
  { icon: Boxes, kind: 'Frontend', label: 'Next.js · RainbowKit · Wagmi' },
  { icon: Cpu, kind: 'AI backend', label: 'FastAPI · XGBoost · SHAP · DoWhy' },
  { icon: Database, kind: 'Data & cache', label: 'MongoDB · Redis' },
  { icon: Link2, kind: 'On-chain', label: 'Polygon · IPFS (Pinata)' },
];

export default function AboutPage() {
  return (
    <div className="mx-auto max-w-5xl px-4 pb-8 sm:px-6">
      {/* Intro */}
      <section className="pt-16">
        <div className="animate-enter max-w-3xl">
          <span className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-medium text-slate-600">
            About Block Sight
          </span>
          <h1 className="mt-6 text-4xl font-bold tracking-tight text-slate-900 sm:text-5xl">
            Security you can actually see
          </h1>
          <p className="mt-6 text-lg leading-relaxed text-slate-600">
            Block Sight is an explainable-AI layer for blockchain security. It detects malicious
            transactions with machine learning, explains every decision with SHAP and causal
            inference, and anchors those explanations on-chain. The result: a “risky” verdict that
            arrives with the reasons behind it — and proof anyone can verify.
          </p>
        </div>
      </section>

      {/* The problem */}
      <section className="pt-16">
        <Reveal>
          <h2 className="text-2xl font-bold tracking-tight text-slate-900">The problem</h2>
          <p className="mt-2 max-w-2xl text-slate-600">
            Crypto fraud is uniquely unforgiving, and the tools meant to stop it usually fall short
            in four ways.
          </p>
        </Reveal>
        <div className="mt-8 grid gap-5 sm:grid-cols-2">
          {problems.map((p, i) => (
            <Reveal key={p.title} delay={i * 90}>
              <div className="lift h-full rounded-xl border border-slate-200 bg-white p-6 shadow-sm hover:shadow-md">
                <span className="inline-flex h-10 w-10 items-center justify-center rounded-lg bg-red-50 text-red-600">
                  <p.icon className="h-5 w-5" />
                </span>
                <h3 className="mt-4 text-base font-semibold text-slate-900">{p.title}</h3>
                <p className="mt-1.5 text-sm leading-relaxed text-slate-600">{p.text}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </section>

      {/* What it solves */}
      <section className="pt-16">
        <Reveal>
          <h2 className="text-2xl font-bold tracking-tight text-slate-900">What Block Sight solves</h2>
          <p className="mt-2 max-w-2xl text-slate-600">
            Every feature maps back to one of those gaps — turning an opaque, after-the-fact warning
            into a transparent, preventive, verifiable decision.
          </p>
        </Reveal>
        <div className="mt-8 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {solutions.map((s, i) => (
            <Reveal key={s.title} delay={(i % 3) * 90}>
              <div className="lift h-full rounded-xl border border-slate-200 bg-white p-6 shadow-sm hover:shadow-md">
                <span className="inline-flex h-10 w-10 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600">
                  <s.icon className="h-5 w-5" />
                </span>
                <h3 className="mt-4 text-base font-semibold text-slate-900">{s.title}</h3>
                <p className="mt-1.5 text-sm leading-relaxed text-slate-600">{s.text}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </section>

      {/* How it works */}
      <section className="pt-16">
        <Reveal>
          <h2 className="text-2xl font-bold tracking-tight text-slate-900">How it works</h2>
          <p className="mt-2 max-w-2xl text-slate-600">
            Three stages run on every transaction — detection, explanation, and verification.
          </p>
        </Reveal>
        <div className="mt-8 grid gap-5 md:grid-cols-3">
          {steps.map((step, i) => (
            <Reveal key={step.n} delay={i * 120}>
              <div className="lift h-full rounded-xl border border-slate-200 bg-white p-6 shadow-sm hover:shadow-md">
                <span className="text-sm font-bold text-indigo-600">{step.n}</span>
                <h3 className="mt-2 text-lg font-semibold text-slate-900">{step.title}</h3>
                <p className="mt-1.5 text-sm leading-relaxed text-slate-600">{step.text}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </section>

      {/* Under the hood */}
      <section className="pt-16">
        <Reveal>
          <div className="rounded-2xl bg-slate-900 p-8 sm:p-10">
            <h2 className="text-2xl font-bold tracking-tight text-white">Under the hood</h2>
            <p className="mt-2 max-w-2xl text-slate-300">
              Built on a modern, fully open stack — from the wallet to the smart contract.
            </p>
            <div className="mt-8 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
              {stack.map((t) => (
                <div key={t.kind} className="rounded-xl border border-white/10 bg-white/5 p-5">
                  <span className="inline-flex h-10 w-10 items-center justify-center rounded-lg bg-white/10 text-indigo-300">
                    <t.icon className="h-5 w-5" />
                  </span>
                  <p className="mt-4 text-xs font-medium uppercase tracking-wide text-slate-400">{t.kind}</p>
                  <p className="mt-1 text-sm font-medium text-white">{t.label}</p>
                </div>
              ))}
            </div>
          </div>
        </Reveal>
      </section>

      {/* CTA */}
      <section className="pt-16">
        <Reveal>
          <div className="flex flex-col items-center justify-between gap-6 rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-sm sm:flex-row sm:text-left">
            <div>
              <h2 className="text-xl font-bold text-slate-900">Try it on a real transaction</h2>
              <p className="mt-1 text-slate-600">
                Screen a transfer before you sign, or explore the causal engine behind every score.
              </p>
            </div>
            <div className="flex shrink-0 gap-3">
              <Link
                href="/prevent"
                className="tappable inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-5 py-3 text-sm font-semibold text-white hover:bg-indigo-700"
              >
                Check a transaction
                <ArrowRight className="h-4 w-4" />
              </Link>
              <Link
                href="/analyze/causal"
                className="tappable inline-flex items-center rounded-lg border border-slate-300 bg-white px-5 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-100"
              >
                Explore Causal AI
              </Link>
            </div>
          </div>
        </Reveal>
      </section>
    </div>
  );
}