# -*- coding: utf-8 -*-
"""Simulador What-If: proyecta rotación ante cambios de variables."""
from __future__ import annotations

import pandas as pd

from .utils import jsonable

# Columnas que el usuario puede modificar (las del modelo, en nombres legibles).
# `tiene_sindicato` se maneja aparte por ser categórica.
SIMULABLE_NUMERIC = [
    "emp_operativos", "emp_admin", "emp_otros", "pct_mujeres",
    "gen_baby_boomers", "gen_x", "gen_millennial_30_37",
    "gen_millennial_23_29", "gen_z",
    "salario_inicial", "salario_inter_bajo", "salario_inter_alto", "salario_maximo",
    "total_faltas", "faltas_oper_justificadas", "faltas_oper_injustificadas",
    "faltas_admin_justificadas", "faltas_admin_injustificadas",
    "casos_incapacidad", "incap_riesgo_trabajo", "incap_enfermedad_general",
    "incap_maternidad", "incap_temporal", "incap_permanente_parcial",
    "incap_permanente_total",
    "hrs_cap_operativos", "hrs_cap_administrativos",
]


def _prepare_df(df: pd.DataFrame) -> pd.DataFrame:
    """Prepara el DataFrame base con las features en el orden del modelo."""
    prep = df.copy()
    prep["tiene_sindicato"] = prep["tiene_sindicato"].map({"Sí": 1, "No": 0})
    return prep


def _feature_row(df: pd.DataFrame, features: list[str], empresa: str | None, periodo: str | None) -> dict:
    """Obtiene la fila base de features: una empresa concreta o la mediana de cohorte."""
    if empresa:
        sel = df[df["empresa"] == empresa]
        if periodo:
            sel = sel[sel["periodo"] == periodo]
        if sel.empty:
            raise ValueError(f"No se encontró la empresa '{empresa}' para el periodo indicado.")
        row = sel.iloc[0]
    else:
        row = df[features].median()

    return {f: (None if pd.isna(row[f]) else float(row[f])) for f in features}


def simulate(state, payload: dict) -> dict:
    """Ejecuta una simulación What-If con el modelo de rotación."""
    features: list[str] = state.model_meta["features"]
    df = _prepare_df(state.kpis)

    empresa = payload.get("empresa")
    periodo = payload.get("periodo")
    overrides = payload.get("cambios", {}) or {}

    baseline = _feature_row(df, features, empresa, periodo)

    # Aplica overrides (con tolerancia a categóricas Sí/No).
    applied = {}
    for key, value in overrides.items():
        if key not in features:
            continue
        if key == "tiene_sindicato":
            if isinstance(value, str):
                value = 1 if value.strip().lower() in ("sí", "si", "yes", "1", "true") else 0
            value = int(value)
        else:
            try:
                value = float(value)
            except (TypeError, ValueError):
                continue
        baseline[key] = value
        applied[key] = value

    X = pd.DataFrame([baseline])[features]
    pred = float(state.model.predict(X)[0])
    pred = max(0.0, pred)

    # Baseline sin cambios (para calcular el delta).
    X_base = pd.DataFrame([_feature_row(df, features, empresa, periodo)])[features]
    base_pred = float(max(0.0, state.model.predict(X_base)[0]))

    delta = pred - base_pred

    top_drivers = state.model_meta.get("feature_importance", [])[:6]

    return jsonable({
        "escenario": "empresa" if empresa else "cohorte_promedio",
        "empresa": empresa,
        "periodo": periodo,
        "rotacion_actual_pct": round(base_pred, 2),
        "rotacion_proyectada_pct": round(pred, 2),
        "delta_pts_porcentuales": round(delta, 2),
        "cambios_aplicados": applied,
        "drivers_principales": top_drivers,
        "interpretacion": _interpret(delta, pred),
    })


def _interpret(delta: float, pred: float) -> str:
    """Texto ejecutivo para el pitch."""
    if abs(delta) < 0.05:
        return "El escenario prácticamente no cambia la rotación proyectada."
    if delta < 0:
        return (
            f"El escenario reduce la rotación proyectada en {abs(delta):.2f} puntos porcentuales "
            f"(rotación estimada: {pred:.2f}% bimestral)."
        )
    return (
        f"El escenario incrementa la rotación proyectada en {delta:.2f} puntos porcentuales "
        f"(rotación estimada: {pred:.2f}% bimestral)."
    )
