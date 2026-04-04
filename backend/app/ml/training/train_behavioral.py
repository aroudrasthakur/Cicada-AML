"""Train Behavioral Lens: XGBoost classifier + autoencoder on transaction features."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.metrics import average_precision_score, classification_report
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

from app.ml.lenses.behavioral_model import BehavioralAutoencoder
from app.utils.logger import get_logger

logger = get_logger(__name__)

BEHAVIORAL_FEATURES = [
    "amount", "log_amount", "fee_ratio", "is_round_amount",
    "burstiness_score", "amount_deviation", "sender_tx_count",
    "receiver_tx_count", "sender_repeat_count",
    "balance_ratio", "unique_counterparties", "relay_pattern_score",
]

OUTPUT_DIR = Path("models/behavioral")
AE_EPOCHS = 50
AE_LR = 1e-3
AE_LATENT = 32
AE_BATCH = 256


def _load_data(data_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    train_path = data_dir / "train_features.csv"
    val_path = data_dir / "val_features.csv"
    if not train_path.exists():
        logger.error("Training data not found at %s", train_path)
        logger.info(
            "Run the feature pipeline first:\n"
            "  python -m scripts.prepare_features --output %s",
            data_dir,
        )
        sys.exit(1)
    train_df = pd.read_csv(train_path)
    val_df = pd.read_csv(val_path) if val_path.exists() else None
    if val_df is None:
        train_df, val_df = train_test_split(train_df, test_size=0.2, random_state=42,
                                            stratify=train_df["label"] if "label" in train_df.columns else None)
    return train_df, val_df


def _select_features(df: pd.DataFrame) -> np.ndarray:
    cols = [c for c in BEHAVIORAL_FEATURES if c in df.columns]
    if not cols:
        logger.warning("No behavioral feature columns found; using all numeric columns")
        cols = df.select_dtypes(include=[np.number]).columns.drop("label", errors="ignore").tolist()
    return df[cols].fillna(0).values.astype(np.float32), cols


def _train_xgboost(X_train, y_train, X_val, y_val) -> XGBClassifier:
    n_pos = int(y_train.sum())
    n_neg = len(y_train) - n_pos
    spw = n_neg / max(n_pos, 1)
    logger.info("Class balance: %d pos / %d neg → scale_pos_weight=%.2f", n_pos, n_neg, spw)

    model = XGBClassifier(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.05,
        scale_pos_weight=spw,
        eval_metric="aucpr",
        early_stopping_rounds=20,
        random_state=42,
        use_label_encoder=False,
    )
    model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)

    y_prob = model.predict_proba(X_val)[:, 1]
    pr_auc = average_precision_score(y_val, y_prob)
    logger.info("XGBoost PR-AUC on validation: %.4f", pr_auc)
    logger.info("\n%s", classification_report(y_val, (y_prob >= 0.5).astype(int), zero_division=0))
    return model


def _train_autoencoder(X_licit: np.ndarray, input_dim: int) -> BehavioralAutoencoder:
    ae = BehavioralAutoencoder(input_dim, latent_dim=AE_LATENT)
    optimizer = torch.optim.Adam(ae.parameters(), lr=AE_LR)
    criterion = nn.MSELoss()
    dataset = torch.FloatTensor(X_licit)

    ae.train()
    for epoch in range(1, AE_EPOCHS + 1):
        perm = torch.randperm(len(dataset))
        epoch_loss = 0.0
        n_batches = 0
        for start in range(0, len(dataset), AE_BATCH):
            idx = perm[start : start + AE_BATCH]
            batch = dataset[idx]
            recon = ae(batch)
            loss = criterion(recon, batch)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            epoch_loss += loss.item()
            n_batches += 1
        if epoch % 10 == 0 or epoch == 1:
            logger.info("AE epoch %d/%d  loss=%.6f", epoch, AE_EPOCHS, epoch_loss / max(n_batches, 1))

    return ae


def main() -> None:
    parser = argparse.ArgumentParser(description="Train Behavioral Lens models")
    parser.add_argument("--data-dir", default="data/processed", help="Directory with preprocessed data")
    args = parser.parse_args()
    data_dir = Path(args.data_dir)

    logger.info("=== Training Behavioral Lens ===")
    train_df, val_df = _load_data(data_dir)

    X_train, feature_names = _select_features(train_df)
    X_val, _ = _select_features(val_df)
    y_train = train_df["label"].values.astype(int)
    y_val = val_df["label"].values.astype(int)

    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_val_s = scaler.transform(X_val)

    xgb_model = _train_xgboost(X_train_s, y_train, X_val_s, y_val)

    licit_mask = y_train == 0
    X_licit = X_train_s[licit_mask]
    logger.info("Training autoencoder on %d licit samples (input_dim=%d)", len(X_licit), X_licit.shape[1])
    ae = _train_autoencoder(X_licit, X_licit.shape[1])

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(xgb_model, OUTPUT_DIR / "xgboost_behavioral.pkl")
    joblib.dump(scaler, OUTPUT_DIR / "scaler_behavioral.pkl")
    joblib.dump(feature_names, OUTPUT_DIR / "feature_names.pkl")
    torch.save(
        {"model_state_dict": ae.state_dict(), "input_dim": X_licit.shape[1], "latent_dim": AE_LATENT},
        OUTPUT_DIR / "autoencoder_behavioral.pt",
    )
    logger.info("Artifacts saved to %s", OUTPUT_DIR)


if __name__ == "__main__":
    main()
