"""
Secrets resolution utility.

Resolution order
────────────────
  1. AWS Secrets Manager  (if boto3 is installed AND AWS_SECRET_NAME is set)
  2. Environment variable / .env file  (always available as fallback)

This means the app runs identically in local dev (env vars) and in production
(Secrets Manager) without any code changes — only the env vars differ.

To use AWS Secrets Manager:
  1. pip install boto3
  2. Set AWS_SECRET_NAME=xai-chain/production in .env
  3. Set AWS_REGION=us-east-1 (or your region)
  4. Ensure the IAM role / credentials have secretsmanager:GetSecretValue

The secret in AWS Secrets Manager should be a JSON object whose keys match
the environment variable names, e.g.:
  {
    "PRIVATE_KEY": "0xabc...",
    "ETHERSCAN_API_KEY": "...",
    "PINATA_JWT": "...",
    "MASTER_API_KEY": "..."
  }

WARNING flags
─────────────
Printed at startup when the app detects insecure secret handling:
  - PRIVATE_KEY present in environment (should come from Secrets Manager in prod)
  - MASTER_API_KEY not set (admin endpoints will not work)
"""

import json
import logging
import os
from functools import lru_cache
from typing import Optional

logger = logging.getLogger(__name__)

_AWS_SECRET_NAME: str = os.getenv("AWS_SECRET_NAME", "")
_AWS_REGION: str      = os.getenv("AWS_REGION", "us-east-1")

# Cache so Secrets Manager is called only once per process lifetime
@lru_cache(maxsize=1)
def _fetch_aws_secrets() -> dict:
    """Fetch all secrets from AWS Secrets Manager as a dict."""
    if not _AWS_SECRET_NAME:
        return {}
    try:
        import boto3
        client = boto3.client("secretsmanager", region_name=_AWS_REGION)
        response = client.get_secret_value(SecretId=_AWS_SECRET_NAME)
        secret_str = response.get("SecretString", "{}")
        secrets = json.loads(secret_str)
        logger.info(f"Loaded {len(secrets)} secrets from AWS Secrets Manager ({_AWS_SECRET_NAME})")
        return secrets
    except ImportError:
        logger.debug("boto3 not installed — AWS Secrets Manager unavailable")
        return {}
    except Exception as e:
        logger.warning(f"AWS Secrets Manager fetch failed: {e} — falling back to env vars")
        return {}


def get_secret(name: str, default: str = "") -> str:
    """
    Resolve a secret by name.

    Checks AWS Secrets Manager first (if configured), then env vars.
    """
    aws = _fetch_aws_secrets()
    if name in aws:
        return aws[name]
    return os.getenv(name, default)


# ── Startup security audit ─────────────────────────────────────────────────────

def run_security_checks() -> None:
    """
    Print warnings for known insecure configurations.
    Call this once from main.py lifespan / startup event.
    """
    warnings: list[str] = []

    # Private key in env var is insecure in production
    if os.getenv("PRIVATE_KEY") and not _AWS_SECRET_NAME:
        warnings.append(
            "PRIVATE_KEY is set as an environment variable. "
            "In production, store it in AWS Secrets Manager or HashiCorp Vault "
            "and set AWS_SECRET_NAME to load it securely."
        )

    # No master key = admin endpoints non-functional
    if not get_secret("MASTER_API_KEY"):
        warnings.append(
            "MASTER_API_KEY is not set. Admin endpoints (/admin/keys) will return 503. "
            "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
        )

    # Auth disabled
    if os.getenv("ENABLE_AUTH", "true").lower() in ("false", "0", "no"):
        warnings.append(
            "ENABLE_AUTH=false — API authentication is disabled. "
            "Never deploy to production with this setting."
        )

    # No Etherscan key = degraded feature enrichment
    if not get_secret("ETHERSCAN_API_KEY"):
        warnings.append(
            "ETHERSCAN_API_KEY is not set. contract_age and gas_price_deviation "
            "will use fallback estimates instead of real Etherscan data."
        )

    if warnings:
        logger.warning("=" * 60)
        logger.warning("  SECURITY / CONFIGURATION WARNINGS")
        logger.warning("=" * 60)
        for i, w in enumerate(warnings, 1):
            logger.warning(f"  [{i}] {w}")
        logger.warning("=" * 60)
    else:
        logger.info("Security checks passed.")
