"""Async orchestrator for a single pipeline run (background task)."""
from __future__ import annotations

import asyncio
import json
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import networkx as nx
import numpy as np
import pandas as pd

from app.repositories import runs_repo
from app.services.cleaning_service import clean_transactions
from app.services.graph_service import build_wallet_graph
from app.services.scoring_service import get_pipeline
from app.utils.graph_utils import graph_to_cytoscape, detect_cycles
from app.utils.logger import get_logger

logger = get_logger(__name__)


def _load_suspicious_threshold() -> float:
    """Read the decision threshold from the trained model artifacts.

    Tries the canonical artifact path first, then the loaded pipeline config,
    then falls back to 0.5.
    """
    from app.ml.model_paths import MODELS_DIR

    cfg_path = MODELS_DIR / "artifacts" / "threshold_config.json"
    if cfg_path.exists():
        try:
            cfg = json.loads(cfg_path.read_text())
            t = cfg.get("decision_threshold")
            if t is not None:
                logger.info("Using trained decision_threshold=%.6f from %s", t, cfg_path)
                return float(t)
        except Exception:
            pass

    pipeline = get_pipeline()
    t = pipeline.threshold_config.get("decision_threshold")
    if t is not None:
        return float(t)

    return 0.5


def _label_indicates_suspicion(tx: dict | None) -> bool:
    """True when the row label marks known-bad or review (training / demo CSVs)."""
    if not tx:
        return False
    raw = tx.get("label")
    if raw is None or (isinstance(raw, float) and np.isnan(raw)):
        return False
    s = str(raw).strip().lower()
    if s in ("illicit", "fraud", "suspicious", "malicious", "scam", "true", "1", "yes"):
        return True
    return "illicit" in s or "fraud" in s or "suspic" in s


def _collect_suspicious_transactions(
    results: list[dict],
    decision_threshold: float,
    tx_by_id: dict[str, dict],
    *,
    min_heuristic_confidence: float = 0.15,
) -> list[dict]:
    """Flag transactions for clustering and reporting.

    The infer pipeline assigns ``medium-low`` when ``low_risk_ceiling < meta < decision_threshold``.
    Older code only flagged ``medium``/``high`` or ``meta >= threshold``, which **dropped every
    medium-low row** when the trained decision threshold was high (common for recall-first meta
    training). That produced **zero** suspicious rows while many txs were still elevated.

    We therefore treat as suspicious:
    - ``meta_score >= decision_threshold``
    - any non-low risk band (``high``, ``medium``, ``medium-low``)
    - rows with illicit/suspicious labels in the source CSV
    - rows with at least one fired heuristic and non-trivial top confidence
    """
    suspicious: list[dict] = []
    for r in results:
        meta = float(r.get("meta_score") or 0)
        level = str(r.get("risk_level") or "")
        tid = str(r.get("transaction_id", ""))

        if meta >= decision_threshold:
            suspicious.append(r)
            continue
        if level in ("high", "medium", "medium-low"):
            suspicious.append(r)
            continue
        if _label_indicates_suspicion(tx_by_id.get(tid)):
            suspicious.append(r)
            continue
        trig = int(r.get("heuristic_triggered_count") or 0)
        top_c = float(r.get("heuristic_top_confidence") or 0)
        if trig > 0 and top_c >= min_heuristic_confidence:
            suspicious.append(r)

    return suspicious


def _step(run_id: str, pct: int, message: str, **kw: Any) -> None:
    """Update progress text + append a line to the visual log."""
    runs_repo.update_run(run_id, progress_pct=pct, current_step=message, **kw)
    try:
        runs_repo.append_progress_log(run_id, message)
    except Exception:
        logger.exception("append_progress_log failed for run %s", run_id)


async def execute_pipeline_run(run_id: str, frames: list[pd.DataFrame]) -> None:
    """Background coroutine that drives a single pipeline run end-to-end.

    Steps:
        1. Merge + clean uploaded DataFrames
        2. Persist run_transactions
        3. Build wallet graph
        4. Score transactions (CPU-heavy, offloaded to executor)
        5. Persist run_scores
        6. Identify suspicious transactions
        7. Detect clusters among suspicious wallets
        8. Persist clusters, cluster_members, suspicious_txns
        9. Build Cytoscape graph snapshots per cluster
       10. Generate structured report
       11. Mark run completed
    """
    loop = asyncio.get_running_loop()
    try:
        runs_repo.update_run_status(
            run_id,
            "running",
            progress_pct=5,
            current_step="Starting pipeline…",
            progress_log=[],
            scoring_tx_done=0,
            scoring_tx_total=0,
            lenses_completed=0,
        )
        runs_repo.append_progress_log(run_id, "Pipeline started")

        # ---- 1. Merge & clean ------------------------------------------------
        merged = pd.concat(frames, ignore_index=True)
        merged = clean_transactions(merged)
        merged = merged.drop_duplicates(subset=["transaction_id"], keep="first")
        merged = merged.sort_values("timestamp").reset_index(drop=True)
        total_txns = len(merged)
        runs_repo.update_run(
            run_id,
            total_txns=total_txns,
            progress_pct=10,
            current_step=f"Merged and validated {total_txns} transactions from upload",
        )
        runs_repo.append_progress_log(
            run_id, f"Merged and validated {total_txns} transactions from upload",
        )
        logger.info("Run %s: merged %d transactions", run_id, total_txns)

        # ---- 2. Persist run_transactions -------------------------------------
        tx_records = _df_to_tx_records(merged)
        await loop.run_in_executor(None, runs_repo.insert_run_transactions, run_id, tx_records)
        _step(run_id, 15, f"Saved {total_txns} rows to run storage")

        # ---- 3. Build wallet graph -------------------------------------------
        transactions_dicts = merged.to_dict("records")
        graph: nx.DiGraph = await loop.run_in_executor(None, build_wallet_graph, transactions_dicts)
        _step(
            run_id,
            20,
            f"Built wallet graph ({graph.number_of_nodes()} wallets, {graph.number_of_edges()} edges)",
        )

        # ---- 4. Score transactions (CPU-heavy) -------------------------------
        # get_pipeline() runs inside the executor so cold model load does not block the event loop.

        def _scoring_progress(info: dict) -> None:
            phase = info.get("phase")
            tx_n = int(info.get("tx_total", 0))
            try:
                if phase == "batch_features":
                    nn = int(info.get("graph_nodes", 0))
                    gm = str(info.get("global_metrics", "full"))
                    if gm == "none":
                        step_msg = (
                            f"Computing features ({tx_n} tx, {nn} wallets) — "
                            "local metrics only (fast path)"
                        )
                    elif nn > 4000 or tx_n > 2000:
                        step_msg = (
                            f"Computing features ({tx_n} tx, {nn} wallets) — "
                            "PageRank/betweenness may take a few minutes"
                        )
                    else:
                        step_msg = f"Computing features ({tx_n} tx, {nn} wallets)"
                    runs_repo.update_run(
                        run_id, progress_pct=21,
                        current_step=step_msg,
                        scoring_tx_total=tx_n, scoring_tx_done=0,
                    )
                    runs_repo.append_progress_log(run_id, step_msg)
                    return

                if phase == "heuristics":
                    runs_repo.update_run(
                        run_id, progress_pct=30,
                        current_step=f"Running {tx_n} × 185 heuristics…",
                    )
                    runs_repo.append_progress_log(
                        run_id, f"Heuristics phase ({tx_n} transactions × 185 rules)",
                    )
                    return

                if phase == "batch_lenses":
                    runs_repo.update_run(
                        run_id, progress_pct=45,
                        current_step="Batch ML inference — 5 lenses (GPU-accelerated)",
                        lenses_completed=0,
                    )
                    runs_repo.append_progress_log(
                        run_id, "Batch lens inference (behavioral, graph, temporal, offramp, entity)",
                    )
                    return

                if phase == "meta_learner":
                    runs_repo.update_run(
                        run_id, progress_pct=60,
                        current_step="Batch meta-learner scoring",
                        lenses_completed=5,
                    )
                    runs_repo.append_progress_log(run_id, "Meta-learner scoring (batched)")
                    return

                # Per-tx result assembly (rapid; only update periodically)
                if "tx_index" in info:
                    tx_i = int(info["tx_index"])
                    if tx_n <= 0:
                        return
                    pct = 60 + int(10 * (tx_i + 1) / tx_n)
                    if tx_i == tx_n - 1 or (tx_n <= 100) or (tx_i % max(1, tx_n // 10) == 0):
                        runs_repo.update_run(
                            run_id, progress_pct=pct,
                            current_step=f"Assembling results: {tx_i + 1}/{tx_n}",
                            scoring_tx_done=tx_i + 1,
                            scoring_tx_total=tx_n,
                        )
            except Exception:
                logger.exception("scoring progress update failed for run %s", run_id)

        def _run_score() -> list[dict]:
            _step(run_id, 20, "Loading ML models…")
            pipeline = get_pipeline()
            return pipeline.score_transactions(
                transactions_dicts,
                graph,
                progress_callback=_scoring_progress,
            )

        results: list[dict] = await loop.run_in_executor(None, _run_score)
        _step(
            run_id,
            70,
            "ML scoring complete — all 5 lenses applied to every transaction",
            lenses_completed=5,
            scoring_tx_done=total_txns,
            scoring_tx_total=total_txns,
        )

        # ---- 5. Persist run_scores -------------------------------------------
        score_records = _build_score_records(results)
        await loop.run_in_executor(None, runs_repo.insert_run_scores, run_id, score_records)
        _step(run_id, 75, "Persisted lens scores and meta-learner output")

        # ---- 6. Identify suspicious transactions -----------------------------
        threshold = _load_suspicious_threshold()
        suspicious = [
            r for r in results
            if (r.get("meta_score") or 0) >= threshold
            or r.get("risk_level") in ("medium", "high")
        ]
        # Demo / evaluation CSVs: optional ``label`` column marking ground-truth suspicious rows.
        _seen_ids = {str(s.get("transaction_id", "")) for s in suspicious}
        by_id = {str(r.get("transaction_id", "")): r for r in results}
        for tx in transactions_dicts:
            if str(tx.get("label", "")).strip().lower() != "suspicious":
                continue
            tid = str(tx.get("transaction_id") or tx.get("id") or "")
            if not tid or tid in _seen_ids:
                continue
            row = by_id.get(tid)
            if row:
                suspicious.append(row)
                _seen_ids.add(tid)
        logger.info(
            "Run %s: %d/%d transactions flagged suspicious (decision_threshold=%.6f)",
            run_id, len(suspicious), len(results), threshold,
        )
        _step(
            run_id,
            80,
            f"Identified {len(suspicious)} suspicious transactions for clustering",
        )

        # ---- 7. Detect clusters among suspicious wallets ---------------------
        sus_wallets: set[str] = set()
        for s in suspicious:
            tx_row = _find_tx(transactions_dicts, s["transaction_id"])
            if tx_row:
                sus_wallets.add(str(tx_row.get("sender_wallet", "")))
                sus_wallets.add(str(tx_row.get("receiver_wallet", "")))
        sus_wallets.discard("")

        cluster_groups = _detect_clusters(graph, sus_wallets, min_size=2)
        _step(run_id, 85, f"Detected {len(cluster_groups)} suspicious wallet clusters")

        # ---- 8. Persist clusters, members, suspicious_txns -------------------
        wallet_to_cluster: dict[str, str] = {}
        cluster_records: list[dict] = []
        for cg in cluster_groups:
            sub = graph.subgraph(cg["wallets"])
            total_amount = sum(d.get("amount", 0) for _, _, d in sub.edges(data=True))
            cluster_data = {
                "label": f"Cluster ({len(cg['wallets'])} wallets)",
                "typology": _classify_typology(sub),
                "risk_score": cg.get("risk_score", 0),
                "total_amount": float(total_amount),
                "wallet_count": len(cg["wallets"]),
                "tx_count": sub.number_of_edges(),
            }
            inserted = await loop.run_in_executor(None, runs_repo.insert_cluster, run_id, cluster_data)
            cid = inserted.get("id", "")
            cluster_records.append({**inserted, "_wallets": cg["wallets"]})
            await loop.run_in_executor(None, runs_repo.insert_cluster_members, cid, list(cg["wallets"]))
            for w in cg["wallets"]:
                wallet_to_cluster[w] = cid

        sus_tx_records = _build_suspicious_records(suspicious, transactions_dicts, wallet_to_cluster)
        await loop.run_in_executor(None, runs_repo.insert_suspicious_txns, run_id, sus_tx_records)
        _step(run_id, 90, "Saved suspicious transactions and cluster memberships")

        # ---- 9. Cytoscape graph snapshots per cluster ------------------------
        for cr in cluster_records:
            cid = cr["id"]
            wallets = cr["_wallets"]
            sub = graph.subgraph(wallets).copy()
            cyto = graph_to_cytoscape(sub)
            _annotate_cytoscape(cyto, results, suspicious)
            await loop.run_in_executor(
                None, runs_repo.insert_graph_snapshot, run_id, cid, cyto.get("elements", []),
            )
        _step(
            run_id,
            92,
            f"Saved {len(cluster_records)} Cytoscape graph snapshots for Flow Explorer",
        )

        # ---- 10. Generate structured report ----------------------------------
        report_content = _build_report(
            run_id,
            total_txns,
            len(suspicious),
            cluster_records,
            results,
            suspicious,
            len(frames),
            threshold,
        )
        report_title = f"Pipeline Run Report - {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}"
        await loop.run_in_executor(
            None, runs_repo.insert_run_report, run_id, report_title, report_content,
        )
        _step(run_id, 95, "Generated structured run report")

        # ---- 11. Mark completed ----------------------------------------------
        runs_repo.update_run_status(
            run_id,
            "completed",
            progress_pct=100,
            suspicious_tx_count=len(suspicious),
            suspicious_cluster_count=len(cluster_records),
            current_step="Completed",
            lenses_completed=5,
            scoring_tx_done=total_txns,
            scoring_tx_total=total_txns,
        )
        runs_repo.append_progress_log(
            run_id,
            f"Finished — {len(suspicious)} suspicious tx, {len(cluster_records)} clusters",
        )
        logger.info("Run %s completed: %d suspicious, %d clusters", run_id, len(suspicious), len(cluster_records))

    except Exception as exc:
        tb = traceback.format_exc()
        logger.error("Run %s failed: %s\n%s", run_id, exc, tb)
        runs_repo.update_run_status(
            run_id,
            "failed",
            error_message=str(exc)[:2000],
            current_step="Failed",
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _df_to_tx_records(df: pd.DataFrame) -> list[dict]:
    records = []
    for _, row in df.iterrows():
        records.append({
            "transaction_id": str(row.get("transaction_id", "")),
            "sender_wallet": str(row.get("sender_wallet", "")),
            "receiver_wallet": str(row.get("receiver_wallet", "")),
            "amount": float(row.get("amount", 0)),
            "timestamp": str(row.get("timestamp", "")),
            "tx_hash": row.get("tx_hash") if pd.notna(row.get("tx_hash")) else None,
            "asset_type": row.get("asset_type") if pd.notna(row.get("asset_type")) else None,
            "chain_id": row.get("chain_id") if pd.notna(row.get("chain_id")) else None,
            "fee": float(row["fee"]) if pd.notna(row.get("fee")) else None,
            "label": row.get("label") if pd.notna(row.get("label")) else None,
            "label_source": row.get("label_source") if pd.notna(row.get("label_source")) else None,
        })
    return records


def _build_score_records(results: list[dict]) -> list[dict]:
    out = []
    for r in results:
        out.append({
            "transaction_id": r.get("transaction_id", ""),
            "behavioral_score": r.get("behavioral_score"),
            "behavioral_anomaly": r.get("behavioral_anomaly_score"),
            "graph_score": r.get("graph_score"),
            "entity_score": r.get("entity_score"),
            "temporal_score": r.get("temporal_score"),
            "offramp_score": r.get("offramp_score"),
            "meta_score": r.get("meta_score"),
            "risk_level": r.get("risk_level"),
            "predicted_label": r.get("predicted_label"),
            "explanation_summary": r.get("explanation_summary"),
            "heuristic_triggered": json.dumps(r.get("triggered_ids", [])),
            "heuristic_top_typo": r.get("heuristic_top_typology"),
            "heuristic_top_conf": r.get("heuristic_top_confidence"),
        })
    return out


def _find_tx(txns: list[dict], tx_id: str) -> dict | None:
    for t in txns:
        if str(t.get("transaction_id", "")) == str(tx_id):
            return t
    return None


def _detect_clusters(
    graph: nx.DiGraph, high_risk_wallets: set[str], min_size: int = 2,
) -> list[dict]:
    if not high_risk_wallets:
        return []
    undirected = graph.to_undirected()
    visited: set[str] = set()
    groups: list[dict] = []
    for w in high_risk_wallets:
        if w in visited or not undirected.has_node(w):
            continue
        component = nx.node_connected_component(undirected, w)
        risky = component & high_risk_wallets
        if len(risky) < min_size:
            continue
        visited.update(component)
        groups.append({
            "wallets": risky,
            "risk_score": len(risky) / max(len(component), 1),
        })
    return groups


def _classify_typology(G: nx.DiGraph) -> str:
    if G.number_of_nodes() == 0:
        return "unknown"
    max_out = max((G.out_degree(n) for n in G.nodes()), default=0)
    max_in = max((G.in_degree(n) for n in G.nodes()), default=0)
    cycles = detect_cycles(G, max_length=6)
    if max_out > 10:
        return "fan-out dispersal"
    if max_in > 10:
        return "fan-in aggregation"
    if len(cycles) > 3:
        return "circular layering"
    avg_degree = sum(G.degree(n) for n in G.nodes()) / max(len(G.nodes()), 1)
    if avg_degree < 2.5:
        return "peel chain"
    return "layering"


def _build_suspicious_records(
    suspicious: list[dict], txns: list[dict], wallet_to_cluster: dict[str, str],
) -> list[dict]:
    out = []
    for s in suspicious:
        tx_id = s["transaction_id"]
        tx_row = _find_tx(txns, tx_id)
        cluster_id = None
        if tx_row:
            sw = str(tx_row.get("sender_wallet", ""))
            rw = str(tx_row.get("receiver_wallet", ""))
            cluster_id = wallet_to_cluster.get(sw) or wallet_to_cluster.get(rw)
        out.append({
            "transaction_id": tx_id,
            "meta_score": s.get("meta_score"),
            "risk_level": s.get("risk_level"),
            "typology": s.get("heuristic_top_typology"),
            "cluster_id": cluster_id,
        })
    return out


def _annotate_cytoscape(cyto: dict, results: list[dict], suspicious: list[dict]) -> None:
    """Add risk metadata to Cytoscape elements for frontend styling."""
    sus_ids = {s["transaction_id"] for s in suspicious}
    score_map = {r["transaction_id"]: r for r in results}
    for el in cyto.get("elements", []):
        data = el.get("data", {})
        nid = data.get("id", "")
        if nid in sus_ids:
            data["suspicious"] = True
        sc = score_map.get(nid)
        if sc:
            data["meta_score"] = sc.get("meta_score")
            data["risk_level"] = sc.get("risk_level")


def _build_report(
    run_id: str,
    total_txns: int,
    suspicious_count: int,
    cluster_records: list[dict],
    all_results: list[dict],
    suspicious: list[dict],
    file_count: int,
    suspicious_threshold: float,
) -> dict:
    top_risky = sorted(suspicious, key=lambda x: x.get("meta_score", 0), reverse=True)[:20]
    cluster_summaries = []
    for cr in cluster_records:
        cluster_summaries.append({
            "cluster_id": cr.get("id"),
            "label": cr.get("label"),
            "typology": cr.get("typology"),
            "risk_score": cr.get("risk_score"),
            "wallet_count": cr.get("wallet_count"),
            "tx_count": cr.get("tx_count"),
            "total_amount": cr.get("total_amount"),
        })

    return {
        "run_id": run_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total_files": file_count,
            "total_transactions": total_txns,
            "suspicious_transactions": suspicious_count,
            "cluster_count": len(cluster_records),
            "threshold_used": suspicious_threshold,
        },
        "top_suspicious_transactions": [
            {
                "transaction_id": t.get("transaction_id"),
                "meta_score": round(t.get("meta_score", 0), 4),
                "risk_level": t.get("risk_level"),
                "typology": t.get("heuristic_top_typology"),
                "behavioral_score": round(t.get("behavioral_score", 0), 4),
                "graph_score": round(t.get("graph_score", 0), 4),
                "entity_score": round(t.get("entity_score", 0), 4),
                "temporal_score": round(t.get("temporal_score", 0), 4),
                "offramp_score": round(t.get("offramp_score", 0), 4),
            }
            for t in top_risky
        ],
        "cluster_findings": cluster_summaries,
        "score_distribution": {
            "high": sum(1 for r in all_results if r.get("risk_level") == "high"),
            "medium": sum(1 for r in all_results if r.get("risk_level") == "medium"),
            "medium-low": sum(1 for r in all_results if r.get("risk_level") == "medium-low"),
            "low": sum(1 for r in all_results if r.get("risk_level") == "low"),
        },
    }
