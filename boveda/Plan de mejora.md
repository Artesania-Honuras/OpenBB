# Plan de mejora — de "datos que no dicen nada" a "datos que deciden"

- **Fecha:** 2026-10-19
- **Estado:** propuesta, **nada aplicado**
- **Contexto:** el panel ya funciona (23/23 ✅) pero el usuario pregunta para qué sirve.
  La respuesta corta: hoy solo hay **capa lenta** (macro) y se está usando como si fuera un gatillo.
- **Regla que manda:** ningún dato entra en vivo si no bate el **benchmark de misma exposición**
  fuera de muestra. Ver `Registro de resultados.md`.

---

## 0. Punto de partida real

| Ya existe | Detalle |
|---|---|
| API local | `127.0.0.1:6900` · 869 rutas · 18 providers |
| Panel visual | `127.0.0.1:8501` · 8 pestañas |
| Contexto diario | 13 columnas × 36.636 filas, con retrasos anti look-ahead |
| Puente a Freqtrade | parquet + `merge_asof` (0 NaN verificado) |
| Validación | walk-forward 7 pares + Monte Carlo + costes |
| **Endpoints usados** | **8 de 869** ← aquí está todo el margen |

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

El parquet debe refrescarse **antes** de arrancar el bot (hoy es manual).

---

## 7. Eje 6 — Operación y app

- Refresco automático diario del contexto (Programador de tareas de Windows) con aviso si falla.
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

---

## 10. Orden propuesto, con puertas

| Paso | Qué | Puerta para pasar al siguiente |
|---|---|---|
| 0 | **P8:** revalidar los 7 pares con el contexto corregido (`C-13`) | ✅ **cerrado** (`E-07`): 0/7 → 1/7, el veredicto no cambia |
| 1 | **F1 funding** ✅ `E-08` | ❌ descartado como filtro: evitar el funding alto resta 8 pts de mediana. Se conserva como termómetro |
| 1b | **Gestión de salida** (stop móvil, break-even, salida por media) ✅ `E-09` | ❌ descartada: empeora o empata. El problema **no** era la salida |
| 1c | **Cambiar la señal de entrada** ✅ `E-10` (momentum transversal) | ✅ **con ventaja**: percentil 99 frente al azar, 16/18 combinaciones lo baten. ❌ **no integrable**: drawdown −77 % a −93 % |
| 1d | **Control de riesgo** sobre el momentum (filtro de régimen, volatilidad objetivo) ⬅ *siguiente paso* | Bajar el drawdown por debajo del 20 % **sin** perder la ventaja frente a la cesta. La capa lenta entra aquí, no antes |
| 2 | Refresco automático + panel con calendario y régimen | `estado.py` 23/23 sin intervención manual |
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
- **Tocar los bots en vivo antes de P1:** sigue bloqueado, y con razón.

---

## 12. Decisiones que faltan del usuario

1. ¿Se empieza por el paso 0 (revalidar con el contexto corregido)?
2. ¿Pack A, B o C?
3. ¿Lista de repositorios y su papel?
