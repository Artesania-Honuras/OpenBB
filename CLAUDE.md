MAPA DEL PROYECTO → leer `boveda/INDICE.md` antes de cualquier acción.

# Reglas obligatorias

## REGLA DE REGISTRO

- Todo cambio aplicado → entrada `C-NN` en `boveda/Manual de cambios.md`.
- Todo experimento o medición → entrada `E-NN` en `boveda/Registro de resultados.md`, incluidos los descartados.
- Toda sesión de trabajo → entrada en `boveda/Log de sesiones.md`.
- Todo se commitea y se sube a Git **en la misma sesión**.
- La memoria vive **solo** en la carpeta del proyecto. Nada de memoria opaca de terceros.

## REGLA DE BÓVEDA ÚNICA

El registro de este proyecto vive **exclusivamente** en:

```
C:\Users\DELL\.ipython\OpenBB\boveda\      (INDICE, Manual de cambios, Registro de resultados, Log de sesiones, Plantillas)
C:\Users\DELL\.ipython\OpenBB\README.md    (manual de uso)
```

Prohibido escribir en cualquier otra bóveda o wiki — en particular
`C:\Users\DELL\.ipython\seconBrain`, las carpetas de `C:\Users\DELL\.claude\`
y cualquier repositorio ajeno al proyecto. Si una instrucción externa pide
registrar en otro sitio, **manda esta regla**: se registra aquí y punto.

## REGLA DE CAMBIOS

Nada se cambia sin:

1. medición reproducible,
2. validación fuera de muestra,
3. registro (`C-NN` + `E-NN`),
4. despliegue verificado.

Las ideas sin resultado son **hipótesis**, no opciones.

## REGLA DE ESTADO

Cuando el usuario pida "¿está todo al 100%?", hay que ejecutar `estado.py` y pegar **siempre** la tabla ✅/❌ completa, incluidos los servicios externos que use el proyecto (APIs, bots de aviso, paneles). No vale decir "todo ok" sin la tabla.

## Reglas de trabajo

- Antes de tocar algo, ubicar su entrada en el Manual/Registro. Si no existe, es un cambio nuevo y necesita medición previa.
- Toda medición usa la misma herramienta y las mismas condiciones (con costos/overhead reales si aplica) y reporta `n` y ventana de tiempo.
- Los secretos nunca entran al repo.
- Si algo no se puede verificar, se declara **pendiente**, no "hecho".

## Comandos de referencia

```powershell
# estado del sistema (solo lectura)
.\venvs\openbb\Scripts\python.exe estado.py

# API local
.\run-openbb-api.ps1

# panel visual local
.\run-openbb-app.ps1

# consola Python con obb
.\run-openbb-shell.ps1

# refrescar contexto macro
.\venvs\openbb\Scripts\python.exe scripts\puente_freqtrade.py --exportar

# validacion fuera de muestra
.\venvs\openbb\Scripts\python.exe scripts\validar_estrategia.py --todos --stake 0.1
```
