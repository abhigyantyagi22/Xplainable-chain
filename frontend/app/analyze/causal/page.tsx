'use client';

import { useState } from 'react';
import CausalGraphViz from '@/components/CausalGraphViz';
import { apiGet, apiPost } from '@/lib/api';
import Reveal from '@/components/Reveal';

export default function CausalAnalysisPage() {
  const [analysisResult, setAnalysisResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fetchingData, setFetchingData] = useState(false);

  const [formData, setFormData] = useState({
    transaction_hash: '',  // Empty by default - user MUST enter valid tx hash
    gas_price: '',
    value: '',
    gas_used: '',
    sender_tx_count: '',
    contract_age: '',
    is_contract_creation: 'false',
  });

  const handleFetchBlockchainData = async () => {
    if (!formData.transaction_hash || formData.transaction_hash.trim() === '') {
      setError('Please enter a transaction hash first');
      return;
    }

    if (!formData.transaction_hash.match(/^0x[a-fA-F0-9]{64}$/)) {
      setError('Invalid transaction hash format. Must be 66 characters starting with 0x');
      return;
    }

    setFetchingData(true);
    setError(null);

    try {
      // Fetch transaction data from blockchain via backend
      const txData = await apiGet<any>(`/api/blockchain/transaction/${formData.transaction_hash}`);

      // Auto-fill form fields with blockchain data
      // API returns features in both root level and features object for compatibility
      setFormData(prev => ({
        ...prev,
        gas_price: (txData.gas_price ?? txData.features?.gas_price)?.toString() || '',
        value: (txData.value ?? txData.features?.value)?.toString() || '',
        gas_used: (txData.gas_used ?? txData.features?.gas_used)?.toString() || '',
        sender_tx_count: (txData.sender_tx_count ?? txData.features?.sender_tx_count)?.toString() || '',
        contract_age: (txData.contract_age ?? txData.features?.contract_age)?.toString() || '',
        is_contract_creation: (txData.is_contract_creation ?? txData.features?.is_contract_creation) ? 'true' : 'false',
        // Also set the calculated fields
        gas_price_deviation: (txData.gas_price_deviation ?? txData.features?.gas_price_deviation)?.toString() || '',
        block_gas_used_ratio: (txData.block_gas_used_ratio ?? txData.features?.block_gas_used_ratio)?.toString() || '',
        amount: (txData.amount ?? txData.features?.amount)?.toString() || '',
      }));

      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch transaction data');
    } finally {
      setFetchingData(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Validate transaction hash before submitting
    if (!formData.transaction_hash || formData.transaction_hash.trim() === '') {
      setError('Please enter a valid transaction hash');
      return;
    }

    if (!formData.transaction_hash.match(/^0x[a-fA-F0-9]{64}$/)) {
      setError('Invalid transaction hash format. Must be 66 characters starting with 0x');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // Only include features if user has entered values
      const features: any = {};

      if (formData.gas_price) features.gas_price = parseFloat(formData.gas_price);
      if (formData.value) features.value = parseFloat(formData.value);
      if (formData.gas_used) features.gas_used = parseFloat(formData.gas_used);
      if (formData.sender_tx_count) features.sender_tx_count = parseFloat(formData.sender_tx_count);
      if (formData.contract_age) features.contract_age = parseFloat(formData.contract_age);
      if (formData.is_contract_creation) features.is_contract_creation = formData.is_contract_creation === 'true' ? 1 : 0;

      const requestBody: any = {
        transaction_hash: formData.transaction_hash,
        treatment_features: ['gas_price', 'value', 'sender_tx_count'],
      };

      // Only send features if user provided any overrides
      if (Object.keys(features).length > 0) {
        requestBody.features = features;
      }

      const data = await apiPost('/api/analyze/causal/', requestBody);
      setAnalysisResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const inputClass =
    'w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-900 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500';
  const labelClass = 'mb-1 block text-sm font-medium text-slate-700';

  return (
    <div className="mx-auto max-w-6xl px-4 py-12 sm:px-6">
      {/* Header */}
      <div className="mb-6 animate-enter">
        <h1 className="text-3xl font-bold tracking-tight text-slate-900">Causal Explainable AI</h1>
        <p className="mt-2 text-slate-600">
          Beyond correlation — identify the true causal relationships behind a fraud prediction.
        </p>
      </div>

      {/* Explainer */}
      <Reveal className="mb-8 rounded-2xl bg-slate-900 p-6 text-slate-200">
        <h2 className="text-lg font-semibold text-white">How this differs from SHAP &amp; LIME</h2>
        <p className="mt-2 text-sm leading-relaxed text-slate-300">
          Traditional correlation-based methods tell you which features move together with the outcome.
          Causal inference goes further: it estimates genuine cause-and-effect, controls for confounders,
          and flags spurious correlations that would otherwise mislead a decision.
        </p>
      </Reveal>

      {/* Causal graph */}
      <Reveal className="mb-8">
        <CausalGraphViz />
      </Reveal>

      {/* Analysis form */}
      <Reveal className="mb-8 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-slate-900">Run causal analysis</h2>
        <form onSubmit={handleSubmit} className="mt-4 space-y-4">
          <div>
            <label className={labelClass}>
              Transaction hash <span className="text-red-500">*</span>
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                value={formData.transaction_hash}
                onChange={(e) => setFormData({ ...formData, transaction_hash: e.target.value })}
                placeholder="0x… (66 characters starting with 0x)"
                required
                className={`${inputClass} flex-1 font-mono text-sm`}
              />
              <button
                type="button"
                onClick={handleFetchBlockchainData}
                disabled={fetchingData || !formData.transaction_hash}
                className="tappable whitespace-nowrap rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {fetchingData ? 'Fetching…' : 'Fetch data'}
              </button>
            </div>
            <p className="mt-1 text-xs text-slate-500">
              Enter a transaction hash, then fetch to auto-fill the fields below with blockchain data.
            </p>
          </div>

          {/* Optional manual features */}
          <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
            <h3 className="text-sm font-semibold text-slate-900">Transaction features</h3>
            <p className="mb-3 mt-1 text-xs text-slate-500">
              Auto-filled from the blockchain. Override any value to test a hypothetical scenario.
            </p>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <label className={labelClass}>Gas price (Gwei)</label>
                <input type="number" step="0.1" value={formData.gas_price} onChange={(e) => setFormData({ ...formData, gas_price: e.target.value })} className={inputClass} />
              </div>
              <div>
                <label className={labelClass}>Value (ETH)</label>
                <input type="number" step="0.01" value={formData.value} onChange={(e) => setFormData({ ...formData, value: e.target.value })} className={inputClass} />
              </div>
              <div>
                <label className={labelClass}>Gas used</label>
                <input type="number" value={formData.gas_used} onChange={(e) => setFormData({ ...formData, gas_used: e.target.value })} className={inputClass} />
              </div>
              <div>
                <label className={labelClass}>Sender transaction count</label>
                <input type="number" value={formData.sender_tx_count} onChange={(e) => setFormData({ ...formData, sender_tx_count: e.target.value })} className={inputClass} />
              </div>
              <div>
                <label className={labelClass}>Contract age (days)</label>
                <input type="number" value={formData.contract_age} onChange={(e) => setFormData({ ...formData, contract_age: e.target.value })} className={inputClass} />
              </div>
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="tappable w-full rounded-lg bg-indigo-600 px-6 py-3 text-sm font-semibold text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:bg-slate-300"
          >
            {loading ? 'Analyzing…' : 'Perform causal analysis'}
          </button>
        </form>

        {error && (
          <div className="mt-4 rounded-lg border border-red-200 bg-red-50 p-4">
            <p className="text-sm font-medium text-red-700">Error: {error}</p>
          </div>
        )}
      </Reveal>

      {/* Results */}
      {analysisResult && (
        <Reveal className="space-y-6">
          {/* Causal effects */}
          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <h3 className="text-lg font-semibold text-slate-900">Causal effects (ACE)</h3>
            <div className="mt-4 space-y-3">
              {Object.entries(analysisResult.causal_effects).map(([feature, effectData]: [string, any]) => {
                const effect = effectData.average_causal_effect;
                const strength = effectData.strength;
                const mechanism = effectData.mechanism;
                return (
                  <div key={feature} className="rounded-lg border border-slate-200 bg-slate-50 p-4">
                    <div className="flex items-center justify-between">
                      <span className="font-medium capitalize text-slate-900">{feature.replace(/_/g, ' ')}</span>
                      <div className="text-right">
                        <div className={`text-lg font-bold ${effect > 0 ? 'text-red-600' : 'text-emerald-600'}`}>
                          {effect > 0 ? '+' : ''}{effect.toFixed(4)}
                        </div>
                        <div className="text-xs text-slate-500">Average causal effect</div>
                      </div>
                    </div>
                    <div className="mt-2 text-sm text-slate-600">
                      <div><strong className="text-slate-700">Strength:</strong> {strength}</div>
                      <div className="mt-1"><strong className="text-slate-700">Mechanism:</strong> {mechanism}</div>
                    </div>
                    {effectData.controlled_for && effectData.controlled_for.length > 0 && (
                      <div className="mt-2 text-xs text-slate-500">
                        Controlled for: {effectData.controlled_for.join(', ')}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Correlation vs causation */}
          {analysisResult.comparison && analysisResult.comparison.length > 0 && (
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <h3 className="text-lg font-semibold text-slate-900">Correlation vs causation</h3>
              <div className="mt-4 space-y-3">
                {analysisResult.comparison.map((comparison: any) => (
                  <div key={comparison.feature} className="rounded-lg border border-slate-200 bg-slate-50 p-4">
                    <div className="mb-2 font-medium capitalize text-slate-900">
                      {comparison.feature.replace(/_/g, ' ')}
                    </div>
                    <div className="mb-2 grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="text-slate-500">Correlation:</span>
                        <span className="ml-2 font-semibold text-slate-900">{comparison.correlation?.toFixed(4) || 'N/A'}</span>
                      </div>
                      <div>
                        <span className="text-slate-500">Causal effect:</span>
                        <span className="ml-2 font-semibold text-slate-900">{comparison.causal_effect?.toFixed(4) || 'N/A'}</span>
                      </div>
                    </div>
                    <div className="mb-2 text-xs text-slate-500">
                      Difference: {comparison.difference?.toFixed(4)} | Type: {comparison.relationship_type}
                    </div>
                    {comparison.interpretation && (
                      <div className="mt-2 text-sm italic text-slate-600">{comparison.interpretation}</div>
                    )}
                    {comparison.is_spurious && (
                      <div className="mt-2 inline-block rounded-full bg-amber-100 px-2.5 py-0.5 text-xs font-medium text-amber-800">
                        Spurious correlation detected
                      </div>
                    )}
                    {comparison.is_suppressed && (
                      <div className="mt-2 inline-block rounded-full bg-indigo-100 px-2.5 py-0.5 text-xs font-medium text-indigo-800">
                        Suppressed effect detected
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Confounders */}
          {analysisResult.confounders && Object.keys(analysisResult.confounders).length > 0 && (
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <h3 className="text-lg font-semibold text-slate-900">Confounding variables</h3>
              <p className="mt-1 text-sm text-slate-600">
                These variables create spurious correlations and must be controlled for accurate causal inference.
              </p>
              <div className="mt-4 space-y-3">
                {Object.entries(analysisResult.confounders).map(([treatment, confounderData]: [string, any]) => (
                  <div key={treatment} className="rounded-lg border border-amber-200 bg-amber-50 p-4">
                    <div className="mb-2 font-medium capitalize text-slate-900">
                      {treatment.replace(/_/g, ' ')}
                    </div>
                    {confounderData.confounders && confounderData.confounders.length > 0 && (
                      <div className="mb-1 text-sm text-slate-700">
                        <strong>Confounders:</strong> {confounderData.confounders.join(', ')}
                      </div>
                    )}
                    {confounderData.mediators && confounderData.mediators.length > 0 && (
                      <div className="mb-1 text-sm text-slate-700">
                        <strong>Mediators:</strong> {confounderData.mediators.join(', ')}
                      </div>
                    )}
                    <div className="mt-2 text-xs text-slate-500">
                      Backdoor paths: {confounderData.backdoor_paths || 0} | Adjustment needed: {confounderData.adjustment_needed ? 'Yes' : 'No'}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Interpretation */}
          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <h3 className="text-lg font-semibold text-slate-900">Interpretation</h3>
            <p className="mt-2 whitespace-pre-line text-slate-700">{analysisResult.interpretation}</p>
          </div>
        </Reveal>
      )}
    </div>
  );
}
