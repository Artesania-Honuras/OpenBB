# Consola interactiva de Python con OpenBB ya configurado (solo local)
# Uso:  .\run-openbb-shell.ps1

$root = $PSScriptRoot
$venvPython = Join-Path $root "venvs\openbb\Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    Write-Error "No existe el entorno: $venvPython"
    exit 1
}

$env:SSL_CERT_FILE = Join-Path $root "venvs\openbb\Lib\site-packages\certifi\cacert.pem"
$env:REQUESTS_CA_BUNDLE = $env:SSL_CERT_FILE
$env:OPENBB_AUTO_BUILD = "false"
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

Write-Host "Consola OpenBB. Ejemplo:" -ForegroundColor Cyan
Write-Host "  from openbb import obb"
Write-Host "  obb.fixedincome.rate.effr(provider='federal_reserve').to_df()"
Write-Host ""

# Startup opcional: deja `obb` listo y la cache disponible
$startup = @"
import sys, pathlib
sys.path.insert(0, r'$root\scripts')
from obb_env import obb_local, consultar
from openbb import obb
print('OpenBB listo.  obb / consultar() disponibles.')
"@
$startupFile = Join-Path $env:TEMP "openbb_startup.py"
Set-Content -Path $startupFile -Value $startup -Encoding UTF8

& $venvPython -i $startupFile
