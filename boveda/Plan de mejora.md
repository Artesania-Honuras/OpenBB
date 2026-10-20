# Plan de mejora — de "datos que no dicen nada" a "datos que deciden"

- **Fecha:** 2026-10-19 (actualizado en S-26)
- **Estado:** **cerrado en la línea de señales.** Pasos 0 a 1h hechos y corregidos: la regla se refutó (`E-16`/`E-17`) y el macro como filtro tampoco aporta (`E-18`). Lo que queda es operación y contexto, no estrategia.
- **Contexto:** el panel funciona (27/27 ✅, 9 pestañas) y el plan ya no es una propuesta: midió,
  descartó y se quedó con lo único que sobrevivió a las pruebas.
- **Regla que manda:** ningún dato entra en vivo si no bate el **benchmark de misma exposición**
  fuera de muestra. Ver `Registro de resultados.md`.

---

## 0. Punto de partida real

| Ya existe | Detalle |
|---|---|
| API local | `127.0.0.1:6900` · 869 rutas · 18 providers |
| Panel visual | `127.0.0.1:8501` · **9 pestañas** · huella de versión para detectar pestañas viejas |
| Contexto diario | **14 columnas** × 36.637 filas (crece a diario), con retrasos anti look-ahead |
| Puente a Freqtrade | parquet + `merge_asof` (0 NaN verificado) |
| Velas | **24 pares** 4h, todos terminando en la misma vela (verificado; EOS descartado por retirado) |
| Validación por activo | walk-forward + Monte Carlo + costes (`validar_estrategia.py`) |
| Validación de cartera | momentum transversal con prueba de permutación (`validar_momentum.py`) |
| Dimensionado | bootstrap por bloques sleeve → cartera (`dimensionar.py`) |
| **Endpoints usados** | **8 de 869** ← aquí sigue habiendo margen, pero ya no es el cuello de botella |

No se están usando: 43 rutas de `deribit`, 6 de `derivatives`, 8 de `etf`,
19 de `cftc`, 17 de `cboe`, 38 de `economy`, 28 de `tmx`, 27 de `sec`,
59 de `technical`, 23 de `quantitative`.

Déficits ya declarados: **order flow nivel 2** y **on-chain**.

---

## 1. El principio que ordena todo

Freqtrade opera **velas de 4h en cripto**. Eso parte el plan en dos velocidades:

- **Capa lenta (régimen):** macro, inflación, tipos. Ya existe, con retraso de
  1 a 45 días. **Nunca dará un gatillo.** Solo decide cuánto riesgo asumir.
- **Capa rápida (gatillo):** derivados, funding, basis, opciones, on-chain.
  Ahí sí puede haber señal en 4h. **Es lo que falta.**

> **Corrección tras medir (`S-18`):** la capa rápida **no era el gatillo que faltaba**.
> Los dos datos de esa capa que se midieron (funding, `E-08`) no aportaron. El gatillo
> que sí tiene ventaja es **transversal y no necesita datos nuevos**: comparar los 24
> pares entre sí (`E-10`). La capa macro se queda como termómetro, que es lo que
> siempre fue.

Diagnóstico honesto: el problema no es la app, es que solo hay capa lenta
aplicada a una estrategia que necesita capa rápida.

---

## 2. Eje 1 — Aprovechar lo que OpenBB ya trae (coste bajo, sin claves)

| # | Fuente | Ruta | Para qué | Relación con Freqtrade |
|---|---|---|---|---|
| F1 | Funding de perpetuos + APR ✅ **probado en `E-08`** | ~~`deribit/rates/funding_history`~~ → solo 31 días; se trae de Binance (`fuentes_externas.py`) | Coste de mantener un largo; extremos = apalancamiento excesivo | Resultado: **no sirve como filtro de entrada**; sí como termómetro de estado |
| F2 | Curva de futuros y basis | `derivatives/futures/curve` | Contango/backwardation = sesgo real del mercado | Filtro de tendencia |
| F3 | Volumen e interés por instrumento | `deribit/market/trade_volumes` | Apalancamiento creciendo | Confirmación de entrada |
| F4 | Volatilidad cripto (realizada + DVOL) | `deribit/volatility/realized`, `index` | Régimen de volatilidad **de los pares operados**, mejor que el VIX | Tamaño de posición y distancia de stop |
| F5 | Opciones: smile, superficie, plazos | `deribit/options/*`, `cboe/options/*` | Miedo implícito del mercado de opciones | Filtro de riesgo |
| F6 | COT extendido: OIS, swaps, FX implied vol | `cftc/ois_curve`, `fx_implied_vol`, `fx_forward_curve` | Posicionamiento institucional y expectativa de tipos | Régimen, no gatillo |
| F7 | Liquidez real del sistema | `economy/money_measures`, `primary_dealer_positioning`, `direction_of_trade` | Cuánto dinero circula | Backdrop de riesgo |
| F8 | Calendario económico y FOMC | `economy/calendar`, `fomc_documents` | Días de CPI/FOMC | Regla de no operar / cooldown |
| F9 | Posiciones cortas | `tmx/markets/short_interest`, `finra` | Presión bajista | Solo si se operan acciones |
| F10 | Materias primas y energía | `commodity/price/spot`, `jodi/oil/*` | Inflación real y ciclo | Régimen macro |
| F11 | Indicadores técnicos calculados | `technical/*` (59) | Cálculo independiente de los propios | Verificación, no señal nueva |
| F12 | Estadística y econometría | `quantitative/*`, `econometrics/*` | Estacionariedad, factores, normalidad | Validación |

---

## 3. Eje 2 — Los déficits declarados

| # | Déficit | Por qué | Cómo se cubre | Coste |
|---|---|---|---|---|
| D1 | Order flow nivel 2 | No está en OpenBB | WebSocket de Binance/Bybit, fuera de OpenBB | Medio-alto |
| D2 | On-chain | No está en OpenBB | blockchain.com, mempool.space, Glassnode free | Medio |
| D3 | Flujos de ETF de BTC/ETH | Nadie más lo da gratis | Farside / emisores | Bajo |
| D4 | Fear & Greed | Sentimiento minorista | alternative.me (gratis) | Muy bajo |
| D5 | Noticias y RSS | Eventos | `news/rss` | Bajo |

---

## 4. Eje 3 — De dato a decisión (aquí está el valor, no en el dato)

El error clásico es meter el valor crudo. Lo que sirve:

1. **Normalizar:** z-score o percentil con ventana larga, calculado siempre con
   datos anteriores a la fecha de la vela.
2. **Derivar:** lo interesante no es el funding, es su **velocidad de cambio**;
   no es la curva, es su **pendiente**.
3. **Agrupar:** 2-4 regímenes legibles (apalancado-euforia, apalancado-miedo,
   desapalancado, neutral).
4. **Una fuente no decide:** ninguna feature sola activa ni veta una operación.

---

## 5. Eje 4 — La puerta de validación

Se mantiene lo que ya existe y se endurece:

- Walk-forward multi-activo + **benchmark de misma exposición** (criterio actual).
- **Monte Carlo** sobre la secuencia de operaciones.
- **Costes reales** incluidos siempre.
- **Nuevo y obligatorio:** corrección por pruebas múltiples (Deflated Sharpe o
  equivalente). Si se prueban 20 features, alguna brillará por puro azar.
- **Nuevo:** selección de features **dentro** de cada ventana de train, nunca en test.

Regla: si no bate el benchmark de misma exposición fuera de muestra, **no entra**.
Sin excepciones. Ya evitó un error una vez con la EMA.

---

## 6. Eje 5 — Mapa concreto con Freqtrade

Freqtrade no trae datos externos. Los caminos reales:

| Nivel | Qué se usa | Qué hace | Riesgo |
|---|---|---|---|
| 1 | `populate_indicators` + parquet + `merge_asof` | Ya funciona: la estrategia ve el contexto | Ninguno, es lo actual |
| 2 | `custom_stake_amount` | Menos tamaño en régimen defensivo | Bajo |
| 3 | `confirm_trade_entry` / `confirm_trade_exit` | Veta entrar con funding extremo o día de FOMC | Bajo |
| 4 | `protections` (StoplossGuard, MaxDrawdown, Cooldown) | Frenos de riesgo global activados por contexto | Bajo |
| 5 | Telegram (`/status`) | Saber en qué régimen se está operando | Nulo |
| 6 | **Evitar** escribir el stake desde fuera | Frágil, rompe el control del bot | Alto |

El parquet se refresca **solo** a las 09:05 desde `C-38` (validado y con copia del anterior).

---

## 7. Eje 6 — Operación y app

- ✅ **Refresco automático diario del contexto** (`C-38`): tarea 09:05, valida antes de guardar, conserva el anterior, log y chequeo en `estado.py` (26/26). **El aviso vive en el panel** (`C-39`): verde si el último refresco terminó bien, rojo si falló, ámbar si lleva más de 48 h. El aviso **externo** está montado y **verificado** (C-42): corre tras cada refresco y entrega por Telegram (bot @AgentFinacieroBot).
- **Calendario de eventos** en el panel (CPI, FOMC) con los próximos 30 días.
- **Régimen actual vs histórico:** percentil del VIX/funding de hoy frente a 5 años.
- **"Qué cambió desde ayer":** diff del contexto, no una tabla entera.
- **Alerta Telegram** cuando cambia el régimen.
- **Vista de correlación:** cómo se comportó cada par según el régimen, usando los
  backtests. Esta vista dirá si merece la pena seguir.

---

## 8. Repositorios del usuario

Al escribir este plan **no había lista de repositorios en el contexto de la sesión**
(la conversación se compactó). En disco: `TradingAgents`, `TradingPython`,
`TradingPython2`, `TradingPython3`, `trading_bot_ia`, `EstudioGSD`,
`Bit_IA_Automatico`, `freqtrade`, `trading-bot-copy` (MT5).

**Pendiente:** que el usuario diga cuáles son y qué papel cumplen (decisión,
backtests, señales, datos) antes de integrar ninguno.

---

## 9. Tres packs para elegir

| Pack | Contenido | Trabajo | Objetivo | Si sale bien |
|---|---|---|---|---|
| **A — Mínimo útil** | F1 funding, F4 volatilidad cripto, F8 calendario, D4 Fear&Greed | 1-2 semanas | Filtro de riesgo: menos drawdown, no más P&L | Base para decidir B o C |
| **B — Cripto-nativo completo** | A + F2 basis, F3 OI, F5 opciones/DVOL, D3 flujos ETF, D2 on-chain básico | 3-6 semanas | Régimen cripto propio + gatillos de alta frecuencia | Mayor probabilidad real de edge |
| **C — Macro-institucional** | A + F6 OIS/FX vol, F7 liquidez y dealers, F10 commodities, F12 econometría | 2-4 semanas | Entender el ciclo; sirve si se operan índices/acciones | Complementa A o B |

**Recomendación: A primero.** Barato, sin claves, y cierra el hueco grande:
hoy no hay **nada** de alta frecuencia. B y C se deciden con los números de A.

> **Actualizado en S-18:** A se ejecutó y **cerró sin resultado** (`E-08` funding, `E-09`
> salidas: los dos negativos). El hueco no era "falta capa rápida", era "falta una señal
> con ventaja": apareció en el **momento transversal** entre pares (`E-10`), que no
> necesita ningún dato nuevo. B y C quedan **congelados** hasta que `P3` demuestre que
> la rotación funciona en modo aviso. Comprar datos antes de eso sería repetir el error.

---

## 10. Orden propuesto, con puertas

| Paso | Qué | Puerta para pasar al siguiente |
|---|---|---|
| 0 | **P8:** revalidar los 7 pares con el contexto corregido (`C-13`) | ✅ **cerrado** (`E-07`): 0/7 → 1/7, el veredicto no cambia |
| 1 | **F1 funding** ✅ `E-08` | ❌ descartado como filtro: evitar el funding alto resta 8 pts de mediana. Se conserva como termómetro |
| 1b | **Gestión de salida** (stop móvil, break-even, salida por media) ✅ `E-09` | ❌ descartada: empeora o empata. El problema **no** era la salida |
| 1c | **Cambiar la señal de entrada** ✅ `E-10` (momentum transversal) | ✅ **con ventaja**: percentil 99 frente al azar, 16/18 combinaciones lo baten. ❌ **no integrable**: drawdown −77 % a −93 % |
| 1d | **Control de riesgo** sobre el momentum ✅ `E-11` | ❌ régimen y volatilidad objetivo descartados: cuestan más retorno del que ahorran. ✅ **Calmar** adoptado como criterio de selección (`D-15`) |
| 1e | **Momentum absoluto por activo** ✅ `E-12` | ❌ descartado: baja el DD pero hunde el Calmar y mata la significación. **La hipótesis del universo quedaba abierta** |
| 1f | **Ampliar el universo a 24 pares** ✅ `E-13` | ❌ **mi hipótesis era falsa**: retorno y Calmar suben, el DD **empeora** (−80,0 % → −87,1 %). El drawdown es de la clase de activo (`D-21`) |
| 1g | **Configuración fija + dimensionado** ✅ `E-14`/`E-15` | ❌ **refutado**: la fase era un parámetro oculto (`E-16`); en mediana la regla no bate a la cesta y el walk-forward tampoco (`E-17`). El dimensionado queda sin objeto |
| 1h | **Escribir la rotación en Freqtrade** (`P3`) | ✅ **cerrado en falso positivo evitado**: escrita y verificada (296/296), **refutada antes de tocar un bot**. No se copia |
| 2 | Refresco automático + panel con calendario y régimen | ✅ refresco hecho y **visible** (`C-38` tarea 09:05 verificada, `C-39` tarjeta de aviso, **27/27**). ⚪ el calendario y la vista de régimen siguen pendientes |
| 3 | Decidir Pack B o C | Según lo que dijeron los números de A |
| 4 | Instalar en un bot **en modo aviso** (sin operar) | Semanas de avisos coherentes antes de arriesgar dinero |

> **Corrección importante del plan (2026-10-19).** El paso 1 se diseñó como "añadir features
> al contexto y medir". Las dos features medidas (`F1` funding, y la salida como control)
> dieron negativo, y el control negativo es el que enseña: si mover la salida tampoco
> cambia nada, es que **el problema no está en los alrededores de la señal, sino en la
> señal**. Añadir `F4` volatilidad cripto solo repetiría el patrón (y además no tiene
> historial suficiente por OpenBB: 17 días). El pack A queda **cerrado como vía** y el
> paso 1c pasa a ser el trabajo real.

---

## 11. Lo que NO se recomienda

- **Noticias y redes como señal:** ruido imposible de medir con honestidad. Como alerta, sí.
- **Order book nivel 2 en velas de 4h:** se destruye al agregar. Solo tiene sentido en segundos.
- **Acumular indicadores técnicos:** hay 59 rutas de `technical` y meter 20 sería
  garantizar sobreajuste.
- **Pagar datos antes de saber si el gratis aporta:** primero A, después se paga con criterio.
- **Tocar los bots en vivo sin una regla que haya pasado la puerta:** sigue bloqueado, y con
  razón. Ya no es que falte el paso 1h: es que **no hay nada que desplegar**. La rotación se
  escribió y se refutó (`E-16`/`E-17`); no se copia a los bots.

---

## 12. Seguimiento del plan (estado al cierre de S-26)

| Pregunta abierta del plan | Respuesta |
|---|---|
| ¿Se empieza por el paso 0 (revalidar con el contexto corregido)? | ✅ hecho: `E-07` — 0/7 → 1/7, el veredicto no cambió |
| ¿Pack A, B o C? | ✅ **A cerrado como vía**: funding (`E-08`) y salidas (`E-09`) dieron negativo. El trabajo real era **cambiar la señal de entrada**, y esa vía también se cerró (`E-16`/`E-17`) |
| ¿Lista de repositorios y su papel? | ✅ 9 repos con veredicto en `Ecosistema de herramientas.md`. Ninguno adoptado; `VectorBT` **en espera**, no urgente: no hay hipótesis que barrer |
| ¿Hay estrategia con ventaja? | ❌ **no**: la ventaja de `E-10`/`E-14` era en buena parte la fase del rebalanceo (`E-16`/`E-17`). El macro no la rescata (`E-18`) |
| ¿Se puede instalar? | ❌ **no**: no queda nada que instalar (`D-31`). `P3` quedó escrita y verificada, y **no se copia** a los bots |
| ¿Qué falta? | Mantenimiento (`P2` aviso externo, `P6` pruebas, `P9` reinicio tras cambios) y contexto informativo. **Ninguna señal pendiente de despliegue** |
| ¿Y el panel? | ✅ sirve para lo que sí hace bien: mostrar el entorno. Refresco diario validado y visible (`C-38`/`C-39`) |

---

## 13. Plan de producto para inversores (propuesta S-29)

> **No aprobado, no implementado.** El detalle vive en `Analisis y plan - fuente de investigacion.md`.

| Fase | Qué | Puerta de salida |
|---|---|---|
| **0. Contexto** (1 sem) | Activo · periodo · benchmark + fuente/as-of + gráfico por tarjeta | 100 % de tarjetas actualizadas |
| **1. Hablar claro** (2–3 sem) | Portada 3 respuestas, glosario, qué cambió, percentiles | 3/3 en < 60 s |
| **2. Descubrir** (4–6 sem) | FinanceDatabase, buscador, ficha, comparador, informe | 10 consultas + ficha + export |
| **3. Conversar** (4–6 sem) | Agente local con 6 herramientas y evaluación | ≥ 18/20, 20/20 citas, 0 consejos |

**Regla:** no se abre una fase sin pasar la puerta anterior. El agente no sustituye al panel: lo maneja y lo explica.

**Capa visual (transversal, §25):** D0 corre en paralelo a las fases 0–1: tokens, componentes, estándar de gráficos y criterios D0.1–D0.10. El tema se cambia con el **conmutador nativo System/Light/Dark** de Streamlit; no se construye uno propio. Sin esto, un cambio no se percibe como producto.

**Alcance (2026-10-20):** **todos los mercados** (7 clases). La cobertura real se mide y se muestra; hoy falta proveedor global para Europa/Asia/LatAm, así que se añade un fallback y un estado "no cubierto" visible (§26).

**Estado al cierre (2026-10-20):** propuesta, **sin implementar**. Aprobar `openbb-yfinance` + 10 años y las fases 0–1 antes de tocar código.
