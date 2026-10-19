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
│   ├── puente_freqtrade.py    Exportar contexto / fusionar velas
│   ├── validar_estrategia.py  Walk-forward + Monte Carlo
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
- 7 pestañas: Resumen, Tipos, Riesgo, Macro, Posicionamiento, Contexto Freqtrade, API.
- 100 % local: no usa nube ni login.
- Cambiar puerto: `.\run-openbb-app.ps1 -Port 8502`
- Detener: `Ctrl+C` en su ventana.

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
| `git push` rechazado | Remoto adelantado | `git pull --rebase` y reintentar |
| `estado.py` marca ❌ Repo | Cambios sin commit | `git add -A && git commit && git push` |

**Regla de dos strikes:** si la API se cuelga dos veces en la misma sesión, no
relanzar una tercera. Anotar el síntoma y los logs.

---

## 9. Datos y configuración

### 9.1 Contexto diario (13 columnas)

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

### Resultado de la validación (2021-01 → 2026-10)

| Par | OOS | Referencia misma exposición |
|---|---|---|
| ADA | +3,2% | +5,7% |
| AVAX | +18,9% | +31,9% |
| BNB | +5,2% | +236,3% |
| BTC | +7,6% | +56,7% |
| ETH | +14,1% | +71,3% |
| SOL | +9,0% | +242,0% |
| XRP | +4,2% | +58,9% |

**7/7 positivos, 0/7 baten la referencia.** El cruce EMA 20/50 no tiene alfa.

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

---

*Manual mantenido junto con la memoria del proyecto. Cualquier cambio se registra
como `C-NN` y se sube a Git en la misma sesión.*
