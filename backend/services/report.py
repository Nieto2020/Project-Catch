# -*- coding: utf-8 -*-
"""Servicio de reportes: HTML ejecutivo con gráficas, filtrable por empresa y bimestre."""
from __future__ import annotations

import base64
import datetime as dt
import io
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # sin interfaz gráfica

import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from ..core import config  # noqa: E402
from .barometro import DIM_LABELS, add_scores, banda_de, global_index  # noqa: E402
from .detalle import perfil  # noqa: E402
from .utils import jsonable  # noqa: E402

plt.rcParams["font.family"] = "DejaVu Sans"
plt.rcParams["axes.edgecolor"] = "#cbd5e1"

PALETA = {
    "cyan": "#0ea5e9",
    "azul": "#2563eb",
    "ambar": "#f59e0b",
    "rosa": "#f43f5e",
    "esmeralda": "#10b981",
    "violeta": "#8b5cf6",
    "gris": "#64748b",
}

_TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "executivo.html"
_TEMPLATE_DETALLE = Path(__file__).resolve().parents[1] / "templates" / "detallado.html"

SALARY_COLS = ["salario_inicial", "salario_inter_bajo", "salario_inter_alto", "salario_maximo"]
MOTIVOS_BAJA = {
    "bajas_renuncia_voluntaria": "Renuncia voluntaria",
    "bajas_abandono": "Abandono de trabajo",
    "bajas_acum_faltas": "Acumulación de faltas",
    "bajas_rescision": "Rescisión de contrato",
    "bajas_disminucion_plazas": "Disminución de plazas",
    "bajas_jubilacion": "Jubilación",
    "bajas_fallecimiento": "Fallecimiento",
    "bajas_incap_permanente": "Incapacidad permanente",
    "bajas_otro": "Otro",
}


# ---------------------------------------------------------------------------
# Filtrado y formateo
# ---------------------------------------------------------------------------
def filter_data(df: pd.DataFrame, empresa: str | None, periodos: list[str] | None) -> pd.DataFrame:
    """Filtra el dataset por empresa y/o lista de bimestres."""
    out = df.copy()
    if empresa:
        out = out[out["empresa"] == empresa]
    if periodos:
        out = out[out["periodo"].isin(periodos)]
    out = out.sort_values(["periodo_num", "empresa"])
    return out


def _fmt(v, digits: int = 2) -> str:
    if v is None or pd.isna(v):
        return "—"
    try:
        return f"{float(v):,.{digits}f}"
    except (TypeError, ValueError):
        return str(v)


def _fmt_int(v) -> str:
    if v is None or pd.isna(v):
        return "—"
    return f"{int(v):,}"


def _money(v) -> str:
    if v is None or pd.isna(v):
        return "—"
    return f"${float(v):,.0f}"


def _med(series: pd.Series) -> float | None:
    s = pd.to_numeric(series, errors="coerce").dropna()
    return float(s.median()) if not s.empty else None


def _mean(series: pd.Series) -> float | None:
    s = pd.to_numeric(series, errors="coerce").dropna()
    return float(s.mean()) if not s.empty else None


# Acción sugerida por dimensión, para el resumen ejecutivo del reporte.
ACCIONES = {
    "salario": "revisar la banda salarial frente a la meta de 500 MXN/día",
    "retencion": "atacar las causas de rotación (renuncias voluntarias y abandono)",
    "ausentismo": "diagnosticar las causas de faltas y reforzar la política de asistencia",
    "capacitacion": "elevar las horas de capacitación por empleado hacia 4 h",
    "equilibrio": "equilibrar la composición de género hacia 50/50",
}


def resumen_ejecutivo(df: pd.DataFrame, empresa: str | None) -> list[tuple[str, str]]:
    """Tres viñetas para leer el reporte sin interpretar las gráficas."""
    gi = global_index(df)
    dims = gi["dimensiones"]
    mejor = max(dims, key=lambda d: d["score"])
    peores = sorted(dims, key=lambda d: d["score"])[:2]
    bimestres = int(df["periodo"].nunique())
    sujeto = empresa or f"La cohorte de {df['empresa'].nunique()} empresas"

    que_vemos = (
        f"{sujeto} registra un Índice SCORE de {gi['score']:.1f}/100 ({banda_de(gi['score'])}) "
        f"en {bimestres} bimestre{'s' if bimestres != 1 else ''}, con salario medio operativo de "
        f"{_money(_med(df['salario_medio']))} MXN/día y rotación bimestral de "
        f"{_fmt(_mean(df['tasa_bajas_bimestral_pct']))}%."
    )
    que_significa = (
        f"Su mejor atributo es {DIM_LABELS.get(mejor['clave'], mejor['clave'])} "
        f"({mejor['score']:.0f}/100) y su mayor brecha está en "
        f"{DIM_LABELS.get(peores[0]['clave'], peores[0]['clave'])} "
        f"({peores[0]['score']:.0f}/100): ahí se concentra el margen de mejora frente a la meta."
    )
    que_hacer = (
        "Priorizar "
        + " y ".join(
            f"{DIM_LABELS.get(d['clave'], d['clave'])} ({d['score']:.0f}/100, "
            f"peso {round(d['peso'] * 100)}%)"
            for d in peores
        )
        + f": {ACCIONES[peores[0]['clave']]}; después, {ACCIONES[peores[1]['clave']]}."
    )
    return [("Qué se observa", que_vemos), ("Qué significa", que_significa), ("Qué hacer", que_hacer)]


def _resumen_html(items: list[tuple[str, str]]) -> str:
    return "".join(
        f"<li><b>{etiqueta}:</b> {texto}</li>" for etiqueta, texto in items
    )


# ---------------------------------------------------------------------------
# Gráficas (base64 para incrustar en HTML)
# ---------------------------------------------------------------------------
def _png_bytes(fig) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return buf.getvalue()


def _data_uri(fig) -> str:
    return "data:image/png;base64," + base64.b64encode(_png_bytes(fig)).decode()


def _estilo(ax, titulo: str) -> None:
    ax.set_title(titulo, fontsize=15, fontweight="bold", color="#0f172a", pad=12, loc="left")
    ax.tick_params(colors="#334155", labelsize=11)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)


def _figure():
    fig = plt.figure(figsize=(7.0, 3.9), dpi=120)
    fig.patch.set_facecolor("white")
    return fig


def _periodo_eje(periodo: str) -> str:
    """Etiqueta de dos líneas para el eje X: 'JUL-AGO_2024' -> 'JUL-AGO\\n2024'."""
    rango, _, anio = str(periodo).partition("_")
    return f"{rango}\n{anio}" if anio else str(periodo)


def _eje_periodos(ax, g: pd.DataFrame) -> None:
    """Coloca un bimestre por marca, sin encimarlos, en orden cronológico."""
    ax.set_xticks(g["periodo_num"].tolist())
    ax.set_xticklabels([_periodo_eje(p) for p in g["periodo"]], fontsize=10)


def _chart_salario(df: pd.DataFrame) -> str:
    fig = _figure()
    ax = fig.add_subplot(111)
    if df["periodo"].nunique() > 1:
        g = (
            df.groupby(["periodo_num", "periodo"])["salario_medio"]
            .median()
            .reset_index()
            .sort_values("periodo_num")
        )
        ax.plot(g["periodo_num"], g["salario_medio"], marker="o", linewidth=2.5, color=PALETA["cyan"], markersize=7)
        ax.set_ylabel("MXN/día", fontsize=11, color="#334155")
        _estilo(ax, "Salario medio operativo por bimestre")
        _eje_periodos(ax, g)
    else:
        vals = [_med(df[c]) for c in SALARY_COLS]
        labels = ["Inicial", "Inter. bajo", "Inter. alto", "Máximo"]
        ax.bar(labels, [v or 0 for v in vals], color=PALETA["azul"], width=0.55)
        ax.set_ylabel("MXN/día", fontsize=11, color="#334155")
        _estilo(ax, "Niveles salariales del personal operativo (mediana)")
    return fig


def _chart_rotacion(df: pd.DataFrame) -> str:
    fig = _figure()
    ax = fig.add_subplot(111)
    if df["periodo"].nunique() > 1:
        g = (
            df.groupby(["periodo_num", "periodo"])
            .agg(rot=("tasa_bajas_bimestral_pct", "mean"), faltas=("faltas_por_100", "median"))
            .reset_index()
            .sort_values("periodo_num")
        )
        ax.plot(g["periodo_num"], g["rot"], marker="o", linewidth=2.5, color=PALETA["rosa"], markersize=7, label="Rotación %")
        ax.plot(g["periodo_num"], g["faltas"], marker="s", linewidth=2.5, color=PALETA["ambar"], markersize=7, label="Faltas / 100")
        ax.legend(fontsize=11, frameon=False)
        _estilo(ax, "Rotación y ausentismo por bimestre")
        _eje_periodos(ax, g)
    else:
        totales = {label: df[col].sum() for col, label in MOTIVOS_BAJA.items()}
        totales = {k: v for k, v in totales.items() if pd.notna(v) and v > 0}
        if totales:
            totales = dict(sorted(totales.items(), key=lambda x: x[1])[-6:])
            ax.barh(list(totales.keys()), list(totales.values()), color=PALETA["rosa"])
            _estilo(ax, "Bajas por motivo (suma del periodo)")
        else:
            ax.text(0.5, 0.5, "Sin datos de bajas", ha="center", va="center", fontsize=14, color="#94a3b8")
            ax.axis("off")
    return fig


def _chart_bajas_motivo(df: pd.DataFrame) -> str:
    """Bajas por motivo (suma de todos los bimestres seleccionados)."""
    fig = _figure()
    ax = fig.add_subplot(111)
    totales = {label: df[col].sum() for col, label in MOTIVOS_BAJA.items()}
    totales = {k: v for k, v in totales.items() if pd.notna(v) and v > 0}
    if totales:
        totales = dict(sorted(totales.items(), key=lambda x: x[1])[-8:])
        ax.barh(list(totales.keys()), list(totales.values()), color=PALETA["rosa"])
        _estilo(ax, "Bajas por motivo (suma del periodo)")
    else:
        ax.text(0.5, 0.5, "Sin datos de bajas", ha="center", va="center", fontsize=14, color="#94a3b8")
        ax.axis("off")
    return fig


def _genero_split(df: pd.DataFrame) -> tuple[float, float] | None:
    """(mujeres %, hombres %) del periodo; None si no hay porcentaje utilizable."""
    mujeres = _med(df["pct_mujeres"])
    if mujeres is None:
        hombres = _med(df["pct_hombres"])
        if hombres is None:
            return None
        mujeres = 100 - hombres
    mujeres = min(100.0, max(0.0, mujeres))
    return mujeres, 100 - mujeres


def _chart_genero(df: pd.DataFrame) -> str:
    fig = _figure()
    ax = fig.add_subplot(111)
    ax.set_title("Composición de género (mediana)", fontsize=15, fontweight="bold", color="#0f172a", pad=12)
    split = _genero_split(df)
    if split is None:
        ax.text(0.5, 0.5, "Sin datos de género", ha="center", va="center", fontsize=14, color="#94a3b8")
        ax.axis("off")
        return fig
    mujeres, hombres = split
    ax.pie(
        [mujeres, hombres], labels=["Mujeres", "Hombres"], autopct="%1.0f%%",
        colors=[PALETA["violeta"], PALETA["cyan"]], startangle=90,
        textprops={"fontsize": 12, "color": "#0f172a"},
        wedgeprops={"edgecolor": "white", "linewidth": 2},
    )
    return fig


def _chart_barometro(df: pd.DataFrame, empresa: str | None) -> str:
    gi = global_index(df)
    labels = {
        "salario": "Salario",
        "retencion": "Retención",
        "ausentismo": "Ausentismo",
        "capacitacion": "Capacitación",
        "equilibrio": "Equilibrio género",
    }
    dims = gi["dimensiones"]
    fig = _figure()
    ax = fig.add_subplot(111)
    y = [labels[d["clave"]] for d in dims]
    v = [d["score"] for d in dims]
    ax.barh(y, v, color=[PALETA["cyan"], PALETA["esmeralda"], PALETA["ambar"], PALETA["azul"], PALETA["violeta"]])
    ax.set_xlim(0, 100)
    titulo = f"Barómetro: {gi['score']:.1f} / 100" + (f" · {empresa}" if empresa else " · cohorte")
    _estilo(ax, titulo)
    for i, val in enumerate(v):
        ax.text(val + 1.5, i, f"{val:.0f}", va="center", fontsize=11, color="#334155", fontweight="bold")
    return fig


def _chart_items(df: pd.DataFrame, empresa: str | None) -> list[tuple[str, object]]:
    """Devuelve [(título, figura matplotlib)] de las 4 gráficas del reporte."""
    return [
        ("Salarios", _chart_salario(df)),
        ("Rotación y bajas", _chart_rotacion(df)),
        ("Género", _chart_genero(df)),
        ("Barómetro", _chart_barometro(df, empresa)),
    ]


def _charts_html(df: pd.DataFrame, empresa: str | None) -> str:
    return "\n".join(
        f"<figure><img src='{_data_uri(fig)}' alt='{titulo}' /><figcaption>{titulo}</figcaption></figure>"
        for titulo, fig in _chart_items(df, empresa)
    )


def _charts_bytes(df: pd.DataFrame, empresa: str | None) -> list[tuple[str, bytes]]:
    return [(titulo, _png_bytes(fig)) for titulo, fig in _chart_items(df, empresa)]


# ---------------------------------------------------------------------------
# Construcción del reporte
# ---------------------------------------------------------------------------
def kpi_rows(df: pd.DataFrame, empresa: str | None) -> list[tuple[str, str]]:
    if empresa:
        rows = [
            ("Empresa", empresa),
            ("Bimestres analizados", str(df["periodo"].nunique())),
        ]
    else:
        rows = [
            ("Empresas incluidas", str(df["empresa"].nunique())),
            ("Bimestres analizados", str(df["periodo"].nunique())),
        ]
    rows += [
        ("Headcount total", _fmt_int(df["total_headcount"].sum())),
        ("Headcount mediano", _fmt_int(_med(df["total_headcount"]))),
        ("Salario medio operativo (mediana)", _money(_med(df["salario_medio"]))),
        ("Rotación bimestral (promedio)", f"{_fmt(_mean(df['tasa_bajas_bimestral_pct']))}%"),
        ("Faltas por cada 100 empleados (mediana)", _fmt(_med(df["faltas_por_100"]), 1)),
        ("Horas de capacitación (mediana)", _fmt_int(_med(df["hrs_cap_operativos"].fillna(0) + df["hrs_cap_administrativos"].fillna(0)))),
        ("Mujeres en plantilla (mediana)", f"{_fmt(_med(df['pct_mujeres']), 1)}%"),
    ]
    return rows


def _ranking_scored(scored: pd.DataFrame, por_talla: int = 3) -> pd.DataFrame:
    """Top N por talla (una fila por empresa, con su mejor score), ordenado por talla."""
    orden = {"Micro": 0, "Pequeña": 1, "Mediana": 2, "Grande": 3}
    scored = scored.copy()
    scored["_orden"] = scored["talla"].map(lambda t: orden.get(t, 99))
    mejor = (
        scored.sort_values("score_competitividad", ascending=False)
        .groupby(["talla", "empresa"], as_index=False, sort=False)
        .head(1)
    )
    return (
        mejor.sort_values(["_orden", "score_competitividad"], ascending=[True, False])
        .groupby("talla", sort=False)
        .head(por_talla)
        .drop(columns="_orden")
    )


def table_html(df: pd.DataFrame, empresa: str | None) -> tuple[str, str, str]:
    if empresa:
        titulo = f"Desglose por bimestre — {empresa}"
        head = "".join(
            f"<th style='text-align:right'>{h}</th>" if h not in ("Bimestre",)
            else f"<th>{h}</th>"
            for h in ["Bimestre", "Talla", "Headcount", "Salario medio", "Rotación", "Faltas/100", "Score"]
        )
        scored = add_scores(df)
        rows = ""
        for _, r in scored.sort_values("periodo_num").iterrows():
            rows += (
                f"<tr><td>{r['periodo']}</td>"
                f"<td>{r['talla']}</td>"
                f"<td class='v'>{_fmt_int(r['total_headcount'])}</td>"
                f"<td class='v'>{_money(r['salario_medio'])}</td>"
                f"<td class='v'>{_fmt(r['tasa_bajas_bimestral_pct'])}%</td>"
                f"<td class='v'>{_fmt(r['faltas_por_100'], 1)}</td>"
                f"<td class='v'>{_fmt(r['score_competitividad'], 1)}</td></tr>"
            )
    else:
        titulo = "Ranking por talla (top 3 de cada talla)"
        head = "".join(
            f"<th style='text-align:right'>{h}</th>" if h not in ("Empresa", "Talla")
            else f"<th>{h}</th>"
            for h in ["Empresa", "Talla", "Periodo", "Score", "Salario medio", "Rotación", "Headcount"]
        )
        ranking = _ranking_scored(add_scores(df))
        rows = ""
        for _, r in ranking.iterrows():
            rows += (
                f"<tr><td>{r['empresa']}</td><td>{r['talla']}</td><td>{r['periodo']}</td>"
                f"<td class='v'>{_fmt(r['score_competitividad'], 1)}</td>"
                f"<td class='v'>{_money(r['salario_medio'])}</td>"
                f"<td class='v'>{_fmt(r['tasa_bajas_bimestral_pct'])}%</td>"
                f"<td class='v'>{_fmt_int(r['total_headcount'])}</td></tr>"
            )
    return titulo, head, rows


def build_html(state, empresa: str | None = None, periodos: list[str] | None = None) -> str:
    """Genera el reporte ejecutivo HTML con los filtros elegidos."""
    df = filter_data(state.kpis, empresa, periodos)
    if df.empty:
        raise ValueError("No hay datos para la combinación de empresa y bimestres elegida.")

    subtitulo = f"Empresa: {empresa}" if empresa else "Todas las empresas"
    pills = ""
    if periodos:
        pills += "".join(f"<span class='pill'>{p}</span>" for p in periodos)
    else:
        pills += "<span class='pill'>Todos los bimestres</span>"
    pills += f"<span class='pill'>{len(df)} registros</span>"

    kpi_html = "\n".join(
        f"<tr><td>{k}</td><td class='v'>{v}</td></tr>" for k, v in kpi_rows(df, empresa)
    )
    tabla_titulo, tabla_head, tabla_rows = table_html(df, empresa)

    plantilla = _TEMPLATE.read_text(encoding="utf-8")
    return (
        plantilla
        .replace("{{TITULO}}", config.APP_NAME)
        .replace("{{SUBTITULO}}", subtitulo)
        .replace("{{FECHA}}", dt.date.today().strftime("%d/%m/%Y"))
        .replace("{{FILTROS}}", pills)
        .replace("{{RESUMEN}}", _resumen_html(resumen_ejecutivo(df, empresa)))
        .replace("{{KPI_ROWS}}", kpi_html)
        .replace("{{CHARTS}}", _charts_html(df, empresa))
        .replace("{{TABLA_TITULO}}", tabla_titulo)
        .replace("{{TABLA_HEAD}}", tabla_head)
        .replace("{{TABLA_ROWS}}", tabla_rows)
    )


def _pdf_table_data(df: pd.DataFrame, empresa: str | None) -> tuple[str, list[str], list[list[str]]]:
    """Tabla del reporte en formato (título, encabezados, filas) para el PDF."""
    if empresa:
        titulo = f"Desglose por bimestre — {empresa}"
        headers = ["Bimestre", "Talla", "Headcount", "Salario medio", "Rotación", "Faltas/100", "Score"]
        scored = add_scores(df).sort_values("periodo_num")
        rows = [
            [
                r["periodo"], r["talla"], _fmt_int(r["total_headcount"]), _money(r["salario_medio"]),
                f"{_fmt(r['tasa_bajas_bimestral_pct'])}%", _fmt(r["faltas_por_100"], 1),
                _fmt(r["score_competitividad"], 1),
            ]
            for _, r in scored.iterrows()
        ]
    else:
        titulo = "Ranking por talla (top 3 de cada talla)"
        headers = ["Empresa", "Talla", "Periodo", "Score", "Salario medio", "Rotación", "Headcount"]
        ranking = _ranking_scored(add_scores(df))
        rows = [
            [
                r["empresa"], r["talla"], r["periodo"], _fmt(r["score_competitividad"], 1),
                _money(r["salario_medio"]), f"{_fmt(r['tasa_bajas_bimestral_pct'])}%",
                _fmt_int(r["total_headcount"]),
            ]
            for _, r in ranking.iterrows()
        ]
    return titulo, headers, rows


def build_pdf(state, empresa: str | None = None, periodos: list[str] | None = None) -> bytes:
    """Genera el reporte ejecutivo en PDF con las gráficas y los filtros elegidos."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        Image,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    df = filter_data(state.kpis, empresa, periodos)
    if df.empty:
        raise ValueError("No hay datos para la combinación de empresa y bimestres elegida.")

    subtitulo = f"Empresa: {empresa}" if empresa else "Todas las empresas"
    filtros = ", ".join(periodos) if periodos else "Todos los bimestres"
    fecha = dt.date.today().strftime("%d/%m/%Y")

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4, topMargin=16 * mm, bottomMargin=16 * mm,
        leftMargin=16 * mm, rightMargin=16 * mm, title="Reporte Ejecutivo SCORE",
    )
    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=styles["Title"], fontSize=19, leading=23, textColor=colors.white)
    sub = ParagraphStyle("sub", parent=styles["Normal"], fontSize=9.5, leading=13, textColor=colors.HexColor("#cbd5e1"))
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontSize=13, leading=16,
                        textColor=colors.HexColor("#0f172a"), spaceBefore=10, spaceAfter=6)
    cell = ParagraphStyle("cell", parent=styles["Normal"], fontSize=9, leading=12)
    cell_right = ParagraphStyle("cellRight", parent=cell, alignment=2)
    bullet = ParagraphStyle("bullet", parent=cell, spaceAfter=4)

    story: list = []

    # Encabezado (misma identidad visual que la plantilla HTML).
    header = Table(
        [
            [Paragraph(config.APP_NAME, h1)],
            [Paragraph(f"{subtitulo} · {fecha}", sub)],
            [Paragraph(f"Filtros: {filtros} · {len(df)} registros", sub)],
        ],
        colWidths=[178 * mm],
    )
    header.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#0f172a")),
        ("LEFTPADDING", (0, 0), (-1, -1), 14),
        ("RIGHTPADDING", (0, 0), (-1, -1), 14),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    story.append(header)
    story.append(Spacer(1, 7 * mm))

    # Resumen ejecutivo: qué se observa, qué significa y qué hacer.
    story.append(Paragraph("Resumen ejecutivo", h2))
    for etiqueta, texto in resumen_ejecutivo(df, empresa):
        story.append(Paragraph(f"• <b>{etiqueta}:</b> {texto}", bullet))
    story.append(Spacer(1, 4 * mm))

    # Indicadores clave.
    story.append(Paragraph("Indicadores clave", h2))
    kpi = Table(
        [[Paragraph(f"<b>{k}</b>", cell), Paragraph(v, cell_right)] for k, v in kpi_rows(df, empresa)],
        colWidths=[110 * mm, 68 * mm],
    )
    kpi.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e2e8f0")),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f8fafc")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(kpi)
    story.append(Spacer(1, 5 * mm))

    # Gráficas (2x2).
    story.append(Paragraph("Gráficas del análisis", h2))
    img_w = 86 * mm
    img_h = img_w / (7.0 / 3.9)
    images = [Image(io.BytesIO(data), width=img_w, height=img_h) for _, data in _charts_bytes(df, empresa)]
    cells = []
    for i in range(0, len(images), 2):
        row = images[i:i + 2]
        while len(row) < 2:
            row.append("")
        cells.append(row)
    chart_table = Table(cells, colWidths=[img_w, img_w])
    chart_table.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(chart_table)
    story.append(Spacer(1, 4 * mm))

    # Tabla de detalle.
    t_titulo, t_headers, t_rows = _pdf_table_data(df, empresa)
    story.append(Paragraph(t_titulo, h2))
    tabla = Table([t_headers] + t_rows, repeatRows=1)
    tabla.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e2e8f0")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(tabla)

    doc.build(story)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Reporte detallado (ficha completa de empresa, consultoría)
# ---------------------------------------------------------------------------
def _fmt_celda(fila: dict) -> str:
    tipo = fila.get("tipo", "num")
    valor = fila.get("valor")
    unidad = fila.get("unidad", "")
    if valor is None:
        return "—"
    if tipo == "texto":
        return str(valor)
    if tipo == "int":
        return f"{int(valor):,}" + (f" {unidad}" if unidad else "")
    if tipo == "pct":
        return f"{float(valor):,.1f}%"
    if tipo == "desglose":
        return ""
    return f"{float(valor):,.1f}" + (f" {unidad}" if unidad else "")


def _fmt_ref(fila: dict) -> str:
    ref = fila.get("cohorte")
    if ref is None:
        return ""
    tipo = fila.get("tipo", "num")
    if tipo == "pct":
        return f"{float(ref):,.1f}%"
    if tipo == "int":
        return f"{int(ref):,}"
    return f"{float(ref):,.1f}"


def _desglose_html(fila: dict) -> str:
    items = fila.get("desglose") or []
    lis = []
    for d in items:
        etiqueta = d["etiqueta"]
        valor = d.get("valor")
        pct = d.get("pct")
        if isinstance(valor, str):
            texto = f"{etiqueta}: {valor}"
            if pct is not None:
                texto += f" ({float(pct):,.0f}% de la talla)"
        elif valor is None:
            texto = f"{etiqueta}: —"
        else:
            texto = f"{etiqueta}: {int(valor):,}"
            if pct is not None:
                texto += f" ({float(pct):,.1f}%)"
        lis.append(f"<li>{texto}</li>")
    return "<ul class='desglose'>" + "".join(lis) + "</ul>"


def _secciones_html(p: dict) -> str:
    out = []
    for sec in p["secciones"]:
        filas_html = []
        for fila in sec["filas"]:
            if fila.get("tipo") == "desglose":
                filas_html.append(
                    f"<tr><td colspan='3' class='desglose-celda'>"
                    f"<span class='sub'>{fila['etiqueta']}</span>{_desglose_html(fila)}</td></tr>"
                )
            else:
                filas_html.append(
                    f"<tr><td>{fila['etiqueta']}</td>"
                    f"<td class='v'>{_fmt_celda(fila)}</td>"
                    f"<td class='v ref'>{_fmt_ref(fila) or '—'}</td></tr>"
                )
                if fila.get("desglose"):
                    filas_html.append(
                        f"<tr><td colspan='3' class='desglose-celda'>{_desglose_html(fila)}</td></tr>"
                    )
        out.append(
            f"<section><h2>{sec['titulo']}</h2><table>"
            "<thead><tr><th>Indicador</th><th style='text-align:right'>Valor</th>"
            "<th style='text-align:right'>Referencia (talla)</th></tr></thead>"
            f"<tbody>{''.join(filas_html)}</tbody></table></section>"
        )
    return "\n".join(out)


def _chart_items_detalle(df: pd.DataFrame, empresa: str | None) -> list[tuple[str, object]]:
    return [
        ("Salarios", _chart_salario(df)),
        ("Rotación y ausentismo", _chart_rotacion(df)),
        ("Bajas por motivo", _chart_bajas_motivo(df)),
        ("Género", _chart_genero(df)),
        ("Barómetro", _chart_barometro(df, empresa)),
    ]


def _charts_detalle_html(df: pd.DataFrame, empresa: str | None) -> str:
    return "\n".join(
        f"<figure><img src='{_data_uri(fig)}' alt='{titulo}' /><figcaption>{titulo}</figcaption></figure>"
        for titulo, fig in _chart_items_detalle(df, empresa)
    )


def build_detalle_html(state, empresa: str | None = None, periodos: list[str] | None = None) -> str:
    """Reporte detallado HTML con la ficha completa por empresa y bimestres."""
    p = perfil(state, empresa, periodos)
    df = filter_data(state.kpis, empresa, periodos)

    subtitulo = f"Empresa: {empresa}" if empresa else "Todas las empresas"
    pills = "".join(f"<span class='pill'>{x}</span>" for x in periodos) if periodos else ""
    pills += "<span class='pill'>Todos los bimestres</span>" if not periodos else ""
    pills += f"<span class='pill'>{p['registros']} registros</span>"

    kpi_html = "\n".join(
        f"<tr><td>{k}</td><td class='v'>{v}</td></tr>" for k, v in kpi_rows(df, empresa)
    )

    plantilla = _TEMPLATE_DETALLE.read_text(encoding="utf-8")
    return (
        plantilla
        .replace("{{TITULO}}", config.APP_NAME)
        .replace("{{SUBTITULO}}", subtitulo)
        .replace("{{FECHA}}", dt.date.today().strftime("%d/%m/%Y"))
        .replace("{{FILTROS}}", pills)
        .replace("{{RESUMEN}}", _resumen_html(resumen_ejecutivo(df, empresa)))
        .replace("{{KPI_ROWS}}", kpi_html)
        .replace("{{CHARTS}}", _charts_detalle_html(df, empresa))
        .replace("{{SECCIONES}}", _secciones_html(p))
    )


def _pdf_filas_seccion(sec: dict) -> list[list[str]]:
    filas: list[list[str]] = []
    for fila in sec["filas"]:
        etiqueta = fila["etiqueta"]
        if fila.get("tipo") == "desglose":
            filas.append([f"• {etiqueta}", "", ""])
            for d in fila.get("desglose") or []:
                valor = d.get("valor")
                pct = d.get("pct")
                if isinstance(valor, str):
                    texto = valor + (f" ({float(pct):.0f}% talla)" if pct is not None else "")
                elif valor is None:
                    texto = "—"
                else:
                    texto = f"{int(valor):,}" + (f" ({float(pct):,.1f}%)" if pct is not None else "")
                filas.append([f"    {d['etiqueta']}", texto, ""])
        else:
            filas.append([etiqueta, _fmt_celda(fila), _fmt_ref(fila) or "—"])
    return filas


def build_detalle_pdf(state, empresa: str | None = None, periodos: list[str] | None = None) -> bytes:
    """Reporte detallado en PDF con la ficha completa por empresa y bimestres."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    p = perfil(state, empresa, periodos)
    df = filter_data(state.kpis, empresa, periodos)

    subtitulo = f"Empresa: {empresa}" if empresa else "Todas las empresas"
    filtros = ", ".join(periodos) if periodos else "Todos los bimestres"
    fecha = dt.date.today().strftime("%d/%m/%Y")

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4, topMargin=16 * mm, bottomMargin=16 * mm,
        leftMargin=16 * mm, rightMargin=16 * mm, title="Reporte Detallado SCORE",
    )
    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=styles["Title"], fontSize=19, leading=23, textColor=colors.white)
    sub = ParagraphStyle("sub", parent=styles["Normal"], fontSize=9.5, leading=13, textColor=colors.HexColor("#cbd5e1"))
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontSize=13, leading=16,
                        textColor=colors.HexColor("#0f172a"), spaceBefore=10, spaceAfter=6)
    cell = ParagraphStyle("cell", parent=styles["Normal"], fontSize=9, leading=12)
    cell_right = ParagraphStyle("cellRight", parent=cell, alignment=2)
    bullet = ParagraphStyle("bullet", parent=cell, spaceAfter=4)

    story: list = []

    header = Table(
        [
            [Paragraph(config.APP_NAME, h1)],
            [Paragraph(f"{subtitulo} · {fecha}", sub)],
            [Paragraph(f"Filtros: {filtros} · {p['registros']} registros · Talla: {p['talla']}", sub)],
        ],
        colWidths=[178 * mm],
    )
    header.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#0f172a")),
        ("LEFTPADDING", (0, 0), (-1, -1), 14),
        ("RIGHTPADDING", (0, 0), (-1, -1), 14),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    story.append(header)
    story.append(Spacer(1, 7 * mm))

    # Resumen ejecutivo: qué se observa, qué significa y qué hacer.
    story.append(Paragraph("Resumen ejecutivo", h2))
    for etiqueta, texto in resumen_ejecutivo(df, empresa):
        story.append(Paragraph(f"• <b>{etiqueta}:</b> {texto}", bullet))
    story.append(Spacer(1, 4 * mm))

    # Indicadores clave.
    story.append(Paragraph("Indicadores clave", h2))
    kpi = Table(
        [[Paragraph(f"<b>{k}</b>", cell), Paragraph(v, cell_right)] for k, v in kpi_rows(df, empresa)],
        colWidths=[110 * mm, 68 * mm],
    )
    kpi.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e2e8f0")),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f8fafc")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(kpi)
    story.append(Spacer(1, 5 * mm))

    # Gráficas (2 columnas).
    story.append(Paragraph("Gráficas del análisis", h2))
    img_w = 86 * mm
    img_h = img_w / (7.0 / 3.9)
    images = [Image(io.BytesIO(data), width=img_w, height=img_h)
              for _, data in [(t, _png_bytes(f)) for t, f in _chart_items_detalle(df, empresa)]]
    cells = []
    for i in range(0, len(images), 2):
        row = images[i:i + 2]
        while len(row) < 2:
            row.append("")
        cells.append(row)
    chart_table = Table(cells, colWidths=[img_w, img_w])
    chart_table.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(chart_table)
    story.append(Spacer(1, 4 * mm))

    # Ficha detallada por secciones.
    for sec in p["secciones"]:
        story.append(Paragraph(sec["titulo"], h2))
        tabla = Table([["Indicador", "Valor", "Referencia (talla)"]] + _pdf_filas_seccion(sec),
                      colWidths=[88 * mm, 50 * mm, 40 * mm], repeatRows=1)
        tabla.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e2e8f0")),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(tabla)
        story.append(Spacer(1, 3 * mm))

    doc.build(story)
    return buf.getvalue()


def opciones(state) -> dict:
    """Opciones para el formulario: empresas y bimestres disponibles."""
    empresas = sorted(state.kpis["empresa"].dropna().unique().tolist())
    periodos = (
        state.kpis[["periodo", "periodo_num"]]
        .drop_duplicates()
        .sort_values("periodo_num")["periodo"]
        .tolist()
    )
    return jsonable({"empresas": empresas, "periodos": periodos})
