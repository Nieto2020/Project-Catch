# -*- coding: utf-8 -*-
"""Utilidades compartidas del backend."""
from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd


def jsonable(obj: Any) -> Any:
    """Convierte tipos numpy/pandas a nativos JSON, con NaN -> None."""
    if obj is None or obj is pd.NA:
        return None
    if isinstance(obj, (str, bool, int)):
        return obj
    if isinstance(obj, float):
        return None if (math.isnan(obj) or math.isinf(obj)) else obj
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        f = float(obj)
        return None if (math.isnan(f) or math.isinf(f)) else f
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, np.ndarray):
        return [jsonable(x) for x in obj.tolist()]
    if isinstance(obj, dict):
        return {str(k): jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [jsonable(x) for x in obj]
    if isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    if isinstance(obj, pd.Series):
        return jsonable(obj.to_dict())
    return str(obj)


def round_or_none(value: float | None, digits: int = 2) -> float | None:
    """Redondea un valor o devuelve None si es nulo/NaN."""
    if value is None:
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(f) or math.isinf(f):
        return None
    return round(f, digits)


def median_or_none(series: pd.Series, digits: int = 2) -> float | None:
    """Mediana de una serie numérica, None si está vacía."""
    s = pd.to_numeric(series, errors="coerce").dropna()
    return round_or_none(float(s.median()), digits) if not s.empty else None


def mean_or_none(series: pd.Series, digits: int = 2) -> float | None:
    """Media de una serie numérica, None si está vacía."""
    s = pd.to_numeric(series, errors="coerce").dropna()
    return round_or_none(float(s.mean()), digits) if not s.empty else None
