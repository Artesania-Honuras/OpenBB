# INDICE — Memoria del proyecto OpenBB local

> Última actualización: 2026-10-19 · Sesión S-03
> Este archivo es lo primero que debe leer cualquier sesión nueva.

---

## 1. Qué es este proyecto

Instalación **local** de OpenBB Platform desde el código fuente (clon del monorepo),
con una API en `127.0.0.1:6900` y un **puente de contexto macro hacia Freqtrade**
(que vive fuera, en `C:\Users\DELL\.ipython\freqtrade`).

Objetivo: que OpenBB aporte el contexto (macro, riesgo, posicionamiento, factores)
y Freqtrade decida la entrada técnica y ejecute. Nada sale a la nube salvo las
peticiones de datos públicos a los proveedores.

---

## 2. Reglas vigentes

Están en `CLAUDE.md`, al inicio. Resumen:

| Regla | Qué exige |
|---|---|
| Registro | Todo cambio `C-NN`, todo experimento `E-NN`, toda sesión en el Log, commit + push en la misma sesión |
| Cambios | Medición reproducible + validación fuera de muestra + registro + despliegue verificado |
| Estado | "¿Está todo al 100%?" → ejecutar `estado.py` y pegar la tabla ✅/❌ completa |
| Trabajo | Ubicar la entrada antes de tocar; misma herramienta y condiciones; secretos fuera; lo no verificable es pendiente |
| Bóveda única | El registro vive **solo** en `OpenBB\boveda\` y `README.md`. Prohibido escribir en `seconBrain` ni en ninguna otra bóveda o repo ajeno |

---

## 3. Qué contiene esta memoria

| Archivo | Para qué |
|---|---|
| `INDICE.md` | Este mapa: estado, decisiones, criterios, pendientes, cómo retomar |
| `Manual de cambios.md` | Una entrada `C-NN` por cambio: qué, por qué, evidencia, cómo revertir |
| `Registro de resultados.md` | Una fila `E-NN` por experimento: hipótesis, método, números, veredicto |
| `Log de sesiones.md` | Bitácora: qué se hizo, qué se rompió, qué se decidió, qué quedó abierto |
| `Plantillas.md` | Formatos vacíos para que el registro sea consistente |
| `Plan de mejora.md` | Hoja de ruta de datos y validación: fuentes disponibles (F1-F12), déficits (D1-D5), packs A/B/C y puertas |
| `Ecosistema de herramientas.md` | Los repositorios del usuario: qué es cada uno, qué papel tiene aquí y veredicto (adoptar / más adelante / no) |

> Manual de uso completo (instalación, arranque, comandos, problemas): `README.md` en la raíz.

---

## 4. Estado actual — decisiones vivas con evidencia

| ID | Decisión | Evidencia | Fecha |
|---|---|---|---|
| D-01 | Python 3.13.12 + venv editable en `venvs\openbb` | 37 paquetes editables, `uv pip check` 243/0 conflictos | 2026-10-19 |
| D-02 | API solo loopback `127.0.0.1:6900`, auth desactivada | HTTP 200, 869 rutas OpenAPI | 2026-10-19 |
| D-03 | Provider `eia` excluido | Su build hook exige `EIA_API_KEY` en vivo y aborta la instalación | 2026-10-19 |
| D-04 | SSL forzado a certifi | `EURUSD` vía BCE devuelve 7.117 filas | 2026-10-19 |
| D-05 | `OPENBB_AUTO_BUILD=false` | Arranque ~60 s sin cuelgues | 2026-10-19 |
| D-06 | Contexto diario con retrasos de publicación | 36.636 filas × 14 columnas, 1926→2026, 0 NaN en 2026 | 2026-10-19 |
| D-07 | Puente por archivo (parquet), no por HTTP | Merge con 14.886 velas 4h sin look-ahead | 2026-10-19 |
| D-08 | **No integrar** la estrategia al bot | Walk-forward revalidado con el contexto corregido (`E-07`): 7/7 OOS positivos, **1/7** baten la referencia ajustada por exposición (y por 0,3 puntos) | 2026-10-19 |
| D-09 | El funding de perpetuos **no** se usa como filtro | `E-08`: evitar el funding alto resta 8 puntos de mediana; exigir funding positivo sube 2,1 pero sigue en 1/7. Se conserva como dato de estado | 2026-10-19 |
| D-10 | La capa rápida se trae de fuera de OpenBB | Los endpoints `deribit/*` solo dan ventanas cortas (funding 31 días); el historial se toma del endpoint público de Binance, sin claves y sin dependencias | 2026-10-19 |
| D-11 | La gestión de salida **no** se toca | `E-09`: stop móvil, break-even y salida por media rápida empeoran o empatan; la búsqueda completa rinde peor que la línea base | 2026-10-19 |
| D-12 | El cruce EMA 20/50 queda **descartado como base** | `E-07`+`E-08`+`E-09`: no bate al azar con la misma exposición en 6 de 7 pares. Trabajo futuro = cambiar la señal de entrada | 2026-10-19 |
| D-13 | **Momentum transversal: primera ventaja demostrada**, pero **no integrable** todavía | `E-10`: cae en el percentil 99 de la nube al azar (p=1 %) y 16/18 combinaciones baten su mediana. Pero el drawdown es del **−77 % a −93 %** en todas ellas: sin control de riesgo no se puede operar | 2026-10-19 |
| D-14 | El control de riesgo es el siguiente trabajo, y es donde encaja la capa lenta | La capa macro no sirve para elegir entradas (`E-07`-`E-09`) pero sí para decidir **cuánto capital está expuesto** al momentum (`D-13`) | 2026-10-19 |
| D-15 | **Calmar** como criterio de selección en entrenamiento | `E-11`: elegir por retorno bruto premiaba el máximo riesgo. Con Calmar, retorno, drawdown y Calmar mejoran a la vez (+1.538 %, −80,1 %, 19,22 frente a 13,69 de la cesta) | 2026-10-19 |
| D-16 | El drawdown del momentum es **estructural**, no de ajuste | `E-11`: filtro de régimen y volatilidad objetivo cuestan más retorno del que ahorran. Con 7 altcoins caen las siete a la vez; el DD < 20 % exige filtro por activo y más universo | 2026-10-19 |
| D-17 | El momentum absoluto por activo **también se descarta** | `E-12`: baja el DD a −59/−76 % pero hunde el Calmar (19,2 → 2,0/10,6/4,0) y el percentil frente al azar cae a 73-89. Con 1-3 candidatos el ranking deja de importar | 2026-10-19 |
| D-18 | ~~El límite es el **universo**, no el mecanismo~~ **REFUTADA** | `E-13`: ampliar de 7 a 24 pares sube retorno y Calmar pero **empeora el DD** (−80,0 % → −87,1 %) y la supervivencia (7/11 → 6/11). El drawdown no venía de la falta de dispersión | 2026-10-19 |
| D-19 | El panel debe mostrar la validación, no solo el contexto | `C-25`: una app que no enseña lo que se ha medido deja al usuario sin ver el trabajo. Los números se leen de los reportes, no se copian | 2026-10-19 |
| D-20 | **Verificar siempre la fecha final de cada serie antes de medir** | `E-13`: 4 de 7 pares terminaban 29 días antes que los otros y `ffill` los dejaba con el precio congelado. `descargar_velas.py` verifica y descarta al rezagado (EOS) | 2026-10-19 |
| D-21 | El drawdown del momentum en cripto es **de la clase de activo** | `E-13`: 3 mecanismos + universo ×3 y el DD sigue en 80-90 %. Correlación entre altcoins en las caídas, no tamaño de cesta. La pregunta pasa a ser de **tamaño de la exposición**, no de filtro | 2026-10-19 |
| D-22 | El percentil frente al azar **no es comparable entre universos** | `E-13`: mediana del azar −17,9 % con 24 pares vs +100,7 % con 7. Con más pares el azar empeora porque incluye más basura. La referencia válida es la cesta | 2026-10-19 |
| D-23 | Un mecanismo que cambia de signo según el universo **no es un mecanismo** | `E-13`: la volatilidad objetivo 60 % gana en las 4 medidas con 24 pares y pierde en las 4 con 7 (`E-11` E). No se adopta, por buena que sea la tabla | 2026-10-19 |

### Capacidades verificadas

- 584 comandos, 18 providers, 869 rutas HTTP.
- 28 pruebas OK, 0 errores, 2 huecos declarados (order flow de equities nivel 2; on-chain).
- Proveedores sin clave que funcionan: `federal_reserve`, `us_treasury`, `sec`,
  `famafrench`, `cftc`, `cboe`, `oecd`, `imf`, `bls`, `ecb`, `deribit`, `jodi`,
  `usda`, `uscongress`, `finra`, `tmx`, `nasdaq`.

### Límites conocidos

- `obb.crypto.price.historical` devuelve vacío → las velas cripto vienen de ccxt/Freqtrade.
- `equity.profile` falla ("FINRA security lookup was not readable").
- Sin `fred_api_key` faltan `tips_yields` y parte de `economy`.
- Sin `EIA_API_KEY` no hay provider `eia`.
- El contexto se refresca **a mano**; no hay tarea programada.

---

## 5. Herramientas fuente de verdad

| Ámbito | Fuente | Nota |
|---|---|---|
| Código | `scripts\`, `strategies\` | Lo que corre |
| Contexto | `data\context\contexto_diario.parquet` | Evidencia del puente; 13 columnas |
| Medición | `scripts\validar_estrategia.py` | La misma herramienta siempre |
| Capa rápida | `scripts\fuentes_externas.py` | Funding de perpetuos (Binance, sin clave, con caché) |
| Estado | `estado.py` | Solo lectura, tabla ✅/❌ |
| Historia | `boveda\*` | Cambios, resultados, sesiones |
| Upstream | `repos\OpenBB` @ `78020ee4b86` (develop) | Referencia, no se edita |
| Config de backtest | `freqtrade_bridge\backtest.json` | Sin claves |

---

## 6. Criterios de aceptación

### Del proyecto (infraestructura)

1. API local responde 200 y una llamada funcional en < 60 s.
2. Contexto con 13 columnas y sin NaN desde 2021.
3. `estado.py` sin ❌ críticos.
4. Repo limpio y pusheado.
5. Cualquier cambio nuevo tiene `C-NN` y su evidencia.

### De una estrategia (compuerta de integración)

No se integra ninguna estrategia al bot si no cumple **las cuatro**:

1. Ventaja fuera de muestra en **≥ 2/3** de los activos.
2. Bate la **referencia ajustada por exposición** (no solo ser positivo).
3. Monte Carlo con **P(pérdida) < 25%** y **drawdown p95 < 20%**.
4. Supervivencia en ≥ 60% de las ventanas walk-forward.

Hoy **ninguna** la cumple.

---

## 7. Pendientes priorizados

| Prioridad | Pendiente | Estado |
|---|---|---|
| P1 | Encontrar un gatillo con ventaja OOS real | 🔴 abierto, redefinido - la ventaja **existe y está medida** (`E-10`, Calmar 35,8 vs cesta 3,83, percentil 100), pero su caída natural es del ~87 % (`D-21`). Lo que falta no es un gatillo nuevo, es **cuánto capital** |
| P2 | Refresco programado del contexto (hoy manual) | 🟡 abierto |
| P3 | Instalar la estrategia en los bots de Freqtrade | 🔴 bloqueado por `P15` (tamaño del sleeve): la estrategia tiene ventaja, lo que falta es decidir el tamaño que hace tolerable su caída |
| P4 | Clave FRED gratuita (`fred_api_key`) para `tips_yields` | 🟡 opcional |
| P5 | Provider `eia` con `EIA_API_KEY` | 🟡 opcional |
| P6 | Tests propios (hoy solo verificación funcional) | 🟡 abierto |
| P7 | Revisar los 2 archivos sucios del clon upstream | 🟢 menor |
| P8 | ~~Re-ejecutar el walk-forward de 7 pares con el contexto corregido (`C-13`)~~ | ✅ cerrado — `E-07`: 0/7 → 1/7, veredicto sin cambios |
| P9 | Panel visual (`app.py`): mantenimiento y nuevas vistas | 🟢 menor — reiniciar el proceso tras cada cambio (`C-21`) |
| P10 | ~~Lista de repositorios del usuario y su papel~~ | ✅ cerrado — 9 repos registrados en `Ecosistema de herramientas.md`; veredicto por repo |
| P11 | ~~Control de riesgo sobre el momentum (`D-13`): filtro de régimen y vol objetivo~~ | ✅ cerrado — `E-11`: ambos **descartados**, cuestan más retorno del que ahorran. Calmar adoptado como criterio (`D-15`) |
| P12 | ~~Momentum absoluto por activo~~ | ✅ cerrado — `E-12`: **descartado**. Baja el DD pero hunde el Calmar y mata la significación |
| P13 | ~~Ampliar el universo de 7 a 20-30 pares~~ | ✅ cerrado — `E-13`: **24 pares**. Sube el retorno y el Calmar, **no baja el DD** (`D-21`) |
| P14 | **Momentum mercado-neutral** (largo en los K mejores, corto en los K peores) | 🟡 abierto, **no desplegable**: es el mecanismo estándar para bajar este DD, pero exige perpetuos y coste de funding; los bots son spot. Medirlo sería para saber, no para operar |
| P15 | **Tamaño del sleeve** según su caída natural del ~87 % | 🔴 abierto — es la decisión que sí queda: presupuesto de riesgo, no estrategia (`D-21`) |

---

## 8. Cómo retomar en 3 pasos

1. **Estado:** `.\venvs\openbb\Scripts\python.exe estado.py` → leer la tabla.
2. **Contexto:** leer este INDICE (secciones 4 y 7) para saber qué está vivo y qué falta.
3. **Historia:** leer la última entrada de `Log de sesiones.md` y continuar por el pendiente P1.

> Si el paso 1 muestra un ❌ crítico, se atiende antes de cualquier otra cosa.
