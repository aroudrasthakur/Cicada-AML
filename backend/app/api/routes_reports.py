"""Report generation endpoints."""
from fastapi import APIRouter, HTTPException
from app.repositories.reports_repo import get_reports, get_report
from app.services.report_service import generate_case_report

router = APIRouter()


@router.get("")
async def list_reports():
    return get_reports()


@router.post("/generate/{case_id}")
async def generate_report(case_id: str):
    try:
        report = generate_case_report(case_id)
        if not report:
            raise HTTPException(500, "Report generation failed")
        return report
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/{report_id}")
async def get_report_detail(report_id: str):
    report = get_report(report_id)
    if not report:
        raise HTTPException(404, "Report not found")
    return report


@router.get("/{report_id}/download")
async def download_report(report_id: str):
    report = get_report(report_id)
    if not report or not report.get("report_path"):
        raise HTTPException(404, "Report not found")
    from fastapi.responses import FileResponse
    return FileResponse(report["report_path"], filename=f"report_{report_id}.json")
