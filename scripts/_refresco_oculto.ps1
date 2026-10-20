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
$avisar = Join-Path $root "scripts\avisar.py"

& $py $script
$refresco = $LASTEXITCODE

# El aviso corre aunque el refresco falle: es cuando mas falta hace. Su
# resultado no cambia el de la tarea (si el envio falla, queda en
# data\avisos.log); la tarea debe reflejar el refresco, no el canal.
& $py $avisar

exit $refresco
