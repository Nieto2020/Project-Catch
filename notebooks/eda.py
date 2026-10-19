# -*- coding: utf-8 -*-
"""
SCORE — EDA y limpieza de "BASE HISTORICA.xlsx"

Pipeline reproducible:
  1. Lee las 7 hojas (periodos bimestrales) del Excel.
  2. Limpia placeholders ("-", vacíos) y convierte columnas numéricas.
  3. Genera:
       - data/processed/encuestas_completo.parquet  (dataset completo, columnas q0001..)
       - data/processed/kpis_empresas.parquet       (columnas curadas con nombres legibles)
       - data/processed/diccionario_datos.csv       (codebook: posicion -> tema -> pregunta)
       - data/processed/perfil_dataset.md           (resumen del perfil de datos)

Ejecutar desde la raíz del repo:
    .venv\\Scripts\\python.exe notebooks\\eda.py
"""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
EXCEL = ROOT / "data" / "raw" / "BASE HISTORICA.xlsx"
OUT_DIR = ROOT / "data" / "processed"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# 1. Tema por rango de columna (1-based, Excel), según .github/MARKDOWN.md
# ---------------------------------------------------------------------------
THEME_RANGES: list[tuple[str, list[tuple[int, int]]]] = [
    ("Identificación y contacto", [(1, 14)]),
    ("Aviso de privacidad y alcance", [(15, 17)]),
    ("Ubicación (plantas y parques)", [(18, 51)]),
    ("Perfil de empresa e industria", [(52, 127), (129, 187)]),
    ("Sindicalización y conflictos", [(128, 128), (188, 193), (368, 369), (527, 593)]),
    ("Headcount y demografía", [(194, 204), (276, 288)]),
    ("Salarios y estructura salarial", [(205, 275)]),
    ("Control del cuestionario", [(289, 290), (594, 594), (961, 961), (1142, 1142)]),
    ("Reclutamiento y escolaridad", [(291, 313), (448, 526), (909, 960)]),
    ("Rotación y bajas", [(314, 340), (597, 619)]),
    ("Ausentismo e incapacidades", [(341, 357), (620, 627)]),
    ("Capacitación y desarrollo", [(358, 367)]),
    ("Incrementos salariales", [(370, 447)]),
    ("Proyección de plantilla", [(595, 596), (962, 963)]),
    ("Prestaciones económicas y de ley", [(628, 716)]),
    ("Reparto de utilidades (PTU)", [(717, 735)]),
    ("Seguros (gastos médicos / vida)", [(736, 761)]),
    ("Prestaciones en especie", [(762, 908)]),
    ("Practicantes y talento joven", [(964, 987)]),
    ("Jornadas, turnos y horarios", [(988, 1021)]),
    ("Beneficios, incentivos y eventos", [(1022, 1117)]),
    ("Responsabilidad social", [(1118, 1141)]),
]

# ---------------------------------------------------------------------------
# 2. Columnas curadas para el producto (índice 0-based -> nombre legible)
# ---------------------------------------------------------------------------
CURATED: dict[int, str] = {
    # Identidad
    5: "empresa",
    127: "tiene_sindicato",
    # Headcount y demografía
    193: "emp_operativos",
    194: "emp_admin",
    195: "emp_otros",
    196: "pct_mujeres",
    197: "pct_hombres",
    198: "gen_baby_boomers",
    199: "gen_x",
    200: "gen_millennial_30_37",
    201: "gen_millennial_23_29",
    202: "gen_z",
    203: "gen_desconocido",
    # Salarios diarios (personal operativo)
    204: "salario_inicial",
    205: "salario_inter_bajo",
    206: "salario_inter_alto",
    207: "salario_maximo",
    # Rotación y bajas
    313: "total_bajas",
    314: "bajas_julio",
    315: "bajas_agosto",
    316: "bajas_operativo",
    317: "bajas_administrativo",
    318: "bajas_renuncia_voluntaria",
    319: "bajas_abandono",
    320: "bajas_acum_faltas",
    321: "bajas_rescision",
    322: "bajas_disminucion_plazas",
    323: "bajas_jubilacion",
    324: "bajas_fallecimiento",
    325: "bajas_incap_permanente",
    326: "bajas_otro",
    328: "antig_bajas_0_1mes",
    329: "antig_bajas_1_3meses",
    330: "antig_bajas_3_12meses",
    331: "antig_bajas_1_3anios",
    332: "antig_bajas_mas_3anios",
    333: "antig_bajas_no_medido",
    334: "edad_bajas_baby_boomers",
    335: "edad_bajas_gen_x",
    336: "edad_bajas_millennial_31_37",
    337: "edad_bajas_millennial_23_30",
    338: "edad_bajas_gen_z",
    339: "edad_bajas_no_medido",
    # Rotación mensual promedio (últimos 6 meses)
    596: "rot_vol_operativa",
    597: "rot_invol_operativa",
    598: "rot_vol_admin",
    599: "rot_invol_admin",
    # Ausentismo
    340: "total_faltas",
    341: "faltas_oper_justificadas",
    342: "faltas_oper_injustificadas",
    343: "aus_oper_incapacidad",
    344: "faltas_admin_justificadas",
    345: "faltas_admin_injustificadas",
    346: "aus_admin_incapacidad",
    349: "casos_incapacidad",
    350: "incap_riesgo_trabajo",
    351: "incap_enfermedad_general",
    352: "incap_maternidad",
    353: "incap_temporal",
    354: "incap_permanente_parcial",
    355: "incap_permanente_total",
    # Capacitación
    357: "hrs_cap_operativos",
    358: "hrs_cap_administrativos",
}

# Columnas cuyo rango natural es 0-100 (porcentajes). Sirven para QC de calidad.
PCT_COLS = [
    "pct_mujeres", "pct_hombres",
    "gen_baby_boomers", "gen_x", "gen_millennial_30_37",
    "gen_millennial_23_29", "gen_z", "gen_desconocido",
    "antig_bajas_0_1mes", "antig_bajas_1_3meses", "antig_bajas_3_12meses",
    "antig_bajas_1_3anios", "antig_bajas_mas_3anios", "antig_bajas_no_medido",
    "edad_bajas_baby_boomers", "edad_bajas_gen_x", "edad_bajas_millennial_31_37",
    "edad_bajas_millennial_23_30", "edad_bajas_gen_z", "edad_bajas_no_medido",
]

PERIOD_ORDER = {
    "JUL-AGO_2024": 1, "SEP-OCT_2024": 2, "NOV-DIC_2024": 3, "ENE-FEB_2025": 4,
    "MAR-ABR_2025": 5, "MAY-JUN_2025": 6, "JUL-AGO_2025": 7,
}

PLACEHOLDERS = {"-", "", "nan", "None", "N/A", "NULL", "null", "N/A - No Aplica"}


def clean_scalar(value):
    """Normaliza un valor crudo de Excel a un escalar limpio."""
    if pd.isna(value):
        return None
    s = str(value).replace("\u00a0", " ").strip()
    if s in PLACEHOLDERS:
        return None
    return s


def to_numeric_series(series: pd.Series) -> pd.Series:
    """Convierte una serie a numérica tolerando $, comas y 'Desconocido'."""
    s = (
        series.astype("string")
        .str.replace(r"[\$,]", "", regex=True)
        .str.strip()
        .replace({"Desconocido": None, "desconocido": None, "": None})
    )
    return pd.to_numeric(s, errors="coerce")


def theme_for_column(pos_1based: int) -> str:
    """Devuelve el tema para una columna 1-based usando THEME_RANGES."""
    for theme, ranges in THEME_RANGES:
        for lo, hi in ranges:
            if lo <= pos_1based <= hi:
                return theme
    return "Sin mapear (columnas extra)"


def load_all_sheets() -> tuple[dict[str, pd.DataFrame], list[tuple[str, str, str]]]:
    """
    Lee todas las hojas como dataframes crudos (header=None).

    Devuelve (dfs, canonical_headers) donde canonical_headers es una lista de
    (pos_0based, pregunta, tipo/subetiqueta) usando JUL-AGO_2024 como canon.
    """
    raw = pd.read_excel(EXCEL, sheet_name=None, header=None, dtype=str)
    dfs: dict[str, pd.DataFrame] = {}
    for sheet, df in raw.items():
        # Fila 0 = pregunta, fila 1 = tipo/subetiqueta, filas 2+ = datos.
        data = df.iloc[2:].reset_index(drop=True)
        data.columns = range(data.shape[1])
        dfs[sheet] = data

    # Cabecera canónica: la hoja con más columnas define las posiciones extra.
    canon_sheet = max(dfs, key=lambda s: dfs[s].shape[1])
    hdr = raw[canon_sheet].iloc[0]
    typ = raw[canon_sheet].iloc[1]
    canonical = []
    for i in range(int(max(dfs[s].shape[1] for s in dfs))):
        q = clean_scalar(hdr[i]) or ""
        t = clean_scalar(typ[i]) or ""
        canonical.append((i, q, t))
    return dfs, canonical


def build_complete(dfs: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Construye el dataset completo en formato largo con columnas q0001..qNNNN."""
    frames = []
    for sheet in sorted(dfs, key=lambda s: PERIOD_ORDER[s]):
        df = dfs[sheet].copy()
        df["periodo"] = sheet
        df["periodo_num"] = PERIOD_ORDER[sheet]
        frames.append(df)
    complete = pd.concat(frames, ignore_index=True, sort=False)

    # Nombre de columna por posición (1-based): q0001...
    n_cols = complete.shape[1] - 2  # resto periodo / periodo_num
    rename = {i: f"q{i + 1:04d}" for i in range(n_cols)}
    rename[n_cols] = "periodo"
    rename[n_cols + 1] = "periodo_num"
    complete = complete.rename(columns=rename)

    # Descarta filas huérfanas: sin nombre de empresa (columna q0006).
    complete = complete[complete["q0006"].notna()].reset_index(drop=True)

    # Limpieza de valores.
    for c in complete.columns:
        if c in ("periodo", "periodo_num"):
            continue
        complete[c] = complete[c].map(clean_scalar)

    # Coerción numérica por columna (heurística: >= 60% convertibles).
    for c in [c for c in complete.columns if c.startswith("q")]:
        num = to_numeric_series(complete[c])
        if num.notna().sum() >= 0.6 * complete[c].notna().sum():
            complete[c] = num

    return complete


def build_curated(complete: pd.DataFrame) -> pd.DataFrame:
    """Extrae las columnas curadas con nombres legibles y añade KPIs derivados."""
    keep = {"q%04d" % (i + 1): name for i, name in CURATED.items()}
    curated = complete[["periodo", "periodo_num"] + list(keep)].rename(columns=keep)

    # Coerción numérica de las columnas curadas.
    numeric_curated = [n for n in CURATED.values() if n not in ("empresa", "tiene_sindicato")]
    for c in numeric_curated:
        curated[c] = to_numeric_series(curated[c])
    curated["empresa"] = curated["empresa"].astype("string")
    curated["tiene_sindicato"] = curated["tiene_sindicato"].astype("string")

    # KPIs derivados.
    curated["total_headcount"] = (
        curated["emp_operativos"].fillna(0)
        + curated["emp_admin"].fillna(0)
        + curated["emp_otros"].fillna(0)
    )
    curated["tasa_bajas_bimestral_pct"] = (
        curated["total_bajas"] / curated["total_headcount"] * 100
    ).round(2)

    # Tasa de rotación mensual promedio (de los 4 indicadores 596-599).
    rot_cols = ["rot_vol_operativa", "rot_invol_operativa", "rot_vol_admin", "rot_invol_admin"]
    curated["rotacion_mensual_promedio"] = curated[rot_cols].mean(axis=1).round(4)

    # Reordenar: identidad + periodo primero.
    first = ["periodo", "periodo_num", "empresa", "tiene_sindicato"]
    rest = [c for c in curated.columns if c not in first]
    return curated[first + rest]


def build_codebook(canonical: list[tuple[int, str, str]], complete_cols: list[str]) -> pd.DataFrame:
    """Codebook: posición, columna qNNNN, tema, pregunta, tipo, nombre curado."""
    rows = []
    for pos, question, qtype in canonical:
        col = f"q{pos + 1:04d}"
        rows.append({
            "posicion_excel": pos + 1,
            "columna": col,
            "tema": theme_for_column(pos + 1),
            "pregunta": question,
            "tipo_respuesta": qtype,
            "nombre_curado": CURATED.get(pos, ""),
        })
    return pd.DataFrame(rows)


def write_profile(curated: pd.DataFrame, complete: pd.DataFrame, codebook: pd.DataFrame) -> str:
    """Genera el markdown de perfil del dataset."""
    n_periodos = curated["periodo"].nunique()
    n_registros = len(curated)
    n_empresas_unicas = curated["empresa"].nunique()
    n_columnas = complete.shape[1] - 2

    def stats(series: pd.Series) -> str:
        s = pd.to_numeric(series, errors="coerce").dropna()
        if s.empty:
            return "sin datos"
        return f"n={len(s)}, min={s.min():,.1f}, mediana={s.median():,.1f}, max={s.max():,.1f}"

    lines = [
        "# Perfil del dataset — SCORE",
        "",
        "Fuente: `BASE HISTORICA.xlsx` (7 hojas, una por bimestre).",
        "",
        "## Naturaleza de los datos",
        f"- **Tipo:** encuesta de RH a nivel empresa (cuestionario de ~{n_columnas} columnas), no registros individuales de empleados.",
        f"- **Cobertura temporal:** {n_periodos} bimestres (JUL-AGO 2024 → JUL-AGO 2025).",
        f"- **Registros:** {n_registros} respuestas empresa-periodo (~{n_registros // n_periodos} empresas por periodo).",
        f"- **Empresas:** nombres anonimizados (`COMPAÑIA 1..N`); no hay identificador que permita seguir a una misma empresa entre periodos, por lo que **el análisis temporal es por cohortes (cortes transversales repetidos), no panel**.",
        "- **Limitación:** las secciones de identidad, ubicación e industria (Estado, Municipio, Industria, origen de capital, tiempo operando) están **vacías** en el export; no es posible segmentar por esas dimensiones.",
        "",
        "## Cobertura de variables clave",
        "| Variable | Estadística |",
        "|---|---|",
    ]
    key_cols = [
        "emp_operativos", "emp_admin", "pct_mujeres", "pct_hombres",
        "salario_inicial", "salario_maximo", "total_bajas", "total_faltas",
        "hrs_cap_operativos", "casos_incapacidad", "total_headcount",
        "tasa_bajas_bimestral_pct",
    ]
    for c in key_cols:
        lines.append(f"| `{c}` | {stats(curated[c])} |")

    lines += [
        "",
        "## Calidad de datos detectada",
        "- Placeholders normalizados a nulos: `-`, vacío, `nan`, `N/A`.",
        "- `pct_mujeres` / `pct_hombres` (y generaciones) deberían sumar 100; existen valores >100 (p. ej. 368, 683) que sugieren captura errónea (porcentajes con decimal corrido).",
        "- `total_bajas` y `total_faltas` tienen valores atípicos altos (máx. 810 y 10,000 respectivamente) a validar con el negocio.",
        "- La rotación mensual (columnas 596-599) está en **tasa decimal** (0.01 = 1%); `Desconocido` se convirtió a nulo.",
        "- `aus_oper_incapacidad` y `aus_admin_incapacidad` están **vacías en todas las hojas** (el subcampo no fue capturado en la fuente).",
        "- Se eliminaron 4 filas huérfanas (sin nombre de empresa, con ≤3 valores no nulos) presentes en 4 periodos.",
        "",
        "## Archivos generados",
        "- `encuestas_completo.parquet` — dataset completo limpio (columnas `q0001..qNNNN` + `periodo`).",
        "- `kpis_empresas.parquet` — columnas curadas con nombres legibles + KPIs derivados.",
        "- `diccionario_datos.csv` — codebook posición → tema → pregunta.",
        "",
        f"Generado con `notebooks/eda.py`. Columnas totales: {n_columnas}. Temas mapeados: {codebook['tema'].nunique()}.",
    ]
    return "\n".join(lines)


def main() -> None:
    dfs, canonical = load_all_sheets()
    complete = build_complete(dfs)
    curated = build_curated(complete)
    codebook = build_codebook(canonical, [c for c in complete.columns if c.startswith("q")])

    complete.to_parquet(OUT_DIR / "encuestas_completo.parquet", index=False)
    curated.to_parquet(OUT_DIR / "kpis_empresas.parquet", index=False)
    codebook.to_csv(OUT_DIR / "diccionario_datos.csv", index=False, encoding="utf-8-sig")
    (OUT_DIR / "perfil_dataset.md").write_text(write_profile(curated, complete, codebook), encoding="utf-8")

    print(f"Registros completos : {len(complete)}")
    print(f"Registros curados   : {len(curated)}")
    print(f"Columnas completas  : {complete.shape[1] - 2}")
    print(f"Columnas curadas    : {curated.shape[1]}")
    print(f"Empresas únicas     : {curated['empresa'].nunique()}")
    print(f"Archivos escritos en: {OUT_DIR}")


if __name__ == "__main__":
    main()
