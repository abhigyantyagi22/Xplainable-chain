'use client'

import { useState } from 'react'
import { AlertTriangle, CheckCircle, Info, TrendingDown, ShieldCheck } from 'lucide-react'
import { apiPost } from '@/lib/api'

interface CausalFactor {
  feature: string
  value: number
  contribution: number
  impact: string
}

interface Counterfactual {
  scenario: string
  new_risk: number
  risk_change: number
  feasibility: string
  recommendation: string
}

interface PreCheckResult {
  risk_score: number
  safe_to_send: boolean
  action: string
  causal_factors: CausalFactor[]
  counterfactuals: Counterfactual[]
  timing: string
  note: string
}

const FEATURE_NOTES: { name: string; note: string }[] = [
  { name: 'amount', note: 'Transaction amount in ETH (what you entered).' },
  { name: 'value', note: 'Transaction value — same as amount for simple transfers.' },
  { name: 'gas_price', note: 'Gas price in Gwei (entered or network average).' },
  { name: 'gas_used', note: 'Estimated: 21000 for a simple transfer, ~100000 for contracts.' },
  { name: 'gas_price_deviation', note: 'Calculated: how much gas price differs from the network average.' },
  { name: 'sender_tx_count', note: 'Fetched: your account’s transaction history (if address provided).' },
  { name: 'contract_age', note: 'Estimated: age of the recipient contract (0 for regular wallets).' },
  { name: 'is_contract_creation', note: 'Detected: whether creating a new contract (1) or not (0).' },
]

export default function PreventPage() {
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<PreCheckResult | null>(null)

  const [toAddress, setToAddress] = useState('')
  const [amount, setAmount] = useState('')
  const [gasPrice, setGasPrice] = useState('')
  const [fromAddress, setFromAddress] = useState('')

  const checkBeforeSend = async () => {
    if (!toAddress) {
      alert('Please enter recipient address')
      return
    }
    setLoading(true)
    setResult(null)
    try {
      const data = await apiPost<PreCheckResult>('/api/check-before-send', {
        to_address: toAddress,
        amount: amount ? parseFloat(amount) : 0,
        gas_price: gasPrice ? parseInt(gasPrice) : null,
        from_address: fromAddress || null,
      })
      setResult(data)
    } catch (error) {
      console.error('Error:', error)
      alert('Error checking transaction. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const riskTone = (risk: number) =>
    risk > 70
      ? 'border-red-200 bg-red-50 text-red-700'
      : risk > 40
      ? 'border-amber-200 bg-amber-50 text-amber-700'
      : 'border-emerald-200 bg-emerald-50 text-emerald-700'

  const riskIcon = (risk: number) =>
    risk > 70 ? <AlertTriangle className="h-8 w-8 text-red-500" />
    : risk > 40 ? <Info className="h-8 w-8 text-amber-500" />
    : <CheckCircle className="h-8 w-8 text-emerald-500" />

  const inputClass =
    'w-full rounded-lg border border-slate-300 bg-white px-4 py-2.5 text-slate-900 placeholder-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500'

  return (
    <div className="mx-auto max-w-4xl px-4 py-12 sm:px-6">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3">
          <span className="inline-flex h-11 w-11 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600">
            <ShieldCheck className="h-6 w-6" />
          </span>
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-slate-900">Check Before You Send</h1>
            <p className="text-slate-600">Analyze a transaction before signing to prevent fraud.</p>
          </div>
        </div>
        <div className="mt-4 rounded-xl border border-slate-200 bg-white p-4 text-sm text-slate-600 shadow-sm">
          Enter your transaction details to check the fraud risk <strong className="text-slate-900">before</strong> you
          sign in MetaMask. Adjust parameters based on the recommendations and re-check until the risk is acceptable.
        </div>
      </div>

      {/* Form */}
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
        <h2 className="text-lg font-semibold text-slate-900">Transaction details</h2>
        <div className="mt-5 space-y-4">
          <div>
            <label className="mb-1.5 block text-sm font-medium text-slate-700">Recipient address *</label>
            <input
              type="text"
              value={toAddress}
              onChange={(e) => setToAddress(e.target.value)}
              placeholder="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb"
              className={`${inputClass} font-mono text-sm`}
            />
            <p className="mt-1 text-xs text-slate-500">The address you want to send funds to.</p>
          </div>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div>
              <label className="mb-1.5 block text-sm font-medium text-slate-700">Amount (ETH)</label>
              <input type="number" step="0.001" value={amount} onChange={(e) => setAmount(e.target.value)} placeholder="0.5" className={inputClass} />
            </div>
            <div>
              <label className="mb-1.5 block text-sm font-medium text-slate-700">Gas price (Gwei) — optional</label>
              <input type="number" value={gasPrice} onChange={(e) => setGasPrice(e.target.value)} placeholder="50" className={inputClass} />
              <p className="mt-1 text-xs text-slate-500">Leave empty to use the network average.</p>
            </div>
          </div>

          <div>
            <label className="mb-1.5 block text-sm font-medium text-slate-700">Your address (from) — optional</label>
            <input type="text" value={fromAddress} onChange={(e) => setFromAddress(e.target.value)} placeholder="0x…" className={`${inputClass} font-mono text-sm`} />
            <p className="mt-1 text-xs text-slate-500">Improves accuracy by including your account history.</p>
          </div>

          <button
            onClick={checkBeforeSend}
            disabled={loading}
            className="w-full rounded-lg bg-indigo-600 px-6 py-3 text-sm font-semibold text-white transition-colors hover:bg-indigo-700 disabled:cursor-not-allowed disabled:bg-slate-300"
          >
            {loading ? 'Analyzing…' : 'Check safety before sending'}
          </button>
        </div>
      </div>

      {/* Results */}
      {result && (
        <div className="mt-6 space-y-6">
          {/* Risk score */}
          <div className={`rounded-2xl border p-6 ${riskTone(result.risk_score)}`}>
            <div className="flex items-center gap-4">
              {riskIcon(result.risk_score)}
              <div>
                <h3 className="text-3xl font-bold text-slate-900">{result.risk_score}% risk</h3>
                <p className="text-lg font-semibold">{result.action}</p>
              </div>
            </div>
            <p className="mt-3 text-sm text-slate-600">{result.note}</p>
          </div>

          {/* Causal factors */}
          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <h3 className="text-lg font-semibold text-slate-900">Causal factors (CC-SHAP)</h3>
            <p className="mt-1 text-sm text-slate-600">The true causes of the risk score — not just correlations.</p>
            <div className="mt-4 space-y-3">
              {result.causal_factors.map((factor, i) => (
                <div key={i} className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                  <div className="mb-1 flex items-center justify-between">
                    <span className="font-medium text-slate-900">{factor.feature}</span>
                    <span className={`text-sm font-medium ${factor.contribution > 0 ? 'text-red-600' : 'text-emerald-600'}`}>
                      {factor.contribution > 0 ? '↑' : '↓'} {Math.abs(factor.contribution).toFixed(3)}
                    </span>
                  </div>
                  <div className="text-sm text-slate-600">Value: {factor.value} • {factor.impact}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Counterfactuals */}
          {result.counterfactuals.length > 0 && (
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <h3 className="flex items-center gap-2 text-lg font-semibold text-slate-900">
                <TrendingDown className="h-5 w-5 text-emerald-600" />
                How to reduce risk
              </h3>
              <p className="mt-1 text-sm text-slate-600">Try these adjustments to lower your fraud risk.</p>
              <div className="mt-4 space-y-3">
                {result.counterfactuals.map((cf, i) => (
                  <div key={i} className="rounded-lg border border-slate-200 bg-slate-50 p-4">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1">
                        <p className="font-semibold text-slate-900">{cf.scenario}</p>
                        <p className="mt-1 text-sm text-slate-600">{cf.recommendation}</p>
                      </div>
                      <div className="text-right">
                        <div className="text-2xl font-bold text-emerald-600">{cf.new_risk}%</div>
                        <div className="text-sm text-emerald-700">↓ {cf.risk_change}% lower</div>
                      </div>
                    </div>
                    <span
                      className={`mt-2 inline-block rounded-full px-2 py-0.5 text-xs font-medium ${
                        cf.feasibility === 'High' ? 'bg-emerald-100 text-emerald-800'
                        : cf.feasibility === 'Medium' ? 'bg-amber-100 text-amber-800'
                        : 'bg-red-100 text-red-800'
                      }`}
                    >
                      Feasibility: {cf.feasibility}
                    </span>
                  </div>
                ))}
              </div>
              <div className="mt-5 rounded-lg border border-indigo-100 bg-indigo-50 p-3 text-sm text-indigo-900">
                Adjust the parameters above based on these recommendations, then check again to see the updated risk score.
              </div>
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-4">
            <button
              onClick={checkBeforeSend}
              className="flex-1 rounded-lg border border-slate-300 bg-white py-3 text-sm font-semibold text-slate-700 transition-colors hover:bg-slate-100"
            >
              Re-check after adjustments
            </button>
            {result.safe_to_send && (
              <button className="flex-1 rounded-lg bg-emerald-600 py-3 text-sm font-semibold text-white transition-colors hover:bg-emerald-700">
                Proceed to MetaMask
              </button>
            )}
          </div>
        </div>
      )}

      {/* Feature reference */}
      <div className="mt-10 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <h3 className="text-lg font-semibold text-slate-900">Understanding the analysis features</h3>
        <p className="mt-1 text-sm text-slate-600">
          The model uses 9 features. Some come from your input; others are calculated, estimated, or fetched
          from the blockchain to match the training format.
        </p>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          {FEATURE_NOTES.map((f) => (
            <div key={f.name} className="rounded-lg border border-slate-200 bg-slate-50 p-3">
              <span className="font-mono text-sm font-semibold text-indigo-700">{f.name}</span>
              <p className="mt-1 text-sm text-slate-600">{f.note}</p>
            </div>
          ))}
        </div>
      </div>

      {/* How to use */}
      <div className="mt-6 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <h3 className="text-lg font-semibold text-slate-900">How to use this tool</h3>
        <ol className="mt-3 space-y-2 text-sm text-slate-600">
          <li>1. Before signing in MetaMask, copy the transaction details (address, amount, gas).</li>
          <li>2. Paste them into the form above and click “Check safety”.</li>
          <li>3. Review the risk score and causal factors (CC-SHAP shows why it’s risky).</li>
          <li>4. If risky, follow the counterfactual recommendations to adjust parameters.</li>
          <li>5. Re-check until the risk is acceptable.</li>
          <li>6. Only then sign the transaction in MetaMask.</li>
        </ol>
      </div>
    </div>
  )
}
