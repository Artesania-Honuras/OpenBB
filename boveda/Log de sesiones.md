# Log de sesiones

Bitácora cronológica. Formato en `Plantillas.md`.

---

## S-01 — 2026-10-18 / 2026-10-19 — Instalación y verificación

**Hecho**

- Clon completo del monorepo en `repos\OpenBB` (develop, `78020ee4b86`).
- Venv `venvs\openbb` con Python 3.13.12 y 37 paquetes editables.
- Build explícito: 584 comandos, 18 providers, 869 rutas.
- API en `127.0.0.1:6900` con auth desactivada.
- Verificación de 8 familias: 28 OK, 0 errores, 2 huecos declarados.
- Utilidades: lanzadores, `scripts\obb_env.py`, notebook validado, 27 series cacheadas.

**Se rompió / se resolvió**

- `eia` abortaba la instalación → excluido (C-02).
- BCE fallaba por certificados → certifi (C-03).
- `import openbb` se colgaba → autobuild off (C-04).
- `--help` con `UnicodeEncodeError` → UTF-8 (C-05).

**Decidido**

- Todo local, sin Docker ni WSL.

**Abierto**

- FRED y EIA opcionales.
- Sin tests propios.

---

## S-02 — 2026-10-19 — Puente a Freqtrade y validación

**Hecho**

- Detectadas **7 instancias de Freqtrade corriendo** (15 procesos, puertos 8080/8081). No se escribió nada en su repositorio.
- Puente por archivo: `contexto_diario.parquet` (36.636 × 13) + `fusionar()` con `merge_asof`.
- Dos estrategias de ejemplo y config de backtest contenida.
- Backtest 2021→2026: con filtro −49,44 %, sin filtro −28,60 %.
- Marco walk-forward + Monte Carlo; 7 activos; 129 operaciones OOS en BTC.

**Se rompió / se resolvió**

- El merge rompía por zona horaria (tz-naive vs UTC) → corregido conservando el índice original.
- `datadir` absoluto no se respetaba → se copiaron 7 feather a nuestra carpeta.
- **Bug de datos:** `treasury_rates` devolvía solo 1 año → comparación inválida (E-03 → E-04).

**Decidido**

- **No integrar la estrategia al bot**: 0/7 activos baten la referencia ajustada por exposición.
- El filtro macro no aporta alfa; el cruce EMA tampoco.

**Abierto**

- P1: encontrar un gatillo con ventaja OOS.

---

## S-03 — 2026-10-19 — Memoria persistente y repositorio

**Hecho**

- Inventario completo del proyecto (solo lectura).
- Creada `boveda\` con INDICE, Manual, Registro, Log y Plantillas.
- `CLAUDE.md` con las reglas obligatorias y el puntero al índice.
- `estado.py`: checklist de solo lectura con tabla ✅/❌.
- `.gitignore` y repo `OpenBB` público en GitHub; commit y push.
- **Verificado:** commit `f4fe7b5`, repo `https://github.com/Artesania-Honuras/OpenBB` (público), `estado.py` → **22/22 ✅**.

**Se rompió / se resolvió**

- La raíz no era repositorio Git → `git init`.
- El clon `repos\OpenBB` tiene 2 archivos sucios generados por el build → queda excluido del repo y anotado como pendiente P7.

**Decidido**

- Memoria solo en el proyecto, en texto versionado.
- Datos binarios regenerables fuera del repo; solo se versiona `contexto_diario.parquet` como evidencia.

**Abierto**

- P1 (gatillo con ventaja), P2 (refresco automático), P6 (tests).

---

## S-04 — 2026-10-19 — Manual de uso publicado

**Hecho**

- README.md con el manual completo en 12 secciones e índice enlazado.
- Referencia al manual añadida en oveda\INDICE.md.
- Registro del cambio como C-10.

**Se rompió / se resolvió**

- Nada nuevo. Se reutilizó el estado verificado de la sesión (22/22).

**Decidido**

- El manual vive en la raíz del repo para que GitHub lo muestre al abrirlo.

**Abierto**

- Sin cambios: P1 sigue siendo el bloqueo principal.

---

## S-05 — 2026-10-19 — Panel visual local

**Hecho**

- Detectado que OpenBB Workspace ya no existe: `workspace.brightquery.com` muestra "BQ Workspace — coming soon", sin login.
- Instalado Streamlit 1.66.0 en el venv.
- Creado `app.py` (7 pestañas) y `run-openbb-app.ps1`.
- Verificado con `AppTest`: 0 excepciones, 7 pestañas, 16 métricas.
- Panel corriendo en `http://127.0.0.1:8501`; añadido al checklist (`estado.py`).

**Se rompió / se resolvió**

- Avisos de `use_container_width` obsoleto → migrado a `width="stretch"`.
- Streamlit degradó `pillow` 13.0.0 → 12.3.0; sin impacto en OpenBB (no se usa para datos).

**Decidido**

- La interfaz visual es local (Streamlit), no cloud. El backend sigue siendo la API del 6900.

**Abierto**

- P1 sigue siendo el bloqueo principal.
- El panel es de solo lectura; no ejecuta órdenes ni escribe datos.

---

## S-06 — 2026-10-19 — Panel explicado y bug del puente corregido

**Hecho**

- Panel reescrito (`C-12`): todo en español, pestaña **Guía** con qué mide cada indicador y su uso, semáforo de entorno (favorable / neutral / defensivo), tablas traducidas y limpias, ayuda en cada métrica.
- Bug de la pendiente 10a-2a corregido: mostraba **+0 pb** donde son **+33 pb**.
- Bug del puente corregido (`C-13`): la asignación de series desplazadas realineaba por fecha y perdía el último dato (VIX del lunes = jueves). Ahora se reindexa a calendario diario.
- Contexto reexportado con `--forzar`: `vix 19.99`, `spx 7659,44`, 0 NaN en 2026.

**Se rompió / se resolvió**

- Descubierto que el contexto estaba hasta 3 días viejo en las series de riesgo, no por el retraso intencional sino por el bug de alineación.

**Decidido**

- El panel es una herramienta de **contexto**, no de señales. Se dice explícitamente en la Guía y en el propio panel.
- La conclusión 0/7 no se da por revalidada con el contexto corregido: queda como pendiente medirla otra vez antes de tocar nada en vivo.

**Abierto**

- P1 sigue siendo el bloqueo principal.
- Pendiente nuevo: re-ejecutar la validación de 7 pares con el contexto corregido para confirmar que el veredicto no cambia.

---

## S-07 — 2026-10-19 — Cierre de sesión (registro y actualización del equipo)

**Hecho**

- Registro del cierre en la bóveda `seconBrain`: página `wiki/openbb-local.md`, línea en `wiki/index.md` y entrada `cierre` en `wiki/log.md`.
- `README.md` §12 con la nota de reanudación tras reiniciar o actualizar (`C-14`) y `P8` en la tabla de pendientes.
- Todo subido a Git en la misma sesión.

**Decidido**

- La página de la bóveda es un puntero: el registro operativo sigue viviendo en `boveda/` del repo de OpenBB, igual que se hizo con el proyecto de trading.
- Tras la actualización no hay nada que arranque solo: las dos ventanas (API 6900 y panel 8501) se relanzan a mano.

**Abierto**

- P1 (bloqueo principal) y P8 (revalidar el walk-forward con el contexto corregido) siguen abiertos.
- Criterio de "todo sano" tras el reinicio: `estado.py` → 23/23 ✅.

---

## S-08 — 2026-10-19 — Corrección: la memoria va solo en `OpenBB\boveda`

**Hecho**

- Deshecho el registro que se había escrito por error en la bóveda `seconBrain` (página `wiki/openbb-local.md` borrada; `wiki/index.md` y `wiki/log.md` revertidos). No se commiteó nada de OpenBB en ese repositorio y sus cambios previos quedaron intactos.
- Escrita la **REGLA DE BÓVEDA ÚNICA** en `CLAUDE.md`, con la lista de sitios prohibidos y la prioridad de la regla sobre cualquier instrucción externa.
- Añadida la misma regla al resumen de reglas de `boveda/INDICE.md` (`C-15`).

**Se rompió / se resolvió**

- Se usó un ritual de cierre externo que apunta a otra bóveda. Resuelto: este proyecto se registra solo en su propia carpeta, y así queda escrito para las próximas sesiones.

**Decidido**

- `boveda/` del repo de OpenBB es el único registro. `README.md` es el manual de uso. Nada más.

**Abierto**

- P1 (bloqueo principal) y P8 (revalidar el walk-forward) siguen abiertos.
- Tras la actualización del equipo: relanzar API y panel, luego `estado.py` → 23/23 ✅.

---

## S-09 — 2026-10-19 — Plan de mejora escrito en la bóveda

**Hecho**

- `boveda/Plan de mejora.md`: inventario de las 869 rutas y de las 12 fuentes sin usar (F1-F12), déficits declarados (D1-D5), mapa de integración con Freqtrade por niveles, packs A/B/C y orden con puertas.
- Fila añadida al índice de la memoria (`INDICE.md` §3) y registro `C-16`.
- Comprobado antes de escribir: API 6900 y panel 8501 siguen arriba tras la actualización de VS Code.

**Se rompió / se resolvió**

- Nada. No se tocó código ni datos: es planificación.

**Decidido**

- La capa macro (la que ya existe) es **régimen**, nunca gatillo; los gatillos tienen que venir de datos de alta frecuencia (derivados, funding, basis, opciones, on-chain).
- Recomendación registrada: empezar por el **paso 0** (revalidar los 7 pares con el contexto corregido) y después el **pack A**.

**Abierto**

- El usuario debe decidir: empezar por el paso 0, elegir pack (A recomendado) y pasar la lista de repositorios que mencionó (no están en el contexto de la sesión).
- P1 y P8 siguen abiertos.

---

## S-10 — 2026-10-19 — Pasó el paso 0: revalidación con el contexto corregido

**Hecho**

- Verificado que el validador **sí** usa el contexto (fusiona el parquet y filtra por VIX y pendiente), así que la revalidación tenía sentido.
- Ejecutado `validar_estrategia.py --todos --stake 0.1` (misma herramienta, misma ventana, mismo grid de 54 combinaciones). Salida en `data/reporte_validacion.txt`.
- Registrado como `E-07` y documentado en `README.md`, `INDICE.md` y `Plan de mejora.md` (`C-17`).

**Se rompió / se resolvió**

- Nada se rompió. Antes de lanzar apareció una duda razonable: si el validador no usara el contexto, la revalidación no mediría el arreglo `C-13`. Se comprobó en el código que sí lo usa (`cargar_par` + `simular`).

**Decidido**

- El defecto `C-13` **no** era la causa de la falta de edge: 0/7 → 1/7 y la única victoria es de 0,3 puntos frente a una referencia de 5,5 %.
- `D-08` sigue vigente: no se integra la estrategia al bot. `P1` sigue siendo el bloqueo principal.
- El paso 0 del plan está cerrado; el siguiente paso natural es el **pack A** (funding, volatilidad cripto, calendario, Fear&Greed).

**Abierto**

- P1 (bloqueo principal), P2 (refresco automático) y P9 (panel) siguen abiertos.
- El usuario debe elegir pack (A recomendado) y pasar la lista de repositorios que mencionó.

---

## S-11 — 2026-10-19 — Pack A, paso 1: funding de perpetuos

**Hecho**

- Inspeccionados los endpoints de derivados de OpenBB: **solo dan ventanas cortas** (funding 31 días, volatilidad realizada 17, índice 1). Sirven para el estado vivo, no para validar.
- Descartado añadir `ccxt` (no está en el venv): el funding se trae del endpoint público de Binance con `urllib`, sin dependencias nuevas. Nuevo `scripts/fuentes_externas.py` con caché (2.118 días desde 2021).
- Columna `funding_btc_anual` añadida al contexto (13 → 14 columnas), con retraso de 1 día. Actualizados `estado.py` y `app.py`.
- Validador ampliado con `funding_max` / `funding_min` (`C-19`) y experimento medido en tres variantes (`E-08`).
- Salidas crudas: `data/reporte_validacion.txt`, `data/reporte_funding_ab.txt`.

**Se rompió / se resolvió**

- Nada roto. El hallazgo que obligó a cambiar de rumbo: la capa rápida de OpenBB no tiene historial suficiente para backtest.

**Decidido**

- El funding **no** se usa como filtro de entrada: evitar el funding alto resta 8 puntos de mediana (0/7) y exigir funding positivo sube 2,1 puntos pero sigue en 1/7.
- La columna se conserva como información de estado en vivo.
- La conclusión que importa del experimento: el cuello de botella no es el filtro macro ni el de derivados, sino que la **exposición del 30-45 % no captura el retorno de comprar y mantener**. Con esa exposición, batir la referencia es casi imposible por diseño.

**Abierto**

- P1 sigue siendo el bloqueo principal.
- Siguiente paso natural del pack A: **F4 volatilidad cripto**, y si también carece de historial, replantear el pack hacia features de la propia vela (velocidad, rango, volumen) en vez de fuentes externas.

---

## S-12 — 2026-10-19 — Gestión de salida (y el panel, que no se veía)

**Hecho**

- El usuario avisa de que no ve nada implementado en la web. Diagnóstico: el proceso de Streamlit llevaba 74 minutos arrancado y **no recarga el script** al modificarlo. Se reinició (`run-openbb-app.ps1`), health `ok`, PID nuevo.
- Para que el dato no quede escondido: sección "Capa rápida" en la **primera** pestaña (métrica, percentiles, lectura y gráfico), fila nueva en la Guía y aviso actualizado.
- Motor de salidas implementado en el validador (`C-20`): stop móvil, break-even, salida por media rápida, modo `--salidas` con entrada fija.
- Verificación de regresión: el modo por defecto reproduce `E-08` exacto → el refactor no cambió nada.
- Experimento medido en 6 variantes × 7 activos × 11 ventanas (`E-09`), salida cruda en `data/reporte_salidas_ab.txt`.

**Resultado**

- **Mover la salida no ayuda.** Stop móvil al 10 %: −4,6 pts. Break-even: −4,3. Salir al perder la media rápida: −13,5. Stop móvil al 20 %: idéntico a la línea base (nunca se activa). Búsqueda completa: −6,7.
- La comparación de fondo se aclara: la referencia de misma exposición equivale a **elegir al azar** ese porcentaje de días, y el cruce EMA pierde en 6 de 7 pares.

**Decidido**

- La base (cruce EMA 20/50) queda **descartada con evidencia acumulada**: ni el filtro macro, ni el de derivados, ni la salida. El trabajo futuro no puede seguir alrededor de esa señal; hay que cambiar la señal de entrada.
- El panel se considera parte del entregable: si un cambio no se ve, el cambio no cuenta.

**Abierto**

- P1 sigue bloqueado, ahora con un motivo mejor fundado: la base no tiene ventaja, no es cuestión de ajustes.
- P9 (lista de repositorios del usuario) sigue sin respuesta.

---

## S-13 — 2026-10-19 — Ecosistema del usuario y momentum transversal

**Hecho**

- El usuario entregó la lista de repositorios (9 en total: TradingAgents, Freqtrade, VectorBT, Backtrader, Hummingbot, CCXT, FinRL, NautilusTrader, Polymarket). Registrados en `boveda\Ecosistema de herramientas.md` con veredicto por repo y **para qué sirve aquí**, no en general. `P10` cerrado.
- Recomendación concreta del ecosistema: **VectorBT** es lo que mueve la aguja (barrer miles de hipótesis con métricas de riesgo); **CCXT** es la vía si el momentum se lleva a 20-30 pares. Se descartan Backtrader, NautilusTrader, Hummingbot y FinRL, cada uno con su motivo escrito.
- Implementado `scripts/validar_momentum.py` con prueba de permutación (`C-22`): momentum transversal contra elegir K pares al azar.

**Resultado (primera señal positiva del proyecto)**

- Walk-forward: **+1.112 %**, drawdown **−81,7 %**, percentil **99** de la nube al azar, P(azar ≥ estrategia) = 1,0 %.
- Robustez: **16/18** combinaciones baten la mediana del azar, mediana global percentil 93 → no es una casualidad de la rejilla.
- Contra no hacer nada: mejor configuración simple (L=30, K=3, semanal) **+1.442,7 % con DD −77,4 %** frente a la cesta a peso igual **+1.121,8 % con DD −81,9 %**. Gana en las dos cosas, pero por poco.
- **Todas** las combinaciones tienen drawdown entre −75 % y −93 %.

**Decidido**

- **Sí** hay ventaja medible por primera vez (`D-13`), y **no** se integra nada: el riesgo es inaceptable y el criterio del proyecto pide drawdown < 20 %.
- La causa es estructural: la cartera está siempre 100 % invertida en 2-3 altcoins porque no se ha puesto ningún control de riesgo.
- `D-14`: el siguiente trabajo es control de riesgo, y es donde la capa lenta de OpenBB pasa a tener papel real (decidir cuánto capital está expuesto, no cuándo entrar).

**Abierto**

- `P11`: filtro de régimen y/o volatilidad objetivo sobre el momentum. Es el único camino que hoy tiene evidencia a favor.
- Nota metodológica anotada para la próxima iteración: seleccionar en entrenamiento por retorno **ajustado por riesgo**, no por retorno bruto.

---

## S-14 — 2026-10-19 — Control de riesgo sobre el momentum

**Hecho**

- Ampliado `scripts/validar_momentum.py` (`C-23`): filtro de régimen sobre la cesta, volatilidad objetivo, Calmar como criterio de selección y bandera `--riesgo` con 6 variantes.
- Verificación de regresión antes de tocar el defecto: la línea base reprodujo `E-10` número a número (+1.112 %, DD −81,8 %, percentil 99).
- Experimento medido en `data/reporte_momentum_riesgo.txt`, con la **nube al azar llevando las mismas señales de riesgo** (si no, la comparación se contamina).

**Resultado**

- **Lo que falló:** el filtro de régimen recorta el drawdown de −80 % a −70 % pero se lleva dos tercios del retorno (+1.538 % → +160 %), y el Calmar cae de 19,2 a 2,3. La volatilidad objetivo baja el DD a −47 % pagando otro tanto. Se paga más retorno del drawdown que se ahorra.
- **Lo que funcionó:** cambiar la selección en entrenamiento de retorno bruto a **Calmar**. Mejora retorno (1.538 vs 1.112), drawdown (−80,1 vs −81,8) y Calmar (19,22 vs 13,69 de la cesta) a la vez, y P(azar ≥ B) = 0,0 %. Era un error mío de diseño: el retorno bruto premia el máximo riesgo.
- **Ninguna variante** alcanza el DD < 20 % del criterio del proyecto.

**Decidido**

- Calmar pasa a ser el criterio por defecto; `--objetivo retorno` reproduce `E-10` para que nada quede sin poder rehacerse.
- Filtro de régimen agregado y volatilidad objetivo: **descartados**. El problema no se resuelve con filtros sobre la cesta.
- `D-16`: el drawdown es **estructural** con 7 altcoins (en un mercado bajista caen las siete). El siguiente trabajo es filtro **absoluto por activo** y ampliar el universo a 20-30 pares, que es donde entran CCXT y VectorBT del ecosistema.

**Abierto**

- `P12`: momentum absoluto por activo (mantener solo los K mejores que además estén por encima de su propia tendencia).
- `P13`: ampliar el universo de 7 a 20-30 pares — es la única vía que ataca el drawdown por construcción, no por filtro.

---

## S-15 — 2026-10-19 — La app se quedaba muda, y el momentum absoluto

**Hecho**

- El usuario avisa por segunda vez de que «la app sigue igual». Comprobado: el proceso servía el código nuevo (`health: ok`, PID posterior al cambio). El problema real era otro y era de fondo: **el panel solo mostraba el contexto macro**; los cinco experimentos de validación no aparecían en ninguna parte.
- Añadida la pestaña **«Estrategia»** (`C-25`): puerta de graduación con sus 4 criterios, aviso de que no se instala nada, tabla de `E-07`…`E-11` con veredictos y los reportes crudos leídos de `data/reporte_*.txt`. Panel reiniciado (PID nuevo, health `ok`).
- Implementado el momentum **absoluto por activo** (`C-24`) con variantes G/H/I y la nube al azar llevando el mismo filtro.

**Resultado**

- **Descartado.** El filtro de tendencia propia baja el drawdown (−80 % → −59/−76 %) y hunde el Calmar (19,2 → 2,0/10,6/4,0). Y lo más serio: el percentil frente al azar cae a 73-89, o sea que **elegir pares al azar con el mismo filtro iguala o supera a la estrategia** el 11-26 % de las veces. Sin habilidad demostrable.
- El motivo se ve en la nube: el filtro deja 1-3 candidatos, la mediana del azar sube a +411 % y el ranking deja de importar porque el azar compra casi lo mismo.
- Regresión verificada: A y B reproducen `E-11` exacto en retorno y drawdown.

**Decidido**

- `D-17`: no hay mecanismo de control de riesgo que conserve la ventaja con 7 pares. El límite es el **universo**, no el mecanismo.
- El siguiente trabajo deja de ser "otro filtro" y pasa a ser **datos**: ampliar a 20-30 pares (`P13`).

**Abierto**

- `P13`: descargar 20-30 pares y repetir `E-10`/`E-11` con esa cesta. El validador ya acepta cualquier número de pares; lo que falta son las velas.

---

## S-16 — 2026-10-19 — Universo ampliado: mi hipótesis era falsa

**Hecho**

- Antes de bajar una sola vela, revisé los datos que ya tenía y encontré un defecto: **4 de 7 pares terminaban 29 días antes que los otros** y el `ffill` los dejaba con el precio congelado en `E-10`…`E-12`. Declarado y corregido (`C-27`), no borrado.
- Escrito `scripts/descargar_velas.py` (`C-26`): descarga desde el endpoint público de Binance **con verificación** — primera/última fecha, huecos, duplicados, retraso. Descartó a **EOS** por retirado (512 días de retraso). Universo final: **24 pares**, todos con la misma última vela.
- `--pares` en el validador, para no perder la reproducibilidad al ampliar el universo.
- Repetido `E-11` con datos limpios: **idéntico** (+1.538,1 % / −80,0 % / Calmar 19,22).
- Medido `E-13`: 24 pares, lógica base y las 9 variantes de riesgo.

**Resultado**

- **Mi hipótesis era falsa.** Dije que el límite era el universo. Con 24 pares: retorno **+3.118 %** (contra +1.538 %), Calmar **35,8** (contra 19,2)… y drawdown **−87,1 %** (contra −80,0 %), supervivencia **6/11** (contra 7/11). **Ampliar la cesta triplica el retorno y empeora justo lo que quería arreglar.**
- Ninguna de las 9 variantes baja de **−35,7 %** de drawdown, y la que llega ahí recorta el retorno un 81 % y pierde 6 de 11 ventanas.
- La volatilidad objetivo 60 % gana en las cuatro medidas con 24 pares y **había perdido en las cuatro con 7**. Un mecanismo que cambia de signo con el universo es suerte de camino: no se adopta, y queda escrito para que nadie lo adopte por verlo ganar.
- El azar dejó de ser rival serio: mediana **−17,9 %** con 24 pares contra **+100,7 %** con 7. El percentil 100 ya no demuestra lo mismo. La referencia que vale es la cesta, y la cesta también cae −81,9 %.

**Decidido**

- `D-20`: verificar siempre la fecha final de cada serie antes de medir.
- `D-21`: el drawdown es **de la clase de activo**. Se acabaron los filtros: la pregunta pasa a ser de **tamaño de la exposición**.
- `D-22`: el percentil frente al azar no es comparable entre universos.
- `D-23`: un mecanismo que cambia de signo según el universo no es un mecanismo.

**Abierto**

- `P15`: **cuánto capital** darle a un sleeve cuya caída natural es del ~87 %. Es una decisión del dueño del capital; el backtest solo informa.
- `P14`: medir la versión mercado-neutral (largo-corto), que es el mecanismo estándar contra este drawdown. **No sirve para sus bots** (son spot), así que es para saber, no para operar.
- `P3`: instalar en Freqtrade deja de estar bloqueado por un gatillo y pasa a estarlo por el tamaño (`P15`).

---

## S-17 — 2026-10-19 — De investigación a algo instalable: +820 % y 10 %

**Hecho**

- Confirmado con datos que el panel sí servía el código nuevo (proceso 16:16:10 posterior al cambio de 16:13:19). El usuario seguía viendo «igual» por la pestaña vieja: **tercera vez**. Añadida una **huella de versión** en la barra lateral (`C-30`) para que deje de ser un problema de fe.
- `--fijo` en el validador (`C-28`): medir un solo juego de parámetros, de principio a fin. Cinco configuraciones, con la propuesta elegida **a priori** en `E-10`.
- `scripts/dimensionar.py` (`C-29`): bootstrap por bloques para traducir el drawdown del sleeve a drawdown de cartera.

**Resultado**

- **`E-14`: la regla que se instala da +820 %, no +3.118 %.** L=30/K=3/semanal: CAGR +47,2 %, DD −82,5 %, Calmar 9,95, 7/11 ventanas, P(azar ≥) 0,5 %. La diferencia con el titular es la re-optimización semestral, que habría que automatizar.
- Sensibilidad brutal: la misma idea con `K=5` y `L=60` da **+68 % y Calmar 0,78**. Funciona en una región, no en general.
- **`E-15`: sleeve del 10 %.** Caída típica −13,0 %, 5 % peor −22,0 %, un año perdedor de cada cinco, ningún camino pierde más del 25 % en un año. Al 15 % la probabilidad de superar el −20 % de DD salta al 42 %.
- **Error propio corregido en el camino:** el primer dimensionado, sin rebalanceo, daba −31 % con el 5 % invertido. Era el modelo el que estaba mal, no alto el riesgo. Cambiado a fracción constante y anotado en `E-15`.

**Decidido**

- `D-24`: el número desplegable es el de la configuración fija.
- `D-25`: **10 %** de sleeve, declarando que incumple `DD p95 < 20 %` por 2 puntos. Si se aplica al pie de la letra, 5 %.
- `D-26`: la puerta se cumple a nivel de **cartera**, que es el riesgo que el dueño del capital ve.

**Abierto**

- `P3`: escribir la estrategia de rotación en Freqtrade (long-only, 24 pares, K=3, semanal) con `stake` equivalente al 10 %. **No tocar los bots que están corriendo** hasta que el puente esté probado.
- `P16`: automatizar la re-optimización semestral, solo si se quiere aspirar al número grande. La regla fija ya es suficiente para empezar.

---

## S-18 — 2026-10-19 — Cierre, auditoría de la bóveda y seguimiento del plan

**Hecho**

- Auditoría de los siete archivos de la bóveda contra lo que realmente hay. Encontrado y corregido:
  - `INDICE.md`: seguía diciendo **S-03** como última sesión, **13 columnas** en el contexto, y «hoy ninguna estrategia cumple la puerta», que ya era falso.
  - `Plan de mejora.md`: decía **«propuesta, nada aplicado»**, **8 pestañas**, **7 pares** de validación y marcaba el paso 1f como siguiente cuando estaba hecho. El paso 1e citaba `D-18`, que está refutada.
  - `README.md`: dos menciones a **13 columnas**, `P3` todavía «bloqueado por P15» y el `estado.py` esperado en **23/23**.
- `--pares` también en `validar_estrategia.py` (`C-31`): con 24 pares en el directorio, `--todos` había dejado de reproducir `E-07`/`E-08`/`E-09`.
- Reescrita la compuerta de aceptación con el **estado real criterio por criterio** para la regla desplegable: criterio 2 ✅, criterio 4 ✅, criterio 3 **❌ por 2 puntos** y criterio 1 no aplica (es cartera, no por activo).
- El plan de mejora pasa de «propuesta» a **«en ejecución»**, con los pasos 0→1g cerrados y `1h` como siguiente. La sección 12 pasa de «decisiones que faltan» a **seguimiento con la respuesta a cada pregunta**.

**Decidido**

- Ninguna decisión nueva de estrategia. Se cierra la documentación y se deja el plan sincronizado con la evidencia.
- El aviso de la bóveda queda explícito: **la puerta se incumple por 2 puntos y así se dice**; no se ajusta el criterio para que cuadre.

**Abierto**

- `P3`: escribir la rotación en Freqtrade (regla fija, 24 pares, K=3, semanal, 10 %).

---

## S-19 — 2026-10-19 — Reinicio del equipo: recuperación y dos falsos negativos del chequeo

**Hecho**

- El equipo se había reiniciado (uptime 6 min al preguntar). `estado.py` lo detectó bien: API y panel caídos. **Pero se equivocó en dos cosas** (`C-32`): decía que no había procesos de Freqtrade (había **10**) y que los puertos 8080/8081 estaban cerrados (estaban los tres, más el 8082 del bot MT5).
- Causa 1: el chequeo buscaba `freqtrade.exe` por **nombre de imagen**, y los bots corren como `python.exe`. Causa 2: `tasklist` responde en la codificación OEM y con `PYTHONUTF8=1` la decodificación UTF-8 reventaba en el hilo lector, tapando el error real con un `AttributeError`.
- Arreglados los dos, más el puerto 8082.
- Relanzados API y panel. La API tardó **~3,5 minutos** en frío (147 s de CPU, 812 MB) frente a los ~60 s que tenía anotados `D-05`: no estaba colgada, estaba importando. Queda anotado para no matarla pensando que se colgó.

**Resultado**

- `estado.py` → **24/24 ✅**, con API (6900), panel (8501) y **3 bots** (8080, 8081, 8082) vivos.

**Decidido**

- Un chequeo de estado que da falso negativo es peor que no tenerlo: se corrige el chequeo, nunca el dato.
- El arranque en frío de la API se documenta como «minutos», no como «un minuto».

**Abierto**

- `P3`: escribir la rotación en Freqtrade.

---

## S-20 — 2026-10-19 — P3: la estrategia se escribio, se verifico y se refuto

**Hecho**

- Escritos strategies/rotacion_nucleo.py, strategies/rotacion_momentum.py y scripts/verificar_rotacion.py.
- Verificacion offline: **296/296** selecciones identicas al validador, shift de **30,00 dias exactos**.
- Medida la fase del rebalanceo: **42 fases**, rango **+95,8 % a +3.776 %**, mediana **+816,5 %**.
- Medida la cesta (+370,3 %, Calmar 4,52) y el azar con el mismo calendario (mediana +27,2 %).

**Resultado**

- La implementacion natural (lunes 00:00) da **+95,8 %, DD −87,9 %, Calmar 1,09, 5/11 ventanas**, percentil 76 del azar, **P(azar >=) 24,0 %**.
- **Pierde contra no hacer nada** y no es significativa. E-16 la refuta.

**Decidido**

- La rotacion **no se instala**. No se copia nada a Freqtrade.
- La **fase** es un parametro de primer orden (D-27): se reporta como rango, nunca como numero unico.
- La implementacion defendible es la elegida **a priori** (D-28), aunque sea la peor de las 42. Elegir la mejor es *data snooping*.
- La prueba de fase pasa a ser obligatoria para cualquier regla nueva (P17).

**Lo que se gano**

- Un error de despliegue evitado **con coste cero**, y una herramienta permanente que ya no hay que reescribir.
- El +820 % dejo de ser una promesa y paso a ser un dato con su rango al lado.

**Abierto**

- P17: elevar la prueba de fase a criterio de la compuerta.
- El gatillo con ventaja real sigue sin existir (P1 reabierto).
