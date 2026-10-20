# SCORE — Smart Catch Optimization & Retention Ecosystem

Prototipo web de analítica de Recursos Humanos impulsada por IA, para el pitch del Datatón.
**No va a producción**: todo corre localmente, sin autenticación ni nube.

## Requisitos

- Python 3.12+ (probado con 3.14)
- Node.js 20+ (probado con 20.18.1) y npm

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
| Dashboard | `/` | KPIs, tendencias y distribuciones descriptivas/prescriptivas |
| Simulador What-If | `/whatif` | Proyecta el impacto en retención al cambiar variables |
| Barómetro | `/barometro` | Índice de competitividad 0-100 por empresa |
| Asistente IA | `/chat` | Consultas en lenguaje natural sobre los datos |
| Capa Comercial | `/comercial` | Niveles de suscripción (Básico, Intermedio, Premium) |

## Asistente IA (opcional)

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

## Estructura

```
data/            raw (Excel) y processed (parquets, codebook)
notebooks/       eda.py, train_model.py
models/          modelo_rotacion.pkl + metadatos
backend/         FastAPI (main.py, api/, core/, services/, templates/)
frontend/        Next.js + Tailwind + Tremor (src/pages, components, services, store)
```

## Notas

- Los datos son una encuesta bimestral de RH a nivel **empresa** (40 empresas × 7 bimestres).
- El modelo de rotación es un RandomForest (R² CV ≈ 0.43) entrenado en `notebooks/train_model.py`.
