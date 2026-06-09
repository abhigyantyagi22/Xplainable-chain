'use client';

import { useState } from 'react';
import CausalGraphViz from '@/components/CausalGraphViz';
import { apiGet, apiPost } from '@/lib/api';

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

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50 p-8">
      <div className="max-w-7xl mx-auto">
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

        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent mb-2">
            Causal Explainable AI
          </h1>
          <p className="text-gray-600 text-lg">
            Beyond correlation: Identify true causal relationships in blockchain fraud detection
          </p>
        </div>

        {/* Research Contribution Banner */}
        <div className="bg-gradient-to-r from-purple-500 to-blue-500 text-white p-6 rounded-lg mb-8 shadow-lg">
          <h2 className="text-2xl font-bold mb-2">🔬 Novel Research Feature</h2>
          <p className="text-purple-100">
            This is the first implementation of <strong>Causal Explainable AI for Blockchain Fraud Detection</strong>.
            Unlike traditional correlation-based methods (SHAP, LIME), causal XAI identifies genuine cause-and-effect
            relationships while revealing spurious correlations created by confounders.
          </p>
        </div>

        {/* Causal Graph Visualization */}
        <div className="mb-8">
          <CausalGraphViz />
        </div>

        {/* Analysis Form */}
        <div className="bg-white rounded-lg shadow-lg p-6 mb-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">Run Causal Analysis</h2>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-1 gap-4 mb-4">
              <div className="col-span-full">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Transaction Hash <span className="text-red-500">*</span>
                </label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={formData.transaction_hash}
                    onChange={(e) => setFormData({ ...formData, transaction_hash: e.target.value })}
                    placeholder="0x... (66 characters starting with 0x)"
                    required
                    className="flex-1 px-3 py-2 border border-gray-300 rounded-md text-gray-900 focus:ring-2 focus:ring-purple-500"
                  />
                  <button
                    type="button"
                    onClick={handleFetchBlockchainData}
                    disabled={fetchingData || !formData.transaction_hash}
                    className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium whitespace-nowrap"
                  >
                    {fetchingData ? 'Fetching...' : '🔍 Fetch Data'}
                  </button>
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  Enter a transaction hash, then click "Fetch Data" to auto-fill the fields below with blockchain data.
                </p>
              </div>
            </div>
            
            {/* Optional Manual Features */}
            <div className="bg-blue-50 p-4 rounded-md mb-4">
              <h3 className="text-sm font-semibold text-blue-900 mb-2">Transaction Features</h3>
              <p className="text-xs text-blue-700 mb-3">
                These fields are auto-filled from blockchain. You can manually override them to test hypothetical scenarios.
              </p>
              <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Gas Price (Gwei)
                </label>
                <input
                  type="number"
                  step="0.1"
                  value={formData.gas_price}
                  onChange={(e) => setFormData({ ...formData, gas_price: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md text-gray-900"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Value (ETH)
                </label>
                <input
                  type="number"
                  step="0.01"
                  value={formData.value}
                  onChange={(e) => setFormData({ ...formData, value: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md text-gray-900"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Gas Used
                </label>
                <input
                  type="number"
                  value={formData.gas_used}
                  onChange={(e) => setFormData({ ...formData, gas_used: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md text-gray-900"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Sender Transaction Count
                </label>
                <input
                  type="number"
                  value={formData.sender_tx_count}
                  onChange={(e) => setFormData({ ...formData, sender_tx_count: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md text-gray-900"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Contract Age (days)
                </label>
                <input
                  type="number"
                  value={formData.contract_age}
                  onChange={(e) => setFormData({ ...formData, contract_age: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md text-gray-900"
                />
              </div>
            </div>
            </div>
            
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-gradient-to-r from-blue-600 to-purple-600 text-white py-3 px-6 rounded-lg font-semibold hover:from-blue-700 hover:to-purple-700 disabled:opacity-50 transition-all"
            >
              {loading ? 'Analyzing...' : 'Perform Causal Analysis'}
            </button>
          </form>

          {error && (
            <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-red-600 font-semibold">Error: {error}</p>
            </div>
          )}
        </div>

        {/* Analysis Results */}
        {analysisResult && (
          <div className="space-y-6">
            {/* Causal Effects */}
            <div className="bg-white rounded-lg shadow-lg p-6">
              <h3 className="text-xl font-bold text-gray-900 mb-4">Causal Effects (ACE)</h3>
              <div className="space-y-3">
                {Object.entries(analysisResult.causal_effects).map(([feature, effectData]: [string, any]) => {
                  const effect = effectData.average_causal_effect;
                  const strength = effectData.strength;
                  const mechanism = effectData.mechanism;
                  return (
                    <div key={feature} className="p-4 bg-gray-50 rounded-lg">
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-medium text-gray-900 capitalize">{feature.replace(/_/g, ' ')}</span>
                        <div className="text-right">
                          <div className="font-bold text-lg" style={{ color: effect > 0 ? '#ef4444' : '#10b981' }}>
                            {effect > 0 ? '+' : ''}{effect.toFixed(4)}
                          </div>
                          <div className="text-xs text-gray-500">Average Causal Effect</div>
                        </div>
                      </div>
                      <div className="text-sm text-gray-600 mt-2">
                        <div><strong>Strength:</strong> {strength}</div>
                        <div className="mt-1"><strong>Mechanism:</strong> {mechanism}</div>
                      </div>
                      {effectData.controlled_for && effectData.controlled_for.length > 0 && (
                        <div className="text-xs text-gray-500 mt-2">
                          Controlled for: {effectData.controlled_for.join(', ')}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Correlation vs Causation Comparison */}
            {analysisResult.comparison && analysisResult.comparison.length > 0 && (
              <div className="bg-white rounded-lg shadow-lg p-6">
                <h3 className="text-xl font-bold text-gray-900 mb-4">Correlation vs Causation</h3>
                <div className="space-y-3">
                  {analysisResult.comparison.map((comparison: any) => (
                    <div key={comparison.feature} className="p-4 bg-gray-50 rounded-lg">
                      <div className="font-medium text-gray-900 capitalize mb-2">
                        {comparison.feature.replace(/_/g, ' ')}
                      </div>
                      <div className="grid grid-cols-2 gap-4 text-sm mb-2">
                        <div>
                          <span className="text-gray-600">Correlation:</span>
                          <span className="ml-2 font-semibold">{comparison.correlation?.toFixed(4) || 'N/A'}</span>
                        </div>
                        <div>
                          <span className="text-gray-600">Causal Effect:</span>
                          <span className="ml-2 font-semibold">{comparison.causal_effect?.toFixed(4) || 'N/A'}</span>
                        </div>
                      </div>
                      <div className="text-xs text-gray-600 mb-2">
                        Difference: {comparison.difference?.toFixed(4)} | Type: {comparison.relationship_type}
                      </div>
                      {comparison.interpretation && (
                        <div className="text-sm text-gray-700 italic mt-2">
                          {comparison.interpretation}
                        </div>
                      )}
                      {comparison.is_spurious && (
                        <div className="mt-2 px-3 py-1 bg-yellow-100 text-yellow-800 text-xs rounded-full inline-block">
                          ⚠️ Spurious Correlation Detected
                        </div>
                      )}
                      {comparison.is_suppressed && (
                        <div className="mt-2 px-3 py-1 bg-blue-100 text-blue-800 text-xs rounded-full inline-block">
                           Suppressed Effect Detected
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Confounders */}
            {analysisResult.confounders && Object.keys(analysisResult.confounders).length > 0 && (
              <div className="bg-white rounded-lg shadow-lg p-6">
                <h3 className="text-xl font-bold text-gray-900 mb-4">Confounding Variables</h3>
                <p className="text-gray-600 text-sm mb-4">
                  These variables create spurious correlations and must be controlled for accurate causal inference.
                </p>
                <div className="space-y-3">
                  {Object.entries(analysisResult.confounders).map(([treatment, confounderData]: [string, any]) => (
                    <div key={treatment} className="p-4 bg-orange-50 border border-orange-200 rounded-lg">
                      <div className="font-medium text-gray-900 capitalize mb-2">
                        {treatment.replace(/_/g, ' ')}
                      </div>
                      {confounderData.confounders && confounderData.confounders.length > 0 && (
                        <div className="text-sm text-gray-700 mb-1">
                          <strong>Confounders:</strong> {confounderData.confounders.join(', ')}
                        </div>
                      )}
                      {confounderData.mediators && confounderData.mediators.length > 0 && (
                        <div className="text-sm text-gray-700 mb-1">
                          <strong>Mediators:</strong> {confounderData.mediators.join(', ')}
                        </div>
                      )}
                      <div className="text-xs text-gray-600 mt-2">
                        Backdoor paths: {confounderData.backdoor_paths || 0} | 
                        Adjustment needed: {confounderData.adjustment_needed ? 'Yes' : 'No'}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Interpretation */}
            <div className="bg-gradient-to-r from-green-50 to-blue-50 rounded-lg p-6 border border-green-200">
              <h3 className="text-xl font-bold text-gray-900 mb-3"> Interpretation</h3>
              <p className="text-gray-700 whitespace-pre-line">{analysisResult.interpretation}</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
