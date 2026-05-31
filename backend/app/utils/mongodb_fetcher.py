"""
MongoDB Data Fetcher for Causal Discovery
ROOT FIX: Connect real MongoDB data to causal XAI endpoints
"""

import pandas as pd
import logging
from typing import Optional
from pymongo import MongoClient
import os

logger = logging.getLogger(__name__)


def fetch_training_data_from_mongodb(
    limit: int = 500,
    min_samples: int = 100
) -> Optional[pd.DataFrame]:
    """
    Fetch real transaction data from MongoDB for causal discovery
    
    Args:
        limit: Maximum number of transactions to fetch
        min_samples: Minimum samples required for causal discovery
        
    Returns:
        DataFrame with transaction features, or None if insufficient data
    """
    try:
        # Connect to MongoDB (Docker service name)
        mongo_host = os.getenv('MONGO_HOST', 'mongodb')
        mongo_port = int(os.getenv('MONGO_PORT', 27017))
        client = MongoClient(f'mongodb://{mongo_host}:{mongo_port}/', serverSelectionTimeoutMS=5000)
        
        db = client['xai_chain']
        collection = db['fraud_predictions']
        
        # Count available documents
        count = collection.count_documents({})
        logger.info(f"Found {count} documents in MongoDB")
        
        if count < min_samples:
            logger.warning(f"Insufficient MongoDB data ({count} < {min_samples}), will use synthetic fallback")
            return None
        
        # Fetch documents with features
        cursor = collection.find(
            {},
            {
                '_id': 0,
                'features': 1,
                'is_malicious': 1,
                'risk_score': 1
            }
        ).limit(limit)
        
        documents = list(cursor)
        
        if not documents:
            logger.warning("No documents found in MongoDB")
            return None
        
        # Extract features and risk scores together, keeping them in sync
        features_list = []
        risk_scores = []
        for doc in documents:
            features = doc.get('features', {})
            if features:
                features_list.append(features)
                risk_scores.append(doc.get('risk_score', 0))

        if not features_list:
            logger.warning("No valid features found in documents")
            return None

        df = pd.DataFrame(features_list)

        # Add outcome variable — risk_scores is now guaranteed same length as df
        df['malicious'] = [1 if score > 70 else 0 for score in risk_scores]
        df['fraud_score'] = [score / 100.0 for score in risk_scores]
        
        logger.info(f" Loaded {len(df)} transactions from MongoDB")
        logger.info(f"   Features: {list(df.columns)}")
        logger.info(f"   Malicious: {df['malicious'].sum()} ({df['malicious'].mean()*100:.1f}%)")
        
        return df
        
    except Exception as e:
        logger.error(f"Failed to fetch MongoDB data: {e}")
        return None


def get_mongodb_stats() -> dict:
    """Get statistics about MongoDB data availability"""
    try:
        mongo_host = os.getenv('MONGO_HOST', 'mongodb')
        mongo_port = int(os.getenv('MONGO_PORT', 27017))
        client = MongoClient(f'mongodb://{mongo_host}:{mongo_port}/', serverSelectionTimeoutMS=5000)
        
        db = client['xai_chain']
        collection = db['fraud_predictions']
        
        count = collection.count_documents({})
        
        if count > 0:
            # Sample one document to get feature list
            sample = collection.find_one({}, {'features': 1, '_id': 0})
            features = list(sample.get('features', {}).keys()) if sample else []
        else:
            features = []
        
        return {
            'available': count > 0,
            'count': count,
            'features': features,
            'sufficient_for_causal': count >= 100
        }
    except Exception as e:
        logger.error(f"Failed to get MongoDB stats: {e}")
        return {
            'available': False,
            'count': 0,
            'features': [],
            'sufficient_for_causal': False
        }
