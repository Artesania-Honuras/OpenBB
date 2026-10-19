# Manual de cambios

Cada cambio aplicado tiene una entrada `C-NN`. Formato en `Plantillas.md`.
Un cambio sin evidencia numérica no entra aquí: es una hipótesis.

---

## C-01 — Instalación editable del monorepo con uv

- **Fecha:** 2026-10-19
- **Qué:** venv `venvs\openbb` con Python 3.13.12 y 37 paquetes instalados en modo editable desde `repos\OpenBB`, usando `openbb_platform\dev_install.py --routers`.
- **Por qué:** correr todo desde el código fuente y en local, sin depender del paquete publicado ni de servicios cloud.
- **Evidencia:** `uv pip check` → 243 paquetes compatibles, 0 conflictos; build reporta 584 comandos, 18 providers.
- **Reversión:** borrar `venvs\openbb` y recrear con `uv venv --python 3.13` + el instalador.

---

## C-02 — Excluir el provider `eia`

- **Fecha:** 2026-10-19
- **Qué:** el provider `eia` no se instala.
- **Por qué:** su `hatch_build.py` regenera un catálogo contra la API en vivo y falla sin `EIA_API_KEY`, abortando toda la instalación.
- **Evidencia:** la instalación completa termina correctamente al excluirlo.
- **Reversión:** instalarlo con `EIA_API_KEY` disponible y reconstruir.

---

## C-03 — Forzar SSL a certifi

- **Fecha:** 2026-10-19
- **Qué:** `SSL_CERT_FILE` y `REQUESTS_CA_BUNDLE` apuntan a `venvs\openbb\Lib\site-packages\certifi\cacert.pem` en los lanzadores.
- **Por qué:** el almacén de certificados de Windows falla contra `data-api.ecb.europa.eu`.
- **Evidencia:** `EURUSD` por `ecb` devuelve 7.117 filas (antes fallaba).
- **Reversión:** quitar las dos variables de `run-openbb-api.ps1` y `run-openbb-shell.ps1`.

---

## C-04 — `OPENBB_AUTO_BUILD=false`

- **Fecha:** 2026-10-19
- **Qué:** se desactiva el autobuild permanente; el build se ejecutó una sola vez de forma explícita.
- **Por qué:** `import openbb` se colgaba durante el auto-build en este equipo.
- **Evidencia:** arranque de la API en ~60 s, sin cuelgues; 50 entry points cargan con 0 errores.
- **Reversión:** quitar la variable del entorno (volverá a intentar autobuild).

---

## C-05 — UTF-8 forzado

- **Fecha:** 2026-10-19
- **Qué:** `PYTHONUTF8=1` y `PYTHONIOENCODING=utf-8` en los lanzadores.
- **Por qué:** `openbb-api --help` lanzaba `UnicodeEncodeError` con cp1252.
- **Evidencia:** ayuda y consola sin errores de codificación.
- **Reversión:** quitar ambas variables.

---

## C-06 — Puente OpenBB → Freqtrade

- **Fecha:** 2026-10-19
- **Qué:** `scripts\puente_freqtrade.py` (exportar/fusionar), dos estrategias de ejemplo y `freqtrade_bridge\backtest.json`.
- **Por qué:** aportar contexto macro a Freqtrade sin tocar los bots en marcha (7 instancias activas).
- **Evidencia:** contexto de 36.636 filas × 13 columnas; merge con 14.886 velas 4h; 0 NaN en 2026.
- **Reversión:** borrar los tres artefactos. No afecta a Freqtrade: nada se escribió en su repositorio.

---

## C-07 — Histórico completo en `treasury_rates` y `effr`

- **Fecha:** 2026-10-19
- **Qué:** `start_date="2000-01-01"` en ambas consultas.
- **Por qué:** el valor por defecto devolvía **solo 1 año**, dejando el filtro macro inactivo casi todo el periodo y falseando la comparación (E-03).
- **Evidencia:** de 248 a 6.700 filas; cobertura del 100 % desde 2021.
- **Reversión:** quitar el parámetro (vuelve al default de 1 año).

---

## C-08 — Marco de validación walk-forward + Monte Carlo

- **Fecha:** 2026-10-19
- **Qué:** `scripts\validar_estrategia.py` con `--pair`, `--todos` y `--stake`; reporta exposición, ventanas positivas, Monte Carlo y referencia ajustada.
- **Por qué:** un backtest único elige parámetros mirando el resultado; hay que separar entrenamiento de prueba.
- **Evidencia:** 11 ventanas, 129 operaciones fuera de muestra en BTC; 7/7 activos positivos y **0/7** baten la referencia.
- **Reversión:** borrar el script; no altera datos ni configuración.

---

## C-09 — Memoria persistente y repositorio Git

- **Fecha:** 2026-10-19
- **Qué:** `boveda\` con 5 archivos, `CLAUDE.md` con reglas, `estado.py` (checklist de solo lectura), `.gitignore`, repo `OpenBB` público en GitHub.
- **Por qué:** memoria auditable dentro del propio proyecto, versionada, sin dependencias de terceros.
- **Evidencia:** repo público `https://github.com/Artesania-Honuras/OpenBB`, commit inicial `f4fe7b5` con 22 archivos (0,6 MB); `estado.py` → 22/22 chequeos ✅.
- **Reversión:** `git revert` del commit de memoria o borrar `boveda\` y `CLAUDE.md`.

---

## C-10 — Manual de uso en el repositorio

- **Fecha:** 2026-10-19
- **Qué:** `README.md` con el manual completo: qué es, requisitos, estructura, arranque, verificación, uso diario, comandos, problemas, datos, reglas, estado y cómo retomar.
- **Por qué:** el usuario necesita revisarlo fuera de la sesión, directamente en GitHub, sin depender del chat.
- **Evidencia:** documento de 12 secciones con índice enlazado; enlace añadido en `boveda\INDICE.md`.
- **Reversión:** borrar `README.md` y la línea de referencia en el índice.

---

## C-11 — Panel visual 100 % local (Streamlit)

- **Fecha:** 2026-10-19
- **Qué:** `app.py` + `run-openbb-app.ps1`. Panel con 7 pestañas (Resumen, Tipos, Riesgo, Macro, Posicionamiento, Contexto Freqtrade, API) que consume la API local en `127.0.0.1:6900`; se abre en `127.0.0.1:8501`.
- **Por qué:** OpenBB Workspace fue reemplazado por BQ Workspace, que aún no está disponible ("coming soon"), así que la única forma de tener interfaz visual es local.
- **Evidencia:** `AppTest` → 0 excepciones, 7 pestañas, 16 métricas; panel respondiendo en 4 s; `estado.py` → 23/23 ✅.
- **Reversión:** borrar `app.py` y `run-openbb-app.ps1`; desinstalar `streamlit` si se desea.

---

## C-12 — Panel traducido, guía y lectura de régimen

- **Fecha:** 2026-10-19
- **Qué:** `app.py` reescrito: 8 pestañas (se añade **Guía**), todo en español, tablas con columnas traducidas (se eliminan percentiles y campos internos), cajas de interpretación, semáforo de entorno (favorable / neutral / defensivo) y ayuda en cada métrica.
- **Corrección incluida:** la pendiente 10a-2a se mostraba en puntos porcentuales como si fueran puntos básicos (**+0 pb** en vez de **+33 pb**). Ahora se multiplica por 10.000.
- **Por qué:** el usuario no entendía qué mostraba el panel ni para qué sirve en trading.
- **Evidencia:** `AppTest` → 0 excepciones, 8 pestañas, 16 métricas; pendiente verificada contra datos crudos (4,77 % a 2 años y 5,10 % a 10 años → +33 pb).
- **Reversión:** volver a la versión anterior de `app.py` en Git.

---

## C-13 — Bug de alineación temporal en el puente (pérdida del dato más reciente)

- **Fecha:** 2026-10-19
- **Qué:** `construir_contexto()` retrasaba cada serie con `shift(freq=1D)` y luego la **asignaba** a la columna del DataFrame. Pandas realinea esa asignación por fecha y descarta los valores cuya fecha desplazada no existe en el índice (sábados, domingos y festivos). Consecuencia: el VIX del viernes se perdía y el lunes seguía mostrando el del jueves (16,46 en vez de 19,99).
- **Arreglo:** se reindexa cada serie desplazada a un calendario diario común (`date_range` + `reindex` + `ffill`), extendido hasta hoy.
- **Evidencia:** antes → `vix 16.46` en 2026-10-17/18/19; después → `vix 19.99` (valor real del 16-10). SPX corregido a 7659,44. 36.636 filas · 13 columnas · 0 NaN en 2026.
- **Impacto declarado:** los backtests previos (walk-forward de 7 pares y Monte Carlo) se ejecutaron con el contexto de este defecto, es decir, con el dato de riesgo hasta 3 días viejo los lunes. **No se han revalidado** tras el arreglo.
- **Reversión:** `git revert` del commit; el efecto es volver a perder el último dato de cada serie en los findes.

---

## C-14 — Nota de reanudación tras reiniciar o actualizar el equipo

- **Fecha:** 2026-10-19
- **Qué:** nueva subsección en la sección 12 de `README.md`: qué relanzar después de un reinicio (las dos ventanas: API y panel), la verificación esperada (23/23) y el refresco del contexto. Se añade `P8` a la tabla de pendientes del manual.
- **Por qué:** el usuario anunció una actualización del equipo; nada arranca solo y las dos ventanas mueren al reiniciar.
- **Evidencia:** `README.md` §12 con los dos comandos y el criterio numérico de éxito.
- **Reversión:** borrar la subsección y la fila `P8`.

---

## C-15 — Regla de bóveda única (corregido un error propio)

- **Fecha:** 2026-10-19
- **Qué:** se añade a `CLAUDE.md` la sección **REGLA DE BÓVEDA ÚNICA** y una fila equivalente en `boveda/INDICE.md` §2. El registro vive solo en `OpenBB\boveda\` y `README.md`; se prohíbe explícitamente escribir en `seconBrain`, en `C:\Users\DELL\.claude\` o en cualquier repo ajeno.
- **Por qué:** en esta sesión, siguiendo un ritual externo de cierre, se escribieron una página, una línea de índice y una entrada de log en la bóveda `C:\Users\DELL\.ipython\seconBrain\wiki\`. El usuario lo corrigió: el registro debe estar todo en `OpenBB\boveda`.
- **Corrección aplicada:** deshechos los tres cambios en `seconBrain` (página borrada, índice y log revertidos a su texto anterior) sin tocar los cambios que el usuario ya tenía pendientes allí. Nada de OpenBB se commiteó en ese repositorio.
- **Evidencia:** `git status` de `seconBrain` sin rastro de OpenBB; los pendientes que había antes de empezar siguen igual. Regla escrita en `CLAUDE.md` (línea 1 del archivo la enlaza: "MAPA DEL PROYECTO").
- **Reversión:** quitar la sección y la fila del resumen.

---

## C-16 — Plan de mejora registrado en la bóveda

- **Fecha:** 2026-10-19
- **Qué:** nuevo documento `boveda/Plan de mejora.md`: inventario de lo que ya existe, las 12 fuentes de OpenBB sin usar (F1-F12) con su relación con Freqtrade, los 5 déficits declarados (D1-D5), el mapa de integración con Freqtrade por niveles (1-6), los 3 packs de trabajo (A/B/C) con esfuerzo y objetivo, y el orden propuesto con puertas de validación. Enlace añadido en `INDICE.md` §3.
- **Por qué:** el usuario pidió el plan por escrito dentro de la bóveda del proyecto (no en el chat, no en otra bóveda).
- **Evidencia:** documento con 12 secciones; inventario de rutas obtenido de `openapi.json` (869 rutas, 18 providers).
- **Impacto:** **ninguno** sobre el código o los datos. Es planificación, no cambio. Nada de lo descrito se aplica hasta que el usuario elija pack y pase la puerta de validación.
- **Reversión:** borrar el documento y la fila del índice.

---

## C-17 — Revalidación con el contexto corregido y documentación actualizada

- **Fecha:** 2026-10-19
- **Qué:** ejecutado el paso 0 del plan. `validar_estrategia.py --todos --stake 0.1` con el contexto corregido; resultados anotados como `E-07`. Actualizados `README.md` §11 (tabla de validación y fila P8), `INDICE.md` (evidencia de D-08 y P8 cerrado) y `Plan de mejora.md` (paso 0 cerrado).
- **Por qué:** medir sobre números que ya no eran válidos invalidaba el plan de mejora.
- **Evidencia:** 7/7 OOS positivos, **1/7 baten la referencia** (ADA +5,8 % vs +5,5 %); antes 0/7. Salida completa en `data/reporte_validacion.txt`.
- **Conclusión:** el defecto `C-13` no era la causa de la falta de edge. `D-08` (no integrar) sigue vigente; `P1` sigue siendo el bloqueo.
- **Impacto:** solo documentación y una medición. **Nada** se cambió en el código, en los datos de contexto ni en los bots.
- **Reversión:** revertir el commit.

---

## C-18 — Capa rápida: fuente externa de funding y 14ª columna del contexto

- **Fecha:** 2026-10-19
- **Qué:** nuevo `scripts/fuentes_externas.py` que trae el **funding de perpetuos** desde el endpoint público de Binance (`fapi/v1/fundingRate`), paginado desde 2021, con caché en `data/cache/`. El puente añade la columna `funding_btc_anual` (media diaria, en % anual, retraso de 1 día). El contexto pasa de 13 a **14 columnas**. Actualizados `estado.py` (esquema 14) y `app.py` (etiqueta en español y métrica en la pestaña Contexto).
- **Por qué:** el paso 1 del pack A. Los endpoints de derivados de OpenBB (`deribit/*`) solo devuelven ventanas cortas —funding 31 días, volatilidad realizada 17, índice 1— así que sirven para el estado en vivo pero **no** para validar 2021-2026. Se descartó añadir `ccxt`: el endpoint público se consume solo con `urllib`, sin dependencias nuevas.
- **Evidencia:** 2.118 días de funding (2021-01-01 → 2026-10-19); media +10,7 % anual, rango −93 % a +178 %; contexto exportado 36.636 × 14.
- **Reversión:** borrar `scripts/fuentes_externas.py`, quitar la columna del puente y volver los contadores a 13.

---

## C-19 — Dimensiones de funding en el validador

- **Fecha:** 2026-10-19
- **Qué:** `validar_estrategia.py` acepta `funding_max` y `funding_min` como filtros de entrada. `funding_max` entra en el grid con dos opciones (None / 20 %); `funding_min` se deja con una sola opción (None) para que los experimentos dirigidos la activen sin ampliar la búsqueda por defecto. La tabla del walk-forward muestra si cada ventana eligió filtro.
- **Por qué:** sin una dimensión en el validador, añadir la columna no se podría medir, y el proyecto exige medición antes que cambio.
- **Evidencia:** corrida por defecto 54 → 108 combinaciones; A/B dirigido en `data/reporte_funding_ab.txt`; resultado en `E-08`.
- **Impacto declarado:** ampliar la búsqueda aumenta el riesgo de sobreajuste. Queda anotado en `E-08`.
- **Reversión:** quitar ambas claves y el bloque de filtro en `simular()`.

---

## C-20 — Motor de salidas configurable y modo `--salidas`

- **Fecha:** 2026-10-19
- **Qué:** `scripts/validar_estrategia.py` gana tres parámetros de salida —stop móvil (`trailing_pct`), break-even (`break_even`) y salida al perder la media rápida (`salida_ema`)—, un `GRID_SALIDAS` con 12 combinaciones, una `BASE_ENTRADA` fija (EMA 20/50, sin filtros) y la bandera `--salidas`. `walk_forward` y `evaluar_par` aceptan ahora `grid` y `base` para poder evaluar un subconjunto sin duplicar código.
- **Por qué:** el resultado de `E-08` dejaba dos sospechosos (el filtro y el *timing*). Para descartar el segundo hacía falta poder mover la salida **sin** tocar la entrada; si se movían las dos cosas a la vez, el resultado no sería atribuible.
- **Rigor del motor:** el stop dinámico se calcula **solo** con velas ya cerradas (el máximo de la vela en curso se incorpora al final del bucle). Si se usara la vela en curso para fijar el stop que esa misma vela dispara, habría look-ahead intravela.
- **Evidencia:** el modo por defecto sigue reproduciendo `E-08` exacto (0/7, mismos siete números) → el refactor no cambió el comportamiento. Resultado del experimento en `E-09`.
- **Reversión:** quitar las claves `trailing_pct` / `break_even` / `salida_ema`, `GRID_SALIDAS`, `BASE_ENTRADA` y la bandera.

---

## C-21 — El panel muestra la capa rápida en la primera pestaña

- **Fecha:** 2026-10-19
- **Qué:** `app.py` añade en **Resumen** una sección "Capa rápida: apalancamiento en cripto" con la métrica de funding, su percentil p15/p85 de un año, una lectura en una palabra (euforia / normal / pánico) y la serie de 180 días. La Guía gana la fila de funding y el aviso recoge el resultado de `E-08`.
- **Por qué:** el dato estaba solo en la pestaña "Contexto Freqtrade", que es la cuarta por la derecha; quien abría el panel no veía nada nuevo. Lo importante para el usuario es que se vea en la primera pantalla, y con la advertencia de que **no** es señal pegada al lado.
- **Reinicio obligatorio:** el proceso de Streamlit que servía el panel arrancó **antes** de estos cambios y no recarga el script por sí solo. Se detuvo y se relanzó con `run-openbb-app.ps1`. Tras un reinicio del proceso, el navegador necesita además un refresco forzado (`Ctrl+F5`).
- **Evidencia:** `streamlit.testing.v1.AppTest` → 0 excepciones, 8 pestañas, 17 métricas (aparece `Funding BTC = +6,7 % anual`), 0 `st.error`.
- **Reversión:** borrar el bloque "capa rápida" de Resumen y la fila de la Guía.
