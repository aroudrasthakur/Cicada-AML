"""Temporal Lens: LSTM-based temporal anomaly detection."""
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from pathlib import Path

from app.ml.ml_device import resolve_torch_device
from app.utils.logger import get_logger

logger = get_logger(__name__)

MAX_SEQ_LEN = 50


class TemporalLSTM(nn.Module):
    def __init__(self, input_dim: int, hidden_dim: int = 128, num_layers: int = 2, dropout: float = 0.2):
        super().__init__()
        self.lstm = nn.LSTM(input_dim, hidden_dim, num_layers=num_layers, dropout=dropout, batch_first=True)
        self.classifier = nn.Sequential(
            nn.Linear(hidden_dim, 64), nn.ReLU(), nn.Dropout(dropout),
            nn.Linear(64, 1),
        )

    def forward(self, x):
        _, (h_n, _) = self.lstm(x)
        out = self.classifier(h_n[-1])
        return out.squeeze(-1)


class TemporalLens:
    LENS_TAGS = ["temporal"]

    def __init__(self):
        self.model = None
        self.input_dim = None
        self._device = None

    def _build_sequence(self, df: pd.DataFrame, wallet: str) -> np.ndarray:
        """Build a (1, MAX_SEQ_LEN, 4) padded sequence for one wallet."""
        sender_col = "sender_wallet" if "sender_wallet" in df.columns else "sender"
        receiver_col = "receiver_wallet" if "receiver_wallet" in df.columns else "receiver"

        mask = np.zeros(len(df), dtype=bool)
        if sender_col in df.columns:
            mask |= (df[sender_col].values == wallet)
        if receiver_col in df.columns:
            mask |= (df[receiver_col].values == wallet)

        wallet_txs = df.loc[mask]
        if "timestamp" in wallet_txs.columns:
            wallet_txs = wallet_txs.sort_values("timestamp")
        wallet_txs = wallet_txs.tail(MAX_SEQ_LEN)

        if len(wallet_txs) == 0:
            return np.zeros((1, MAX_SEQ_LEN, 4), dtype=np.float32)

        amt = wallet_txs["amount"].fillna(0).to_numpy(dtype=np.float32) if "amount" in wallet_txs.columns else np.zeros(len(wallet_txs), dtype=np.float32)
        tspo = wallet_txs["time_since_prev_out"].fillna(0).to_numpy(dtype=np.float32) if "time_since_prev_out" in wallet_txs.columns else np.zeros(len(wallet_txs), dtype=np.float32)
        is_sender = (wallet_txs[sender_col].values == wallet).astype(np.float32) if sender_col in wallet_txs.columns else np.zeros(len(wallet_txs), dtype=np.float32)
        burst = wallet_txs["burstiness_score"].fillna(0).to_numpy(dtype=np.float32) if "burstiness_score" in wallet_txs.columns else np.zeros(len(wallet_txs), dtype=np.float32)

        seq = np.column_stack([amt, tspo, is_sender, burst])
        if len(seq) < MAX_SEQ_LEN:
            pad = np.zeros((MAX_SEQ_LEN - len(seq), 4), dtype=np.float32)
            seq = np.vstack([pad, seq])
        return seq.reshape(1, MAX_SEQ_LEN, 4)

    def predict(self, transactions_df: pd.DataFrame, wallets: list[str], heuristic_scores: np.ndarray = None) -> dict:
        """Score temporal risk for all wallets in a single batched GPU call."""
        if not wallets:
            return {"temporal_scores": {}}

        seqs = [self._build_sequence(transactions_df, w) for w in wallets]
        batch = np.concatenate(seqs, axis=0)  # (W, MAX_SEQ_LEN, 4)

        scores: dict[str, float] = {}
        if self.model is not None:
            device = self._device or resolve_torch_device()
            self.model.eval()
            with torch.no_grad():
                tensor = torch.from_numpy(batch).to(device)
                logits = self.model(tensor).cpu().numpy()  # (W,)
                probs = 1.0 / (1.0 + np.exp(-logits))
            for i, w in enumerate(wallets):
                scores[w] = float(probs[i])
        else:
            for w in wallets:
                scores[w] = 0.0

        return {"temporal_scores": scores}

    def load(self, model_path: str):
        p = Path(model_path)
        if p.exists():
            self._device = resolve_torch_device()
            state = torch.load(p, map_location=self._device, weights_only=True)
            input_dim = state.get("input_dim", 4)
            self.input_dim = input_dim
            self.model = TemporalLSTM(input_dim)
            self.model.load_state_dict(state["model_state_dict"])
            self.model.to(self._device)
            logger.info(f"Loaded temporal LSTM from {p} (device={self._device})")
