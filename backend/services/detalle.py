# -*- coding: utf-8 -*-
"""Ficha detallada por empresa: datos estructurados para reportes y chatbot.

A partir del diccionario de datos se agrupan las variables relevantes de la
encuesta en secciones que una consultoría consideraría importantes (headcount
y demografía, salarios, rotación y bajas, ausentismo, capacitación,
prestaciones y competitividad). La misma estructura alimenta:

- El reporte detallado (HTML/PDF) con la referencia de la talla.
- La ``ficha`` de texto que el chatbot adjunta automáticamente cuando el
  usuario menciona una empresa, para responder en una sola llamada sin iterar.
"""
from __future__ import annotations

import pandas as pd

from .barometro import add_scores
from .utils import jsonable

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

ANTIGUEDAD_BAJAS = {
    "antig_bajas_0_1mes": "0 a 1 mes",
    "antig_bajas_1_3meses": "1 a 3 meses",
    "antig_bajas_3_12meses": "3 a 12 meses",
    "antig_bajas_1_3anios": "1 a 3 años",
    "antig_bajas_mas_3anios": "Más de 3 años",
    "antig_bajas_no_medido": "No medido",
}

EDAD_BAJAS = {
    "edad_bajas_gen_z": "Gen Z",
    "edad_bajas_millennial_23_30": "Millennial 23-30",
    "edad_bajas_millennial_31_37": "Millennial 31-37",
    "edad_bajas_gen_x": "Gen X",
    "edad_bajas_baby_boomers": "Baby Boomers",
    "edad_bajas_no_medido": "No medido",
}

INCAPACIDADES = {
    "incap_riesgo_trabajo": "Riesgo de trabajo",
    "incap_enfermedad_general": "Enfermedad general",
    "incap_maternidad": "Maternidad",
    "incap_temporal": "Temporal",
    "incap_permanente_parcial": "Permanente parcial",
    "incap_permanente_total": "Permanente total",
}

DESCANSOS = {
    "descanso_jueves_santo": "Jueves Santo",
    "descanso_viernes_santo": "Viernes Santo",
    "descanso_10_mayo": "10 de mayo",
    "descanso_15_septiembre": "15 de septiembre",
    "descanso_2_noviembre": "2 de noviembre",
    "descanso_12_diciembre": "12 de diciembre",
    "descanso_24_diciembre": "24 de diciembre",
    "descanso_31_diciembre": "31 de diciembre",
    "descanso_matrimonio": "Matrimonio",
    "descanso_nacimiento": "Nacimiento de un hijo",
    "descanso_defuncion": "Defunción de un familiar",
}

# Columnas numéricas cuyo "referencia de talla" es la mediana dentro de la talla.
BENCH_NUMERIC = (
    ["total_headcount", "emp_operativos", "emp_admin", "emp_otros", "pct_mujeres", "pct_hombres"]
    + SALARY_COLS
    + ["salario_medio", "tasa_bajas_bimestral_pct",
       "faltas_por_100", "cap_por_empleado", "hrs_cap_operativos", "hrs_cap_administrativos",
       "vales_despensa_pct", "fondo_ahorro_pct", "prima_vacacional_pct",
       "vacaciones_1er_anio", "aguinaldo_dias", "dias_descanso_adicionales"]
)

# Rotaciones mensuales capturadas como fracción (0.0-1.0): se muestran en %.
ROTACION_FRACCION = [
    "rotacion_mensual_promedio", "rot_vol_operativa", "rot_invol_operativa",
    "rot_vol_admin", "rot_invol_admin",
]

# Generaciones: se normalizan a participación porcentual (suman 100).
GEN_COLS = ["gen_baby_boomers", "gen_x", "gen_millennial_23_29", "gen_millennial_30_37", "gen_z"]

# Sub-indicadores y score solo existen en el DataFrame con `add_scores`.
BENCH_SCORE = [
    "score_competitividad", "sub_salario", "sub_retencion",
    "sub_ausentismo", "sub_capacitacion", "sub_equilibrio",
]

# Columnas booleanas cuyo "referencia de talla" es el % de empresas de la talla que otorgan.
BENCH_BOOL = list(DESCANSOS)


# ---------------------------------------------------------------------------
# Filtrado y agregaciones
# ---------------------------------------------------------------------------
def _filter(df: pd.DataFrame, empresa: str | None, periodos: list[str] | None) -> pd.DataFrame:
    out = df.copy()
    if empresa:
        out = out[out["empresa"] == empresa]
    if periodos:
        out = out[out["periodo"].isin(periodos)]
    return out.sort_values(["periodo_num", "empresa"])


def _num(value, digits: int = 2) -> float | None:
    if value is None or pd.isna(value):
        return None
    return round(float(value), digits)


def _med(series: pd.Series) -> float | None:
    s = pd.to_numeric(series, errors="coerce").dropna()
    return float(s.median()) if not s.empty else None


def _mean(series: pd.Series) -> float | None:
    s = pd.to_numeric(series, errors="coerce").dropna()
    return float(s.mean()) if not s.empty else None


def _sum(series: pd.Series) -> float | None:
    s = pd.to_numeric(series, errors="coerce").dropna()
    return float(s.sum()) if not s.empty else None


def _porc(value) -> float | None:
    """Convierte una fracción (0-1) a porcentaje; None si no hay dato."""
    if value is None or pd.isna(value):
        return None
    return round(float(value) * 100, 2)


def _talla_de(df: pd.DataFrame) -> str:
    tallas = df["talla"].dropna()
    if tallas.empty:
        return "—"
    return str(tallas.mode().iloc[0])


def _benchmarks(base: pd.DataFrame, full: pd.DataFrame) -> dict[str, dict[str, float]]:
    """Referencias de talla: mediana (o % que otorga) dentro de cada talla."""
    out: dict[str, dict[str, float]] = {}
    b = base.copy()
    b["talla"] = full["talla"].values

    for col in BENCH_NUMERIC:
        if col in b.columns:
            out[col] = b.groupby("talla")[col].median().to_dict()

    # Rotaciones mensuales en fracción -> porcentaje.
    for col in ROTACION_FRACCION:
        if col in b.columns:
            out[col] = (b.groupby("talla")[col].median() * 100).to_dict()

    # Generaciones normalizadas a participación porcentual (suman 100).
    g = b[GEN_COLS].apply(pd.to_numeric, errors="coerce")
    total_gen = g.sum(axis=1)
    gen_shares = g.div(total_gen, axis=0) * 100
    gen_shares["talla"] = b["talla"]
    for col in GEN_COLS:
        out[col] = gen_shares.groupby("talla")[col].median().to_dict()

    for col in BENCH_SCORE:
        if col in full.columns:
            out[col] = full.groupby("talla")[col].median().to_dict()

    for col in BENCH_BOOL:
        if col in b.columns:
            serie = pd.to_numeric(b[col], errors="coerce").fillna(0).astype(bool)
            out[col] = (serie.groupby(b["talla"]).mean() * 100).to_dict()
    return out


def _bench(bench: dict, col: str, talla: str) -> float | None:
    return _num(bench.get(col, {}).get(talla))


def _pct(parte: float | None, total: float | None) -> float | None:
    if parte is None or total is None or total == 0:
        return None
    return round(parte / total * 100, 1)


def _genero_split(df: pd.DataFrame) -> tuple[float | None, float | None]:
    """(mujeres %, hombres %) con datos saneados; None donde no hay dato."""
    mujeres = _med(df["pct_mujeres"])
    hombres = _med(df["pct_hombres"])
    if mujeres is None and hombres is not None and 0 <= 100 - hombres <= 100:
        mujeres = 100 - hombres
    if hombres is None and mujeres is not None and 0 <= 100 - mujeres <= 100:
        hombres = 100 - mujeres
    return mujeres, hombres


def _gen_shares(base: pd.DataFrame) -> pd.DataFrame:
    """Participación porcentual de cada generación (las filas suman 100)."""
    g = base[GEN_COLS].apply(pd.to_numeric, errors="coerce")
    total = g.sum(axis=1)
    shares = g.div(total, axis=0) * 100
    shares["millennials"] = shares["gen_millennial_23_29"] + shares["gen_millennial_30_37"]
    return shares


# ---------------------------------------------------------------------------
# Construcción del perfil
# ---------------------------------------------------------------------------
def _fila(etiqueta: str, valor, tipo: str = "num", unidad: str = "", cohorte=None,
          desglose: list[dict] | None = None) -> dict:
    return {
        "etiqueta": etiqueta,
        "valor": valor,
        "tipo": tipo,
        "unidad": unidad,
        "cohorte": cohorte,
        "desglose": desglose,
    }


def _desglose_sumas(df: pd.DataFrame, columnas: dict[str, str], total_col: str) -> list[dict]:
    total = _sum(df[total_col])
    filas = []
    for col, etiqueta in columnas.items():
        if col not in df.columns:
            continue
        valor = _sum(df[col])
        filas.append({
            "etiqueta": etiqueta,
            "valor": _num(valor, 0),
            "unidad": "bajas" if total_col == "total_bajas" else "casos",
            "pct": _pct(valor, total),
        })
    filas.sort(key=lambda r: (r["valor"] is None, -(r["valor"] or 0)))
    return filas


def perfil(state, empresa: str | None = None, periodos: list[str] | None = None) -> dict:
    """Perfil detallado (estructurado) de una empresa o de la cohorte completa."""
    base = state.kpis
    if _filter(base, empresa, periodos).empty:
        raise ValueError("No hay datos para la combinación de empresa y bimestres elegida.")

    # Talla y sub-indicadores sobre la cohorte completa (comparación entre
    # pares de la misma talla); la demografía se lee del dataset saneado.
    full = add_scores(base)
    df = _filter(full, empresa, periodos)
    df_base = _filter(base, empresa, periodos)
    bench = _benchmarks(base, full)
    gen_shares = _gen_shares(base)
    idx = df_base.index

    talla = _talla_de(df)
    n_bimestres = int(df["periodo"].nunique())
    periodos_unicos = (
        df[["periodo", "periodo_num"]]
        .drop_duplicates()
        .sort_values("periodo_num")["periodo"]
        .tolist()
    )

    tiene_sindicato = (
        df["tiene_sindicato"].astype(str).str.lower().isin(["sí", "si"]).any()
    )
    mujeres, hombres = _genero_split(df_base)
    gen_millennials = _num(
        (_bench(bench, "gen_millennial_23_29", talla) or 0)
        + (_bench(bench, "gen_millennial_30_37", talla) or 0)
    )

    secciones: list[dict] = []

    # --- Identificación -----------------------------------------------------
    secciones.append({
        "titulo": "Identificación y perfil",
        "filas": [
            _fila("Empresa", empresa or "Cohorte completa", "texto"),
            _fila("Talla", talla, "texto"),
            _fila("Bimestres analizados", n_bimestres, "int", "bimestres"),
            _fila("Periodo", f"{periodos_unicos[0]} → {periodos_unicos[-1]}", "texto"),
            _fila("Sindicato", "Sí" if tiene_sindicato else "No", "texto"),
        ],
    })

    # --- Headcount y demografía --------------------------------------------
    secciones.append({
        "titulo": "Headcount y demografía",
        "filas": [
            _fila("Headcount (mediana por bimestre)", _med(df_base["total_headcount"]), "int",
                  "empleados", _bench(bench, "total_headcount", talla)),
            _fila("Personal operativo", _med(df_base["emp_operativos"]), "int",
                  "empleados", _bench(bench, "emp_operativos", talla)),
            _fila("Personal administrativo", _med(df_base["emp_admin"]), "int",
                  "empleados", _bench(bench, "emp_admin", talla)),
            _fila("Otro personal", _med(df_base["emp_otros"]), "int",
                  "empleados", _bench(bench, "emp_otros", talla)),
            _fila("Mujeres", mujeres, "pct", "%",
                  _bench(bench, "pct_mujeres", talla)),
            _fila("Hombres", hombres, "pct", "%",
                  _bench(bench, "pct_hombres", talla)),
            _fila("Baby Boomers", _med(gen_shares.loc[idx, "gen_baby_boomers"]), "pct", "%",
                  _bench(bench, "gen_baby_boomers", talla)),
            _fila("Generación X", _med(gen_shares.loc[idx, "gen_x"]), "pct", "%",
                  _bench(bench, "gen_x", talla)),
            _fila("Millennials", _med(gen_shares.loc[idx, "millennials"]), "pct", "%",
                  gen_millennials),
            _fila("Generación Z", _med(gen_shares.loc[idx, "gen_z"]), "pct", "%",
                  _bench(bench, "gen_z", talla)),
        ],
    })

    # --- Salarios -----------------------------------------------------------
    secciones.append({
        "titulo": "Salarios y estructura salarial",
        "filas": [
            _fila("Salario inicial", _med(df["salario_inicial"]), "num", "MXN/día",
                  _bench(bench, "salario_inicial", talla)),
            _fila("Salario intermedio bajo", _med(df["salario_inter_bajo"]), "num", "MXN/día",
                  _bench(bench, "salario_inter_bajo", talla)),
            _fila("Salario intermedio alto", _med(df["salario_inter_alto"]), "num", "MXN/día",
                  _bench(bench, "salario_inter_alto", talla)),
            _fila("Salario máximo", _med(df["salario_maximo"]), "num", "MXN/día",
                  _bench(bench, "salario_maximo", talla)),
            _fila("Salario medio", _med(df["salario_medio"]), "num", "MXN/día",
                  _bench(bench, "salario_medio", talla)),
        ],
    })

    # --- Rotación y bajas ---------------------------------------------------
    total_bajas = _sum(df["total_bajas"])
    motivos = _desglose_sumas(df, MOTIVOS_BAJA, "total_bajas")
    antiguedad = _desglose_sumas(df, ANTIGUEDAD_BAJAS, "total_bajas")
    edades = _desglose_sumas(df, EDAD_BAJAS, "total_bajas")
    secciones.append({
        "titulo": "Rotación y bajas",
        "filas": [
            _fila("Tasa de rotación bimestral", _mean(df["tasa_bajas_bimestral_pct"]), "pct", "%",
                  _bench(bench, "tasa_bajas_bimestral_pct", talla)),
            _fila("Rotación mensual promedio", _porc(_mean(df["rotacion_mensual_promedio"])), "pct", "%",
                  _bench(bench, "rotacion_mensual_promedio", talla)),
            _fila("Total de bajas", _num(total_bajas, 0), "int", "bajas"),
            _fila("Bajas personal operativo", _sum(df["bajas_operativo"]), "int", "bajas"),
            _fila("Bajas personal administrativo", _sum(df["bajas_administrativo"]), "int", "bajas"),
            _fila("Rotación voluntaria operativa", _porc(_mean(df["rot_vol_operativa"])), "pct", "%",
                  _bench(bench, "rot_vol_operativa", talla)),
            _fila("Rotación involuntaria operativa", _porc(_mean(df["rot_invol_operativa"])), "pct", "%",
                  _bench(bench, "rot_invol_operativa", talla)),
            _fila("Rotación voluntaria administrativa", _porc(_mean(df["rot_vol_admin"])), "pct", "%",
                  _bench(bench, "rot_vol_admin", talla)),
            _fila("Rotación involuntaria administrativa", _porc(_mean(df["rot_invol_admin"])), "pct", "%",
                  _bench(bench, "rot_invol_admin", talla)),
            _fila("Bajas por motivo", _num(total_bajas, 0), "int", "bajas", desglose=motivos),
            _fila("Bajas por antigüedad", _num(total_bajas, 0), "int", "bajas", desglose=antiguedad),
            _fila("Bajas por edad", _num(total_bajas, 0), "int", "bajas", desglose=edades),
        ],
    })

    # --- Ausentismo e incapacidades ----------------------------------------
    total_faltas = _sum(df["total_faltas"])
    faltas_desglose = [
        {"etiqueta": "Justificadas operativo", "valor": _num(_sum(df["faltas_oper_justificadas"]), 0),
         "unidad": "faltas", "pct": _pct(_sum(df["faltas_oper_justificadas"]), total_faltas)},
        {"etiqueta": "Injustificadas operativo", "valor": _num(_sum(df["faltas_oper_injustificadas"]), 0),
         "unidad": "faltas", "pct": _pct(_sum(df["faltas_oper_injustificadas"]), total_faltas)},
        {"etiqueta": "Justificadas administrativo", "valor": _num(_sum(df["faltas_admin_justificadas"]), 0),
         "unidad": "faltas", "pct": _pct(_sum(df["faltas_admin_justificadas"]), total_faltas)},
        {"etiqueta": "Injustificadas administrativo", "valor": _num(_sum(df["faltas_admin_injustificadas"]), 0),
         "unidad": "faltas", "pct": _pct(_sum(df["faltas_admin_injustificadas"]), total_faltas)},
    ]
    casos_incapacidad = _sum(df["casos_incapacidad"])
    incapacidades = _desglose_sumas(df, INCAPACIDADES, "casos_incapacidad")
    secciones.append({
        "titulo": "Ausentismo e incapacidades",
        "filas": [
            _fila("Total de faltas", _num(total_faltas, 0), "int", "faltas"),
            _fila("Faltas por cada 100 empleados", _med(df_base["faltas_por_100"]), "num",
                  "faltas/100", _bench(bench, "faltas_por_100", talla)),
            _fila("Ausencias por incapacidad operativo", _sum(df["aus_oper_incapacidad"]), "int", "días"),
            _fila("Ausencias por incapacidad administrativo", _sum(df["aus_admin_incapacidad"]), "int", "días"),
            _fila("Faltas por tipo", _num(total_faltas, 0), "int", "faltas", desglose=faltas_desglose),
            _fila("Casos de incapacidad", _num(casos_incapacidad, 0), "int", "casos"),
            _fila("Incapacidades por tipo", _num(casos_incapacidad, 0), "int", "casos",
                  desglose=incapacidades),
        ],
    })

    # --- Capacitación -------------------------------------------------------
    hrs_oper = _sum(df["hrs_cap_operativos"])
    hrs_admin = _sum(df["hrs_cap_administrativos"])
    secciones.append({
        "titulo": "Capacitación y desarrollo",
        "filas": [
            _fila("Horas operativos (mediana por bimestre)", _med(df_base["hrs_cap_operativos"]),
                  "int", "horas", _bench(bench, "hrs_cap_operativos", talla)),
            _fila("Horas administrativos (mediana por bimestre)", _med(df_base["hrs_cap_administrativos"]),
                  "int", "horas", _bench(bench, "hrs_cap_administrativos", talla)),
            _fila("Horas totales (suma del periodo)", _num((hrs_oper or 0) + (hrs_admin or 0), 0),
                  "int", "horas"),
            _fila("Horas por empleado", _med(df_base["cap_por_empleado"]), "num", "horas/empleado",
                  _bench(bench, "cap_por_empleado", talla)),
        ],
    })

    # --- Prestaciones -------------------------------------------------------
    descansos_otorgados = [
        {"etiqueta": etiqueta, "valor": "Sí" if df[col].fillna(0).astype(bool).any() else "No",
         "unidad": "", "pct": _bench(bench, col, talla)}
        for col, etiqueta in DESCANSOS.items() if col in df.columns
    ]
    secciones.append({
        "titulo": "Prestaciones y condiciones",
        "filas": [
            _fila("Vacaciones (1.er año)", _med(df["vacaciones_1er_anio"]), "num", "días",
                  _bench(bench, "vacaciones_1er_anio", talla)),
            _fila("Aguinaldo", _med(df["aguinaldo_dias"]), "num", "días",
                  _bench(bench, "aguinaldo_dias", talla)),
            _fila("Prima vacacional", _med(df["prima_vacacional_pct"]), "pct", "%",
                  _bench(bench, "prima_vacacional_pct", talla)),
            _fila("Vales de despensa", _med(df["vales_despensa_pct"]), "pct", "%",
                  _bench(bench, "vales_despensa_pct", talla)),
            _fila("Fondo de ahorro", _med(df["fondo_ahorro_pct"]), "pct", "%",
                  _bench(bench, "fondo_ahorro_pct", talla)),
            _fila("Días de descanso adicionales", _med(df["dias_descanso_adicionales"]), "num", "días",
                  _bench(bench, "dias_descanso_adicionales", talla)),
            _fila("Descansos adicionales otorgados", None, "desglose", "", desglose=descansos_otorgados),
        ],
    })

    # --- Competitividad -----------------------------------------------------
    score = _mean(df["score_competitividad"])
    secciones.append({
        "titulo": "Competitividad (barómetro)",
        "filas": [
            _fila("Índice de competitividad", score, "num", "/100",
                  _bench(bench, "score_competitividad", talla)),
            _fila("Sub-indicador salario", _mean(df["sub_salario"]), "num", "/100",
                  _bench(bench, "sub_salario", talla)),
            _fila("Sub-indicador retención", _mean(df["sub_retencion"]), "num", "/100",
                  _bench(bench, "sub_retencion", talla)),
            _fila("Sub-indicador ausentismo", _mean(df["sub_ausentismo"]), "num", "/100",
                  _bench(bench, "sub_ausentismo", talla)),
            _fila("Sub-indicador capacitación", _mean(df["sub_capacitacion"]), "num", "/100",
                  _bench(bench, "sub_capacitacion", talla)),
            _fila("Sub-indicador equilibrio de género", _mean(df["sub_equilibrio"]), "num", "/100",
                  _bench(bench, "sub_equilibrio", talla)),
        ],
    })

    return jsonable({
        "empresa": empresa,
        "talla": talla,
        "periodos": periodos_unicos,
        "registros": int(len(df)),
        "secciones": secciones,
    })


# ---------------------------------------------------------------------------
# Ficha de texto para el chatbot
# ---------------------------------------------------------------------------
def _fmt_valor(fila: dict) -> str:
    tipo = fila.get("tipo", "num")
    valor = fila.get("valor")
    unidad = fila.get("unidad", "")
    if valor is None:
        return "sin dato"
    if tipo == "texto":
        return str(valor)
    if tipo == "int":
        return f"{int(valor):,}" + (f" {unidad}" if unidad else "")
    if tipo == "pct":
        return f"{float(valor):,.1f}%" + (f" {unidad}" if unidad and unidad != "%" else "")
    return f"{float(valor):,.1f}" + (f" {unidad}" if unidad else "")


def _fmt_referencia(fila: dict) -> str:
    ref = fila.get("cohorte")
    if ref is None:
        return ""
    tipo = fila.get("tipo", "num")
    if tipo == "pct":
        return f"{float(ref):,.1f}%"
    if tipo == "int":
        return f"{int(ref):,}"
    return f"{float(ref):,.1f}"


def ficha_text(state, empresa: str | None = None, periodos: list[str] | None = None) -> str:
    """Ficha compacta en texto plano para enviar al modelo como contexto."""
    p = perfil(state, empresa, periodos)
    nombre = p["empresa"] or "Cohorte completa"
    lineas = [f"FICHA DETALLADA — {nombre} (talla: {p['talla']})"]

    for sec in p["secciones"]:
        lineas.append("")
        lineas.append(f"## {sec['titulo']}")
        for fila in sec["filas"]:
            es_desglose = fila.get("tipo") == "desglose"
            valor = _fmt_valor(fila)
            ref = _fmt_referencia(fila)
            if es_desglose:
                linea = f"- {fila['etiqueta']}:"
            else:
                linea = f"- {fila['etiqueta']}: {valor}"
                if ref:
                    linea += f" · referencia de talla: {ref}"
            lineas.append(linea)
            if fila.get("desglose"):
                partes = []
                for d in fila["desglose"]:
                    etiqueta = d["etiqueta"]
                    valor = d.get("valor")
                    pct = d.get("pct")
                    if isinstance(valor, str):
                        detalle = f"{etiqueta} {valor}"
                    elif valor is None:
                        detalle = f"{etiqueta} sin dato"
                    else:
                        detalle = f"{etiqueta} {valor:,.0f}"
                        if pct is not None:
                            detalle += f" ({pct:.0f}%)"
                    partes.append(detalle)
                lineas.append("    " + "; ".join(partes))

    return "\n".join(lineas)
