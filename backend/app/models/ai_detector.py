import pickle
import numpy as np
import pandas as pd
from pathlib import Path
import logging
import os

logger = logging.getLogger(__name__)

class AIDetector:
    """AI-based malicious transaction detector using XGBoost"""
    
    def __init__(self, model_path: str = None, scaler_path: str = None):
        """
        Initialize AI detector with pre-trained model
        
        Args:
            model_path: Path to the trained model pickle file
            scaler_path: Path to the feature scaler pickle file
        """
        self.model = None
        self.scaler = None
        self.feature_names = None
        self.model_path = model_path
        self.scaler_path = scaler_path
        self.load_model()
    
    def load_model(self):
        """Load pre-trained XGBoost model and scaler"""
        try:
            # Default paths
            if self.model_path is None:
                self.model_path = Path(__file__).parent.parent / "ml" / "model.pkl"
            if self.scaler_path is None:
                self.scaler_path = Path(__file__).parent.parent / "ml" / "scaler.pkl"
            
            # Check if files exist
            if not os.path.exists(self.model_path):
                logger.warning(f"Model file not found at {self.model_path}")
                logger.warning("Using mock model for testing. Please train model first!")
                self._create_mock_model()
                return
            
            with open(self.model_path, 'rb') as f:
                self.model = pickle.load(f)
            
            with open(self.scaler_path, 'rb') as f:
                self.scaler = pickle.load(f)
            
            # Load feature names from training to ensure exact match
            feature_names_path = Path(__file__).parent.parent / "ml" / "feature_names.pkl"
            if os.path.exists(feature_names_path):
                with open(feature_names_path, 'rb') as f:
                    self.feature_names = pickle.load(f)
                logger.info(f"Loaded {len(self.feature_names)} features from training: {self.feature_names}")
            else:
                # Fallback to Kaggle dataset features (9 features)
                self.feature_names = [
                    'amount', 'gas_price', 'gas_used', 'gas_price_deviation',
                    'value', 'sender_tx_count', 'is_contract_creation',
                    'contract_age', 'block_gas_used_ratio'
                ]
                logger.warning("Feature names file not found, using default Kaggle features")
            
            logger.info("AI model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            logger.warning("Using mock model for testing")
            self._create_mock_model()
    
    def _create_mock_model(self):
        """Create a mock model for testing when real model is not available"""
        class MockModel:
            def predict(self, X):
                # Ensure X is numpy array with float dtype
                X_array = np.asarray(X, dtype=np.float64)
                # Simple heuristic: high gas price or high value = malicious
                # x[0] = amount, x[1] = gas_price, x[2] = gas_used
                predictions = []
                for x in X_array:
                    # High amount (> 10 ETH) or very high gas used (> 100000) = suspicious
                    is_suspicious = (x[0] > 10.0) or (x[2] > 100000) or (x[1] > 200)
                    predictions.append(1 if is_suspicious else 0)
                return np.array(predictions, dtype=np.int32)
            
            def predict_proba(self, X):
                predictions = self.predict(X)
                # Convert to probabilities [prob_normal, prob_malicious]
                probabilities = []
                for pred in predictions:
                    if pred == 1:
                        # Malicious: higher probability for class 1
                        probabilities.append([0.3, 0.7])
                    else:
                        # Normal: higher probability for class 0
                        probabilities.append([0.8, 0.2])
                return np.array(probabilities, dtype=np.float64)
        
        class MockScaler:
            def transform(self, X):
                # Ensure input is converted to numpy array with proper float dtype
                # This prevents string comparison errors
                return np.asarray(X, dtype=np.float64)
        
        self.model = MockModel()
        self.scaler = MockScaler()
        self.feature_names = [
            'amount', 'gas_price', 'gas_used', 'gas_price_deviation',
            'value', 'sender_tx_count', 'is_contract_creation',
            'contract_age', 'block_gas_used_ratio'
        ]
    
    def predict(self, features: dict) -> dict:
        """
        Predict if transaction is malicious
        
        Args:
            features: Dictionary of transaction features
        
        Returns:
            {
                'is_malicious': bool,
                'confidence': float,
                'probabilities': list
            }
        """
        try:
            # Convert to DataFrame
            df = pd.DataFrame([features])
            
            # Ensure all required features are present
            for feature in self.feature_names:
                if feature not in df.columns:
                    df[feature] = 0
            
            # Reorder columns to match training
            df = df[self.feature_names]
            
            # Scale features
            X_scaled = self.scaler.transform(df)
            
            # Predict
            probabilities = self.model.predict_proba(X_scaled)[0]
            prediction = self.model.predict(X_scaled)[0]
            
            return {
                'is_malicious': bool(prediction),
                'confidence': float(probabilities[1] if prediction else probabilities[0]),
                'probabilities': probabilities.tolist()
            }
        except Exception as e:
            logger.error(f"Prediction error: {e}")
            raise
