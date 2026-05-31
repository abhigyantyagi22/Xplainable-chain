"""
Unified model training script for XAI-Chain.

Trains both models from the same canonical feature mapping:
  - app/ml/model.pkl          → used by /api/analyze and causal XAI endpoints
  - app/ml/prevention_model.pkl → used by /api/check-before-send

Data source: Kaggle Ethereum Fraud Detection Dataset
  backend/data/transaction_dataset.csv  (account-level features, FLAG = fraud label)

Canonical feature mapping is the single source of truth for how Kaggle account-level
columns are translated into the 9 model features.  The same mapping is used in:
  - backend/app/routers/causal.py   (causal analysis on training set)
  - backend/import_kaggle_dataset.py (MongoDB import)
  - HERE (model training)

Usage (from backend/):
    python train_all_models.py

Outputs
-------
  app/ml/model.pkl
  app/ml/scaler.pkl
  app/ml/feature_names.pkl
  app/ml/prevention_model.pkl
  app/ml/prevention_scaler.pkl
"""

import logging
import os
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    roc_auc_score,
    average_precision_score,
)
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── paths ──────────────────────────────────────────────────────────────────────
ROOT        = Path(__file__).parent
# Primary data source: real per-transaction labeled data (collect_transaction_data.py)
REAL_DATA_PATH   = ROOT / "data" / "transaction_level_labeled.csv"
SAVE_DIR    = ROOT / "app" / "ml"

# 11 features — 9 original + 2 graph features
FEATURE_NAMES = [
    "amount", "gas_price", "gas_used", "gas_price_deviation",
    "value", "sender_tx_count", "is_contract_creation",
    "contract_age", "block_gas_used_ratio",
    # Graph features (require real transaction-level data)
    "sender_fraud_neighbor_ratio",
    "sender_account_age_days",
]


# ── Data loading ──────────────────────────────────────────────────────────────

def load_real_data(path: Path) -> pd.DataFrame:
    """
    Load the real per-transaction labeled dataset produced by
    collect_transaction_data.py.

    This is the ONLY data source.  No Kaggle proxies, no synthetic data.
    Raises if the file doesn't exist — run collect_transaction_data.py first.
    """
    if not path.exists():
        raise FileNotFoundError(
            f"\n\nReal training data not found at: {path}\n"
            f"Run the data collector first:\n"
            f"  cd backend && python collect_transaction_data.py\n"
            f"(requires ETHERSCAN_API_KEY in .env)\n"
        )
    df = pd.read_csv(path)
    logger.info(f"Loaded real transaction dataset: {len(df)} samples from {path}")
    logger.info(f"  Columns : {list(df.columns)}")
    fraud = (df["label"] == 1).sum()
    logger.info(f"  Fraud   : {fraud} ({fraud / len(df) * 100:.1f}%)")
    logger.info(f"  Legit   : {len(df) - fraud}")
    # Validate all features are present
    missing = [f for f in FEATURE_NAMES if f not in df.columns]
    if missing:
        raise ValueError(
            f"Real data is missing features: {missing}\n"
            f"Re-run collect_transaction_data.py to regenerate.\n"
        )
    return df.dropna()


# ── evaluation helper ─────────────────────────────────────────────────────────

def evaluate(model, scaler, X_test: pd.DataFrame, y_test: pd.Series, label: str) -> dict:
    """Print and return evaluation metrics for a fitted model."""
    X_scaled = scaler.transform(X_test)
    y_pred  = model.predict(X_scaled)
    y_proba = model.predict_proba(X_scaled)[:, 1]

    auc_roc = roc_auc_score(y_test, y_proba)
    auc_pr  = average_precision_score(y_test, y_proba)

    logger.info(f"\n{'─'*60}")
    logger.info(f"  {label} — evaluation on held-out test set")
    logger.info(f"{'─'*60}")
    logger.info("\n" + classification_report(y_test, y_pred, target_names=["Legitimate", "Fraud"]))
    logger.info(f"Confusion matrix:\n{confusion_matrix(y_test, y_pred)}")
    logger.info(f"ROC-AUC  : {auc_roc:.4f}")
    logger.info(f"PR-AUC   : {auc_pr:.4f}  (better metric for imbalanced data)")
    logger.info(f"{'─'*60}\n")

    return {"roc_auc": auc_roc, "pr_auc": auc_pr}


# ── training ──────────────────────────────────────────────────────────────────

def train_model(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    random_state: int,
) -> tuple[XGBClassifier, StandardScaler]:
    """Scale features and train an XGBClassifier with class-imbalance correction."""

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_train)

    n_neg = int((y_train == 0).sum())
    n_pos = int((y_train == 1).sum())
    scale_pos_weight = n_neg / max(n_pos, 1)
    logger.info(f"Class ratio  : {n_neg} legitimate / {n_pos} fraud  (scale_pos_weight={scale_pos_weight:.2f})")

    model = XGBClassifier(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.05,
        scale_pos_weight=scale_pos_weight,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=5,
        gamma=0.1,
        random_state=random_state,
        eval_metric="aucpr",           # PR-AUC is more informative for imbalanced data
        use_label_encoder=False,
    )
    model.fit(X_scaled, y_train, verbose=False)

    return model, scaler


def cross_validate(model_cls, scaler_cls, X: pd.DataFrame, y: pd.Series, n_splits: int = 5) -> float:
    """Return mean CV ROC-AUC across stratified folds."""
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
    scores = []

    for fold, (train_idx, val_idx) in enumerate(skf.split(X, y), 1):
        X_tr, X_val = X.iloc[train_idx], X.iloc[val_idx]
        y_tr, y_val = y.iloc[train_idx], y.iloc[val_idx]

        scaler = scaler_cls()
        X_tr_s  = scaler.fit_transform(X_tr)
        X_val_s = scaler.transform(X_val)

        n_neg = int((y_tr == 0).sum())
        n_pos = int((y_tr == 1).sum())
        clf = model_cls(
            n_estimators=300, max_depth=6, learning_rate=0.05,
            scale_pos_weight=n_neg / max(n_pos, 1),
            subsample=0.8, colsample_bytree=0.8,
            random_state=42, eval_metric="aucpr", use_label_encoder=False,
        )
        clf.fit(X_tr_s, y_tr, verbose=False)

        proba = clf.predict_proba(X_val_s)[:, 1]
        scores.append(roc_auc_score(y_val, proba))
        logger.info(f"  Fold {fold}: ROC-AUC = {scores[-1]:.4f}")

    mean_auc = float(np.mean(scores))
    std_auc  = float(np.std(scores))
    logger.info(f"  CV ROC-AUC: {mean_auc:.4f} ± {std_auc:.4f}")
    return mean_auc


def save_model(model, scaler, name_prefix: str, feature_names: list):
    """Pickle model, scaler, and feature names list to app/ml/."""
    SAVE_DIR.mkdir(parents=True, exist_ok=True)

    with open(SAVE_DIR / f"{name_prefix}_model.pkl", "wb") as f:
        pickle.dump(model, f)
    with open(SAVE_DIR / f"{name_prefix}_scaler.pkl", "wb") as f:
        pickle.dump(scaler, f)

    # feature_names.pkl is read by ai_detector.py for the primary model
    if name_prefix == "model":
        # strip suffix so it saves as model.pkl (not model_model.pkl)
        pass
    with open(SAVE_DIR / "feature_names.pkl", "wb") as f:
        pickle.dump(feature_names, f)

    logger.info(f"Saved: {name_prefix}_model.pkl, {name_prefix}_scaler.pkl")


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    logger.info("=" * 60)
    logger.info("  XAI-Chain — Unified Model Training Pipeline")
    logger.info("  Data source: real per-transaction labeled data")
    logger.info("=" * 60)

    # 1. Load real per-transaction labeled data (no Kaggle proxies, no synthetic data)
    df = load_real_data(REAL_DATA_PATH)

    X = df[FEATURE_NAMES]
    y = df["label"]

    # 2. Split — 80% train / 20% test (held-out)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )
    logger.info(f"Train: {len(X_train)}  Test: {len(X_test)}")

    # ── Model A: analysis model (model.pkl) ────────────────────────────────────
    logger.info("\n── Training Analysis Model (model.pkl) ──────────────────────")
    logger.info("5-fold stratified cross-validation on train set:")
    cv_auc = cross_validate(XGBClassifier, StandardScaler, X_train, y_train)

    model_a, scaler_a = train_model(X_train, y_train, random_state=42)
    metrics_a = evaluate(model_a, scaler_a, X_test, y_test, "Analysis model")

    # Save — primary paths that ai_detector.py reads
    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    with open(SAVE_DIR / "model.pkl",         "wb") as f: pickle.dump(model_a,  f)
    with open(SAVE_DIR / "scaler.pkl",        "wb") as f: pickle.dump(scaler_a, f)
    with open(SAVE_DIR / "feature_names.pkl", "wb") as f: pickle.dump(FEATURE_NAMES, f)
    logger.info("Saved: model.pkl  scaler.pkl  feature_names.pkl")

    # ── Model B: prevention model (prevention_model.pkl) ──────────────────────
    logger.info("\n── Training Prevention Model (prevention_model.pkl) ─────────")
    model_b, scaler_b = train_model(X_train, y_train, random_state=7)
    metrics_b = evaluate(model_b, scaler_b, X_test, y_test, "Prevention model")

    with open(SAVE_DIR / "prevention_model.pkl",  "wb") as f: pickle.dump(model_b,  f)
    with open(SAVE_DIR / "prevention_scaler.pkl", "wb") as f: pickle.dump(scaler_b, f)
    logger.info("Saved: prevention_model.pkl  prevention_scaler.pkl")

    # ── Model card summary ─────────────────────────────────────────────────────
    logger.info("\n" + "=" * 60)
    logger.info("  MODEL CARD")
    logger.info("=" * 60)
    logger.info(f"  Algorithm        : XGBoost (n_estimators=300, max_depth=6)")
    logger.info(f"  Training data    : Real per-transaction labeled data (Etherscan)")
    logger.info(f"  Data source      : {REAL_DATA_PATH}")
    logger.info(f"  Samples          : {len(df)} transactions ({y.mean()*100:.1f}% fraud)")
    logger.info(f"  Features (11)    : {FEATURE_NAMES}")
    logger.info(f"  CV ROC-AUC       : {cv_auc:.4f}  (5-fold stratified)")
    logger.info(f"  Test ROC-AUC     : {metrics_a['roc_auc']:.4f}")
    logger.info(f"  Test PR-AUC      : {metrics_a['pr_auc']:.4f}")
    logger.info("")
    logger.info("  DATA QUALITY")
    logger.info("  - Training data is per-transaction (matches inference)")
    logger.info("  - Graph features computed from real Etherscan tx history")
    logger.info("  - Fraud labels from OFAC + known exploit wallets (ground truth)")
    logger.info("  - No synthetic data, no Kaggle proxies")
    logger.info("")
    logger.info("  TO IMPROVE")
    logger.info("  - Run collect_transaction_data.py again to get more samples")
    logger.info("  - Add more seed fraud addresses as new exploits are documented")
    logger.info("  - Collect user feedback (POST /api/feedback) to refine labels")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
