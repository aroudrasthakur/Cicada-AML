"""Train Document Lens: XGBoost on document features or heuristic-only fallback."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, classification_report
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier

from app.ml.ml_device import fit_xgboost_classifier, log_device_banner, xgboost_fit_kwargs
from app.utils.logger import get_logger

logger = get_logger(__name__)

OUTPUT_DIR = Path("models/document")

DOCUMENT_FEATURES = [
    "doc_consistency_score", "doc_completeness_score", "doc_timeliness_score",
    "doc_name_mismatch", "doc_address_mismatch", "doc_expired",
    "doc_count", "doc_types_count",
]

HEURISTIC_FALLBACK_FEATURES = [
    "heuristic_mean", "heuristic_max", "heuristic_triggered_count",
    "heuristic_top_confidence",
]


def _load_data(data_dir: Path) -> tuple[pd.DataFrame, str]:
    doc_path = data_dir / "document_features.csv"
    train_path = data_dir / "train_features.csv"

    if doc_path.exists():
        df = pd.read_csv(doc_path)
        logger.info("Loaded document features: %d rows", len(df))
        return df, "full"

    if train_path.exists():
        df = pd.read_csv(train_path)
        logger.info("No document features found; training in reduced mode from %s", train_path)
        return df, "reduced"

    logger.error("No training data found in %s", data_dir)
    logger.info(
        "Run the feature pipeline first:\n"
        "  python -m scripts.prepare_features --output %s",
        data_dir,
    )
    sys.exit(1)


def _prepare_features(df: pd.DataFrame, mode: str) -> tuple[np.ndarray, list[str]]:
    if mode == "full":
        cols = [c for c in DOCUMENT_FEATURES if c in df.columns]
    else:
        cols = [c for c in HEURISTIC_FALLBACK_FEATURES if c in df.columns]

    if not cols:
        logger.warning("No expected columns found; using all numeric columns")
        cols = df.select_dtypes(include=[np.number]).columns.drop("label", errors="ignore").tolist()

    X = df[cols].fillna(0).values.astype(np.float32)
    return X, cols


def main() -> None:
    parser = argparse.ArgumentParser(description="Train Document Lens classifier")
    parser.add_argument("--data-dir", default="data/processed", help="Directory with preprocessed data")
    args = parser.parse_args()
    data_dir = Path(args.data_dir)

    logger.info("=== Training Document Lens ===")
    log_device_banner(logger, "train_document")
    df, mode = _load_data(data_dir)
    logger.info("Training mode: %s", mode)

    if "label" not in df.columns:
        logger.error("No 'label' column found in data; cannot train")
        sys.exit(1)

    X, feature_names = _prepare_features(df, mode)
    y = df["label"].values.astype(int)

    X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    n_pos = int(y_train.sum())
    n_neg = len(y_train) - n_pos
    spw = n_neg / max(n_pos, 1)
    logger.info("Mode=%s  features=%d  balance: %d pos / %d neg → spw=%.2f", mode, len(feature_names), n_pos, n_neg, spw)

    model = XGBClassifier(
        n_estimators=200,
        max_depth=5,
        learning_rate=0.05,
        scale_pos_weight=spw,
        eval_metric="aucpr",
        early_stopping_rounds=15,
        random_state=42,
        use_label_encoder=False,
        **xgboost_fit_kwargs(),
    )
    model = fit_xgboost_classifier(model, X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)

    y_prob = model.predict_proba(X_val)[:, 1]
    pr_auc = average_precision_score(y_val, y_prob)
    logger.info("Document XGBoost PR-AUC on validation: %.4f", pr_auc)
    logger.info("\n%s", classification_report(y_val, (y_prob >= 0.5).astype(int), zero_division=0))

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, OUTPUT_DIR / "document_classifier.pkl")
    joblib.dump(feature_names, OUTPUT_DIR / "feature_names.pkl")
    joblib.dump(mode, OUTPUT_DIR / "training_mode.pkl")
    logger.info("Artifacts saved to %s (mode=%s)", OUTPUT_DIR, mode)


if __name__ == "__main__":
    main()
