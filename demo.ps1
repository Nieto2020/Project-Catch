# ============================================================
# SCORE - Demo launcher
# Levanta backend (FastAPI) y frontend (Next.js) en dos ventanas
# y abre el navegador en el puerto real del frontend.
#
# Uso:  .\demo.ps1                     (abre navegador al final)
#       .\demo.ps1 -NoBrowser          (solo levanta servidores)
#       .\demo.ps1 -CheckPorts         (solo informa que ocupa cada puerto)
#       .\demo.ps1 -FrontendPort 3010  (fuerza un puerto concreto)
# ============================================================
param(
    [switch]$NoBrowser,
    [int]$FrontendPort = 3000,
    [int]$BackendPort = 8000,
    [switch]$KeepExisting,
    [switch]$CheckPorts
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path

# --- Utilidades de puertos -------------------------------------------
function Get-PortOwner {
    param([int]$Port)
    $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if (-not $conn) { return $null }
    $proc = Get-CimInstance Win32_Process -Filter "ProcessId = $($conn.OwningProcess)" -ErrorAction SilentlyContinue
    [pscustomobject]@{
        Port        = $Port
        ProcessId   = $conn.OwningProcess
        Name        = $proc.Name
        CommandLine = $proc.CommandLine
    }
}

function Test-PortInUse {
    param([int]$Port)
    return [bool](Get-PortOwner -Port $Port)
}

function Wait-PortFree {
    param([int]$Port, [int]$TimeoutMs = 6000)
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    while ($sw.ElapsedMilliseconds -lt $TimeoutMs) {
        if (-not (Test-PortInUse -Port $Port)) { return $true }
        Start-Sleep -Milliseconds 200
    }
    return -not (Test-PortInUse -Port $Port)
}

function Get-NextFreePort {
    param([int]$Start)
    for ($p = $Start; $p -lt $Start + 20; $p++) {
        if (-not (Test-PortInUse -Port $p)) { return $p }
    }
    throw "No hay puerto libre a partir de $Start."
}

function Stop-ProcessTree {
    param([int[]]$RootIds, [string]$ProcessName, [string]$PathPattern)
    if (-not $RootIds -or $RootIds.Count -eq 0) { return }
    $all = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue

    $ids = New-Object System.Collections.Generic.List[int]
    $queue = New-Object System.Collections.Generic.Queue[int]
    foreach ($id in $RootIds) { $queue.Enqueue($id) }
    while ($queue.Count -gt 0) {
        $id = $queue.Dequeue()
        if ($ids.Contains($id)) { continue }
        $ids.Add($id)
        foreach ($child in @($all | Where-Object {
                    $_.ParentProcessId -eq $id -and
                    ($_.Name -eq $ProcessName -or ($PathPattern -and $_.CommandLine -like $PathPattern))
                })) {
            $queue.Enqueue([int]$child.ProcessId)
        }
    }

    $ordered = $ids.ToArray()
    [array]::Reverse($ordered)
    foreach ($id in $ordered) {
        try { Stop-Process -Id $id -Force -ErrorAction Stop } catch { }
    }
    return $ordered
}

# Detiene instancias previas de este mismo proyecto (node/next o uvicorn).
function Stop-ProjectProcesses {
    param([string]$PathPattern, [string]$ProcessName)
    $all = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue
    $roots = @($all | Where-Object {
            $_.Name -eq $ProcessName -and $_.CommandLine -and $_.CommandLine -like $PathPattern
        } | ForEach-Object { [int]$_.ProcessId })
    Stop-ProcessTree -RootIds $roots -ProcessName $ProcessName -PathPattern $PathPattern | Out-Null
    return $roots
}

# Libera un socket heredado por hijos de un proceso ya terminado.
function Stop-OrphanHolders {
    param([int]$ParentId, [string]$ProcessName)
    $all = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue
    $roots = @($all | Where-Object {
            $_.ParentProcessId -eq $ParentId -and $_.Name -eq $ProcessName
        } | ForEach-Object { [int]$_.ProcessId })
    Stop-ProcessTree -RootIds $roots -ProcessName $ProcessName
}

# Devuelve un puerto utilizable: libera sockets heredados de procesos ya
# terminados y, si lo ocupa un proceso ajeno, usa el siguiente libre.
function Resolve-DemoPort {
    param([int]$Port, [string]$Label, [string]$ProcessName, [switch]$Strict)

    $owner = Get-PortOwner -Port $Port
    if (-not $owner) { return $Port }

    $alive = [bool](Get-Process -Id $owner.ProcessId -ErrorAction SilentlyContinue)
    if (-not $KeepExisting -and -not $alive) {
        Write-Host "${Label}: liberando puerto $Port (socket heredado por PID $($owner.ProcessId), ya terminado)..." -ForegroundColor Yellow
        Stop-OrphanHolders -ParentId $owner.ProcessId -ProcessName $ProcessName
        if (Wait-PortFree -Port $Port) { return $Port }
    }

    $detail = "el puerto $Port ($Label) esta ocupado por '$($owner.Name)' (PID $($owner.ProcessId))"
    if ($Strict) {
        Write-Host "ERROR: $detail." -ForegroundColor Red
        Write-Host "  Cierra ese proceso, usa -$($Label)Port con otro valor, o ejecuta .\demo.ps1 sin ese parametro para elegir un puerto libre." -ForegroundColor Yellow
        exit 1
    }

    $free = Get-NextFreePort -Start ($Port + 1)
    Write-Host "AVISO: $detail. Usando el puerto $free." -ForegroundColor Yellow
    return $free
}

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

# Diagnostico de puertos ------------------------------------------------
if ($CheckPorts) {
    foreach ($p in @($BackendPort, $FrontendPort)) {
        $owner = Get-PortOwner -Port $p
        if ($owner) {
            Write-Host "Puerto $p ocupado por $($owner.Name) (PID $($owner.ProcessId))" -ForegroundColor Yellow
            Write-Host "  $($owner.CommandLine)" -ForegroundColor DarkGray
        } else {
            Write-Host "Puerto $p libre" -ForegroundColor Green
        }
    }
    exit 0
}

# Libera instancias previas del demo ------------------------------------
$ownFrontend = "*$root\frontend\node_modules*"
$ownBackend = "*$root\.venv*uvicorn*"

if (-not $KeepExisting) {
    $previous = @(
        [pscustomobject]@{ Label = "frontend"; Pattern = $ownFrontend; Name = "node.exe"; Port = $FrontendPort }
        [pscustomobject]@{ Label = "backend"; Pattern = $ownBackend; Name = "python.exe"; Port = $BackendPort }
    )
    foreach ($prev in $previous) {
        $pids = @(Stop-ProjectProcesses -PathPattern $prev.Pattern -ProcessName $prev.Name)
        if ($pids.Count -gt 0) {
            Write-Host "$($prev.Label): deteniendo instancia previa (PID $($pids -join ', '))..." -ForegroundColor Yellow
            [void](Wait-PortFree -Port $prev.Port -TimeoutMs 8000)
        }
    }
}

# Resolucion de puertos -------------------------------------------------
$fePort = Resolve-DemoPort -Port $FrontendPort -Label "frontend" -ProcessName "node.exe" `
    -Strict:$PSBoundParameters.ContainsKey("FrontendPort")
$bePort = Resolve-DemoPort -Port $BackendPort -Label "backend" -ProcessName "python.exe" `
    -Strict:$PSBoundParameters.ContainsKey("BackendPort")

Write-Host ""
Write-Host "  SCORE - Smart Catch Optimization & Retention Ecosystem" -ForegroundColor Cyan
Write-Host "  Backend  -> http://127.0.0.1:$bePort" -ForegroundColor White
Write-Host "  Frontend -> http://localhost:$fePort" -ForegroundColor White
Write-Host ""
if ($fePort -ne 3000 -or $bePort -ne 8000) {
    Write-Host "  (puertos en uso: backend $bePort, frontend $fePort)" -ForegroundColor DarkGray
    Write-Host ""
}

# Backend (Terminal 1) ------------------------------------------------
$corsOrigins = "http://localhost:$fePort,http://127.0.0.1:$fePort"
$backendCmd = "Set-Location '$root'; " +
    "`$env:CORS_ORIGINS = '$corsOrigins'; " +
    "Write-Host 'SCORE Backend (Ctrl+C para detener)' -ForegroundColor Cyan; " +
    ".\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --host 127.0.0.1 --port $bePort"
Start-Process powershell -ArgumentList "-NoExit -Command `"$backendCmd`""

# Frontend (Terminal 2) ------------------------------------------------
$frontendCmd = "Set-Location '$root\frontend'; " +
    "`$env:NEXT_PUBLIC_API_URL = 'http://127.0.0.1:$bePort'; " +
    "Write-Host 'SCORE Frontend (Ctrl+C para detener)' -ForegroundColor Cyan; " +
    "npm run dev -- --port $fePort"
Start-Process powershell -ArgumentList "-NoExit -Command `"$frontendCmd`""

# Navegador ------------------------------------------------------------
if (-not $NoBrowser) {
    $url = "http://localhost:$fePort"
    Write-Host "Esperando a que responda $url ..." -ForegroundColor DarkGray
    $ready = $false
    for ($i = 0; $i -lt 90; $i++) {
        try {
            Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 3 | Out-Null
            $ready = $true
            break
        } catch {
            Start-Sleep -Seconds 1
        }
    }
    if ($ready) {
        Start-Process $url
    } else {
        Write-Host "El frontend aun no responde; abrelo manualmente en $url" -ForegroundColor Yellow
    }
}

Write-Host "Listo. Deten cada servidor con Ctrl+C en su ventana (cierra tambien las ventanas previas)." -ForegroundColor Green
