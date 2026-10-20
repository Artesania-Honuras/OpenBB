<#
Registra (o quita) la tarea diaria que refresca el contexto macro.

Por que a las 09:05
-------------------
El contexto aplica un retraso de publicacion de 1 dia: la fila de hoy lleva el
cierre de ayer. A las 09:05 (hora local) el cierre de EE. UU. de la sesion
anterior ya esta publicado y descargado, asi que el contexto que se genera
sirve para operar todo el dia. Ejecutarlo de madrugada solo añadiria huecos.

Si el equipo estaba apagado a esa hora, la tarea se ejecuta al encenderlo
(`-StartWhenAvailable`): un refresco tarde es mejor que ninguno.

Uso:
    powershell -ExecutionPolicy Bypass -File scripts\instalar_refresco.ps1
    powershell -ExecutionPolicy Bypass -File scripts\instalar_refresco.ps1 -Hora 21:30
    powershell -ExecutionPolicy Bypass -File scripts\instalar_refresco.ps1 -Quitar
#>
param(
    [string]$Hora = "09:05",
    [switch]$Quitar
)

$ErrorActionPreference = "Stop"
$root   = Split-Path -Parent $PSScriptRoot
$nombre = "OpenBB - refresco de contexto"
$py     = Join-Path $root "venvs\openbb\Scripts\python.exe"
$script = Join-Path $root "scripts\refrescar_contexto.py"

if ($Quitar) {
    $t = Get-ScheduledTask -TaskName $nombre -ErrorAction SilentlyContinue
    if ($t) {
        Unregister-ScheduledTask -TaskName $nombre -Confirm:$false
        "Tarea eliminada: $nombre"
    } else {
        "No existia la tarea: $nombre"
    }
    exit 0
}

if (-not (Test-Path $py))     { throw "No existe el interprete: $py" }
if (-not (Test-Path $script)) { throw "No existe el script: $script" }

# Se lanza a traves de un envoltorio oculto: python.exe directo abriria una
# consola visible durante todo el refresco. El envoltorio propaga el codigo de
# salida, asi que el Programador de tareas sigue registrando los fallos.
$lanzador = Join-Path $root "scripts\_refresco_oculto.ps1"
$accion = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$lanzador`"" `
    -WorkingDirectory $root
$disparo = New-ScheduledTaskTrigger -Daily -At $Hora
$ajustes = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 45) `
    -MultipleInstances IgnoreNew

$usuario = "$env:USERDOMAIN\$env:USERNAME"
$principal = New-ScheduledTaskPrincipal -UserId $usuario -LogonType S4U -RunLevel Limited

if (Get-ScheduledTask -TaskName $nombre -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $nombre -Confirm:$false
    "Tarea anterior retirada (se vuelve a registrar)."
}

try {
    Register-ScheduledTask -TaskName $nombre -Action $accion -Trigger $disparo `
        -Settings $ajustes -Principal $principal `
        -Description "Refresca data/context/contexto_diario.parquet, lo valida y conserva el anterior si falla." | Out-Null
} catch {
    Write-Warning "S4U no disponible ($($_.Exception.Message))."
    Write-Warning "Se registra en modo interactivo: solo correra con la sesion abierta."
    $principal = New-ScheduledTaskPrincipal -UserId $usuario -LogonType Interactive -RunLevel Limited
    Register-ScheduledTask -TaskName $nombre -Action $accion -Trigger $disparo `
        -Settings $ajustes -Principal $principal `
        -Description "Refresca data/context/contexto_diario.parquet, lo valida y conserva el anterior si falla." | Out-Null
}

$info = Get-ScheduledTaskInfo -TaskName $nombre
"Tarea registrada: $nombre"
"  usuario   : $usuario"
"  diaria a  : $Hora"
"  estado    : $((Get-ScheduledTask -TaskName $nombre).State)"
"  proxima   : $($info.NextRunTime)"
"  ultimo    : $($info.LastRunTime)  resultado $($info.LastTaskResult)"
"  log       : data\refresco_contexto.log"
""
"Pruebala ahora:  Start-ScheduledTask -TaskName '$nombre'"
"Quitala:         powershell -ExecutionPolicy Bypass -File scripts\instalar_refresco.ps1 -Quitar"
