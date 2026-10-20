# Lanzador oculto para la tarea programada.
#
# Por que existe: una tarea interactiva que ejecuta python.exe directamente
# abre una ventana de consola durante todo el refresco (~2 minutos). Este
# envoltorio arranca PowerShell sin ventana, llama al script y **propaga el
# codigo de salida** para que el Programador de tareas registre el fallo
# (LastTaskResult != 0) en vez de dar exito siempre.
$root = Split-Path -Parent $PSScriptRoot
$py = Join-Path $root "venvs\openbb\Scripts\python.exe"
$script = Join-Path $root "scripts\refrescar_contexto.py"

& $py $script
exit $LASTEXITCODE
