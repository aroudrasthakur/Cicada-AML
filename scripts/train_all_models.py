#!/usr/bin/env python3
"""Full ML training pipeline: features -> lenses -> entity -> score -> meta.

Artifacts are written to the repository ``models/`` directory (not ``backend/models``).

Usage (from repository root):

  python scripts/train_all_models.py

Requires ``data/external`` Elliptic CSVs unless you pass ``--skip-features`` and already have
``data/processed`` populated.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
DATA_EXTERNAL = REPO_ROOT / "data" / "external"
DATA_PROCESSED = REPO_ROOT / "data" / "processed"

LENS_MODULES = [
    "app.ml.training.train_behavioral",
    "app.ml.training.train_graph",
    "app.ml.training.train_temporal",
    "app.ml.training.train_offramp",
]


def _run(cmd: list[str], *, cwd: Path) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=cwd, check=True)


def _run_module(module: str, *, data_dir: Path) -> None:
    _run(
        [sys.executable, "-m", module, "--data-dir", str(data_dir)],
        cwd=BACKEND_DIR,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Train all lens models, then entity and meta.")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DATA_PROCESSED,
        help="Directory with train_features.csv and related artifacts (default: repo data/processed)",
    )
    parser.add_argument(
        "--skip-features",
        action="store_true",
        help="Skip scripts.prepare_features (use existing data/processed)",
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DATA_EXTERNAL,
        help="Elliptic CSV directory for prepare_features (default: repo data/external)",
    )
    args = parser.parse_args()
    data_dir = args.data_dir.resolve()

    if not args.skip_features:
        _run(
            [
                sys.executable,
                "-m",
                "scripts.prepare_features",
                "--input",
                str(args.input.resolve()),
                "--output",
                str(data_dir),
            ],
            cwd=BACKEND_DIR,
        )

    with ThreadPoolExecutor(max_workers=len(LENS_MODULES)) as pool:
        futures = {pool.submit(_run_module, m, data_dir=data_dir): m for m in LENS_MODULES}
        for fut in as_completed(futures):
            fut.result()

    _run_module("app.ml.training.train_entity", data_dir=data_dir)

    # Score training data with all trained lenses -> train_features_scored.csv
    _run(
        [sys.executable, "-m", "scripts.score_training_data", "--data-dir", str(data_dir)],
        cwd=BACKEND_DIR,
    )
    # Build meta_features.csv from scored data
    _run(
        [sys.executable, "-m", "scripts.prepare_meta_features", "--data-dir", str(data_dir)],
        cwd=BACKEND_DIR,
    )
    _run_module("app.ml.training.train_meta", data_dir=data_dir)


if __name__ == "__main__":
    main()
