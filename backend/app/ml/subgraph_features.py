"""Subgraph and temporal-pattern features per wallet over a rolling time window."""
from __future__ import annotations

from collections import defaultdict

import networkx as nx
import numpy as np
import pandas as pd

from app.services.graph_service import build_wallet_graph
from app.utils.graph_utils import detect_cycles
from app.utils.logger import get_logger

logger = get_logger(__name__)

_SYNC_WINDOW_SEC = 60.0


def _shannon_entropy(amounts: np.ndarray) -> float:
    v = np.asarray(amounts, dtype=float)
    v = v[np.isfinite(v) & (v > 0)]
    if v.size == 0:
        return 0.0
    p = v / v.sum()
    p = p[p > 0]
    return float(-np.sum(p * np.log(p + 1e-12)))


def _normalized_entropy(amounts: np.ndarray) -> float:
    v = np.asarray(amounts, dtype=float)
    v = v[np.isfinite(v) & (v > 0)]
    n = v.size
    if n <= 1:
        return 0.0
    h = _shannon_entropy(v)
    return float(h / (np.log(n) + 1e-12))


def _longest_temporal_chain_from(
    df: pd.DataFrame,
    wallet: str,
    send_col: str,
    recv_col: str,
) -> int:
    txs = df.sort_values("timestamp", na_position="last")
    best: dict[str, int] = {}
    for _, row in txs.iterrows():
        s = str(row[send_col])
        r = str(row[recv_col])
        best.setdefault(s, -1)
        best.setdefault(r, -1)
    if wallet not in best:
        return 0
    best[wallet] = 0
    for _, row in txs.iterrows():
        s = str(row[send_col])
        r = str(row[recv_col])
        if best.get(s, -1) < 0:
            continue
        cand = best[s] + 1
        if cand > best.get(r, -1):
            best[r] = cand
    reachable = [v for v in best.values() if v >= 0]
    return int(max(reachable)) if reachable else 0


def _peel_chain_score(amounts_time_sorted: list[float]) -> int:
    if len(amounts_time_sorted) < 2:
        return 0
    best = 1
    run = 1
    for i in range(1, len(amounts_time_sorted)):
        if amounts_time_sorted[i] < amounts_time_sorted[i - 1]:
            run += 1
            best = max(best, run)
        else:
            run = 1
    return max(0, best - 1)


def _reconvergence_ratio(G: nx.DiGraph, w: str) -> float:
    succs = list(G.successors(w))
    if len(succs) < 2:
        return 0.0
    shared = 0
    for i, a in enumerate(succs):
        down_a = set(G.successors(a))
        for b in succs[i + 1 :]:
            down_b = set(G.successors(b))
            if down_a & down_b:
                shared += 1
    pairs = len(succs) * (len(succs) - 1) / 2.0
    return float(shared / pairs) if pairs > 0 else 0.0


def _sync_score_for_wallet(
    df: pd.DataFrame,
    wallet: str,
    send_col: str,
    recv_col: str,
) -> int:
    """Count of this wallet's outgoing txs with another tx to same receiver within 60s."""
    mine = df[df[send_col] == wallet]
    if mine.empty:
        return 0
    total = 0
    for _, row in mine.iterrows():
        recv = row[recv_col]
        t = row["timestamp"]
        if pd.isna(t):
            continue
        peers = df[(df[recv_col] == recv) & df["timestamp"].notna()]
        delta = (peers["timestamp"] - t).abs()
        if (delta <= pd.Timedelta(seconds=_SYNC_WINDOW_SEC)).sum() >= 2:
            total += 1
    return int(total)


def compute_subgraph_features(
    G: nx.DiGraph,
    transactions_df: pd.DataFrame,
    time_window_hours: int = 24,
) -> pd.DataFrame:
    """Per-wallet metrics over the last ``time_window_hours`` (from max timestamp)."""
    if transactions_df is None or transactions_df.empty:
        logger.info("compute_subgraph_features: empty transactions DataFrame")
        return pd.DataFrame()

    logger.debug(
        "compute_subgraph_features: reference graph nodes=%d edges=%d",
        G.number_of_nodes(),
        G.number_of_edges(),
    )

    df = transactions_df.copy()
    if "timestamp" not in df.columns:
        logger.warning("compute_subgraph_features: no timestamp column")
        return pd.DataFrame()

    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df = df.dropna(subset=["timestamp"])
    if df.empty:
        return pd.DataFrame()

    send_col = "sender_wallet" if "sender_wallet" in df.columns else None
    recv_col = "receiver_wallet" if "receiver_wallet" in df.columns else None
    if send_col is None:
        send_col = "sender" if "sender" in df.columns else "from"
    if recv_col is None:
        recv_col = "receiver" if "receiver" in df.columns else "to"
    if send_col not in df.columns or recv_col not in df.columns:
        logger.warning("compute_subgraph_features: missing sender/receiver columns")
        return pd.DataFrame()

    for c in (send_col, recv_col):
        df[c] = df[c].astype(str)

    if "amount" not in df.columns:
        df["amount"] = 0.0
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)

    t_max = df["timestamp"].max()
    hours = max(1, int(time_window_hours))
    t0 = t_max - pd.Timedelta(hours=hours)
    win = df[(df["timestamp"] >= t0) & (df["timestamp"] <= t_max)].copy()
    if win.empty:
        return pd.DataFrame()

    wallets = pd.unique(
        pd.concat([win[send_col], win[recv_col]], ignore_index=True).dropna().astype(str),
    )
    G_win = build_wallet_graph(win.to_dict("records"))

    cycles = detect_cycles(G_win, max_length=10)
    cycle_hits: defaultdict[str, int] = defaultdict(int)
    for cyc in cycles:
        for n in cyc:
            cycle_hits[str(n)] += 1

    rows = []
    for w in wallets:
        sub = G_win.subgraph({w} | set(G_win.successors(w)) | set(G_win.predecessors(w))).copy()
        out_amt = [float(sub[w][v].get("amount", 0) or 0) for v in sub.successors(w)]

        hop_count = _longest_temporal_chain_from(win, w, send_col, recv_col)

        frag = _normalized_entropy(np.array(out_amt, dtype=float)) if out_amt else 0.0
        recon = _reconvergence_ratio(G_win, w) if w in G_win else 0.0

        w_out = win[win[send_col] == w].sort_values("timestamp")
        peel = _peel_chain_score(w_out["amount"].astype(float).tolist())

        circ = int(cycle_hits.get(w, 0))

        w_tx = win[(win[send_col] == w) | (win[recv_col] == w)]
        tspan = (w_tx["timestamp"].max() - w_tx["timestamp"].min()).total_seconds()
        vol = float(
            win.loc[win[send_col] == w, "amount"].sum()
            + win.loc[win[recv_col] == w, "amount"].sum(),
        )
        velocity = float(vol / (tspan + 1.0)) if tspan >= 0 else float(vol)

        fund_ent = _shannon_entropy(np.array(out_amt, dtype=float)) if out_amt else 0.0

        sync_w = _sync_score_for_wallet(win, w, send_col, recv_col)

        rows.append(
            {
                "wallet": w,
                "hop_count_in_window": hop_count,
                "fragmentation_score": frag,
                "reconvergence_score": recon,
                "peel_chain_score": peel,
                "circularity_score": circ,
                "velocity_score": velocity,
                "synchronized_transfer_score": sync_w,
                "fund_splitting_entropy": fund_ent,
            },
        )

    result = pd.DataFrame(rows).set_index("wallet")
    return result.replace([np.inf, -np.inf], 0.0).fillna(0.0)
