"""Shared helpers used by every agent: NaN cleanup, timestamp parsing, rounding, capping."""

from datetime import datetime
from typing import Any, List, Optional

import pandas as pd

TIMESTAMP_FMT = "%Y-%m-%d %H:%M:%S"


def clean(value: Any) -> Optional[str]:
    """Convert pandas NaN/NaT to None, otherwise return the value unchanged."""
    if value is None:
        return None
    if isinstance(value, (list, dict)):
        return value
    if pd.isna(value):
        return None
    return value


def parse_ts(value: Optional[str]) -> Optional[datetime]:
    value = clean(value)
    if not value:
        return None
    try:
        return datetime.strptime(str(value), TIMESTAMP_FMT)
    except ValueError:
        return None


def money(value: float) -> float:
    return round(float(value), 2)


def cap(items: List[Any], limit: int) -> List[Any]:
    return list(items[:limit])
