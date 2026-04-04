"""Repository for pipeline_runs and all run-scoped tables."""
from __future__ import annotations

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
