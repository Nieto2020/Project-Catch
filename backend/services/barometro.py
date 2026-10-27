# -*- coding: utf-8 -*-
"""Barómetro de Competitividad: índice normalizado 0-100 por empresa."""
from __future__ import annotations

import pandas as pd

from .utils import jsonable

WEIGHTS = {
    "sub_salario": 0.30,
    "sub_retencion": 0.30,
    "sub_ausentismo": 0.15,
    "sub_capacitacion": 0.15,
    "sub_equilibrio": 0.10,
}

# Segmentos de tamaño (talla). El barómetro compara empresas SOLO contra
# otras de su misma talla, para no mezclar microempresas con plantas grandes.
TALLA_BANDS = [
    ("Micro", 0, 50),
    ("Pequeña", 50, 250),
    ("Mediana", 250, 1000),
    ("Grande", 1000, float("inf")),
]

# Metas de referencia (benchmarks simulados para el pitch). Cada dimensión se
# convierte a 0-100 comparando la métrica de la cohorte contra su meta.
GLOBAL_BENCHMARKS = {
    "salario":       {"peso": 0.30, "meta": 500.0, "unidad": "MXN/día",  "mejor": "alto"},
    "retencion":     {"peso": 0.30, "meta": 15.0,  "unidad": "% bimestral", "mejor": "bajo"},
    "ausentismo":    {"peso": 0.15, "meta": 150.0, "unidad": "faltas/100", "mejor": "bajo"},
    "capacitacion":  {"peso": 0.15, "meta": 4.0,   "unidad": "horas/empleado", "mejor": "alto"},
    "equilibrio":    {"peso": 0.10, "meta": 50.0,  "unidad": "% mujeres", "mejor": "centro"},
}


def _score_vs_meta(valor: float, meta: float, mejor: str) -> float:
    """Convierte una métrica de cohorte a un score 0-100 frente a su meta."""
    if pd.isna(valor):
        return 50.0
    if mejor == "bajo":
        return float(100 - min(100.0, valor / meta * 100))
    if mejor == "centro":
        return float(max(0.0, 100 - abs(valor - meta) * 2))
    return float(min(100.0, valor / meta * 100))


def global_index(df: pd.DataFrame) -> dict:
    """Índice global 0-100 de la cohorte a partir de las métricas establecidas."""
    salario = pd.to_numeric(df["salario_medio"], errors="coerce").median()
    retencion = pd.to_numeric(df["tasa_bajas_bimestral_pct"], errors="coerce").mean()
    ausentismo = pd.to_numeric(df["faltas_por_100"], errors="coerce").median()
    capacitacion = pd.to_numeric(df["cap_por_empleado"], errors="coerce").median()
    equilibrio = pd.to_numeric(df["pct_mujeres"], errors="coerce").median()

    valores = {
        "salario": salario,
        "retencion": retencion,
        "ausentismo": ausentismo,
        "capacitacion": capacitacion,
        "equilibrio": equilibrio,
    }

    dimensiones = []
    score = 0.0
    for key, cfg in GLOBAL_BENCHMARKS.items():
        s = _score_vs_meta(valores[key], cfg["meta"], cfg["mejor"])
        score += s * cfg["peso"]
        dimensiones.append({
            "clave": key,
            "peso": cfg["peso"],
            "meta": cfg["meta"],
            "unidad": cfg["unidad"],
            "valor_actual": _f(valores[key], 2),
            "score": round(s, 1),
        })

    return {
        "score": round(score, 1),
        "dimensiones": dimensiones,
    }



def talla_of(headcount) -> str:
    """Devuelve la talla (segmento de tamaño) para un headcount dado."""
    h = pd.to_numeric(pd.Series([headcount]), errors="coerce").iloc[0]
    if pd.isna(h):
        return "Mediana"
    for label, lo, hi in TALLA_BANDS:
        if lo <= h < hi:
            return label
    return "Grande"


def add_scores(df: pd.DataFrame) -> pd.DataFrame:
    """Añade `talla`, `score_competitividad` y sub-indicadores al DataFrame.

    Los sub-indicadores se calculan por percentil DENTRO de cada talla
    (comparación entre pares de tamaño similar).
    """
    out = df.copy()

    # Valores neutrales (mediana / 50%) para no perder el score ante nulos.
    for col in ["salario_medio", "tasa_bajas_bimestral_pct", "faltas_por_100", "cap_por_empleado"]:
        out[col] = pd.to_numeric(out[col], errors="coerce")
        out[col] = out[col].fillna(out[col].median())
    out["pct_mujeres"] = pd.to_numeric(out["pct_mujeres"], errors="coerce").fillna(50.0)

    out["talla"] = out["total_headcount"].apply(talla_of)

    # Percentil (0-100) dentro de la misma talla; las "peores" se invierten.
    out["sub_salario"] = out.groupby("talla")["salario_medio"].rank(pct=True) * 100
    out["sub_retencion"] = 100 - out.groupby("talla")["tasa_bajas_bimestral_pct"].rank(pct=True) * 100
    out["sub_ausentismo"] = 100 - out.groupby("talla")["faltas_por_100"].rank(pct=True) * 100
    out["sub_capacitacion"] = out.groupby("talla")["cap_por_empleado"].rank(pct=True) * 100
    # Equilibrio de género: más cerca de 50/50 = mejor (no es relativo a pares).
    out["sub_equilibrio"] = (100 - (out["pct_mujeres"] - 50).abs() * 2).clip(lower=0, upper=100)

    out["score_competitividad"] = sum(
        out[col] * w for col, w in WEIGHTS.items()
    ).round(1)
    return out


def _f(value, digits: int = 1) -> float | None:
    """float seguro: None ante nulos."""
    if value is None or pd.isna(value):
        return None
    return round(float(value), digits)


def summary(df: pd.DataFrame) -> dict:
    """Resumen del barómetro: distribución, tendencia y top empresas."""
    scored = add_scores(df)
    score = scored["score_competitividad"]

    trend = []
    for (periodo, num), g in scored.groupby(["periodo", "periodo_num"], sort=True):
        trend.append({
            "periodo": periodo,
            "periodo_num": int(num),
            "score_promedio": round(float(g["score_competitividad"].mean()), 1),
        })
    trend.sort(key=lambda r: r["periodo_num"])

    top = (
        scored[["periodo", "empresa", "talla", "score_competitividad", "salario_medio",
                "tasa_bajas_bimestral_pct", "total_headcount"]]
        .sort_values("score_competitividad", ascending=False)
        .head(5)
    )
    top_list = [
        {
            "periodo": r["periodo"],
            "empresa": r["empresa"],
            "talla": r["talla"],
            "score": _f(r["score_competitividad"], 1),
            "salario_medio": _f(r["salario_medio"], 2),
            "rotacion_bimestral_pct": _f(r["tasa_bajas_bimestral_pct"], 2),
            "headcount": _f(r["total_headcount"], 0),
        }
        for _, r in top.iterrows()
    ]

    return jsonable({
        "global": global_index(df),
        "distribucion": {
            "min": _f(score.min(), 1),
            "promedio": _f(score.mean(), 1),
            "mediana": _f(score.median(), 1),
            "max": _f(score.max(), 1),
        },
        "tendencia": trend,
        "top5": top_list,
        "dimensiones": {
            "salario": 0.30,
            "retencion": 0.30,
            "ausentismo": 0.15,
            "capacitacion": 0.15,
            "equilibrio_genero": 0.10,
        },
    })


def company_scores(df: pd.DataFrame, periodo: str | None = None) -> list[dict]:
    """Lista de empresas con su score (opcionalmente filtrada por periodo)."""
    scored = add_scores(df)
    if periodo:
        scored = scored[scored["periodo"] == periodo]

    cols = [
        "periodo", "empresa", "talla", "score_competitividad",
        "sub_salario", "sub_retencion", "sub_ausentismo",
        "sub_capacitacion", "sub_equilibrio",
        "salario_medio", "tasa_bajas_bimestral_pct", "total_headcount",
        # Condiciones descriptivas (no ponderan el índice).
        "dias_descanso_adicionales", "vacaciones_1er_anio", "aguinaldo_dias",
        "prima_vacacional_pct",
    ]
    out = []
    for _, r in scored[cols].sort_values(
        ["talla", "score_competitividad"], ascending=[True, False]
    ).iterrows():
        out.append({
            "periodo": r["periodo"],
            "empresa": r["empresa"],
            "talla": r["talla"],
            "score_competitividad": _f(r["score_competitividad"], 1),
            "sub_salario": _f(r["sub_salario"], 1),
            "sub_retencion": _f(r["sub_retencion"], 1),
            "sub_ausentismo": _f(r["sub_ausentismo"], 1),
            "sub_capacitacion": _f(r["sub_capacitacion"], 1),
            "sub_equilibrio": _f(r["sub_equilibrio"], 1),
            "salario_medio": _f(r["salario_medio"], 2),
            "rotacion_bimestral_pct": _f(r["tasa_bajas_bimestral_pct"], 2),
            "headcount": _f(r["total_headcount"], 0),
            "dias_descanso_adicionales": _f(r["dias_descanso_adicionales"], 0),
            "vacaciones_dias": _f(r["vacaciones_1er_anio"], 0),
            "aguinaldo_dias": _f(r["aguinaldo_dias"], 0),
            "prima_vacacional_pct": _f(r["prima_vacacional_pct"], 1),
        })
    return out
