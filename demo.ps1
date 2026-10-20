# ============================================================
# SCORE - Demo launcher
# Levanta backend (FastAPI) y frontend (Next.js) en dos ventanas
# y abre el navegador en http://localhost:3000
#
# Uso:  .\demo.ps1            (abre navegador al final)
#       .\demo.ps1 -NoBrowser (solo levanta servidores)
# ============================================================
param(
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path

# Asegura node/npm en el PATH (por si VS Code no se reinicio tras instalar Node).
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    $nodeDir = "C:\Program Files\nodejs"
    if (Test-Path "$nodeDir\node.exe") {
        $env:Path = "$nodeDir;$env:Path"
    }
}

# Prerrequisitos ------------------------------------------------------
if (-not (Test-Path "$root\.venv\Scripts\python.exe")) {
    Write-Host "ERROR: no existe .venv. Crea el entorno:" -ForegroundColor Red
    Write-Host "  py -m venv .venv" -ForegroundColor Yellow
    Write-Host "  .venv\Scripts\python.exe -m pip install -r backend\requirements.txt" -ForegroundColor Yellow
    exit 1
}

if (-not (Test-Path "$root\frontend\node_modules")) {
    Write-Host "Instalando dependencias del frontend (primera vez)..." -ForegroundColor Yellow
    Push-Location "$root\frontend"
    try { npm install } finally { Pop-Location }
}

Write-Host ""
Write-Host "  SCORE - Smart Catch Optimization & Retention Ecosystem" -ForegroundColor Cyan
Write-Host "  Backend  -> http://127.0.0.1:8000" -ForegroundColor White
Write-Host "  Frontend -> http://localhost:3000" -ForegroundColor White
Write-Host ""

# Backend (Terminal 1) ------------------------------------------------
$backendCmd = "Set-Location '$root'; Write-Host 'SCORE Backend (Ctrl+C para detener)' -ForegroundColor Cyan; .\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload"
Start-Process powershell -ArgumentList "-NoExit -Command `"$backendCmd`""

# Frontend (Terminal 2) ------------------------------------------------
$frontendCmd = "Set-Location '$root\frontend'; Write-Host 'SCORE Frontend (Ctrl+C para detener)' -ForegroundColor Cyan; npm run dev"
Start-Process powershell -ArgumentList "-NoExit -Command `"$frontendCmd`""

# Navegador ------------------------------------------------------------
if (-not $NoBrowser) {
    Write-Host "Esperando a que arranque el frontend..." -ForegroundColor DarkGray
    Start-Sleep -Seconds 7
    Start-Process "http://localhost:3000"
}

Write-Host "Listo. Deten cada servidor con Ctrl+C en su ventana." -ForegroundColor Green
