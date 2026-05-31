import re
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

# Valid blockchain networks accepted by the API
_VALID_NETWORKS = {"ethereum", "polygon", "polygon-amoy"}
_TX_HASH_RE = re.compile(r"^0x[a-fA-F0-9]{64}$")
_ETH_ADDR_RE = re.compile(r"^0x[a-fA-F0-9]{40}$")


class AnalyzeRequest(BaseModel):
    """Request model for transaction analysis."""

    tx_hash: str = Field(
        ...,
        min_length=66,
        max_length=66,
        description="Ethereum/Polygon transaction hash (0x + 64 hex chars)",
    )
    network: str = Field(
        default="ethereum",
        description="Blockchain network",
    )
    # Optional pre-computed features — max 20 keys, values must be numbers
    transaction_data: Optional[Dict[str, float]] = Field(
        None,
        description="Pre-computed feature dict (9 keys max) — skips blockchain fetch",
    )

    @field_validator("tx_hash")
    @classmethod
    def validate_tx_hash(cls, v: str) -> str:
        if not _TX_HASH_RE.match(v):
            raise ValueError("Transaction hash must be 0x followed by exactly 64 hex characters")
        return v.lower()

    @field_validator("network")
    @classmethod
    def validate_network(cls, v: str) -> str:
        if v not in _VALID_NETWORKS:
            raise ValueError(f"Network must be one of: {sorted(_VALID_NETWORKS)}")
        return v

    @field_validator("transaction_data")
    @classmethod
    def validate_transaction_data(cls, v: Optional[Dict]) -> Optional[Dict]:
        if v is None:
            return v
        if len(v) > 20:
            raise ValueError("transaction_data must contain at most 20 keys")
        for key, val in v.items():
            if not isinstance(key, str) or len(key) > 64:
                raise ValueError("transaction_data keys must be strings of at most 64 characters")
            if not isinstance(val, (int, float)):
                raise ValueError(f"transaction_data values must be numbers; got {type(val)} for key '{key}'")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "tx_hash": "0x5c504ed432cb51138bcf09aa5e8a410dd4a1e204ef84bfed1be16dfba1b22060",
                "network": "ethereum",
            }
        }
    }


class AnalyzeResponse(BaseModel):
    """Response model for transaction analysis."""

    tx_hash: str
    is_malicious: bool
    risk_score: int = Field(..., ge=0, le=100, description="Risk score 0-100")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Fraud probability (P(fraud))")
    explanation: Dict[str, Any]
    ipfs_hash: Optional[str] = None
    blockchain_hash: Optional[str] = None
    features: Dict[str, Any]
    timestamp: Optional[str] = None

    # Production transparency fields
    is_experimental: bool = Field(
        default=True,
        description=(
            "True when the risk score comes from the ML model (treat as soft signal). "
            "False when it comes from a definitive source: OFAC sanctions list, "
            "Chainabuse community reports, or internal fraud history (hard block)."
        ),
    )
    screening_source: Optional[str] = Field(
        default=None,
        description="Source that flagged this transaction: 'ofac' | 'chainabuse' | 'internal' | None (ML only)",
    )


class VerifyResponse(BaseModel):
    """Response model for on-chain verification."""

    tx_hash: str
    exists: bool
    verified: bool
    ipfs_hash: Optional[str] = None
    risk_score: Optional[int] = None
    auditor: Optional[str] = None
    timestamp: Optional[int] = None


class AuditLogEntry(BaseModel):
    """One entry in the analysis audit trail."""

    tx_hash: str
    risk_score: int
    is_malicious: bool
    analyzed_at: str
    blockchain_hash: Optional[str] = None
    ipfs_hash: Optional[str] = None


# ── Prevention (pre-transaction check) ────────────────────────────────────────

class PreTransactionRequest(BaseModel):
    """Request model for the pre-transaction risk check."""

    to_address: str = Field(..., description="Recipient Ethereum address")
    amount: float = Field(
        0, ge=0, le=10_000,
        description="Amount to send in ETH (max 10 000)",
    )
    gas_price: Optional[int] = Field(
        None, ge=1, le=10_000,
        description="Gas price in Gwei (1–10 000)",
    )
    from_address: Optional[str] = Field(None, description="Sender address (optional)")
    gas_limit: Optional[int] = Field(
        None, ge=21_000, le=30_000_000,
        description="Gas limit (21 000–30 000 000)",
    )

    @field_validator("to_address", "from_address", mode="before")
    @classmethod
    def validate_eth_address(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not _ETH_ADDR_RE.match(v):
            raise ValueError(f"'{v}' is not a valid Ethereum address (expected 0x + 40 hex chars)")
        return v.lower()
