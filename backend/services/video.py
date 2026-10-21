# -*- coding: utf-8 -*-
"""Generación del video descriptivo de SCORE.

Flujo: hallazgos (datos) -> gráficas (matplotlib) -> narración (edge-tts,
voz natural de Microsoft) -> ensamblado de slides en MP4 (ffmpeg).
"""
from __future__ import annotations

import asyncio
import re
import subprocess
import tempfile
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # sin interfaz gráfica

import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from ..core import config  # noqa: E402
from .barometro import add_scores, global_index  # noqa: E402
from .kpis import distributions, global_kpis, trends  # noqa: E402
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


def _hablar_num(n: float) -> str:
    """Formatea números para que la voz los lea de forma natural."""
    if n is None or pd.isna(n):
        return "sin dato"
    n = float(n)
    if abs(n) >= 1_000_000:
        return f"{n / 1_000_000:.1f} millones"
    if abs(n) >= 1_000:
        return f"{round(n / 1_000)} mil"
    if n == int(n):
        return str(int(n))
    return f"{n:.1f}".replace(".", " punto ")


def _hablar_pct(n: float) -> str:
    if n is None or pd.isna(n):
        return "sin dato"
    return f"{float(n):.1f} por ciento"


def build_findings(state) -> list[dict]:
    """Construye la lista de hallazgos (título, narración y gráfica)."""
    df = state.kpis
    k = global_kpis(df)
    t = trends(df)
    d = distributions(df)
    scored = add_scores(df)
    gi = global_index(df)
    top = scored.sort_values("score_competitividad", ascending=False).head(5)

    salario_min = k["salario_inicial_promedio"]
    salario_max = k["salario_maximo_promedio"]
    rot = k["rotacion_bimestral_promedio"]
    faltas = k["faltas_por_100_promedio"]
    generaciones = d["generaciones"]

    findings = [
        {
            "titulo": "Portada",
            "chart": "portada",
            "narracion": (
                "Bienvenidos al análisis descriptivo de S C O R E. "
                f"Estudiamos {_hablar_num(k['empresas'])} empresas industriales a lo largo de "
                f"{_hablar_num(k['periodos'])} bimestres, con un total de {_hablar_num(k['registros'])} "
                "observaciones empresa periodo. Veamos los hallazgos más importantes."
            ),
        },
        {
            "titulo": "Headcount y plantilla",
            "chart": "headcount",
            "narracion": (
                f"El headcount total de la cohorte es de {_hablar_num(k['headcount_total'])} empleados. "
                f"La empresa mediana tiene {_hablar_num(k['headcount_promedio'])} colaboradores, "
                "lo que muestra una mezcla de plantas pequeñas y operaciones muy grandes."
            ),
        },
        {
            "titulo": "Salarios operativos",
            "chart": "salario",
            "narracion": (
                f"El salario medio del personal operativo es de {_hablar_num(k['salario_medio_operativo'])} "
                "pesos diarios. El salario inicial mediano ronda los "
                f"{_hablar_num(salario_min)} pesos, mientras que el máximo alcanza "
                f"{_hablar_num(salario_max)} pesos por día."
            ),
        },
        {
            "titulo": "Rotación",
            "chart": "rotacion",
            "narracion": (
                f"La rotación bimestral promedio es de {_hablar_pct(rot)} del headcount. "
                "Los niveles varían entre bimestres, y el control de las bajas voluntarias "
                "es el principal reto de retención detectado."
            ),
        },
        {
            "titulo": "Ausentismo",
            "chart": "ausentismo",
            "narracion": (
                f"Se registran {_hablar_num(faltas)} faltas por cada cien empleados en un bimestre típico. "
                "El ausentismo injustificado presiona la productividad y se correlaciona "
                "con mayores tasas de rotación."
            ),
        },
        {
            "titulo": "Género y generaciones",
            "chart": "genero",
            "narracion": (
                f"La plantilla está compuesta en {_hablar_pct(k['mujeres_pct_promedio'])} por mujeres. "
                f"Por generaciones, los millennials representan {_hablar_pct(generaciones.get('millennials'))} "
                f"y la generación Z {_hablar_pct(generaciones.get('gen_z'))}, "
                "lo que confirma una fuerza laboral joven."
            ),
        },
        {
            "titulo": "Barómetro global",
            "chart": "barometro",
            "narracion": (
                f"El índice global de competitividad es de {_hablar_num(gi['score'])} sobre cien. "
                "Las dimensiones mejor evaluadas son las que muestran salarios competitivos "
                "y control de ausentismo, mientras que el equilibrio de género tiene espacio de mejora."
            ),
        },
        {
            "titulo": "Empresas destacadas",
            "chart": "top5",
            "narracion": (
                "Las empresas más competitivas de la cohorte son "
                + ", ".join(dict.fromkeys(r["empresa"] for _, r in top.iterrows()))
                + ". Estas combinan buena retención con salarios por encima del promedio."
            ),
        },
        {
            "titulo": "Conclusiones",
            "chart": "cierre",
            "narracion": (
                "En conclusión, SCORE identifica tres palancas accionables: subir salarios en las "
                "categorías de entrada, atacar el ausentismo injustificado y cuidar la experiencia de "
                "los empleados más jóvenes. Gracias por ver este análisis."
            ),
        },
    ]
    return findings


# ---------------------------------------------------------------------------
# Gráficas (una imagen 1280x720 por slide)
# ---------------------------------------------------------------------------
def _fig():
    fig = plt.figure(figsize=(12.8, 7.2), dpi=100)
    fig.patch.set_facecolor("#f8fafc")
    return fig


def _save(fig, path: Path) -> None:
    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            fig.tight_layout()
        except Exception:
            pass
    fig.savefig(path, dpi=100, facecolor=fig.get_facecolor())
    plt.close(fig)


def _estilo_titulo(ax, titulo: str) -> None:
    ax.set_title(titulo, fontsize=26, fontweight="bold", color="#0f172a", pad=18, loc="left")
    ax.set_facecolor("#f8fafc")


def _chart_portada(state, path: Path) -> None:
    fig = _fig()
    ax = fig.add_axes([0, 0, 1, 1])
    ax.axis("off")
    ax.set_facecolor("#0f172a")
    fig.patch.set_facecolor("#0f172a")
    ax.text(0.5, 0.58, "SCORE", ha="center", va="center", fontsize=110, fontweight="bold", color="#22d3ee")
    ax.text(
        0.5, 0.40,
        "Smart Catch Optimization & Retention Ecosystem",
        ha="center", va="center", fontsize=24, color="#e2e8f0",
    )
    ax.text(0.5, 0.30, "Análisis descriptivo de Recursos Humanos", ha="center", va="center", fontsize=20, color="#94a3b8")
    _save(fig, path)


def _chart_headcount(state, path: Path) -> None:
    d = distributions(state.kpis)["headcount"]["buckets"]
    data = sorted(d, key=lambda b: _bucket_sort(b["rango"]))
    fig = _fig()
    ax = fig.add_subplot(111)
    ax.bar([b["rango"] for b in data], [b["conteo"] for b in data], color=PALETA["azul"], width=0.6)
    _estilo_titulo(ax, "Distribución de headcount por empresa")
    ax.set_ylabel("Empresas", fontsize=14, color="#334155")
    ax.tick_params(colors="#334155", labelsize=13)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    _save(fig, path)


def _bucket_sort(rango: str) -> int:
    orden = {"<100": 0, "100-249": 1, "250-499": 2, "500-999": 3, "1000-2499": 4, "2500+": 5}
    return orden.get(rango, 99)


def _chart_salario(state, path: Path) -> None:
    t = trends(state.kpis)
    fig = _fig()
    ax = fig.add_subplot(111)
    ax.plot([r["periodo"] for r in t], [r["salario_medio_mediana"] for r in t],
            marker="o", linewidth=3, color=PALETA["cyan"], markersize=9)
    _estilo_titulo(ax, "Salario medio operativo por bimestre (MXN/día)")
    ax.set_ylabel("Pesos por día", fontsize=14, color="#334155")
    ax.tick_params(colors="#334155", labelsize=12)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    _save(fig, path)


def _chart_rotacion(state, path: Path) -> None:
    t = trends(state.kpis)
    fig = _fig()
    ax = fig.add_subplot(111)
    x = [r["periodo"] for r in t]
    ax.plot(x, [r["rotacion_bimestral_media"] for r in t], marker="o", linewidth=3, color=PALETA["rosa"], markersize=9, label="Rotación bimestral %")
    ax.plot(x, [r["faltas_por_100_mediana"] for r in t], marker="s", linewidth=3, color=PALETA["ambar"], markersize=9, label="Faltas por 100 empleados")
    _estilo_titulo(ax, "Rotación y ausentismo por bimestre")
    ax.legend(fontsize=14, frameon=False)
    ax.tick_params(colors="#334155", labelsize=12)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    _save(fig, path)


def _chart_ausentismo(state, path: Path) -> None:
    t = trends(state.kpis)
    fig = _fig()
    ax = fig.add_subplot(111)
    x = [r["periodo"] for r in t]
    ax.fill_between(x, [r["faltas_por_100_mediana"] for r in t], color=PALETA["ambar"], alpha=0.35)
    ax.plot(x, [r["faltas_por_100_mediana"] for r in t], marker="o", linewidth=3, color=PALETA["rosa"], markersize=9)
    _estilo_titulo(ax, "Faltas por cada 100 empleados (mediana)")
    ax.tick_params(colors="#334155", labelsize=12)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    _save(fig, path)


def _chart_genero(state, path: Path) -> None:
    k = global_kpis(state.kpis)
    mujeres = k["mujeres_pct_promedio"] or 0
    hombres = 100 - mujeres
    fig = _fig()
    ax = fig.add_subplot(111)
    ax.pie(
        [mujeres, hombres], labels=["Mujeres", "Hombres"], autopct="%1.0f%%",
        colors=[PALETA["violeta"], PALETA["cyan"]], startangle=90,
        textprops={"fontsize": 20, "color": "#0f172a"},
        wedgeprops={"edgecolor": "white", "linewidth": 2},
    )
    ax.set_title("Composición de género de la plantilla", fontsize=26, fontweight="bold", color="#0f172a", pad=18)
    _save(fig, path)


def _chart_barometro(state, path: Path) -> None:
    gi = global_index(state.kpis)
    dims = gi["dimensiones"]
    labels = {
        "salario": "Salario",
        "retencion": "Retención",
        "ausentismo": "Ausentismo",
        "capacitacion": "Capacitación",
        "equilibrio": "Equilibrio género",
    }
    fig = _fig()
    ax = fig.add_subplot(111)
    y = [labels[d["clave"]] for d in dims]
    v = [d["score"] for d in dims]
    ax.barh(y, v, color=[PALETA["cyan"], PALETA["esmeralda"], PALETA["ambar"], PALETA["azul"], PALETA["violeta"]])
    ax.set_xlim(0, 100)
    ax.set_title(f"Barómetro global: {gi['score']:.1f} / 100", fontsize=26, fontweight="bold", color="#0f172a", pad=18, loc="left")
    ax.tick_params(colors="#334155", labelsize=14)
    for i, val in enumerate(v):
        ax.text(val + 2, i, f"{val:.0f}", va="center", fontsize=14, color="#334155", fontweight="bold")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    _save(fig, path)


def _chart_top5(state, path: Path) -> None:
    scored = add_scores(state.kpis)
    top = scored.sort_values("score_competitividad", ascending=False).head(5)
    fig = _fig()
    ax = fig.add_subplot(111)
    y = [r["empresa"] for _, r in top.iterrows()]
    v = [r["score_competitividad"] for _, r in top.iterrows()]
    ax.barh(y[::-1], v[::-1], color=PALETA["esmeralda"])
    ax.set_xlim(0, 100)
    ax.set_title("Top 5 empresas más competitivas", fontsize=26, fontweight="bold", color="#0f172a", pad=18, loc="left")
    ax.tick_params(colors="#334155", labelsize=14)
    for i, val in enumerate(v[::-1]):
        ax.text(val + 1, i, f"{val:.1f}", va="center", fontsize=13, color="#334155", fontweight="bold")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    _save(fig, path)


def _chart_cierre(state, path: Path) -> None:
    k = global_kpis(state.kpis)
    gi = global_index(state.kpis)
    items = [
        ("Empresas", _hablar_num(k["empresas"])),
        ("Headcount total", _hablar_num(k["headcount_total"])),
        ("Rotación bimestral", _hablar_pct(k["rotacion_bimestral_promedio"])),
        ("Índice global", f"{gi['score']:.0f} / 100"),
    ]
    fig = _fig()
    ax = fig.add_axes([0, 0, 1, 1])
    ax.axis("off")
    ax.set_facecolor("#0f172a")
    fig.patch.set_facecolor("#0f172a")
    ax.text(0.5, 0.78, "Conclusiones clave", ha="center", fontsize=40, fontweight="bold", color="white")
    for i, (titulo, valor) in enumerate(items):
        y = 0.58 - i * 0.13
        ax.text(0.14, y, titulo, ha="left", fontsize=20, color="#94a3b8")
        ax.text(0.86, y, valor, ha="right", fontsize=20, fontweight="bold", color="#22d3ee")
    _save(fig, path)


_CHARTS = {
    "portada": _chart_portada,
    "headcount": _chart_headcount,
    "salario": _chart_salario,
    "rotacion": _chart_rotacion,
    "ausentismo": _chart_ausentismo,
    "genero": _chart_genero,
    "barometro": _chart_barometro,
    "top5": _chart_top5,
    "cierre": _chart_cierre,
}


def render_chart(chart_key: str, state, path: Path) -> None:
    _CHARTS[chart_key](state, path)


# ---------------------------------------------------------------------------
# Narración (TTS) y ensamblado (ffmpeg)
# ---------------------------------------------------------------------------
async def _tts(text: str, out: Path, voice: str) -> None:
    import edge_tts

    communicate = edge_tts.Communicate(text, voice, rate="+0%")
    await communicate.save(str(out))


def _ffmpeg() -> str:
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


def _run(cmd: list[str]) -> None:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip()[-800:] or "Error de ffmpeg")


def _slide_video(img: Path, audio: Path, out: Path) -> None:
    ff = _ffmpeg()
    _run([
        ff, "-y", "-loop", "1", "-i", str(img), "-i", str(audio),
        "-c:v", "libx264", "-tune", "stillimage", "-c:a", "aac", "-b:a", "192k",
        "-pix_fmt", "yuv420p", "-shortest", str(out),
    ])


def _concat(slides: list[Path], out: Path) -> None:
    ff = _ffmpeg()
    list_file = out.with_suffix(".txt")
    with open(list_file, "w", encoding="utf-8") as f:
        for s in slides:
            f.write(f"file '{str(s).replace(chr(92), '/')}'\n")
    _run([ff, "-y", "-f", "concat", "-safe", "0", "-i", str(list_file), "-c", "copy", str(out)])
    list_file.unlink(missing_ok=True)


def _duration(mp4: Path) -> float | None:
    ff = _ffmpeg()
    result = subprocess.run([ff, "-i", str(mp4)], capture_output=True, text=True)
    m = re.search(r"Duration: (\d+):(\d+):(\d+)\.(\d+)", result.stderr)
    if not m:
        return None
    h, mi, s, cs = (int(g) for g in m.groups())
    return h * 3600 + mi * 60 + s + cs / 100


def generate_video(state) -> dict:
    """Genera el video completo y devuelve metadatos."""
    findings = build_findings(state)
    config.VIDEO_DIR.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        slides: list[Path] = []
        for i, f in enumerate(findings):
            img = tmp / f"slide{i:02d}.png"
            audio = tmp / f"slide{i:02d}.mp3"
            slide = tmp / f"slide{i:02d}.mp4"
            render_chart(f["chart"], state, img)
            asyncio.run(_tts(f["narracion"], audio, config.SCORE_VOICE))
            _slide_video(img, audio, slide)
            slides.append(slide)

        _concat(slides, config.VIDEO_PATH)

    return jsonable({
        "path": str(config.VIDEO_PATH),
        "duracion_segundos": _duration(config.VIDEO_PATH),
        "hallazgos": [{"titulo": f["titulo"], "narracion": f["narracion"]} for f in findings],
    })
