"""
User feedback endpoint — false positive / false negative reporting.

Every report is stored in MongoDB `feedback` collection and used to:
  1. Build a real labeled dataset over time (supplement collect_transaction_data.py)
  2. Identify systematic model errors (e.g., specific tx patterns always misclassified)
  3. Surface model drift before it appears in aggregate metrics

This is how Chainalysis and Elliptic continuously improve their models —
user feedback is the highest-quality labeling signal available.
"""

import logging
from datetime import datetime
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from pymongo import MongoClient

from app.middleware.auth import verify_api_key
from app.utils.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/feedback", tags=["feedback"])

# MongoDB (optional — feedback still accepted even if DB unavailable, just logged)
try:
    _client     = MongoClient(settings.MONGODB_URI, serverSelectionTimeoutMS=2000)
    _db         = _client.get_database()
    _collection = _db["feedback"]
    _mongo_ok   = True
    logger.info("Feedback: MongoDB connected")
except Exception as e:
    logger.warning(f"Feedback: MongoDB unavailable ({e}) — reports will be logged only")
    _collection = None
    _mongo_ok   = False


class FeedbackRequest(BaseModel):
    """User-reported false positive or false negative."""

    tx_hash: str = Field(
        ...,
        description="Transaction hash that was incorrectly classified",
    )
    reported_label: Literal["fraud", "legitimate"] = Field(
        ...,
        description="What the transaction ACTUALLY is (user's assessment)",
    )
    model_label: Literal["fraud", "legitimate"] = Field(
        ...,
        description="What the model predicted",
    )
    model_risk_score: Optional[int] = Field(
        None, ge=0, le=100,
        description="Risk score the model assigned (0-100)",
    )
    network: str = Field(default="ethereum")
    notes: Optional[str] = Field(
        None, max_length=500,
        description="Optional context: why you believe this is misclassified",
    )


class FeedbackResponse(BaseModel):
    accepted: bool
    feedback_type: str   # "false_positive" | "false_negative" | "correct"
    message: str


@router.post("", response_model=FeedbackResponse, dependencies=[Depends(verify_api_key)])
async def submit_feedback(body: FeedbackRequest) -> FeedbackResponse:
    """
    Report a misclassified transaction.

    False positives (legitimate tx flagged as fraud) are especially valuable —
    they teach the model which patterns are safe and help reduce alert fatigue.

    False negatives (fraud tx missed by model) are used to add similar patterns
    to the training data at the next collection cycle.

    Submitted feedback is stored in MongoDB and reviewed during the next
    model retraining cycle (run train_all_models.py).
    """
    # Determine feedback type
    if body.reported_label == "legitimate" and body.model_label == "fraud":
        feedback_type = "false_positive"
    elif body.reported_label == "fraud" and body.model_label == "legitimate":
        feedback_type = "false_negative"
    else:
        feedback_type = "correct"

    doc = {
        "tx_hash":       body.tx_hash.lower(),
        "reported_label": body.reported_label,
        "model_label":   body.model_label,
        "model_risk_score": body.model_risk_score,
        "network":       body.network,
        "notes":         body.notes,
        "feedback_type": feedback_type,
        "submitted_at":  datetime.utcnow(),
    }

    # Log regardless of DB availability
    logger.info(
        f"Feedback [{feedback_type}]: tx={body.tx_hash[:14]}…  "
        f"model={body.model_label}  user={body.reported_label}  "
        f"risk_score={body.model_risk_score}"
    )

    # Persist to MongoDB
    if _collection is not None:
        try:
            _collection.insert_one(doc)
        except Exception as e:
            logger.warning(f"Feedback MongoDB write failed: {e}")

    messages = {
        "false_positive": (
            "Thank you — this false positive has been recorded. "
            "It will be used to reduce over-triggering in the next model update."
        ),
        "false_negative": (
            "Thank you — this missed fraud has been recorded. "
            "Similar patterns will be added to the training data."
        ),
        "correct": "Thank you for confirming this classification.",
    }

    return FeedbackResponse(
        accepted=True,
        feedback_type=feedback_type,
        message=messages[feedback_type],
    )


@router.get("/summary", dependencies=[Depends(verify_api_key)])
async def feedback_summary():
    """
    Summary of all feedback received.
    Useful for understanding model weaknesses before retraining.
    """
    if _collection is None:
        raise HTTPException(status_code=503, detail="MongoDB unavailable.")

    try:
        pipeline = [
            {"$group": {
                "_id":   "$feedback_type",
                "count": {"$sum": 1},
                "recent": {"$max": "$submitted_at"},
            }},
            {"$sort": {"count": -1}},
        ]
        results = list(_collection.aggregate(pipeline))
        total   = _collection.count_documents({})
        return {
            "total_feedback":  total,
            "by_type":         {r["_id"]: {"count": r["count"], "most_recent": r.get("recent")} for r in results},
            "note": (
                f"After collecting ≥50 new false-positive / false-negative reports, "
                f"re-run train_all_models.py to incorporate user feedback."
            ),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
