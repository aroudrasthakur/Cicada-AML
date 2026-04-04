"""Train Temporal Lens: 2-layer LSTM on per-wallet transaction sequences."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.metrics import average_precision_score, classification_report

from app.ml.lenses.temporal_model import TemporalLSTM, MAX_SEQ_LEN
from app.ml.ml_device import log_device_banner, resolve_torch_device
from app.utils.logger import get_logger

logger = get_logger(__name__)

OUTPUT_DIR = Path("models/temporal")
EPOCHS = 60
LR = 1e-3
BATCH_SIZE = 64
PATIENCE = 10

SEQUENCE_FEATURES = ["amount", "time_since_prev_out", "is_outgoing", "burstiness_score"]


def _load_data(data_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame | None]:
    txn_path = data_dir / "train_features.csv"
    wallet_labels_path = data_dir / "wallet_labels.csv"
    if not txn_path.exists():
        logger.error("Training data not found at %s", txn_path)
        logger.info(
            "Run the feature pipeline first:\n"
            "  python -m scripts.prepare_features --output %s",
            data_dir,
        )
        sys.exit(1)
    txn_df = pd.read_csv(txn_path)
    wallet_labels = pd.read_csv(wallet_labels_path) if wallet_labels_path.exists() else None
    return txn_df, wallet_labels


def _resolve_sender_col(df: pd.DataFrame) -> str:
    for c in ("sender_wallet", "sender", "from"):
        if c in df.columns:
            return c
    return "sender_wallet"


def _resolve_receiver_col(df: pd.DataFrame) -> str:
    for c in ("receiver_wallet", "receiver", "to"):
        if c in df.columns:
            return c
    return "receiver_wallet"


def _build_wallet_sequences(
    txn_df: pd.DataFrame,
    wallet_labels: pd.DataFrame | None,
) -> tuple[np.ndarray, np.ndarray]:
    send_col = _resolve_sender_col(txn_df)
    recv_col = _resolve_receiver_col(txn_df)

    if "timestamp" in txn_df.columns:
        txn_df["timestamp"] = pd.to_datetime(txn_df["timestamp"], utc=True, errors="coerce")
        txn_df = txn_df.sort_values("timestamp")

    if wallet_labels is not None and "wallet" in wallet_labels.columns:
        label_map = dict(zip(wallet_labels["wallet"].astype(str), wallet_labels["label"].astype(int)))
    elif "label" in txn_df.columns:
        senders = txn_df.groupby(send_col)["label"].max()
        receivers = txn_df.groupby(recv_col)["label"].max()
        label_map = pd.concat([senders, receivers]).groupby(level=0).max().to_dict()
    else:
        logger.warning("No wallet labels found; assigning label=0 to all wallets")
        all_wallets = pd.unique(pd.concat([txn_df[send_col], txn_df[recv_col]]).dropna().astype(str))
        label_map = {w: 0 for w in all_wallets}

    wallets = list(label_map.keys())
    sequences, labels = [], []

    for wallet in wallets:
        mask = (txn_df[send_col].astype(str) == wallet) | (txn_df[recv_col].astype(str) == wallet)
        w_txns = txn_df[mask].tail(MAX_SEQ_LEN)
        if len(w_txns) < 2:
            continue
        feats = []
        for _, row in w_txns.iterrows():
            f = [
                float(row.get("amount", 0)),
                float(row.get("time_since_prev_out", 0)),
                1.0 if str(row.get(send_col, "")) == wallet else 0.0,
                float(row.get("burstiness_score", 0)),
            ]
            feats.append(f)
        seq = np.array(feats, dtype=np.float32)
        if len(seq) < MAX_SEQ_LEN:
            pad = np.zeros((MAX_SEQ_LEN - len(seq), seq.shape[1]), dtype=np.float32)
            seq = np.vstack([pad, seq])
        sequences.append(seq)
        labels.append(label_map.get(wallet, 0))

    return np.array(sequences, dtype=np.float32), np.array(labels, dtype=np.int64)


def _oversample_illicit(X: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    illicit_mask = y == 1
    n_illicit = illicit_mask.sum()
    n_licit = len(y) - n_illicit
    if n_illicit == 0 or n_illicit >= n_licit:
        return X, y
    factor = max(int(n_licit / n_illicit) - 1, 1)
    X_over = np.concatenate([X, np.tile(X[illicit_mask], (factor, 1, 1))], axis=0)
    y_over = np.concatenate([y, np.tile(y[illicit_mask], factor)], axis=0)
    perm = np.random.RandomState(42).permutation(len(y_over))
    logger.info("Oversampled illicit: %d → %d (total %d)", n_illicit, illicit_mask.sum() * (factor + 1), len(y_over))
    return X_over[perm], y_over[perm]


def _train_lstm(X_train, y_train, X_val, y_val, input_dim: int, device: torch.device) -> TemporalLSTM:
    model = TemporalLSTM(input_dim=input_dim, hidden_dim=128, num_layers=2, dropout=0.2).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=LR)

    n_pos = int(y_train.sum())
    n_neg = len(y_train) - n_pos
    pos_weight = torch.FloatTensor([max(n_neg / max(n_pos, 1), 1.0)]).to(device)
    criterion = nn.BCEWithLogitsLoss(pos_weight=pos_weight)

    X_t = torch.FloatTensor(X_train).to(device)
    y_t = torch.FloatTensor(y_train).to(device)
    X_v = torch.FloatTensor(X_val).to(device)
    y_v_np = y_val

    best_ap, best_state, wait = 0.0, None, 0
    for epoch in range(1, EPOCHS + 1):
        model.train()
        perm = torch.randperm(len(X_t), device=device)
        epoch_loss = 0.0
        n_batches = 0
        for start in range(0, len(X_t), BATCH_SIZE):
            idx = perm[start : start + BATCH_SIZE]
            pred = model(X_t[idx])
            loss = criterion(pred, y_t[idx])
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            epoch_loss += loss.item()
            n_batches += 1

        if epoch % 5 == 0 or epoch == 1:
            model.eval()
            with torch.no_grad():
                val_pred = model(X_v).detach().cpu().numpy()
            val_prob = 1.0 / (1.0 + np.exp(-val_pred))
            val_ap = average_precision_score(y_v_np, val_prob) if y_v_np.sum() > 0 else 0.0
            logger.info("Epoch %d/%d  loss=%.4f  val_PR-AUC=%.4f", epoch, EPOCHS, epoch_loss / max(n_batches, 1), val_ap)
            if val_ap > best_ap:
                best_ap = val_ap
                best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
                wait = 0
            else:
                wait += 5
                if wait >= PATIENCE:
                    logger.info("Early stopping at epoch %d", epoch)
                    break

    if best_state is not None:
        model.load_state_dict(best_state)
    logger.info("Best validation PR-AUC: %.4f", best_ap)

    model.eval()
    with torch.no_grad():
        val_pred = model(X_v).detach().cpu().numpy()
    val_prob = 1.0 / (1.0 + np.exp(-val_pred))
    logger.info("\n%s", classification_report(y_v_np, (val_prob >= 0.5).astype(int), zero_division=0))
    return model


def main() -> None:
    parser = argparse.ArgumentParser(description="Train Temporal Lens LSTM")
    parser.add_argument("--data-dir", default="data/processed", help="Directory with preprocessed data")
    args = parser.parse_args()
    data_dir = Path(args.data_dir)

    logger.info("=== Training Temporal Lens ===")
    log_device_banner(logger, "train_temporal")
    device = resolve_torch_device()
    txn_df, wallet_labels = _load_data(data_dir)
    X, y = _build_wallet_sequences(txn_df, wallet_labels)
    logger.info("Built %d wallet sequences (illicit=%d)", len(y), int(y.sum()))

    split = int(0.8 * len(y))
    perm = np.random.RandomState(42).permutation(len(y))
    X, y = X[perm], y[perm]
    X_train, y_train = X[:split], y[:split]
    X_val, y_val = X[split:], y[split:]

    X_train, y_train = _oversample_illicit(X_train, y_train)
    input_dim = X_train.shape[2]
    logger.info("Input dim=%d, train=%d, val=%d", input_dim, len(y_train), len(y_val))

    model = _train_lstm(X_train, y_train, X_val, y_val, input_dim, device)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    torch.save(
        {"model_state_dict": model.state_dict(), "input_dim": input_dim},
        OUTPUT_DIR / "lstm_model.pt",
    )
    logger.info("Artifacts saved to %s", OUTPUT_DIR)


if __name__ == "__main__":
    main()
