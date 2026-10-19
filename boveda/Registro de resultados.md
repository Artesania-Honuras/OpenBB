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
