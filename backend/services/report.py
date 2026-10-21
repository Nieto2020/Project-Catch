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
from .barometro import add_scores, global_index  # noqa: E402
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


# ---------------------------------------------------------------------------
# Gráficas (base64 para incrustar en HTML)
# ---------------------------------------------------------------------------
def _data_uri(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def _estilo(ax, titulo: str) -> None:
    ax.set_title(titulo, fontsize=13, fontweight="bold", color="#0f172a", pad=10, loc="left")
    ax.tick_params(colors="#334155", labelsize=10)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)


def _figure():
    fig = plt.figure(figsize=(6.4, 3.6), dpi=110)
    fig.patch.set_facecolor("white")
    return fig


def _chart_salario(df: pd.DataFrame) -> str:
    fig = _figure()
    ax = fig.add_subplot(111)
    if df["periodo"].nunique() > 1:
        g = df.groupby("periodo")["salario_medio"].median().reset_index()
        g = g.sort_values("periodo")
        ax.plot(g["periodo"], g["salario_medio"], marker="o", linewidth=2.5, color=PALETA["cyan"], markersize=7)
        ax.set_ylabel("MXN/día", fontsize=10, color="#334155")
        _estilo(ax, "Salario medio operativo por bimestre")
    else:
        vals = [_med(df[c]) for c in SALARY_COLS]
        labels = ["Inicial", "Inter. bajo", "Inter. alto", "Máximo"]
        ax.bar(labels, [v or 0 for v in vals], color=PALETA["azul"], width=0.55)
        ax.set_ylabel("MXN/día", fontsize=10, color="#334155")
        _estilo(ax, "Niveles salariales del personal operativo (mediana)")
    return _data_uri(fig)


def _chart_rotacion(df: pd.DataFrame) -> str:
    fig = _figure()
    ax = fig.add_subplot(111)
    if df["periodo"].nunique() > 1:
        g = df.groupby("periodo").agg(
            rot=("tasa_bajas_bimestral_pct", "mean"),
            faltas=("faltas_por_100", "median"),
        ).reset_index().sort_values("periodo")
        ax.plot(g["periodo"], g["rot"], marker="o", linewidth=2.5, color=PALETA["rosa"], markersize=7, label="Rotación %")
        ax.plot(g["periodo"], g["faltas"], marker="s", linewidth=2.5, color=PALETA["ambar"], markersize=7, label="Faltas / 100")
        ax.legend(fontsize=10, frameon=False)
        _estilo(ax, "Rotación y ausentismo por bimestre")
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
    return _data_uri(fig)


def _chart_genero(df: pd.DataFrame) -> str:
    mujeres = _med(df["pct_mujeres"]) or 0
    hombres = 100 - mujeres
    fig = _figure()
    ax = fig.add_subplot(111)
    ax.pie(
        [mujeres, hombres], labels=["Mujeres", "Hombres"], autopct="%1.0f%%",
        colors=[PALETA["violeta"], PALETA["cyan"]], startangle=90,
        textprops={"fontsize": 11, "color": "#0f172a"},
        wedgeprops={"edgecolor": "white", "linewidth": 2},
    )
    ax.set_title("Composición de género (mediana)", fontsize=13, fontweight="bold", color="#0f172a", pad=10)
    return _data_uri(fig)


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
        ax.text(val + 1.5, i, f"{val:.0f}", va="center", fontsize=10, color="#334155", fontweight="bold")
    return _data_uri(fig)


def _charts_html(df: pd.DataFrame, empresa: str | None) -> str:
    items = [
        ("Salarios", _chart_salario(df)),
        ("Rotación y bajas", _chart_rotacion(df)),
        ("Género", _chart_genero(df)),
        ("Barómetro", _chart_barometro(df, empresa)),
    ]
    return "\n".join(
        f"<figure><img src='{uri}' alt='{titulo}' /><figcaption>{titulo}</figcaption></figure>"
        for titulo, uri in items
    )


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


def table_html(df: pd.DataFrame, empresa: str | None) -> tuple[str, str, str]:
    if empresa:
        titulo = f"Desglose por bimestre — {empresa}"
        head = "".join(
            f"<th style='text-align:right'>{h}</th>" if h not in ("Bimestre",)
            else f"<th>{h}</th>"
            for h in ["Bimestre", "Headcount", "Salario medio", "Rotación", "Faltas/100", "Score"]
        )
        scored = add_scores(df)
        rows = ""
        for _, r in scored.sort_values("periodo_num").iterrows():
            rows += (
                f"<tr><td>{r['periodo']}</td>"
                f"<td class='v'>{_fmt_int(r['total_headcount'])}</td>"
                f"<td class='v'>{_money(r['salario_medio'])}</td>"
                f"<td class='v'>{_fmt(r['tasa_bajas_bimestral_pct'])}%</td>"
                f"<td class='v'>{_fmt(r['faltas_por_100'], 1)}</td>"
                f"<td class='v'>{_fmt(r['score_competitividad'], 1)}</td></tr>"
            )
    else:
        titulo = "Ranking de empresas (top 10)"
        head = "".join(
            f"<th style='text-align:right'>{h}</th>" if h not in ("Empresa",)
            else f"<th>{h}</th>"
            for h in ["Empresa", "Periodo", "Score", "Salario medio", "Rotación", "Headcount"]
        )
        scored = add_scores(df).sort_values("score_competitividad", ascending=False).head(10)
        rows = ""
        for _, r in scored.iterrows():
            rows += (
                f"<tr><td>{r['empresa']}</td><td>{r['periodo']}</td>"
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
        .replace("{{KPI_ROWS}}", kpi_html)
        .replace("{{CHARTS}}", _charts_html(df, empresa))
        .replace("{{TABLA_TITULO}}", tabla_titulo)
        .replace("{{TABLA_HEAD}}", tabla_head)
        .replace("{{TABLA_ROWS}}", tabla_rows)
    )


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
