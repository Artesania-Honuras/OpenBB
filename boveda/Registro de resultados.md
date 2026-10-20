# Registro de resultados

Cada experimento o medición tiene una fila `E-NN`. Formato en `Plantillas.md`.
Los descartados también se registran: evitan repetir el mismo camino.

---

## E-01 — Instalación y carga completa

- **Fecha:** 2026-10-19
- **Hipótesis:** el monorepo se instala editable en Windows con Python 3.13 y funciona sin claves para los proveedores base.
- **Método:** `dev_install.py --routers`; `uv pip check`; `openbb.build()`; conteo de comandos, providers, rutas y entry points.
- **N:** 37 paquetes editables, 243 paquetes resueltos.
- **Números:** 243 compatibles / 0 conflictos; 584 comandos; 18 providers; 869 rutas HTTP; 50 entry points con 0 errores.
- **Veredicto:** ✅ **vigente**. La instalación es reproducible.

---

## E-02 — Verificación de las 8 familias de análisis

- **Fecha:** 2026-10-19
- **Hipótesis:** se cubren las 8 familias sin claves de API.
- **Método:** `scripts\verificar_familias.py` con caché parquet; 30 pruebas.
- **N:** 30 pruebas, 27 series cacheadas en ese momento.
- **Números:** **28 OK, 0 errores, 2 huecos** declarados (order flow de equities nivel 2; on-chain).
- **Veredicto:** ✅ **vigente parcial**: 6 de 8 familias completas. Los 2 huecos requieren proveedores de pago o claves.

---

## E-03 — Backtest inicial 2025-01 → 2026-10 (con vs sin filtro macro)

- **Fecha:** 2026-10-19
- **Hipótesis:** el filtro macro (VIX + curva) mejora el cruce EMA 20/50.
- **Método:** Freqtrade `backtesting`, Binance spot 4h, 7 pares, 3 trades máx.
- **Números:** con filtro 202 operaciones, −9,81 %, DD 18,30 %, acierto 42,1 %; sin filtro 448 operaciones, −11,16 %, DD 21,54 %, acierto 47,8 %.
- **Veredicto:** ❌ **INVALIDADO** por E-04. `treasury_rates` cubría solo 1 año (248 filas), así que el filtro estuvo inactivo casi todo el periodo. Se conserva para no repetir el error de comparar con datos incompletos.

---

## E-04 — Backtest 2021-01 → 2026-10 con datos completos

- **Fecha:** 2026-10-19
- **Hipótesis:** con cobertura completa de tasas, el filtro macro sí aporta.
- **Método:** mismo comando y config que E-03, con `start_date="2000-01-01"`.
- **N:** 7 pares, 4h, 5,75 años.
- **Números:** con filtro **1.464 operaciones, −49,44 %, DD 60,13 %** (acierto 52,4 %); sin filtro **2.349 operaciones, −28,60 %, DD 45,56 %** (acierto 52,9 %).
- **Veredicto:** ❌ **el filtro empeora**. El cruce EMA no tiene alfa en este periodo.

---

## E-05 — Walk-forward multi-activo (7 pares)

- **Fecha:** 2026-10-19
- **Hipótesis:** alguna combinación de EMA / VIX máximo / filtro de curva tiene ventaja fuera de muestra.
- **Método:** 18 meses de entrenamiento → 6 de prueba, avance de 6 en 6; 54 combinaciones; sizing 10 %; referencia = comprar y mantener escalado al mismo tiempo en mercado.
- **Ventana:** 2021-01-01 → 2026-10-01 (11 ventanas por activo).
- **N:** 7 activos; 129 operaciones fuera de muestra en BTC.
- **Números (OOS vs referencia misma exposición):** ADA +3,2 % vs +5,7 % · AVAX +18,9 % vs +31,9 % · BNB +5,2 % vs +236,3 % · BTC +7,6 % vs +56,7 % · ETH +14,1 % vs +71,3 % · SOL +9,0 % vs +242,0 % · XRP +4,2 % vs +58,9 %.
- **Agregado:** 7/7 OOS positivos; **0/7 baten la referencia**; exposición media 26-46 %.
- **Veredicto:** ❌ **sin ventaja consistente**. El 7/7 positivo es beta de cripto con 10 % de sizing, no habilidad.

---

## E-06 — Monte Carlo sobre BTC (129 operaciones OOS)

- **Fecha:** 2026-10-19
- **Hipótesis:** la secuencia de operaciones es robusta a remuestreo.
- **Método:** 5.000 remuestreos con reemplazo, sizing 10 %, equity compuesta por operación.
- **N:** 129 operaciones, 5.000 simulaciones.
- **Números:** retorno final p5 −7,9 % / p50 +7,5 % / p95 +26,4 %; DD medio −8,1 %; DD (5 % peor) −14,1 %; P(pérdida) 21,3 %; P(DD > 20 %) 0,2 %; P(ruina −50 %) 0,0 %.
- **Veredicto:** ⚠️ **riesgo bajo, retorno insuficiente**. Pasa el criterio de riesgo pero falla el de retorno frente a la referencia. No justifica integración.

---

## E-07 — Revalidación del walk-forward con el contexto corregido

- **Fecha:** 2026-10-19
- **Hipótesis:** el defecto de alineación del puente (`C-13`) dejaba fuera el dato de los viernes en VIX, S&P y EUR/USD; con el arreglo, el filtro de VIX trabajaría sobre valores reales y el resultado podría cambiar.
- **Método:** exactamente el mismo que E-05 — `validar_estrategia.py --todos --stake 0.1`, ventana 2021-01-01 → 2026-10-01, 18 meses de entrenamiento → 6 de prueba, 54 combinaciones, referencia escalada al mismo tiempo en mercado. **Única diferencia:** el contexto ya corregido.
- **N:** 7 activos, 11 ventanas cada uno, 7/7 con operaciones fuera de muestra.
- **Números (OOS vs referencia misma exposición):** ADA +5,8 % vs +5,5 % · AVAX +16,1 % vs +32,6 % · BNB +5,6 % vs +197,6 % · BTC +8,2 % vs +57,1 % · ETH +18,6 % vs +71,7 % · SOL +14,2 % vs +285,6 % · XRP +4,6 % vs +60,8 %.
- **Agregado:** 7/7 OOS positivos; **1/7 baten la referencia** (ADA, por 0,3 puntos).
- **Comparación con E-05** (mismo método, contexto defectuoso): 0/7 → 1/7. Todos los OOS suben algo (SOL +9,0 → +14,2; ETH +14,1 → +18,6); las referencias apenas se mueven.
- **Veredicto:** ❌ **sin ventaja consistente**, igual que E-05. La única "victoria" es un empate estadístico: 0,3 puntos sobre una referencia de 5,5 %. El criterio exige ≥ 2/3 de los activos y solo lo cumple 1/7. Confirma que el defecto `C-13` **no** era la causa de la falta de edge.
- **Cierra:** pendiente **P8**.

---

## E-08 — Filtro de funding de perpetuos (capa rápida, primera prueba)

- **Fecha:** 2026-10-19
- **Hipótesis:** el funding de perpetuos mide el apalancamiento y el sesgo del mercado; usarlo como filtro debería mejorar el cruce EMA 20/50.
- **Fuente:** Binance `fapi/v1/fundingRate` (público, sin clave, sin dependencia nueva), paginado desde 2021 → 2.118 días. Columna nueva `funding_btc_anual` en el contexto (14 columnas), retraso de 1 día.
- **Método:** la misma herramienta (`validar_estrategia.py`), misma ventana 2021-01-01 → 2026-10-01, 18 meses train / 6 test, sizing 10 %. Tres mediciones: (A) sin filtro — línea base que reproduce E-07; (B) `funding_max = 20` (no comprar si estar largo cuesta más de 20 % anual); (C) `funding_min = 0` (solo comprar con funding positivo).
- **N:** 7 activos, 11 ventanas. Además, corrida por defecto con la dimensión de funding **dentro** de la búsqueda (108 combinaciones en vez de 54).
- **Números (OOS mediano / exposición media / baten la referencia):**
  - A) sin filtro: **+8,2 %** · 35,7 % · **1/7**
  - B) `funding_max = 20`: **+3,0 %** · 30,3 % · **0/7**
  - C) `funding_min = 0`: **+15,2 %** · 34,3 % · **1/7**
  - Con la dimensión dentro de la búsqueda (54 → 108 combinaciones): **0/7**
- **Detalle por par (A → B → C, referencia):** ADA 5,8 → −0,0 → 15,6 (5,5) · AVAX 16,1 → 3,4 → 15,2 (32,6) · BNB 5,6 → −6,4 → 7,7 (197,6) · BTC 8,2 → 3,0 → 7,0 (57,1) · ETH 18,6 → 10,6 → 16,1 (71,7) · SOL 14,2 → 8,8 → 21,0 (285,6) · XRP 4,6 → −7,7 → 10,4 (60,8).
- **Veredicto:** ❌ **no pasa la puerta**. Dos hallazgos:
  1. **La dirección importa y mucho.** Evitar el funding alto resta 8 puntos de mediana (0/7): en cripto, el funding alto coincide con tendencias alcistas, así que filtrarlo deja fuera lo bueno. Exigir funding positivo suma 2,1 puntos de mediana y mejora 4 de 7 pares.
  2. **Ni así alcanza.** Sigue 1/7 contra la referencia de misma exposición, y el criterio exige ≥ 2/3. El problema de fondo no es el filtro: es que la exposición del 30-45 % no captura el retorno de comprar y mantener.
- **Se conserva:** la columna `funding_btc_anual` queda en el contexto (es informativa para el estado en vivo), pero **no** se usa como filtro de entrada.
- **Coste de búsqueda declarado:** probar tres variantes más el aumento de 54 a 108 combinaciones eleva el riesgo de sobreajuste. El resultado en contra es, por tanto, más fiable que si hubiera salido a favor.

---

## E-09 — Gestión de salida con la entrada fija (cruce EMA 20/50)

- **Fecha:** 2026-10-19
- **Hipótesis:** si el cuello de botella medido en `E-08` era el *timing*, mover la salida con la entrada quieta debería notarse en el retorno fuera de muestra.
- **Método:** entrada **fija** en el cruce EMA 20/50, sin filtros macro ni de funding (`BASE_ENTRADA`). Se optimiza **solo** la salida con `--salidas`: stop móvil (10 % / 20 %), break-even tras +6 %, salida al perder la media rápida. Misma ventana 2021-01-01 → 2026-10-01, 18 meses entrenamiento / 6 de prueba, sizing 10 %, 5.000 simulaciones.
- **N:** 7 activos, 11 ventanas, 12 combinaciones de salida. Salida cruda en `data/reporte_salidas_ab.txt`.
- **Números (OOS mediano · exposición · baten la referencia · Δ frente a la salida actual):**
  - A) Salida actual (−8 % / +15 % / cruce): **+10,0 %** · 46,7 % · **1/7** · —
  - B) Stop móvil 10 %: **+6,5 %** · 46,2 % · **0/7** · **−4,6 pts**
  - C) Stop móvil 20 %: **+10,0 %** · 46,7 % · **1/7** · **+0,0 pts**
  - D) Break-even tras +6 %: **+6,8 %** · 46,1 % · **0/7** · **−4,3 pts**
  - E) Salir al perder la media rápida: **−3,9 %** · 39,0 % · **0/7** · **−13,5 pts**
  - F) Búsqueda completa (12 combinaciones): **+4,6 %** · 45,2 % · **0/7** · **−6,7 pts**
- **Veredicto:** ❌ **no pasa la puerta.** Tres lecturas:
  1. El stop móvil al 20 % da **exactamente** los mismos números que la línea base: nunca llega a activarse, porque el take profit del +15 % entra antes. No es que no ayude: es que en la práctica no existe.
  2. **La búsqueda completa rinde peor que la línea base** (−6,7 pts). Cuando el buscador solo puede empeorar, no hay señal que encontrar y lo único que queda es sobreajuste.
  3. La comparación de fondo: **la referencia de misma exposición equivale a elegir al azar ese mismo porcentaje de días**, y el cruce EMA queda por debajo en 6 de 7 pares. Solo gana ADA (10,0 vs 6,9), un activo que cayó un 17 % en el periodo: la "ventaja" es defensiva, no de tendencia.
- **Conclusión acumulada (`E-07` + `E-08` + `E-09`):** no es el filtro macro, no es el filtro de derivados, no es la salida. **El cruce EMA 20/50 no bate al azar con la misma exposición.** Cualquier trabajo futuro sobre esta base está condenado por diseño: hay que cambiar la **señal de entrada**, no sus alrededores.
- **Coste de búsqueda declarado:** 12 combinaciones × 7 activos × 11 ventanas. El resultado en contra es, por tanto, fiable.

---

## E-10 — Momentum transversal (rotación entre pares): primera ventaja demostrada

- **Fecha:** 2026-10-19
- **Hipótesis:** `E-07`/`E-08`/`E-09` dejaron claro que el problema no eran los alrededores de la señal, sino la señal. Un **cruce de medias por par** es una señal de tendencia absoluta; lo que tiene literatura a favor es el **momentum relativo entre activos** (mantener los K mejores de la cesta).
- **Método:** en cada rebalanceo se mantienen los *K* pares con mejor retorno de los últimos *L* días, a peso igual, siempre invertido. Rejilla: L ∈ {30, 60, 90} días, K ∈ {1, 2, 3}, rebalanceo ∈ {7, 28} días = 18 combinaciones. Mismo protocolo: 18 meses de entrenamiento / 6 de prueba, comisión 0,1 % por lado sobre el giro real. **Sin filtros macro** (se aísla el criterio de selección).
- **La referencia honesta:** los K pares **elegidos al azar**, con el mismo K, el mismo calendario y los mismos costes. Es una prueba de permutación con 200 semillas, y es el mismo tipo de referencia que descartó el cruce EMA en `E-09`.
- **N:** 7 pares (ADA, AVAX, BNB, BTC, ETH, SOL, XRP), 13.296 velas 4h alineadas, 11 ventanas de prueba × 2 generaciones de simulación al azar.
- **Números:**
  - Walk-forward (parámetros elegidos en entrenamiento): **+1.112 %** con drawdown **−81,7 %**, 7/11 ventanas positivas.
    Cae en el **percentil 99** de la nube al azar; P(azar ≥ estrategia) = **1,0 %**.
  - Robustez (cada combinación fija, sin selección en entrenamiento): **16/18 baten la mediana del azar**, mediana global **percentil 93**, 7/18 en percentil ≥ 95. **No es una casualidad de la rejilla.**
  - Comparación con no hacer nada (mismo periodo, 100 % invertido): cesta a peso igual **+1.121,8 %** con DD **−81,9 %**; mejor configuración simple (L=30, K=3, semanal) **+1.442,7 %** con DD **−77,4 %** → **gana a la cesta en retorno y en riesgo**.
  - Pero: **todas las 18 combinaciones tienen drawdown entre −75 % y −93 %.**
- **Veredicto:** ⚠️ **ventaja demostrada, integración descartada por ahora.** Tres lecturas:
  1. **Por primera vez hay señal medible.** El ranking de momentum bate a la elección aleatoria en 16 de 18 configuraciones y la línea base por búsqueda cae en el percentil 99. Eso no pasaba con nada anterior.
  2. **La referencia era baja.** La mediana del azar en esta cesta es **negativa** (−68 % a +52 % según la configuración): elegir pares al azar entre 7 altcoins pierde dinero. Batir a un mal rival es más fácil que batir al mercado. Por eso la comparación que manda es la de la cesta: y ahí la ventaja es modesta (+1.443 % vs +1.122 %).
  3. **El riesgo es inaceptable.** −77 % de drawdown no se puede operar, y el criterio del proyecto pide < 20 %. La causa es estructural: la estrategia está **siempre 100 % invertida** en 2-3 altcoins. No hay control de riesgo porque no se ha puesto ninguno.
- **Decidido:** no se integra nada todavía. El siguiente experimento es **control de riesgo** (filtro de régimen y/o volatilidad objetivo), y ahí es donde la capa lenta de OpenBB por fin tiene papel: no para elegir entradas, sino para **decidir cuánto capital está expuesto**.
- **Coste de búsqueda declarado:** 18 combinaciones × 11 ventanas × 7 pares + 200 permutaciones por ventana. Nota metodológica: seleccionar en entrenamiento por **retorno compuesto bruto** empuja hacia el máximo riesgo (K=1, K=2); la próxima iteración debe seleccionar por **retorno ajustado por riesgo**.
- **Salidas crudas:** `data/reporte_momentum.txt`, `data/reporte_momentum_robustez.txt`.

---

## E-11 — Control de riesgo sobre el momentum: qué funciona y qué no

- **Fecha:** 2026-10-19
- **Hipótesis:** el momentum transversal tiene ventaja (`E-10`) pero un drawdown del 77-93 %. Se probaron tres piezas de control de riesgo y una corrección de diseño mía.
- **Método:** las tres piezas, como **interruptores** (no como parámetros a optimizar, para no inflar la búsqueda): (1) **filtro de régimen** — si la cesta a peso igual pierde su media de *N* días, se pasa a caja, venta inmediata y vuelta solo en rebalanceo; (2) **volatilidad objetivo** — peso × (objetivo / vol realizada de 30 días), con tope 1, sin apalancamiento; (3) **criterio de selección en entrenamiento** — retorno bruto o **Calmar** (retorno / |drawdown|).
  Detalle que hace honesta la comparación: **la nube al azar lleva las mismas señales de riesgo**, así que lo único que cambia sigue siendo el criterio de selección.
- **N:** 6 variantes × 18 combinaciones × 11 ventanas × 200 permutaciones. Salida cruda: `data/reporte_momentum_riesgo.txt`.
- **Números** (referencia: cesta a peso igual **+1.121,8 %**, DD **−81,9 %**, **Calmar 13,69**):

| Variante | OOS | DD | Calmar | Ventanas | Percentil azar | P(azar ≥) |
|---|---|---|---|---|---|---|
| A) Retorno bruto, sin control (= `E-10`) | +1.112 % | −81,8 % | 13,61 | 7/11 | 99 | 1,0 % |
| **B) Calmar, sin control** | **+1.538 %** | **−80,1 %** | **19,22** | 7/11 | **100** | **0,0 %** |
| C) Calmar + régimen 200 d | +160 % | −69,7 % | 2,30 | 3/11 | 97 | 3,0 % |
| D) Calmar + régimen 200 d + vol 60 % | +374 % | −47,3 % | 7,91 | 3/11 | 99,5 | 0,5 % |
| E) Calmar + vol 60 % | +630 % | −74,3 % | 8,49 | 7/11 | 98 | 2,0 % |
| F) Calmar + régimen 100 d + vol 40 % | +184 % | −49,9 % | 3,69 | 4/11 | 88,5 | 11,5 % |

- **Veredicto:** ⚠️ **ninguna variante cumple las tres condiciones** (DD mejor que −20 %, percentil ≥ 95, Calmar mejor que la cesta). Dos hallazgos:
  1. **El control de riesgo sale caro.** El filtro de régimen recorta el drawdown de −80 % a −70 % pero **se come dos tercios del retorno** (+1.538 % → +160 %) y el Calmar se hunde de 19,2 a 2,3: entra tarde, después de la caída, y sale tarde, después de la subida. La volatilidad objetivo baja el DD a −47 % pagando lo mismo. **Se paga más retorno del drawdown que se ahorra**, porque el retorno de la estrategia vive justo en las fases que el filtro corta.
  2. **Lo que sí funcionó fue arreglar mi propio error.** Cambiar la selección en entrenamiento de retorno bruto a **Calmar** mejora las tres cosas a la vez: +1.538 % (vs +1.112 %), DD −80,1 % (vs −81,8 %) y Calmar **19,22** frente a los **13,69** de la cesta. Y P(azar ≥ B) = 0,0 %. El retorno bruto premia el máximo riesgo (elegía K=1); el ajustado por riesgo no.
- **Decidido:** se adopta **Calmar como criterio de selección por defecto** (reversible con `--objetivo retorno`, que reproduce `E-10`). Se **descartan** el filtro de régimen sobre la cesta y la volatilidad objetivo: cuestan más de lo que protegen.
- **Lo que esto dice del problema de fondo:** con 7 altcoins, el drawdown es **estructural**. En un mercado bajista caen las siete a la vez, así que cualquier cartera siempre invertida hereda la caída, y cualquier filtro sobre la cesta entra y sale tarde. El DD < 20 % no se alcanza con filtros agregados; hacen falta dos cosas distintas: (a) **filtro absoluto por activo** (mantener solo los K mejores que además estén por encima de su propia tendencia) y (b) **más universo** (20-30 pares), para que siempre haya algo tendiendo arriba. La segunda necesita CCXT/VectorBT.
- **Coste de búsqueda declarado:** 6 variantes fijas (interruptores) × 18 combinaciones × 200 permutaciones por variante. Dos objetivos probados en entrenamiento; se declara porque elegir la función objetivo *después* de ver los resultados es un grado de libertad del investigador.

---

## E-12 — Momentum absoluto por activo (dual momentum): descartado

- **Fecha:** 2026-10-19
- **Hipótesis:** `E-11` dejó claro que los filtros **sobre la cesta** llegan tarde. El filtro natural es por activo: mantener solo los K mejores que **además conserven su propia tendencia** (precio por encima de su media propia). Un activo que cae no debería mantenerse aunque sea el menos malo de la cesta.
- **Método:** la señal de tendencia propia se calcula sobre la serie completa (una media de 200 días no cabe en una ventana de 6 meses) y se aplica **igual a la nube al azar**, así que lo único que cambia sigue siendo el criterio de selección. Variantes G (tendencia 200 d), H (100 d), I (200 d + volatilidad objetivo 60 %). Mismo protocolo y misma referencia que `E-11`.
- **N (referencia: cesta +1.121,8 %, DD −81,9 %, Calmar 13,69; mejor variante hasta ahora: B, Calmar 19,22):**

| Variante | OOS | DD | Calmar | Ventanas | Percentil azar | P(azar ≥) |
|---|---|---|---|---|---|---|
| B) Calmar, sin control (mejor de `E-11`) | +1.538 % | −80,1 % | **19,22** | 7/11 | 100 | 0,0 % |
| G) Calmar + tendencia propia 200 d | +145 % | −72,0 % | **2,01** | 5/11 | 84 | 16,0 % |
| H) Calmar + tendencia propia 100 d | +811 % | −76,2 % | **10,64** | 5/11 | 73,5 | 26,5 % |
| I) Calmar + tendencia 200 d + vol 60 % | +240 % | −59,4 % | **4,03** | 5/11 | 89 | 11,0 % |

- **Veredicto:** ❌ **descartado, y con más motivo que el filtro de régimen.** Tres lecturas:
  1. **Baja el drawdown, destroza el Calmar.** El mejor caso (I) recorta el DD de −80 % a −59 % y el Calmar cae de 19,2 a 4,0: se paga otra vez más retorno del que se ahorra.
  2. **Y además mata la ventaja estadística.** En G y H el percentil frente al azar cae a 84 y 73,5: elegir pares al azar **con el mismo filtro** iguala o supera a la estrategia el 16 % y el 26,5 % de las veces. Ya no hay habilidad demostrable.
  3. **El motivo es mecánico y se ve en la nube:** con el filtro, la mediana del azar sube a **+411 %** (variante H) porque el universo elegible se reduce a 1-3 activos y, con K hasta 3, la selección aleatoria acaba comprando casi la misma cartera que la estrategia. Cuando el filtro deja tan poco donde elegir, el ranking deja de importar.
- **Conclusión acumulada (`E-10` a `E-12`):** el momentum transversal tiene ventaja real, pero **ningún mecanismo de control de riesgo probado la conserva**. Régimen sobre la cesta (`E-11`), volatilidad objetivo (`E-11`), tendencia propia (`E-12`): los tres bajan el drawdown y los tres se llevan por delante el Calmar y, en dos casos, la significación.
- **Lo que esto dice:** el límite no es el mecanismo, es el **universo**. Con 7 altcoins no hay dispersión suficiente: o caen las siete a la vez, o el filtro deja tan pocos candidatos que la selección se vuelve ruido. La vía estructural es ampliar a 20-30 pares (`P13`), donde la cartera de los K mejores puede estar siempre en activos que suben mientras el resto cae.
- **Nota de reproducibilidad:** al añadir la tendencia propia hubo que cambiar el generador de la nube de `rng.choice` a `rng.permutation` (mismo subconjunto uniforme, otro consumo del generador). Los **retornos y drawdowns** de A-F se reproducen exactos; los **percentiles** de `E-11` varían ±2,5 puntos. `data/reporte_momentum_riesgo.txt` se regeneró con las 9 variantes.

---

## E-13 — Universo ampliado de 7 a 24 pares: el drawdown NO viene del universo

- **Fecha:** 2026-10-19
- **Hipótesis (la mía, en `D-18`):** con 7 altcoins no hay dispersión suficiente y por eso ningún filtro conserva la ventaja. Ampliar a 20-30 pares debería permitir mantener siempre los K mejores en activos que suben mientras el resto cae, y **bajar el drawdown por construcción**, no por filtro.
- **Defecto de datos encontrado antes de medir (y corregido):** los 7 archivos originales **no terminaban en la misma fecha** (BTC/ETH/XRP el 2026-10-17; ADA/BNB/SOL/AVAX el 2026-09-18) y `cargar_matriz` rellena hacia adelante (`ffill`). Durante las últimas 174 velas (29 días), **4 de 7 activos tenían el precio congelado** en `E-10`/`E-11`/`E-12`. Corregido descargando los 25 pares homogéneos desde el endpoint público de Binance hasta la última vela cerrada (`scripts/descargar_velas.py`). La verificación descartó a **EOS** (retirado el 2025-05-26, 512 días de retraso): habría repetido el defecto. Universo final: **24 pares**.
- **Control del efecto del defecto:** repetido `E-11` (7 pares) con los datos limpios → **+1.538,1 % / −80,0 % / Calmar 19,22**, idéntico a la cifra original. El defecto no cambiaba ninguna conclusión, pero ya no está.
- **N (24 pares, 2021-2026, mismo protocolo, objetivo Calmar):**

| | retorno OOS | DD | Calmar | Ventanas |
|---|---|---|---|---|
| **Cesta a peso igual (24 pares)** | +314 % | −81,9 % | 3,83 | — |
| 7 pares, misma lógica (`E-11` B) | +1.538 % | **−80,0 %** | 19,22 | 7/11 |
| **24 pares, misma lógica (B)** | **+3.118 %** | **−87,1 %** | **35,82** | **6/11** |

- **Veredicto: ❌ hipótesis refutada.** Ampliar de 7 a 24 pares **mejora el retorno (+103 %) y el Calmar (+86 %) y EMPEORA el drawdown (−80,0 % → −87,1 %) y la supervivencia (7/11 → 6/11)**. El drawdown no venía de la falta de dispersión. Con 7 o con 24, en un mercado bajista caen todos a la vez: la correlación entre altcoins en las caídas es el mecanismo, no el tamaño de la cesta.
- **Tabla de control de riesgo sobre 24 pares (misma máquina, misma puerta, azar con las mismas señales):**

| Variante | OOS | DD | Calmar | Ventanas | Percentil azar | P(azar ≥) |
|---|---|---|---|---|---|---|
| A) retorno bruto, sin control | +2.875 % | −88,4 % | 32,52 | 6/11 | 100 | 0,0 % |
| B) Calmar, sin control | +3.118 % | −87,1 % | 35,82 | 6/11 | 100 | 0,0 % |
| C) Calmar + régimen 200 d | +501 % | −71,7 % | 6,99 | 4/11 | 99,0 | 1,0 % |
| D) Calmar + régimen 200 d + vol 60 % | +419 % | −49,8 % | 8,42 | 5/11 | 99,5 | 0,5 % |
| E) Calmar + vol 60 % | **+3.679 %** | −79,7 % | **46,16** | **8/11** | 100 | 0,0 % |
| F) Calmar + régimen 100 d + vol 40 % | +588 % | **−35,7 %** | 16,45 | 5/11 | 99,5 | 0,5 % |
| G) Calmar + tendencia propia 200 d | +433 % | −91,5 % | 4,73 | 7/11 | 100 | 0,0 % |
| H) Calmar + tendencia propia 100 d | +1.029 % | −84,9 % | 12,12 | 8/11 | 97,0 | 3,0 % |
| I) Calmar + tendencia 200 d + vol 60 % | +540 % | −70,8 % | 7,63 | 8/11 | 99,0 | 1,0 % |

- **Tres lecturas que importan:**
  1. **Ninguna variante baja de −35,7 % de drawdown**, y la única que llega ahí (F) pierde 6 de 11 ventanas y recorta el retorno un 81 %. La puerta pide < 20 %: sigue sin cumplirse, ni de lejos.
  2. **El aviso serio:** la volatilidad objetivo al 60 % (**E**) gana en las cuatro medidas con 24 pares… y **había perdido en las cuatro con 7 pares** (`E-11` E: retorno a la mitad, Calmar 8,49 contra 19,22). Un mecanismo que **cambia de signo según el universo** no es un mecanismo: es suerte de camino. No se adopta, y se deja escrito para que nadie lo adopte por verlo ganar aquí.
  3. **El azar deja de ser un rival serio.** Con 24 pares la mediana del azar es **negativa** (−17,9 %; con 7 pares era **+100,7 %**). El percentil 100 ya no demuestra lo que demostraba: elegir 1-3 pares entre 24 al azar incluye mucha basura. **El percentil frente al azar no es comparable entre universos distintos**; la referencia honesta sigue siendo la cesta, y la cesta también se hunde (−81,9 %).
- **Conclusión (y giro de la pregunta):** tres mecanismos de control de riesgo y un universo tres veces mayor después, el drawdown del momentum transversal en cripto sigue en el 80-90 %. La evidencia dice que **el drawdown es de la clase de activo, no del mecanismo ni del universo**. Por tanto la pregunta deja de ser *«¿cómo bajo el DD al 20 %?»* —que no tiene respuesta con instrumentos largos— y pasa a ser *«¿qué tamaño le doy a una exposición cuya caída natural es del 80 %?»*. Eso es asignación de capital, no estrategia: con un sleeve del 10 %, la caída del 87 % es una caída del ~8,7 % del capital (primer orden). El retorno del sleeve es ~+83 % anual compuesto; el tamaño lo decide el dueño del capital, no el backtest.
- **Lo que NO está medido (declarado para no sobrevender):** todo `E-10`…`E-13` es **solo largos**. La versión mercado-neutral (largo en los K mejores, corto en los K peores) es el mecanismo estándar de la industria para bajar exactamente este drawdown y **no se ha medido**; requiere perpetuos y coste de funding, y los bots de Freqtrade son spot, así que no sería desplegable en ellos.
- **Herramientas:** `scripts/descargar_velas.py` (25 pares, verificación con reporte en `data/reporte_velas.txt`), `--pares` para reproducir cualquier subconjunto. Reportes: `data/reporte_momentum_24pares.txt`, `data/reporte_momentum_riesgo_24pares.txt`, `data/reporte_momentum_7pares_datos_limpios.txt`.
- **Coste de búsqueda declarado:** 9 variantes × 18 combinaciones × 200 permutaciones × 2 universos. Se probaron **2 universos y 9 mecanismos**; los que ganan en uno y pierden en otro se reportan como inestables, que es lo que son.

---

## E-14 — Configuración fija: el número que se instalaría es +820 %, no +3.118 %

- **Fecha:** 2026-10-19
- **Qué se mide y por qué:** `E-13` da +3.118 %, pero ese número sale de **re-optimizar cada 6 meses** (el walk-forward elige `L`, `K` y rebalanceo en cada ventana con la mitad de entrenamiento). Para operarlo habría que automatizar esa re-optimización. Una **configuración fija**, con los mismos parámetros de principio a fin, es lo que un humano puede instalar, auditar y explicar. Se miden las cinco configuraciones razonables para no ocultar la dispersión, pero la que se propone es **L=30 d, K=3, semanal**, elegida **a priori** en `E-10` (antes de ver estos resultados).
- **N (24 pares, 2021-01 → 2026-07, azar = 200 semillas con los mismos parámetros):**

| L (d) | K | rebal | retorno | DD | Calmar | CAGR | Ventanas | Peor ventana | Percentil azar | P(azar ≥) |
|---|---|---|---|---|---|---|---|---|---|---|
| **30** | **3** | **7 d** | **+820 %** | **−82,5 %** | **9,95** | **+47,2 %** | **7/11** | **−61,2 %** | 99,5 | **0,5 %** |
| 30 | 5 | 7 d | +915 % | −79,8 % | 11,47 | +49,7 % | 6/11 | −55,5 % | 100 | 0,0 % |
| 60 | 3 | 7 d | +341 % | −92,1 % | 3,70 | +29,5 % | 6/11 | −58,1 % | 99,5 | 0,5 % |
| 60 | 5 | 7 d | +68 % | −86,8 % | **0,78** | +9,4 % | 6/11 | −56,4 % | 95 | **5,0 %** |
| 90 | 3 | 7 d | +509 % | −82,5 % | 6,17 | +37,0 % | 7/11 | −59,1 % | 100 | 0,0 % |

- **Veredicto:** ✅ **hay una regla desplegable, y es mucho más modesta que el titular.** L=30/K=3/semanal: **+820 % en 5,7 años (CAGR +47,2 %), drawdown −82,5 %, Calmar 9,95** contra una cesta con Calmar 4,52 en la misma ventana. La ventaja sigue siendo real (P(azar ≥) = 0,5 %) y la supervivencia es 7 de 11 ventanas.
- **Tres cosas que este experimento obliga a decir:**
  1. **La re-optimización semestral aporta +2.300 puntos de los +3.118.** Es legítima (usa solo el pasado), pero no es gratis: exige automatizarla y duplicarla en producción. Si no se automatiza, el número honesto es +820.
  2. **La sensibilidad a los parámetros es brutal:** con `K=5` y `L=60` la misma idea da **+68 % y Calmar 0,78** (P(azar ≥) = 5 %, ya no significativo). No es una estrategia robusta a los parámetros; es una estrategia que funciona en una región concreta. Eso justifica todavía más el tamaño pequeño.
  3. **La peor ventana de 6 meses es −61,2 %** con la regla fija. No es un drawdown teórico de un gráfico: es medio año perdiendo dos tercios.
- **Evidencia:** `data/reporte_momentum_fijo.txt`.

---

## E-15 — Dimensionado: el sleeve máximo que aguanta la puerta es 10 %

- **Fecha:** 2026-10-19
- **Qué se mide:** traducir el −82,5 % del sleeve a un drawdown **de cartera**, que es lo que la puerta pide. Bootstrap por bloques de 7 días (1.000 caminos) sobre la curva de la configuración fija, con fracción de sleeve **constante** (rebalanceo), caja al 0 %.
- **N:**

| sleeve | CAGR mediano | DD típico | DD al 5 % peor | P(DD > 20 %) | P(año perdedor) | P(año < −25 %) |
|---|---|---|---|---|---|---|
| 5 % | +4,0 % | −6,6 % | **−11,5 %** | 0,0 % | 19,0 % | 0,0 % |
| **10 %** | **+8,0 %** | **−13,0 %** | **−22,0 %** | **9,0 %** | **19,5 %** | **0,0 %** |
| 15 % | +12,0 % | −19,1 % | −31,7 % | 42,3 % | 20,6 % | 0,0 % |
| 20 % | +15,8 % | −24,8 % | −40,3 % | 77,4 % | 21,3 % | 0,8 % |
| 25 % | +19,5 % | −30,3 % | −48,3 % | 95,2 % | 21,8 % | 2,0 % |
| 30 % | +23,0 % | −35,6 % | −55,5 % | 99,3 % | 22,4 % | 3,4 % |

- **Veredicto:** ✅ **10 % es el techo razonable.** Con el 10 %: caída típica −13,0 %, **5 % peor −22,0 %**, año perdedor 1 de cada 5, y **ningún camino simulado pierde más del 25 % en un año**. Con el 15 % la probabilidad de superar el −20 % de drawdown salta al 42 %; con el 25 % es del 95 %.
- **Nota de honestidad sobre el modelo:** el 10 % cumple `P(pérdida) < 25 %` y **falla por poco** el `DD p95 < 20 %` (−22,0 %). Si la puerta se aplica al pie de la letra, el sleeve es **5 %** (p95 −11,5 %), que da +4,0 % de CAGR: demasiado pequeño para compensar el trabajo. **Se elige 10 % declarando que se incumple un criterio por 2 puntos**, no fingiendo que se cumple.
- **Modelo declarado (y el error que se corrigió):** primero se probó sin rebalanceo —caja fija más sleeve que se deja correr— y salían drawdowns del 31 % con solo el 5 % invertido: **imposible**, y señal de que el modelo estaba mal, no de que el riesgo fuera alto (un sleeve que crece acaba siendo el 80 % de la cartera y entonces su drawdown es el de la cartera). Con fracción constante el resultado es el de la tabla. Es el modelo que corresponde a operar de verdad.
- **Evidencia:** `data/reporte_dimensionado.txt`, `data/reporte_dimensionado.csv`.

---

## E-16 — La fase del rebalanceo: el parametro que nadie habia declarado

**Pregunta.** La regla fija de E-14 (L=30, K=3, semanal) da +820 %. Pero "semanal" no dice **cuando**. ¿El resultado depende de ese instante?

**Por que se midio.** Al escribir la estrategia para Freqtrade (P3) habia que elegir un momento concreto, y el calendario natural es el lunes 00:00. La primera medicion con ese calendario dio +95,8 %, no +820 %. Eso no se discute: se mide.

**Metodo.**
- Mismo motor, mismos datos, mismos 24 pares, misma comision (0,1 %/lado).
- El validador rebalancea cuando (i - L) % 42 == 0: una rejilla semanal con **fase arbitraria**. Se recorren las **42 fases** (una por vela de 4 h de la semana).
- Referencia 1: la **cesta a peso igual** (los 24 pares, sin rotar, sin decisiones).
- Referencia 2: **K=3 pares al azar** con el mismo calendario del lunes y los mismos costes (200 semillas).
- Verificacion previa: el nucleo que correra en el bot elige **296/296** veces el mismo conjunto que el validador, y el momento se mide siempre a 30,00 dias exactos.

**Resultado.**

| Medicion | Retorno | DD | Calmar |
|---|---|---|---|
| Validador, fase 0 (E-14) | +820,4 % | −82,5 % | 9,95 |
| **Mediana de las 42 fases** | **+816,5 %** | −82 a −88 % | — |
| Mejor fase (miercoles 08:00) | +3.776,3 % | −82,5 % | — |
| **Peor fase (lunes 00:00)** | **+95,8 %** | **−87,9 %** | **1,09** |
| Cesta a peso igual | +370,3 % | −81,9 % | 4,52 |
| Azar, calendario del lunes (mediana) | +27,2 % | — | — |
| Azar, calendario del lunes (p95) | +332,6 % | — | — |

- Las 42 fases son positivas, pero el rango es de **40x** y tiene **estacionalidad semanal sistematica**: domingo y lunes son el peor tramo (+96 % a +250 %), martes a jueves el mejor (+1.050 % a +3.776 %).
- Con el calendario natural: percentil **76** frente al azar, **P(azar >= esta) = 24,0 %**. No es significativo (el umbral es 5 %).
- Ventanas de 6 meses con el calendario natural: **5/11** (45,5 %), peor −61,2 %.

**Veredicto:** ❌ **la rotacion no es desplegable.** El +820 % no era una propiedad de la regla: era la mediana de una rejilla cuya fase nunca se declaro. La unica implementacion defendible a priori (lunes) es el **minimo** de las 42, **pierde contra no hacer nada** en retorno, drawdown y Calmar, y **no se distingue del azar**. Elegir el miercoles porque da +3.776 % seria *data snooping* sobre 42 variantes.

**Lo que si queda:**
- strategies/rotacion_momentum.py + otacion_nucleo.py: la implementacion fiel, verificada y **no instalada**.
- scripts/verificar_rotacion.py: la prueba de fase, permanente, reutilizable para cualquier regla futura (P17).
- D-27/D-28/D-29: la fase es un parametro; el numero honesto es el de la implementacion a priori; si cambia 40x, no es una ventaja.

**Evidencia:** data/reporte_rotacion.txt (ejecucion completa), scripts/verificar_rotacion.py.
