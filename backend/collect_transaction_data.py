"""
Real transaction-level fraud dataset collector.

Replaces the Kaggle account-level dataset with per-transaction labeled data
collected directly from the Ethereum blockchain via Etherscan API.

Label definitions
─────────────────
  fraud=1 : transaction sent FROM or TO a known fraud address
             (OFAC sanctioned, known exploit wallet — see fraud_addresses.py)
  fraud=0 : transaction sent from a well-known, long-standing legitimate address

Features collected (11 features — matches model training)
───────────────────────────────────────────────────────────
  amount, gas_price, gas_used, gas_price_deviation,
  value, sender_tx_count, is_contract_creation, contract_age,
  block_gas_used_ratio,
  sender_fraud_neighbor_ratio,   ← new graph feature
  sender_account_age_days        ← new graph feature

Prerequisites
─────────────
  Set ETHERSCAN_API_KEY in backend/.env before running.
  Free tier: 5 req/s, 100k calls/day — sufficient for this script.

Usage (from backend/):
    python collect_transaction_data.py

Output:
    backend/data/transaction_level_labeled.csv
    (used directly by train_all_models.py — no other data source needed)
"""

import csv
import logging
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(message)s")
logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────
API_KEY     = os.getenv("ETHERSCAN_API_KEY", "")
BASE_URL    = "https://api.etherscan.io/v2/api"
CHAIN_ID    = 1   # Ethereum mainnet
RATE_LIMIT  = 0.22   # seconds between calls (≤5 req/s on free tier)
TX_PER_ADDR = 50     # transactions to collect per seed address
OUTPUT_PATH = Path(__file__).parent / "data" / "transaction_level_labeled.csv"

FEATURE_NAMES = [
    "amount", "gas_price", "gas_used", "gas_price_deviation",
    "value", "sender_tx_count", "is_contract_creation", "contract_age",
    "block_gas_used_ratio",
    "sender_fraud_neighbor_ratio",
    "sender_account_age_days",
    "label",
]

# ── Seed addresses ────────────────────────────────────────────────────────────
# Import canonical fraud set (no hardcoding here)
sys.path.insert(0, str(Path(__file__).parent))
from app.utils.fraud_addresses import ALL_FRAUD_ADDRESSES, OFAC_ADDRESSES, KNOWN_HACK_ADDRESSES  # noqa: E402

# Seed fraud addresses — fetch transactions FROM these
FRAUD_SEED_ADDRESSES = [
    "0x098b716b8aaf21512996dc57eb0615e2383e2f96",  # Ronin Bridge hacker
    "0x0d6e286a7cfd25e0f01673702071e46191d7ed0e",  # PolyNetwork exploiter
    "0xd90e2f925da726b50c4ed8d0fb90ad053324f31b",  # Tornado Cash proxy
    "0x910cbd523d972eb0a6f4cae4618ad62622b39dbf",  # Tornado Cash proxy
    "0xb541fc07bc7619fd4062a54d96268525cbc6ffef",  # Tornado Cash proxy
    "0x8576acc5c05d6ce88f4e49bf65bdf0c62f91353c",  # Blender.io
    "0x7f367cc41522ce07553e823bf3be79a889debe1b",  # Blender.io
    "0xb66cd966670d962c227b3eaba30a872dbfb995db",  # Euler Finance hacker
    "0x56d8b635a7c88fd1104d23d632af40c1e3a550a1",  # Nomad Bridge hacker
    "0xe74b28c2eae8679e3ccc3a94d5d0de83ccb84705",  # Wintermute hack
]

# Legitimate seed addresses — well-known, long-standing, clean accounts
LEGIT_SEED_ADDRESSES = [
    "0xde0b295669a9fd93d5f28d9ec85e40f4cb697bae",  # Ethereum Foundation
    "0xab5801a7d398351b8be11c439e05c5b3259aec9b",  # Vitalik Buterin
    "0x28c6c06298d514db089934071355e5743bf21d60",  # Binance hot wallet
    "0x21a31ee1afc51d94c2efccaa2092ad1028285549",  # Binance cold wallet
    "0xdfd5293d8e347dfe59e90efd55b2956a1343963d",  # Coinbase
    "0x4976fb03c32e5b8cfe2b6ccb31c09ba78ebaba41",  # ENS Public Resolver
    "0x00000000219ab540356cbb839cbe05303d7705fa",  # ETH2 deposit contract
    "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",  # WETH contract
    "0x7a250d5630b4cf539739df2c5dacb4c659f2488d",  # Uniswap V2 Router
    "0xe592427a0aece92de3edee1f18e0157c05861564",  # Uniswap V3 Router
]


# ── Etherscan helpers ─────────────────────────────────────────────────────────

_last_call = 0.0

def _call(params: dict) -> Optional[dict]:
    """Rate-limited Etherscan API call."""
    global _last_call
    elapsed = time.time() - _last_call
    if elapsed < RATE_LIMIT:
        time.sleep(RATE_LIMIT - elapsed)
    _last_call = time.time()

    params["apikey"]  = API_KEY
    params["chainid"] = CHAIN_ID
    try:
        r = requests.get(BASE_URL, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        if data.get("status") == "0" and "No transactions found" in str(data.get("message", "")):
            return {"result": []}
        return data
    except Exception as e:
        logger.warning(f"API call failed: {e}")
        return None


def get_transactions(address: str, count: int = TX_PER_ADDR) -> List[dict]:
    """Fetch the most recent N transactions for an address."""
    resp = _call({
        "module": "account", "action": "txlist",
        "address": address, "sort": "desc",
        "offset": count, "page": 1,
    })
    if resp and isinstance(resp.get("result"), list):
        return resp["result"][:count]
    return []


def get_block_gas_ratio(block_number: str, _cache: dict = {}) -> float:
    """Block gas used / gas limit ratio (cached per block)."""
    if block_number in _cache:
        return _cache[block_number]
    resp = _call({
        "module": "proxy", "action": "eth_getBlockByNumber",
        "tag": hex(int(block_number)), "boolean": "false",
    })
    ratio = 0.5  # default
    if resp and resp.get("result"):
        blk = resp["result"]
        try:
            used  = int(blk.get("gasUsed", "0x0"), 16)
            limit = int(blk.get("gasLimit", "0x1"), 16) or 1
            ratio = used / limit
        except (ValueError, TypeError):
            pass
    _cache[block_number] = ratio
    return ratio


def get_account_age_days(address: str, _cache: dict = {}) -> float:
    """Days since the first transaction of this address."""
    if address in _cache:
        return _cache[address]
    resp = _call({
        "module": "account", "action": "txlist",
        "address": address, "sort": "asc",
        "offset": 1, "page": 1,
    })
    age = 0.0
    if resp and isinstance(resp.get("result"), list) and resp["result"]:
        first_ts = int(resp["result"][0].get("timeStamp", time.time()))
        age = max(0.0, (time.time() - first_ts) / 86_400)
    _cache[address] = age
    return age


def get_sender_fraud_neighbor_ratio(
    sender: str,
    recent_count: int = 20,
    _cache: dict = {},
) -> float:
    """
    Fraction of the sender's recent transaction counterparties that are
    in the known fraud address set.

    This is the core graph feature: it captures indirect fraud exposure
    even when the current transaction is not directly to/from a fraud wallet.
    """
    if sender in _cache:
        return _cache[sender]

    resp = _call({
        "module": "account", "action": "txlist",
        "address": sender, "sort": "desc",
        "offset": recent_count, "page": 1,
    })
    ratio = 0.0
    if resp and isinstance(resp.get("result"), list):
        txs = resp["result"]
        counterparties = set()
        for tx in txs:
            for field in ("from", "to"):
                addr = tx.get(field, "").lower()
                if addr and addr != sender.lower():
                    counterparties.add(addr)
        if counterparties:
            fraud_count = sum(1 for a in counterparties if a in ALL_FRAUD_ADDRESSES)
            ratio = fraud_count / len(counterparties)
    _cache[sender] = ratio
    return ratio


def get_contract_age_days(address: str, _cache: dict = {}) -> float:
    """Days since contract deployment (0 for EOAs)."""
    if address in _cache:
        return _cache[address]
    # Check if it's a contract by looking for contract creation tx
    resp = _call({
        "module": "account", "action": "txlistinternal",
        "address": address, "sort": "asc",
        "offset": 1, "page": 1,
        "action": "txlist",
    })
    # Simple heuristic: EOA = 0 days
    _cache[address] = 0.0
    return 0.0


# ── Feature extraction ────────────────────────────────────────────────────────

def extract_tx_features(tx: dict, label: int) -> Optional[dict]:
    """
    Extract all 11 features from a raw Etherscan transaction record.
    Returns None if the transaction is invalid/incomplete.
    """
    try:
        sender    = tx.get("from", "").lower()
        recipient = tx.get("to", "").lower()
        if not sender:
            return None

        # Core transaction features
        value_wei   = int(tx.get("value", "0"))
        value_eth   = value_wei / 1e18
        gas_price_wei = int(tx.get("gasPrice", "50000000000"))
        gas_price_gwei = gas_price_wei / 1e9
        gas_used    = int(tx.get("gasUsed", tx.get("gas", "21000")))
        nonce       = int(tx.get("nonce", "0"))

        # gas_price_deviation vs 50 Gwei long-run median
        median_gas = 50.0
        gas_price_deviation = abs(gas_price_gwei - median_gas) / median_gas

        # is_contract_creation
        is_contract_creation = 1 if not recipient else 0

        # contract_age (recipient): we use 0 as default — expensive to compute for every tx
        contract_age = 0.0

        # block_gas_used_ratio
        block_number = tx.get("blockNumber", "0")
        block_gas_ratio = get_block_gas_ratio(block_number)

        # Graph features
        fraud_neighbor_ratio = get_sender_fraud_neighbor_ratio(sender)
        account_age_days     = get_account_age_days(sender)

        return {
            "amount":                      value_eth,
            "gas_price":                   gas_price_gwei,
            "gas_used":                    float(gas_used),
            "gas_price_deviation":         gas_price_deviation,
            "value":                       value_eth,
            "sender_tx_count":             float(nonce),
            "is_contract_creation":        float(is_contract_creation),
            "contract_age":                contract_age,
            "block_gas_used_ratio":        block_gas_ratio,
            "sender_fraud_neighbor_ratio": fraud_neighbor_ratio,
            "sender_account_age_days":     account_age_days,
            "label":                       label,
        }
    except (ValueError, TypeError) as e:
        logger.debug(f"Feature extraction failed: {e}")
        return None


# ── Main collection loop ──────────────────────────────────────────────────────

def collect(label: int, addresses: List[str]) -> List[dict]:
    """Collect labeled transactions from a list of seed addresses."""
    rows: List[dict] = []
    category = "fraud" if label == 1 else "legitimate"

    for addr in addresses:
        logger.info(f"Fetching {TX_PER_ADDR} {category} transactions from {addr[:12]}…")
        txs = get_transactions(addr, TX_PER_ADDR)

        if not txs:
            logger.warning(f"  No transactions found for {addr[:12]}…")
            continue

        for tx in txs:
            row = extract_tx_features(tx, label)
            if row is not None:
                rows.append(row)

        logger.info(f"  Collected {len(rows)} total {category} rows so far")

    return rows


def main():
    if not API_KEY:
        logger.error(
            "ETHERSCAN_API_KEY not set in backend/.env — "
            "cannot collect real transaction data."
        )
        sys.exit(1)

    logger.info("=" * 60)
    logger.info("  XAI-Chain — Real Transaction Data Collector")
    logger.info("=" * 60)
    logger.info(f"  Fraud seed addresses   : {len(FRAUD_SEED_ADDRESSES)}")
    logger.info(f"  Legit seed addresses   : {len(LEGIT_SEED_ADDRESSES)}")
    logger.info(f"  Transactions per addr  : {TX_PER_ADDR}")
    logger.info(f"  Known fraud addresses  : {len(ALL_FRAUD_ADDRESSES)}")
    logger.info("")

    # Collect fraud and legitimate transactions
    fraud_rows = collect(label=1, addresses=FRAUD_SEED_ADDRESSES)
    legit_rows = collect(label=0, addresses=LEGIT_SEED_ADDRESSES)

    if not fraud_rows or not legit_rows:
        logger.error("Insufficient data collected — check your API key and network connection.")
        sys.exit(1)

    # Balance the dataset (equal fraud/legit)
    min_count = min(len(fraud_rows), len(legit_rows))
    fraud_rows = fraud_rows[:min_count]
    legit_rows = legit_rows[:min_count]

    all_rows = fraud_rows + legit_rows
    # Shuffle
    import random; random.shuffle(all_rows)

    # Save
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FEATURE_NAMES)
        writer.writeheader()
        writer.writerows(all_rows)

    fraud_count = sum(1 for r in all_rows if r["label"] == 1)
    logger.info("")
    logger.info("=" * 60)
    logger.info("  COLLECTION COMPLETE")
    logger.info("=" * 60)
    logger.info(f"  Total transactions    : {len(all_rows)}")
    logger.info(f"  Fraud (label=1)       : {fraud_count} ({fraud_count / len(all_rows) * 100:.1f}%)")
    logger.info(f"  Legitimate (label=0)  : {len(all_rows) - fraud_count}")
    logger.info(f"  Saved to              : {OUTPUT_PATH}")
    logger.info("")
    logger.info("  Next step: python train_all_models.py")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
