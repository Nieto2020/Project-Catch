# -*- coding: utf-8 -*-
"""Endpoints REST de SCORE: chatbot, barómetro y video descriptivo."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, Response
from pydantic import BaseModel

from ..core import config
from ..services import (
    barometro,
    chatbot,
    descriptivo,
    detalle as detalle_service,
    kpis as kpis_service,
    report as report_service,
    video as video_service,
)

router = APIRouter()


class ChatRequest(BaseModel):
    pregunta: str
    contexto: str | None = None


def _state(request: Request):
    return request.app.state.state


@router.get("/")
def root():
    return {
        "app": config.APP_NAME,
        "version": config.APP_VERSION,
        "modulos": ["chatbot", "barometro", "video", "reportes"],
        "endpoints": [
            "/api/kpis",
            "/api/barometro",
            "/api/barometro/comparables",
            "/api/empresas",
            "/api/periodos",
            "/api/chat (POST)",
            "/api/chat/estado (GET)",
            "/api/chat/sugerencias (GET)",
            "/api/video (GET)",
            "/api/video/generar (POST)",
            "/api/video/descargar (GET)",
            "/api/report/opciones (GET)",
            "/api/report (GET)",
            "/api/report/descargar (GET)",
            "/api/report/pdf (GET)",
            "/api/report/detalle (GET)",
            "/api/report/detalle/descargar (GET)",
            "/api/report/detalle/pdf (GET)",
            "/api/report/ficha (GET)",
        ],
        "llm_configurado": bool(config.OPENAI_API_KEY),
        "voz_video": config.SCORE_VOICE,
    }


@router.get("/api/kpis")
def get_kpis(request: Request):
    state = _state(request)
    return kpis_service.global_kpis(state.kpis)


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


@router.get("/api/barometro/comparables")
def get_comparables(
    request: Request,
    variable: Optional[str] = None,
    periodo: Optional[str] = None,
    talla: Optional[str] = None,
):
    """Variables descriptivas (descansos, vacaciones, prestaciones) fuera del índice."""
    state = _state(request)
    return descriptivo.comparativa(state.kpis, variable=variable, periodo=periodo, talla=talla)


@router.get("/api/chat/estado")
def get_chat_estado():
    """Indica si el modelo de lenguaje está configurado y cuál es."""
    return chatbot.estado()


@router.get("/api/chat/sugerencias")
def get_chat_sugerencias(request: Request):
    """Preguntas frecuentes con su respuesta ya calculada del dataset."""
    state = _state(request)
    return {"sugerencias": chatbot.sugerencias(state)}


@router.post("/api/chat")
def post_chat(payload: ChatRequest, request: Request):
    state = _state(request)
    return chatbot.query(state, payload.pregunta, payload.contexto)


# ---------------------------------------------------------------------------
# Video descriptivo
# ---------------------------------------------------------------------------
@router.get("/api/video")
def get_video(request: Request):
    state = _state(request)
    exists = config.VIDEO_PATH.exists()
    return {
        "disponible": exists,
        "path": str(config.VIDEO_PATH) if exists else None,
        "voz": config.SCORE_VOICE,
        "hallazgos": video_service.build_findings(state) if exists else None,
    }


@router.post("/api/video/generar")
def post_video_generar(request: Request):
    state = _state(request)
    try:
        return video_service.generate_video(state)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Error al generar el video: {exc}") from exc


@router.get("/api/video/descargar")
def get_video_descargar():
    if not config.VIDEO_PATH.exists():
        raise HTTPException(status_code=404, detail="El video aún no ha sido generado.")
    return FileResponse(
        config.VIDEO_PATH,
        media_type="video/mp4",
        filename="score_descriptivo.mp4",
    )


# ---------------------------------------------------------------------------
# Reportes ejecutivos (HTML con gráficas)
# ---------------------------------------------------------------------------
@router.get("/api/report/opciones")
def get_report_opciones(request: Request):
    state = _state(request)
    return report_service.opciones(state)


def _parse_periodos(periodos: str | None) -> list[str] | None:
    if not periodos:
        return None
    return [p.strip() for p in periodos.split(",") if p.strip()]


@router.get("/api/report")
def get_report(request: Request, empresa: str | None = None, periodos: str | None = None):
    state = _state(request)
    try:
        html = report_service.build_html(
            state, empresa=empresa, periodos=_parse_periodos(periodos)
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return HTMLResponse(content=html)


@router.get("/api/report/descargar")
def get_report_descargar(request: Request, empresa: str | None = None, periodos: str | None = None):
    state = _state(request)
    try:
        html = report_service.build_html(
            state, empresa=empresa, periodos=_parse_periodos(periodos)
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return Response(
        content=html,
        media_type="text/html",
        headers={"Content-Disposition": 'attachment; filename="reporte_score.html"'},
    )


@router.get("/api/report/pdf")
def get_report_pdf(request: Request, empresa: str | None = None, periodos: str | None = None):
    state = _state(request)
    try:
        pdf = report_service.build_pdf(
            state, empresa=empresa, periodos=_parse_periodos(periodos)
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="reporte_score.pdf"'},
    )


# ---------------------------------------------------------------------------
# Reporte detallado (ficha completa por empresa y bimestres)
# ---------------------------------------------------------------------------
@router.get("/api/report/detalle")
def get_report_detalle(request: Request, empresa: str | None = None, periodos: str | None = None):
    state = _state(request)
    try:
        html = report_service.build_detalle_html(
            state, empresa=empresa, periodos=_parse_periodos(periodos)
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return HTMLResponse(content=html)


@router.get("/api/report/detalle/descargar")
def get_report_detalle_descargar(request: Request, empresa: str | None = None, periodos: str | None = None):
    state = _state(request)
    try:
        html = report_service.build_detalle_html(
            state, empresa=empresa, periodos=_parse_periodos(periodos)
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return Response(
        content=html,
        media_type="text/html",
        headers={"Content-Disposition": 'attachment; filename="reporte_detallado.html"'},
    )


@router.get("/api/report/detalle/pdf")
def get_report_detalle_pdf(request: Request, empresa: str | None = None, periodos: str | None = None):
    state = _state(request)
    try:
        pdf = report_service.build_detalle_pdf(
            state, empresa=empresa, periodos=_parse_periodos(periodos)
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="reporte_detallado.pdf"'},
    )


@router.get("/api/report/ficha")
def get_report_ficha(request: Request, empresa: str | None = None, periodos: str | None = None):
    """Ficha estructurada (JSON) de una empresa o cohorte; la misma que usa el chat."""
    state = _state(request)
    try:
        ficha = detalle_service.perfil(
            state, empresa=empresa, periodos=_parse_periodos(periodos)
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ficha
