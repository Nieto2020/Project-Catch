# -*- coding: utf-8 -*-
"""Endpoints REST de SCORE."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel, Field

from ..core import config
from ..services import barometro, chatbot, kpis as kpis_service, report, whatif

router = APIRouter()


class WhatIfRequest(BaseModel):
    empresa: Optional[str] = None
    periodo: Optional[str] = None
    cambios: dict[str, float | str] = Field(default_factory=dict)


class ChatRequest(BaseModel):
    pregunta: str


def _state(request: Request):
    return request.app.state.state


@router.get("/")
def root():
    return {
        "app": config.APP_NAME,
        "version": config.APP_VERSION,
        "endpoints": [
            "/api/kpis",
            "/api/dashboard",
            "/api/empresas",
            "/api/barometro",
            "/api/periodos",
            "/api/whatif (POST)",
            "/api/chat (POST)",
            "/api/report/pdf",
            "/api/report/html",
        ],
        "llm_configurado": bool(config.OPENAI_API_KEY),
    }


@router.get("/api/kpis")
def get_kpis(request: Request):
    state = _state(request)
    return kpis_service.global_kpis(state.kpis)


@router.get("/api/dashboard")
def get_dashboard(request: Request):
    state = _state(request)
    return {
        "kpis": kpis_service.global_kpis(state.kpis),
        "tendencias": kpis_service.trends(state.kpis),
        "distribuciones": kpis_service.distributions(state.kpis),
        "barometro": barometro.summary(state.kpis),
    }


@router.get("/api/periodos")
def get_periodos(request: Request):
    state = _state(request)
    periodos = (
        state.kpis[["periodo", "periodo_num"]]
        .drop_duplicates()
        .sort_values("periodo_num")["periodo"]
        .tolist()
    )
    return {"periodos": periodos}


@router.get("/api/empresas")
def get_empresas(request: Request, periodo: Optional[str] = None):
    state = _state(request)
    return {"empresas": barometro.company_scores(state.kpis, periodo=periodo)}


@router.get("/api/barometro")
def get_barometro(request: Request):
    state = _state(request)
    return barometro.summary(state.kpis)


@router.post("/api/whatif")
def post_whatif(payload: WhatIfRequest, request: Request):
    state = _state(request)
    try:
        return whatif.simulate(state, payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/chat")
def post_chat(payload: ChatRequest, request: Request):
    state = _state(request)
    return chatbot.query(state, payload.pregunta)


@router.get("/api/report/pdf")
def get_report_pdf(request: Request):
    state = _state(request)
    pdf_bytes = report.build_pdf(state)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": 'inline; filename="reporte_score.pdf"'},
    )


@router.get("/api/report/html")
def get_report_html(request: Request):
    state = _state(request)
    return HTMLResponse(content=report.build_html(state))
