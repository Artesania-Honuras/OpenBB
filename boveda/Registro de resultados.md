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
