"""Threshold policy management endpoints."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.supabase_client import get_supabase

router = APIRouter()


class ThresholdUpdate(BaseModel):
    alert_threshold: float
    case_threshold: float


@router.get("/thresholds")
async def list_thresholds():
    client = get_supabase()
    try:
        result = client.table("threshold_policies").select("*").execute()
        return {"policies": result.data}
    except Exception:
        return {"policies": []}


@router.put("/thresholds/{cohort_key}")
async def update_threshold(cohort_key: str, body: ThresholdUpdate):
    client = get_supabase()
    try:
        result = client.table("threshold_policies").upsert({
            "cohort_key": cohort_key,
            "alert_threshold": body.alert_threshold,
            "case_threshold": body.case_threshold,
        }).execute()
        return result.data[0] if result.data else {}
    except Exception as e:
        raise HTTPException(500, str(e))
