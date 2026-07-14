<#
.SYNOPSIS
  NV-SynthForge — Track C (SDG + OCR) demo launcher for Windows PowerShell.

.DESCRIPTION
  Starts the offline FastAPI backend on the first free port among 8000/8001/8002
  and the Next.js frontend on 3000, wired to that backend via BACKEND_INTERNAL_URL
  (server rewrites) and NEXT_PUBLIC_API_URL (browser). Each service opens in its own
  window. Press Ctrl-C in this window (or close it) to stop both.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\demo-track-c.ps1
#>
[CmdletBinding()]
param(
  [int[]]$BackendPorts = @(8000, 8001, 8002),
  [int]$FrontendPort = 3000
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$BackendDir = Join-Path $Root 'backend'
$FrontendDir = Join-Path $Root 'frontend'
$LogDir = Join-Path $Root '.demo-logs'
$Host127 = '127.0.0.1'
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

function Test-PortFree([int]$Port) {
  $client = New-Object System.Net.Sockets.TcpClient
  try {
    $client.Connect($Host127, $Port)
    $client.Close()
    return $false  # something is listening -> not free
  } catch {
    return $true   # connection refused -> free
  }
}

$BackendPort = $null
foreach ($candidate in $BackendPorts) {
  if (Test-PortFree $candidate) { $BackendPort = $candidate; break }
  Write-Host "Port $candidate is busy, trying the next candidate..." -ForegroundColor DarkYellow
}
if ($null -eq $BackendPort) {
  Write-Error "No free backend port among $($BackendPorts -join ', ')."
  exit 1
}
$BackendUrl = "http://${Host127}:${BackendPort}"

# Prefer the project venv interpreter; fall back to `uv run`.
$VenvPy = Join-Path $BackendDir '.venv\Scripts\python.exe'
if (Test-Path $VenvPy) {
  $BackendFile = $VenvPy
  $BackendArgs = @('-m', 'uvicorn', 'app.main:app', '--host', $Host127, '--port', "$BackendPort")
} else {
  $BackendFile = 'uv'
  $BackendArgs = @('run', 'uvicorn', 'app.main:app', '--host', $Host127, '--port', "$BackendPort")
}

Write-Host "==> Backend  $BackendUrl   (logs: $LogDir\backend.log)" -ForegroundColor Cyan
$backend = Start-Process -FilePath $BackendFile -ArgumentList $BackendArgs `
  -WorkingDirectory $BackendDir -PassThru `
  -RedirectStandardOutput (Join-Path $LogDir 'backend.out.log') `
  -RedirectStandardError (Join-Path $LogDir 'backend.err.log')

# Wait (up to ~60s) for the backend health endpoint.
$backendReady = $false
for ($i = 0; $i -lt 60; $i++) {
  try {
    Invoke-WebRequest -Uri "$BackendUrl/api/v1/health" -TimeoutSec 2 -UseBasicParsing | Out-Null
    $backendReady = $true
    break
  } catch {
    Start-Sleep -Seconds 1
  }
}
if (-not $backendReady) {
  Write-Error "Backend did not become healthy — see $LogDir\backend.err.log"
  Stop-Process -Id $backend.Id -Force -ErrorAction SilentlyContinue
  exit 1
}
Write-Host "==> Backend healthy." -ForegroundColor Green

Write-Host "==> Frontend http://${Host127}:${FrontendPort}   (logs: $LogDir\frontend.log)" -ForegroundColor Cyan
$env:PORT = "$FrontendPort"
$env:BACKEND_INTERNAL_URL = $BackendUrl
$env:NEXT_PUBLIC_API_URL = $BackendUrl
$frontend = Start-Process -FilePath 'pnpm' -ArgumentList @('run', 'dev') `
  -WorkingDirectory $FrontendDir -PassThru `
  -RedirectStandardOutput (Join-Path $LogDir 'frontend.out.log') `
  -RedirectStandardError (Join-Path $LogDir 'frontend.err.log')

Write-Host ""
Write-Host "------------------------------------------------------------------"
Write-Host "NV-SynthForge — Track C demo is starting."
Write-Host ""
Write-Host "  Studio    http://${Host127}:${FrontendPort}/studio?domain=invoices"
Write-Host "  OCR       http://${Host127}:${FrontendPort}/ocr"
Write-Host "  API docs  $BackendUrl/docs"
Write-Host ""
Write-Host "  Backend    $BackendUrl"
Write-Host "  Smoke test `$env:API_BASE='$BackendUrl'; python scripts\ocr-demo-smoke.py"
Write-Host ""
Write-Host "The frontend needs a few seconds to compile on first load."
Write-Host "Press Ctrl-C to stop both services."
Write-Host "------------------------------------------------------------------"

try {
  while (-not $backend.HasExited -and -not $frontend.HasExited) {
    Start-Sleep -Seconds 1
  }
} finally {
  Write-Host ""
  Write-Host "Stopping demo services..."
  Stop-Process -Id $backend.Id -Force -ErrorAction SilentlyContinue
  Stop-Process -Id $frontend.Id -Force -ErrorAction SilentlyContinue
}
