# -*- coding: utf-8 -*-
"""Entry point de la API FastAPI de SCORE.

Ejecutar desde la raíz del repo:
    .venv\\Scripts\\python.exe -m uvicorn backend.main:app --reload
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import router
from .core import config
from .services.state import load_state


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Carga dataset y modelo en RAM al iniciar.
    app.state.state = load_state()
    yield


app = FastAPI(
    title=config.APP_NAME,
    version=config.APP_VERSION,
    description="API de analítica de Recursos Humanos para el pitch de SCORE.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000)
