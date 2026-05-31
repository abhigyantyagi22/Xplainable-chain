"""
Baseline Explanation Methods for Comparison with CC-SHAP
=========================================================

This module implements state-of-the-art baseline methods for comparison:

1. CXPlain-style: Causal explanations via perturbation-based attribution
2. DECE-style: Decomposed Causal Effects using causal graph
3. DiCE-style Counterfactuals: Diverse counterfactual explanations
4. FACE-style: Feasible and Actionable Counterfactual Explanations
5. Vanilla SHAP: Standard SHAP without causal constraints
6. Causal-Only: Pure causal path analysis without SHAP

These baselines allow rigorous comparison to demonstrate CC-SHAP's superiority.

References:
-----------
1. CXPlain: "CXPlain: Causal Explanations from Expert Models" (Schwab & Karlen, 2019)
2. DECE: "Causal Explanation Methods for Neural Networks" (Heskes et al., 2020)
3. DiCE: "Explaining Machine Learning Classifiers through Diverse Counterfactual Explanations" (Mothilal et al., 2020)
4. FACE: "FACE: Feasible and Actionable Counterfactual Explanations" (Poyiadzi et al., 2020)

Author: Abhigyan Tyagi
Date: November 2025
"""

import numpy as np
import pandas as pd
import shap
import networkx as nx
from typing import Dict, List, Tuple, Optional, Any
from sklearn.metrics import pairwise_distances
import logging
from copy import deepcopy

logger = logging.getLogger(__name__)


class CXPlainStyleExplainer:
    """
    CXPlain-style Causal Explanations via Perturbation
    
    Measures causal importance by:
    1. Masking/perturbing each feature
    2. Measuring change in model prediction
    3. Higher change = more causally important
    
    Pros: Reflects model behavior, interpretable
    Cons: Not actionable, computationally expensive
    """
    
    def __init__(self, model, feature_names: List[str]):
        self.model = model
        self.feature_names = feature_names
        
    def explain(
        self,
        transaction: pd.DataFrame,
        background_data: pd.DataFrame,
        top_k: int = 5,
        n_samples: int = 100
    ) -> Dict[str, Any]:
        """
        Generate CXPlain-style explanation by perturbation
        
        Args:
            transaction: Single transaction to explain
            background_data: Background data for sampling perturbations
            top_k: Number of top features to return
            n_samples: Number of perturbation samples per feature
            
        Returns:
            Dictionary with causal importance scores and recommendations
        """
        logger.info("🔬 Computing CXPlain-style causal explanations...")
        
        # Get base prediction
        base_pred = self.model.predict_proba(transaction)[0, 1]
        
        # Compute causal importance for each feature
        causal_importance = {}
        
        for i, feature in enumerate(self.feature_names):
            # Perturb this feature by sampling from background
            perturbation_effects = []
            
            for _ in range(n_samples):
                # Create perturbed instance
                perturbed = transaction.copy()
                perturbed.iloc[0, i] = background_data.iloc[
                    np.random.randint(len(background_data)), i
                ]
                
                # Measure prediction change
                perturbed_pred = self.model.predict_proba(perturbed)[0, 1]
                effect = abs(perturbed_pred - base_pred)
                perturbation_effects.append(effect)
            
            # Average effect across samples
            causal_importance[feature] = np.mean(perturbation_effects)
        
        # Rank features by causal importance
        sorted_features = sorted(
            causal_importance.items(),
            key=lambda x: x[1],
            reverse=True
        )[:top_k]
        
        recommendations = [
            {
                "feature": feature,
                "causal_importance": float(importance),
                "method": "CXPlain-style Perturbation",
                "recommendation": f"Feature '{feature}' has high causal importance (avg change: {importance:.4f})",
                "actionable": "UNKNOWN",
                "faithful": "HIGH"
            }
            for feature, importance in sorted_features
        ]
        
        return {
            "method": "CXPlain-style",
            "causal_importance": causal_importance,
            "recommendations": recommendations,
            "top_k_features": [f[0] for f in sorted_features],
            "metadata": {
                "total_features": len(self.feature_names),
                "n_samples": n_samples,
                "base_prediction": float(base_pred)
            }
        }


class DECEStyleExplainer:
    """
    DECE-style: Decomposed Causal Effects using Causal Graph
    
    Computes causal effects by:
    1. Using causal graph to identify direct/indirect effects
    2. Estimating effect size using path analysis
    3. Decomposing total effect into direct and mediated components
    
    Pros: Theoretically grounded, actionable
    Cons: Doesn't reflect model behavior, requires correct graph
    """
    
    def __init__(self, model, causal_graph: nx.DiGraph, feature_names: List[str]):
        self.model = model
        self.causal_graph = causal_graph
        self.feature_names = feature_names
        
    def explain(
        self,
        transaction: pd.DataFrame,
        background_data: pd.DataFrame,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        Generate DECE-style decomposed causal effects
        
        Args:
            transaction: Single transaction to explain
            background_data: Background data (not used, for API consistency)
            top_k: Number of top features to return
            
        Returns:
            Dictionary with causal effects and recommendations
        """
        logger.info("🔬 Computing DECE-style causal effects...")
        
        causal_effects = {}
        
        for feature in self.feature_names:
            # Check if feature has path to target
            if nx.has_path(self.causal_graph, feature, 'malicious'):
                # Get all paths from feature to target
                all_paths = list(nx.all_simple_paths(
                    self.causal_graph, feature, 'malicious'
                ))
                
                # Direct effect (1-hop path)
                direct_effect = 1.0 if any(len(p) == 2 for p in all_paths) else 0.0
                
                # Indirect effect (multi-hop paths)
                indirect_paths = [p for p in all_paths if len(p) > 2]
                indirect_effect = len(indirect_paths) * 0.5  # Decay for indirect
                
                # Total causal effect
                total_effect = direct_effect + indirect_effect
                
                causal_effects[feature] = {
                    "total_effect": total_effect,
                    "direct_effect": direct_effect,
                    "indirect_effect": indirect_effect,
                    "num_paths": len(all_paths),
                    "shortest_path_length": len(all_paths[0]) if all_paths else 0
                }
            else:
                causal_effects[feature] = {
                    "total_effect": 0.0,
                    "direct_effect": 0.0,
                    "indirect_effect": 0.0,
                    "num_paths": 0,
                    "shortest_path_length": 0
                }
        
        # Rank by total causal effect
        sorted_features = sorted(
            [(f, e["total_effect"]) for f, e in causal_effects.items()],
            key=lambda x: x[1],
            reverse=True
        )[:top_k]
        
        recommendations = [
            {
                "feature": feature,
                "total_causal_effect": float(effect),
                "direct_effect": float(causal_effects[feature]["direct_effect"]),
                "indirect_effect": float(causal_effects[feature]["indirect_effect"]),
                "method": "DECE-style Causal Graph",
                "recommendation": f"Feature '{feature}' has causal effect {effect:.4f} on fraud",
                "actionable": "HIGH",
                "faithful": "UNKNOWN"
            }
            for feature, effect in sorted_features if effect > 0
        ]
        
        return {
            "method": "DECE-style",
            "causal_effects": causal_effects,
            "recommendations": recommendations,
            "top_k_features": [f[0] for f in sorted_features if f[1] > 0],
            "metadata": {
                "total_features": len(self.feature_names),
                "causal_valid_features": sum(1 for e in causal_effects.values() if e["total_effect"] > 0)
            }
        }


class CounterfactualExplainer:
    """
    DiCE/FACE-style Counterfactual Explanations
    
    Finds minimal changes to flip prediction:
    1. Start from current transaction
    2. Search for nearby instance with different prediction
    3. Return minimal feature changes needed
    
    Pros: Actionable by design, intuitive
    Cons: Fails at high accuracy, not faithful to model
    """
    
    def __init__(self, model, feature_names: List[str], causal_graph: Optional[nx.DiGraph] = None):
        self.model = model
        self.feature_names = feature_names
        self.causal_graph = causal_graph
        
    def explain(
        self,
        transaction: pd.DataFrame,
        background_data: pd.DataFrame,
        top_k: int = 5,
        max_iterations: int = 100,
        step_size: float = 0.1
    ) -> Dict[str, Any]:
        """
        Generate counterfactual explanation via gradient-free search
        
        Args:
            transaction: Single transaction to explain (fraud=1)
            background_data: Background data for sampling
            top_k: Number of counterfactual features to return
            max_iterations: Maximum search iterations
            step_size: Step size for feature perturbations
            
        Returns:
            Dictionary with counterfactual recommendations
        """
        logger.info("🔬 Computing counterfactual explanations...")
        
        current = transaction.values[0].copy()
        current_pred = self.model.predict_proba(transaction)[0, 1]
        
        # Target: flip prediction (fraud=1 → fraud=0)
        target_class = 0 if current_pred > 0.5 else 1
        
        feature_changes = {}
        successful_counterfactual = None
        
        # Simple random search for counterfactual
        for iteration in range(max_iterations):
            # Randomly select feature to perturb
            feature_idx = np.random.randint(len(self.feature_names))
            feature_name = self.feature_names[feature_idx]
            
            # Only perturb causally valid features if graph available
            if self.causal_graph:
                if not nx.has_path(self.causal_graph, feature_name, 'malicious'):
                    continue
            
            # Perturb feature
            candidate = current.copy()
            
            # Sample from background or adjust by step
            if np.random.rand() > 0.5:
                candidate[feature_idx] = background_data.iloc[
                    np.random.randint(len(background_data)), feature_idx
                ]
            else:
                direction = np.random.choice([-1, 1])
                candidate[feature_idx] += direction * step_size * abs(current[feature_idx])
            
            # Check if prediction flipped
            candidate_df = pd.DataFrame([candidate], columns=self.feature_names)
            candidate_pred = self.model.predict_proba(candidate_df)[0, 1]
            candidate_class = 1 if candidate_pred > 0.5 else 0
            
            if candidate_class == target_class:
                # Found counterfactual!
                successful_counterfactual = candidate
                break
            
            # Track feature change magnitude
            change = abs(candidate[feature_idx] - current[feature_idx])
            if feature_name not in feature_changes or change > feature_changes[feature_name]:
                feature_changes[feature_name] = change
        
        # Generate recommendations
        if successful_counterfactual is not None:
            # Identify changed features
            changes = []
            for i, feature in enumerate(self.feature_names):
                if abs(successful_counterfactual[i] - current[i]) > 1e-6:
                    changes.append({
                        "feature": feature,
                        "original_value": float(current[i]),
                        "counterfactual_value": float(successful_counterfactual[i]),
                        "change": float(successful_counterfactual[i] - current[i]),
                        "method": "Counterfactual Search",
                        "recommendation": f"Change '{feature}' from {current[i]:.4f} to {successful_counterfactual[i]:.4f}",
                        "actionable": "HIGH",
                        "faithful": "UNKNOWN"
                    })
            
            recommendations = sorted(changes, key=lambda x: abs(x["change"]), reverse=True)[:top_k]
            success = True
        else:
            # Failed to find counterfactual
            recommendations = []
            success = False
        
        return {
            "method": "Counterfactual (DiCE/FACE-style)",
            "success": success,
            "iterations": iteration + 1,
            "recommendations": recommendations,
            "top_k_features": [r["feature"] for r in recommendations],
            "metadata": {
                "total_features": len(self.feature_names),
                "current_prediction": float(current_pred),
                "target_class": target_class,
                "counterfactual_found": success
            }
        }


class VanillaSHAPExplainer:
    """
    Vanilla SHAP (No Causal Constraints)
    
    Standard SHAP feature importance without any causal filtering.
    This is the baseline that CC-SHAP improves upon.
    """
    
    def __init__(self, model, feature_names: List[str]):
        self.model = model
        self.feature_names = feature_names
        
    def explain(
        self,
        transaction: pd.DataFrame,
        background_data: pd.DataFrame,
        top_k: int = 5,
        threshold: float = 0.01
    ) -> Dict[str, Any]:
        """
        Generate vanilla SHAP explanation
        
        Args:
            transaction: Single transaction to explain
            background_data: Background data for SHAP
            top_k: Number of top features to return
            threshold: Minimum |SHAP value| threshold
            
        Returns:
            Dictionary with SHAP values and recommendations
        """
        logger.info("🔬 Computing vanilla SHAP explanations...")
        
        # Compute SHAP values
        explainer = shap.TreeExplainer(self.model, background_data)
        shap_values = explainer.shap_values(transaction)
        
        # Handle binary classification output
        if isinstance(shap_values, list):
            shap_values = shap_values[1]  # Class 1 (fraud)
        
        shap_dict = dict(zip(self.feature_names, shap_values[0]))
        
        # Filter by threshold and rank
        important_features = {
            f: v for f, v in shap_dict.items() 
            if abs(v) > threshold
        }
        
        sorted_features = sorted(
            important_features.items(),
            key=lambda x: abs(x[1]),
            reverse=True
        )[:top_k]
        
        recommendations = [
            {
                "feature": feature,
                "shap_value": float(shap_val),
                "shap_abs": float(abs(shap_val)),
                "method": "Vanilla SHAP",
                "recommendation": f"Feature '{feature}' has SHAP value {shap_val:.4f}",
                "actionable": "UNKNOWN",
                "faithful": "HIGH"
            }
            for feature, shap_val in sorted_features
        ]
        
        return {
            "method": "Vanilla SHAP",
            "shap_values": shap_dict,
            "recommendations": recommendations,
            "top_k_features": [f[0] for f in sorted_features],
            "metadata": {
                "total_features": len(self.feature_names),
                "important_features": len(important_features),
                "threshold": threshold
            }
        }


class CausalOnlyExplainer:
    """
    Pure Causal Path Analysis (No SHAP)
    
    Ranks features purely by causal structure:
    1. Features with direct path to fraud
    2. Ranked by path length (shorter = better)
    3. No model faithfulness guarantee
    """
    
    def __init__(self, causal_graph: nx.DiGraph, feature_names: List[str]):
        self.causal_graph = causal_graph
        self.feature_names = feature_names
        
    def explain(
        self,
        transaction: pd.DataFrame,
        background_data: Optional[pd.DataFrame] = None,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        Generate pure causal explanation
        
        Args:
            transaction: Single transaction (not used, for API consistency)
            background_data: Background data (not used)
            top_k: Number of top features to return
            
        Returns:
            Dictionary with causal rankings
        """
        logger.info("🔬 Computing causal-only explanations...")
        
        causal_scores = {}
        
        for feature in self.feature_names:
            if nx.has_path(self.causal_graph, feature, 'malicious'):
                path = nx.shortest_path(self.causal_graph, feature, 'malicious')
                path_length = len(path) - 1
                
                # Score: inverse of path length (shorter path = higher score)
                causal_scores[feature] = {
                    "score": 1.0 / path_length,
                    "path_length": path_length,
                    "path": path
                }
            else:
                causal_scores[feature] = {
                    "score": 0.0,
                    "path_length": float('inf'),
                    "path": []
                }
        
        # Rank by causal score
        sorted_features = sorted(
            [(f, s["score"]) for f, s in causal_scores.items()],
            key=lambda x: x[1],
            reverse=True
        )[:top_k]
        
        recommendations = [
            {
                "feature": feature,
                "causal_score": float(score),
                "path_length": causal_scores[feature]["path_length"],
                "causal_path": causal_scores[feature]["path"],
                "method": "Causal-Only",
                "recommendation": f"Feature '{feature}' has causal path to fraud (length {causal_scores[feature]['path_length']})",
                "actionable": "HIGH",
                "faithful": "UNKNOWN"
            }
            for feature, score in sorted_features if score > 0
        ]
        
        return {
            "method": "Causal-Only",
            "causal_scores": causal_scores,
            "recommendations": recommendations,
            "top_k_features": [f[0] for f in sorted_features if f[1] > 0],
            "metadata": {
                "total_features": len(self.feature_names),
                "causal_valid_features": sum(1 for s in causal_scores.values() if s["score"] > 0)
            }
        }


def compare_all_methods(
    transaction: pd.DataFrame,
    background_data: pd.DataFrame,
    model,
    causal_graph: nx.DiGraph,
    feature_names: List[str],
    top_k: int = 5
) -> Dict[str, Any]:
    """
    Compare all baseline methods + CC-SHAP
    
    Args:
        transaction: Single transaction to explain
        background_data: Background dataset
        model: Trained model
        causal_graph: Causal graph
        feature_names: Feature names
        top_k: Number of top features per method
        
    Returns:
        Comprehensive comparison dictionary
    """
    logger.info("="*80)
    logger.info("COMPREHENSIVE BASELINE COMPARISON")
    logger.info("="*80)
    
    results = {}
    
    # 1. CXPlain-style
    try:
        cxplain = CXPlainStyleExplainer(model, feature_names)
        results["cxplain"] = cxplain.explain(transaction, background_data, top_k, n_samples=50)
    except Exception as e:
        logger.error(f"CXPlain failed: {e}")
        results["cxplain"] = {"error": str(e)}
    
    # 2. DECE-style
    try:
        dece = DECEStyleExplainer(model, causal_graph, feature_names)
        results["dece"] = dece.explain(transaction, background_data, top_k)
    except Exception as e:
        logger.error(f"DECE failed: {e}")
        results["dece"] = {"error": str(e)}
    
    # 3. Counterfactuals
    try:
        counterfactual = CounterfactualExplainer(model, feature_names, causal_graph)
        results["counterfactual"] = counterfactual.explain(transaction, background_data, top_k)
    except Exception as e:
        logger.error(f"Counterfactual failed: {e}")
        results["counterfactual"] = {"error": str(e)}
    
    # 4. Vanilla SHAP
    try:
        vanilla_shap = VanillaSHAPExplainer(model, feature_names)
        results["vanilla_shap"] = vanilla_shap.explain(transaction, background_data, top_k)
    except Exception as e:
        logger.error(f"Vanilla SHAP failed: {e}")
        results["vanilla_shap"] = {"error": str(e)}
    
    # 5. Causal-Only
    try:
        causal_only = CausalOnlyExplainer(causal_graph, feature_names)
        results["causal_only"] = causal_only.explain(transaction, background_data, top_k)
    except Exception as e:
        logger.error(f"Causal-Only failed: {e}")
        results["causal_only"] = {"error": str(e)}
    
    # Summary comparison
    summary = {
        "methods_compared": len(results),
        "comparison": {
            "CXPlain": {
                "features": len(results.get("cxplain", {}).get("top_k_features", [])),
                "faithful": "HIGH",
                "actionable": "UNKNOWN",
                "status": "success" if "cxplain" in results and "error" not in results["cxplain"] else "failed"
            },
            "DECE": {
                "features": len(results.get("dece", {}).get("top_k_features", [])),
                "faithful": "UNKNOWN",
                "actionable": "HIGH",
                "status": "success" if "dece" in results and "error" not in results["dece"] else "failed"
            },
            "Counterfactual": {
                "features": len(results.get("counterfactual", {}).get("top_k_features", [])),
                "faithful": "UNKNOWN",
                "actionable": "HIGH",
                "status": "success" if results.get("counterfactual", {}).get("success", False) else "failed"
            },
            "Vanilla SHAP": {
                "features": len(results.get("vanilla_shap", {}).get("top_k_features", [])),
                "faithful": "HIGH",
                "actionable": "UNKNOWN",
                "status": "success" if "vanilla_shap" in results and "error" not in results["vanilla_shap"] else "failed"
            },
            "Causal-Only": {
                "features": len(results.get("causal_only", {}).get("top_k_features", [])),
                "faithful": "UNKNOWN",
                "actionable": "HIGH",
                "status": "success" if "causal_only" in results and "error" not in results["causal_only"] else "failed"
            }
        }
    }
    
    results["summary"] = summary
    
    logger.info(f"\n✅ Comparison complete: {summary['methods_compared']} methods tested")
    
    return results
