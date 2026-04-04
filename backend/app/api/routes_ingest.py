"""Data ingestion endpoints."""
from fastapi import APIRouter, UploadFile, File, HTTPException
from app.services.ingest_service import ingest_csv, ingest_elliptic

router = APIRouter()


@router.post("/csv")
async def upload_csv(file: UploadFile = File(...)):
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(400, "File must be a CSV")
    contents = await file.read()
    try:
        result = ingest_csv(contents, file.filename)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Ingestion failed: {e}")
    return result


@router.post("/elliptic")
async def load_elliptic(data_dir: str = "data/external"):
    try:
        result = ingest_elliptic(data_dir)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"Elliptic load failed: {e}")
    return result
