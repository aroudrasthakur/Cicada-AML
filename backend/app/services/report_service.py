"""Generate investigation reports."""
import json
from datetime import datetime, timezone
from pathlib import Path
from app.repositories.network_cases_repo import get_network_case
from app.repositories.reports_repo import insert_report
from app.services.explanation_service import explain_case
from app.utils.logger import get_logger
from app.utils.file_utils import ensure_dir

logger = get_logger(__name__)

REPORTS_DIR = Path("data/processed/reports")


def generate_case_report(case_id: str) -> dict | None:
    """Generate a JSON report for a network case."""
    case = get_network_case(case_id)
    if not case:
        return None
    
    explanation = explain_case(case_id) or {}
    
    report_content = {
        "case_id": case_id,
        "case_name": case.get("case_name"),
        "typology": case.get("typology"),
        "risk_score": case.get("risk_score"),
        "total_amount": case.get("total_amount"),
        "wallets": case.get("wallet_addresses", []),
        "time_range": {
            "start": str(case.get("start_time", "")),
            "end": str(case.get("end_time", "")),
        },
        "explanation": explanation,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    
    ensure_dir(REPORTS_DIR)
    report_path = REPORTS_DIR / f"report_{case_id}.json"
    report_path.write_text(json.dumps(report_content, indent=2, default=str))
    
    record = insert_report({
        "case_id": case_id,
        "title": f"Investigation Report: {case.get('case_name', case_id)}",
        "report_path": str(report_path),
    })
    
    logger.info(f"Generated report for case {case_id}")
    return record
