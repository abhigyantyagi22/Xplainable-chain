"""
Monitoring and metrics endpoints.

GET /api/metrics
    Returns a real-time snapshot of API health, fraud detection rates,
    and latency percentiles.  Responds in < 50 ms using the in-memory
    ring-buffer; MongoDB is used for richer historical data when available.

GET /api/metrics/alert
    Returns whether the fraud rate has drifted significantly above baseline.
    Intended for integration with PagerDuty / Slack / any webhook.
"""

import logging
import time
from datetime import datetime, timedelta, timezone
from statistics import mean, median, quantiles
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends
from pymongo import MongoClient

from app.middleware.auth import verify_api_key
from app.middleware.telemetry import get_buffer_snapshot, get_totals
from app.utils.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/metrics", tags=["metrics"])

# MongoDB connection (optional — metrics still work from in-memory buffer)
try:
    _client     = MongoClient(settings.MONGODB_URI, serverSelectionTimeoutMS=2000)
    _db         = _client.get_database()
    _analysis   = _db["analysis_history"]
    _req_metrics = _db["request_metrics"]
    _mongo_ok   = True
    logger.info("Metrics: MongoDB connected")
except Exception as e:
    logger.warning(f"Metrics: MongoDB unavailable ({e}) — using in-memory only")
    _analysis    = None
    _req_metrics = None
    _mongo_ok    = False


# ── Helpers ────────────────────────────────────────────────────────────────────

def _percentile(data: List[float], pct: float) -> float:
    if not data:
        return 0.0
    data = sorted(data)
    idx  = int(len(data) * pct / 100)
    return data[min(idx, len(data) - 1)]


def _latency_stats(entries: list) -> Dict[str, float]:
    """Compute latency stats from in-memory buffer entries."""
    latencies = [e[1] for e in entries if e[1] > 0]
    if not latencies:
        return {"p50_ms": 0, "p95_ms": 0, "p99_ms": 0, "avg_ms": 0}
    return {
        "p50_ms": round(_percentile(latencies, 50), 1),
        "p95_ms": round(_percentile(latencies, 95), 1),
        "p99_ms": round(_percentile(latencies, 99), 1),
        "avg_ms": round(mean(latencies), 1),
    }


def _analyse_window(hours: int = 24) -> Dict[str, Any]:
    """
    Pull analysis stats from MongoDB for the past N hours.
    Falls back to empty stats if MongoDB unavailable.
    """
    if _analysis is None:
        return {"total": 0, "fraud": 0, "fraud_rate": 0.0, "avg_risk": 0.0}

    since = datetime.utcnow() - timedelta(hours=hours)
    try:
        pipeline = [
            {"$match": {"analyzed_at": {"$gte": since}}},
            {"$group": {
                "_id": None,
                "total":      {"$sum": 1},
                "fraud":      {"$sum": {"$cond": ["$is_malicious", 1, 0]}},
                "avg_risk":   {"$avg": "$risk_score"},
                "high_risk":  {"$sum": {"$cond": [{"$gte": ["$risk_score", 70]}, 1, 0]}},
            }},
        ]
        result = list(_analysis.aggregate(pipeline))
        if not result:
            return {"total": 0, "fraud": 0, "fraud_rate": 0.0, "avg_risk": 0.0, "high_risk": 0}
        r = result[0]
        total = r.get("total", 0)
        fraud = r.get("fraud", 0)
        return {
            "total":      total,
            "fraud":      fraud,
            "fraud_rate": round(fraud / total, 4) if total else 0.0,
            "avg_risk":   round(r.get("avg_risk") or 0.0, 1),
            "high_risk":  r.get("high_risk", 0),
        }
    except Exception as e:
        logger.debug(f"Metrics MongoDB query failed: {e}")
        return {"total": 0, "fraud": 0, "fraud_rate": 0.0, "avg_risk": 0.0, "high_risk": 0}


def _drift_alert(
    fraud_rate_1h: float,
    fraud_rate_7d: float,
    multiplier: float = 2.0,
) -> Dict[str, Any]:
    """
    Return alert status: fraud rate in the last hour vs 7-day baseline.
    Triggered when 1-hour rate > multiplier × 7-day rate AND 7-day rate > 0.
    """
    triggered = (
        fraud_rate_7d > 0
        and fraud_rate_1h > multiplier * fraud_rate_7d
    )
    if fraud_rate_7d == 0:
        message = "Insufficient baseline data (< 7 days of history)"
    elif triggered:
        message = (
            f"ALERT: Fraud rate ({fraud_rate_1h:.1%}) is "
            f"{fraud_rate_1h / fraud_rate_7d:.1f}× the 7-day baseline "
            f"({fraud_rate_7d:.1%}). Possible model drift or attack."
        )
    else:
        message = (
            f"Normal: 1-hour fraud rate ({fraud_rate_1h:.1%}) within "
            f"2× of 7-day baseline ({fraud_rate_7d:.1%})"
        )
    return {
        "triggered":           triggered,
        "fraud_rate_1h":       round(fraud_rate_1h, 4),
        "fraud_rate_7d_baseline": round(fraud_rate_7d, 4),
        "threshold_multiplier": multiplier,
        "message":             message,
    }


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get("", dependencies=[Depends(verify_api_key)])
async def get_metrics() -> Dict[str, Any]:
    """
    Real-time API metrics snapshot.

    Returns:
      - request_stats: latency percentiles from the last 10 000 requests
      - analysis_24h:  fraud detection summary for the last 24 hours
      - analysis_7d:   fraud detection summary for the last 7 days
      - alert:         drift detection (1-hour fraud rate vs 7-day baseline)
      - cache:         Redis / in-memory cache status
      - uptime:        cumulative request counts since last restart
    """
    # ── In-memory request stats (fast) ────────────────────────────────────────
    snapshot = get_buffer_snapshot()
    now      = time.time()

    # Last hour
    hour_ago = now - 3600
    recent   = [e for e in snapshot if e[0] >= hour_ago]

    request_stats = {
        "last_1h": {
            "requests": len(recent),
            "errors":   sum(1 for e in recent if e[2] >= 400),
            **_latency_stats(recent),
        },
        "all_time": get_totals(),
    }

    # ── MongoDB analysis stats ─────────────────────────────────────────────────
    analysis_1h  = _analyse_window(hours=1)
    analysis_24h = _analyse_window(hours=24)
    analysis_7d  = _analyse_window(hours=168)

    # ── Drift alert ────────────────────────────────────────────────────────────
    alert = _drift_alert(
        fraud_rate_1h=analysis_1h["fraud_rate"],
        fraud_rate_7d=analysis_7d["fraud_rate"],
    )

    return {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "request_stats": request_stats,
        "analysis_1h":  analysis_1h,
        "analysis_24h": analysis_24h,
        "analysis_7d":  analysis_7d,
        "alert":        alert,
        "data_sources": {
            "request_latency": "in-memory ring-buffer (last 10 000 requests)",
            "fraud_stats":     "MongoDB analysis_history" if _mongo_ok else "unavailable",
        },
    }


@router.get("/alert", dependencies=[Depends(verify_api_key)])
async def get_alert_status() -> Dict[str, Any]:
    """
    Lightweight drift-alert check — suitable for polling from a health-check
    or webhook (e.g., PagerDuty, Slack).

    Returns HTTP 200 always; check `alert.triggered` in the response body.
    Typical integration: if triggered == true, fire a Slack notification.
    """
    analysis_1h = _analyse_window(hours=1)
    analysis_7d = _analyse_window(hours=168)

    alert = _drift_alert(
        fraud_rate_1h=analysis_1h["fraud_rate"],
        fraud_rate_7d=analysis_7d["fraud_rate"],
    )

    return {
        "checked_at": datetime.utcnow().isoformat() + "Z",
        "alert":      alert,
        "action":     (
            "Investigate model outputs and recent transaction patterns."
            if alert["triggered"] else "No action required."
        ),
    }
