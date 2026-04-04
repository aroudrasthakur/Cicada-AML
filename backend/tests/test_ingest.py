"""Tests for data ingestion: cleaning, wallet extraction, CSV validation."""
import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch

from app.services.cleaning_service import clean_transactions
from app.services.ingest_service import _extract_wallets, REQUIRED_COLUMNS, ingest_csv


class TestCleanTransactions:
    def test_normalizes_types(self, sample_transactions):
        df = pd.DataFrame(sample_transactions)
        result = clean_transactions(df)

        assert result["amount"].dtype == np.float64
        assert pd.api.types.is_datetime64_any_dtype(result["timestamp"])
        assert result["sender_wallet"].dtype == object
        assert result["receiver_wallet"].dtype == object

    def test_handles_missing_optional_columns(self):
        df = pd.DataFrame({
            "transaction_id": ["tx_1"],
            "sender_wallet": ["w_A"],
            "receiver_wallet": ["w_B"],
            "amount": [100.0],
            "timestamp": ["2024-01-01T00:00:00Z"],
        })
        result = clean_transactions(df)

        for col in ["tx_hash", "asset_type", "chain_id", "label", "label_source"]:
            assert col in result.columns

    def test_drops_invalid_rows(self):
        df = pd.DataFrame({
            "transaction_id": ["tx_1", "tx_2"],
            "sender_wallet": ["w_A", None],
            "receiver_wallet": ["w_B", "w_C"],
            "amount": [100.0, "not_a_number"],
            "timestamp": ["2024-01-01T00:00:00Z", None],
        })
        result = clean_transactions(df)
        assert len(result) == 1
        assert result.iloc[0]["transaction_id"] == "tx_1"


class TestExtractWallets:
    def test_extract_wallets_from_transactions(self, sample_transactions):
        df = pd.DataFrame(sample_transactions)
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        wallets = _extract_wallets(df)

        addresses = {w["wallet_address"] for w in wallets}
        assert "wallet_A" in addresses
        assert "wallet_B" in addresses
        assert "wallet_C" in addresses
        assert len(wallets) >= 3

    def test_wallet_aggregates_are_numeric(self, sample_transactions):
        df = pd.DataFrame(sample_transactions)
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        wallets = _extract_wallets(df)

        for w in wallets:
            assert isinstance(w["total_in"], (int, float))
            assert isinstance(w["total_out"], (int, float))


class TestCsvValidation:
    @patch("app.services.ingest_service.insert_transactions", return_value=[])
    @patch("app.services.ingest_service.upsert_wallets", return_value=[])
    def test_missing_required_columns_raises(self, _mock_wallets, _mock_tx):
        incomplete_csv = b"id,sender,receiver\n1,A,B\n"
        with pytest.raises(ValueError, match="Missing required columns"):
            ingest_csv(incomplete_csv, "bad.csv")

    @patch("app.services.ingest_service.insert_transactions", return_value=[{"id": 1}])
    @patch("app.services.ingest_service.upsert_wallets", return_value=[{"id": 1}])
    def test_valid_csv_succeeds(self, _mock_wallets, _mock_tx):
        csv_bytes = (
            "transaction_id,sender_wallet,receiver_wallet,amount,timestamp\n"
            "tx_1,w_A,w_B,100.0,2024-01-01T00:00:00Z\n"
        ).encode()
        result = ingest_csv(csv_bytes, "good.csv")
        assert "transactions" in result
        assert "wallets" in result
