"""Repository for pipeline_runs and all run-scoped tables."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from app.supabase_client import get_supabase
from app.utils.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# pipeline_runs
# ---------------------------------------------------------------------------

def create_run(label: str | None, total_files: int, user_id: str) -> dict:
    sb = get_supabase()
    row = {
        "label": label,
        "total_files": total_files,
        "status": "pending",
        "user_id": user_id,
    }
    resp = sb.table("pipeline_runs").insert(row).execute()
    return (resp.data or [{}])[0]


def update_run(run_id: str, **fields: Any) -> dict:
    sb = get_supabase()
    resp = sb.table("pipeline_runs").update(fields).eq("id", run_id).execute()
    return (resp.data or [{}])[0]


def append_progress_log(run_id: str, message: str) -> None:
    """Append a timestamped step to progress_log (capped in-app)."""
    sb = get_supabase()
    resp = sb.table("pipeline_runs").select("progress_log").eq("id", run_id).maybe_single().execute()
    raw = (resp.data or {}).get("progress_log") if resp and resp.data else None
    log: list = raw if isinstance(raw, list) else []
    log.append({"t": datetime.now(timezone.utc).isoformat(), "msg": message})
    log = log[-40:]
    sb.table("pipeline_runs").update({"progress_log": log}).eq("id", run_id).execute()


def update_run_status(
    run_id: str,
    status: str,
    *,
    progress_pct: int | None = None,
    error_message: str | None = None,
    **extra: Any,
) -> dict:
    fields: dict[str, Any] = {"status": status}
    if progress_pct is not None:
        fields["progress_pct"] = progress_pct
    if error_message is not None:
        fields["error_message"] = error_message
    if status == "running" and "started_at" not in extra:
        fields["started_at"] = datetime.now(timezone.utc).isoformat()
    if status in ("completed", "failed") and "completed_at" not in extra:
        fields["completed_at"] = datetime.now(timezone.utc).isoformat()
    fields.update(extra)
    return update_run(run_id, **fields)


def get_run(run_id: str, user_id: str | None = None) -> dict | None:
    sb = get_supabase()
    q = sb.table("pipeline_runs").select("*").eq("id", run_id)
    if user_id is not None:
        q = q.eq("user_id", user_id)
    resp = q.maybe_single().execute()
    return resp.data if resp else None


def list_runs(
    page: int = 1,
    limit: int = 50,
    user_id: str | None = None,
) -> tuple[list[dict], int]:
    sb = get_supabase()
    offset = (page - 1) * limit
    q = (
        sb.table("pipeline_runs")
        .select("*", count="exact")
        .order("created_at", desc=True)
    )
    if user_id is not None:
        q = q.eq("user_id", user_id)
    resp = q.range(offset, offset + limit - 1).execute()
    return list(resp.data or []), resp.count or 0


def get_cluster(cluster_id: str) -> dict | None:
    sb = get_supabase()
    resp = sb.table("run_clusters").select("*").eq("id", cluster_id).maybe_single().execute()
    return resp.data if resp else None


# ---------------------------------------------------------------------------
# run_transactions
# ---------------------------------------------------------------------------

def insert_run_transactions(run_id: str, records: list[dict]) -> int:
    if not records:
        return 0
    sb = get_supabase()
    for r in records:
        r["run_id"] = run_id
    BATCH = 500
    inserted = 0
    for i in range(0, len(records), BATCH):
        chunk = records[i : i + BATCH]
        try:
            sb.table("run_transactions").insert(chunk).execute()
            inserted += len(chunk)
        except Exception:
            logger.exception("insert_run_transactions batch %d failed", i)
    return inserted


def get_run_transactions(run_id: str) -> list[dict]:
    sb = get_supabase()
    resp = sb.table("run_transactions").select("*").eq("run_id", run_id).execute()
    return list(resp.data or [])


# ---------------------------------------------------------------------------
# run_scores
# ---------------------------------------------------------------------------

def insert_run_scores(run_id: str, records: list[dict]) -> int:
    if not records:
        return 0
    sb = get_supabase()
    for r in records:
        r["run_id"] = run_id
    BATCH = 500
    inserted = 0
    for i in range(0, len(records), BATCH):
        chunk = records[i : i + BATCH]
        try:
            sb.table("run_scores").insert(chunk).execute()
            inserted += len(chunk)
        except Exception:
            logger.exception("insert_run_scores batch %d failed", i)
    return inserted


def get_run_scores(run_id: str) -> list[dict]:
    sb = get_supabase()
    resp = sb.table("run_scores").select("*").eq("run_id", run_id).execute()
    return list(resp.data or [])


# ---------------------------------------------------------------------------
# run_suspicious_txns
# ---------------------------------------------------------------------------

def insert_suspicious_txns(run_id: str, records: list[dict]) -> int:
    if not records:
        return 0
    sb = get_supabase()
    for r in records:
        r["run_id"] = run_id
    resp = sb.table("run_suspicious_txns").insert(records).execute()
    return len(resp.data or [])


def get_suspicious_txns(run_id: str) -> list[dict]:
    sb = get_supabase()
    resp = sb.table("run_suspicious_txns").select("*").eq("run_id", run_id).execute()
    return list(resp.data or [])


def _parse_triggered_ids(raw: Any) -> list[Any]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return raw
    if isinstance(raw, str):
        s = raw.strip()
        if not s:
            return []
        try:
            return json.loads(s)
        except Exception:
            return []
    return []


def _heuristic_labels_for_ids(ids: list[int]) -> list[str]:
    """Resolve stored heuristic IDs to registry names for API consumers."""
    if not ids:
        return []
    try:
        import app.ml.heuristics.traditional  # noqa: F401
        import app.ml.heuristics.blockchain  # noqa: F401
        import app.ml.heuristics.hybrid  # noqa: F401
        import app.ml.heuristics.ai_enabled  # noqa: F401
        from app.ml.heuristics import registry as hreg
    except Exception:
        logger.exception("heuristic registry unavailable; returning numeric labels")
        return [f"Heuristic {i}" for i in ids]
    out: list[str] = []
    for i in ids:
        h = hreg.get(i)
        out.append(h.name if h else f"Heuristic {i}")
    return out


def get_enriched_suspicious_txns(run_id: str) -> list[dict]:
    """Merge ``run_suspicious_txns`` with ``run_transactions`` and ``run_scores`` by ``transaction_id``."""
    suspicious = get_suspicious_txns(run_id)
    tx_by_id: dict[str, dict] = {}
    for r in get_run_transactions(run_id):
        tid = str(r.get("transaction_id", ""))
        if tid:
            tx_by_id[tid] = r
    score_by_id: dict[str, dict] = {}
    for r in get_run_scores(run_id):
        tid = str(r.get("transaction_id", ""))
        if tid:
            score_by_id[tid] = r

    out: list[dict] = []
    for s in suspicious:
        tid = str(s.get("transaction_id", ""))
        tx = tx_by_id.get(tid) or {}
        sc = score_by_id.get(tid) or {}
        trig = _parse_triggered_ids(sc.get("heuristic_triggered"))
        trig_ints: list[int] = []
        for x in trig:
            try:
                trig_ints.append(int(x))
            except (TypeError, ValueError):
                continue
        h_count_raw = sc.get("heuristic_triggered_count")
        heuristic_triggered_count = len(trig_ints)
        if heuristic_triggered_count == 0 and h_count_raw is not None:
            try:
                heuristic_triggered_count = int(h_count_raw)
            except (TypeError, ValueError):
                heuristic_triggered_count = 0
        amt = tx.get("amount")
        fee = tx.get("fee")
        ts = tx.get("timestamp")
        ts_str = ts if isinstance(ts, str) else (str(ts) if ts is not None else "")

        row = {
            **s,
            "sender_wallet": str(tx.get("sender_wallet") or ""),
            "receiver_wallet": str(tx.get("receiver_wallet") or ""),
            "amount": float(amt) if amt is not None else 0.0,
            "timestamp": ts_str,
            "tx_hash": tx.get("tx_hash"),
            "asset_type": tx.get("asset_type"),
            "chain_id": tx.get("chain_id"),
            "fee": float(fee) if fee is not None else None,
            "label": tx.get("label"),
            "label_source": tx.get("label_source"),
            "behavioral_score": sc.get("behavioral_score"),
            "behavioral_anomaly": sc.get("behavioral_anomaly"),
            "graph_score": sc.get("graph_score"),
            "entity_score": sc.get("entity_score"),
            "temporal_score": sc.get("temporal_score"),
            "offramp_score": sc.get("offramp_score"),
            "heuristic_triggered_count": heuristic_triggered_count,
            "heuristic_triggered": trig_ints,
            "heuristic_triggered_labels": _heuristic_labels_for_ids(trig_ints),
            "heuristic_top_typology": sc.get("heuristic_top_typo"),
            "heuristic_top_confidence": sc.get("heuristic_top_conf"),
        }
        out.append(row)
    return out


# ---------------------------------------------------------------------------
# run_clusters + run_cluster_members
# ---------------------------------------------------------------------------

def insert_cluster(run_id: str, cluster: dict) -> dict:
    sb = get_supabase()
    cluster["run_id"] = run_id
    resp = sb.table("run_clusters").insert(cluster).execute()
    return (resp.data or [{}])[0]


def insert_cluster_members(cluster_id: str, wallets: list[str]) -> int:
    if not wallets:
        return 0
    sb = get_supabase()
    records = [{"cluster_id": cluster_id, "wallet_address": w} for w in wallets]
    resp = sb.table("run_cluster_members").insert(records).execute()
    return len(resp.data or [])


def get_run_clusters(run_id: str) -> list[dict]:
    sb = get_supabase()
    resp = sb.table("run_clusters").select("*").eq("run_id", run_id).execute()
    return list(resp.data or [])


def get_cluster_members(cluster_id: str) -> list[dict]:
    sb = get_supabase()
    resp = sb.table("run_cluster_members").select("*").eq("cluster_id", cluster_id).execute()
    return list(resp.data or [])


# ---------------------------------------------------------------------------
# run wallets (aggregated view)
# ---------------------------------------------------------------------------

def get_run_wallets(run_id: str) -> list[dict]:
    """Build a wallet-level view by aggregating cluster members, scores, and suspicious txns."""
    sb = get_supabase()

    members = list(
        (sb.table("run_cluster_members")
         .select("wallet_address, cluster_id")
         .eq("cluster_id.run_id", run_id)
         .execute()).data or []
    )

    clusters = {c["id"]: c for c in get_run_clusters(run_id)}
    scores = get_run_scores(run_id)
    suspicious = get_suspicious_txns(run_id)

    score_by_tx: dict[str, dict] = {}
    for s in scores:
        tid = s.get("transaction_id")
        if tid:
            score_by_tx[tid] = s

    wallet_map: dict[str, dict] = {}

    for m in members:
        addr = m.get("wallet_address", "")
        if addr not in wallet_map:
            wallet_map[addr] = {
                "wallet_address": addr,
                "risk_score": 0.0,
                "risk_level": "low",
                "suspicious_tx_count": 0,
                "cluster_count": 0,
                "clusters": set(),
                "top_heuristic": None,
            }
        w = wallet_map[addr]
        cid = m.get("cluster_id")
        if cid and cid not in w["clusters"]:
            w["clusters"].add(cid)
            w["cluster_count"] += 1
            cluster = clusters.get(cid)
            if cluster:
                cscore = cluster.get("risk_score", 0) or 0
                if cscore > w["risk_score"]:
                    w["risk_score"] = cscore
                    w["top_heuristic"] = cluster.get("typology")

    for st in suspicious:
        tid = st.get("transaction_id", "")
        sc = score_by_tx.get(tid, {})
        sender = sc.get("sender_wallet") or ""
        receiver = sc.get("receiver_wallet") or ""
        for addr in [sender, receiver]:
            if addr in wallet_map:
                wallet_map[addr]["suspicious_tx_count"] += 1
                ms = st.get("meta_score", 0) or 0
                if ms > wallet_map[addr]["risk_score"]:
                    wallet_map[addr]["risk_score"] = ms
                    wallet_map[addr]["risk_level"] = st.get("risk_level", "low")
                    wallet_map[addr]["top_heuristic"] = st.get("typology")

    result = []
    for w in wallet_map.values():
        w.pop("clusters", None)
        result.append(w)
    result.sort(key=lambda x: x.get("risk_score", 0), reverse=True)
    return result


# ---------------------------------------------------------------------------
# run_reports
# ---------------------------------------------------------------------------

def insert_run_report(run_id: str, title: str, content: dict) -> dict:
    sb = get_supabase()
    row = {"run_id": run_id, "title": title, "content": content}
    resp = sb.table("run_reports").insert(row).execute()
    return (resp.data or [{}])[0]


def get_run_report(run_id: str) -> dict | None:
    sb = get_supabase()
    resp = sb.table("run_reports").select("*").eq("run_id", run_id).maybe_single().execute()
    return resp.data if resp else None


# ---------------------------------------------------------------------------
# run_graph_snapshots
# ---------------------------------------------------------------------------

def insert_graph_snapshot(run_id: str, cluster_id: str, elements: list[dict]) -> dict:
    sb = get_supabase()
    row = {"run_id": run_id, "cluster_id": cluster_id, "elements": elements}
    resp = sb.table("run_graph_snapshots").insert(row).execute()
    return (resp.data or [{}])[0]


def get_graph_snapshot(run_id: str, cluster_id: str) -> dict | None:
    sb = get_supabase()
    resp = (
        sb.table("run_graph_snapshots")
        .select("*")
        .eq("run_id", run_id)
        .eq("cluster_id", cluster_id)
        .maybe_single()
        .execute()
    )
    return resp.data if resp else None
