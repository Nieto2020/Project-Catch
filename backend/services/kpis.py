# -*- coding: utf-8 -*-
"""Servicio descriptivo: KPIs, tendencias y distribuciones del dashboard."""
from __future__ import annotations

import pandas as pd

from .utils import jsonable, mean_or_none, median_or_none

SALARY_COLS = ["salario_inicial", "salario_inter_bajo", "salario_inter_alto", "salario_maximo"]


def global_kpis(df: pd.DataFrame) -> dict:
    """KPIs globales del periodo completo."""
    empresas = int(df["empresa"].nunique())
    total_headcount = df["total_headcount"].sum()

    kpis = {
        "empresas": empresas,
        "periodos": int(df["periodo"].nunique()),
        "registros": int(len(df)),
        "headcount_total": int(total_headcount),
        "headcount_promedio": median_or_none(df["total_headcount"], 0),
        "salario_medio_operativo": median_or_none(df["salario_medio"], 2),
        "salario_inicial_promedio": median_or_none(df["salario_inicial"], 2),
        "salario_maximo_promedio": median_or_none(df["salario_maximo"], 2),
        "rotacion_bimestral_promedio": mean_or_none(df["tasa_bajas_bimestral_pct"], 2),
        "faltas_por_100_promedio": median_or_none(df["faltas_por_100"], 2),
        "capacitacion_hrs_promedio": median_or_none(
            df["hrs_cap_operativos"].fillna(0) + df["hrs_cap_administrativos"].fillna(0), 0
        ),
        "mujeres_pct_promedio": median_or_none(df["pct_mujeres"], 2),
    }
    return jsonable(kpis)


def trends(df: pd.DataFrame) -> list[dict]:
    """Evolución temporal por bimestre de las métricas principales."""
    rows = []
    for (periodo, num), g in df.groupby(["periodo", "periodo_num"], sort=True):
        rows.append({
            "periodo": periodo,
            "periodo_num": int(num),
            "empresas": int(len(g)),
            "headcount_mediana": median_or_none(g["total_headcount"], 0),
            "salario_medio_mediana": median_or_none(g["salario_medio"], 2),
            "rotacion_bimestral_media": mean_or_none(g["tasa_bajas_bimestral_pct"], 2),
            "faltas_por_100_mediana": median_or_none(g["faltas_por_100"], 2),
        })
    rows.sort(key=lambda r: r["periodo_num"])
    return jsonable(rows)


def distributions(df: pd.DataFrame) -> dict:
    """Distribuciones para los gráficos del dashboard."""
    bins_headcount = [0, 100, 250, 500, 1000, 2500, 10_000_000]
    labels_headcount = ["<100", "100-249", "250-499", "500-999", "1000-2499", "2500+"]
    hc = pd.cut(df["total_headcount"], bins=bins_headcount, labels=labels_headcount, right=False)

    salario_hist = pd.cut(
        df["salario_medio"].dropna(), bins=10
    ).value_counts().sort_index()

    rotacion_hist = pd.cut(
        df["tasa_bajas_bimestral_pct"].dropna(),
        bins=[0, 2.5, 5, 7.5, 10, 15, 25, 100],
        include_lowest=True,
    ).value_counts().sort_index()

    def hist_to_list(counts: pd.Series) -> list[dict]:
        return [{"rango": str(k), "conteo": int(v)} for k, v in counts.items()]

    generaciones = {
        "baby_boomers": median_or_none(df["gen_baby_boomers"], 1),
        "gen_x": median_or_none(df["gen_x"], 1),
        "millennials": median_or_none(
            df["gen_millennial_30_37"].fillna(0) + df["gen_millennial_23_29"].fillna(0), 1
        ),
        "gen_z": median_or_none(df["gen_z"], 1),
    }

    return jsonable({
        "headcount": {
            "buckets": [{"rango": lbl, "conteo": int(v)} for lbl, v in hc.value_counts().items()],
            "min": int(df["total_headcount"].min()),
            "mediana": median_or_none(df["total_headcount"], 0),
            "max": int(df["total_headcount"].max()),
        },
        "salario_medio": {
            "histograma": hist_to_list(salario_hist),
            "min": median_or_none(df["salario_medio"], 2),
            "mediana": median_or_none(df["salario_medio"], 2),
            "max": round_or_none_max(df["salario_medio"]),
        },
        "rotacion_bimestral": {
            "histograma": hist_to_list(rotacion_hist),
            "mediana": median_or_none(df["tasa_bajas_bimestral_pct"], 2),
            "max": round_or_none_max(df["tasa_bajas_bimestral_pct"]),
        },
        "generaciones": generaciones,
    })


def round_or_none_max(series: pd.Series) -> float | None:
    s = pd.to_numeric(series, errors="coerce").dropna()
    return round(float(s.max()), 2) if not s.empty else None
