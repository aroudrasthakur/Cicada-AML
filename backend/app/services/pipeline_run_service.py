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
from app.services.graph_service import build_wallet_graph, compute_node_features
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


def _update(run_id: str, pct: int, **kw: Any) -> None:
    runs_repo.update_run_status(run_id, "running", progress_pct=pct, **kw)


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
        runs_repo.update_run_status(run_id, "running", progress_pct=5)

        # ---- 1. Merge & clean ------------------------------------------------
        merged = pd.concat(frames, ignore_index=True)
        merged = clean_transactions(merged)
        merged = merged.drop_duplicates(subset=["transaction_id"], keep="first")
        merged = merged.sort_values("timestamp").reset_index(drop=True)
        total_txns = len(merged)
        runs_repo.update_run(run_id, total_txns=total_txns, progress_pct=10)
        logger.info("Run %s: merged %d transactions", run_id, total_txns)

        # ---- 2. Persist run_transactions -------------------------------------
        tx_records = _df_to_tx_records(merged)
        await loop.run_in_executor(None, runs_repo.insert_run_transactions, run_id, tx_records)
        _update(run_id, 15)

        # ---- 3. Build wallet graph -------------------------------------------
        transactions_dicts = merged.to_dict("records")
        graph: nx.DiGraph = await loop.run_in_executor(None, build_wallet_graph, transactions_dicts)
        _update(run_id, 20)

        # ---- 4. Score transactions (CPU-heavy) -------------------------------
        pipeline = get_pipeline()
        results: list[dict] = await loop.run_in_executor(
            None, pipeline.score_transactions, transactions_dicts, graph,
        )
        _update(run_id, 70)

        # ---- 5. Persist run_scores -------------------------------------------
        score_records = _build_score_records(results)
        await loop.run_in_executor(None, runs_repo.insert_run_scores, run_id, score_records)
        _update(run_id, 75)

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
            "Run %s: %d/%d transactions flagged suspicious (threshold=%.6f)",
            run_id, len(suspicious), len(results), threshold,
        )
        _update(run_id, 80)

        # ---- 7. Detect clusters among suspicious wallets ---------------------
        sus_wallets: set[str] = set()
        for s in suspicious:
            tx_row = _find_tx(transactions_dicts, s["transaction_id"])
            if tx_row:
                sus_wallets.add(str(tx_row.get("sender_wallet", "")))
                sus_wallets.add(str(tx_row.get("receiver_wallet", "")))
        sus_wallets.discard("")

        cluster_groups = _detect_clusters(graph, sus_wallets, min_size=2)
        _update(run_id, 85)

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
        _update(run_id, 90)

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
        _update(run_id, 92)

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
        _update(run_id, 95)

        # ---- 11. Mark completed ----------------------------------------------
        runs_repo.update_run_status(
            run_id,
            "completed",
            progress_pct=100,
            suspicious_tx_count=len(suspicious),
            suspicious_cluster_count=len(cluster_records),
        )
        logger.info("Run %s completed: %d suspicious, %d clusters", run_id, len(suspicious), len(cluster_records))

    except Exception as exc:
        tb = traceback.format_exc()
        logger.error("Run %s failed: %s\n%s", run_id, exc, tb)
        runs_repo.update_run_status(run_id, "failed", error_message=str(exc)[:2000])


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
