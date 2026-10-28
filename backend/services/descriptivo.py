# -*- coding: utf-8 -*-
"""Variables descriptivas del dataset que NO ponderan el Índice SCORE.

Permiten comparar condiciones laborales (descansos adicionales, vacaciones,
aguinaldo y prestaciones) entre empresas y bimestres sin alterar el score
del barómetro.
"""
from __future__ import annotations

import pandas as pd

from .barometro import add_scores
from .utils import jsonable

# Catálogo de variables comparables. `mejor` solo ordena la tabla; ninguna
# de estas variables entra en el cálculo de `score_competitividad`.
CATALOGO: tuple[dict, ...] = (
    {
        "clave": "dias_descanso_adicionales",
        "etiqueta": "Días de descanso adicionales",
        "grupo": "Días y prestaciones",
        "unidad": "días",
        "tipo": "numerica",
        "mejor": "alto",
        "descripcion": (
            "Días de descanso que la empresa otorga al personal operativo además "
            "de los festivos de ley."
        ),
    },
    {
        "clave": "vacaciones_1er_anio",
        "etiqueta": "Días de vacaciones (1.er año)",
        "grupo": "Días y prestaciones",
        "unidad": "días",
        "tipo": "numerica",
        "mejor": "alto",
        "descripcion": "Días de vacaciones que otorga al personal operativo en su primer año.",
    },
    {
        "clave": "aguinaldo_dias",
        "etiqueta": "Días de aguinaldo (1.er año)",
        "grupo": "Días y prestaciones",
        "unidad": "días",
        "tipo": "numerica",
        "mejor": "alto",
        "descripcion": "Días de aguinaldo que otorga al personal operativo en su primer año.",
    },
    {
        "clave": "prima_vacacional_pct",
        "etiqueta": "Prima vacacional",
        "grupo": "Días y prestaciones",
        "unidad": "%",
        "tipo": "numerica",
        "mejor": "alto",
        "descripcion": "Porcentaje de prima vacacional ofertado al personal operativo.",
    },
    {
        "clave": "vales_despensa_pct",
        "etiqueta": "Vales de despensa",
        "grupo": "Días y prestaciones",
        "unidad": "%",
        "tipo": "numerica",
        "mejor": "alto",
        "descripcion": "Porcentaje de vales de despensa ofertado al personal operativo.",
    },
    {
        "clave": "fondo_ahorro_pct",
        "etiqueta": "Fondo de ahorro",
        "grupo": "Días y prestaciones",
        "unidad": "%",
        "tipo": "numerica",
        "mejor": "alto",
        "descripcion": "Porcentaje de fondo de ahorro ofertado al personal operativo.",
    },
    {
        "clave": "descanso_jueves_santo",
        "etiqueta": "Jueves Santo",
        "grupo": "Descansos adicionales",
        "unidad": "",
        "tipo": "booleana",
        "mejor": "alto",
        "descripcion": "Otorga Jueves Santo como día de descanso adicional a los festivos de ley.",
    },
    {
        "clave": "descanso_viernes_santo",
        "etiqueta": "Viernes Santo",
        "grupo": "Descansos adicionales",
        "unidad": "",
        "tipo": "booleana",
        "mejor": "alto",
        "descripcion": "Otorga Viernes Santo como día de descanso adicional a los festivos de ley.",
    },
    {
        "clave": "descanso_10_mayo",
        "etiqueta": "10 de mayo",
        "grupo": "Descansos adicionales",
        "unidad": "",
        "tipo": "booleana",
        "mejor": "alto",
        "descripcion": "Otorga el 10 de mayo como día de descanso adicional.",
    },
    {
        "clave": "descanso_15_septiembre",
        "etiqueta": "15 de septiembre",
        "grupo": "Descansos adicionales",
        "unidad": "",
        "tipo": "booleana",
        "mejor": "alto",
        "descripcion": "Otorga el 15 de septiembre como día de descanso adicional.",
    },
    {
        "clave": "descanso_2_noviembre",
        "etiqueta": "2 de noviembre",
        "grupo": "Descansos adicionales",
        "unidad": "",
        "tipo": "booleana",
        "mejor": "alto",
        "descripcion": "Otorga el 2 de noviembre como día de descanso adicional.",
    },
    {
        "clave": "descanso_12_diciembre",
        "etiqueta": "12 de diciembre",
        "grupo": "Descansos adicionales",
        "unidad": "",
        "tipo": "booleana",
        "mejor": "alto",
        "descripcion": "Otorga el 12 de diciembre como día de descanso adicional.",
    },
    {
        "clave": "descanso_24_diciembre",
        "etiqueta": "24 de diciembre",
        "grupo": "Descansos adicionales",
        "unidad": "",
        "tipo": "booleana",
        "mejor": "alto",
        "descripcion": "Otorga el 24 de diciembre como día de descanso adicional.",
    },
    {
        "clave": "descanso_31_diciembre",
        "etiqueta": "31 de diciembre",
        "grupo": "Descansos adicionales",
        "unidad": "",
        "tipo": "booleana",
        "mejor": "alto",
        "descripcion": "Otorga el 31 de diciembre como día de descanso adicional.",
    },
    {
        "clave": "descanso_matrimonio",
        "etiqueta": "Matrimonio",
        "grupo": "Descansos adicionales",
        "unidad": "",
        "tipo": "booleana",
        "mejor": "alto",
        "descripcion": "Otorga permiso por matrimonio.",
    },
    {
        "clave": "descanso_nacimiento",
        "etiqueta": "Nacimiento de un hijo",
        "grupo": "Descansos adicionales",
        "unidad": "",
        "tipo": "booleana",
        "mejor": "alto",
        "descripcion": "Otorga permiso por nacimiento de un hijo.",
    },
    {
        "clave": "descanso_defuncion",
        "etiqueta": "Defunción de un familiar",
        "grupo": "Descansos adicionales",
        "unidad": "",
        "tipo": "booleana",
        "mejor": "alto",
        "descripcion": "Otorga permiso por defunción de un familiar.",
    },
)

ORDEN_TALLA = ["Micro", "Pequeña", "Mediana", "Grande"]


def _num(value, digits: int = 2) -> float | None:
    if value is None or pd.isna(value):
        return None
    return round(float(value), digits)


def _meta(clave: str | None) -> dict:
    for item in CATALOGO:
        if item["clave"] == clave:
            return item
    return CATALOGO[0]


def _valores(df: pd.DataFrame, meta: dict) -> pd.Series:
    """Serie lista para comparar (numérica o booleana según la variable)."""
    if meta["tipo"] == "booleana":
        return df[meta["clave"]].fillna(False).astype(bool)
    return pd.to_numeric(df[meta["clave"]], errors="coerce")


def _resumen(valores: pd.Series, meta: dict) -> dict:
    """Estadísticos de la variable sobre un conjunto de empresas."""
    if meta["tipo"] == "booleana":
        total = int(len(valores))
        otorgan = int(valores.sum())
        return {
            "n": total,
            "otorgan": otorgan,
            "otorgan_pct": round(otorgan / total * 100, 1) if total else None,
        }

    s = valores.dropna()
    if s.empty:
        return {"n": 0, "cobertura_pct": None, "mediana": None, "promedio": None,
                "p25": None, "p75": None, "min": None, "max": None}
    return {
        "n": int(len(s)),
        "cobertura_pct": round(len(s) / len(valores) * 100, 1) if len(valores) else None,
        "mediana": _num(s.median()),
        "promedio": _num(s.mean()),
        "p25": _num(s.quantile(0.25)),
        "p75": _num(s.quantile(0.75)),
        "min": _num(s.min()),
        "max": _num(s.max()),
    }


def _por_talla(df: pd.DataFrame, meta: dict) -> list[dict]:
    valores = _valores(df, meta)
    rows = [
        {"talla": talla, **_resumen(valores.loc[idx], meta)}
        for talla, idx in df.groupby("talla").groups.items()
    ]
    rows.sort(key=lambda r: ORDEN_TALLA.index(r["talla"]) if r["talla"] in ORDEN_TALLA else 99)
    return rows


def _por_periodo(df: pd.DataFrame, meta: dict) -> list[dict]:
    valores = _valores(df, meta)
    rows = [
        {"periodo": periodo, "periodo_num": int(num), **_resumen(valores.loc[idx], meta)}
        for (periodo, num), idx in df.groupby(["periodo", "periodo_num"]).groups.items()
    ]
    rows.sort(key=lambda r: r["periodo_num"])
    return rows


def _empresas(df: pd.DataFrame, meta: dict) -> list[dict]:
    """Fila por empresa-periodo con su valor y la referencia de su talla."""
    valores = _valores(df, meta)
    es_numerica = meta["tipo"] == "numerica"

    if es_numerica:
        mediana_talla = valores.groupby(df["talla"]).median()
        percentil = valores.rank(pct=True) * 100
    else:
        pct_talla = valores.groupby(df["talla"]).mean() * 100

    out = []
    for idx, row in df.iterrows():
        talla = row["talla"]
        item = {
            "empresa": row["empresa"],
            "periodo": row["periodo"],
            "talla": talla,
            "score_competitividad": _num(row["score_competitividad"], 1),
            "valor": None,
            "otorga": None,
            "mediana_talla": None,
            "diferencia": None,
            "diferencia_pct": None,
            "percentil": None,
            "pct_talla": None,
        }

        if es_numerica:
            valor = valores.loc[idx]
            referencia = mediana_talla.get(talla)
            item["valor"] = _num(valor)
            item["mediana_talla"] = _num(referencia)
            item["percentil"] = _num(percentil.loc[idx], 1) if pd.notna(valor) else None
            if pd.notna(valor) and pd.notna(referencia) and referencia:
                item["diferencia"] = _num(valor - referencia)
                item["diferencia_pct"] = _num((valor - referencia) / referencia * 100, 1)
        else:
            item["otorga"] = bool(valores.loc[idx])
            item["pct_talla"] = _num(pct_talla.get(talla), 1)

        out.append(item)

    if es_numerica:
        descendente = meta.get("mejor", "alto") == "alto"
        out.sort(
            key=lambda r: (r["valor"] is None, -(r["valor"] or 0) if descendente else (r["valor"] or 0))
        )
    else:
        out.sort(key=lambda r: (not r["otorga"], r["empresa"]))
    return out


def catalogo(df: pd.DataFrame) -> list[dict]:
    """Variables comparables disponibles con un resumen de una línea."""
    items = []
    for meta in CATALOGO:
        if meta["clave"] not in df.columns:
            continue
        resumen = _resumen(_valores(df, meta), meta)
        if meta["tipo"] == "numerica":
            mediana = resumen["mediana"]
            resumen_texto = (
                f"mediana {mediana:g} {meta['unidad']}".strip() if mediana is not None else "sin datos"
            )
        else:
            pct = resumen["otorgan_pct"]
            resumen_texto = f"{pct:g}% de las empresas" if pct is not None else "sin datos"
        items.append({**meta, "resumen": resumen_texto})
    return items


def comparativa(
    df: pd.DataFrame,
    variable: str | None = None,
    periodo: str | None = None,
    talla: str | None = None,
) -> dict:
    """Comparación de una variable descriptiva entre empresas del mismo corte.

    Si no se indica `periodo`, se compara el último bimestre disponible.
    """
    scored = add_scores(df)
    meta = _meta(variable)

    ultimo_num = int(scored["periodo_num"].max())
    if periodo and (scored["periodo"] == periodo).any():
        periodo_num = int(scored.loc[scored["periodo"] == periodo, "periodo_num"].iloc[0])
        periodo_efectivo = periodo
    else:
        periodo_num = ultimo_num
        periodo_efectivo = str(scored.loc[scored["periodo_num"] == ultimo_num, "periodo"].iloc[0])

    del_periodo = scored[scored["periodo_num"] == periodo_num]
    talla_aplicada = talla if talla and (scored["talla"] == talla).any() else None
    cohorte = del_periodo[del_periodo["talla"] == talla_aplicada] if talla_aplicada else del_periodo
    if cohorte.empty:
        cohorte = del_periodo

    por_talla = _por_talla(del_periodo, meta)
    por_periodo = _por_periodo(
        scored[scored["talla"] == talla_aplicada] if talla_aplicada else scored,
        meta,
    )

    return jsonable({
        "variable": meta,
        "periodo_efectivo": periodo_efectivo,
        "talla": talla_aplicada,
        "resumen": _resumen(_valores(cohorte, meta), meta),
        "por_talla": por_talla,
        "por_periodo": por_periodo,
        "empresas": _empresas(cohorte, meta),
        "variables": catalogo(scored),
    })
