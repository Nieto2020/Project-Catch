# SCORE — Smart Catch Optimization & Retention Ecosystem

Prototipo web de analítica de Recursos Humanos impulsada por IA, para el pitch del Datatón.
**No va a producción**: todo corre localmente, sin autenticación ni nube.

El proyecto se centra en **tres módulos**:

1. **Chatbot** — asistente que responde preguntas cuantitativas sobre los datos (LangChain + LLM).
2. **Barómetro global** — Índice SCORE 0-100 con métricas establecidas.
3. **Reportes** — reporte ejecutivo HTML con gráficas, filtrable por empresa y bimestre.

## Requisitos

- Python 3.12+ (probado con 3.14)
- Node.js 20+ (probado con 20.18.1) y npm
- Internet (para el LLM)

## Instalación (una sola vez)

```powershell
# 1. Entorno Python + dependencias
py -m venv .venv
.venv\Scripts\python.exe -m pip install -r backend\requirements.txt

# 2. Dependencias del frontend
cd frontend
npm install
cd ..
```

> Si nunca has generado los datos procesados (ya vienen commiteados en `data/processed/`),
> ejecuta `.venv\Scripts\python.exe notebooks\eda.py` para regenerarlos.

## Correr la demo

**Opción rápida (un solo comando):** levanta backend y frontend en dos ventanas
y abre el navegador.

```powershell
.\demo.ps1
```

**Opción manual (dos terminales):**

**Terminal 1 — Backend (FastAPI, puerto 8000):**

```powershell
.venv\Scripts\python.exe -m uvicorn backend.main:app --reload
```

**Terminal 2 — Frontend (Next.js, puerto 3000):**

```powershell
cd frontend
npm run dev
```

Abre **http://localhost:3000** en el navegador.

- API: http://127.0.0.1:8000
- Documentación interactiva (Swagger): http://127.0.0.1:8000/docs

## Módulos (vistas)

| Vista | Ruta | Descripción |
|---|---|---|
| Barómetro Global | `/` | Índice SCORE 0-100, desglose por dimensión, tendencia, ranking, comparador de condiciones y simulador de pesos |
| Asistente IA | `/chat` | Consultas en lenguaje natural sobre los datos |
| Reportes | `/reportes` | Reporte ejecutivo con gráficas, filtrable por empresa y bimestre |

## Asistente IA

El chat responde **con el modelo de lenguaje**. Para activarlo:

1. Copia `backend\.env.example` a `backend\.env`.
2. Añade tu clave: `OPENAI_API_KEY=sk-...`

**OpenAI:**

```
OPENAI_MODEL=gpt-4o-mini
```

**DeepSeek** (compatible con OpenAI; el endpoint se detecta automáticamente si el modelo contiene "deepseek"):

```
OPENAI_MODEL=deepseek-chat
```

Reinicia el backend tras editar `.env`.

### Cómo funciona

Cada consulta es **una sola llamada al LLM** sobre un resumen del dataset calculado
en Python (KPIs, medianas, top empresas, barómetro, prestaciones y descansos). Esto lo
hace rápido y confiable, sin iterar sobre el DataFrame. Si se adjunta contexto desde el
ranking, se incluye en esa misma llamada.

No hay agente con pasos ni límite de iteraciones: si el modelo no está configurado,
falla, se agota el tiempo o devuelve una respuesta vacía, el chat responde con el
cálculo local del dataset (o con el resumen de indicadores si la pregunta no está
cubierta) y lo indica en el globo de la respuesta, de modo que el asistente nunca
queda sin contestar.

### Contexto con IA desde el ranking

En el **Barómetro Global**, cada fila del ranking tiene un botón **"Contexto con IA"**.
Al pulsarlo:

1. Se navega al asistente (`/chat`) de inmediato.
2. Los datos de esa fila (empresa, talla, bimestre, score, headcount, salario,
   rotación y sub-indicadores) quedan adjuntos en una tarjeta de contexto.
3. Se precarga una pregunta para que solo tengas que enviarla o editarla.

Mientras el contexto está adjunto, cada consulta se envía al modelo junto con esos
datos, así las respuestas se refieren a esa empresa y bimestre. Se puede quitar con
el botón **Quitar**.

- `GET /api/chat/estado` → `{ llm_disponible, modelo }`.
- `GET /api/chat/sugerencias` → `[{ pregunta, respuesta }]` (precalculadas).
- `POST /api/chat` con `{ "pregunta": "...", "contexto": "..." }` → el LLM recibe el contexto.

## Barómetro global (Índice SCORE)

Índice 0-100 construido con métricas establecidas y pesos:

| Dimensión | Peso | Meta de referencia |
|---|---|---|
| Salario | 30% | 500 MXN/día |
| Retención | 30% | ≤ 15% de rotación bimestral |
| Ausentismo | 15% | ≤ 150 faltas / 100 empleados |
| Capacitación | 15% | ≥ 4 horas / empleado |
| Equilibrio de género | 10% | 50% mujeres |

Además muestra la tendencia del índice por bimestre, el ranking de empresas y una lectura
en texto del resultado (banda, referencia de la cohorte y mayor oportunidad de mejora).

### Comparador “qué pasa si…”

La vista incluye un simulador que recalcula el índice y **el ranking** con otros pesos por
dimensión, para conversar con el cliente sobre qué priorizar. Los puntajes por dimensión no
cambian: solo su importancia relativa. Mientras hay pesos personalizados, el ranking muestra
un aviso y el botón **“Volver a los pesos base”**. Endpoint: `POST /api/barometro/escenario`
con `{ "pesos": { "salario": 40, "retencion": 25, "ausentismo": 15, "capacitacion": 10, "equilibrio": 10 } }`;
la respuesta incluye el índice resultante y el puntaje recalculado de cada empresa-bimestre.

### Privacidad en los reportes

Los datos del prototipo están **seudonimizados**. Como regla de agregación, cuando una
cohorte tiene **menos de 5 empresas** los reportes omiten los indicadores agregados, el
ranking y las gráficas (se muestran como “dato insuficiente”), para evitar reidentificar a
una empresa concreta. El reporte de una sola empresa sí muestra sus propios datos.

### Condiciones laborales (fuera del índice)

Las variables **descriptivas** de condiciones de trabajo **no ponderan** el Índice SCORE,
pero se siguen calculando y se usan en el **reporte detallado** de cada empresa:

| Grupo | Variables | Unidad |
|---|---|---|
| Días y prestaciones | Días de descanso adicionales a los festivos de ley, vacaciones (1.er año), aguinaldo (1.er año), prima vacacional, vales de despensa, fondo de ahorro | días / % |
| Descansos adicionales | Jueves y Viernes Santo, 10 de mayo, 15 de septiembre, 2 de noviembre, 12, 24 y 31 de diciembre, matrimonio, nacimiento y defunción | sí / no |

Las métricas siguen disponibles vía API, aunque **ya no se muestran en la vista del
Barómetro Global**:

- `GET /api/barometro/comparables?variable=&periodo=&talla=` devuelve la mediana de la
  cohorte, rango P25–P75 y mínimo–máximo (o % de empresas que la otorgan), la comparación
  empresa por empresa contra la mediana de su talla con su percentil, y la evolución por
  bimestre y por talla.

## Reportes

- Vista `/reportes`: elige **todas las empresas o una específica** y los **bimestres** a incluir.
- Genera un reporte ejecutivo HTML con la plantilla corporativa de SCORE, con:
  - Indicadores clave calculados del dataset filtrado.
  - 4 gráficas (salarios, rotación/bajas, género y barómetro) incrustadas.
  - Tabla de ranking (todas las empresas) o desglose por bimestre (empresa específica).
- Se puede **abrir en pestaña nueva**, **descargar como HTML** o **descargar como PDF** directamente.
- Endpoints: `GET /api/report/opciones`, `GET /api/report`, `GET /api/report/descargar`, `GET /api/report/pdf`.

## Estructura

```
assets/          logo de Catch Consulting
data/            raw (Excel) y processed (parquet curado, codebook, perfil)
notebooks/       eda.py (limpieza y perfilado)
backend/         FastAPI (main.py, api/, core/, services/, templates/)
frontend/        Next.js + Tailwind + Tremor (src/pages, components, services, store)
```

El detalle completo de la estructura está en [structure.txt](structure.txt).

## Notas

- Los datos son una encuesta bimestral de RH a nivel **empresa** (40 empresas × 7 bimestres).
