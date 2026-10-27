# -*- coding: utf-8 -*-
"""Configuración central del backend de SCORE."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]

# Carga variables de entorno opcionales (backend/.env).
load_dotenv(ROOT / "backend" / ".env")

# --- Rutas de datos ---
DATA_PROCESSED = ROOT / "data" / "processed" / "kpis_empresas.parquet"

# --- LLM (asistente IA) ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "")

# DeepSeek es compatible con la API de OpenAI (solo cambia el endpoint).
DEEPSEEK_BASE_URL = "https://api.deepseek.com"

# Límite de la llamada al proveedor del chat (segundos).
LLM_TIMEOUT_SEGUNDOS = float(os.getenv("LLM_TIMEOUT_SEGUNDOS", "60"))

# --- CORS: el frontend Next.js corre en localhost:3000 ---
CORS_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

APP_NAME = "SCORE — Smart Catch Optimization & Retention Ecosystem"
APP_VERSION = "0.2.0"
