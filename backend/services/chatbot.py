# -*- coding: utf-8 -*-
"""Asistente IA (chat): agente LangChain sobre el DataFrame + fallback local."""
from __future__ import annotations

import re

import pandas as pd

from ..core import config, prompts
from .barometro import add_scores
from .utils import jsonable


def _agent_df(state) -> pd.DataFrame:
    """DataFrame reducido y legible que consume el agente."""
    df = state.kpis.copy()
    # Solo se añade el score; el resto de columnas conserva valores reales (con
    # nulos) para que los promedios coincidan con el dashboard.
    df["score_competitividad"] = add_scores(state.kpis)["score_competitividad"]
    cols = [
        "periodo", "empresa", "tiene_sindicato",
        "emp_operativos", "emp_admin", "emp_otros", "total_headcount",
        "pct_mujeres", "pct_hombres",
        "gen_baby_boomers", "gen_x", "gen_millennial_30_37",
        "gen_millennial_23_29", "gen_z",
        "salario_inicial", "salario_inter_bajo", "salario_inter_alto",
        "salario_maximo", "salario_medio",
        "total_bajas", "tasa_bajas_bimestral_pct",
        "rot_vol_operativa", "rot_invol_operativa", "rot_vol_admin", "rot_invol_admin",
        "total_faltas", "faltas_por_100", "casos_incapacidad",
        "hrs_cap_operativos", "hrs_cap_administrativos",
        "score_competitividad",
    ]
    return df[cols]


def query(state, question: str) -> dict:
    """Responde una pregunta en lenguaje natural."""
    question = (question or "").strip()
    if not question:
        return {"answer": prompts.FALLBACK_HELP, "engine": "local"}

    if config.OPENAI_API_KEY:
        try:
            answer = _llm_query(state, question)
            return {"answer": answer, "engine": "llm"}
        except Exception as exc:  # noqa: BLE001 — nunca debe romper la demo
            fallback = _fallback(state, question)
            return {
                "answer": f"{fallback}\n\n_(Agente LLM no disponible: {exc})_",
                "engine": "local",
            }

    return {"answer": _fallback(state, question), "engine": "local"}


def _llm_query(state, question: str) -> str:
    """Consulta vía LangChain Pandas DataFrame Agent (requiere OPENAI_API_KEY)."""
    from langchain_openai import ChatOpenAI

    try:
        from langchain_experimental.agents import create_pandas_dataframe_agent
    except ImportError:  # pragma: no cover
        from langchain_classic.agents import create_pandas_dataframe_agent

    df = _agent_df(state)
    llm_kwargs = {
        "model": config.OPENAI_MODEL,
        "temperature": 0,
        "api_key": config.OPENAI_API_KEY,
    }
    base_url = config.OPENAI_BASE_URL
    if not base_url and "deepseek" in config.OPENAI_MODEL.lower():
        base_url = config.DEEPSEEK_BASE_URL
    if base_url:
        llm_kwargs["base_url"] = base_url

    llm = ChatOpenAI(**llm_kwargs)

    agent_kwargs = dict(
        llm=llm,
        df=df,
        verbose=False,
        allow_dangerous_code=True,
        prefix=prompts.SYSTEM_PROMPT,
        number_of_head_rows=5,
        include_df_in_prompt=False,
        agent_executor_kwargs={"handle_parsing_errors": True},
    )
    try:
        agent = create_pandas_dataframe_agent(agent_type="tool-calling", **agent_kwargs)
    except (TypeError, ValueError):
        agent = create_pandas_dataframe_agent(**agent_kwargs)

    result = agent.invoke({"input": question})
    if isinstance(result, dict) and "output" in result:
        return str(result["output"])
    return str(result)


def _norm(text: str) -> str:
    """Normaliza acentos y minúsculas para el pattern matching."""
    replacements = {"á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u", "ñ": "n"}
    t = text.lower().strip()
    for a, b in replacements.items():
        t = t.replace(a, b)
    return t


def _fallback(state, question: str) -> str:
    """Respuestas cuantitativas sin LLM (patrones sobre métricas clave)."""
    df = add_scores(state.kpis)
    q = _norm(question)

    def f(x, digits=1):
        return f"{x:,.{digits}f}".rstrip("0").rstrip(".")

    med = df.median(numeric_only=True)
    mean = df.mean(numeric_only=True)

    # Empresas / registros
    if re.search(r"cuantas empresas|numero de empresas|total de empresas", q):
        return (
            f"Hay {df['empresa'].nunique()} empresas participantes en "
            f"{df['periodo'].nunique()} bimestres ({len(df)} registros empresa-periodo)."
        )
    if re.search(r"cuantos registros|cuantos periodos", q):
        return f"Hay {len(df)} registros empresa-periodo en {df['periodo'].nunique()} bimestres."

    # Headcount
    if re.search(r"headcount|plantilla|empleados|personal", q):
        total = int(df["total_headcount"].sum())
        return (
            f"Headcount promedio por empresa: {f(med['total_headcount'], 0)} empleados "
            f"(mediana). Headcount total de la cohorte: {total:,} empleados. "
            f"Promedio operativos: {f(med['emp_operativos'], 0)} y administrativos: {f(med['emp_admin'], 0)}."
        )

    # Salarios
    if re.search(r"salario|sueldo", q):
        return (
            f"Salario diario del personal operativo (mediana): inicial {f(med['salario_inicial'], 2)}, "
            f"intermedio bajo {f(med['salario_inter_bajo'], 2)}, intermedio alto {f(med['salario_inter_alto'], 2)} "
            f"y máximo {f(med['salario_maximo'], 2)} pesos/día."
        )

    # Rotación
    if re.search(r"rotacion|rotacion|bajas|renuncia", q):
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

    # Competitividad / top
    if re.search(r"top|mejores|competitiv", q):
        top = df.sort_values("score_competitividad", ascending=False).head(5)
        lines = ["Top 5 por índice de competitividad:"]
        for _, r in top.iterrows():
            lines.append(
                f"- {r['empresa']} ({r['periodo']}): score {r['score_competitividad']:.1f}/100, "
                f"rotación {r['tasa_bajas_bimestral_pct']:.2f}%"
            )
        return "\n".join(lines)

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

    return prompts.FALLBACK_HELP
