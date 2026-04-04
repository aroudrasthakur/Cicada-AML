"""Model metrics and monitoring endpoints."""
from fastapi import APIRouter
from app.supabase_client import get_supabase

router = APIRouter()


@router.get("/typology")
async def typology_metrics():
    """Per-typology precision/recall metrics."""
    client = get_supabase()
    try:
        result = client.table("model_metrics").select("*").eq("metric_name", "typology_recall").execute()
        return {"metrics": result.data}
    except Exception:
        return {"metrics": []}


@router.get("/cohort")
async def cohort_metrics():
    """Per-cohort model performance."""
    client = get_supabase()
    try:
        result = client.table("model_metrics").select("*").execute()
        return {"metrics": result.data}
    except Exception:
        return {"metrics": []}


@router.get("/drift")
async def drift_metrics():
    """Feature and label drift monitoring."""
    client = get_supabase()
    try:
        result = client.table("model_metrics").select("*").like("metric_name", "drift_%").execute()
        return {"metrics": result.data}
    except Exception:
        return {"metrics": []}
