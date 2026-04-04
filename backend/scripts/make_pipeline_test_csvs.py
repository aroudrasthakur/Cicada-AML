"""Build 3 small transaction CSVs (max 2000 rows each) for pipeline / upload testing.

Reads ``data/processed_subset/edges.csv`` (same schema as ingest: transaction_id,
sender_wallet, receiver_wallet, amount, timestamp). Optionally annotates ``label`` /
``label_source`` from ``node_labels.csv`` (Elliptic-style 0/1).

Run from repo root::

    python backend/scripts/make_pipeline_test_csvs.py

Or from ``backend``::

    python -m scripts.make_pipeline_test_csvs

Default output: ``data/pipeline_test/pipeline_test_batch_{1,2,3}.csv``
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from app.utils.logger import get_logger

logger = get_logger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EDGES = REPO_ROOT / "data" / "processed_subset" / "edges.csv"
DEFAULT_LABELS = REPO_ROOT / "data" / "processed_subset" / "node_labels.csv"
DEFAULT_OUT_DIR = REPO_ROOT / "data" / "pipeline_test"


def main() -> None:
    parser = argparse.ArgumentParser(description="Create pipeline test CSV batches.")
    parser.add_argument("--input", type=Path, default=DEFAULT_EDGES, help="Source edges CSV")
    parser.add_argument("--labels", type=Path, default=DEFAULT_LABELS, help="node_labels.csv (optional)")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUT_DIR, help="Directory for output files")
    parser.add_argument("--max-per-file", type=int, default=2000, help="Max rows per CSV")
    parser.add_argument("--num-files", type=int, default=3, help="Number of CSV files to write")
    parser.add_argument("--seed", type=int, default=42, help="Shuffle seed (reproducible splits)")
    args = parser.parse_args()

    if not args.input.exists():
        raise SystemExit(f"Input not found: {args.input}")

    df = pd.read_csv(args.input)
    required = {"transaction_id", "sender_wallet", "receiver_wallet", "amount", "timestamp"}
    missing = required - set(df.columns)
    if missing:
        raise SystemExit(f"Input missing columns {missing}; expected at least {required}")

    df = df.drop_duplicates(subset=["transaction_id"], keep="first").reset_index(drop=True)

    if args.labels.exists():
        lab = pd.read_csv(args.labels)
        if "node_id" in lab.columns and "label" in lab.columns:
            illicit = set(lab.loc[lab["label"] == 1, "node_id"].astype(str))
            s = df["sender_wallet"].astype(str)
            r = df["receiver_wallet"].astype(str)
            mask = s.isin(illicit) | r.isin(illicit)
            df = df.copy()
            df["label"] = "licit"
            df.loc[mask, "label"] = "illicit"
            df["label_source"] = "subset_node_labels"
            logger.info("Annotated labels: %d illicit-touch edges", int(mask.sum()))
        else:
            logger.warning("Labels file missing node_id/label columns; skipping label merge")
    else:
        logger.warning("No labels file at %s; outputs will not include label columns", args.labels)

    df = df.sample(frac=1.0, random_state=args.seed).reset_index(drop=True)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    need = args.max_per_file * args.num_files
    if len(df) < need:
        logger.warning(
            "Only %d rows available; need %d for %d x %d — files will be shorter",
            len(df),
            need,
            args.num_files,
            args.max_per_file,
        )

    for i in range(args.num_files):
        start = i * args.max_per_file
        end = start + args.max_per_file
        chunk = df.iloc[start:end]
        out_path = args.output_dir / f"pipeline_test_batch_{i + 1}.csv"
        chunk.to_csv(out_path, index=False)
        logger.info("Wrote %s (%d rows)", out_path, len(chunk))


if __name__ == "__main__":
    main()
