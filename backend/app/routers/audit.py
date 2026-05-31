from fastapi import APIRouter, Query
from typing import List
import logging
from pymongo import MongoClient
from datetime import datetime
from app.models.schemas import AuditLogEntry
from app.utils.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

# MongoDB connection
try:
    mongo_client = MongoClient(settings.MONGODB_URI)
    db = mongo_client.get_database()
    analysis_collection = db['analysis_history']
    logger.info("MongoDB connected for audit trail")
except Exception as e:
    logger.warning(f"MongoDB connection failed: {e}")
    mongo_client = None
    analysis_collection = None

@router.get("/", response_model=List[AuditLogEntry])
async def get_audit_trail(
    limit: int = Query(default=10, ge=1, le=100, description="Number of entries to return"),
    skip: int = Query(default=0, ge=0, description="Number of entries to skip")
):
    """
    Get audit trail of analyzed transactions
    
    Args:
        limit: Maximum number of entries to return
        skip: Number of entries to skip (pagination)
    
    Returns:
        List of audit log entries
    """
    try:
        logger.info(f"Fetching audit trail: limit={limit}, skip={skip}")
        
        # Query MongoDB for real analysis history
        if analysis_collection is None:
            logger.warning("MongoDB not available, returning empty audit trail")
            return []
        
        # Fetch from MongoDB sorted by analyzed_at descending
        cursor = analysis_collection.find().sort("analyzed_at", -1).skip(skip).limit(limit)
        
        entries = []
        for doc in cursor:
            entry = AuditLogEntry(
                tx_hash=doc.get("tx_hash", ""),
                risk_score=doc.get("risk_score", 0),
                is_malicious=doc.get("is_malicious", False),
                analyzed_at=doc.get("analyzed_at", datetime.now()).isoformat() if isinstance(doc.get("analyzed_at"), datetime) else str(doc.get("analyzed_at", "")),
                blockchain_hash=doc.get("blockchain_hash", ""),
                ipfs_hash=doc.get("ipfs_hash", "")
            )
            entries.append(entry)
        
        logger.info(f"Returning {len(entries)} audit entries")
        return entries
        
    except Exception as e:
        logger.error(f"Audit trail error: {str(e)}")
        return []
