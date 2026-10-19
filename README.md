# OpenBB local — Manual de uso

> Repositorio: `https://github.com/Artesania-Honuras/OpenBB`
> Última revisión: 2026-10-19 · Windows 11
> Para agentes de IA: empezar por `boveda/INDICE.md`.

---

## Índice

1. [Qué es este proyecto](#1-qué-es-este-proyecto)
2. [Requisitos](#2-requisitos)
3. [Estructura](#3-estructura)
4. [Arranque](#4-arranque)
5. [Verificación](#5-verificación)
6. [Uso diario](#6-uso-diario)
7. [Comandos de referencia](#7-comandos-de-referencia)
8. [Solución de problemas](#8-solución-de-problemas)
9. [Datos y configuración](#9-datos-y-configuración)
10. [Reglas del proyecto](#10-reglas-del-proyecto)
11. [Estado actual y pendientes](#11-estado-actual-y-pendientes)
12. [Cómo retomar en 3 pasos](#12-cómo-retomar-en-3-pasos)

---

## 1. Qué es este proyecto

Instalación **local** de OpenBB Platform desde el código fuente, con una API HTTP
en `127.0.0.1:6900` y un **puente de contexto macro hacia Freqtrade**.

```
Proveedores públicos (Fed, BCE, CBOE, CFTC, OECD, IMF, BLS, Deribit...)
        │  HTTPS de salida
        ▼
OpenBB Platform (tu PC)  ──►  API local 127.0.0.1:6900  ──►  /docs (Swagger)
        │
        │  exportación manual
        ▼
data/context/contexto_diario.parquet   (13 columnas macro)
        │  lectura directa en populate_indicators()
        ▼
Freqtrade (velas + decisión técnica + ejecución)
```

**Qué aporta OpenBB:** régimen macro (tipos, curva, VIX, inflación, PIB),
posicionamiento (COT), factores (Fama-French) y datos de múltiples proveedores
normalizados a un mismo formato.

**Qué NO aporta:** velas de cripto (devuelve vacío; eso lo da ccxt/Freqtrade),
ejecución de órdenes, ni señales de entrada.

**Privacidad:** todo corre en tu máquina. Solo hay tráfico de salida hacia las
APIs públicas de datos. Nada se sube a la nube. El enlace `my.openbb.co` que
aparece en el banner es opcional y no se usa.

---

## 2. Requisitos

| Requisito | Valor usado |
|---|---|
| Sistema | Windows 11 Pro build 26300 |
| Python | 3.13.12 dentro de `venvs\openbb` |
| Espacio | ~1 GB (venv 904 MB + datos) |
| Internet | Necesario para consultar proveedores |
| Git | 2.56+ |
| Opcional | `gh` CLI autenticado para publicar cambios |

No hace falta Docker ni WSL. No se requieren claves de API para los proveedores base.

---

## 3. Estructura

```
OpenBB\
├── venvs\openbb\              Entorno Python (NO se versiona)
├── repos\OpenBB\              Clon upstream (NO se versiona)
├── scripts\
│   ├── obb_env.py             Entorno + caché parquet
│   ├── fuentes_externas.py    Capa rápida: funding de perpetuos (Binance, sin clave)
│   ├── puente_freqtrade.py    Exportar contexto / fusionar velas
│   ├── validar_estrategia.py  Walk-forward + Monte Carlo
│   ├── validar_momentum.py    Momentum transversal contra el azar (permutación)
│   └── verificar_familias.py  Verificación de las 8 familias
├── strategies\
│   ├── StrategyContextoOpenBB.py
│   └── StrategyContextoOpenBBSinMacro.py
├── notebooks\
│   └── verificacion_8_familias.ipynb
├── data\
│   ├── cache\                 29 parquet cacheados (NO se versiona)
│   ├── context\               contexto_diario.parquet (sí se versiona)
│   ├── reporte_familias.txt
│   └── reporte_validacion.txt
├── freqtrade_bridge\
│   ├── backtest.json          Config de backtest (sin claves)
│   └── user_data\             Copias de velas (NO se versiona)
├── boveda\                    Memoria del proyecto (5 archivos)
├── CLAUDE.md                  Reglas obligatorias
├── estado.py                  Checklist de estado (solo lectura)
├── app.py                     Panel visual (Streamlit)
├── run-openbb-api.ps1         Lanzador de la API
├── run-openbb-app.ps1         Lanzador del panel visual
├── run-openbb-shell.ps1       Consola Python con obb
└── NOTAS-INSTALACION.md       Notas técnicas de instalación
```

**Fuera del repo (por `.gitignore`):** `venvs/`, `repos/`, `data/cache/`,
`freqtrade_bridge/user_data/`, `__pycache__/`, `*.csv` del contexto, logs y secretos.

---

## 4. Arranque

### 4.1 API (lo principal)

```powershell
cd C:\Users\DELL\.ipython\OpenBB
.\run-openbb-api.ps1
```

- Tarda **~60 segundos** en arrancar.
- Deja la ventana abierta: ahí se ven las peticiones en vivo.
- Al terminar muestra:

```
OpenBB Platform v2.0.1core
Authentication: DISABLED
Uvicorn running on http://127.0.0.1:6900
```

- Detener: `Ctrl+C` en esa ventana.
- Cambiar puerto: `.\run-openbb-api.ps1 -Port 6901`

El lanzador configura automáticamente:

| Variable | Para qué |
|---|---|
| `SSL_CERT_FILE` / `REQUESTS_CA_BUNDLE` | Que el BCE funcione (certifi) |
| `OPENBB_AUTO_BUILD=false` | Evita el cuelgue del import inicial |
| `PYTHONUTF8=1` / `PYTHONIOENCODING=utf-8` | Evita errores de codificación |

### 4.2 Consola Python (opcional)

```powershell
.\run-openbb-shell.ps1
```

Deja `obb` y `consultar()` listos:

```python
obb.fixedincome.rate.effr(provider='federal_reserve').to_df().tail(3)
consultar('vix', lambda: obb.index.price.historical('VIX', provider='cboe')).tail(2)
exit()
```

### 4.3 Panel visual (la app)

```powershell
.\run-openbb-app.ps1
```

- Abre en **http://127.0.0.1:8501** (y en el navegador automáticamente).
- Requiere la API arriba (paso 4.1).
- 8 pestañas: Resumen, Guía, Tipos, Riesgo, Macro, Posicionamiento, Contexto Freqtrade, API.
- 100 % local: no usa nube ni login.
- Cambiar puerto: `.\run-openbb-app.ps1 -Port 8502`
- Detener: `Ctrl+C` en su ventana.
- **Si cambias `app.py`, reinicia el panel.** Streamlit no recarga el script por sí solo:
  cierra su ventana, relanza `.\run-openbb-app.ps1` y refresca el navegador con `Ctrl+F5`.
  Un cambio que no se ve no cuenta como cambio hecho.

### 4.4 Swagger (navegador)

Con la API arriba: **http://127.0.0.1:6900/docs**

---

## 5. Verificación

```powershell
.\venvs\openbb\Scripts\python.exe estado.py
```

Imprime 22 chequeos con ✅/❌ y un veredicto. Es **solo lectura**.

| Bloque | Qué comprueba |
|---|---|
| Servicio | Puerto 6900, HTTP raíz, Swagger, llamada funcional real |
| Datos | Contexto (filas, columnas, frescura), caché |
| Config | `backtest.json`, sintaxis de estrategias |
| Externos | Fed, BCE, CBOE, CFTC alcanzables |
| Freqtrade | Procesos y puertos 8080/8081 (solo observación) |
| Repo | Git inicializado, limpio, con remoto y sincronizado |
| Máquina | Disco libre, RAM, uptime |

Códigos de salida: `0` todo OK · `1` fallo crítico · `2` degradado.

**Estado verificado el 2026-10-19 13:11:** 22/22 ✅.

---

## 6. Uso diario

### 6.1 Consultar datos

```powershell
.\run-openbb-shell.ps1
```

```python
# Tipos de la Fed
obb.fixedincome.rate.effr(provider='federal_reserve').to_df()

# Curva de treasuries (histórico completo)
obb.fixedincome.government.treasury_rates(
    provider='federal_reserve', start_date='2000-01-01').to_df()

# VIX
obb.index.price.historical('VIX', provider='cboe').to_df()

# EUR/USD
obb.currency.price.historical('EURUSD', provider='ecb').to_df()
```

### 6.2 Refrescar el contexto macro

```powershell
.\venvs\openbb\Scripts\python.exe scripts\puente_freqtrade.py --exportar
```

Reescribe `data\context\contexto_diario.parquet` (36.636 filas × 13 columnas).
Usa `--forzar` para ignorar la caché.

### 6.3 Ver el estado vivo (funding, libro de órdenes)

```powershell
.\venvs\openbb\Scripts\python.exe scripts\puente_freqtrade.py --estado
```

### 6.4 Medir una estrategia

```powershell
# Un par, detallado
.\venvs\openbb\Scripts\python.exe scripts\validar_estrategia.py --pair BTC_USDT --stake 0.1

# Los 7 pares
.\venvs\openbb\Scripts\python.exe scripts\validar_estrategia.py --todos --stake 0.1

# Experimento dirigido: entrada fija 20/50, se optimiza solo la SALIDA
.\venvs\openbb\Scripts\python.exe scripts\validar_estrategia.py --todos --stake 0.1 --salidas

# Momentum transversal (rotación entre pares) contra elegir pares al azar
.\venvs\openbb\Scripts\python.exe scripts\validar_momentum.py --sims 200

# Control de riesgo: tabla de variantes (régimen, volatilidad objetivo, criterio)
.\venvs\openbb\Scripts\python.exe scripts\validar_momentum.py --riesgo --sims 200
```

Reporta: ventanas walk-forward, exposición, Monte Carlo y referencia ajustada.

### 6.5 Verificar las 8 familias

```powershell
.\venvs\openbb\Scripts\python.exe scripts\verificar_familias.py
```

### 6.6 Notebook

```powershell
.\venvs\openbb\Scripts\jupyter.exe notebook notebooks\verificacion_8_familias.ipynb
```

---

## 7. Comandos de referencia

| Objetivo | Comando |
|---|---|
| Arrancar API | `.\run-openbb-api.ps1` |
| Abrir panel visual | `.\run-openbb-app.ps1` |
| Consola OpenBB | `.\run-openbb-shell.ps1` |
| Estado completo | `.\venvs\openbb\Scripts\python.exe estado.py` |
| Refrescar contexto | `.\venvs\openbb\Scripts\python.exe scripts\puente_freqtrade.py --exportar` |
| Estado vivo | `.\venvs\openbb\Scripts\python.exe scripts\puente_freqtrade.py --estado` |
| Validar 1 par | `... validar_estrategia.py --pair BTC_USDT --stake 0.1` |
| Validar 7 pares | `... validar_estrategia.py --todos --stake 0.1` |
| Validar salidas (entrada fija) | `... validar_estrategia.py --todos --stake 0.1 --salidas` |
| Validar momentum transversal | `... validar_momentum.py --sims 200` |
| Variantes de riesgo del momentum | `... validar_momentum.py --riesgo --sims 200` |
| Verificar familias | `... verificar_familias.py` |
| Swagger | `http://127.0.0.1:6900/docs` |
| Backtest Freqtrade | ver [sección 6.4](#64-medir-una-estrategia) |

---

## 8. Solución de problemas

| Síntoma | Causa probable | Arreglo |
|---|---|---|
| `puerto 6900 en uso` | Ya hay una instancia | Cerrarla o usar `-Port 6901` |
| La API no responde tras 90 s | Import lento o error de build | Mirar la ventana; verificar `OPENBB_AUTO_BUILD=false` |
| `import openbb` se cuelga | Auto-build activo | Asegurar `OPENBB_AUTO_BUILD=false` |
| `UnicodeEncodeError` | Consola en cp1252 | Usar `run-openbb-*.ps1` (ya fuerza UTF-8) |
| BCE falla (`URLError`) | Certificados de Windows | Usar los lanzadores (cargan certifi) |
| `results: []` | Proveedor requiere clave | Ver sección 11 (FRED/EIA) |
| Primera consulta tarda 30-60 s | Proveedor externo lento | Normal; las siguientes usan caché |
| Contexto desactualizado | No se reexportó | `puente_freqtrade.py --exportar` |
| Panel 8501 no abre | La API está caída | Arrancar `.\run-openbb-api.ps1` y refrescar |
| Cambié `app.py` y no veo nada nuevo | Streamlit sirve el script que cargó al arrancar | Reiniciar el panel y `Ctrl+F5` en el navegador |
| `git push` rechazado | Remoto adelantado | `git pull --rebase` y reintentar |
| `estado.py` marca ❌ Repo | Cambios sin commit | `git add -A && git commit && git push` |

**Regla de dos strikes:** si la API se cuelga dos veces en la misma sesión, no
relanzar una tercera. Anotar el síntoma y los logs.

---

## 9. Datos y configuración

### 9.1 Contexto diario (14 columnas)

| Columna | Fuente | Retraso aplicado |
|---|---|---|
| `yield_2y`, `yield_10y`, `slope_10y_2y` | Fed | 1 día |
| `fed_funds` | Fed | 1 día |
| `vix` | CBOE | 1 día |
| `spx` | CBOE | 1 día |
| `eurusd` | BCE | 1 día |
| `cpi_yoy` | OECD | 45 días |
| `gdp_yoy` | OECD | 45 días |
| `cot_net` | CFTC | 3 días |
| `ff_mkt_rf`, `ff_smb`, `ff_hml` | Fama-French | 31 días |

Y una columna de **capa rápida**, de fuente externa a OpenBB:

| Columna | Fuente | Retraso aplicado |
|---|---|---|
| `funding_btc_anual` | Binance (`fapi/v1/fundingRate`) | 1 día |

El funding es lo que cuesta estar largo en el perpetuo de BTC, expresado en %
anual. Positivo = los largos pagan a los cortos (euforia, apalancamiento);
negativo = pánico. Medido en `E-08`: **no sirve como filtro de entrada**, pero
sí como termómetro de estado.

El retraso replica la fecha real de publicación: evita look-ahead. La fusión con
velas usa `merge_asof(direction="backward")`.

### 9.2 Configuración viva

`freqtrade_bridge\backtest.json`:

| Clave | Valor |
|---|---|
| exchange | binance (spot) |
| timeframe | 4h |
| pares | 7 (BTC, ETH, SOL, BNB, ADA, AVAX, XRP) |
| stake | 100 USDT por operación |
| claves | vacías (no se necesitan para backtest) |

### 9.3 Secretos

- No hay `.env`, `.pem`, `.key` ni tokens en el repositorio.
- `user_settings.json` global de OpenBB está fuera del proyecto y en `.gitignore`.
- Claves opcionales (FRED, EIA) se configuran fuera del repo, nunca en él.

---

## 10. Reglas del proyecto

Están completas en `CLAUDE.md`. Resumen:

1. **Registro:** todo cambio → `C-NN`; todo experimento → `E-NN`; toda sesión →
   Log; commit y push **en la misma sesión**.
2. **Cambios:** nada se cambia sin medición reproducible, validación fuera de
   muestra, registro y despliegue verificado.
3. **Estado:** "¿está todo al 100%?" obliga a ejecutar `estado.py` y pegar la
   tabla completa. No vale "todo ok" sin tabla.
4. **Trabajo:** ubicar la entrada antes de tocar; misma herramienta y condiciones;
   secretos fuera; lo no verificable es **pendiente**, no "hecho".

Memoria: `boveda/INDICE.md`, `Manual de cambios.md`, `Registro de resultados.md`,
`Log de sesiones.md`, `Plantillas.md`.

---

## 11. Estado actual y pendientes

### Decisiones vivas

| ID | Decisión | Evidencia |
|---|---|---|
| D-01 | Python 3.13.12 + venv editable | 37 paquetes, 0 conflictos |
| D-02 | API loopback, auth off | 200 OK, 869 rutas |
| D-03 | `eia` excluido | Requiere clave en build |
| D-04 | SSL certifi | EURUSD 7.117 filas |
| D-05 | Autobuild off | Arranque ~60 s |
| D-06 | Contexto con retrasos de publicación | 36.636 × 13, 0 NaN en 2026 |
| D-07 | Puente por archivo | 14.886 velas fusionadas |
| D-08 | No integrar la estrategia | 0/7 baten la referencia |

### Resultado de la validación (2021-01 → 2026-10) — revalidado con el contexto corregido

| Par | OOS | Referencia misma exposición | ¿Bate? |
|---|---|---|---|
| ADA | +5,8% | +5,5% | ✅ por 0,3 pp |
| AVAX | +16,1% | +32,6% | ❌ |
| BNB | +5,6% | +197,6% | ❌ |
| BTC | +8,2% | +57,1% | ❌ |
| ETH | +18,6% | +71,7% | ❌ |
| SOL | +14,2% | +285,6% | ❌ |
| XRP | +4,6% | +60,8% | ❌ |

**7/7 positivos, 1/7 baten la referencia** (y el único lo hace por 0,3 puntos, un
empate estadístico). Antes del arreglo del contexto era 0/7. El criterio exige
≥ 2/3 de los activos. El cruce EMA 20/50 no tiene alfa: `E-07`.

### Filtro de funding de perpetuos (`E-08`)

Primera feature de la capa rápida. Misma herramienta y ventana, tres variantes:

| Variante | OOS mediano | Exposición | Baten la referencia |
|---|---|---|---|
| Sin filtro (base) | +8,2% | 35,7% | 1/7 |
| `funding_max = 20` (evitar largos caros) | +3,0% | 30,3% | 0/7 |
| `funding_min = 0` (solo con funding positivo) | **+15,2%** | 34,3% | 1/7 |

**Veredicto: no pasa la puerta.** La dirección importa (filtrar el funding alto
resta 8 puntos de mediana), pero ninguna variante alcanza ≥ 2/3. El cuello de
botella real está en la exposición del 30-45%, que no captura el retorno de
comprar y mantener.

### Gestión de salida con la entrada fija (`E-09`)

Si el problema fuera el *timing de salida*, mover la salida debería notarse. Se
fija la entrada (EMA 20/50, sin filtros macro ni de funding) y se optimiza solo
la salida:

| Variante | OOS mediano | Exposición | Baten | Δ vs salida actual |
|---|---|---|---|---|
| A) Salida actual (−8 % / +15 % / cruce) | +10,0% | 46,7% | 1/7 | — |
| B) Stop móvil 10% | +6,5% | 46,2% | 0/7 | −4,6 pts |
| C) Stop móvil 20% | +10,0% | 46,7% | 1/7 | +0,0 pts |
| D) Break-even tras +6% | +6,8% | 46,1% | 0/7 | −4,3 pts |
| E) Salir al perder la media rápida | −3,9% | 39,0% | 0/7 | −13,5 pts |
| F) Búsqueda completa (12 combinaciones) | +4,6% | 45,2% | 0/7 | −6,7 pts |

**Veredicto: no pasa la puerta, y aquí el hallazgo es más duro.** El stop móvil
al 20 % nunca llega a activarse (idéntico a la línea base). La búsqueda completa
rinde *peor* que la línea base, que es lo que pasa cuando no hay señal que
encontrar y el buscador solo añade sobreajuste. Y sobre todo: la referencia de
misma exposición equivale a **elegir al azar ese mismo porcentaje de días**, y el
cruce EMA queda por debajo en 6 de 7 pares. Conclusión: no es el filtro, no es la
salida — **la base (cruce EMA 20/50) no tiene ventaja frente al azar**.

### Momentum transversal (`E-10`) — la primera señal con ventaja

Se cambia la señal, no los alrededores: en cada rebalanceo se mantienen los *K*
pares con mejor retorno de los últimos *L* días. La referencia es **elegir los K
pares al azar** con el mismo calendario y los mismos costes (permutación, 200
semillas).

| Medición | Resultado |
|---|---|
| Walk-forward (parámetros elegidos en entrenamiento) | **+1.112 %** · drawdown **−81,7 %** · percentil **99** de la nube al azar |
| Probabilidad de que el azar la iguale o supere | **1,0 %** |
| Robustez: 18 combinaciones fijas | **16/18** baten la mediana del azar · mediana global percentil 93 |
| Contra no hacer nada: mejor config. simple (L=30, K=3, semanal) | **+1.442,7 %** y DD **−77,4 %** |
| Cesta a peso igual (comprar los 7 y no tocar) | +1.121,8 % y DD −81,9 % |

**Veredicto: ventaja demostrada, integración descartada por ahora.** Dos avisos
que van pegados al titular: la mediana del azar en esta cesta es **negativa**
(elegir pares al azar entre 7 altcoins pierde dinero), así que superarla es más
fácil que superar al mercado — la comparación que manda es contra la cesta, y ahí
la ventaja es modesta. Y **todas** las combinaciones tienen drawdowns de −75 % a
−93 %, porque la cartera está siempre 100 % invertida: no hay control de riesgo.
Eso es exactamente lo siguiente que hay que construir, y es donde la capa lenta
por fin tiene papel: no elegir entradas, sino cuánto capital está expuesto.

### Control de riesgo del momentum (`E-11`) — qué funciona y qué no

Tres piezas probadas como interruptores (no como parámetros a optimizar). La nube
al azar lleva **las mismas señales de riesgo**, así que lo único que cambia es el
criterio de selección. Referencia: cesta a peso igual **+1.121,8 %**, DD **−81,9 %**,
Calmar **13,69**.

| Variante | OOS | DD | Calmar | Percentil azar |
|---|---|---|---|---|
| A) Retorno bruto, sin control (= `E-10`) | +1.112 % | −81,8 % | 13,61 | 99 |
| **B) Calmar, sin control** | **+1.538 %** | **−80,1 %** | **19,22** | **100** |
| C) Calmar + régimen 200 d | +160 % | −69,7 % | 2,30 | 97 |
| D) Calmar + régimen 200 d + vol 60 % | +374 % | −47,3 % | 7,91 | 99,5 |
| E) Calmar + vol 60 % | +630 % | −74,3 % | 8,49 | 98 |
| F) Calmar + régimen 100 d + vol 40 % | +184 % | −49,9 % | 3,69 | 88,5 |

**Veredicto: ninguna variante cumple las tres condiciones** (DD mejor que −20 %,
percentil ≥ 95, Calmar mejor que la cesta). El control de riesgo sale caro: el
filtro de régimen recorta el drawdown de −80 % a −70 % y **se lleva dos tercios
del retorno**; el Calmar se hunde de 19,2 a 2,3 porque entra tarde y sale tarde.
Lo que sí funcionó fue arreglar un error de diseño: seleccionar en entrenamiento
por **Calmar** en vez de por retorno bruto (el bruto premiaba el máximo riesgo).
Se adopta Calmar como criterio por defecto; `--objetivo retorno` reproduce `E-10`.

**Lo que esto dice del fondo del problema:** con 7 altcoins el drawdown es
**estructural** — en un mercado bajista caen las siete a la vez. El DD < 20 % no
se alcanza con filtros sobre la cesta: hacen falta filtro **absoluto por activo**
y **más universo** (20-30 pares), que es donde entran `CCXT` y `VectorBT` del
ecosistema.

### Pendientes

| Prioridad | Pendiente |
|---|---|
| P1 | Encontrar un gatillo con ventaja fuera de muestra (bloqueo principal) |
| P2 | Refresco automático del contexto |
| P3 | Instalar estrategia en los bots (bloqueado por P1) |
| P4 | Clave FRED gratuita (opcional) |
| P5 | Provider EIA (opcional) |
| P6 | Tests propios |
| P7 | Revisar 2 archivos sucios del clon upstream |
| P8 | Re-ejecutar el walk-forward de 7 pares con el contexto corregido (`C-13`) | ✅ hecho (`E-07`): 0/7 → 1/7, sin cambios en el veredicto |

---

## 12. Cómo retomar en 3 pasos

1. **Estado:**
   ```powershell
   cd C:\Users\DELL\.ipython\OpenBB
   .\venvs\openbb\Scripts\python.exe estado.py
   ```
2. **Mapa:** leer `boveda/INDICE.md` (secciones 4 y 7).
3. **Historia:** leer la última entrada de `boveda/Log de sesiones.md` y seguir
   por el pendiente P1.

Si el paso 1 muestra un ❌ crítico, se atiende antes de cualquier otra cosa.

### Después de reiniciar o actualizar el equipo

Nada arranca solo. Las dos ventanas hay que relanzarlas:

```powershell
cd C:\Users\DELL\.ipython\OpenBB
.\run-openbb-api.ps1     # ventana 1: esperar "Uvicorn running on 127.0.0.1:6900"
.\run-openbb-app.ps1     # ventana 2: restaurar ventana 1 si se cerró
```

Luego `.\venvs\openbb\Scripts\python.exe estado.py` → debe dar **23/23 ✅**.
Si el contexto tiene más de dos días, el propio panel avisa; se refresca con
`... scripts\puente_freqtrade.py --exportar --forzar`.

---

*Manual mantenido junto con la memoria del proyecto. Cualquier cambio se registra
como `C-NN` y se sube a Git en la misma sesión.*
