# -*- coding: utf-8 -*-
"""Asistente IA (chat): respuesta LLM de una sola llamada sobre un resumen."""
from __future__ import annotations

import logging
import re
import time

import pandas as pd

from ..core import config, prompts
from .barometro import add_scores, global_index
from .detalle import EDAD_BAJAS, MOTIVOS_BAJA, ficha_text
from .utils import jsonable

# Se cuelga del logger de uvicorn para que los tiempos salgan en la terminal.
logger = logging.getLogger("uvicorn.error")


def _norm(text: str) -> str:
    """Normaliza acentos y minúsculas para el pattern matching."""
    replacements = {"á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u", "ñ": "n"}
    t = text.lower().strip()
    for a, b in replacements.items():
        t = t.replace(a, b)
    return t


def _empresa_mencionada(state, question: str) -> str | None:
    """Nombre de empresa si la pregunta la menciona (COMPAÑÍA 10, empresa 10, la 10...)."""
    q = _norm(question)
    if not q:
        return None
    empresas = [(str(e), _norm(str(e))) for e in state.kpis["empresa"].dropna().unique()]
    # De mayor a menor nombre para que "compania 10" se evalúe antes que "compania 1".
    for empresa, nombre in sorted(empresas, key=lambda t: -len(t[1])):
        numero = nombre.split()[-1] if nombre.split() else ""
        if not numero.isdigit():
            continue
        patrones = [
            rf"\b{re.escape(nombre)}\b",
            rf"\bempresa\s+{numero}\b",
            rf"\bcompania\s+{numero}\b",
            rf"\bla\s+{numero}\b",
        ]
        if any(re.search(p, q) for p in patrones):
            return empresa
    return None


def _ficha_conveniente(question: str) -> bool:
    """Si conviene adjuntar la ficha completa de la empresa mencionada.

    En preguntas de ranking o comparación entre empresas el resumen ya trae los
    extremos con su motivo y generación, así que la ficha solo alargaría el
    prompt sin aportar a la respuesta.
    """
    q = _norm(question)
    return not re.search(
        r"cual(es)? de las empresas|que empresa|cual es la empresa|"
        r"ranking|top\s*\d|lista de empresas|empresas con (mayor|menor|mas)",
        q,
    )


# Único motor del chat: el agente LLM.
MODE_LLM = "llm"

SUGERENCIAS = (
    "¿Cuántas empresas hay?",
    "¿Cuántos empleados hay en total?",
    "¿Cuál es la rotación bimestral promedio?",
    "¿Por qué renuncian los trabajadores?",
    "¿Cuál es la empresa con mayor rotación y por qué?",
    "¿Qué empresas tienen la rotación más baja?",
    "¿A qué generación de edad pertenecen los que se dieron de baja?",
    "¿Cómo se movieron las bajas en cada bimestre?",
    "¿Cuál es el salario inicial promedio del personal operativo?",
    "¿Cuál es el promedio de faltas por cada 100 empleados?",
    "¿Qué proporción de mujeres y hombres hay?",
    "¿Cuántas horas de capacitación se invierten al bimestre?",
    "¿Cuántos registros tienen sindicato?",
    "¿Cuáles son las 5 empresas más competitivas?",
)


def llm_disponible() -> bool:
    """True si hay una API key configurada para el agente LLM."""
    return bool(config.OPENAI_API_KEY)


def estado() -> dict:
    """Estado del asistente para la UI (si la API está lista y con qué modelo)."""
    return jsonable({
        "llm_disponible": llm_disponible(),
        "modelo": config.OPENAI_MODEL if llm_disponible() else None,
    })


def sugerencias(state) -> list[dict]:
    """Preguntas frecuentes con su respuesta ya calculada del dataset.

    Se responden al instante y sin consumir el modelo; el chat libre usa el LLM.
    """
    scored = add_scores(state.kpis)
    items = []
    for pregunta in SUGERENCIAS:
        respuesta = _local_answer(state, pregunta, scored)
        if respuesta:
            items.append({"pregunta": pregunta, "respuesta": respuesta})
    return jsonable(items)


def query(state, question: str, contexto: str | None = None) -> dict:
    """Responde una pregunta con el agente LLM (único motor del chat)."""
    question = (question or "").strip()
    if not question:
        return {
            "answer": prompts.FALLBACK_HELP,
            "engine": MODE_LLM,
            "motivo": "sin pregunta",
        }

    if not llm_disponible():
        return _respuesta_respaldo(
            state, question, "falta `OPENAI_API_KEY` en `backend/.env`"
        )

    inicio = time.perf_counter()
    try:
        answer = _llm_query(state, question, contexto)
    except Exception as exc:  # noqa: BLE001 — nunca debe romper la demo
        transcurrido = time.perf_counter() - inicio
        logger.warning("chat LLM falló tras %.1fs: %s", transcurrido, exc)
        return _respuesta_respaldo(state, question, f"error del modelo: {exc}")

    transcurrido = time.perf_counter() - inicio
    if not answer:
        logger.warning("chat LLM devolvió una respuesta vacía tras %.1fs", transcurrido)
        return _respuesta_respaldo(state, question, "el modelo no devolvió texto")

    logger.info("chat LLM respondido en %.1fs (contexto=%s)", transcurrido, bool(contexto))
    return {
        "answer": answer,
        "engine": MODE_LLM,
        "motivo": "agente LLM" + (" con contexto" if contexto else ""),
    }


def _respuesta_respaldo(state, question: str, causa: str) -> dict:
    """Respuesta garantizada cuando el modelo no está disponible o falla.

    Usa la respuesta precalculada del dataset y, si la pregunta no está
    cubierta, el resumen del dataset: el chat nunca queda sin respuesta.
    """
    motivo = f"respaldo local — {causa}"

    # Si la pregunta menciona una empresa concreta, su ficha completa responde
    # mejor que cualquier respuesta genérica y evita iteraciones.
    try:
        empresa = _empresa_mencionada(state, question)
    except Exception:  # noqa: BLE001
        empresa = None
    if empresa and _ficha_conveniente(question):
        try:
            ficha = ficha_text(state, empresa)
            return {
                "answer": (
                    f"Ficha detallada de {empresa} (el modelo no está disponible ahora — {causa}):\n\n{ficha}"
                ),
                "engine": MODE_LLM,
                "motivo": f"{motivo} — ficha de empresa",
            }
        except Exception:  # noqa: BLE001
            logger.warning("no se pudo construir la ficha de %s", empresa, exc_info=True)

    local = None
    try:
        local = _local_answer(state, question)
    except Exception:  # noqa: BLE001
        logger.warning("la respuesta local falló", exc_info=True)

    if local:
        return {
            "answer": (
                f"{local}\n\n"
                f"(Respuesta calculada del dataset: el modelo no está disponible ahora — {causa})."
            ),
            "engine": MODE_LLM,
            "motivo": motivo,
        }

    try:
        resumen = _build_summary(state)
    except Exception:  # noqa: BLE001
        logger.warning("no se pudo construir el resumen del dataset", exc_info=True)
        return {
            "answer": (
                "El asistente no puede responder en este momento "
                f"({causa}). Revisa la configuración del modelo y reinicia el backend."
            ),
            "engine": MODE_LLM,
            "motivo": motivo,
        }

    return {
        "answer": (
            f"El modelo no está disponible ahora ({causa}). "
            f"Mientras tanto, este es el resumen del dataset:\n\n{resumen}"
        ),
        "engine": MODE_LLM,
        "motivo": motivo,
    }


def _med(series: pd.Series) -> float | None:
    s = pd.to_numeric(series, errors="coerce").dropna()
    return float(s.median()) if not s.empty else None


def _mean(series: pd.Series) -> float | None:
    s = pd.to_numeric(series, errors="coerce").dropna()
    return float(s.mean()) if not s.empty else None


def _fmt(v, digits: int = 1) -> str:
    if v is None:
        return "sin dato"
    txt = f"{v:,.{digits}f}"
    # Solo se recortan los decimales sobrantes: "20" o "2,355" no deben cambiar.
    return txt.rstrip("0").rstrip(".") if "." in txt else txt


# --- Bajas: motivo, impacto por bimestre y generación de edad --------------
# Los motivos se capturan como conteo; la edad de las bajas viene como
# proporción de las bajas de cada empresa-bimestre (suma 1 por registro).
def _bajas_por_motivo(df: pd.DataFrame) -> list[dict]:
    """Bajas atribuidas a cada motivo y su % de las bajas con motivo declarado."""
    filas = []
    for col, etiqueta in MOTIVOS_BAJA.items():
        if col not in df.columns:
            continue
        serie = pd.to_numeric(df[col], errors="coerce").dropna()
        if serie.empty:
            continue
        filas.append({"etiqueta": etiqueta, "bajas": float(serie.sum())})
    total = sum(fila["bajas"] for fila in filas)
    for fila in filas:
        fila["pct"] = fila["bajas"] / total * 100 if total else None
    filas.sort(key=lambda fila: -fila["bajas"])
    return filas


def _bajas_por_generacion(df: pd.DataFrame) -> list[dict]:
    """Bajas por generación: proporciones ponderadas por las bajas del registro."""
    columnas = [col for col in EDAD_BAJAS if col in df.columns]
    proporcion = df[columnas].apply(pd.to_numeric, errors="coerce")
    # Algunos registros reparten de más (suman >1): la participación se
    # normaliza por fila para que el reparto sea comparable entre empresas.
    suma_fila = proporcion.sum(axis=1, min_count=1)
    participacion = proporcion.div(suma_fila.where(suma_fila > 0), axis=0)
    conteos = pd.to_numeric(df["total_bajas"], errors="coerce")
    filas = []
    for col in columnas:
        valor = (participacion[col] * conteos).sum(min_count=1)
        if pd.isna(valor):
            continue
        filas.append({"etiqueta": EDAD_BAJAS[col], "bajas": float(valor)})
    total = sum(fila["bajas"] for fila in filas)
    for fila in filas:
        fila["pct"] = fila["bajas"] / total * 100 if total else None
    filas.sort(key=lambda fila: -fila["bajas"])
    return filas


def _bajas_por_bimestre(df: pd.DataFrame) -> list[dict]:
    """Bajas del bimestre y tasa media de rotación, en orden cronológico."""
    filas = []
    for (periodo, num), g in df.groupby(["periodo", "periodo_num"], sort=True):
        bajas = pd.to_numeric(g["total_bajas"], errors="coerce")
        tasa = pd.to_numeric(g["tasa_bajas_bimestral_pct"], errors="coerce").dropna()
        filas.append({
            "periodo": str(periodo),
            "periodo_num": int(num),
            "bajas": float(bajas.sum()) if bajas.notna().any() else None,
            "tasa_media": float(tasa.mean()) if not tasa.empty else None,
        })
    filas.sort(key=lambda fila: fila["periodo_num"])
    return filas


# --- Rankings por empresa --------------------------------------------------
# Métricas comparables: (patrón en la pregunta, columna, etiqueta, decimales, unidad,
# comparativos (alto, bajo) para redactar la frase).
METRICAS_RANKING = (
    (r"rotacion|bajas|renuncia|abandon", "tasa_bajas_bimestral_pct",
     "rotación bimestral media", 2, "%", ("mayor", "menor")),
    (r"faltas|ausentismo", "faltas_por_100",
     "faltas por cada 100 empleados", 1, "", ("más", "menos")),
    (r"salario|sueldo", "salario_medio",
     "salario medio", 1, " MXN/día", ("mayor", "menor")),
    (r"capacitacion", "cap_por_empleado",
     "horas de capacitación por empleado", 1, " h", ("más", "menos")),
    (r"headcount|plantilla|empleados|personal", "total_headcount",
     "headcount", 0, "", ("mayor", "menor")),
)


def _razones_baja(df: pd.DataFrame, empresa: str) -> tuple[dict | None, dict | None]:
    """Motivo y generación predominantes entre las bajas de una empresa."""
    sub = df[df["empresa"] == empresa]
    motivos = [m for m in _bajas_por_motivo(sub) if m["etiqueta"] != "Otro"]
    generaciones = [g for g in _bajas_por_generacion(sub) if g["etiqueta"] != "No medido"]
    return (motivos[0] if motivos else None, generaciones[0] if generaciones else None)


def _ranking_empresas(df: pd.DataFrame, col: str, ascendente: bool = False,
                      n: int = 5) -> list[dict]:
    """Ranking de empresas por la media de una métrica (una fila por empresa).

    La media entre bimestres evita que una empresa quede arriba solo por un
    bimestre atípico, y permite comparar empresas con distinto número de
    periodos capturados.
    """
    if col not in df.columns:
        return []
    agrupado = (
        df.groupby("empresa")
        .agg(
            valor=(col, "mean"),
            periodos=("periodo", "nunique"),
            headcount=("total_headcount", "median"),
            talla=("talla", lambda s: s.mode().iloc[0] if not s.mode().empty else "—"),
        )
        .dropna(subset=["valor"])
        .sort_values("valor", ascending=ascendente)
        .head(n)
    )

    filas = []
    for empresa, r in agrupado.iterrows():
        fila = {
            "empresa": str(empresa),
            "valor": float(r["valor"]),
            "periodos": int(r["periodos"]),
            "headcount": float(r["headcount"]) if pd.notna(r["headcount"]) else None,
            "talla": str(r["talla"]),
        }
        if col == "tasa_bajas_bimestral_pct":
            conteos = pd.to_numeric(df.loc[df["empresa"] == empresa, "total_bajas"], errors="coerce")
            fila["bajas"] = float(conteos.sum()) if conteos.notna().any() else None
            fila["motivo"], fila["generacion"] = _razones_baja(df, empresa)
        filas.append(fila)
    return filas


def _fmt_ranking(filas: list[dict], etiqueta: str, sentido: str, digits: int = 2,
                 unidad: str = "", referencia: float | None = None) -> str:
    """Ranking en una línea, con motivo y generación cuando la métrica son bajas."""
    cabecera = f"Empresas con {sentido} {etiqueta}"
    if referencia is not None:
        cabecera += f" (promedio de la cohorte {_fmt(referencia, digits)}{unidad})"

    partes = []
    for i, fila in enumerate(filas, 1):
        detalle = f"{i}. {fila['empresa']} ({fila['talla']}): {_fmt(fila['valor'], digits)}{unidad}"
        if fila.get("bajas") is not None:
            detalle += f", {_fmt(fila['bajas'], 0)} bajas en {fila['periodos']} bimestres"
        if fila.get("motivo") and fila["motivo"]["bajas"]:
            detalle += f", motivo principal {fila['motivo']['etiqueta'].lower()} {_fmt(fila['motivo']['pct'], 0)}%"
        if fila.get("generacion") and fila["generacion"]["bajas"]:
            detalle += f", generación {fila['generacion']['etiqueta']} {_fmt(fila['generacion']['pct'], 0)}%"
        partes.append(detalle)
    return f"{cabecera}: " + "; ".join(partes) + "."


def _build_summary(state) -> str:
    """Resumen compacto del dataset calculado en Python (sin LLM).

    Se envía al modelo para que responda en una sola llamada, sin iterar
    sobre el DataFrame. Es lo que mantiene el chat rápido y confiable.
    """
    df = add_scores(state.kpis)
    total_headcount = int(df["total_headcount"].sum())
    n_empresas = int(df["empresa"].nunique())
    n_periodos = int(df["periodo"].nunique())
    n_registros = int(len(df))

    sindicato_si = int((df["tiene_sindicato"] == "Sí").sum())
    pct_sindicato = sindicato_si / n_registros * 100 if n_registros else 0

    def pct_otorgan(col: str) -> str:
        return _fmt(df[col].fillna(False).astype(bool).mean() * 100, 0)

    def por_talla(col: str) -> str:
        medianas = (
            df.groupby("talla")[col].median()
            .reindex([t for t in ("Micro", "Pequeña", "Mediana", "Grande") if t in set(df["talla"])])
        )
        return ", ".join(
            f"{talla} {_fmt(valor, 1)}" for talla, valor in medianas.items() if pd.notna(valor)
        )

    top = (
        df.sort_values("score_competitividad", ascending=False)
        .groupby("empresa", as_index=False)
        .head(1)
        .sort_values("score_competitividad", ascending=False)
        .head(5)
    )
    top_lineas = "\n".join(
        f"- {r['empresa']} ({r['talla']}, {r['periodo']}): "
        f"score {r['score_competitividad']:.1f}/100, headcount {int(r['total_headcount'])}, "
        f"salario medio {r['salario_medio']:.0f} MXN/día, "
        f"rotación {r['tasa_bajas_bimestral_pct']:.2f}%"
        for _, r in top.iterrows()
    )

    gi = global_index(df)

    motivos = _bajas_por_motivo(df)
    generaciones_bajas = _bajas_por_generacion(df)
    bimestres = _bajas_por_bimestre(df)
    total_bajas = float(pd.to_numeric(df["total_bajas"], errors="coerce").dropna().sum())
    peor = max((b for b in bimestres if b["tasa_media"] is not None),
               key=lambda b: b["tasa_media"], default=None)
    mayor_rotacion = _ranking_empresas(df, "tasa_bajas_bimestral_pct", n=5)
    menor_rotacion = _ranking_empresas(df, "tasa_bajas_bimestral_pct", ascendente=True, n=3)
    rotacion_media = _mean(df["tasa_bajas_bimestral_pct"])
    linea_mayor = ("- " + _fmt_ranking(mayor_rotacion, "rotación bimestral media", "mayor", 2, "%",
                                       rotacion_media)
                   if mayor_rotacion else "- Sin datos de rotación por empresa")
    linea_menor = ("- " + _fmt_ranking(menor_rotacion, "rotación bimestral media", "menor", 2, "%",
                                       rotacion_media)
                   if menor_rotacion else "")

    lineas = [
        "RESUMEN DEL DATASET (encuesta bimestral de RH, nivel empresa):",
        f"- Registros empresa-bimestre: {n_registros} · Empresas únicas: {n_empresas} · Bimestres: {n_periodos}",
        f"- Headcount: total {total_headcount:,} · mediana {_fmt(_med(df['total_headcount']), 0)} por empresa",
        "- Salario diario del personal operativo (medianas, MXN/día): "
        f"inicial {_fmt(_med(df['salario_inicial']), 2)}, intermedio bajo {_fmt(_med(df['salario_inter_bajo']), 2)}, "
        f"intermedio alto {_fmt(_med(df['salario_inter_alto']), 2)}, máximo {_fmt(_med(df['salario_maximo']), 2)}",
        f"- Rotación bimestral: promedio {_fmt(_mean(df['tasa_bajas_bimestral_pct']), 2)}% del headcount "
        f"(mediana {_fmt(_med(df['tasa_bajas_bimestral_pct']), 2)}%)",
        f"- Bajas acumuladas en los {n_periodos} bimestres: {_fmt(total_bajas, 0)}",
        "- Motivos de baja (% de las bajas con motivo declarado): "
        + "; ".join(f"{m['etiqueta']} {_fmt(m['pct'], 1)}% ({_fmt(m['bajas'], 0)})" for m in motivos),
        "- Bajas por generación de edad (ponderadas por bajas): "
        + "; ".join(f"{g['etiqueta']} {_fmt(g['pct'], 1)}% ({_fmt(g['bajas'], 0)})" for g in generaciones_bajas),
        "- Bajas por bimestre (bajas · tasa media de rotación): "
        + "; ".join(f"{b['periodo']} {_fmt(b['bajas'], 0)} · {_fmt(b['tasa_media'], 2)}%" for b in bimestres)
        + (f". El bimestre con mayor rotación media fue {peor['periodo']} ({_fmt(peor['tasa_media'], 2)}%)"
           if peor else ""),
        linea_mayor,
        linea_menor,
        f"- Faltas: mediana {_fmt(_med(df['faltas_por_100']), 1)} por cada 100 empleados "
        f"(promedio {_fmt(_mean(df['total_faltas']), 0)} faltas por empresa-bimestre)",
        f"- Capacitación: mediana {_fmt(_med(df['hrs_cap_operativos'].fillna(0) + df['hrs_cap_administrativos'].fillna(0)), 0)} horas por empresa-bimestre",
        f"- Género: mediana {_fmt(_med(df['pct_mujeres']), 1)}% mujeres",
        f"- Generaciones (medianas %): Baby Boomers {_fmt(_med(df['gen_baby_boomers']), 0)}, "
        f"Gen X {_fmt(_med(df['gen_x']), 0)}, Millennials "
        f"{_fmt(_med(df['gen_millennial_30_37'].fillna(0) + df['gen_millennial_23_29'].fillna(0)), 0)}, "
        f"Gen Z {_fmt(_med(df['gen_z']), 0)}",
        f"- Sindicato: {sindicato_si} de {n_registros} registros ({pct_sindicato:.1f}%)",
        "- Prestaciones (medianas, personal operativo): "
        f"vacaciones 1.er año {_fmt(_med(df['vacaciones_1er_anio']), 0)} días, "
        f"aguinaldo {_fmt(_med(df['aguinaldo_dias']), 0)} días, "
        f"prima vacacional {_fmt(_med(df['prima_vacacional_pct']), 0)}%, "
        f"vales de despensa {_fmt(_med(df['vales_despensa_pct']), 1)}%, "
        f"fondo de ahorro {_fmt(_med(df['fondo_ahorro_pct']), 1)}%",
        f"- Descansos adicionales a los festivos de ley: mediana {_fmt(_med(df['dias_descanso_adicionales']), 0)} días. "
        f"Los otorgan: Viernes Santo {pct_otorgan('descanso_viernes_santo')}%, Jueves Santo {pct_otorgan('descanso_jueves_santo')}%, "
        f"12 dic {pct_otorgan('descanso_12_diciembre')}%, 24 dic {pct_otorgan('descanso_24_diciembre')}%, "
        f"31 dic {pct_otorgan('descanso_31_diciembre')}%, 2 nov {pct_otorgan('descanso_2_noviembre')}%, "
        f"matrimonio {pct_otorgan('descanso_matrimonio')}%, defunción {pct_otorgan('descanso_defuncion')}%",
        f"- Descansos adicionales por talla (mediana de días): {por_talla('dias_descanso_adicionales')}",
        f"- Aguinaldo por talla (mediana de días): {por_talla('aguinaldo_dias')}",
        "- Nota: estas condiciones descriptivas NO ponderan el Índice SCORE.",
        f"- Índice SCORE global: {gi['score']:.1f}/100",
        "- Top 5 empresas por Índice SCORE:",
        top_lineas,
    ]
    return "\n".join(lineas)


def _llm_query(state, question: str, contexto: str | None = None) -> str:
    """Respuesta de una sola llamada al LLM sobre el resumen del dataset."""
    from langchain_core.messages import HumanMessage, SystemMessage
    from langchain_openai import ChatOpenAI

    resumen = _build_summary(state)

    # Si la pregunta menciona una empresa, se adjunta su ficha completa para
    # que el modelo responda con todo a la mano (una sola llamada, sin iterar).
    empresa = None
    ficha = None
    try:
        empresa = _empresa_mencionada(state, question)
        if empresa and _ficha_conveniente(question):
            ficha = ficha_text(state, empresa)
    except Exception:  # noqa: BLE001
        logger.warning("no se pudo preparar la ficha de empresa", exc_info=True)

    llm_kwargs = {
        "model": config.OPENAI_MODEL,
        "temperature": 0,
        "api_key": config.OPENAI_API_KEY,
        "timeout": config.LLM_TIMEOUT_SEGUNDOS,
        "max_retries": 1,
    }
    base_url = config.OPENAI_BASE_URL
    if not base_url and "deepseek" in config.OPENAI_MODEL.lower():
        base_url = config.DEEPSEEK_BASE_URL
    if base_url:
        llm_kwargs["base_url"] = base_url

    llm = ChatOpenAI(**llm_kwargs)

    texto = ""
    if ficha:
        texto += (
            f"FICHA DETALLADA de la empresa mencionada ({empresa}). "
            "Úsala como fuente principal para responder sobre esa empresa:\n"
            f"{ficha}\n\n"
        )
    texto += f"RESUMEN general de la cohorte (para comparar contra el promedio de su talla):\n{resumen}\n\n"
    if contexto:
        texto += f"CONTEXTO seleccionado por el usuario:\n{contexto}\n\n"
    texto += f"Pregunta del usuario: {question}"

    resultado = llm.invoke(
        [
            SystemMessage(content=prompts.SYSTEM_PROMPT),
            HumanMessage(content=texto),
        ]
    )
    return _extract_text(resultado)


def _extract_text(resultado) -> str:
    """Texto plano de la respuesta del modelo (algunos proveedores devuelven bloques)."""
    contenido = getattr(resultado, "content", resultado)
    if isinstance(contenido, str):
        return contenido.strip()
    if isinstance(contenido, list):
        partes: list[str] = []
        for bloque in contenido:
            if isinstance(bloque, str):
                partes.append(bloque)
            elif isinstance(bloque, dict):
                texto = bloque.get("text") or bloque.get("content")
                if isinstance(texto, str):
                    partes.append(texto)
        return "\n".join(partes).strip()
    return str(contenido).strip()


def _local_answer(state, question: str, scored: pd.DataFrame | None = None) -> str | None:
    """Respuesta precalculada del dataset para preguntas frecuentes.

    Devuelve ``None`` si la pregunta no está cubierta por los patrones; esas
    preguntas se atienden con el LLM.
    """
    df = scored if scored is not None else add_scores(state.kpis)
    q = _norm(question)

    def f(x, digits=1):
        txt = f"{x:,.{digits}f}"
        return txt.rstrip("0").rstrip(".") if "." in txt else txt

    med = df.median(numeric_only=True)
    mean = df.mean(numeric_only=True)

    # Ranking de empresas: va antes que cualquier media, porque "cuál empresa
    # tiene el salario/rotación más alta" pide el ranking y no el promedio.
    if re.search(r"empresa", q) and re.search(
        r"cual|que empresa|ranking|top|mayor|menor|mas|mejor|peor", q
    ) and not re.search(r"cuantas empresas|numero de empresas|total de empresas", q):
        ascendente = bool(re.search(r"menor|menos|mejor|mas baja|mas bajo", q)) and not re.search(
            r"mayor|mas alta|mas alto|peor", q
        )
        for patron, col, etiqueta, digitos, unidad, comparativos in METRICAS_RANKING:
            if not re.search(patron, q):
                continue
            filas = _ranking_empresas(df, col, ascendente=ascendente, n=5)
            if filas:
                return _fmt_ranking(
                    filas, etiqueta, comparativos[1] if ascendente else comparativos[0],
                    digitos, unidad, float(mean[col]) if col in mean else None,
                )

    # Salarios (antes que headcount: la pregunta suele decir "personal operativo")
    if re.search(r"salario|sueldo", q):
        return (
            f"Salario diario del personal operativo (mediana): inicial {f(med['salario_inicial'], 2)}, "
            f"intermedio bajo {f(med['salario_inter_bajo'], 2)}, intermedio alto {f(med['salario_inter_alto'], 2)} "
            f"y máximo {f(med['salario_maximo'], 2)} pesos/día."
        )

    # Motivos de baja (antes que "rotación|bajas": la pregunta suele decir "por qué")
    if re.search(r"motivo|por que|porque|causa|razon|abandon|renunci", q):
        motivos = _bajas_por_motivo(df)
        if motivos:
            total = sum(m["bajas"] for m in motivos)
            desglose = "; ".join(
                f"{m['etiqueta'].lower()} {f(m['pct'], 1)}% ({f(m['bajas'], 0)} bajas)"
                for m in motivos[:5]
            )
            principal = motivos[0]
            return (
                f"De {f(total, 0)} bajas con motivo declarado en los "
                f"{df['periodo'].nunique()} bimestres, la principal causa es "
                f"{principal['etiqueta'].lower()} ({f(principal['pct'], 1)}%, "
                f"{f(principal['bajas'], 0)} bajas). Desglose: {desglose}."
            )

    # Generación de edad de los trabajadores que se dieron de baja
    if re.search(r"generacion|gen z|millennial|baby|rango de edad|edad", q):
        generaciones = _bajas_por_generacion(df)
        if generaciones:
            desglose = "; ".join(
                f"{g['etiqueta'].lower()} {f(g['pct'], 1)}% ({f(g['bajas'], 0)} bajas)"
                for g in generaciones
            )
            principal = next((g for g in generaciones if g["etiqueta"] != "No medido"), generaciones[0])
            return (
                f"La generación más afectada por las bajas es {principal['etiqueta'].lower()} "
                f"con {f(principal['pct'], 1)}% de las bajas ponderadas. Desglose: {desglose}."
            )

    # Impacto de las bajas por bimestre
    if re.search(r"bajas|rotacion|renuncia", q) and re.search(
        r"bimestre|por periodo|cada periodo|evolucion|tendencia", q
    ):
        bimestres = _bajas_por_bimestre(df)
        if bimestres:
            detalle = "; ".join(
                f"{b['periodo']} {f(b['bajas'], 0)} bajas ({f(b['tasa_media'], 2)}%)"
                for b in bimestres
            )
            con_tasa = [b for b in bimestres if b["tasa_media"] is not None]
            peor = max(con_tasa, key=lambda b: b["tasa_media"]) if con_tasa else None
            extra = (
                f" El bimestre más afectado fue {peor['periodo']} "
                f"({f(peor['bajas'], 0)} bajas, tasa media {f(peor['tasa_media'], 2)}%)."
                if peor else ""
            )
            return f"Bajas por bimestre: {detalle}.{extra}"

    # Rotación
    if re.search(r"rotacion|bajas|renuncia", q):
        return (
            f"Rotación bimestral promedio: {f(mean['tasa_bajas_bimestral_pct'], 2)}% del headcount "
            f"(mediana {f(med['tasa_bajas_bimestral_pct'], 2)}%). "
            f"Bajas bimestrales promedio por empresa: {f(mean['total_bajas'], 1)}."
        )

    # Ausentismo / faltas
    if re.search(r"ausentismo|faltas|incapacidad", q):
        return (
            f"Faltas bimestrales promedio por empresa: {f(mean['total_faltas'], 0)} "
            f"(equivalente a {f(med['faltas_por_100'], 1)} faltas por cada 100 empleados). "
            f"Casos de incapacidad promedio: {f(mean['casos_incapacidad'], 0)}."
        )

    # Capacitación
    if re.search(r"capacitacion|cursos|entrenamiento", q):
        return (
            f"Horas de capacitación bimestral promedio: {f(mean['hrs_cap_operativos'], 0)} (operativos) "
            f"y {f(mean['hrs_cap_administrativos'], 0)} (administrativos)."
        )

    # Género
    if re.search(r"mujer|hombre|genero", q):
        return (
            f"Composición de género (mediana): {f(med['pct_mujeres'], 1)}% mujeres y "
            f"{f(med['pct_hombres'], 1)}% hombres."
        )

    # Sindicato
    if re.search(r"sindicato|sindical", q):
        si = int((df["tiene_sindicato"] == "Sí").sum())
        return f"{si} de {len(df)} registros ({si / len(df) * 100:.1f}%) cuentan con sindicato."

    # Competitividad / top
    if re.search(r"top|mejores|competitiv", q):
        top = df.sort_values("score_competitividad", ascending=False).head(5)
        lines = ["Top 5 por Índice SCORE:"]
        for _, r in top.iterrows():
            lines.append(
                f"- {r['empresa']} ({r['periodo']}): score {r['score_competitividad']:.1f}/100, "
                f"rotación {r['tasa_bajas_bimestral_pct']:.2f}%"
            )
        return "\n".join(lines)

    # Headcount
    if re.search(r"headcount|plantilla|empleados|personal", q):
        total = int(df["total_headcount"].sum())
        return (
            f"Headcount promedio por empresa: {f(med['total_headcount'], 0)} empleados "
            f"(mediana). Headcount total de la cohorte: {total:,} empleados. "
            f"Promedio operativos: {f(med['emp_operativos'], 0)} y administrativos: {f(med['emp_admin'], 0)}."
        )

    # Empresas / registros
    if re.search(r"cuantas empresas|numero de empresas|total de empresas", q):
        return (
            f"Hay {df['empresa'].nunique()} empresas participantes en "
            f"{df['periodo'].nunique()} bimestres ({len(df)} registros empresa-periodo)."
        )
    if re.search(r"cuantos registros|cuantos periodos", q):
        return f"Hay {len(df)} registros empresa-periodo en {df['periodo'].nunique()} bimestres."

    return None
