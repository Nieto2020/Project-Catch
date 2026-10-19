# Perfil del dataset — SCORE

Fuente: `BASE HISTORICA.xlsx` (7 hojas, una por bimestre).

## Naturaleza de los datos
- **Tipo:** encuesta de RH a nivel empresa (cuestionario de ~1169 columnas), no registros individuales de empleados.
- **Cobertura temporal:** 7 bimestres (JUL-AGO 2024 → JUL-AGO 2025).
- **Registros:** 280 respuestas empresa-periodo (~40 empresas por periodo).
- **Empresas:** nombres anonimizados (`COMPAÑIA 1..N`); no hay identificador que permita seguir a una misma empresa entre periodos, por lo que **el análisis temporal es por cohortes (cortes transversales repetidos), no panel**.
- **Limitación:** las secciones de identidad, ubicación e industria (Estado, Municipio, Industria, origen de capital, tiempo operando) están **vacías** en el export; no es posible segmentar por esas dimensiones.

## Cobertura de variables clave
| Variable | Estadística |
|---|---|
| `emp_operativos` | n=280, min=0.0, mediana=274.0, max=17,100.0 |
| `emp_admin` | n=280, min=12.0, mediana=97.0, max=2,252.0 |
| `pct_mujeres` | n=259, min=10.0, mediana=35.0, max=368.0 |
| `pct_hombres` | n=259, min=33.0, mediana=71.0, max=683.0 |
| `salario_inicial` | n=280, min=226.0, mediana=321.7, max=633.3 |
| `salario_maximo` | n=280, min=320.0, mediana=530.5, max=900.0 |
| `total_bajas` | n=233, min=0.0, mediana=26.0, max=810.0 |
| `total_faltas` | n=232, min=0.0, mediana=296.0, max=10,000.0 |
| `hrs_cap_operativos` | n=273, min=0.0, mediana=436.0, max=57,982.0 |
| `casos_incapacidad` | n=268, min=0.0, mediana=47.0, max=5,306.0 |
| `total_headcount` | n=280, min=12.0, mediana=470.5, max=17,560.0 |
| `tasa_bajas_bimestral_pct` | n=233, min=0.0, mediana=5.6, max=38.1 |

## Calidad de datos detectada
- Placeholders normalizados a nulos: `-`, vacío, `nan`, `N/A`.
- `pct_mujeres` / `pct_hombres` (y generaciones) deberían sumar 100; existen valores >100 (p. ej. 368, 683) que sugieren captura errónea (porcentajes con decimal corrido).
- `total_bajas` y `total_faltas` tienen valores atípicos altos (máx. 810 y 10,000 respectivamente) a validar con el negocio.
- La rotación mensual (columnas 596-599) está en **tasa decimal** (0.01 = 1%); `Desconocido` se convirtió a nulo.
- `aus_oper_incapacidad` y `aus_admin_incapacidad` están **vacías en todas las hojas** (el subcampo no fue capturado en la fuente).
- Se eliminaron 4 filas huérfanas (sin nombre de empresa, con ≤3 valores no nulos) presentes en 4 periodos.

## Archivos generados
- `encuestas_completo.parquet` — dataset completo limpio (columnas `q0001..qNNNN` + `periodo`).
- `kpis_empresas.parquet` — columnas curadas con nombres legibles + KPIs derivados.
- `diccionario_datos.csv` — codebook posición → tema → pregunta.

Generado con `notebooks/eda.py`. Columnas totales: 1169. Temas mapeados: 23.