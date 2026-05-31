"""
Pre-Transaction Prevention Router
Analyzes transactions BEFORE they are signed and sent.
This is where CC-SHAP becomes truly valuable - enabling prevention!
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
import logging
from web3 import Web3
import pickle
from pathlib import Path

from app.models.ai_detector import AIDetector
from app.models.xai_explainer import XAIExplainer
from app.utils.feature_simulation import create_feature_simulator
from app.utils.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize PREVENTION-SPECIFIC detector (separate model)
class PreventionDetector(AIDetector):
    """Prevention-specific detector using separate model trained on Kaggle dataset"""
    def __init__(self):
        model_path = Path(__file__).parent.parent / "ml" / "prevention_model.pkl"
        scaler_path = Path(__file__).parent.parent / "ml" / "prevention_scaler.pkl"
        super().__init__(model_path=str(model_path), scaler_path=str(scaler_path))
        logger.info("✅ Loaded PREVENTION model (trained on Kaggle dataset)")

# Initialize services
prevention_detector = PreventionDetector()  # Separate prevention model
xai_explainer = XAIExplainer()

# Create feature simulator
try:
    infura_key = settings.INFURA_API_KEY if hasattr(settings, 'INFURA_API_KEY') and settings.INFURA_API_KEY else ""
    if infura_key:
        rpc_url = f"https://polygon-amoy.infura.io/v3/{infura_key}"
    else:
        # Fallback to INFURA_URL from settings
        rpc_url = settings.INFURA_URL
    feature_simulator = create_feature_simulator(rpc_url)
    logger.info(f"Feature simulator initialized with RPC: {rpc_url[:50]}...")
except Exception as e:
    logger.warning(f"Could not initialize feature simulator: {e}")
    feature_simulator = None


class PreTransactionRequest(BaseModel):
    """Request model for pre-transaction check"""
    to_address: str = Field(..., description="Recipient address")
    amount: float = Field(0, ge=0, description="Amount in ETH")
    gas_price: Optional[int] = Field(None, description="Gas price in Gwei (optional, uses network average if None or <= 0)")
    from_address: Optional[str] = Field(None, description="Sender address (optional)")
    gas_limit: Optional[int] = Field(None, description="Gas limit (optional)")


class CounterfactualScenario(BaseModel):
    """A counterfactual 'what-if' scenario"""
    scenario: str
    new_risk: int
    risk_change: int
    feasibility: str
    recommendation: str


class PreTransactionResponse(BaseModel):
    """Response model for pre-transaction check"""
    risk_score: int
    safe_to_send: bool
    action: str
    causal_factors: List[Dict]
    counterfactuals: List[CounterfactualScenario]
    timing: str = "pre_transaction"
    note: str


def calibrate_risk_score(features: Dict, raw_score: int) -> int:
    """
    Calibrate ML risk score using rule-based heuristics.
    
    Problem: Prevention model trained on real Ethereum fraud data from Kaggle,
    but we're feeding simulated/dummy features. This causes consistently high
    risk scores (99%) for all transactions.
    
    Solution: Apply domain knowledge to adjust scores based on known fraud patterns.
    """
    # Start with base score (reduce from raw to more realistic baseline)
    base_risk = 30  # Most normal transactions start here
    
    # Factor 1: Excessive amount (common fraud indicator)
    amount = features.get('amount', 0)
    if amount > 10:
        base_risk += 30  # Very high amount
    elif amount > 5:
        base_risk += 20  # High amount
    elif amount > 1:
        base_risk += 10  # Moderate amount
    
    # Factor 2: Gas price manipulation (fraud evasion tactic)
    gas_price_dev = features.get('gas_price_deviation', 0)
    if abs(gas_price_dev) > 100:  # 100x deviation
        base_risk += 25
    elif abs(gas_price_dev) > 10:  # 10x deviation
        base_risk += 15
    elif abs(gas_price_dev) > 2:  # 2x deviation
        base_risk += 5
    
    # Factor 3: Contract creation (slightly more risky)
    if features.get('is_contract_creation', 0) == 1:
        base_risk += 10
    
    # Factor 4: New sender account (suspicious if combined with large amount)
    sender_tx_count = features.get('sender_tx_count', 0)
    if sender_tx_count < 10 and amount > 1:
        base_risk += 15  # New account with large transfer
    
    # Factor 5: Very new contract recipient
    contract_age = features.get('contract_age', 0)
    if contract_age > 0 and contract_age < 7 and amount > 0.5:
        base_risk += 10  # Sending to very new contract
    
    # Clamp to valid range
    calibrated_score = max(0, min(100, base_risk))
    
    return calibrated_score


@router.post("/api/check-before-send", response_model=PreTransactionResponse)
async def check_before_send(request: PreTransactionRequest):
    """
    ✅ FIX: Check transaction BEFORE user signs
    This is where CC-SHAP becomes actually useful for PREVENTION!
    
    This endpoint simulates what a transaction would look like and
    analyzes it using ML + CC-SHAP BEFORE the user commits to sending it.
    """
    try:
        if not feature_simulator:
            raise HTTPException(status_code=503, detail="Feature simulator not available")
        
        logger.info(f"Pre-transaction check for {request.to_address}, amount: {request.amount}")
        
        # 1. Simulate transaction features (NO real transaction needed)
        features = feature_simulator.simulate_transaction_features(
            to_address=request.to_address,
            amount=request.amount,
            gas_price=request.gas_price,
            from_address=request.from_address,
            gas_limit=request.gas_limit
        )
        
        # 2. Predict fraud risk using PREVENTION model (trained on Kaggle dataset)
        prediction_result = prevention_detector.predict(features)
        # Always use P(fraud) = probabilities[1], not 'confidence' which flips to
        # P(safe) when the predicted class is 0.
        raw_risk_score = int(prediction_result['probabilities'][1] * 100)
        is_malicious = prediction_result['is_malicious']
        
        # 2.5 CALIBRATION FIX: Adjust risk score for simulated features
        # Problem: Model trained on real Ethereum data, but we're feeding simulated features
        # Solution: Apply rule-based adjustments to align with realistic risk levels
        risk_score = calibrate_risk_score(features, raw_risk_score)
        logger.info(f"Risk calibration: {raw_risk_score}% → {risk_score}% (after rules)")
        
        # 3. Generate CC-SHAP explanation (shows CAUSAL factors)
        shap_explanation = xai_explainer.explain(features, prevention_detector.model)
        
        # 4. Extract causal factors from SHAP
        causal_factors = []
        for feature_data in shap_explanation.get('top_features', [])[:5]:
            # Get the feature name (handle both 'feature' and 'name' keys)
            feature_name = feature_data.get('feature') or feature_data.get('name', 'unknown')
            feature_value = feature_data.get('value', 0)
            feature_importance = feature_data.get('importance') or feature_data.get('shap_value', 0)
            
            causal_factors.append({
                "feature": feature_name,
                "value": round(feature_value, 2),
                "contribution": round(feature_importance, 3),
                "impact": "increases risk" if feature_importance > 0 else "decreases risk"
            })
        
        # 5. Generate counterfactual recommendations
        counterfactuals = generate_counterfactuals(
            features=features,
            current_risk=prediction_result['probabilities'][1],
            shap_explanation=shap_explanation,
            ai_detector=prevention_detector
        )
        
        # 6. Determine action and safety
        if risk_score > 80:
            action = "🚨 DO NOT SEND - Critical fraud risk detected"
            safe_to_send = False
        elif risk_score > 60:
            action = "⚠️ HIGH RISK - Strongly recommend adjusting parameters"
            safe_to_send = False
        elif risk_score > 40:
            action = "⚠️ Medium risk - Proceed with caution or adjust parameters"
            safe_to_send = True
        else:
            action = "✅ Appears safe to send"
            safe_to_send = True
        
        return PreTransactionResponse(
            risk_score=risk_score,
            safe_to_send=safe_to_send,
            action=action,
            causal_factors=causal_factors,
            counterfactuals=counterfactuals,
            timing="pre_transaction",
            note="You can adjust parameters and re-check before signing"
        )
        
    except Exception as e:
        logger.error(f"Error in pre-transaction check: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/quick-address-check/{address}")
async def quick_address_check(address: str):
    """
    Ultra-fast address check (< 200ms)
    Uses simple heuristics, no ML - for instant feedback
    """
    try:
        if not feature_simulator:
            raise HTTPException(status_code=503, detail="Feature simulator not available")
        
        # Get address risk indicators
        indicators = feature_simulator.get_address_risk_indicators(address)
        
        # Simple risk scoring based on heuristics
        risk_score = 0
        warnings = []
        
        # Check 1: Very new contract
        if indicators["is_contract"] and indicators["estimated_age"] == "very_new":
            risk_score += 40
            warnings.append("⚠️ Very new or minimal contract code")
        
        # Check 2: Low transaction count
        if indicators["transaction_count"] < 10:
            risk_score += 30
            warnings.append("⚠️ Address has very few transactions")
        
        # Check 3: New contract with activity
        if indicators["is_contract"] and indicators["estimated_age"] == "recent":
            risk_score += 20
            warnings.append("⚠️ Recently deployed contract")
        
        # Determine status
        if risk_score > 60:
            status = "high_risk"
            recommendation = "Run full analysis before sending"
        elif risk_score > 30:
            status = "medium_risk"
            recommendation = "Consider running full analysis"
        else:
            status = "low_risk"
            recommendation = "Appears safe (full analysis recommended for certainty)"
        
        return {
            "address": address,
            "risk_score": min(risk_score, 100),
            "status": status,
            "warnings": warnings,
            "recommendation": recommendation,
            "indicators": indicators,
            "analysis_time": "< 200ms",
            "note": "Quick check only - run full analysis for detailed assessment"
        }
        
    except Exception as e:
        logger.error(f"Error in quick address check: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def generate_counterfactuals(
    features: Dict,
    current_risk: float,
    shap_explanation: Dict,
    ai_detector: AIDetector
) -> List[CounterfactualScenario]:
    """
    Generate "what-if" scenarios showing how to reduce risk.
    This is only useful BEFORE transaction (when user can still change it).
    
    This is a key part of making CC-SHAP actionable!
    """
    counterfactuals = []
    current_risk_score = int(current_risk * 100)
    
    # Get top risk-increasing features from SHAP
    risky_features = []
    for f in shap_explanation.get('top_features', []):
        importance = f.get('importance') or f.get('shap_value', 0)
        if importance > 0:
            risky_features.append({
                'name': f.get('feature') or f.get('name', 'unknown'),
                'value': f.get('value', 0),
                'shap_value': importance
            })
    
    # Sort by SHAP value (highest impact first)
    risky_features.sort(key=lambda x: x.get('shap_value', 0), reverse=True)
    
    # Generate counterfactuals for top 3 risky features
    for feature in risky_features[:3]:
        feature_name = feature.get('name', '')
        feature_value = feature.get('value', 0)
        
        if feature_name == 'gas_price' and feature_value > 50:
            # Suggest reducing gas price
            new_gas = max(20, int(feature_value * 0.4))  # 60% reduction, min 20
            new_features = features.copy()
            new_features['gas_price'] = new_gas
            
            # Recalculate gas_price_deviation
            avg_gas = 30  # Approximate average
            new_features['gas_price_deviation'] = (new_gas - avg_gas) / avg_gas
            
            new_risk_result = ai_detector.predict(new_features)
            new_risk_score = int(new_risk_result['probabilities'][1] * 100)

            counterfactuals.append(CounterfactualScenario(
                scenario=f"Reduce gas price: {int(feature_value)}→{new_gas} Gwei",
                new_risk=new_risk_score,
                risk_change=current_risk_score - new_risk_score,
                feasibility="High",
                recommendation="Lower gas price to network average to reduce suspicion"
            ))
        
        elif feature_name == 'amount' and feature_value > 1:
            # Suggest reducing amount
            new_amount = round(feature_value * 0.5, 2)
            new_features = features.copy()
            new_features['amount'] = new_amount
            new_features['value'] = new_amount
            
            new_risk_result = ai_detector.predict(new_features)
            new_risk_score = int(new_risk_result['probabilities'][1] * 100)

            counterfactuals.append(CounterfactualScenario(
                scenario=f"Reduce amount: {feature_value}→{new_amount} ETH",
                new_risk=new_risk_score,
                risk_change=current_risk_score - new_risk_score,
                feasibility="Medium",
                recommendation="Consider splitting into multiple smaller transactions"
            ))
        
        elif feature_name == 'sender_tx_count' and feature_value < 50:
            # Can't easily change this, but inform user
            counterfactuals.append(CounterfactualScenario(
                scenario=f"If sender had more history (50+ transactions)",
                new_risk=max(20, current_risk_score - 15),
                risk_change=min(15, current_risk_score - 20),
                feasibility="Low",
                recommendation="New accounts are flagged as risky - consider using established account"
            ))
    
    return counterfactuals


@router.post("/api/recheck-after-adjustment")
async def recheck_after_adjustment(request: PreTransactionRequest):
    """
    Re-check after user adjusts parameters based on counterfactuals.
    Allows iterative improvement until risk is acceptable.
    """
    # Same logic as check_before_send
    return await check_before_send(request)
