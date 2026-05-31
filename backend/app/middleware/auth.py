"""
API key authentication for XAI-Chain.

Every protected route depends on `verify_api_key`.  Set ENABLE_AUTH=false in
.env to disable auth entirely during local development.

Key lifecycle
─────────────
  Bootstrap : set MASTER_API_KEY in .env — this key is never stored and always
              works, even when MongoDB is unavailable.
  Create    : POST /admin/keys  (master key required)
  List      : GET  /admin/keys  (master key required)
  Revoke    : DELETE /admin/keys/{key_id}  (master key required)

Keys at rest are stored as SHA-256 hashes — the plaintext is returned only once
at creation time and is never stored.
"""

import hashlib
import logging
import os
import secrets
from datetime import datetime
from typing import Optional

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

logger = logging.getLogger(__name__)

_API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

# Loaded once at import time so the hot-path doesn't call os.getenv on every request
_MASTER_KEY: str = os.getenv("MASTER_API_KEY", "")
_AUTH_ENABLED: bool = os.getenv("ENABLE_AUTH", "true").lower() not in ("false", "0", "no")


def _hash(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


# ── MongoDB-backed key store ───────────────────────────────────────────────────

class APIKeyStore:
    """
    Thin wrapper around the MongoDB `api_keys` collection.
    Instantiated once and shared across requests.
    """

    def __init__(self, collection):
        self._col = collection

    # ── write operations ──────────────────────────────────────────────────────

    def create(self, description: str) -> str:
        """Generate a key, persist its hash, return the plaintext."""
        plaintext = secrets.token_urlsafe(32)
        self._col.insert_one({
            "key_hash":    _hash(plaintext),
            "description": description,
            "created_at":  datetime.utcnow(),
            "last_used":   None,
            "active":      True,
        })
        return plaintext

    def revoke(self, key_id: str) -> bool:
        from bson import ObjectId
        result = self._col.update_one(
            {"_id": ObjectId(key_id)},
            {"$set": {"active": False}},
        )
        return result.modified_count > 0

    # ── read operations ───────────────────────────────────────────────────────

    def verify(self, plaintext: str) -> bool:
        """Return True if the key exists, is active, and update last_used."""
        h = _hash(plaintext)
        doc = self._col.find_one({"key_hash": h, "active": True})
        if doc:
            self._col.update_one({"key_hash": h}, {"$set": {"last_used": datetime.utcnow()}})
            return True
        return False

    def list_keys(self) -> list:
        """Return key metadata — never returns hashes."""
        cursor = self._col.find({"active": True}, {"key_hash": 0})
        return [
            {
                "id":          str(doc["_id"]),
                "description": doc.get("description", ""),
                "created_at":  doc.get("created_at"),
                "last_used":   doc.get("last_used"),
            }
            for doc in cursor
        ]


# Module-level store — populated by main.py after MongoDB connects
_store: Optional[APIKeyStore] = None


def init_key_store(collection) -> None:
    """Call this once in main.py after the MongoDB collection is ready."""
    global _store
    _store = APIKeyStore(collection)
    logger.info("API key store initialised")


# ── FastAPI dependency ─────────────────────────────────────────────────────────

async def verify_api_key(api_key: str = Security(_API_KEY_HEADER)) -> str:
    """
    FastAPI dependency injected into every protected router.

    Priority:
      1. Auth disabled (ENABLE_AUTH=false) → pass through
      2. Master key match                  → pass through
      3. MongoDB key match                 → pass through
      4. All else                          → 401
    """
    if not _AUTH_ENABLED:
        return "dev-mode"

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Add the X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Master key — always works (for bootstrapping and admin ops)
    if _MASTER_KEY and api_key == _MASTER_KEY:
        return api_key

    # MongoDB-backed key
    if _store is not None and _store.verify(api_key):
        return api_key

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or revoked API key.",
        headers={"WWW-Authenticate": "ApiKey"},
    )


async def require_master_key(api_key: str = Security(_API_KEY_HEADER)) -> str:
    """
    Stricter dependency used by /admin/* endpoints.
    Only the MASTER_API_KEY is accepted — regular client keys are refused.
    """
    if not _MASTER_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MASTER_API_KEY not configured. Set it in .env to enable admin endpoints.",
        )
    if api_key != _MASTER_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin operations require the master API key.",
        )
    return api_key
