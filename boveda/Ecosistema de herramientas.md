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
| 07 | **CCXT** | Conexión a exchanges | Ya se usa **de facto**: el funding se trae del endpoint público de Binance (`C-18`). Serviría si hicieran falta más exchanges o más datos de derivados | 🟡 **Parcialmente cubierto.** Si el momentum se lleva a más pares, es la vía natural |
| 08 | **FinRL** | Aprendizaje por refuerzo | Entrenar un agente para operar. Con 7 pares y 5 años de datos hay más parámetros que observaciones: es la receta del sobreajuste | ❌ **No.** Con este tamaño de datos no es serio |
| 09 | **NautilusTrader** | Plataforma algorítmica | Compite con Freqtrade. Migrar el bot no está en el alcance de este proyecto | ❌ **No.** |
| 10 | **Polymarket API** | Mercados de predicción | Otro mercado (eventos binarios). Aporta **probabilidades** ya agregadas sobre macro: recortes de tipos, recesión, elecciones. Sería una fuente de la capa lenta, con la ventaja de que es una probabilidad, no un indicador | 💡 **Interesante a medio plazo.** No para este paso |

## 2. Lo que sí mueve la aguja ahora

Solo dos cosas de esta lista cambian el trabajo de las próximas semanas, y en este orden:

1. **VectorBT** — porque el proyecto ya demostró que su cuello de botella es *cuántas
   hipótesis se pueden probar con rigor*. Mi motor hace 18 combinaciones con esfuerzo;
   VectorBT hace miles y además ya trae drawdown, Sharpe y Calmar, que es justo lo que
   `E-10` deja pendiente.
2. **CCXT** — si el momentum transversal se lleva a 20-30 pares en vez de 7, la selección
   entre activos mejora por construcción y se puede hacer la prueba de permutación con
   más potencia.

## 3. Lo que NO se adopta y por qué (para no repetir la pregunta)

- **Backtrader y NautilusTrader:** duplican lo que ya hay (Freqtrade para operar, mi motor para medir).
- **Hummingbot:** otro modelo de negocio.
- **FinRL:** el tamaño de datos no lo aguanta.
- **TradingAgents:** sin forma de medirlo, integrarlo sería creer, no saber.

## 4. Cómo se relaciona con lo ya decidido

- `D-12`: la base EMA 20/50 quedó descartada → el trabajo es cambiar la **señal**, y
  la señal nueva es momentum transversal (`D-13`).
- `D-13` + `P11`: el momentum tiene ventaja estadística frente al azar pero un drawdown
  del 77-93 %. El siguiente experimento es **control de riesgo** (filtro de régimen,
  volatilidad objetivo), y ahí es donde la capa lenta de OpenBB por fin tiene un papel
  real: no elegir entradas, sino **decidir cuánto capital está expuesto**.
