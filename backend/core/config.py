# -*- coding: utf-8 -*-
"""Configuración central del backend de SCORE."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]

# Carga variables de entorno opcionales (backend/.env).
load_dotenv(ROOT / "backend" / ".env")

# --- Rutas de datos y modelo ---
DATA_PROCESSED = ROOT / "data" / "processed" / "kpis_empresas.parquet"
DATA_COMPLETE = ROOT / "data" / "processed" / "encuestas_completo.parquet"
CODEBOOK_PATH = ROOT / "data" / "processed" / "diccionario_datos.csv"
MODEL_PATH = ROOT / "models" / "modelo_rotacion.pkl"
MODEL_META_PATH = ROOT / "models" / "modelo_rotacion_meta.json"

# --- LLM (asistente IA) ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# --- CORS: el frontend Next.js corre en localhost:3000 ---
CORS_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

APP_NAME = "SCORE — Smart Catch Optimization & Retention Ecosystem"
APP_VERSION = "0.1.0"
