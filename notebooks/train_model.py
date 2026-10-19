# -*- coding: utf-8 -*-
"""
SCORE — Entrenamiento del modelo de rotación.

Predice `tasa_bajas_bimestral_pct` (rotación bimestral en %) a partir de
variables de estructura salarial, demografía, ausentismo y capacitación.

Ejecutar desde la raíz del repo:
    .venv\\Scripts\\python.exe notebooks\\train_model.py

Salidas:
    models/modelo_rotacion.pkl      -> Pipeline (imputación + RandomForest)
    models/modelo_rotacion_meta.json -> features, importancias y métricas CV
"""
from __future__ import annotations

import json
import datetime as dt
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import cross_val_score
from sklearn.pipeline import Pipeline

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed" / "kpis_empresas.parquet"
MODEL_DIR = ROOT / "models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

TARGET = "tasa_bajas_bimestral_pct"

# Variables usadas como predictores (excluyen la variable objetivo y sus
# desgloses, que serían fuga de información).
FEATURES = [
    # Demografía / headcount
    "emp_operativos", "emp_admin", "emp_otros", "pct_mujeres",
    "gen_baby_boomers", "gen_x", "gen_millennial_30_37",
    "gen_millennial_23_29", "gen_z",
    # Salarios (diarios, personal operativo)
    "salario_inicial", "salario_inter_bajo", "salario_inter_alto", "salario_maximo",
    # Ausentismo
    "total_faltas", "faltas_oper_justificadas", "faltas_oper_injustificadas",
    "faltas_admin_justificadas", "faltas_admin_injustificadas",
    "casos_incapacidad", "incap_riesgo_trabajo", "incap_enfermedad_general",
    "incap_maternidad", "incap_temporal", "incap_permanente_parcial",
    "incap_permanente_total",
    # Capacitación
    "hrs_cap_operativos", "hrs_cap_administrativos",
    # Sindicalización (binaria)
    "tiene_sindicato",
]


def main() -> None:
    df = pd.read_parquet(DATA)

    # Binario: tiene_sindicato -> 1/0 (los nulos se imputan después).
    df["tiene_sindicato"] = df["tiene_sindicato"].map({"Sí": 1, "No": 0})

    model_df = df[[TARGET, *FEATURES]].copy()
    model_df = model_df[model_df[TARGET].notna()].reset_index(drop=True)

    X = model_df[FEATURES]
    y = model_df[TARGET]

    pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("model", RandomForestRegressor(
                n_estimators=400,
                max_depth=None,
                min_samples_leaf=2,
                random_state=42,
                oob_score=True,
                n_jobs=-1,
            )),
        ]
    )

    # Validación cruzada (5 folds).
    cv_r2 = cross_val_score(pipeline, X, y, cv=5, scoring="r2", n_jobs=-1)
    cv_mae = -cross_val_score(pipeline, X, y, cv=5, scoring="neg_mean_absolute_error", n_jobs=-1)

    # Entrena el pipeline final.
    pipeline.fit(X, y)
    y_pred = pipeline.predict(X)

    metrics = {
        "cv_r2_mean": round(float(cv_r2.mean()), 4),
        "cv_r2_std": round(float(cv_r2.std()), 4),
        "cv_mae_mean": round(float(cv_mae.mean()), 4),
        "oob_r2": round(float(pipeline.named_steps["model"].oob_score_), 4),
        "train_mae": round(mean_absolute_error(y, y_pred), 4),
        "train_r2": round(r2_score(y, y_pred), 4),
    }

    importances = pipeline.named_steps["model"].feature_importances_
    order = np.argsort(importances)[::-1]
    feature_importance = [
        {"feature": FEATURES[i], "importance": round(float(importances[i]), 4)}
        for i in order
    ]

    meta = {
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "target": TARGET,
        "n_samples": int(len(model_df)),
        "features": FEATURES,
        "metrics": metrics,
        "feature_importance": feature_importance,
        "target_stats": {
            "min": round(float(y.min()), 2),
            "median": round(float(y.median()), 2),
            "max": round(float(y.max()), 2),
        },
    }

    import joblib
    joblib.dump(pipeline, MODEL_DIR / "modelo_rotacion.pkl")
    (MODEL_DIR / "modelo_rotacion_meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"n_samples={len(model_df)}")
    print(f"CV R2   = {metrics['cv_r2_mean']} +/- {metrics['cv_r2_std']}")
    print(f"CV MAE  = {metrics['cv_mae_mean']}")
    print(f"OOB R2  = {metrics['oob_r2']}")
    print(f"Train MAE = {metrics['train_mae']} | Train R2 = {metrics['train_r2']}")
    print("Top features:")
    for fi in feature_importance[:8]:
        print(f"  {fi['feature']}: {fi['importance']}")


if __name__ == "__main__":
    main()
