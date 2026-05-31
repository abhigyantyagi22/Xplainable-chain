"""
Admin endpoints for API key management.
All routes require the MASTER_API_KEY (see middleware/auth.py).
"""

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.middleware.auth import _store, require_master_key

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["admin"])


class CreateKeyRequest(BaseModel):
    description: str = Field(..., min_length=1, max_length=200,
                              description="Human-readable label for this key")


class CreateKeyResponse(BaseModel):
    key: str
    description: str
    note: str = "Save this key — it is shown only once and never stored in plaintext."


class KeyMetadata(BaseModel):
    id: str
    description: str
    created_at: str
    last_used: str | None


@router.post("/keys", response_model=CreateKeyResponse,
             dependencies=[Depends(require_master_key)])
async def create_api_key(body: CreateKeyRequest):
    """
    Generate a new API key.

    The plaintext key is returned exactly once in this response.
    Store it securely — it cannot be recovered after this call.
    """
    if _store is None:
        raise HTTPException(status_code=503, detail="Key store not available (MongoDB offline).")

    plaintext = _store.create(body.description)
    logger.info(f"New API key created: {body.description}")

    return CreateKeyResponse(
        key=plaintext,
        description=body.description,
    )


@router.get("/keys", dependencies=[Depends(require_master_key)])
async def list_api_keys():
    """List active API keys (metadata only — no hashes or plaintexts)."""
    if _store is None:
        raise HTTPException(status_code=503, detail="Key store not available.")

    keys = _store.list_keys()
    return {"active_keys": len(keys), "keys": keys}


@router.delete("/keys/{key_id}", dependencies=[Depends(require_master_key)])
async def revoke_api_key(key_id: str):
    """Permanently revoke an API key by its MongoDB document ID."""
    if _store is None:
        raise HTTPException(status_code=503, detail="Key store not available.")

    revoked = _store.revoke(key_id)
    if not revoked:
        raise HTTPException(status_code=404, detail=f"Key {key_id} not found or already revoked.")

    logger.info(f"API key revoked: {key_id}")
    return {"revoked": True, "key_id": key_id}
