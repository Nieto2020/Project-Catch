# -*- coding: utf-8 -*-
"""Estado global de la aplicación: datos cargados en RAM."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from ..core import config


@dataclass
class AppState:
    kpis: pd.DataFrame          # dataset curado (280 x 68) + columnas derivadas


def _valid_pct(series: pd.Series) -> pd.Series:
    """Porcentaje utilizable (0-100); fuera de ese rango se toma como faltante."""
    s = pd.to_numeric(series, errors="coerce")
    return s.where(s.between(0, 100))


def load_state() -> AppState:
    """Carga el dataset curado en memoria."""
    kpis = pd.read_parquet(config.DATA_PROCESSED)

    # Derivadas usadas por varios servicios.
    salary_cols = ["salario_inicial", "salario_inter_bajo", "salario_inter_alto", "salario_maximo"]
    kpis["salario_medio"] = kpis[salary_cols].mean(axis=1)
    kpis["faltas_por_100"] = kpis["total_faltas"] / kpis["total_headcount"] * 100
    kpis["cap_por_empleado"] = (
        (kpis["hrs_cap_operativos"].fillna(0) + kpis["hrs_cap_administrativos"].fillna(0))
        / kpis["total_headcount"]
    )

    # Algunas empresas capturaron la proporción de género como conteos en vez de
    # porcentajes (> 100), lo que rompía la gráfica de composición de género.
    kpis["pct_mujeres"] = _valid_pct(kpis["pct_mujeres"])
    kpis["pct_hombres"] = _valid_pct(kpis["pct_hombres"])

    return AppState(kpis=kpis)
