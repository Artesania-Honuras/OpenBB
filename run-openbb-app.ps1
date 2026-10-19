# Panel visual local (Streamlit) sobre la API de OpenBB
# Uso:  .\run-openbb-app.ps1
#       .\run-openbb-app.ps1 -Port 8502

param(
    [int]$Port = 8501
)

$root = $PSScriptRoot
$streamlit = Join-Path $root "venvs\openbb\Scripts\streamlit.exe"
$app = Join-Path $root "app.py"

if (-not (Test-Path $streamlit)) {
    Write-Error "Streamlit no esta instalado en el entorno. Ejecuta: uv pip install --python .\venvs\openbb\Scripts\python.exe streamlit"
    exit 1
}

$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

Write-Host "Panel OpenBB -> http://127.0.0.1:$Port" -ForegroundColor Cyan
Write-Host "Requiere la API en http://127.0.0.1:6900 (run-openbb-api.ps1)" -ForegroundColor DarkGray

& $streamlit run $app `
    --server.address 127.0.0.1 `
    --server.port $Port `
    --server.headless true `
    --browser.gatherUsageStats false
