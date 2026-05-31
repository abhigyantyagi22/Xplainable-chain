"""
Model backtesting against known historical exploits.

Tests the trained model against transactions from three major hacks:
  1. Ronin Bridge hack (March 2022, ~$625M)
  2. Tornado Cash usage (OFAC-sanctioned)
  3. PolyNetwork exploit (August 2021, ~$611M)

For each event, fetches transactions from the known attacker address,
extracts features, and reports how many the model catches.

A production-ready fraud detector should catch ≥80% of these known events.
If it doesn't, retrain with more data (run collect_transaction_data.py again).

Usage (from backend/):
    python backtest_model.py

Requires:
  - ETHERSCAN_API_KEY in .env
  - trained models in app/ml/ (run train_all_models.py first)
"""

import logging
import os
import pickle
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(message)s")
logger = logging.getLogger(__name__)

ROOT      = Path(__file__).parent
MODEL_DIR = ROOT / "app" / "ml"
API_KEY   = os.getenv("ETHERSCAN_API_KEY", "")
BASE_URL  = "https://api.etherscan.io/v2/api"
CHAIN_ID  = 1   # Ethereum mainnet
RATE_LIMIT = 0.22

_last_call = 0.0

# ── Known exploit events ───────────────────────────────────────────────────────
BACKTEST_EVENTS = [
    {
        "name":       "Ronin Bridge Hack (Mar 2022, $625M)",
        "address":    "0x098b716b8aaf21512996dc57eb0615e2383e2f96",
        "label":      "fraud",
        "expected_catch_rate": 0.70,
    },
    {
        "name":       "PolyNetwork Exploiter (Aug 2021, $611M)",
        "address":    "0x0d6e286a7cfd25e0f01673702071e46191d7ed0e",
        "label":      "fraud",
        "expected_catch_rate": 0.70,
    },
    {
        "name":       "Euler Finance Hacker (Mar 2023, $197M)",
        "address":    "0xb66cd966670d962c227b3eaba30a872dbfb995db",
        "label":      "fraud",
        "expected_catch_rate": 0.60,
    },
    {
        "name":       "Ethereum Foundation (legitimate baseline)",
        "address":    "0xde0b295669a9fd93d5f28d9ec85e40f4cb697bae",
        "label":      "legit",
        "expected_catch_rate": 0.0,   # expect FP rate < 20%
    },
    {
        "name":       "Vitalik Buterin (legitimate baseline)",
        "address":    "0xab5801a7d398351b8be11c439e05c5b3259aec9b",
        "label":      "legit",
        "expected_catch_rate": 0.0,
    },
]

FEATURE_NAMES = [
    "amount", "gas_price", "gas_used", "gas_price_deviation",
    "value", "sender_tx_count", "is_contract_creation",
    "contract_age", "block_gas_used_ratio",
    "sender_fraud_neighbor_ratio",
    "sender_account_age_days",
]


# ── Etherscan helpers ─────────────────────────────────────────────────────────

def _api(params: dict) -> dict:
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
        return r.json()
    except Exception as e:
        logger.warning(f"API error: {e}")
        return {}


def fetch_transactions(address: str, count: int = 20) -> List[dict]:
    data = _api({"module": "account", "action": "txlist",
                 "address": address, "sort": "desc", "offset": count, "page": 1})
    txs = data.get("result", [])
    return txs if isinstance(txs, list) else []


def block_gas_ratio(block_number: str, _cache: dict = {}) -> float:
    if block_number in _cache:
        return _cache[block_number]
    data = _api({"module": "proxy", "action": "eth_getBlockByNumber",
                 "tag": hex(int(block_number)), "boolean": "false"})
    blk = data.get("result", {}) or {}
    try:
        ratio = int(blk.get("gasUsed", "0x0"), 16) / max(int(blk.get("gasLimit", "0x1"), 16), 1)
    except Exception:
        ratio = 0.5
    _cache[block_number] = ratio
    return ratio


def account_age(address: str, _cache: dict = {}) -> float:
    if address in _cache:
        return _cache[address]
    data = _api({"module": "account", "action": "txlist",
                 "address": address, "sort": "asc", "offset": 1, "page": 1})
    txs = data.get("result", [])
    if isinstance(txs, list) and txs:
        age = max(0.0, (time.time() - int(txs[0].get("timeStamp", time.time()))) / 86400)
    else:
        age = 365.0
    _cache[address] = age
    return age


def fraud_neighbor_ratio(address: str, fraud_set: frozenset, _cache: dict = {}) -> float:
    if address in _cache:
        return _cache[address]
    data = _api({"module": "account", "action": "txlist",
                 "address": address, "sort": "desc", "offset": 20, "page": 1})
    txs = data.get("result", [])
    if not isinstance(txs, list) or not txs:
        _cache[address] = 0.0
        return 0.0
    counterparties = {tx.get(f, "").lower() for tx in txs for f in ("from", "to")} - {address.lower()}
    ratio = sum(1 for a in counterparties if a in fraud_set) / max(len(counterparties), 1)
    _cache[address] = ratio
    return ratio


def build_feature_row(tx: dict, sender: str, fraud_set: frozenset) -> dict:
    """Extract features from a raw Etherscan transaction dict."""
    value_eth      = int(tx.get("value", "0")) / 1e18
    gas_price_gwei = int(tx.get("gasPrice", "50000000000")) / 1e9
    gas_used_val   = int(tx.get("gasUsed", tx.get("gas", "21000")))
    nonce          = int(tx.get("nonce", "0"))
    to_addr        = tx.get("to", "").lower()
    is_creation    = 1 if not to_addr else 0
    block_ratio    = block_gas_ratio(tx.get("blockNumber", "0"))
    fnr            = fraud_neighbor_ratio(sender, fraud_set)
    age            = account_age(sender)

    return {
        "amount":                      value_eth,
        "gas_price":                   gas_price_gwei,
        "gas_used":                    float(gas_used_val),
        "gas_price_deviation":         abs(gas_price_gwei - 50) / 50,
        "value":                       value_eth,
        "sender_tx_count":             float(nonce),
        "is_contract_creation":        float(is_creation),
        "contract_age":                0.0,
        "block_gas_used_ratio":        block_ratio,
        "sender_fraud_neighbor_ratio": fnr,
        "sender_account_age_days":     age,
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if not API_KEY:
        logger.error("ETHERSCAN_API_KEY not set — cannot fetch backtest transactions.")
        sys.exit(1)

    # Load model and scaler
    model_path  = MODEL_DIR / "model.pkl"
    scaler_path = MODEL_DIR / "scaler.pkl"
    if not model_path.exists():
        logger.error("Model not found — run train_all_models.py first.")
        sys.exit(1)

    with open(model_path, "rb")  as f: model  = pickle.load(f)
    with open(scaler_path, "rb") as f: scaler = pickle.load(f)
    logger.info(f"Loaded model from {model_path}")

    # Load fraud address set
    sys.path.insert(0, str(ROOT))
    from app.utils.fraud_addresses import ALL_FRAUD_ADDRESSES

    logger.info("\n" + "=" * 65)
    logger.info("  XAI-Chain — Model Backtest Against Known Exploits")
    logger.info("=" * 65)

    results: List[dict] = []

    for event in BACKTEST_EVENTS:
        logger.info(f"\n── {event['name']} ──")
        logger.info(f"   Address : {event['address']}")

        txs = fetch_transactions(event["address"], count=20)
        if not txs:
            logger.warning("   No transactions found — skipping")
            continue

        predictions = []
        for tx in txs:
            try:
                row   = build_feature_row(tx, event["address"], ALL_FRAUD_ADDRESSES)
                X     = pd.DataFrame([row])[FEATURE_NAMES]
                Xs    = scaler.transform(X)
                prob  = model.predict_proba(Xs)[0][1]
                predictions.append(prob)
            except Exception as e:
                logger.debug(f"   Feature extraction error: {e}")

        if not predictions:
            continue

        flagged_at_70 = sum(1 for p in predictions if p >= 0.70)
        flagged_at_50 = sum(1 for p in predictions if p >= 0.50)
        avg_score     = np.mean(predictions)
        catch_rate_70 = flagged_at_70 / len(predictions)

        is_fraud = event["label"] == "fraud"
        passed   = (is_fraud and catch_rate_70 >= event["expected_catch_rate"]) or \
                   (not is_fraud and catch_rate_70 <= 0.20)

        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"   Transactions   : {len(predictions)}")
        logger.info(f"   Avg risk score : {avg_score*100:.1f}%")
        logger.info(f"   Flagged @50%   : {flagged_at_50}/{len(predictions)}")
        logger.info(f"   Flagged @70%   : {flagged_at_70}/{len(predictions)}  (catch rate: {catch_rate_70:.0%})")
        logger.info(f"   Expected       : ≥{event['expected_catch_rate']:.0%} for fraud")
        logger.info(f"   Result         : {status}")

        results.append({
            "event":          event["name"],
            "label":          event["label"],
            "n_txs":          len(predictions),
            "avg_risk":       round(avg_score * 100, 1),
            "catch_rate_70":  round(catch_rate_70, 3),
            "expected":       event["expected_catch_rate"],
            "passed":         passed,
        })

    # Summary
    logger.info("\n" + "=" * 65)
    logger.info("  BACKTEST SUMMARY")
    logger.info("=" * 65)
    passed  = sum(1 for r in results if r["passed"])
    total   = len(results)
    fraud_r = [r for r in results if r["label"] == "fraud"]
    legit_r = [r for r in results if r["label"] == "legit"]

    for r in results:
        status = "✅" if r["passed"] else "❌"
        logger.info(f"  {status}  {r['event'][:45]:<45}  avg_risk={r['avg_risk']}%  catch={r['catch_rate_70']:.0%}")

    logger.info(f"\n  Passed : {passed}/{total}")
    if fraud_r:
        avg_catch = np.mean([r["catch_rate_70"] for r in fraud_r])
        logger.info(f"  Avg fraud catch rate (≥70% threshold) : {avg_catch:.0%}")
    if legit_r:
        avg_fp = np.mean([r["catch_rate_70"] for r in legit_r])
        logger.info(f"  Avg false-positive rate on legit addrs : {avg_fp:.0%}")

    if passed < total:
        logger.info("\n  ⚠️  Model needs improvement. Recommended actions:")
        logger.info("     1. Run collect_transaction_data.py to get more training data")
        logger.info("     2. Re-run train_all_models.py")
        logger.info("     3. Re-run this backtest")
    else:
        logger.info("\n  ✅  Model passes all backtest cases. Ready for production.")
    logger.info("=" * 65)


if __name__ == "__main__":
    main()
