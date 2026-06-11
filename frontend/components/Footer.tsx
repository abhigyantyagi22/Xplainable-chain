import Link from 'next/link';
import { Github } from 'lucide-react';
import BlockSightLogo from '@/components/BlockSightLogo';

export default function Footer() {
  return (
    <footer className="mt-24 border-t border-slate-800 bg-slate-900 text-slate-300">
      <div className="mx-auto max-w-6xl px-4 py-12 sm:px-6">
        <div className="flex flex-col gap-8 md:flex-row md:items-start md:justify-between">
          <div className="max-w-sm">
            <div className="flex items-center gap-2">
              <BlockSightLogo className="h-7 w-7 text-indigo-400" />
              <span className="text-lg font-semibold text-white">Block Sight</span>
            </div>
            <p className="mt-3 text-sm leading-relaxed text-slate-400">
              Explainable AI for blockchain security. Detect malicious transactions,
              understand every decision, and verify on-chain.
            </p>
          </div>

          <div className="grid grid-cols-2 gap-12">
            <div>
              <h4 className="text-sm font-semibold text-white">Product</h4>
              <ul className="mt-3 space-y-2 text-sm">
                <li><Link href="/prevent" className="text-slate-400 transition-colors hover:text-white">Check Before Send</Link></li>
                <li><Link href="/analyze" className="text-slate-400 transition-colors hover:text-white">Analyze</Link></li>
                <li><Link href="/analyze/causal" className="text-slate-400 transition-colors hover:text-white">Causal AI</Link></li>
                <li><Link href="/dashboard" className="text-slate-400 transition-colors hover:text-white">Dashboard</Link></li>
              </ul>
            </div>
            <div>
              <h4 className="text-sm font-semibold text-white">Built with</h4>
              <ul className="mt-3 space-y-2 text-sm text-slate-400">
                <li>Next.js</li>
                <li>FastAPI</li>
                <li>Polygon</li>
              </ul>
            </div>
          </div>
        </div>

        <div className="mt-10 flex flex-col items-center justify-between gap-4 border-t border-slate-800 pt-6 sm:flex-row">
          <p className="text-sm text-slate-500">
            © {new Date().getFullYear()} Block Sight. All rights reserved.
          </p>
          <a
            href="https://github.com/abhigyantyagi22/Xplainable-chain"
            target="_blank"
            rel="noopener noreferrer"
            className="text-slate-400 transition-colors hover:text-white"
            aria-label="GitHub repository"
          >
            <Github className="h-5 w-5" />
          </a>
        </div>
      </div>
    </footer>
  );
}
