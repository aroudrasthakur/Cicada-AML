"""LLM-powered report summary generation using OpenAI, with deterministic fallback."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from app.config import settings
from app.repositories import runs_repo
from app.supabase_client import get_supabase
from app.utils.logger import get_logger

logger = get_logger(__name__)

PROMPT_VERSION = "v3"
FALLBACK_MODEL = "deterministic-fallback"

SYSTEM_PROMPT = """Given a pipeline run report as JSON, reply with at most 100 words total.

Format: 4–6 short bullet lines. Start each line with "• " (bullet + space).

Cover only: run scale (tx count, suspicious count, clusters, threshold in plain terms), risk-band takeaway, which transaction IDs to review first, cluster typology hint.

No JSON dumps. No long sentences. Tight, scannable, plain English."""


def _get_openai_client():
    """Lazy-import openai to avoid startup failure when key is not set."""
    try:
        import openai
    except ImportError:
        raise RuntimeError("openai package is not installed. Run: pip install openai")
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")
    kwargs = {"api_key": settings.openai_api_key}
    if settings.openai_base_url:
        kwargs["base_url"] = settings.openai_base_url
    return openai.OpenAI(**kwargs)


def _truncate_content(content: dict, max_chars: int = 12000) -> str:
    """Serialize report content to JSON, truncating if too long for the prompt."""
    text = json.dumps(content, indent=2, default=str)
    if len(text) > max_chars:
        text = text[:max_chars] + "\n... [truncated]"
    return text


def _trim_to_max_words(text: str, max_words: int = 100) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text
    cut = " ".join(words[:max_words]).rstrip(".,;:")
    return cut + "…"


def _bullet_block(bullets: list[str]) -> str:
    return "\n".join(f"• {b.strip()}" for b in bullets if b.strip())


def _word_count(s: str) -> int:
    return len(s.split())


def _trim_bullets_to_max_words(bullets: list[str], max_words: int = 100) -> str:
    """Drop from the end or shorten until the block is ≤ max_words."""
    b = [x.strip() for x in bullets if x.strip()]
    while b and _word_count(_bullet_block(b)) > max_words:
        if len(b) == 1:
            b[0] = _trim_to_max_words(b[0], max_words=max(12, max_words - 2))
            break
        b.pop()
    return _bullet_block(b) if b else "• No report metrics available."


def _generate_fallback_summary(content: dict[str, Any]) -> str:
    """~100 words max, bullet lines, when LLM is unavailable."""
    summary = content.get("summary") or {}
    total_tx = int(summary.get("total_transactions", 0) or 0)
    sus = int(summary.get("suspicious_transactions", 0) or 0)
    clusters = int(summary.get("cluster_count", 0) or 0)
    thr = summary.get("threshold_used")
    thr_s = f"{float(thr):.4f}" if isinstance(thr, (int, float)) else "n/a"

    bullets: list[str] = [
        f"{total_tx} txs scored; {sus} suspicious; {clusters} clusters; threshold ≈ {thr_s}.",
    ]

    dist = content.get("score_distribution") or {}
    if dist:
        parts = [f"{k}:{v}" for k, v in dist.items() if v]
        if parts:
            bullets.append(f"Risk bands: {', '.join(parts)}—focus on non-bulk bands first.")
    else:
        bullets.append("Check the report table for risk-band counts; triage outliers.")

    top = list(content.get("top_suspicious_transactions") or [])
    top.sort(
        key=lambda t: float(t.get("meta_score") if t.get("meta_score") is not None else 0.0),
        reverse=True,
    )
    if top:
        ids = [str(t.get("transaction_id") or "?") for t in top[:4]]
        try:
            ms0 = float(top[0].get("meta_score") if top[0].get("meta_score") is not None else 0.0)
        except (TypeError, ValueError):
            ms0 = 0.0
        rl = str(top[0].get("risk_level") or "—")
        bullets.append(f"Review first (by score): {', '.join(ids)} (top ≈ {ms0:.4f}, {rl}).")
    else:
        bullets.append("Sort suspicious list by meta-score to pick review order.")

    cfs = content.get("cluster_findings") or []
    themes: list[str] = []
    for c in cfs[:6]:
        t = str(c.get("typology") or "").strip()
        if t and t not in themes:
            themes.append(t)
    if themes:
        bullets.append(f"Cluster themes: {', '.join(themes[:4])}—trace wallets in Flow Explorer.")
    elif clusters:
        bullets.append("Open each cluster graph to see wallet links.")
    else:
        bullets.append("No clusters in this run; rely on per-tx scores.")

    return _trim_bullets_to_max_words(bullets, max_words=100)


def generate_run_report_summary(
    run_id: str,
    *,
    force: bool = False,
) -> dict:
    """Generate (or return cached) an LLM summary for a run report.

    Returns dict with summary_text, summary_model, summary_generated_at.
    """
    report = runs_repo.get_run_report(run_id)
    if not report:
        raise ValueError(f"No report found for run {run_id}")

    if not force and report.get("summary_text"):
        return {
            "summary_text": report["summary_text"],
            "summary_model": report.get("summary_model"),
            "summary_generated_at": report.get("summary_generated_at"),
            "cached": True,
        }

    content = report.get("content", {})
    content_str = _truncate_content(content)

    summary_text: str
    model_used: str
    prompt_version = PROMPT_VERSION

    if settings.openai_api_key and settings.openai_api_key.strip():
        try:
            client = _get_openai_client()
            response = client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"Summarize this pipeline run report:\n\n{content_str}"},
                ],
                max_tokens=220,
                temperature=0.3,
            )
            summary_text = response.choices[0].message.content or ""
            model_used = response.model or settings.openai_model
        except Exception as exc:
            logger.warning(
                "OpenAI summary failed (%s); using deterministic fallback",
                exc,
                exc_info=True,
            )
            summary_text = _generate_fallback_summary(content)
            model_used = FALLBACK_MODEL
            prompt_version = f"{PROMPT_VERSION}+fallback"
    else:
        logger.info("OPENAI_API_KEY not set; generating deterministic report summary")
        summary_text = _generate_fallback_summary(content)
        model_used = FALLBACK_MODEL
        prompt_version = f"{PROMPT_VERSION}+fallback"

    generated_at = datetime.now(timezone.utc).isoformat()

    sb = get_supabase()
    sb.table("run_reports").update({
        "summary_text": summary_text,
        "summary_model": model_used,
        "summary_generated_at": generated_at,
        "summary_prompt_version": prompt_version,
    }).eq("id", report["id"]).execute()

    logger.info(
        "Generated summary for run %s report %s (%d chars, model=%s)",
        run_id, report["id"], len(summary_text), model_used,
    )

    return {
        "summary_text": summary_text,
        "summary_model": model_used,
        "summary_generated_at": generated_at,
        "cached": False,
    }


def get_run_report_summary(run_id: str) -> dict | None:
    """Return cached summary for a run report, or None if not generated."""
    report = runs_repo.get_run_report(run_id)
    if not report or not report.get("summary_text"):
        return None
    return {
        "summary_text": report["summary_text"],
        "summary_model": report.get("summary_model"),
        "summary_generated_at": report.get("summary_generated_at"),
    }
