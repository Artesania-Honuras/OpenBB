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

---

## C-22 — Validador de momentum transversal contra el azar

- **Fecha:** 2026-10-19
- **Qué:** nuevo `scripts/validar_momentum.py`: matriz de cierres alineada de los 7 pares, cartera que mantiene los *K* mejores por retorno de *L* días con rebalanceo periódico, rejilla de 18 combinaciones con selección en entrenamiento, y una **prueba de permutación** de 200 semillas que elige los pares al azar con el mismo K y el mismo calendario. Incluye `max_dd()` y comparación con la cesta a peso igual.
- **Por qué:** la puerta del proyecto necesita una referencia honesta, y en una cartera "elegir al azar los mismos K activos" es la referencia exacta: misma exposición y misma diversificación por construcción, así que cualquier diferencia es atribuible al criterio de selección.
- **Rigor:** el ranking usa el cierre de la vela *i*, pero los pesos entran desde la vela *i+1*; el coste se aplica sobre el giro real (`FEE × Σ|Δw|`). Sin filtros macro, a propósito, para aislar la selección.
- **Evidencia:** `data/reporte_momentum.txt` (walk-forward + nube al azar), `data/reporte_momentum_robustez.txt` (18 combinaciones fijas × 200 permutaciones). Resultado en `E-10`.
- **Reversión:** borrar el script y los dos reportes.

---

## C-23 — Control de riesgo en el validador de momentum y criterio Calmar por defecto

- **Fecha:** 2026-10-19
- **Qué:** `scripts/validar_momentum.py` gana: `preparar_senales()` (régimen por media de la cesta y escala por volatilidad objetivo), soporte de esas señales dentro de `simular()` —salida inmediata a caja al perder el régimen, vuelta solo en rebalanceo, pesos escalados con el resto en caja—, `calmar()` como criterio de selección en entrenamiento, la bandera `--riesgo` con la tabla de 6 variantes y las banderas `--ma`, `--vol`, `--objetivo`.
- **Por qué:** `E-10` dejó el momentum con ventaja pero con drawdown del 77-93 %. Había que medir si el control de riesgo lo arreglaba, y con la referencia corregida (la nube al azar lleva las **mismas** señales de riesgo).
- **Cambio de comportamiento:** el criterio de selección por defecto pasa de **retorno bruto a Calmar**. Es un cambio de resultado, no de forma: `--objetivo retorno` reproduce `E-10` exacto (+1.112 %, DD −81,8 %), y el nuevo defecto da `E-11` variante B (+1.538 %, Calmar 19,22).
- **Rigor:** las señales se calculan sobre la serie completa y se recortan por ventana. Es correcto (cada fecha usa solo datos pasados) y necesario: una media de 200 días no cabe en una ventana de prueba de 6 meses. La venta por pérdida de régimen se cobra con comisión; la vuelta espera al rebalanceo.
- **Evidencia:** `data/reporte_momentum_riesgo.txt`; verificación de regresión antes del cambio (la línea base reprodujo `E-10` número a número). Resultado en `E-11`.
- **Reversión:** `--objetivo retorno` y no usar `--ma`/`--vol`. Para revertir el código, quitar `preparar_senales`, las señales de `simular` y el bloque `--riesgo`.

---

## C-24 — Momentum absoluto por activo en el validador

- **Fecha:** 2026-10-19
- **Qué:** `preparar_senales()` devuelve ahora un diccionario con `en_mercado`, `escala` y `tendencia` (matriz fecha × activo con la tendencia propia de cada uno). `simular()` filtra el ranking por esa tendencia y reparte el peso entre los elegibles (si no hay ninguno, caja). La nube al azar usa **el mismo filtro**. Añadidas las variantes G/H/I y la bandera `--tendencia`.
- **Por qué:** `E-11` demostró que los filtros sobre la cesta llegan tarde; el filtro por activo es el mecanismo estándar (dual momentum) y había que medirlo, no suponerlo.
- **Nota técnica:** el generador de la nube al azar pasa de `rng.choice` a `rng.permutation` porque con el filtro hace falta un **orden** aleatorio que luego se filtra. Es el mismo subconjunto uniforme, pero consume el generador de otra forma: los retornos se reproducen exactos, los percentiles no (variación ≤ 2,5 puntos). Declarado en `E-12`.
- **Evidencia:** `data/reporte_momentum_riesgo.txt` (9 variantes). Resultado en `E-12`.
- **Reversión:** quitar `tendencia` de `preparar_senales`, el bloque de filtrado en `simular` y las variantes G/H/I.

---

## C-25 — Pestaña «Estrategia» en el panel

- **Fecha:** 2026-10-19
- **Qué:** `app.py` gana una novena pestaña con: la **puerta de graduación** (4 criterios y su estado, todos ❌), el aviso de que no se instala nada en Freqtrade, la tabla de los experimentos `E-07`…`E-11` con su veredicto, y los **reportes crudos** de `data/reporte_*.txt` en desplegables (descubiertos automáticamente, truncados a las últimas 120 líneas).
- **Por qué:** el usuario dijo dos veces que «la app sigue igual», y tenía razón en el fondo: el panel solo mostraba el contexto macro. Todo el trabajo de validación —que es el objetivo del proyecto— no aparecía en ninguna parte. Un resultado que no se ve no existe para quien lo usa.
- **Decisión de diseño:** los números de los reportes se leen **de los archivos**, no se copian en el código. La única tabla escrita a mano es la de veredictos, que es texto estable. Así no hay dos fuentes de verdad.
- **Evidencia:** `AppTest` → 0 excepciones, **9 pestañas**; el único `st.error` es el aviso intencionado de «nada se instala en Freqtrade».
- **Reversión:** quitar `tab_estrategia` de la lista de pestañas y su bloque.

---

## C-26 — Descarga de velas y verificación de la cola

- **Fecha:** 2026-10-19
- **Qué:** `scripts/descargar_velas.py`: baja velas 4h del endpoint público de Binance (`/api/v3/klines`, paginando de 1000 en 1000) para una lista de pares curada, y **verifica** cada archivo (primera/última fecha, huecos, duplicados, días de retraso). Escribe `data/reporte_velas.txt` y avisa de los pares que no llegan a la fecha final común.
- **Por qué:** al ir a ampliar el universo descubrí que los 7 archivos originales **no terminaban en la misma fecha** (4 de 7 el 2026-09-18, los otros el 2026-10-17) y que `cargar_matriz` rellena hacia adelante (`ffill`): 29 días con 4 de 7 precios congelados en `E-10`…`E-12`. La verificación descartó a **EOS** por retirado (512 días de retraso): sin la comprobación habría repetido el defecto con otro par.
- **Decisión:** **no se adopta `CCXT`** para esto. Una sola fuente y una sola temporalidad no lo necesitan (`urllib`, igual que `fuentes_externas.py`); el disparador para CCXT sigue siendo multi-exchange o multi-temporalidad. Registrado en `Ecosistema de herramientas.md`.
- **Evidencia:** `data/reporte_velas.txt` (24 de 25 pares con última vela 2026-10-19 20:00 UTC; 1 hueco de 8 h en los pares viejos, probablemente mantenimiento de Binance; 0 duplicados).
- **Reversión:** borrar el script y el reporte; los archivos de velas se pueden regenerar.

---

## C-27 — Universo de 24 pares homogéneos y `--pares` en el validador

- **Fecha:** 2026-10-19
- **Qué:** los 7 archivos de velas se **reemplazan** por 24 pares descargados de la misma fuente y todos terminando en la misma vela (2020-01-01 → 2026-10-19; la matriz común arranca el 2020-09-22, lo que fija AVAX, igual que antes). Los archivos viejos quedan copiados en `data/cache/velas_antes_2026-10-19/` (ignorado por git). Añadido `--pares` a `validar_momentum.py` para poder reproducir cualquier medición anterior sobre un subconjunto.
- **Por qué:** sin homogeneidad no se puede comparar nada: el `ffill` convierte un par desfasado en un par con el precio quieto. Y sin `--pares`, ampliar el universo destruía la reproducibilidad de `E-10`/`E-11`.
- **Evidencia:** `E-13`; `--pares` de 7 reproduce `E-11` B exacto con datos limpios (+1.538,1 % / −80,0 % / Calmar 19,22).
- **Reversión:** restaurar los archivos desde `data/cache/velas_antes_2026-10-19/` y quitar `--pares`.

---

## C-28 — Configuración fija en el validador (`--fijo`)

- **Fecha:** 2026-10-19
- **Qué:** `--fijo "L,K,rebal[;...]"`: simula **un solo juego de parámetros** de principio a fin (sin re-optimizar), con la nube al azar usando esos mismos parámetros y el desglose ventana a ventana. Imprime la tabla de todas las configuraciones pedidas para no ocultar la dispersión.
- **Por qué:** el walk-forward elige parámetros en cada ventana; eso es out-of-sample legítimo pero **no es lo que se instala**. Sin esta medición, el número que se lleva a Freqtrade sería una extrapolación.
- **Evidencia:** `E-14`, `data/reporte_momentum_fijo.txt`.
- **Reversión:** quitar `fijo()`, el bloque `--fijo` y el argumento.

---

## C-29 — Dimensionado del sleeve (`scripts/dimensionar.py`)

- **Fecha:** 2026-10-19
- **Qué:** bootstrap por bloques de 7 días (1.000 caminos) sobre la curva de la configuración fija, con fracción de sleeve **constante**, y tabla de CAGR / drawdown típico / drawdown al 5 % peor / P(DD>20 %) / P(año perdedor) para 5-30 % de capital. Escribe `data/reporte_dimensionado.txt` y `.csv`.
- **Por qué:** la puerta pide `DD < 20 %`, y eso solo tiene sentido **a nivel de cartera**. Traducir el −82,5 % del sleeve a un número de cartera no es una regla de tres: hace falta la distribución.
- **Error corregido durante el desarrollo:** la primera versión modelaba el sleeve **sin rebalanceo** y daba un drawdown del 31 % con solo el 5 % invertido — imposible. El modelo estaba mal (un sleeve que crece acaba siendo el 80 % de la cartera), no el riesgo alto. Se cambió a fracción constante y quedó documentado en `E-15`.
- **Evidencia:** `E-15`.
- **Reversión:** borrar el script y sus dos reportes.

---

## C-30 — Huella de versión en la barra lateral

- **Fecha:** 2026-10-19
- **Qué:** la barra lateral muestra `Versión del panel: AAAA-MM-DD HH:MM · N reportes`, tomando la fecha de modificación de `app.py` y contando los `data/reporte_*.txt`.
- **Por qué:** el usuario ha dicho **tres veces** que «la app sigue igual». El problema real es que una pestaña abierta antes de un reinicio se queda con la imagen vieja y **no hay forma de distinguirlo mirando la pantalla**. Con la huella, la pregunta «¿estoy viendo la versión nueva?» se responde en un segundo: si la hora no coincide con la última modificación de `app.py`, es una pestaña vieja.
- **Evidencia:** PID reiniciado 16:35:51, `app.py` modificado 16:35:26, health `ok`.
- **Reversión:** quitar las dos líneas de `st.caption` del final del bloque de la barra lateral.

---

## C-31 — `--pares` en el validador por activo

- **Fecha:** 2026-10-19
- **Qué:** `validar_estrategia.py` acepta `--pares A,B,C`; al haber más de uno activa la tabla resumen (antes solo la activaba `--todos`).
- **Por qué:** `--todos` recorre **todos** los archivos del directorio, y con la ampliación a 24 pares (`C-27`) ese comando dejó de servir para reproducir `E-07`/`E-08`/`E-09`, que son de 7. Sin `--pares`, la documentación habría prometido una reproducción que ya no era tal.
- **Evidencia:** `--pares` de 7 en `validar_momentum.py` reproduce `E-11` exacto (mismo patrón); en `validar_estrategia.py` el cambio es el mismo criterio de rebanado.
- **Reversión:** quitar el argumento y volver a `if not args.todos: return`.

---

## C-32 — `estado.py`: dos falsos negativos que mentían sobre el sistema

- **Fecha:** 2026-10-19
- **Qué se encontró:** tras un reinicio del equipo, `estado.py` dijo **3 fallos críticos** y, entre ellos, `Freqtrade Procesos: AttributeError` y `Puertos 8080/8081: ninguno` — **con los tres bots vivos**. Dos defectos distintos:
  1. **Buscaba `freqtrade.exe` por nombre de imagen** (`tasklist /FI "IMAGENAME eq freqtrade.exe"`), pero los bots corren como **`python.exe`** con `freqtrade.exe trade ...` en la línea de comandos. Resultado: 0 procesos siempre que se lanzan así. Ahora se cuentan por **línea de comandos** (`Get-CimInstance` + `-match 'freqtrade.exe'`).
  2. **`text=True` con `PYTHONUTF8=1`**: la salida de `tasklist` viene en la codificación **OEM** de Windows, la decodificación UTF-8 reventaba en el hilo lector y el `AttributeError` tapaba la causa real. Ahora se decodifica a mano con `errors="replace"`.
- **Además:** el chequeo de puertos incluye **8082** (el bot de reporte MT5), y el nombre pasa a `Puertos 8080/8081/8082`.
- **Por qué importa:** un chequeo de estado que da falso negativo es **peor que no tenerlo**: induce a «arreglar» lo que no está roto o a desconfiar de lo que sí funciona. El caso contrario —decir ✅ con el servicio caído— habría sido peor todavía.
- **EVIDENCIA:** mismo minuto, antes y después —
  antes: `Freqtrade Procesos ❌ AttributeError` · `Puertos 8080/8081 ❌ ninguno` · veredicto 3 críticos.
  después: `Freqtrade Procesos ✅ 10 procesos` · `Puertos 8080/8081/8082 ✅ 3 escuchando (8080, 8081, 8082)` · veredicto 24/24 con la API arriba.
- **Reversión:** volver a `tasklist` por imagen y `text=True`. No se recomienda: es lo que fallaba.

---

## C-33 — Estrategia de rotacion escrita, verificada y refutada antes de instalar

- **Fecha:** 2026-10-19
- **Que se hizo:**
  1. strategies/rotacion_nucleo.py: la decision pura (momento a 30 d, top-K, calendario), sin depender de Freqtrade, para poder probarla fuera del bot.
  2. strategies/rotacion_momentum.py: el envoltorio IStrategy. stake_amount **no** se toca: la config debe traer max_open_trades = 3 y stake_amount = "unlimited"; el sleeve del 10 % se impone **financiando la cuenta**, no dentro del codigo.
  3. scripts/verificar_rotacion.py: verificacion offline contra el validador + **prueba de las 42 fases** + cesta + azar del mismo calendario.
- **Que se encontro:** la seleccion coincide **296/296** y el shift es de **30,00 dias exactos** — la logica estaba bien. El problema no era el codigo: era el **calendario**. Con el lunes 00:00, la regla da **+95,8 %** (no +820 %), **pierde contra la cesta** (+370,3 %, Calmar 4,52 vs 1,09) y **no se distingue del azar** (P = 24 %). Ver E-16.
- **Por que importa:** este es exactamente el caso para el que existe la verificacion offline. El codigo se escribio, se comprobo y **no se copio a Freqtrade ni se toco ningun bot**. El coste del error fue cero.
- **No se borra el codigo.** Se queda como implementacion de referencia y como banco de pruebas: si aparece una regla que pase la fase, el envoltorio y el verificador ya estan.
- **EVIDENCIA:** data/reporte_rotacion.txt · E-16 · D-27/D-28/D-29.
- **Reversion:** borrar los tres archivos. No se recomienda: el verificador es la herramienta que detecto el fallo.

---

## C-34 — La fase como parametro explicito en el validador

- **Fecha:** 2026-10-19
- **Que se cambio:** simular(..., fase=0), y se propaga a walk_forward, 
ube_al_azar y evaluar_config. El rebalanceo pasa de (i - L) % rebal == 0 a (i - L - fase) % rebal == 0.
- **Por que:** E-16 encontro que la fase era un parametro oculto de primer orden (40x de rango). Sin poder desplazarla, no se puede auditar nada hacia atras.
- **Garantia de no-regresion:** ase=0 es el comportamiento historico. Verificado: walk_forward con ase=0 da **+3.118,3 % / −87,1 % / Calmar 35,82 / 6/11**, identico a E-13. La auditoria mide lo mismo que se midio.
- **Ademas:** scripts\\auditar_fase.py, que repite el walk-forward en las 42 fases para los dos universos.
- **Coste:** 42 walk-forward completos ≈ **80 s** (1,9 s cada uno). La prueba de fase es barata; no hay excusa para no hacerla.
- **EVIDENCIA:** data/reporte_fase.txt · E-17.
- **Reversion:** quitar el parametro y volver a (i - L) % rebal == 0. No se recomienda: es lo que ocultaba el defecto.
