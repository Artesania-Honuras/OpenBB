# Lanzador local del Open Data Platform (OpenBB) - solo localhost
# Uso:  .\run-openbb-api.ps1
#       .\run-openbb-api.ps1 -Port 6901

param(
    [string]$Host_ = "127.0.0.1",
    [int]$Port = 6900
)

$root = $PSScriptRoot
$venvPython = Join-Path $root "venvs\openbb\Scripts\python.exe"
$apiExe = Join-Path $root "venvs\openbb\Scripts\openbb-api.exe"

if (-not (Test-Path $venvPython)) {
    Write-Error "No existe el entorno: $venvPython"
    exit 1
}

# 1) Certificados: el almacen de Windows falla con la API del BCE (data-api.ecb.europa.eu).
#    El bundle de certifi si funciona, asi que lo forzamos para todo el proceso.
$env:SSL_CERT_FILE = Join-Path $root "venvs\openbb\Lib\site-packages\certifi\cacert.pem"
$env:REQUESTS_CA_BUNDLE = $env:SSL_CERT_FILE

# 2) Sin autobuild: el build ya se ejecuto una vez (openbb.build()).
#    Evita que el import inicial se quede colgado.
$env:OPENBB_AUTO_BUILD = "false"

# 3) Consola en UTF-8 (evita UnicodeEncodeError del --help en cp1252)
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

Write-Host "OpenBB API -> http://$Host_`:$Port" -ForegroundColor Cyan
& $apiExe --host $Host_ --port $Port
