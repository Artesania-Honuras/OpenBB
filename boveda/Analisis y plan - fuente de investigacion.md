# Análisis y plan — De panel técnico a fuente de investigación para inversores

> **Documento de análisis y planificación. No implementa nada: no hay cambios de código.**
> Fecha: 2026-10-20 · Sesión S-29
> Estado: **propuesta registrada, pendiente de aprobación**.
> Entrada: petición del usuario (2026-10-20), transcripción del video y cuatro referencias.
> **Actualización (2026-10-20):** respuestas del usuario en **§24** — Inversor/Analista, Claude vía MCP, múltiples fuentes.

---

## 0. Resumen ejecutivo

1. La app actual es un **buen panel de instrumentos para un quant**, no una **fuente de investigación para un inversor**. Sabe medir; no sabe contar qué significa ni qué hacer con ello.
2. El video no pide copiar el **Terminal clásico** (más técnico todavía): pide copiar su **secuencia** (`load` → `candle` → `ca` → `fa` → `cash`) y quitarle la sintaxis.
3. Las cuatro referencias cubren cuatro piezas distintas: **amplitud** (FinanceDatabase), **profundidad** (FinanceToolkit), **recorrido** (video/Terminal) y **conversación** (openbb-ai / agents-for-openbb). Hoy solo tenemos profundidad macro.
4. El cuello de botella no es "más datos": es **contexto persistente** (un activo cargado, un periodo, un benchmark) y una **capa de lenguaje llano**. Sin eso, la ficha, el comparador y el agente no tienen sujeto.
5. Plan en **4 fases** (~3–4 meses): contexto → hablar claro → descubrir → conversar. Cada fase tiene criterios de aceptación verificables y no se abre la siguiente sin pasar la anterior.

---

# PARTE I — REGISTRO DEL ANÁLISIS

## 1. Punto de partida

Instalación **local** de OpenBB Platform desde el código fuente, con:

| Pieza | Estado verificado |
|---|---|
| API | `127.0.0.1:6900`, 869 rutas OpenAPI |
| Panel | `127.0.0.1:8501`, Streamlit, 9 pestañas en español |
| Contexto | `data/context/contexto_diario.parquet`, **36.637 filas × 14 columnas** |
| Historia | CPI desde **1956-02-15**, sin NaN en 2026 |
| Refresco | tarea diaria **09:05**, validada, con aviso externo por Telegram |
| Salud | `estado.py` **27/27** |
| Repo | HEAD `6c9b025` al inicio del análisis; limpio y pusheado |

**Lo que ya funciona y no se debe perder:** datos validados, sin look-ahead, con historia, escritura atómica, archivo anterior conservado, panel que avisa y alerta externa cuando algo se rompe.

**La queja del usuario:** los datos son técnicos, no amigables; hay mucha información y no está pensada para quien busca datos para **tomar decisiones**.

**La petición:** que sea una **fuente de investigación financiera** que cualquier usuario pueda usar y que sea **interactiva con un agente de IA**.

---

## 2. Fuentes consultadas

| Fuente | Enlace | Qué se extrajo |
|---|---|---|
| Video | <https://www.youtube.com/watch?v=NeZjsadeEVs> | Tutorial del **OpenBB Terminal clásico**: comandos, `load`, gráficos, comparación, valoración, flujos, economía, claves de API |
| FinanceDatabase | <https://github.com/JerBouma/FinanceDatabase> | Catálogo libre de **302.991 símbolos**, 7 clases de activo, filtros por sector/industria/país/market cap, MCP |
| FinanceToolkit | <https://www.jeroenbouma.com/projects/financetoolkit> | Motor de análisis: **500+ métricas**, 80+ ratios, estados financieros, DCF, VaR, Sharpe, cartera, MCP |
| openbb-ai | <https://github.com/OpenBB-finance/openbb-ai> | **SDK** de agentes para OpenBB Workspace: SSE, widgets, citas, tablas, gráficos, pasos de razonamiento |
| agents-for-openbb | <https://github.com/OpenBB-finance/agents-for-openbb> | **Agentes de ejemplo**: prompt, widgets, citas, gráficos, tablas, PDF, herramientas MCP; Agent Rita como referencia de producción |

Referencias secundarias citadas por las anteriores:

- FinanceToolkit (repo): <https://github.com/JerBouma/FinanceToolkit>
- FinanceDatabase (docs): <https://www.jeroenbouma.com/projects/financedatabase>
- FinanceDatabase MCP: <https://www.jeroenbouma.com/projects/financedatabase/mcp>
- FinanceToolkit MCP: <https://www.jeroenbouma.com/projects/financetoolkit/mcp>
- Agent Rita: <https://github.com/OpenBB-finance/agent-rita>
- MCP (protocolo): <https://modelcontextprotocol.io>

> **Nota sobre el video:** la transcripción tiene errores de reconocimiento de voz. Se interpretan por contexto: "open vivir" = OpenBB, "candel" = `candle`, "sea" = `ca`, "un valuación" = valoración/`fa`, "bachar" = Barchart, "akinsola shafiq" = API keys. No se corrige la transcripción; se interpreta.

---

## 3. Qué dice el video (análisis de la transcripción)

### 3.1. Qué enseña

1. **El dolor:** "hay tanta información que al final tienes 200 navegadores abiertos". Lo que vende es **centralización y velocidad**: un sitio, un comando, el dato.
2. **El flujo:** `stock` → `load TICKER` → `candle` → `ca` (comparar) → `fa` (valoración) → `cash` (flujos) → `economy` → opciones. Cada paso **habilita el siguiente**.
3. **La amplitud:** acciones, cripto, economía, derivados, cartera, informes, automatización. "Infinitas posibilidades".
4. **La fuente a la vista:** al comparar aparecen FMP, Polygon y Yahoo Finance. El dato lleva proveedor.
5. **El requisito oculto:** el terminal **asume que sabes el ticker y el comando**. El autor es técnico; su usuario también. Ahí está la brecha con "cualquier usuario".

### 3.2. Las seis lecciones transferibles

| # | Lección | Qué significa para nuestra app |
|---|---|---|
| 1 | Todo en un sitio | Ya lo tenemos; hay que **hacerlo visible** en los primeros 10 segundos |
| 2 | `load` crea un contexto | Falta una **barra de contexto** (activo · periodo · benchmark) que todas las tarjetas usen |
| 3 | Divulgación progresiva | Sustituir 9 pestañas planas por **Mira → Entiende → Compara** |
| 4 | Comandos rápidos | Un **buscador único** y, para el resto, lenguaje natural |
| 5 | Fuentes junto al dato | **Sello uniforme**: fuente · as-of · retraso |
| 6 | Amplitud | Añadir **acciones/ETF**; opciones y cartera después |

### 3.3. Los límites del video

- **Es el Terminal clásico**, no el panel actual ni el OpenBB moderno. OpenBB migró a Workspace y agentes; construir sobre la consola sería ir contra la corriente.
- **Asume conocimiento:** ticker, comando y submenú. Un principiante no sabe que existe `load`.
- **No explica:** no hay "qué significa", ni "es bueno o malo", ni "qué riesgo corro".
- **"Infinitas posibilidades" es el problema, no la solución:** sin curaduría, el usuario se paraliza.

---

## 4. Qué aporta cada referencia

| Referencia | Qué es | Qué resuelve | Qué NO resuelve | Coste / dependencia |
|---|---|---|---|---|
| **FinanceDatabase** | Catálogo libre de 302.991 símbolos (acciones, ETF, índices, divisas, cripto), con sector, industria, país, mercado y market cap. CSV, actualización semanal, sin clave. MCP propio. | El **"qué existe"**: buscar, filtrar y descubrir instrumentos. | No da fundamentales ni precios actualizados; es un catálogo. | Gratis. Local o MCP alojado. |
| **FinanceToolkit** | Motor de análisis: 500+ métricas, 80+ ratios, estados financieros, DCF, WACC, Altman, VaR, Sharpe, técnicos, opciones, cartera, economía. Fórmulas transparentes. MCP propio. | El **"cómo está"**: valorar, comparar, medir riesgo y rentabilidad. | Necesita **clave de FMP** para estados financieros (free: 250 peticiones/día, 5 años, solo EE. UU.; fallback a Yahoo). | Clave y límites. Es la dependencia más delicada. |
| **openbb-ai** | **SDK** para agentes dentro de **OpenBB Workspace**: streaming SSE, `agents.json`, widgets, citas, tablas, gráficos, pasos de razonamiento. | El **"cómo conversar"**: respuestas con evidencia y artefactos. | No es un modelo ni una app: es el protocolo. Necesita Workspace y un backend de LLM. | SDK gratis; Workspace y LLM aparte. |
| **agents-for-openbb** | Repositorio de **agentes de ejemplo** (prompt, widgets, citas, gráficos, tablas, PDF, MCP). Agent Rita como referencia de producción. | El **"cómo se monta"**: patrones copiables. | Son ejemplos, no un producto; hay que adaptarlos. | Gratis; mismo requisito de Workspace/LLM. |
| **Video / Terminal** | Tutorial del Terminal clásico de comandos. | El **"cómo se recorre"**: secuencia, velocidad, amplitud. | No es una referencia de usabilidad para principiantes. | Gratis; UI legacy. |

### 4.1. El marco de las cuatro piezas

| Pieza | Referencia | En una palabra |
|---|---|---|
| **Amplitud** | FinanceDatabase | Qué existe |
| **Profundidad** | FinanceToolkit | Cómo está |
| **Recorrido** | Video / Terminal | Cómo se navega |
| **Conversación** | openbb-ai / agents | Cómo se explica |

Hoy tenemos **profundidad macro** y algo de recorrido. Faltan amplitud y conversación.

---

## 5. Diagnóstico de la app actual

**En una frase:** es un **panel de instrumentos para un quant**; para ser una **fuente de investigación para un inversor** le falta traducir, descubrir y conversar.

### 5.1. Tres síntomas

1. **Vocabulario de laboratorio:** `slope_10y_2y`, `cot_net`, `ff_smb`, `funding_btc_anual`. Sin traducción, el usuario no sabe si eso es bueno, malo o irrelevante.
2. **Todo es serie y cifra, nada es decisión:** no hay portada que diga "el entorno está en tal régimen, esto vigilo, esto cambió".
3. **No hay universo de activos:** solo macro y funding de BTC. Un inversor que busca "qué comprar" o "cómo está Apple" no encuentra nada.

### 5.2. Lo que sí funciona y hay que conservar

- Validación estricta del refresco (filas, fechas, NaN nuevos, rangos, historia del CPI).
- Sin look-ahead: retrasos de publicación declarados (1/3/45/31 días).
- Historia larga y archivo anterior conservado; escritura atómica.
- Panel que muestra la salud y alerta externa cuando algo se rompe.
- Registro y trazabilidad en la bóveda.

---

## 6. La brecha, pregunta a pregunta

| Lo que pregunta un inversor | ¿Lo responde hoy? | Por qué no |
|---|---|---|
| ¿Cómo está el mercado? | ❌ | Hay 9 pestañas, pero ninguna sintetiza. |
| ¿Qué puedo mirar/comprar? | ❌ | No hay buscador ni universo de activos. |
| ¿Está caro X? | ❌ | No hay fundamentales ni valoración. |
| ¿Qué riesgo corro? | ⚠️ | Hay VIX y drawdown, pero en % técnico, no en dinero ni escenarios. |
| ¿Qué cambió desde ayer? | ❌ | No hay diff ni narrativa diaria. |
| ¿Por qué pasó? | ❌ | Hay series, no explicaciones. |
| ¿Y si...? | ❌ | No hay escenarios ni simulación. |
| ¿Puedo confiar en este dato? | ⚠️ | La fuente está en algunas tarjetas, no en todas, y no siempre con retraso declarado. |

---

## 7. Cuadro de mejoras (18 palancas)

**Esfuerzo:** S ≤ 3 días · M 1–2 semanas · L 3–6 semanas (una persona, con agente).
**Prioridad:** P1 = hace usable la app · P2 = la hace útil · P3 = la completa.

| # | Bloque | Hoy | Propuesta concreta | Referencia | Impacto | Esf. | P |
|---|---|---|---|---|---|---|---|
| 1 | Lenguaje | 9 pestañas sin jerarquía | **Portada "3 respuestas"**: régimen, riesgo y qué cambió; 3 cifras grandes y un semáforo | Propia | Alto | S | **P1** |
| 2 | Lenguaje | `slope_10y_2y` sin explicar | **Glosario y tooltip** en cada tarjeta: qué es, cómo se lee, qué NO significa | FinanceToolkit (fórmulas transparentes) | Alto | S | **P1** |
| 3 | Lenguaje | Solo el valor de hoy | **"Qué cambió desde ayer"**: flechas, delta y una frase por serie | Propia + rolling de FT | Alto | S | **P1** |
| 4 | Lenguaje | Cifras absolutas | **Percentil vs 5 años**: "VIX en percentil 72 → miedo alto pero no extremo" | FinanceToolkit (`standardize`) | Alto | S | **P1** |
| 5 | Lenguaje | Un solo nivel de densidad | **3 modos**: Principiante / Inversor / Analista (mismos datos, distinto detalle) | Propia | Alto | M | **P1** |
| 6 | Descubrir | No hay buscador | **Buscador de 300k símbolos** con filtros sector, industria, país, market cap | FinanceDatabase | Muy alto | M | **P1** |
| 7 | Descubrir | No hay ficha | **Ficha de activo**: precio, retorno, volatilidad, drawdown, ratios, comparación con benchmark y contexto macro | FinanceDatabase + FinanceToolkit | Muy alto | L | **P2** |
| 8 | Descubrir | No hay screening | **Screener**: "semiconductores de Taiwán, mid cap, con dividendo" + ranking + exportar | FinanceToolkit Discovery | Alto | M | **P2** |
| 9 | Descubrir | No hay comparación | **Comparador 2–5 activos** vs benchmark: retorno, riesgo, correlación | FinanceToolkit | Alto | M | **P2** |
| 10 | Analizar | No hay cartera | **Cartera**: importar CSV/XLSX, PnL, pesos, VaR, benchmark | FinanceToolkit Portfolio | Alto | L | **P3** |
| 11 | Analizar | Riesgo en % | **Riesgo en dinero y escenarios**: "con 1.000 €, el 5% peor de los días perderías X €" | FinanceToolkit VaR | Alto | M | **P2** |
| 12 | Analizar | No se puede sacar | **Informe PDF/CSV** de la vista, con fuente, fecha y "no es asesoramiento" | FT / Workspace | Medio | M | **P2** |
| 13 | Conversar | No hay chat | **Agente anclado a los datos**: responde en español, cita la serie y la fecha, devuelve tabla/gráfico | openbb-ai + agents-for-openbb | Muy alto | L | **P1/P2** |
| 14 | Conversar | Nada que preguntar | **"Explícame esto"** en cada tarjeta: abre el chat con el contexto ya cargado | openbb-ai (contexto) | Alto | M | **P2** |
| 15 | Confianza | Fuente dispersa | **Sello uniforme** en cada dato: fuente · fecha del dato · retraso · "as-of" | OpenBB + FT | Alto | S | **P1** |
| 16 | Confianza | Límites implícitos | **Aviso legal y límites** visibles: información, no asesoramiento; datos pueden retrasarse | — | Alto | S | **P1** |
| 17 | Producto | Guía larga | **Onboarding de 3 pasos** con un ejemplo real ("mira el VIX de hoy") | FT notebooks | Medio | S | **P1** |
| 18 | Producto | Solo escritorio | **Responsive + accesibilidad** (contraste, teclado, móvil) | — | Medio | M | **P3** |

---

## 8. Qué copiar y qué no copiar del video

| Elemento del video | Por qué funciona | Traducción a nuestra app | Qué evitar |
|---|---|---|---|
| `load TICKER` antes de preguntar | Crea un **contexto de trabajo**; todo lo demás se refiere a él | **Barra de contexto persistente**: activo, periodo, benchmark | Obligar a escribir el ticker a mano |
| `stock` → submenú → `candle` | **Divulgación progresiva**: solo muestra lo posible | **Mira → Entiende → Compara** | 9 pestañas planas con todo a la vez |
| Comandos de 2–4 letras | Velocidad para el experto | **Buscador único (Ctrl+K)** + lenguaje natural | Enseñar 40 comandos al principiante |
| `ca`, `fa`, `cash` | Comparar y valorar en el mismo sitio | Comparador + ficha + estados financieros | Números sin explicación |
| Fuentes junto al dato | Confianza y trazabilidad | **Sello fuente · fecha · retraso** | Fuente solo en un pie de página |
| "Infinitas posibilidades" | Potencia real | **Curaduría**: 3 preguntas, 3 respuestas | Un menú infinito sin opinión |
| Terminal de escritorio | Cero fricción de instalación | Ya lo tenemos: panel local | Depender de una UI obsoleta |

---

## 9. El agente de IA

### 9.1. Precisión técnica

`openbb-ai` **no se enchufa a nuestro Streamlit**: es el SDK para agentes que viven dentro de **OpenBB Workspace**. Nuestro panel es propio. Hay dos caminos:

- **A. Chat dentro del panel** (Streamlit `chat_message` + herramientas sobre el parquet y la API). Reutilizamos las *ideas* de `openbb-ai` (streaming, citas, tablas), no el SDK.
- **B. Workspace + agente** con `openbb-ai`: más potente y "nativo", pero implica otra interfaz y otra cuenta.

Para el objetivo ("que cualquier usuario la pueda usar"), el camino A es el que encaja con lo que ya hay.

### 9.2. Opciones de modelo

| Enfoque | Corre en | Clave | Privacidad | Calidad | Coste | Veredicto |
|---|---|---|---|---|---|---|
| **Ollama local** (Qwen 7–14B / Llama 8B) | Tu PC | No | Total | Media | 0 € | **Recomendado para empezar**; cumple "todo local" |
| **API cloud** (OpenAI/Anthropic) | Nube | Sí | Los datos salen | Alta | Por uso | Opcional, declarado |
| **Workspace + `openbb-ai`** | Workspace + backend | Cuenta | Según plan | Alta | Según plan | Si se quiere la UI de OpenBB |
| **MCP** (FinanceDatabase / FinanceToolkit / nuestra API) | Tu PC | No | Total | n/a (herramientas) | 0 € | **Sí**: conecta cualquier agente sin acoplarnos |

### 9.3. Diseño del agente

**Herramientas (6), nada de texto libre con números:**

1. `contexto_ultimo()` — última fila del contexto.
2. `serie(nombre, desde)` — serie histórica.
3. `percentil(nombre, años)` — posición vs historia.
4. `buscar_activo(q)` — catálogo (FinanceDatabase).
5. `ficha(simbolo)` — métricas del activo (FinanceToolkit o Yahoo).
6. `comparar(a, b, benchmark)` — retorno, riesgo, correlación.

**Estado:** activo, periodo y benchmark. Es el `load` del video, pero compartido entre panel y agente.

**Grounding obligatorio:** cada cifra sale de una herramienta; cada respuesta lleva **fuente + as-of**. Si no está en los datos, "no lo sé".

**Guardarraíles:**

- No comprar/vender, no predecir, no inventar.
- "Esto es información, no asesoramiento" visible.
- Respetar los retrasos de publicación (nada de mirar el CPI de mañana).
- Mostrar el rastro: "he consultado el contexto, el funding y el VIX".

**Interactividad real:** el agente no solo responde; **cambia el panel**. "Cárgame Energy Fuels y compárala con el sector desde 2022" fija el contexto y redibuja las tarjetas. Es el `load` + `ca` del video, en una frase.

**Ejemplo de flujo:**

```
Usuario:  "cárgame Energy Fuels y compárala con el sector desde 2022"

Agente:
  1. buscar_activo("Energy Fuels")        → UUUU
  2. cargar_activo("UUUU", desde=2022)    → fija el contexto
  3. comparar("UUUU", ["CCJ","UEC"], benchmark="SPY")
  4. mostrar tabla + gráfico + 3 conclusiones
  5. citar fuente y fecha: "Yahoo/FMP · datos al 2026-10-20"
```

### 9.4. Evaluación (antes de publicar)

- **20 preguntas de oro** con cifra esperada, cita y veredicto.
- Métricas: acierto de cifra ≥ 90 %, citas 100 %, consejos 0, latencia p95 < 20 s (local).
- Casos límite: activo sin datos, periodo vacío, serie con retraso, pregunta fuera de alcance.
- Si no pasa, no se publica.

---

## 10. Riesgos y límites

| Riesgo | Qué puede pasar | Mitigación |
|---|---|---|
| **Alucinación** | El LLM inventa una cifra | Solo herramientas; cero números de memoria; cita obligatoria |
| **Consejo financiero** | El agente dice "compra" | Guardarraíl explícito; "información, no asesoramiento"; revisión de prompts |
| **Look-ahead** | El agente usa datos no publicados | Mismos retrasos del contexto; el as-of viaja con cada dato |
| **Licencias** | FMP/Yahoo no permiten redistribuir | Uso personal; no exponer datos crudos; declarar fuente |
| **Claves** | FMP/Cloud LLM | Fuera del repo; `.env` o `data/` ignorado; declarar dependencia |
| **Scope creep** | 300k símbolos sin curar | Empezar por un subconjunto; medir calidad antes de ampliar |
| **UI legacy** | Copiar el Terminal | Copiar el flujo, no la consola |
| **Coste** | Cloud LLM por uso | Local por defecto; cloud opt-in |
| **Mantenimiento** | Más fuentes, más roturas | Validación y alertas desde el primer día; una fuente, un test |

### 10.1. Lo que NO se hará

- Convertirlo en un **servicio de señales**. La línea está cerrada con evidencia (`E-16`, `E-17`, `E-18`).
- Meter **300k símbolos sin curar**.
- Depender de una **clave paga** para lo básico.
- Dejar que el LLM **escriba cifras de memoria**.
- Ocultar la **fecha o el retraso**.
- Mezclar **investigación** con **consejo**.

---

## 11. Decisiones propuestas (pendientes de aprobación)

> No son decisiones tomadas. Se registran para que la aprobación sea explícita.

| ID | Propuesta | Estado |
|---|---|---|
| **P19** | Rediseño de producto en 4 fases (contexto, lenguaje, descubrimiento, agente) | **Propuesta, no aprobada** |
| **D-37** (propuesta) | El agente **explica y compara**, no recomienda; toda cifra lleva fuente y as-of | Pendiente |
| **D-38** (propuesta) | **Local-first**: Ollama por defecto; cloud solo opt-in y declarado | Pendiente |
| **D-39** (propuesta) | El **contexto persistente** (activo · periodo · benchmark) es requisito de la ficha, el comparador y el agente | Pendiente |
| **D-40** (propuesta) | La **amplitud** entra por FinanceDatabase; la **profundidad** por FinanceToolkit, con FMP opcional | Pendiente |

---

# PARTE II — PLAN COMPLETO

## 12. Principios de diseño

1. **Una pregunta, una respuesta.** La portada responde tres preguntas; el resto es detalle.
2. **El dato habla con fecha y fuente.** Sin as-of no se muestra.
3. **Progresivo:** Mira → Entiende → Compara. Nunca todo a la vez.
4. **Local-first:** funciona sin nube y sin claves; lo que necesite clave, se declara.
5. **El agente no sustituye al panel:** lo maneja y lo explica.
6. **Nada de consejos:** información, evidencia y límites.

---

## 13. Fase 0 — Contexto (1 semana)

**Objetivo:** que el panel sepa **de qué está hablando**.

### Alcance

- Barra de contexto persistente: **activo · periodo · benchmark**.
- **Sello** fuente · as-of · retraso en cada tarjeta.
- **Gráfico por tarjeta** con selector de periodo y benchmark.
- Estado vacío claro cuando no hay activo o no hay datos.

**Fuera:** nuevos proveedores, fundamentales, chat.

### Cambios visibles

- Cabecera del panel: `Activo: UUUU · Periodo: 2022→hoy · Benchmark: SPY` con botón "cambiar".
- Cada tarjeta: una línea inferior `Fuente: CBOE · dato al 2026-10-20 · retraso 1 d`.
- Cada serie: botón "ver gráfico" que abre el gráfico con el periodo activo.

### Datos que necesita

- El parquet actual y la API local. **Nada nuevo.**

### Tareas

1. Definir el objeto de contexto (activo, periodo, benchmark) y su persistencia en `session_state`.
2. Pintar la barra y conectarla a todas las tarjetas.
3. Añadir el sello fuente/as-of/retraso a cada tarjeta.
4. Añadir el gráfico por tarjeta con periodo y benchmark.
5. Estados vacíos y errores.
6. Pruebas de interfaz (AppTest) y de coherencia.

### Criterios de aceptación

- [ ] Al cambiar de activo, **el 100 %** de las tarjetas se actualiza; ninguna conserva el anterior.
- [ ] **Ninguna** tarjeta se muestra sin fuente y fecha.
- [ ] Activo sin datos → mensaje claro, sin excepción.
- [ ] Gráfico con datos locales en **< 2 s**.
- [ ] AppTest: **0 excepciones**; 6 casos (con activo, sin activo, periodo vacío, benchmark inválido, activo sin datos, cambio de activo).
- [ ] El panel sigue mostrando el estado del refresco y la alerta.

### Esfuerzo y riesgo

- **1 semana.** Riesgo bajo: no hay datos nuevos.
- **Reversión:** quitar la barra y el sello; el panel vuelve a las tarjetas actuales.

---

## 14. Fase 1 — Hablar claro (2–3 semanas)

**Objetivo:** que una persona no técnica entienda el panel **sin manual**.

### Alcance

- **Portada "3 respuestas"**: cómo está el entorno, qué es lo relevante, qué cambió.
- **Semáforo** por régimen (favorable / neutro / tenso) con criterio explícito.
- **Glosario y tooltips** (20 términos).
- **"Qué cambió desde ayer"**: delta y una frase por serie.
- **Percentil vs 5 años** para VIX, funding, pendiente y CPI.
- **3 modos**: Principiante / Inversor / Analista.
- **Onboarding de 3 pasos** con un ejemplo real.
- **Aviso legal y límites** visible.

**Fuera:** activos, fundamentales, chat.

### Cambios visibles

- Nueva primera pantalla: 3 tarjetas grandes + semáforo + "lo que vigilo".
- Cada tarjeta técnica con un botón "¿qué es esto?".
- Selector de modo en la cabecera.
- Pie: "Información, no asesoramiento. Datos con retraso de publicación."

### Datos que necesita

- El parquet actual. Percentiles y deltas se calculan en local.

### Tareas

1. Definir el criterio del semáforo (reglas explícitas, no caja negra).
2. Redactar los 3 textos de la portada y el glosario.
3. Implementar deltas y percentiles con pruebas contra cálculo manual.
4. Implementar los 3 modos (mismos datos, distinto detalle).
5. Onboarding y aviso legal.
6. Prueba con una persona no técnica.

### Criterios de aceptación

- [ ] Una persona no técnica responde **3/3** preguntas (entorno, riesgo, qué cambió) en **< 60 s**.
- [ ] **0** términos técnicos visibles sin tooltip en modo Principiante.
- [ ] El delta de cada serie coincide con el cálculo manual (test).
- [ ] El percentil coincide con el cálculo en Python (test, 5 series).
- [ ] El aviso legal es visible sin abrir un modal.
- [ ] AppTest: 0 excepciones; 3 modos conmutan sin perder el contexto.

### Esfuerzo y riesgo

- **2–3 semanas.** Riesgo: que el semáforo sea arbitrario → criterio escrito y test.
- **Reversión:** la portada es una vista más; se puede volver a la pestaña Resumen.

---

## 15. Fase 2 — Descubrir (4–6 semanas)

**Objetivo:** que el usuario encuentre un activo y lo entienda.

### Alcance

- **FinanceDatabase** local (CSV, caché semanal, sin clave).
- **Buscador** con filtros: sector, industria, país, market cap, clase.
- **Screener** con ranking y exportación.
- **Ficha de activo**: precio, retorno, volatilidad, drawdown, 10 métricas, comparación con benchmark y contexto macro.
- **Comparador** 2–5 activos vs benchmark.
- **Informe PDF/CSV** con fuente y fecha.
- **Fundamentales opcionales** con FinanceToolkit + FMP (clave fuera del repo; fallback Yahoo).

**Fuera:** cartera, opciones, alertas por activo.

### Cambios visibles

- Nueva pestaña **"Buscar"** (o buscador global Ctrl+K).
- Ficha con cabecera de contexto y sello de fuente.
- Comparador con tabla y gráfico.
- Botón "Exportar informe".

### Datos que necesita

- FinanceDatabase (paquete + CSV; ~302.991 símbolos; actualización semanal).
- FinanceToolkit (opcional) + FMP (opcional).
- Precios: Yahoo/OpenBB según disponibilidad.

### Tareas

1. Instalar y cachear FinanceDatabase; medir tamaño y tiempo de carga.
2. Implementar búsqueda y filtros; medir 10 consultas.
3. Implementar screener y ranking.
4. Implementar ficha (10 métricas) y comparador.
5. Implementar exportación PDF/CSV.
6. Integrar fundamentales opcionales con degradación elegante si no hay clave.
7. Pruebas de datos: símbolos duplicados, delisted, monedas, zonas horarias.

### Criterios de aceptación

- [ ] 10 consultas de ejemplo devuelven ≥ 1 resultado correcto.
- [ ] La ficha muestra **10 métricas** con fuente y fecha.
- [ ] El comparador acepta **3 activos + benchmark** y calcula retorno, vol y correlación.
- [ ] El informe se abre y contiene fuente, fecha y aviso legal.
- [ ] **Sin clave FMP**: la búsqueda y la ficha funcionan; los fundamentales muestran "no disponible", sin romper.
- [ ] Con clave FMP: los estados financieros cargan dentro de los límites del plan free.
- [ ] AppTest: 0 excepciones; 8 casos límite.

### Esfuerzo y riesgo

- **4–6 semanas.** Riesgo: calidad y licencias de datos; límites de FMP; mapeo de tickers.
- **Reversión:** la pestaña Buscar es aditiva; se oculta sin afectar al resto.

---

## 16. Fase 3 — Conversar (4–6 semanas)

**Objetivo:** que el usuario pregunte en español y el agente responda **con sus datos**, citando fuente y fecha, y **mueva el panel**.

### Alcance

- **Agente local** (Ollama + Qwen/Llama) con las 6 herramientas.
- **Chat en el panel** con streaming, citas, tablas y gráficos.
- **"Explícame esto"** en cada tarjeta.
- **Evaluación** con 20 preguntas de oro.
- **Opcional:** cloud LLM (declarado) y cartera.

**Fuera:** consejos, predicciones, ejecución de órdenes.

### Cambios visibles

- Panel lateral de chat.
- Cada respuesta con "Fuente: … · dato al …".
- El agente puede fijar el contexto y redibujar las tarjetas.
- Botón "¿qué puedo preguntar?" con 5 ejemplos.

### Datos que necesita

- Ollama + modelo (4–8 GB).
- Las herramientas sobre el parquet y la API.
- FinanceDatabase/FinanceToolkit si se activan.

### Tareas

1. Definir las 6 herramientas y sus contratos.
2. Implementar el estado compartido panel ↔ agente.
3. Implementar el chat con streaming y citas.
4. Implementar "Explícame esto".
5. Redactar el system prompt con guardarraíles.
6. Construir las 20 preguntas de oro y el arnés de evaluación.
7. Medir latencia y acierto; ajustar.
8. Documentar límites y modo degradado (sin modelo, sin clave).

### Criterios de aceptación

- [ ] **≥ 18/20** preguntas de oro con cifra exacta.
- [ ] **20/20** respuestas con fuente y as-of.
- [ ] **0** respuestas con consejo de compra/venta.
- [ ] p95 de latencia **< 20 s** en el equipo de referencia.
- [ ] Funciona **sin conexión** (solo datos locales).
- [ ] Sin modelo instalado: el chat se desactiva con un mensaje claro; el panel sigue funcionando.
- [ ] AppTest: 0 excepciones; 10 casos (sin datos, fuera de alcance, activo inexistente, etc.).

### Esfuerzo y riesgo

- **4–6 semanas.** Riesgo: alucinación, latencia, hardware; mitigado con herramientas y evaluación.
- **Reversión:** el chat es un panel lateral; se oculta y el panel vuelve a Fase 2.

---

## 17. Backlog priorizado

| ID | Tarea | Fase | Esf. | Dependencia | Criterio de aceptación |
|---|---|---|---|---|---|
| F0-1 | Barra de contexto | 0 | M | — | Cambia el 100 % de las tarjetas |
| F0-2 | Sello fuente/as-of | 0 | S | — | 0 tarjetas sin sello |
| F0-3 | Gráfico por tarjeta | 0 | S | — | < 2 s con datos locales |
| F1-1 | Portada 3 respuestas | 1 | S | F0 | 3/3 en < 60 s |
| F1-2 | Glosario/tooltips | 1 | S | — | 0 jerga sin explicar |
| F1-3 | Qué cambió desde ayer | 1 | S | F0 | Delta coincide con cálculo |
| F1-4 | Percentiles 5 años | 1 | S | F0 | Coincide con Python |
| F1-5 | 3 modos | 1 | M | F1-1 | Conmutan sin perder contexto |
| F1-6 | Onboarding | 1 | S | F1-1 | 3 pasos, ejemplo real |
| F1-7 | Aviso legal | 1 | S | — | Visible sin modal |
| F2-1 | FinanceDatabase | 2 | M | — | 10 consultas OK |
| F2-2 | Buscador | 2 | M | F2-1 | Filtros combinados |
| F2-3 | Screener | 2 | M | F2-1 | Ranking + export |
| F2-4 | Ficha | 2 | L | F2-1 | 10 métricas con fuente |
| F2-5 | Comparador | 2 | M | F2-4 | 3 activos + benchmark |
| F2-6 | Informe PDF/CSV | 2 | M | F2-4 | Fuente, fecha, aviso |
| F2-7 | Fundamentales (opcional) | 2 | M | FMP | Degrada sin clave |
| F3-1 | Herramientas del agente | 3 | M | F0 | 6 contratos testeados |
| F3-2 | Chat con citas | 3 | L | F3-1 | 20/20 citas |
| F3-3 | "Explícame esto" | 3 | M | F3-2 | Abre con contexto |
| F3-4 | Evaluación 20 preguntas | 3 | M | F3-2 | ≥ 18/20 |
| F3-5 | Cloud opt-in | 3 | M | F3-2 | Declarado y apagado por defecto |
| F3-6 | Cartera | 3 | L | F2-4 | Importa y calcula PnL |

---

## 18. Roadmap y puertas

| Fase | Duración | Puerta de salida |
|---|---|---|
| **0. Contexto** | 1 semana | Todas las tarjetas comparten contexto y sello; AppTest 0 |
| **1. Hablar claro** | 2–3 semanas | 3/3 preguntas en < 60 s; 0 jerga sin tooltip |
| **2. Descubrir** | 4–6 semanas | Buscar, ficha y comparar funcionan; sin clave no rompe |
| **3. Conversar** | 4–6 semanas | ≥ 18/20, 20/20 citas, 0 consejos, offline |

**Total:** ~3–4 meses. **No se abre una fase sin pasar la puerta anterior.**

---

## 19. Métricas de éxito

| Métrica | Objetivo |
|---|---|
| Tiempo hasta la primera respuesta útil | < 60 s |
| Sesiones que encuentran un activo | > 60 % |
| Preguntas de oro con cifra exacta | ≥ 90 % |
| Respuestas con fuente y as-of | 100 % |
| Respuestas con consejo | 0 |
| Refresco validado | 27/27, 0 NaN nuevos |
| Historia del CPI | intacta (desde 1956) |
| Caídas del panel por cambio | 0 |

---

## 20. Dependencias y costes

| Dependencia | Coste | Riesgo | Decisión |
|---|---|---|---|
| FinanceDatabase | 0 € | Bajo | **Sí** (local) |
| FinanceToolkit | 0 € | Medio | **Sí** (opcional) |
| FMP (fundamentales) | Free: 250/día, 5 años, EE. UU. | Medio | **Opcional**, clave fuera del repo |
| Ollama + modelo | 0 € (hardware) | Medio | **Sí** (local) |
| Cloud LLM | Por uso | Alto (privacidad) | **Opt-in** |
| OpenBB Workspace | Según plan | Medio | **No** para el panel actual |
| MCP | 0 € | Bajo | **Sí** para conectar agentes |

---

## 21. Preguntas abiertas (para decidir antes de la Fase 1)

1. ¿El usuario prioritario es **principiante**, **inversor** o **analista**? (recomiendo principiante/inversor).
2. ¿Se acepta **cloud LLM** o solo local?
3. ¿Se usa **clave FMP** o solo Yahoo?
4. ¿Qué mercados primero: **EE. UU., Europa o cripto**?
5. ¿Historial mínimo por activo: 5, 10 o 20 años?
6. ¿El informe lleva marca/nombre?
7. ¿Móvil ahora o después?

---

## 22. Referencias completas

- Video: <https://www.youtube.com/watch?v=NeZjsadeEVs>
- FinanceDatabase: <https://github.com/JerBouma/FinanceDatabase>
- FinanceDatabase docs: <https://www.jeroenbouma.com/projects/financedatabase>
- FinanceDatabase MCP: <https://www.jeroenbouma.com/projects/financedatabase/mcp>
- FinanceToolkit: <https://www.jeroenbouma.com/projects/financetoolkit>
- FinanceToolkit repo: <https://github.com/JerBouma/FinanceToolkit>
- FinanceToolkit MCP: <https://www.jeroenbouma.com/projects/financetoolkit/mcp>
- openbb-ai: <https://github.com/OpenBB-finance/openbb-ai>
- agents-for-openbb: <https://github.com/OpenBB-finance/agents-for-openbb>
- Agent Rita: <https://github.com/OpenBB-finance/agent-rita>
- MCP: <https://modelcontextprotocol.io>
- Documentación interna: `README.md`, `boveda/INDICE.md`, `boveda/Plan de mejora.md`

---

## 23. Registro de esta sesión

- **Qué se hizo:** análisis de la app, del video y de las cuatro referencias; diagnóstico; cuadro de 18 mejoras; diseño del agente; plan en 4 fases con criterios de aceptación.
- **Qué NO se hizo:** ningún cambio de código, ninguna instalación, ninguna tarea programada, ningún commit de código.
- **Dónde queda:** este documento + `P19` en `INDICE.md` + `S-29` en `Log de sesiones.md` + puntero en `Plan de mejora.md`.
- **Estado:** **propuesta, pendiente de aprobación**.
- **Siguiente paso:** aprobar (o corregir) las fases 0 y 1; solo entonces se implementa y se registra como `C-43` en adelante.

---

## 24. Respuestas del usuario y ajustes al plan (2026-10-20)

> Estas respuestas **ajustan** la propuesta; no la aprueban. Cuando haya conflicto, manda esta sección.

| Pregunta | Respuesta | Consecuencia |
|---|---|---|
| Usuario prioritario | **Inversor y analista** | **Dos modos**, no tres: **Inversor** (por defecto) y **Analista** (denso). El inversor ve 3 respuestas; el analista abre serie, fórmula y fuente en ≤ 2 clics. |
| Modelo | **Suscripción Anthropic con Claude** | La suscripción **no incluye la API**. Ruta recomendada: **MCP + Claude Desktop** (sin clave). Ollama como respaldo offline. API key solo si se quiere el chat dentro del panel (facturación aparte). |
| Fuentes | **Carga múltiple de información de diferentes fuentes** | **Registro de fuentes** + adaptadores + contraste; **carga por lotes** de varios activos; fuente y as-of por dato; discrepancia visible. |

### 24.1. Claude: qué permite la suscripción y qué no

| Ruta | Qué usa | ¿Sirve la suscripción? | Coste | Privacidad | Integración |
|---|---|---|---|---|---|
| **MCP + Claude Desktop** | Servidor MCP local + Claude Desktop | **Sí** | 0 extra | Solo salen las respuestas de las herramientas consultadas | Chat fuera del panel; el panel sigue siendo la vista |
| **API key + chat en el panel** | SDK/API de Anthropic | **No**; la API se factura aparte | Por token | Salen los datos consultados | Chat dentro del panel (mejor UX) |
| **Ollama local** | Modelo local | No aplica | 0 | Nada sale | Chat dentro del panel, offline |
| **Híbrido** | MCP + Ollama | Sí + local | 0 extra | Mixta | Claude para profundo, Ollama para rutina/offline |

**Recomendación:** **MCP + Claude Desktop** como ruta principal (usa la suscripción, no pide clave) y **Ollama** como respaldo offline. La API key queda como opción si más adelante se quiere el chat integrado en el panel.

**Consecuencia para la evaluación:** con MCP, la evaluación del LLM es **manual** (20 preguntas en Claude Desktop); la de las **herramientas** sí es automática. La evaluación automática del LLM exigiría API key.

### 24.2. MCP: qué expondríamos

Un servidor MCP local (`scripts/mcp_server.py`, futuro), por **stdio**, sin puerto y sin clave, con:

- `contexto_ultimo()` — última fila del contexto.
- `serie(nombre, desde)` — serie histórica.
- `percentil(nombre, años)` — posición vs historia.
- `buscar_activo(q)` — catálogo (FinanceDatabase).
- `ficha(simbolo)` — métricas del activo.
- `comparar(a, b, benchmark)` — retorno, riesgo, correlación.
- `fuentes_estado()` — fuente, as-of y retraso de cada serie.

Claude Desktop se configura **fuera del repo** (su `claude_desktop_config.json`); el repo solo contiene el servidor y sus pruebas. El panel no cambia: sigue siendo la vista; Claude es la capa de conversación.

### 24.3. Múltiples fuentes: registro, contraste y carga por lotes

**Registro de fuentes** (por métrica): primaria, fallback, contraste, retraso, unidades y licencia.

| Dato | Primaria | Fallback | Contraste |
|---|---|---|---|
| VIX / SPX | CBOE | Yahoo | — |
| Tasas / EFFR | Fed | — | — |
| EUR/USD | BCE | — | — |
| CPI / PIB | OECD | — | — |
| COT | CFTC | — | — |
| Factores | French | — | — |
| Funding BTC | Binance | — | — |
| Fundamentales | FMP (si clave) | Yahoo | — |

**Reglas de integridad:**

- La **primaria manda**; el fallback solo entra si la primaria falla.
- Si dos fuentes discrepan por encima de la tolerancia (p. ej. 1 % en precio, 0,1 pp en tipos), se muestra **bandera de discrepancia**; **no se mezcla en silencio**.
- Cada dato lleva **fuente, as-of y retraso**.
- **No se empalman series** de fuentes distintas sin documentar los puntos de empalme; si se empalma, se valida y se registra.
- Para evitar look-ahead, el contraste respeta el **retraso más conservador** de las fuentes comparadas.
- La caché no se encoge (`D-35`); el refresco valida y conserva el archivo anterior (`C-41`).

**Carga por lotes:** N activos a la vez (watchlist), con límite de concurrencia, progreso, fallos parciales y caché. Aceptación propuesta: **10 activos en < 30 s**, sin bloquear el panel.

**Riesgos:** doble conteo, look-ahead por retrasos distintos, licencias, límites de tasa, mapeo de tickers, monedas y zonas horarias, precios ajustados vs no ajustados.

### 24.4. Cambios concretos al plan

| Fase | Antes | Ahora |
|---|---|---|
| 1 | 3 modos (Principiante/Inversor/Analista) | **2 modos** (Inversor/Analista) + "ver detalle" |
| 2 | FinanceDatabase + ficha | + **registro de fuentes**, contraste y **carga por lotes** |
| 3 | Ollama primero, cloud opcional | **MCP + Claude Desktop** primero (suscripción), Ollama respaldo, API key opcional |
| 20 | Ollama + cloud | + **Claude Desktop/MCP** (sin coste extra), API key opt-in |
| 17 | — | + `F2-8` registro de fuentes, `F2-9` carga por lotes, `F3-7` servidor MCP |

### 24.5. Preguntas que siguen abiertas

4. ¿Mercados primero: EE. UU., Europa o cripto?
5. ¿Historial mínimo por activo: 5, 10 o 20 años?
6. ¿El informe lleva marca/nombre?
7. ¿Móvil ahora o después?

**Falta una confirmación para cerrar la Fase 3:** ¿la conversación va en **Claude Desktop vía MCP** (sin clave, usa tu suscripción) o quieres el **chat dentro del panel** (requiere API key y facturación aparte)? La recomendación es **MCP**.

---

> Este documento no es una decisión. Es la base para tomarla.
