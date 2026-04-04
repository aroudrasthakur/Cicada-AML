"""Tests for data leakage prevention: future features and time-split integrity."""
import pytest
import numpy as np
import pandas as pd

from app.ml.transaction_features import compute_transaction_features


class TestNoFutureFeatures:
    def test_features_only_use_historical_data(self):
        """Verify that expanding-window features at row i never look at rows > i."""
        df = pd.DataFrame({
            "transaction_id": [f"tx_{i}" for i in range(20)],
            "sender_wallet": ["w_A"] * 10 + ["w_B"] * 10,
            "receiver_wallet": ["w_B"] * 10 + ["w_A"] * 10,
            "amount": list(range(10, 30)),
            "timestamp": pd.date_range("2024-01-01", periods=20, freq="h", tz="UTC"),
            "fee": [0.5] * 20,
        })
        result = compute_transaction_features(df)

        for col in ["amount_deviation", "burstiness_score"]:
            if col in result.columns:
                first_per_sender = result.groupby("sender_wallet").head(1)
                assert (first_per_sender[col] == 0.0).all(), (
                    f"First transaction per sender should have {col}=0 (no history)"
                )

    def test_time_order_preserved(self):
        """Features should preserve chronological order within senders."""
        df = pd.DataFrame({
            "transaction_id": ["tx_1", "tx_2", "tx_3"],
            "sender_wallet": ["w_A", "w_A", "w_A"],
            "receiver_wallet": ["w_B", "w_C", "w_D"],
            "amount": [100, 200, 300],
            "timestamp": pd.to_datetime([
                "2024-01-01T10:00:00Z",
                "2024-01-01T11:00:00Z",
                "2024-01-01T12:00:00Z",
            ]),
        })
        result = compute_transaction_features(df)
        assert "time_since_prev_out" in result.columns


class TestTimeSplitIntegrity:
    def test_train_val_test_no_overlap(self):
        """Simulate a time-based split and verify no temporal overlap."""
        np.random.seed(42)
        n = 1000
        timestamps = pd.date_range("2024-01-01", periods=n, freq="h", tz="UTC")
        df = pd.DataFrame({
            "transaction_id": [f"tx_{i}" for i in range(n)],
            "timestamp": timestamps,
            "label": np.random.choice([0, 1], size=n, p=[0.9, 0.1]),
        })
        df = df.sort_values("timestamp").reset_index(drop=True)

        train_end = int(n * 0.6)
        val_end = int(n * 0.8)
        train = df.iloc[:train_end]
        val = df.iloc[train_end:val_end]
        test = df.iloc[val_end:]

        assert train["timestamp"].max() <= val["timestamp"].min(), "Train leaks into val"
        assert val["timestamp"].max() <= test["timestamp"].min(), "Val leaks into test"

        train_ids = set(train["transaction_id"])
        val_ids = set(val["transaction_id"])
        test_ids = set(test["transaction_id"])
        assert train_ids.isdisjoint(val_ids), "Train/val ID overlap"
        assert val_ids.isdisjoint(test_ids), "Val/test ID overlap"
        assert train_ids.isdisjoint(test_ids), "Train/test ID overlap"
