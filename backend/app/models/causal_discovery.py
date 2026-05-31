"""
NOVEL: Data-Driven Causal Discovery for Blockchain Fraud
Uses NOTEARS algorithm to automatically learn causal structure from data
This is a key research contribution - no manual graph specification
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
import networkx as nx
from scipy.optimize import minimize
from scipy.special import expit
import logging

logger = logging.getLogger(__name__)


class NOTEARSCausalDiscovery:
    """
    NOTEARS: Non-combinatorial Optimization via Trace Exponential and Augmented lagRangian for Structure learning
    
    Novel Contribution: Automatically discovers causal relationships in blockchain transactions
    without manual domain knowledge specification.
    
    Reference: Zheng et al. (2018) "DAGs with NO TEARS"
    """
    
    def __init__(self, lambda_l1: float = 0.01, lambda_dag: float = 0.1):
        """
        Args:
            lambda_l1: L1 penalty for sparsity (fewer edges)
            lambda_dag: DAG constraint penalty (ensures acyclicity)
        """
        self.lambda_l1 = lambda_l1
        self.lambda_dag = lambda_dag
        self.W = None  # Learned weighted adjacency matrix
        self.graph = None
        
    def _loss(self, W: np.ndarray, X: np.ndarray) -> float:
        """Squared loss for continuous data"""
        n, d = X.shape
        M = X @ W
        R = X - M
        loss = 0.5 / n * (R ** 2).sum()
        return loss
    
    def _h(self, W: np.ndarray) -> float:
        """DAG constraint: h(W) = 0 iff W represents a DAG"""
        d = W.shape[0]
        return np.trace(np.linalg.matrix_power(np.eye(d) + W * W, d)) - d
    
    def _gradient_loss(self, W: np.ndarray, X: np.ndarray) -> np.ndarray:
        """Gradient of squared loss"""
        n, d = X.shape
        M = X @ W
        G = -1.0 / n * X.T @ (X - M)
        return G
    
    def _gradient_h(self, W: np.ndarray) -> np.ndarray:
        """Gradient of DAG constraint"""
        d = W.shape[0]
        M = np.eye(d) + W * W
        E = np.linalg.matrix_power(M, d - 1)
        G = E.T * W * 2
        return G
    
    def fit(self, X: pd.DataFrame, max_iter: int = 100) -> nx.DiGraph:
        """
        Learn causal structure from data using NOTEARS
        
        Args:
            X: DataFrame with features (rows=samples, cols=variables)
            max_iter: Maximum optimization iterations
            
        Returns:
            Directed Acyclic Graph (DAG) representing causal relationships
        """
        logger.info("Running NOTEARS causal discovery algorithm...")
        
        # Convert to numpy
        feature_names = X.columns.tolist()
        X_np = X.values
        n, d = X_np.shape
        
        # Standardize data; guard against zero-variance (constant) features
        std = X_np.std(axis=0)
        std[std == 0] = 1.0  # Constant features carry no information; keep them as-is
        X_np = (X_np - X_np.mean(axis=0)) / std
        
        # Initialize weights
        W = np.zeros((d, d))
        
        # Optimization with augmented Lagrangian
        rho = 1.0  # Penalty multiplier
        alpha = 0.0  # Lagrange multiplier
        h_tol = 1e-8
        
        for iter_num in range(max_iter):
            # Define augmented Lagrangian
            def _func(w):
                W_mat = w.reshape((d, d))
                loss = self._loss(W_mat, X_np)
                h_val = self._h(W_mat)
                return loss + self.lambda_l1 * np.abs(w).sum() + alpha * h_val + 0.5 * rho * h_val ** 2
            
            def _grad(w):
                W_mat = w.reshape((d, d))
                G_loss = self._gradient_loss(W_mat, X_np)
                G_h = self._gradient_h(W_mat)
                G = G_loss + (alpha + rho * self._h(W_mat)) * G_h
                G += self.lambda_l1 * np.sign(w).reshape((d, d))
                return G.flatten()
            
            # Optimize
            w_init = W.flatten()
            result = minimize(_func, w_init, method='L-BFGS-B', jac=_grad, options={'maxiter': 1000})
            W = result.x.reshape((d, d))
            
            # Check DAG constraint
            h_val = self._h(W)
            
            if h_val <= h_tol:
                logger.info(f"NOTEARS converged at iteration {iter_num}, h={h_val:.6e}")
                break
            
            # Update Lagrange multiplier
            alpha += rho * h_val
            rho *= 10
            
            if iter_num % 10 == 0:
                logger.info(f"Iter {iter_num}: h={h_val:.6e}, rho={rho:.2e}")
        
        # Threshold small weights to ensure DAG property
        # Use adaptive threshold based on weight distribution
        weight_threshold = max(0.05, np.percentile(np.abs(W), 50))  # At least 0.05 or median
        logger.info(f"Using weight threshold: {weight_threshold:.3f}")
        W[np.abs(W) < weight_threshold] = 0
        
        # Remove cycles if any exist
        logger.info("Checking for cycles...")
        temp_graph = nx.DiGraph()
        feature_names_list = list(feature_names) if hasattr(feature_names, '__iter__') and not isinstance(feature_names, str) else feature_names
        
        for i, cause in enumerate(feature_names_list):
            for j, effect in enumerate(feature_names_list):
                if W[i, j] != 0:
                    temp_graph.add_edge(cause, effect, weight=float(W[i, j]))
        
        # Remove weakest edges until DAG
        while not nx.is_directed_acyclic_graph(temp_graph) and temp_graph.number_of_edges() > 0:
            # Find weakest edge and remove it
            edges = [(u, v, abs(data['weight'])) for u, v, data in temp_graph.edges(data=True)]
            edges.sort(key=lambda x: x[2])
            weakest_edge = edges[0]
            temp_graph.remove_edge(weakest_edge[0], weakest_edge[1])
            logger.info(f"Removed cycle edge: {weakest_edge[0]} → {weakest_edge[1]} (weight: {weakest_edge[2]:.3f})")
        
        # Update W matrix based on final DAG
        W_final = np.zeros_like(W)
        for i, cause in enumerate(feature_names_list):
            for j, effect in enumerate(feature_names_list):
                if temp_graph.has_edge(cause, effect):
                    W_final[i, j] = temp_graph[cause][effect]['weight']
        
        W = W_final
        
        self.W = W
        
        # Convert to NetworkX graph
        self.graph = nx.DiGraph()
        
        for i, cause in enumerate(feature_names):
            for j, effect in enumerate(feature_names):
                if W[i, j] != 0:
                    self.graph.add_edge(cause, effect, weight=float(W[i, j]))
        
        logger.info(f"Discovered causal graph: {self.graph.number_of_nodes()} nodes, {self.graph.number_of_edges()} edges")
        
        return self.graph
    
    def get_parents(self, node: str) -> List[str]:
        """Get direct causes of a node"""
        if self.graph is None:
            return []
        return list(self.graph.predecessors(node))
    
    def get_children(self, node: str) -> List[str]:
        """Get direct effects of a node"""
        if self.graph is None:
            return []
        return list(self.graph.successors(node))
    
    def get_causal_strength(self, cause: str, effect: str) -> float:
        """Get causal strength between two variables"""
        if self.graph is None or not self.graph.has_edge(cause, effect):
            return 0.0
        return self.graph[cause][effect]['weight']


class CausalEffectEstimator:
    """
    NOVEL: Estimate heterogeneous causal effects for different transaction types
    Uses Conditional Average Treatment Effect (CATE)
    """
    
    def __init__(self, causal_graph: nx.DiGraph):
        self.graph = causal_graph
        
    def estimate_cate(
        self, 
        data: pd.DataFrame, 
        treatment: str, 
        outcome: str,
        moderator: str
    ) -> Dict[str, float]:
        """
        Estimate how causal effects vary by transaction type
        
        Args:
            data: Transaction data
            treatment: Treatment variable (e.g., 'gas_price')
            outcome: Outcome variable (e.g., 'malicious')
            moderator: Grouping variable (e.g., 'is_contract_creation')
            
        Returns:
            CATE for each group
        """
        logger.info(f"Estimating CATE: {treatment} → {outcome} | {moderator}")
        
        cate_results = {}
        
        # Split by moderator
        for group_val in data[moderator].unique():
            group_data = data[data[moderator] == group_val]
            
            if len(group_data) < 30:
                continue
            
            # Get confounders
            confounders = self._get_backdoor_adjustment_set(treatment, outcome)
            available_confounders = [c for c in confounders if c in group_data.columns]
            
            # Estimate ATE for this group using linear regression
            if available_confounders:
                X = group_data[[treatment] + available_confounders].values
            else:
                X = group_data[[treatment]].values
            
            y = group_data[outcome].values
            
            # Simple linear regression
            from numpy.linalg import lstsq
            coef = lstsq(X, y, rcond=None)[0]
            ate = coef[0]  # Treatment effect
            
            cate_results[f"{moderator}={group_val}"] = float(ate)
            
        return cate_results
    
    def _get_backdoor_adjustment_set(self, treatment: str, outcome: str) -> List[str]:
        """Find confounders to control for"""
        # Simple approach: all common ancestors
        try:
            treatment_ancestors = nx.ancestors(self.graph, treatment)
            outcome_ancestors = nx.ancestors(self.graph, outcome)
            confounders = treatment_ancestors.intersection(outcome_ancestors)
            return list(confounders)
        except:
            return []


class CounterfactualGenerator:
    """
    NOVEL: Generate counterfactual explanations for blockchain fraud
    'What would happen if gas_price were different?'
    
    This is a key research contribution - actionable explanations for fraud prevention
    """
    
    def __init__(self, causal_graph: nx.DiGraph, ml_model=None):
        self.graph = causal_graph
        self.ml_model = ml_model
        
    def generate_counterfactual(
        self,
        observed_features: Dict[str, float],
        intervention: Dict[str, float],
        outcome: str = 'malicious'
    ) -> Dict:
        """
        Generate counterfactual: What if we intervened on certain features?
        
        Args:
            observed_features: Actual transaction features
            intervention: Features to change (e.g., {'gas_price': 50})
            outcome: Target outcome variable
            
        Returns:
            Counterfactual prediction and explanation
        """
        logger.info(f"Generating counterfactual with intervention: {intervention}")
        
        # Create counterfactual features
        counterfactual_features = observed_features.copy()
        
        for var, value in intervention.items():
            counterfactual_features[var] = value
            
            # Propagate causal effects to children
            if var in self.graph:
                descendants = nx.descendants(self.graph, var)
                
                for desc in descendants:
                    if desc in counterfactual_features:
                        # Simple linear propagation (improve with SCM)
                        if self.graph.has_edge(var, desc):
                            weight = self.graph[var][desc].get('weight', 0)
                            delta = (value - observed_features[var]) * weight
                            counterfactual_features[desc] += delta
        
        # Predict outcomes
        observed_outcome = self._predict_outcome(observed_features, outcome)
        counterfactual_outcome = self._predict_outcome(counterfactual_features, outcome)
        
        effect_size = counterfactual_outcome - observed_outcome
        
        return {
            'observed_features': observed_features,
            'counterfactual_features': counterfactual_features,
            'intervention': intervention,
            'observed_outcome': observed_outcome,
            'counterfactual_outcome': counterfactual_outcome,
            'causal_effect': effect_size,
            'recommendation': self._generate_recommendation(intervention, effect_size),
            'affected_variables': list(set(counterfactual_features.keys()) - set(observed_features.keys()))
        }
    
    def _predict_outcome(self, features: Dict, outcome: str) -> float:
        """Predict outcome using ML model or heuristic"""
        try:
            # Use actual ML model
            from app.models.ai_detector import AIDetector
            detector = AIDetector()
            
            # Convert features dict to format expected by detector
            feature_dict = {
                'amount': features.get('amount', 0),
                'gas_price': features.get('gas_price', 50),
                'gas_used': features.get('gas_used', 21000),
                'gas_price_deviation': features.get('gas_price_deviation', 0),
                'value': features.get('value', 0),
                'sender_tx_count': features.get('sender_tx_count', 0),
                'is_contract_creation': features.get('is_contract_creation', 0),
                'contract_age': features.get('contract_age', 0),
                'block_gas_used_ratio': features.get('block_gas_used_ratio', 0.5)
            }
            
            pred = detector.predict(feature_dict)
            fraud_prob = pred['probabilities'][1]  # Fraud probability
            logger.debug(f"ML model prediction: {fraud_prob:.3f}")
            return fraud_prob
            
        except Exception as e:
            logger.warning(f"ML model prediction failed: {e}, using heuristic")
            
            # Fallback heuristic
            fraud_score = (
                0.3 * (features.get('gas_price', 50) - 50) / 50 +
                0.2 * features.get('value', 0) / 10 +
                0.2 * (1 / (features.get('sender_tx_count', 10) + 1)) +
                0.3 * features.get('gas_price_deviation', 0)
            )
            return 1 / (1 + np.exp(-fraud_score))  # Sigmoid
    
    def _generate_recommendation(self, intervention: Dict, effect: float) -> str:
        """Generate actionable recommendation"""
        if effect < -0.1:
            return f" RECOMMENDED: This intervention would DECREASE fraud risk by {abs(effect)*100:.1f}%"
        elif effect > 0.1:
            return f"⚠️ WARNING: This intervention would INCREASE fraud risk by {effect*100:.1f}%"
        else:
            return f"ℹ️ NEUTRAL: This intervention has minimal impact on fraud risk ({abs(effect)*100:.1f}%)"
