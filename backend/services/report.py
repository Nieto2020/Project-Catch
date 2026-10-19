# -*- coding: utf-8 -*-
"""Reporte ejecutivo: PDF (reportlab) y HTML (template en templates/)."""
from __future__ import annotations

import datetime as dt
from io import BytesIO
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

from ..core import config
from .barometro import add_scores
from .kpis import global_kpis, trends

_TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "executivo.html"


def _fmt(value, digits=2):
    if value is None:
        return "—"
    try:
        return f"{float(value):,.{digits}f}"
    except (TypeError, ValueError):
        return str(value)


def build_pdf(state) -> bytes:
    """Genera un PDF ejecutivo con los KPIs y el top del barómetro."""
    df = add_scores(state.kpis)
    kpis = global_kpis(df)
    trend = trends(df)
    today = dt.date.today().strftime("%d/%m/%Y")

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4, topMargin=20 * mm, bottomMargin=20 * mm,
        leftMargin=18 * mm, rightMargin=18 * mm,
        title="Reporte Ejecutivo SCORE",
    )
    styles = getSampleStyleSheet()
    title = styles["Title"]
    subtitle = styles["Normal"]
    body = styles["BodyText"]

    story = [
        Paragraph("SCORE — Reporte Ejecutivo", title),
        Paragraph(
            "Smart Catch Optimization &amp; Retention Ecosystem · "
            f"Generado el {today}",
            subtitle,
        ),
        Spacer(1, 6 * mm),
        Paragraph("<b>Indicadores globales (cohorte completa)</b>", styles["Heading2"]),
        Spacer(1, 3 * mm),
    ]

    kpi_pairs = [
        ("Empresas participantes", f"{kpis['empresas']}"),
        ("Bimestres analizados", f"{kpis['periodos']}"),
        ("Headcount total", f"{_fmt(kpis['headcount_total'], 0)}"),
        ("Headcount mediano", f"{_fmt(kpis['headcount_promedio'], 0)}"),
        ("Salario medio operativo (MXN/día)", f"{_fmt(kpis['salario_medio_operativo'])}"),
        ("Salario máximo mediano (MXN/día)", f"{_fmt(kpis['salario_maximo_promedio'])}"),
        ("Rotación bimestral promedio", f"{_fmt(kpis['rotacion_bimestral_promedio'])}%"),
        ("Faltas por 100 empleados", f"{_fmt(kpis['faltas_por_100_promedio'])}"),
        ("Mujeres en plantilla", f"{_fmt(kpis['mujeres_pct_promedio'])}%"),
    ]
    kpi_table = Table(
        [[Paragraph(f"<b>{k}</b>", body), Paragraph(v, body)] for k, v in kpi_pairs],
        colWidths=[95 * mm, 60 * mm],
    )
    kpi_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d1d5db")),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f3f4f6")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(kpi_table)
    story.append(Spacer(1, 6 * mm))

    story.append(Paragraph("<b>Top 5 — Barómetro de Competitividad (0-100)</b>", styles["Heading2"]))
    story.append(Spacer(1, 3 * mm))
    top = df.sort_values("score_competitividad", ascending=False).head(5)
    top_rows = [["Empresa", "Periodo", "Score", "Rotación %", "Salario medio"]]
    for _, r in top.iterrows():
        top_rows.append([
            r["empresa"], r["periodo"], f"{r['score_competitividad']:.1f}",
            _fmt(r["tasa_bajas_bimestral_pct"]), _fmt(r["salario_medio"]),
        ])
    top_table = Table(top_rows, colWidths=[30 * mm, 32 * mm, 22 * mm, 30 * mm, 41 * mm])
    top_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d1d5db")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e5e7eb")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(top_table)
    story.append(Spacer(1, 6 * mm))

    story.append(Paragraph("<b>Tendencia por bimestre</b>", styles["Heading2"]))
    story.append(Spacer(1, 3 * mm))
    trend_rows = [["Bimestre", "Empresas", "Headcount med.", "Salario med.", "Rotación %"]]
    for t in trend:
        trend_rows.append([
            t["periodo"], str(t["empresas"]), _fmt(t["headcount_mediana"], 0),
            _fmt(t["salario_medio_mediana"]), _fmt(t["rotacion_bimestral_media"]),
        ])
    trend_table = Table(trend_rows, colWidths=[32 * mm, 22 * mm, 30 * mm, 30 * mm, 41 * mm])
    trend_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d1d5db")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e5e7eb")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(trend_table)
    story.append(Spacer(1, 6 * mm))

    story.append(Paragraph(
        "Metodología: los datos provienen de la encuesta bimestral de RH (BASE HISTORICA.xlsx). "
        "El índice de competitividad pondera salario (30%), retención (30%), ausentismo (15%), "
        "capacitación (15%) y equilibrio de género (10%), normalizados por percentil 0-100.",
        subtitle,
    ))

    doc.build(story)
    return buf.getvalue()


def build_html(state) -> str:
    """Renderiza el reporte ejecutivo en HTML (para el pitch)."""
    df = add_scores(state.kpis)
    kpis = global_kpis(df)
    trend = trends(df)
    today = dt.date.today().strftime("%d/%m/%Y")

    template = _TEMPLATE.read_text(encoding="utf-8")

    kpi_rows = "\n".join(
        f"<tr><td>{k}</td><td class='v'>{v}</td></tr>"
        for k, v in [
            ("Empresas participantes", kpis["empresas"]),
            ("Bimestres analizados", kpis["periodos"]),
            ("Headcount total", _fmt(kpis["headcount_total"], 0)),
            ("Salario medio operativo (MXN/día)", _fmt(kpis["salario_medio_operativo"])),
            ("Rotación bimestral promedio", f"{_fmt(kpis['rotacion_bimestral_promedio'])}%"),
            ("Faltas por 100 empleados", _fmt(kpis["faltas_por_100_promedio"])),
        ]
    )

    top = df.sort_values("score_competitividad", ascending=False).head(5)
    top_rows = "\n".join(
        "<tr>"
        f"<td>{r['empresa']}</td><td>{r['periodo']}</td>"
        f"<td class='v'>{r['score_competitividad']:.1f}</td>"
        f"<td class='v'>{_fmt(r['tasa_bajas_bimestral_pct'])}%</td>"
        f"<td class='v'>{_fmt(r['salario_medio'])}</td>"
        "</tr>"
        for _, r in top.iterrows()
    )

    trend_rows = "\n".join(
        "<tr>"
        f"<td>{t['periodo']}</td><td>{t['empresas']}</td>"
        f"<td class='v'>{_fmt(t['headcount_mediana'], 0)}</td>"
        f"<td class='v'>{_fmt(t['salario_medio_mediana'])}</td>"
        f"<td class='v'>{_fmt(t['rotacion_bimestral_media'])}%</td>"
        "</tr>"
        for t in trend
    )

    return (
        template
        .replace("{{TITULO}}", config.APP_NAME)
        .replace("{{FECHA}}", today)
        .replace("{{KPI_ROWS}}", kpi_rows)
        .replace("{{TOP_ROWS}}", top_rows)
        .replace("{{TREND_ROWS}}", trend_rows)
    )
