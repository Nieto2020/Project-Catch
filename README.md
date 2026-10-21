# SCORE — Smart Catch Optimization & Retention Ecosystem

Prototipo web de analítica de Recursos Humanos impulsada por IA, para el pitch del Datatón.
**No va a producción**: todo corre localmente, sin autenticación ni nube.

El proyecto se centra en **tres módulos**:

1. **Chatbot** — asistente que responde preguntas cuantitativas sobre los datos (LangChain + LLM).
2. **Video descriptivo** — video de 1-3 minutos con voz natural (sin avatar) que narra los
   hallazgos del análisis y muestra gráficas.
3. **Barómetro global** — índice de competitividad 0-100 con métricas establecidas.

## Requisitos

- Python 3.12+ (probado con 3.14)
- Node.js 20+ (probado con 20.18.1) y npm
- Internet (para la voz del video vía edge-tts de Microsoft y para el LLM)

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
| Barómetro Global | `/` | Índice global 0-100, desglose por dimensión, tendencia y ranking |
| Asistente IA | `/chat` | Consultas en lenguaje natural sobre los datos |
| Video Descriptivo | `/video` | Genera y reproduce el video narrado con hallazgos y gráficas |

## Asistente IA

El chat funciona **sin configuración** en "modo local" (respuestas cuantitativas
predefinidas). Para activar el agente LangChain + LLM completo:

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

## Video descriptivo

- Se genera bajo demanda desde la vista `/video` (botón "Generar video").
- Flujo: hallazgos → gráficas (matplotlib) → narración (edge-tts, voz natural de
  Microsoft) → ensamblado MP4 con ffmpeg (incluido vía `imageio-ffmpeg`).
- Voz configurable en `backend\.env` con `SCORE_VOICE`:
  - `es-MX-JorgeNeural` (hombre, por defecto)
  - `es-MX-DaliaNeural` (mujer)
- El MP4 se guarda en `data/processed/video/score_descriptivo.mp4` (no se commitea)
  y puede descargarse desde la vista.

## Barómetro global

Índice 0-100 construido con métricas establecidas y pesos:

| Dimensión | Peso | Meta de referencia |
|---|---|---|
| Salario | 30% | 500 MXN/día |
| Retención | 30% | ≤ 15% de rotación bimestral |
| Ausentismo | 15% | ≤ 150 faltas / 100 empleados |
| Capacitación | 15% | ≥ 4 horas / empleado |
| Equilibrio de género | 10% | 50% mujeres |

Además muestra la tendencia del índice por bimestre y el ranking de empresas.

## Estructura

```
data/            raw (Excel) y processed (parquets, codebook, video/)
notebooks/       eda.py (limpieza y perfilado)
backend/         FastAPI (main.py, api/, core/, services/)
frontend/        Next.js + Tailwind + Tremor (src/pages, components, services, store)
```

## Notas

- Los datos son una encuesta bimestral de RH a nivel **empresa** (40 empresas × 7 bimestres).
- El video es el resultado del análisis descriptivo (KPIs, tendencias y barómetro).
