"""
Blockchain Data API Router
Provides endpoints to fetch transaction data from blockchain
"""

from fastapi import APIRouter, HTTPException
from typing import Dict
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/blockchain", tags=["blockchain"])


@router.get("/transaction/{transaction_hash}")
async def get_transaction_data(transaction_hash: str) -> Dict:
    """
    Fetch transaction data from blockchain and extract features
    
    Args:
        transaction_hash: Ethereum transaction hash
        
    Returns:
        Dictionary containing extracted features
    """
    try:
        from app.services.blockchain import BlockchainService
        from app.utils.feature_engineering import extract_features
        import re
        
        # Validate transaction hash format
        if not re.match(r'^0x[a-fA-F0-9]{64}$', transaction_hash):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid transaction hash format: {transaction_hash}. Must be 66 characters starting with '0x'"
            )
        
        logger.info(f"Fetching transaction data for: {transaction_hash}")
        
        # Fetch from blockchain
        blockchain_service = BlockchainService()
        tx_data = await blockchain_service.get_transaction(transaction_hash, "ethereum")
        
        if not tx_data:
            raise HTTPException(
                status_code=404,
                detail=f"Transaction {transaction_hash} not found on blockchain"
            )
        
        # Extract features
        features = extract_features(tx_data)
        
        logger.info(f"Successfully extracted features: {list(features.keys())}")
        
        return {
            "transaction_hash": transaction_hash,
            "features": features,
            **features  # Flatten features to top level for easy access
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching transaction data: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch transaction data: {str(e)}"
        )
