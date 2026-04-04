from __future__ import annotations

from app.supabase_client import get_supabase


def insert_report(data: dict) -> dict:
    try:
        sb = get_supabase()
        resp = sb.table("reports").insert(data).select().execute()
        rows = resp.data or []
        if not rows:
            return {}
        row = rows[0]
        return row if isinstance(row, dict) else {}
    except Exception:
        return {}


def get_reports() -> list[dict]:
    try:
        sb = get_supabase()
        resp = (
            sb.table("reports")
            .select("*")
            .order("generated_at", desc=True)
            .execute()
        )
        return list(resp.data or [])
    except Exception:
        return []


def get_report(report_id: str) -> dict | None:
    try:
        sb = get_supabase()
        resp = (
            sb.table("reports")
            .select("*")
            .eq("id", report_id)
            .maybe_single()
            .execute()
        )
        if resp is None:
            return None
        return resp.data
    except Exception:
        return None
