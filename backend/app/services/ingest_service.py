"""Data ingestion service for CSV uploads and Elliptic dataset loading."""
import pandas as pd
from io import BytesIO
from pathlib import Path
from app.utils.logger import get_logger
from app.repositories.transactions_repo import insert_transactions
from app.repositories.wallets_repo import upsert_wallets
from app.services.cleaning_service import clean_transactions

logger = get_logger(__name__)

REQUIRED_COLUMNS = {"transaction_id", "sender_wallet", "receiver_wallet", "amount", "timestamp"}
OPTIONAL_COLUMNS = {"tx_hash", "asset_type", "chain_id", "fee", "label", "label_source"}


def ingest_csv(file_bytes: bytes, filename: str) -> dict:
    """Parse uploaded CSV, validate, clean, deduplicate, and store."""
    df = pd.read_csv(BytesIO(file_bytes))
    
    # Validate required columns
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    
    # Clean and normalize
    df = clean_transactions(df)
    
    # Deduplicate by transaction_id
    df = df.drop_duplicates(subset=["transaction_id"], keep="first")
    
    # Sort by timestamp
    df = df.sort_values("timestamp").reset_index(drop=True)
    
    # Extract wallets
    wallets = _extract_wallets(df)
    
    # Build edge records
    edges = _build_edges(df)
    
    # Persist
    tx_records = df.to_dict("records")
    inserted_tx = insert_transactions(tx_records)
    inserted_wallets = upsert_wallets(wallets)
    
    logger.info(f"Ingested {len(inserted_tx)} transactions, {len(inserted_wallets)} wallets from {filename}")
    
    return {
        "transactions": len(inserted_tx),
        "wallets": len(inserted_wallets),
        "filename": filename,
    }


def ingest_elliptic(data_dir: str = "data/external") -> dict:
    """Load the Elliptic Bitcoin Dataset from local CSV files."""
    data_path = Path(data_dir)
    
    features_file = data_path / "elliptic_txs_features.csv"
    classes_file = data_path / "elliptic_txs_classes.csv"
    edges_file = data_path / "elliptic_txs_edgelist.csv"
    
    for f in [features_file, classes_file, edges_file]:
        if not f.exists():
            raise FileNotFoundError(f"Elliptic file not found: {f}. Download the dataset first.")
    
    # Load features (no header in original Elliptic)
    features_df = pd.read_csv(features_file, header=None)
    classes_df = pd.read_csv(classes_file)
    edges_df = pd.read_csv(edges_file)
    
    # Map Elliptic columns
    # Column 0 = txId, column 1 = time_step, columns 2-94 = local features, 95-166 = neighborhood
    node_ids = features_df.iloc[:, 0].astype(str)
    time_steps = features_df.iloc[:, 1].astype(int)
    
    # Map classes: 1=illicit, 2=licit, unknown
    classes_df.columns = ["txId", "class"]
    class_map = dict(zip(classes_df["txId"].astype(str), classes_df["class"].astype(str)))
    
    label_map = {"1": "illicit", "2": "licit"}
    
    # Build transaction records
    transactions = []
    for i, node_id in enumerate(node_ids):
        label_raw = class_map.get(node_id, "unknown")
        label = label_map.get(label_raw)
        
        transactions.append({
            "transaction_id": f"elliptic_{node_id}",
            "tx_hash": None,
            "sender_wallet": f"elliptic_sender_{node_id}",
            "receiver_wallet": f"elliptic_receiver_{node_id}",
            "amount": 0.0,
            "asset_type": "BTC",
            "chain_id": "bitcoin",
            "timestamp": f"2019-01-01T00:00:00Z",  # Elliptic doesn't have real timestamps
            "fee": None,
            "label": label,
            "label_source": "elliptic" if label else None,
        })
    
    # Build edges
    edges_df.columns = ["txId1", "txId2"]
    
    # Persist
    tx_df = pd.DataFrame(transactions)
    tx_df = clean_transactions(tx_df)
    wallets = _extract_wallets(tx_df)
    
    inserted_tx = insert_transactions(tx_df.to_dict("records"))
    inserted_wallets = upsert_wallets(wallets)
    
    logger.info(f"Ingested Elliptic dataset: {len(inserted_tx)} transactions, {len(inserted_wallets)} wallets")
    
    return {
        "transactions": len(inserted_tx),
        "wallets": len(inserted_wallets),
        "edges": len(edges_df),
        "labeled": sum(1 for t in transactions if t["label"] is not None),
        "unlabeled": sum(1 for t in transactions if t["label"] is None),
    }


def _extract_wallets(df: pd.DataFrame) -> list[dict]:
    """Extract unique wallets from transaction data."""
    senders = df.groupby("sender_wallet").agg(
        first_seen=("timestamp", "min"),
        last_seen=("timestamp", "max"),
        total_out=("amount", "sum"),
    ).reset_index().rename(columns={"sender_wallet": "wallet_address"})
    senders["total_in"] = 0.0
    
    receivers = df.groupby("receiver_wallet").agg(
        first_seen=("timestamp", "min"),
        last_seen=("timestamp", "max"),
        total_in=("amount", "sum"),
    ).reset_index().rename(columns={"receiver_wallet": "wallet_address"})
    receivers["total_out"] = 0.0
    
    wallets = pd.concat([senders, receivers]).groupby("wallet_address").agg({
        "first_seen": "min",
        "last_seen": "max",
        "total_in": "sum",
        "total_out": "sum",
    }).reset_index()
    
    return wallets.to_dict("records")


def _build_edges(df: pd.DataFrame) -> list[dict]:
    """Build edge records from transaction data."""
    return df[["sender_wallet", "receiver_wallet", "transaction_id", "amount", "timestamp"]].to_dict("records")
