"""Temporal Lens: LSTM-based temporal anomaly detection."""
import numpy as np
import torch
import torch.nn as nn
from pathlib import Path
from app.utils.logger import get_logger

logger = get_logger(__name__)

MAX_SEQ_LEN = 50


class TemporalLSTM(nn.Module):
    def __init__(self, input_dim: int, hidden_dim: int = 128, num_layers: int = 2, dropout: float = 0.2):
        super().__init__()
        self.lstm = nn.LSTM(input_dim, hidden_dim, num_layers=num_layers, dropout=dropout, batch_first=True)
        self.classifier = nn.Sequential(
            nn.Linear(hidden_dim, 64), nn.ReLU(), nn.Dropout(dropout),
            nn.Linear(64, 1), nn.Sigmoid(),
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

    def build_sequences(self, transactions_df, wallet: str, heuristic_scores: np.ndarray = None) -> np.ndarray:
        """Build padded sequence for a wallet."""
        import pandas as pd
        wallet_txs = transactions_df[
            (transactions_df.get("sender_wallet", transactions_df.get("sender", pd.Series())) == wallet) |
            (transactions_df.get("receiver_wallet", transactions_df.get("receiver", pd.Series())) == wallet)
        ].sort_values("timestamp").tail(MAX_SEQ_LEN)
        if len(wallet_txs) == 0:
            return np.zeros((1, MAX_SEQ_LEN, 4), dtype=np.float32)
        features = []
        for _, row in wallet_txs.iterrows():
            f = [
                float(row.get("amount", 0)),
                float(row.get("time_since_prev_out", 0)),
                1.0 if row.get("sender_wallet", row.get("sender")) == wallet else 0.0,
                float(row.get("burstiness_score", 0)),
            ]
            features.append(f)
        seq = np.array(features, dtype=np.float32)
        if len(seq) < MAX_SEQ_LEN:
            pad = np.zeros((MAX_SEQ_LEN - len(seq), seq.shape[1]), dtype=np.float32)
            seq = np.vstack([pad, seq])
        return seq.reshape(1, MAX_SEQ_LEN, -1)

    def predict(self, transactions_df, wallets: list[str], heuristic_scores: np.ndarray = None) -> dict:
        """Score temporal risk for a list of wallets."""
        scores = {}
        for wallet in wallets:
            seq = self.build_sequences(transactions_df, wallet, heuristic_scores)
            if self.model is not None:
                self.model.eval()
                with torch.no_grad():
                    tensor = torch.FloatTensor(seq)
                    score = self.model(tensor).item()
            else:
                score = 0.0
            scores[wallet] = score
        return {"temporal_scores": scores}

    def load(self, model_path: str):
        p = Path(model_path)
        if p.exists():
            state = torch.load(p, map_location="cpu", weights_only=True)
            input_dim = state.get("input_dim", 4)
            self.input_dim = input_dim
            self.model = TemporalLSTM(input_dim)
            self.model.load_state_dict(state["model_state_dict"])
            logger.info(f"Loaded temporal LSTM from {p}")
