"""Supabase storage bucket operations for datasets, reports, and model artifacts."""
from pathlib import Path
from app.supabase_client import get_supabase
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


def upload_file(bucket: str, file_path: str, storage_path: str) -> str | None:
    """Upload a file to Supabase storage."""
    client = get_supabase()
    try:
        with open(file_path, "rb") as f:
            client.storage.from_(bucket).upload(storage_path, f.read())
        logger.info(f"Uploaded {file_path} to {bucket}/{storage_path}")
        return storage_path
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        return None


def download_file(bucket: str, storage_path: str, local_path: str) -> str | None:
    """Download a file from Supabase storage."""
    client = get_supabase()
    try:
        data = client.storage.from_(bucket).download(storage_path)
        Path(local_path).parent.mkdir(parents=True, exist_ok=True)
        Path(local_path).write_bytes(data)
        logger.info(f"Downloaded {bucket}/{storage_path} to {local_path}")
        return local_path
    except Exception as e:
        logger.error(f"Download failed: {e}")
        return None


def upload_raw_dataset(file_path: str, name: str) -> str | None:
    return upload_file(settings.supabase_bucket_raw, file_path, f"datasets/{name}")


def upload_report(file_path: str, name: str) -> str | None:
    return upload_file(settings.supabase_bucket_reports, file_path, f"reports/{name}")


def upload_model_artifact(file_path: str, name: str) -> str | None:
    return upload_file(settings.supabase_bucket_models, file_path, f"artifacts/{name}")
