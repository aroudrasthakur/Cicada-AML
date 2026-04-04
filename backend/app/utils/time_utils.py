from datetime import datetime, timezone
from typing import Optional
import pandas as pd


def parse_timestamp(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return pd.to_datetime(value, utc=True).to_pydatetime()


def time_window_filter(
    df: pd.DataFrame,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    col: str = "timestamp",
) -> pd.DataFrame:
    if start is not None:
        df = df[df[col] >= start]
    if end is not None:
        df = df[df[col] <= end]
    return df


def seconds_between(a: datetime, b: datetime) -> float:
    return abs((b - a).total_seconds())
