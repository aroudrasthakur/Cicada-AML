"""Data cleaning and normalization service."""
import pandas as pd
import numpy as np
from app.utils.logger import get_logger

logger = get_logger(__name__)


def clean_transactions(df: pd.DataFrame) -> pd.DataFrame:
    """Clean and normalize transaction data."""
    df = df.copy()
    
    # Type coercion
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    
    if "fee" in df.columns:
        df["fee"] = pd.to_numeric(df["fee"], errors="coerce")
    
    # Drop rows with invalid required fields
    before = len(df)
    df = df.dropna(subset=["sender_wallet", "receiver_wallet", "amount", "timestamp"])
    dropped = before - len(df)
    if dropped > 0:
        logger.warning(f"Dropped {dropped} rows with missing required fields")
    
    # Ensure string types
    for col in ["transaction_id", "sender_wallet", "receiver_wallet"]:
        df[col] = df[col].astype(str)
    
    # Optional columns: fill missing
    for col in ["tx_hash", "asset_type", "chain_id", "label", "label_source"]:
        if col not in df.columns:
            df[col] = None
    
    # Cap outlier amounts at 99.9th percentile
    if len(df) > 100:
        cap = df["amount"].quantile(0.999)
        outliers = (df["amount"] > cap).sum()
        if outliers > 0:
            logger.info(f"Capping {outliers} outlier amounts at {cap:.4f}")
            df.loc[df["amount"] > cap, "amount"] = cap
    
    return df
