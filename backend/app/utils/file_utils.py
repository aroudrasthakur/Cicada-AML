from pathlib import Path
from typing import Optional
import pandas as pd


def read_csv_safe(path: str | Path, **kwargs) -> pd.DataFrame:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"CSV not found: {path}")
    return pd.read_csv(path, **kwargs)


def resolve_model_path(path: str, model_dir: Optional[str] = None) -> Path:
    p = Path(path)
    if p.is_absolute():
        return p
    if model_dir:
        return Path(model_dir) / p
    return p


def ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p
