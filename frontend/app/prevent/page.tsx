'use client'

import { useState } from 'react'
import { AlertTriangle, CheckCircle, Info, TrendingDown } from 'lucide-react'
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

export default function PreventPage() {
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<PreCheckResult | null>(null)
  
  // Form state
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

  const getRiskColor = (risk: number) => {
    if (risk > 70) return 'text-red-600 bg-red-50 border-red-200'
    if (risk > 40) return 'text-yellow-600 bg-yellow-50 border-yellow-200'
    return 'text-green-600 bg-green-50 border-green-200'
  }

  const getRiskIcon = (risk: number) => {
    if (risk > 70) return <AlertTriangle className="w-8 h-8 text-red-600" />
    if (risk > 40) return <Info className="w-8 h-8 text-yellow-600" />
    return <CheckCircle className="w-8 h-8 text-green-600" />
  }

  return (
    <div className="container mx-auto p-8 max-w-6xl">
      {/* Back Navigation */}
      <div className="mb-6">
        <a 
          href="/" 
          className="inline-flex items-center gap-2 text-blue-600 hover:text-blue-800 transition-colors font-medium group"
        >
          <svg 
            className="w-5 h-5 transform group-hover:-translate-x-1 transition-transform" 
            fill="none" 
            stroke="currentColor" 
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
          </svg>
          Back to Home
        </a>
      </div>

      <div className="mb-8">
        <h1 className="text-4xl font-bold mb-2 flex items-center gap-2">
          <CheckCircle className="w-10 h-10 text-blue-600" />
          Check Before You Send
        </h1>
        <p className="text-gray-600 text-lg">
          ✅ Analyze transactions BEFORE signing to prevent fraud
        </p>
        <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
          <p className="text-sm text-blue-800">
            <strong>New Prevention Feature:</strong> Enter your transaction details below to check 
            for fraud risk BEFORE you sign in MetaMask. You can adjust parameters based on recommendations 
            and re-check until the risk is acceptable.
          </p>
        </div>
      </div>

      {/* Input Form */}
      <div className="bg-white rounded-lg shadow-lg p-6 mb-8">
        <h2 className="text-2xl font-semibold mb-6">Transaction Details</h2>
        
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-2">
              Recipient Address *
            </label>
            <input
              type="text"
              value={toAddress}
              onChange={(e) => setToAddress(e.target.value)}
              placeholder="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb"
              className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <p className="text-xs text-gray-500 mt-1">
              The address you want to send funds to
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-2">
                Amount (ETH)
              </label>
              <input
                type="number"
                step="0.001"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                placeholder="0.5"
                className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">
                Gas Price (Gwei) - Optional
              </label>
              <input
                type="number"
                value={gasPrice}
                onChange={(e) => setGasPrice(e.target.value)}
                placeholder="50"
                className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <p className="text-xs text-gray-500 mt-1">
                Leave empty to use network average
              </p>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">
              Your Address (From) - Optional
            </label>
            <input
              type="text"
              value={fromAddress}
              onChange={(e) => setFromAddress(e.target.value)}
              placeholder="0x..."
              className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <p className="text-xs text-gray-500 mt-1">
              For better accuracy (includes your account history)
            </p>
          </div>

          <button
            onClick={checkBeforeSend}
            disabled={loading}
            className="w-full bg-blue-600 text-white py-3 rounded-lg font-semibold hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? 'Analyzing...' : '🔍 Check Safety Before Sending'}
          </button>
        </div>
      </div>

      {/* Results */}
      {result && (
        <div className="space-y-6">
          {/* Risk Score */}
          <div className={`p-6 border-2 rounded-lg ${getRiskColor(result.risk_score)}`}>
            <div className="flex items-center gap-4 mb-4">
              {getRiskIcon(result.risk_score)}
              <div>
                <h3 className="text-3xl font-bold">{result.risk_score}% Risk</h3>
                <p className="font-semibold text-lg">{result.action}</p>
              </div>
            </div>
            <p className="text-sm opacity-80">{result.note}</p>
          </div>

          {/* Feature Explanation */}
          <div className="bg-gradient-to-r from-blue-50 to-purple-50 rounded-lg shadow-lg p-6 border-2 border-blue-200">
            <h3 className="text-xl font-semibold mb-4 flex items-center gap-2">
              ℹ️ Understanding the Analysis Features
            </h3>
            <div className="grid md:grid-cols-2 gap-4 text-sm">
              <div className="space-y-2">
                <div className="p-3 bg-white rounded-lg border border-blue-100">
                  <span className="font-semibold text-blue-800">amount</span>
                  <p className="text-gray-600 mt-1">Transaction amount in ETH (what you entered)</p>
                </div>
                <div className="p-3 bg-white rounded-lg border border-blue-100">
                  <span className="font-semibold text-blue-800">value</span>
                  <p className="text-gray-600 mt-1">Transaction value - same as amount for simple transfers</p>
                </div>
                <div className="p-3 bg-white rounded-lg border border-blue-100">
                  <span className="font-semibold text-blue-800">gas_price</span>
                  <p className="text-gray-600 mt-1">Gas price in Gwei (entered or network average)</p>
                </div>
                <div className="p-3 bg-white rounded-lg border border-blue-100">
                  <span className="font-semibold text-blue-800">gas_used</span>
                  <p className="text-gray-600 mt-1">⚙️ ESTIMATED: 21000 for simple transfer, 100000 for contracts</p>
                </div>
              </div>
              <div className="space-y-2">
                <div className="p-3 bg-white rounded-lg border border-blue-100">
                  <span className="font-semibold text-blue-800">gas_price_deviation</span>
                  <p className="text-gray-600 mt-1">⚙️ CALCULATED: How much gas price differs from network average</p>
                </div>
                <div className="p-3 bg-white rounded-lg border border-blue-100">
                  <span className="font-semibold text-blue-800">sender_tx_count</span>
                  <p className="text-gray-600 mt-1">⚙️ FETCHED: Your account's transaction history (if address provided)</p>
                </div>
                <div className="p-3 bg-white rounded-lg border border-blue-100">
                  <span className="font-semibold text-blue-800">contract_age</span>
                  <p className="text-gray-600 mt-1">⚙️ ESTIMATED: Age of recipient contract based on code size (0 for regular wallets)</p>
                </div>
                <div className="p-3 bg-white rounded-lg border border-blue-100">
                  <span className="font-semibold text-blue-800">is_contract_creation</span>
                  <p className="text-gray-600 mt-1">⚙️ DETECTED: Whether creating new contract (1) or not (0)</p>
                </div>
              </div>
            </div>
            <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
              <p className="text-xs text-yellow-800">
                <strong>Note:</strong> The model uses 9 features total. Some are what you entered (amount, gas_price), 
                while others are automatically calculated, estimated, or fetched from the blockchain to match the 
                training data format. Features marked with ⚙️ are auto-generated.
              </p>
            </div>
          </div>

          {/* Causal Factors (CC-SHAP) */}
          <div className="bg-white rounded-lg shadow-lg p-6">
            <h3 className="text-xl font-semibold mb-4 flex items-center gap-2">
              🧠 Causal Factors (CC-SHAP Analysis)
            </h3>
            <p className="text-sm text-gray-600 mb-4">
              These are the TRUE CAUSES of the risk score (not just correlations):
            </p>
            <div className="space-y-3">
              {result.causal_factors.map((factor, i) => (
                <div key={i} className="p-3 bg-gray-50 rounded-lg border border-gray-200">
                  <div className="flex justify-between items-center mb-1">
                    <span className="font-semibold">{factor.feature}</span>
                    <span className={`text-sm ${factor.contribution > 0 ? 'text-red-600' : 'text-green-600'}`}>
                      {factor.contribution > 0 ? '↑' : '↓'} {Math.abs(factor.contribution).toFixed(3)}
                    </span>
                  </div>
                  <div className="text-sm text-gray-600">
                    Value: {factor.value} • {factor.impact}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Counterfactuals */}
          {result.counterfactuals.length > 0 && (
            <div className="bg-white rounded-lg shadow-lg p-6">
              <h3 className="text-xl font-semibold mb-4 flex items-center gap-2">
                <TrendingDown className="w-6 h-6 text-green-600" />
                How to Reduce Risk (Counterfactual Recommendations)
              </h3>
              <p className="text-sm text-gray-600 mb-4">
                Try these adjustments to lower your fraud risk:
              </p>
              <div className="space-y-4">
                {result.counterfactuals.map((cf, i) => (
                  <div key={i} className="p-4 bg-gradient-to-r from-blue-50 to-green-50 rounded-lg border border-blue-200">
                    <div className="flex justify-between items-start mb-2">
                      <div className="flex-1">
                        <p className="font-semibold text-lg">{cf.scenario}</p>
                        <p className="text-sm text-gray-700 mt-1">{cf.recommendation}</p>
                      </div>
                      <div className="text-right ml-4">
                        <div className="text-2xl font-bold text-green-600">
                          {cf.new_risk}%
                        </div>
                        <div className="text-sm text-green-700">
                          ↓ {cf.risk_change}% lower
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 mt-2">
                      <span className={`text-xs px-2 py-1 rounded ${
                        cf.feasibility === 'High' ? 'bg-green-100 text-green-800' :
                        cf.feasibility === 'Medium' ? 'bg-yellow-100 text-yellow-800' :
                        'bg-red-100 text-red-800'
                      }`}>
                        Feasibility: {cf.feasibility}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
              
              <div className="mt-6 p-4 bg-blue-100 border border-blue-300 rounded-lg">
                <p className="text-sm text-blue-900">
                  💡 <strong>Tip:</strong> Adjust your transaction parameters above based on these recommendations, 
                  then click "Check Safety" again to see the updated risk score!
                </p>
              </div>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex gap-4">
            <button
              onClick={checkBeforeSend}
              className="flex-1 bg-blue-600 text-white py-3 rounded-lg font-semibold hover:bg-blue-700 transition-colors"
            >
              🔄 Re-Check After Adjustments
            </button>
            {result.safe_to_send && (
              <button
                className="flex-1 bg-green-600 text-white py-3 rounded-lg font-semibold hover:bg-green-700 transition-colors"
              >
                ✅ Proceed to MetaMask
              </button>
            )}
          </div>
        </div>
      )}

      {/* Instructions */}
      <div className="mt-8 bg-gray-50 rounded-lg p-6">
        <h3 className="font-semibold text-lg mb-3">How to Use This Tool:</h3>
        <ol className="space-y-2 text-sm text-gray-700">
          <li>1. <strong>Before</strong> signing a transaction in MetaMask, copy the details (address, amount, gas)</li>
          <li>2. Paste them into the form above and click "Check Safety"</li>
          <li>3. Review the risk score and causal factors (CC-SHAP shows WHY it's risky)</li>
          <li>4. If risky, follow the counterfactual recommendations to adjust parameters</li>
          <li>5. Re-check until the risk is acceptable</li>
          <li>6. Only then sign the transaction in MetaMask</li>
        </ol>
      </div>
    </div>
  )
}
