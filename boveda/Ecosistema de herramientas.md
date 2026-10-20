# Ecosistema de herramientas del usuario

**Fecha:** 2026-10-19 · **Origen:** lista aportada por el usuario (`P10`, cerrado)
**Regla:** aquí se dice para qué sirve cada repo **en este proyecto**, no para qué sirve en general.
Un repo que no entra no es un repo malo: es que no tiene papel.

## 1. Los nueve

| # | Repositorio | Tipo | Papel en este proyecto | Veredicto |
|---|---|---|---|---|
| 02 | **TradingAgents** | Agentes de IA | Capa de decisión cualitativa (noticias, sentimiento). No se puede medir con la puerta del proyecto: no hay forma honesta de validarlo fuera de muestra | ⏸️ **Más adelante, y solo como aviso.** Nunca como gatillo mientras no pase una puerta |
| 03 | **Freqtrade** | Bot de trading | **El destino.** Es donde se instalaría una estrategia que pase la puerta. Prohibido tocarlo mientras hay bots corriendo | ✅ **En uso.** No se modifica |
| 04 | **VectorBT** | Backtesting ultrarrápido | Reemplazaría mi motor vectorizado en Python puro. Permitiría barrer **miles** de combinaciones con métricas de riesgo (drawdown, Sharpe, Calmar) en segundos | ⭐ **Adoptar cuando toque.** Es la respuesta al último cuello de botella: hoy cada experimento cuesta minutos y una rejilla de 18 combinaciones ya es lenta |
| 05 | **Backtrader** | Backtesting | Alternativa más pesada y más lenta. Se solapa con VectorBT y con el motor de Freqtrade | ❌ **No.** Tres motores para lo mismo es deuda, no capacidad |
| 06 | **Hummingbot** | Market making / arbitraje | Otro negocio: ganar del *spread* y de la liquidez, no de la dirección. Requiere capital parado, latencia y comisiones de maker | ❌ **No.** Fuera del alcance |
| 07 | **CCXT** | Conexión a exchanges | Ya se usa **de facto**: el funding se trae del endpoint público de Binance (`C-18`) | ⚪ **No se adopta aún, y ya no hace falta.** Se amplió el universo a 24 pares (`E-13`) con `urllib` desde el mismo endpoint (`C-26`): una sola fuente y una sola temporalidad no justifican una dependencia. Sigue siendo la vía si algún día hace falta más de un exchange o más temporalidades |
| 08 | **FinRL** | Aprendizaje por refuerzo | Entrenar un agente para operar. Con 7 pares y 5 años de datos hay más parámetros que observaciones: es la receta del sobreajuste | ❌ **No.** Con este tamaño de datos no es serio |
| 09 | **NautilusTrader** | Plataforma algorítmica | Compite con Freqtrade. Migrar el bot no está en el alcance de este proyecto | ❌ **No.** |
| 10 | **Polymarket API** | Mercados de predicción | Otro mercado (eventos binarios). Aporta **probabilidades** ya agregadas sobre macro: recortes de tipos, recesión, elecciones. Sería una fuente de la capa lenta, con la ventaja de que es una probabilidad, no un indicador | 💡 **Interesante a medio plazo.** No para este paso |

## 2. Lo que sí mueve la aguja ahora

**Ahora mismo, ninguno.** La línea de señales está cerrada (`D-31`, `D-33`): no hay una
hipótesis esperando a que la prueben más rápido. Eso cambia el veredicto de la lista:

1. **VectorBT** — **en espera, no urgente.** Su argumento era «probar miles de
   hipótesis», y hoy no hay ninguna que probar. Entra el día que aparezca una señal
   medible que exija barrer una rejilla; antes de eso, solo añadiría una dependencia.
2. **CCXT** — **el disparador no se cumplió.** Decía que entraría si el momentum se
   llevaba a 20-30 pares; se llevó a 24 (`E-13`) y bastó con `urllib` sobre el
   endpoint público de Binance (`C-26`). Su disparador sigue siendo otro: **más de un
   exchange o más temporalidades**.

## 3. Lo que NO se adopta y por qué (para no repetir la pregunta)

- **Backtrader y NautilusTrader:** duplican lo que ya hay (Freqtrade para operar, mi motor para medir).
- **Hummingbot:** otro modelo de negocio.
- **FinRL:** el tamaño de datos no lo aguanta.
- **TradingAgents:** sin forma de medirlo, integrarlo sería creer, no saber.

## 4. Cómo se relaciona con lo ya decidido

- `D-12`: la base EMA 20/50 quedó descartada → el trabajo pasó a cambiar la **señal**.
- `D-13` + `P11`: el momentum tenía ventaja frente al azar pero un drawdown del 77-93 %.
  Se probó el control de riesgo, no el filtro de régimen: `E-16` midió el **efecto de la
  fase del rebalanceo** (42 fases, +95,8 % a +3.776 %) y `E-17` lo confirmó en
  walk-forward: 24 pares, Calmar mediano 3,56 frente a 4,52 de la cesta, 18/42 por
  encima. La «ventaja» era en buena parte un parámetro no declarado. **Rama cerrada**
  (`D-30`, `D-31`).
- `E-18` + `D-33`: el macro de OpenBB como **filtro de mercado** tampoco bate a la cesta
  (Calmar 4,21 vs 5,16; percentil 75; P(azar ≥) 25,2 %). OpenBB se queda como **panel
  de información**, no como fuente de señales.
- Consecuencia para esta lista: ninguna herramienta de aquí desbloquea nada mientras no
  haya una señal que medir. VectorBT sigue siendo la mejor candidata **si** vuelve a
  haber un cuello de botella de hipótesis; CCXT, si se amplía a más exchanges.
