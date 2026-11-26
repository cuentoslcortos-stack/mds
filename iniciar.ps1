<#
    Sistema MDS - lanzador
    Levanta el motor RAG (backend + interfaz web) y abre el navegador.

      .\iniciar.ps1            -> solo en esta compu (http://127.0.0.1:8765)
      .\iniciar.ps1 -Red       -> tambien en la red local, para usar el celu
      .\iniciar.ps1 -Detener   -> frena el motor

    Todo queda corriendo en tu maquina: el modelo de lenguaje se ejecuta en tu
    GPU con Ollama y el corpus nunca sale del equipo.
#>
param(
    [switch]$Red,
    [switch]$Detener,
    [switch]$Reiniciar
)

$ErrorActionPreference = 'Stop'
$raiz = Split-Path -Parent $MyInvocation.MyCommand.Path
$rag  = Join-Path $raiz 'rag'
$web  = Join-Path $raiz 'web'
$dist = Join-Path $web 'dist\index.html'
$puerto = 8765

function Buscar-Servidor {
    Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -like '*cli.py servir*' }
}

function Test-Puerto {
    try {
        Invoke-RestMethod -Uri "http://127.0.0.1:$puerto/api/health" -TimeoutSec 4 | Out-Null
        return $true
    } catch { return $false }
}

function Test-Ollama {
    try {
        Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/tags' -TimeoutSec 4 | Out-Null
        return $true
    } catch { return $false }
}

function Get-IP-Local {
    try {
        $ip = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction Stop |
            Where-Object { $_.IPAddress -notlike '127.*' -and $_.PrefixOrigin -ne 'WellKnown' } |
            Select-Object -First 1
        return $ip.IPAddress
    } catch { return $null }
}

# --- Detener ---------------------------------------------------------------
if ($Detener) {
    $procesos = Buscar-Servidor
    if ($procesos) {
        foreach ($p in $procesos) { Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue }
        Write-Host "Motor RAG detenido ($($procesos.Count) proceso(s))." -ForegroundColor Yellow
    } else {
        Write-Host "No habia ningun motor RAG corriendo." -ForegroundColor Yellow
    }
    exit 0
}

Write-Host ''
Write-Host '  SISTEMA MDS  |  RAG local del corpus lacaniano' -ForegroundColor Cyan
Write-Host '  ------------------------------------------------' -ForegroundColor DarkGray
Write-Host ''

# 1) Si ya esta corriendo, solo abro el navegador.
if ((Test-Puerto) -and -not $Reiniciar) {
    Write-Host '  El motor ya estaba corriendo.' -ForegroundColor Green
    Start-Process "http://127.0.0.1:$puerto"
    Write-Host '  Abriendo http://127.0.0.1:' + $puerto -ForegroundColor Green
    exit 0
}

# 2) Ollama
if (-not (Test-Ollama)) {
    $ollama = Join-Path $env:LOCALAPPDATA 'Programs\Ollama\ollama.exe'
    if (Test-Path $ollama) {
        Write-Host '  Iniciando Ollama...'
        Start-Process -FilePath $ollama -WindowStyle Hidden
        for ($i = 0; $i -lt 30; $i++) {
            Start-Sleep -Seconds 2
            if (Test-Ollama) { break }
        }
    }
    if (-not (Test-Ollama)) {
        Write-Host '  No se pudo contactar a Ollama (127.0.0.1:11434).' -ForegroundColor Red
        Write-Host '  Abrilo manualmente y volve a intentar.' -ForegroundColor Red
        exit 1
    }
}
Write-Host '  [ok] Ollama respondiendo' -ForegroundColor Green

# 3) Interfaz web compilada (una sola vez hace falta)
if (-not (Test-Path $dist)) {
    Write-Host '  Compilando la interfaz web (solo la primera vez)...' -ForegroundColor Yellow
    Push-Location $web
    try {
        if (-not (Test-Path 'node_modules')) { & npm.cmd install | Out-Null }
        & npm.cmd run build | Out-Null
    } finally { Pop-Location }
    if (-not (Test-Path $dist)) {
        Write-Host '  No se pudo compilar la interfaz web.' -ForegroundColor Red
        exit 1
    }
}
Write-Host '  [ok] Interfaz web lista' -ForegroundColor Green

# 4) Levantar el motor
if ($Red) { $env:MDS_RAG_HOST = '0.0.0.0' }
else { $env:MDS_RAG_HOST = '127.0.0.1' }

$log = Join-Path $env:TEMP 'mds_rag_server.log'
$err = Join-Path $env:TEMP 'mds_rag_server.err'
Start-Process -FilePath 'python' -ArgumentList 'cli.py', 'servir' -WorkingDirectory $rag `
    -WindowStyle Minimized -RedirectStandardOutput $log -RedirectStandardError $err | Out-Null

for ($i = 0; $i -lt 40; $i++) {
    Start-Sleep -Milliseconds 500
    if (Test-Puerto) { break }
}
if (-not (Test-Puerto)) {
    Write-Host '  El motor noLevanto. Last lines of the log:' -ForegroundColor Red
    Get-Content $err -Tail 10 -ErrorAction SilentlyContinue | ForEach-Object { Write-Host "    $_" -ForegroundColor DarkGray }
    exit 1
}

$salud = Invoke-RestMethod -Uri "http://127.0.0.1:$puerto/api/health" -TimeoutSec 20
Write-Host ('  [ok] Motor RAG  |  {0} fragmentos | {1} documentos | embeddings {2}' -f `
    $salud.indice.chunks, $salud.indice.documentos, $salud.embed_model) -ForegroundColor Green
Write-Host ('       Modo A: {0}   |   Modo B (informe MDS): {1}' -f $salud.llm_model, $salud.llm_model_b) -ForegroundColor DarkGray

Write-Host ''
Start-Process "http://127.0.0.1:$puerto"
Write-Host '  Abriendo http://127.0.0.1:' + $puerto -ForegroundColor Cyan

if ($Red) {
    $ip = Get-IP-Local
    if ($ip) {
        Write-Host ''
        Write-Host '  Tambien podes usarlo desde el celu, en la misma wifi:' -ForegroundColor Cyan
        Write-Host ('      http://{0}:{1}' -f $ip, $puerto) -ForegroundColor White
    }
}

Write-Host ''
Write-Host '  Para frenarlo: DETENER.cmd   (o cerrá la ventana minimizada)' -ForegroundColor DarkGray
Write-Host ''
exit 0
