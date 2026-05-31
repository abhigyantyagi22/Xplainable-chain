"""
Transaction analysis router.

Phase 3 changes
───────────────
  Step 7 — Selective storage: IPFS + blockchain writes only happen when
            risk_score >= STORAGE_RISK_THRESHOLD (default 70).  Low-risk
            transactions are saved to MongoDB only, cutting storage costs.

  Step 8 — Background storage: the IPFS upload and blockchain write are
            dispatched as a BackgroundTask so the HTTP response is returned
            immediately after ML inference + SHAP.  Clients wanting storage
            confirmation should poll GET /api/verify/{tx_hash}.

  Step 9 — Cache: the full analysis result is cached (Redis → in-memory
            fallback) for ANALYSIS_CACHE_TTL seconds so repeated lookups of
            the same tx_hash skip the entire pipeline.
"""

import json
import logging
import random
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pymongo import MongoClient

from app.models.schemas import AnalyzeRequest, AnalyzeResponse
from app.models.ai_detector import AIDetector
from app.models.xai_explainer import XAIExplainer
from app.services.blockchain import BlockchainService
from app.services.cache import CacheService
from app.services.enrichment import EnrichmentService
from app.services.ipfs import IPFSService
from app.utils.config import settings
from app.utils.feature_engineering import extract_features
from app.utils.mongodb_fetcher import fetch_training_data_from_mongodb

router = APIRouter()
logger = logging.getLogger(__name__)

# ── Singleton services ─────────────────────────────────────────────────────────
ai_detector        = AIDetector()
xai_explainer      = XAIExplainer()
blockchain_service = BlockchainService()
ipfs_service       = IPFSService()
cache_service      = CacheService(redis_url=settings.REDIS_URL)
# Enrichment is wired up with the DB after MongoDB connects (see _init_enrichment)
enrichment_service: EnrichmentService = EnrichmentService(
    chainabuse_api_key=settings.CHAINABUSE_API_KEY,
    cache=cache_service,
)

# ── MongoDB (optional — graceful degradation if unavailable) ───────────────────
try:
    _mongo_client      = MongoClient(settings.MONGODB_URI, serverSelectionTimeoutMS=3000)
    _db                = _mongo_client.get_database()
    analysis_collection = _db["analysis_history"]
    # Wire MongoDB into enrichment service so it can check internal history
    enrichment_service._db = _db
    logger.info("MongoDB connected for analysis history")
except Exception as e:
    logger.warning(f"MongoDB connection failed: {e}")
    _mongo_client       = None
    analysis_collection = None

# ── Risk threshold for on-chain / IPFS storage ────────────────────────────────
_STORAGE_THRESHOLD = settings.STORAGE_RISK_THRESHOLD


# ── Background storage task ────────────────────────────────────────────────────

async def _store_explanation_async(
    tx_hash: str,
    explanation_data: dict,
    risk_score: int,
) -> None:
    """
    Background task: upload explanation to IPFS, store hash on-chain,
    then update the MongoDB record with both hashes.

    Runs AFTER the HTTP response has already been sent.
    All exceptions are caught and logged — failures never reach the client.
    """
    ipfs_hash       = None
    blockchain_hash = None

    # Step 1: IPFS upload
    try:
        ipfs_hash = await ipfs_service.upload_json(explanation_data)
        logger.info(f"[BG] IPFS upload complete for {tx_hash}: {ipfs_hash}")
    except Exception as e:
        logger.warning(f"[BG] IPFS upload failed for {tx_hash}: {e}")

    # Step 2: Blockchain storage (only if IPFS succeeded)
    if ipfs_hash:
        try:
            blockchain_hash = await blockchain_service.store_explanation(
                tx_hash=tx_hash,
                ipfs_hash=ipfs_hash,
                risk_score=risk_score,
            )
            logger.info(f"[BG] Blockchain storage complete for {tx_hash}: {blockchain_hash}")
        except Exception as e:
            logger.warning(f"[BG] Blockchain storage failed for {tx_hash}: {e}")

    # Step 3: Update MongoDB record with the final hashes
    if analysis_collection is not None and (ipfs_hash or blockchain_hash):
        try:
            analysis_collection.update_one(
                {"tx_hash": tx_hash},
                {"$set": {
                    "ipfs_hash":       ipfs_hash,
                    "blockchain_hash": blockchain_hash,
                    "stored_at":       datetime.utcnow(),
                }},
            )
            logger.info(f"[BG] MongoDB updated with storage hashes for {tx_hash}")
        except Exception as e:
            logger.warning(f"[BG] MongoDB update failed for {tx_hash}: {e}")


# ── Main endpoint ──────────────────────────────────────────────────────────────

def _validate_tx_hash(tx_hash: str) -> bool:
    import re
    return bool(re.match(r"^0x[a-fA-F0-9]{64}$", tx_hash))


@router.post("/", response_model=AnalyzeResponse)
async def analyze_transaction(
    request: AnalyzeRequest,
    background_tasks: BackgroundTasks,
):
    """
    Analyze a blockchain transaction for fraud.

    Returns ML prediction + SHAP explanation immediately.
    If risk_score >= STORAGE_RISK_THRESHOLD, IPFS upload and on-chain
    storage happen in the background after this response is sent.
    Use GET /api/verify/{tx_hash} to check storage status.
    """
    try:
        logger.info(f"Analyzing transaction: {request.tx_hash}")

        # ── Step 9: Check cache ────────────────────────────────────────────────
        cache_key = f"analysis:{request.tx_hash.lower()}"
        if not request.transaction_data:  # Cache only real-blockchain analyses
            cached_json = await cache_service.get(cache_key)
            if cached_json:
                logger.info(f"Cache hit for {request.tx_hash} — returning instantly")
                return AnalyzeResponse(**json.loads(cached_json))

        # ── Feature extraction ─────────────────────────────────────────────────
        dataset_mode = bool(request.transaction_data)
        tx_data: dict = {}

        if dataset_mode:
            logger.info("Using provided transaction features (dataset mode)")
            features = request.transaction_data

            required = [
                "amount", "gas_price", "gas_used", "gas_price_deviation",
                "value", "sender_tx_count", "is_contract_creation",
                "contract_age", "block_gas_used_ratio",
            ]
            missing = [f for f in required if f not in features]
            if missing:
                raise HTTPException(status_code=400, detail=f"Missing features: {missing}")

        else:
            if not _validate_tx_hash(request.tx_hash):
                raise HTTPException(
                    status_code=400,
                    detail="Invalid transaction hash — must be 0x followed by 64 hex characters",
                )

            tx_data = await blockchain_service.get_transaction(request.tx_hash, request.network)
            if not tx_data:
                raise HTTPException(
                    status_code=404,
                    detail=f"Transaction {request.tx_hash} not found on {request.network}",
                )
            logger.info(f"Fetched transaction from {request.network}")
            features = extract_features(tx_data)

        logger.info(f"Features: {features}")

        # ── Step 10: Address screening (OFAC / Chainabuse / internal) ──────────
        # Only applies when we have real blockchain addresses (not dataset mode)
        screening_source = ""
        if not dataset_mode and tx_data:
            sender    = tx_data.get("from", "")
            recipient = tx_data.get("to", "")
            screening = await enrichment_service.screen_transaction(sender, recipient)
            if screening.flagged:
                logger.warning(
                    f"Address screening flagged transaction {request.tx_hash}: "
                    f"source={screening.source}, detail={screening.detail}"
                )
                # Short-circuit — skip ML inference entirely
                risk_score   = screening.risk_override
                is_malicious = True
                confidence   = risk_score / 100.0
                screening_source = screening.source

                explanation_data = {
                    "tx_hash":       request.tx_hash,
                    "risk_score":    risk_score,
                    "is_malicious":  True,
                    "confidence":    confidence,
                    "shap_values":   [],
                    "feature_importance": {},
                    "top_features":  [],
                    "base_value":    confidence,
                    "model_version": "enrichment_screening",
                    "timestamp":     datetime.utcnow().isoformat(),
                    "network":       request.network,
                    "screening": {
                        "flagged": True,
                        "source":  screening.source,
                        "detail":  screening.detail,
                    },
                }

                if analysis_collection is not None:
                    try:
                        analysis_collection.insert_one({
                            "tx_hash":         request.tx_hash,
                            "is_malicious":    True,
                            "risk_score":      float(risk_score),
                            "confidence":      confidence,
                            "features":        features,
                            "explanation":     explanation_data,
                            "screening_source": screening.source,
                            "analyzed_at":     datetime.utcnow(),
                            "network":         request.network,
                            "storage_pending": True,
                        })
                    except Exception as e:
                        logger.warning(f"MongoDB insert failed: {e}")

                background_tasks.add_task(
                    _store_explanation_async,
                    request.tx_hash, explanation_data, risk_score,
                )

                return AnalyzeResponse(
                    tx_hash=request.tx_hash,
                    is_malicious=True,
                    risk_score=risk_score,
                    confidence=confidence,
                    explanation=explanation_data,
                    ipfs_hash=None,
                    blockchain_hash=None,
                    features=features,
                    timestamp=datetime.utcnow().isoformat(),
                    is_experimental=False,          # definitive — from threat intel
                    screening_source=screening.source,
                )

        # ── ML inference ───────────────────────────────────────────────────────
        prediction  = ai_detector.predict(features)
        is_malicious = prediction["is_malicious"]
        confidence   = float(prediction["probabilities"][1])  # P(fraud)
        risk_score   = int(confidence * 100)

        logger.info(f"Prediction: malicious={is_malicious}, risk_score={risk_score}")

        # ── SHAP explanation ───────────────────────────────────────────────────
        shap_explanation = xai_explainer.explain(features, ai_detector.model)

        explanation_data = {
            "tx_hash":           request.tx_hash,
            "risk_score":        risk_score,
            "is_malicious":      is_malicious,
            "confidence":        confidence,
            "shap_values":       shap_explanation["shap_values"],
            "feature_importance": shap_explanation["feature_importance"],
            "top_features":      shap_explanation["top_features"],
            "base_value":        shap_explanation.get("base_value", 0.5),
            "model_version":     "xgboost_v2.0",
            "timestamp":         datetime.utcnow().isoformat(),
            "network":           request.network,
        }

        # ── MongoDB: save record immediately (without storage hashes) ──────────
        if analysis_collection is not None:
            try:
                analysis_collection.insert_one({
                    "tx_hash":       request.tx_hash,
                    "is_malicious":  is_malicious,
                    "risk_score":    float(risk_score),
                    "confidence":    confidence,
                    "features":      features,
                    "explanation":   explanation_data,
                    "ipfs_hash":     None,
                    "blockchain_hash": None,
                    "analyzed_at":   datetime.utcnow(),
                    "network":       request.network,
                    "storage_pending": risk_score >= _STORAGE_THRESHOLD,
                })
            except Exception as e:
                logger.warning(f"MongoDB insert failed: {e}")

        # ── Step 7 + 8: Selective + background storage ─────────────────────────
        if dataset_mode:
            # Dataset-mode: never hits the chain, no storage needed
            ipfs_hash       = None
            blockchain_hash = None

        elif risk_score >= _STORAGE_THRESHOLD:
            # High-risk transaction: queue IPFS + blockchain write as background task
            background_tasks.add_task(
                _store_explanation_async,
                request.tx_hash,
                explanation_data,
                risk_score,
            )
            logger.info(
                f"risk_score={risk_score} >= threshold={_STORAGE_THRESHOLD}: "
                f"storage queued in background"
            )
            ipfs_hash       = None   # filled by background task
            blockchain_hash = None

        else:
            # Low-risk transaction: skip storage entirely (cost saving)
            logger.info(
                f"risk_score={risk_score} < threshold={_STORAGE_THRESHOLD}: "
                f"skipping IPFS + blockchain storage"
            )
            ipfs_hash       = None
            blockchain_hash = None

        # ── Build response ─────────────────────────────────────────────────────
        response = AnalyzeResponse(
            tx_hash=request.tx_hash,
            is_malicious=is_malicious,
            risk_score=risk_score,
            confidence=confidence,
            explanation=explanation_data,
            ipfs_hash=ipfs_hash,
            blockchain_hash=blockchain_hash,
            features=features,
            timestamp=datetime.utcnow().isoformat(),
            is_experimental=True,       # ML model — treat as soft signal
            screening_source=None,      # no threat-intel match; ML made this call
        )

        # ── Step 9: Cache result (real transactions only) ──────────────────────
        if not dataset_mode:
            try:
                await cache_service.set(
                    cache_key,
                    response.model_dump_json(),
                    ttl=settings.ANALYSIS_CACHE_TTL,
                )
            except Exception as e:
                logger.debug(f"Cache write failed (non-fatal): {e}")

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Analysis error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")


# ── Demo endpoint ──────────────────────────────────────────────────────────────

@router.post("/demo", response_model=AnalyzeResponse)
async def analyze_demo():
    """
    Demo mode: analyze a random transaction from the training dataset.
    Not cached — always fetches a fresh random sample.
    """
    try:
        logger.info("Demo mode: selecting random transaction from dataset")

        df = fetch_training_data_from_mongodb()
        if df is None or len(df) == 0:
            raise HTTPException(status_code=500, detail="No training data available for demo")

        sample = df.iloc[random.randint(0, len(df) - 1)]
        feature_cols = [c for c in df.columns if c not in ("malicious", "fraud_score", "label")]
        features = {col: float(sample[col]) for col in feature_cols if col in sample}

        prediction   = ai_detector.predict(features)
        is_malicious  = prediction["is_malicious"]
        confidence    = float(prediction["probabilities"][1])
        risk_score    = int(confidence * 100)

        shap_explanation = xai_explainer.explain(features, ai_detector.model)

        demo_hash = "0x" + "".join(random.choices("0123456789abcdef", k=64))

        explanation_data = {
            "tx_hash":            demo_hash,
            "risk_score":         risk_score,
            "is_malicious":       is_malicious,
            "confidence":         confidence,
            "shap_values":        shap_explanation["shap_values"],
            "feature_importance": shap_explanation["feature_importance"],
            "top_features":       shap_explanation["top_features"],
            "base_value":         shap_explanation.get("base_value", 0.5),
            "model_version":      "xgboost_v2.0_demo",
            "timestamp":          datetime.utcnow().isoformat(),
            "mode":               "demo",
            "actual_label":       int(sample.get("label", sample.get("malicious", 0))),
        }

        return AnalyzeResponse(
            tx_hash=demo_hash,
            is_malicious=is_malicious,
            risk_score=risk_score,
            confidence=confidence,
            explanation=explanation_data,
            ipfs_hash=None,
            blockchain_hash=None,
            features=features,
            timestamp=datetime.utcnow().isoformat(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Demo error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Demo failed: {e}")
