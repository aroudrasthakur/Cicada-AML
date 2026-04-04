from __future__ import annotations

from collections import Counter

from app.supabase_client import get_supabase


def upsert_heuristic_results(records: list[dict]) -> list[dict]:
    if not records:
        return []
    try:
        sb = get_supabase()
        resp = sb.table("heuristic_results").upsert(
            records, on_conflict="transaction_id"
        ).execute()
        return list(resp.data or [])
    except Exception:
        return []


def get_heuristic_result(transaction_id: str) -> dict | None:
    try:
        sb = get_supabase()
        resp = (
            sb.table("heuristic_results")
            .select("*")
            .eq("transaction_id", transaction_id)
            .maybe_single()
            .execute()
        )
        if resp is None:
            return None
        return resp.data
    except Exception:
        return None


def _fetch_heuristic_summary_rows(sb, page_size: int = 1000) -> tuple[list[dict], int]:
    offset = 0
    total: int | None = None
    all_rows: list[dict] = []
    while True:
        resp = (
            sb.table("heuristic_results")
            .select("top_typology, triggered_ids", count="exact")
            .range(offset, offset + page_size - 1)
            .execute()
        )
        if total is None:
            total = int(resp.count or 0)
        chunk = list(resp.data or [])
        all_rows.extend(chunk)
        if len(chunk) < page_size or (total is not None and len(all_rows) >= total):
            break
        offset += page_size
    resolved_total = total if total is not None else len(all_rows)
    return all_rows, resolved_total


def get_heuristic_stats() -> dict:
    try:
        sb = get_supabase()
        rows, total = _fetch_heuristic_summary_rows(sb)
        typology_counter: Counter[str] = Counter()
        triggered_counter: Counter[str] = Counter()
        for row in rows:
            top = row.get("top_typology")
            if top:
                typology_counter[str(top)] += 1
            raw_ids = row.get("triggered_ids")
            if isinstance(raw_ids, list):
                for tid in raw_ids:
                    triggered_counter[str(tid)] += 1
        most_common = typology_counter.most_common(1)
        top_typology = most_common[0][0] if most_common else None
        top_typology_count = most_common[0][1] if most_common else 0
        return {
            "total_scored": total,
            "most_common_top_typology": top_typology,
            "most_common_top_typology_count": top_typology_count,
            "triggered_ids_frequency": dict(triggered_counter),
        }
    except Exception:
        return {
            "total_scored": 0,
            "most_common_top_typology": None,
            "most_common_top_typology_count": 0,
            "triggered_ids_frequency": {},
        }
