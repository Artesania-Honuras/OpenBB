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
data/context/contexto_diario.parquet   (14 columnas macro)
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
│   ├── context\               contexto_diario.parquet (regenerable, NO se versiona)
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
- 9 pestañas: Resumen, Guía, Tipos, Riesgo, Macro, Posicionamiento, Contexto Freqtrade, Estrategia, API.
- La pestaña **Estrategia** muestra la puerta de graduación, los experimentos `E-07`…`E-11` y los reportes crudos de `data/reporte_*.txt`.
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

La forma verificada (valida antes de guardar, escribe atómico y deja copia del
anterior):

```powershell
.\venvs\openbb\Scripts\python.exe scripts\refrescar_contexto.py
```

- Descarga las 10 fuentes con `forzar=True` (si no, no refresca nada).
- **Valida**: columnas, filas que no retrocedan, fecha final, rangos plausibles,
  saltos imposibles frente al contexto anterior y frescura de cada fuente.
- Si algo falla, **conserva el contexto anterior** y sale con código 1.
- Guarda con escritura atómica y deja `contexto_diario_anterior.parquet`.
- Escribe una línea en `data\refresco_contexto.log`.

El contexto termina **mañana** por diseño: cada serie lleva su retraso de
publicación, así que el cierre de hoy se etiqueta para mañana (`merge_asof` lo
usa sin ver el futuro).

**Tarea diaria** (a las 09:05, tras el cierre de EE. UU. del día anterior):

```powershell
# registrar (idempotente)
powershell -ExecutionPolicy Bypass -File scripts\instalar_refresco.ps1

# probarla ahora
Start-ScheduledTask -TaskName "OpenBB - refresco de contexto"
Get-ScheduledTaskInfo -TaskName "OpenBB - refresco de contexto"   # LastTaskResult = 0

# quitarla
powershell -ExecutionPolicy Bypass -File scripts\instalar_refresco.ps1 -Quitar
```

Se registra en modo **interactivo**: corre con la sesión abierta. `S4U` (sin
sesión) exige permisos de administrador que no se piden. Si el equipo estaba
apagado a las 09:05, se ejecuta al iniciar sesión (`-StartWhenAvailable`).
`estado.py` comprueba que la tarea existe, que corrió hace menos de 48 h y que
su último resultado fue 0.

El modo manual recomendado es `scripts\refrescar_contexto.py` (valida y conserva el
anterior). `puente_freqtrade.py --exportar --forzar` sigue existiendo, pero **no valida
ni conserva el anterior**: solo para diagnosticar.

El `.parquet` **no se versiona** (es binario regenerable); el CSV tampoco.

**En el panel**, la pestaña *Contexto Freqtrade* muestra una tarjeta con el
resultado del último refresco: verde si terminó bien, roja si falló (con el
motivo), ámbar si lleva más de 48 h, gris si no hay registro. Debajo, las
últimas líneas del log. La lógica vive en `scripts\estado_contexto.py` y se
puede probar sin panel: `python scripts\estado_contexto.py`.

### 6.3 Ver el estado vivo (funding, libro de órdenes)

```powershell
.\venvs\openbb\Scripts\python.exe scripts\puente_freqtrade.py --estado
```

### 6.4 Medir una estrategia

```powershell
# Un par, detallado
.\venvs\openbb\Scripts\python.exe scripts\validar_estrategia.py --pair BTC_USDT --stake 0.1

# Los 7 pares originales (hoy hay 24: usar --pares para reproducir)
.\venvs\openbb\Scripts\python.exe scripts\validar_estrategia.py --todos --stake 0.1

# Experimento dirigido: entrada fija 20/50, se optimiza solo la SALIDA
.\venvs\openbb\Scripts\python.exe scripts\validar_estrategia.py --todos --stake 0.1 --salidas

# Momentum transversal (rotación entre pares) contra elegir pares al azar
.\venvs\openbb\Scripts\python.exe scripts\validar_momentum.py --sims 200

# Control de riesgo: tabla de variantes (régimen, volatilidad objetivo, criterio)
.\venvs\openbb\Scripts\python.exe scripts\validar_momentum.py --riesgo --sims 200

# La fase del rebalanceo: ¿la estrategia decide igual que el validador? (42 fases)
.\venvs\openbb\Scripts\python.exe scripts\verificar_rotacion.py
.\venvs\openbb\Scripts\python.exe scripts\auditar_fase.py
```

Reporta: ventanas walk-forward, exposición, Monte Carlo y referencia ajustada.

> **Si guardas la salida en un reporte**, no uses `>` ni `Tee-Object` a secas:
> PowerShell 5.1 escribe **UTF-16** y además decodifica la salida de Python con
> la codificación de la consola (cp850), así que rompe tildes y guiones. La
> receta que funciona:
>
> ```powershell
> $env:PYTHONIOENCODING = "utf-8"
> [Console]::OutputEncoding = [Text.Encoding]::UTF8
> .\venvs\openbb\Scripts\python.exe scripts\auditar_fase.py |
>     Out-File -Encoding utf8 data\reporte_fase.txt
> ```
>
> Si ya tienes alguno mal, `python scripts\normalizar_reportes.py` arregla
> **las dos cosas**: la codificación y el mojibake. `estado.py` lo comprueba.

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
| Refrescar contexto | `.\venvs\openbb\Scripts\python.exe scripts\refrescar_contexto.py` |
| Estado vivo | `.\venvs\openbb\Scripts\python.exe scripts\puente_freqtrade.py --estado` |
| Validar 1 par | `... validar_estrategia.py --pair BTC_USDT --stake 0.1` |
| Validar 7 pares | `... validar_estrategia.py --todos --stake 0.1` |
| Validar salidas (entrada fija) | `... validar_estrategia.py --todos --stake 0.1 --salidas` |
| Descargar/verificar velas (24 pares) | `... scripts\descargar_velas.py` · `--verificar` para solo revisar |
| Validar momentum transversal | `... validar_momentum.py --sims 200` |
| Variantes de riesgo del momentum | `... validar_momentum.py --riesgo --sims 200` |
| Reproducir una medición previa | `... validar_momentum.py --pares BTC_USDT,ETH_USDT,... --sims 200` |
| Configuración fija (lo instalable) | `... validar_momentum.py --fijo "30,3,7" --sims 200` |
| Dimensionar el sleeve | `... scripts\dimensionar.py --sleeves 5,10,15,20` |
| Momentum absoluto por activo (`E-12`) | `... validar_momentum.py --tendencia 200 --sims 200` |
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
| Contexto desactualizado | La tarea diaria no corrió | Mirar la tarjeta del panel o `data\refresco_contexto.log`; lanzarla con `Start-ScheduledTask` |
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
| D-06 | Contexto con retrasos de publicación | 36.637 × 14, 0 NaN en 2026 |
| D-07 | Puente por archivo | 14.886 velas fusionadas |
| D-08 | No integrar la estrategia | 0/7 baten la referencia |

> Las decisiones de investigación (**D-09 … D-34**: funding, fase del rebalanceo,
> cierre de la línea de señales, refresco verificado) viven en
> `boveda/INDICE.md`, sección 4. El resumen que importa: **no hay nada que
> instalar** (`D-31`, `D-33`).

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
se alcanza con filtros sobre la cesta. Las dos hipótesis que quedaban —filtro
**absoluto por activo** y **más universo**— se midieron después: las dos
fallaron. Ver `E-12` y `E-13`.

### Momentum absoluto por activo (`E-12`) — también descartado

El filtro por activo (mantener solo los K mejores que además conserven su propia
tendencia) se aplica **igual a la nube al azar**:

| Variante | OOS | DD | Calmar | Percentil azar | P(azar ≥) |
|---|---|---|---|---|---|
| B) Calmar, sin control (mejor de `E-11`) | +1.538 % | −80,1 % | **19,22** | 100 | 0,0 % |
| G) + tendencia propia 200 d | +145 % | −72,0 % | 2,01 | 84 | 16,0 % |
| H) + tendencia propia 100 d | +811 % | −76,2 % | 10,64 | 73,5 | 26,5 % |
| I) + tendencia 200 d + vol 60 % | +240 % | −59,4 % | 4,03 | 89 | 11,0 % |

**Descartado, y con más motivo que el filtro de régimen:** baja el drawdown
(−80 % → −59/−76 %) y hunde el Calmar (19,2 → 2,0/10,6/4,0); además **mata la
significación** — con el mismo filtro, elegir pares al azar iguala o supera a la
estrategia el 11-26 % de las veces. El motivo se ve en la nube: el filtro deja
1-3 candidatos, la mediana del azar sube a +411 % y el ranking deja de importar
porque el azar compra casi lo mismo.

**Conclusión de la serie `E-10`…`E-12`:** el momentum tiene ventaja real, pero
**ningún control de riesgo probado la conserva**. El límite no es el mecanismo:
parecía ser el **universo**, con 7 altcoins sin dispersión suficiente.

### Universo ampliado a 24 pares (`E-13`) — la hipótesis era falsa

Antes de ampliar apareció un **defecto en los datos**: los 7 pares no terminaban
en la misma fecha (4 de 7 el 2026-09-18, los otros el 2026-10-17) y el relleno
hacia adelante dejaba **29 días con 4 de 7 precios congelados**. Corregido
descargando 24 pares homogéneos con `scripts/descargar_velas.py`, que **verifica**
primera/última fecha, huecos y retraso (y descartó a EOS, retirado en 2025).
Repetir `E-11` con datos limpios da lo mismo: +1.538,1 % / −80,0 % / Calmar 19,22.

| | retorno OOS | DD | Calmar | Ventanas |
|---|---|---|---|---|
| Cesta a peso igual (24 pares) | +314 % | −81,9 % | 3,83 | — |
| 7 pares (`E-11` B) | +1.538 % | −80,0 % | 19,22 | 7/11 |
| **24 pares, misma lógica** | **+3.118 %** | **−87,1 %** | **35,82** | **6/11** |

**Triplicar la cesta sube el retorno un 103 % y el Calmar un 86 %, y EMPEORA el
drawdown y la supervivencia.** El drawdown no venía de la falta de dispersión:
con 7 o con 24, en las caídas caen todos a la vez. De las 9 variantes de riesgo,
**ninguna baja de −35,7 %**, y la que llega ahí recorta el retorno un 81 %.

Dos avisos que quedan escritos:

- **La volatilidad objetivo 60 % gana en las cuatro medidas con 24 pares y
  perdía en las cuatro con 7.** Un mecanismo que cambia de signo según el
  universo es suerte de camino. No se adopta.
- **El azar dejó de ser rival serio**: la mediana del azar pasa de +100,7 % (7
  pares) a **−17,9 %** (24 pares) porque elegir al azar entre 24 incluye mucha
  basura. El percentil 100 ya no demuestra lo mismo; la referencia que vale es la
  cesta, y la cesta también cae −81,9 %.

**Conclusión:** el drawdown del momentum transversal en cripto es **de la clase de
activo, no del mecanismo ni del universo**. La pregunta deja de ser *«¿cómo bajo
el DD al 20 %?»* y pasa a ser *«¿qué tamaño le doy a una exposición cuya caída
natural es del 87 %?»*. Con un sleeve del 10 %, esa caída es un ~8,7 % del
capital. Es una decisión de asignación, no de estrategia.

**Lo que no está medido:** todo `E-10`…`E-13` es **solo largos**. La versión
mercado-neutral (largo en los mejores, corto en los peores) es el mecanismo
estándar contra este drawdown y no se ha medido; exige perpetuos y coste de
funding, y los bots de Freqtrade son spot.

### Configuración fija (`E-14`) — y la prueba que la refutó (`E-16`)

El +3.118 % sale de **re-optimizar cada 6 meses**. Para operarlo hay que
automatizar eso. Una regla fija —mismos parámetros de principio a fin— es lo que
se puede instalar y auditar. La propuesta, **elegida a priori en `E-10`**, es
`L=30 d`, `K=3`, semanal:

| L | K | retorno | DD | Calmar | CAGR | Ventanas | P(azar ≥) |
|---|---|---|---|---|---|---|---|
| **30** | **3** | **+820 %** | **−82,5 %** | **9,95** | **+47,2 %** | **7/11** | **0,5 %** |
| 30 | 5 | +915 % | −79,8 % | 11,47 | +49,7 % | 6/11 | 0,0 % |
| 60 | 3 | +341 % | −92,1 % | 3,70 | +29,5 % | 6/11 | 0,5 % |
| 60 | 5 | +68 % | −86,8 % | **0,78** | +9,4 % | 6/11 | 5,0 % |

**Esa tabla tiene un parámetro que no aparece: la fase del rebalanceo.**
«Semanal» no dice *cuándo*. El validador rebalancea cada 42 velas desde el inicio
de la ventana — una fase arbitraria. Al escribir la estrategia para Freqtrade
(`P3`) hubo que elegir una fecha concreta, y el calendario natural es el lunes
00:00. El resultado cambió de +820 % a **+95,8 %**. Se midieron las 42 fases:

| Medición (`E-16`) | Retorno | DD | Calmar |
|---|---|---|---|
| Validador, fase 0 (la de `E-14`) | +820,4 % | −82,5 % | 9,95 |
| **Mediana de las 42 fases** | **+816,5 %** | −82 a −88 % | — |
| Mejor fase (miércoles 08:00) | +3.776,3 % | −82,5 % | — |
| **Peor fase (lunes 00:00, a priori)** | **+95,8 %** | **−87,9 %** | **1,09** |
| Cesta a peso igual (no hacer nada) | +370,3 % | −81,9 % | 4,52 |
| Azar, calendario del lunes (mediana) | +27,2 % | — | — |

Con el calendario natural la rotación **pierde contra la cesta** en retorno,
drawdown y Calmar, y **no se distingue del azar**: percentil 76, **P(azar ≥)
24,0 %**. Ventanas de 6 meses: **5/11**. Las 42 fases son positivas, pero el
rango es de **40×** y tiene **estacionalidad semanal sistemática** (domingo y
lunes son el peor tramo; martes a jueves, el mejor). Elegir el miércoles porque
da +3.776 % sería *data snooping* sobre 42 variantes.

**Conclusión:** ❌ **la rotación no se instala.** El código está escrito y
verificado (`C-33`): el núcleo elige **296/296** veces lo mismo que el validador
y mide el momento a **30,00 días exactos**. Lo que falló no fue el código, fue la
regla. El error de despliegue se evitó antes de tocar un bot.

### La auditoría completa (`E-17`) — la rama de momentum se cierra

La fase no era un defecto de la regla fija: era un defecto de **todo lo medido antes**.
Se repitió el walk-forward completo (18 m / 6 m, 18 combinaciones, objetivo Calmar) en
las **42 fases**, en los dos universos. `fase=0` reproduce `E-13` exacto, así que la
auditoría mide lo mismo que se midió.

| Universo | Retorno OOS mediano | Calmar mediano | Cesta (Calmar) | Fases que baten la cesta |
|---|---|---|---|---|
| 24 pares (`E-13`) | +342,0 % | 3,56 | 4,52 | **18/42** |
| 7 pares (`E-10`) | +129,7 % | 1,55 | 15,65 | **1/42** |

- `E-10` publicó **+1.538 % y Calmar 19,22**: el **máximo exacto** de las 42 fases, y la
  única que bate a la cesta. Su mediana es Calmar 1,55.
- `E-13` publicó +3.118 % y Calmar 35,82: pegado al máximo (36,45 en la fase 2). Su
  mediana es 3,56, **por debajo** de la cesta.
- La dirección de `E-13` (24 pares > 7 pares) sí sobrevive en las medianas — pero entre
  dos variantes que **ninguna** supera a la cesta.

**Conclusión:** ❌ **no hay nada desplegable y no se sigue optimizando.** No falta un
ajuste: falta un mecanismo. La prueba cuesta **80 s** (`scripts\auditar_fase.py`), así
que desde ahora es obligatoria para cualquier regla nueva (`D-32`).

### El macro como filtro de mercado (`E-18`) — la última pregunta

Si no se puede elegir **qué** tener, ¿se puede elegir **cuándo** estar? Se probó la
regla macro pre-registrada (la de `E-07`, fijada antes de medir) sobre la cesta a peso
igual: dentro cuando `VIX < 25` y la pendiente 10a-2a es positiva, en caja si no.

Dos protecciones: el VIX se usa con **un día de retraso** (a las 00:00 del día d no se
conoce su cierre) y el control no es "no hacer nada", sino la **misma serie de
posiciones desplazada circularmente** — mismos días dentro, mismos cambios, otras
fechas. Si la regla no supera esa nube, lo que mejora es la exposición, no la señal.

| Variante | Retorno | DD | Calmar | Dentro |
|---|---|---|---|---|
| **Cesta sin filtro** | **+420,9 %** | −81,6 % | **5,16** | 100 % |
| **Regla a priori (VIX<25 + pendiente, lag 1)** | +318,9 % | −75,8 % | **4,21** | 52,9 % |
| VIX<30 · lag 2 (la mejor de 12) | +447,8 % | −72,0 % | 6,22 | 95,3 % |
| Regla invertida | +10,5 % | −72,0 % | 0,15 | 47,1 % |

- La regla a priori **pierde** contra la cesta y cae en el **percentil 75** del azar:
  P(azar ≥ regla) = **25,2 %**.
- Solo **2 de 12** variantes baten a la cesta, y ninguna es significativa (percentiles
  68 y 72). Son las mejores de 12: elegirlas sería el mismo error que la fase.
- El signo **sí** importa (invertirla la hunde a 0,15), pero distinguir algo no es
  batir a no hacer nada.

**Conclusión:** ❌ el macro **no sirve como filtro de mercado** (`D-33`). OpenBB se
queda como **panel de información y contexto**, que es lo que sí aporta: saber en qué
régimen se opera, con datos verificados y en local.

### Dimensionado (`E-15`) — sleeve del 10 % (sin objeto tras `E-16`)

| sleeve | CAGR mediano | caída típica | 5 % peor | P(caída > 20 %) | P(año perdedor) |
|---|---|---|---|---|---|
| 5 % | +4,0 % | −6,6 % | −11,5 % | 0,0 % | 19,0 % |
| **10 %** | **+8,0 %** | **−13,0 %** | **−22,0 %** | **9,0 %** | **19,5 %** |
| 15 % | +12,0 % | −19,1 % | −31,7 % | 42,3 % | 20,6 % |
| 20 % | +15,8 % | −24,8 % | −40,3 % | 77,4 % | 21,3 % |

> **Sin objeto tras `E-16`.** La aritmética del bootstrap es correcta, pero
> dimensionaba una regla que no supera la puerta. Se conserva como método.

**Se elige el 10 %** y se declara que **incumple el `DD p95 < 20 %` por 2 puntos**
(−22,0 %). Si la puerta se aplica al pie de la letra, el sleeve es el 5 % y el
CAGR cae a +4 %: demasiado pequeño para compensar el trabajo. Al 15 % la
probabilidad de superar el −20 % de drawdown salta al 42 %.

Modelo: bootstrap por bloques de 7 días (1.000 caminos), fracción de sleeve
**constante** (rebalanceada), caja al 0 %. La primera versión se hizo sin
rebalanceo y daba −31 % con el 5 % invertido — imposible: era el modelo el que
estaba mal (un sleeve que crece acaba siendo el 80 % de la cartera), no alto el
riesgo.

### Pendientes

| Prioridad | Pendiente |
|---|---|
| P1 | ~~Gatillo con ventaja fuera de muestra~~ | ❌ **cerrado en negativo** (`E-17` + `E-18`): en momentum no existe, y el macro como filtro temporal tampoco lo aporta |
| P2 | ~~Refresco automático del contexto~~ | ✅ **hecho** (`C-38`/`C-39`): `scripts\refrescar_contexto.py` con validación y escritura atómica, tarea diaria a las 09:05, log y **tarjeta de aviso en el panel** |
| P3 | ~~Instalar estrategia en los bots~~ | ✅ **Cerrado en falso positivo evitado**: escrita y verificada, **refutada por la fase** (`E-16`). No se copia a Freqtrade |
| P17 | ~~Prueba de fase obligatoria~~ | ✅ hecha y aplicada (`C-34`): 42 fases, reportar rango |
| P4 | Clave FRED gratuita (opcional) |
| P5 | Provider EIA (opcional) |
| P6 | Tests propios |
| P7 | Revisar 2 archivos sucios del clon upstream |
| P8 | ~~Re-ejecutar el walk-forward de 7 pares con el contexto corregido (`C-13`)~~ | ✅ hecho (`E-07`): 0/7 → 1/7, sin cambios en el veredicto |
| P13 | ~~Ampliar el universo a 20-30 pares~~ | ✅ hecho (`E-13`): 24 pares. Sube retorno y Calmar, **no baja el DD** |
| P14 | Medir la versión mercado-neutral (largo-corto) | 🟡 abierto. Es el mecanismo estándar contra este drawdown; **no desplegable en spot** |
| P15 | ~~Tamaño del sleeve~~ | ✅ cerrado (`E-15` / `D-25`): 10 % — y sin objeto tras `E-16` |
| P16 | Automatizar la re-optimización semestral | ⚪ sin objeto (`E-16`): re-optimizar solo optimiza la fase |
| P18 | ¿Sirve el macro para decidir cuándo estar en la cesta? | ❌ **cerrado en negativo** (`E-18`): la regla a priori pierde y las que ganan no superan al azar |

---

## 12. Cómo retomar en 3 pasos

1. **Estado:**
   ```powershell
   cd C:\Users\DELL\.ipython\OpenBB
   .\venvs\openbb\Scripts\python.exe estado.py
   ```
2. **Mapa:** leer `boveda/INDICE.md` (secciones 4 y 7).
3. **Historia:** leer la última entrada de `boveda/Log de sesiones.md`. La línea de
   señales está **cerrada** (`D-31`, `D-33`): P1 no está abierto, está **cerrado en
   negativo**. Lo que queda es mantenimiento (P6, P9), un aviso externo al panel si el
   refresco falla, y —si se quiere entender— P14.

Si el paso 1 muestra un ❌ crítico, se atiende antes de cualquier otra cosa.

### Después de reiniciar o actualizar el equipo

Nada arranca solo. Las dos ventanas hay que relanzarlas:

```powershell
cd C:\Users\DELL\.ipython\OpenBB
.\run-openbb-api.ps1     # ventana 1: esperar "Uvicorn running on 127.0.0.1:6900"
.\run-openbb-app.ps1     # ventana 2: restaurar ventana 1 si se cerró
```

Luego `.\venvs\openbb\Scripts\python.exe estado.py` → debe dar **26/26 ✅**.
Si el contexto tiene más de dos días, el propio panel avisa; se refresca con
`... scripts\refrescar_contexto.py` (o se lanza la tarea programada).

> **Paciencia con la API en frío.** Después de reiniciar el equipo puede tardar
> **3-5 minutos** en escuchar en el 6900 (importa todo OpenBB desde cero: ~150 s de
> CPU y ~800 MB). No está colgada. Comprobarlo con
> `Get-NetTCPConnection -LocalPort 6900 -State Listen` o abriendo
> `http://127.0.0.1:6900/docs`. Matarla antes de tiempo solo reinicia la espera.
>
> **Los bots de Freqtrade no arrancan solos:** si `estado.py` dice
> `Puertos 8080/8081/8082: ninguno`, hay que relanzarlos desde su propio directorio.
> El panel y la API no los tocan ni los reinician.

---

*Manual mantenido junto con la memoria del proyecto. Cualquier cambio se registra
como `C-NN` y se sube a Git en la misma sesión.*
