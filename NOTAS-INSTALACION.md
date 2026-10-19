# OpenBB — Instalación local (solo localhost)

Fecha: 2026-10-19
Ruta: `C:\Users\DELL\.ipython\OpenBB\`

## Qué quedó instalado

| Elemento | Valor |
|---|---|
| Repo clonado | `repos\OpenBB` (rama `develop`, HEAD `78020ee4b86`) |
| Entorno | `venvs\openbb` — Python **3.13.12** (creado con `uv`) |
| Instalación | editable (todo el monorepo), vía `openbb_platform\dev_install.py` |
| Versión del core | OpenBB Platform **v2.0.1core** |
| Comandos disponibles | **584** |
| Providers registrados | **18** |

## Providers que funcionan SIN clave de API (verificado)

| Provider | Sirve para |
|---|---|
| `federal_reserve` | Tasas, EFFR, curvas de rendimiento, medidas monetarias (145 comandos) |
| `us_treasury` / `ustreasury` | Subastas y precios de bonos del Tesoro |
| `sec` | Fundamentales de empresas (balance, income, filings) |
| `famafrench` | Factores, retornos de portafolios |
| `cftc` | Posicionamiento COT (sentimiento) |
| `cboe` | Precios históricos de índices, cadenas de opciones |
| `oecd`, `imf` | Macro global (PIB, CPI, balanza de pagos) |
| `bls` | Inflación / empleo EE.UU. |
| `ecb` | Tipos de cambio, tasas BCE |
| `deribit` | Derivados cripto (opciones, volatilidad) |
| `jodi`, `usda`, `uscongress`, `finra`, `tmx`, `nasdaq` | Petróleo, agrícolas, congreso, bonos, Canadá, Nasdaq |

## Problemas encontrados y cómo se resolvieron

### 1. Provider `eia` rompe la instalación — Omitido
`openbb-us-eia` tiene un build hook que regenera su catálogo contra la API de EIA en vivo
y exige `EIA_API_KEY`. Sin clave, la instalación completa falla.

**Solución aplicada:** se instaló todo **excepto** `openbb_platform/providers/eia`.
Para añadirlo después hace falta una clave gratuita de https://api.eia.gov y re-ejecutar
la instalación de ese provider.

### 2. La API del BCE falla por certificados SSL (Windows)
```
SSLCertVerificationError: unable to get local issuer certificate
data-api.ecb.europa.eu:443
```
El almacén de certificados de Windows no valida esa cadena; el bundle de **certifi** sí.

**Solución aplicada:** el lanzador `run-openbb-api.ps1` exporta:
```powershell
$env:SSL_CERT_FILE       = "venvs\openbb\Lib\site-packages\certifi\cacert.pem"
$env:REQUESTS_CA_BUNDLE  = $env:SSL_CERT_FILE
```
Verificado: `currency.price.historical("EURUSD")` devuelve 7.117 filas.

### 3. `import openbb` se cuelga la primera vez
El *auto-build* (generación de assets estáticos + linters) tarda muchísimo.

**Solución aplicada:** build explícito una sola vez + `OPENBB_AUTO_BUILD=false`.

### 4. `openbb-api --help` lanza `UnicodeEncodeError`
La consola en cp1252 no puede imprimir el carácter `→` del texto de ayuda.
**Solución aplicada:** `PYTHONUTF8=1` y `PYTHONIOENCODING=utf-8` en el lanzador.

## Cómo se arranca

```powershell
cd C:\Users\DELL\.ipython\OpenBB
.\run-openbb-api.ps1          # -> http://127.0.0.1:6900
```
- Documentación interactiva: `http://127.0.0.1:6900/docs`
- Sin autenticación, escuchando **solo** en 127.0.0.1.

Uso desde Python:
```powershell
$env:OPENBB_AUTO_BUILD="false"
.\venvs\openbb\Scripts\python.exe
```
```python
from openbb import obb
obb.fixedincome.government.treasury_rates().to_df()
```

## Huecos conocidos

| Hueco | Detalle |
|---|---|
| Precios de cripto | El provider `nasdaq` no devuelve datos. **No importa:** Freqtrade ya cubre velas cripto vía ccxt 4.5.78 |
| `fred` | Requiere `fred_api_key` (gratuita). Sin ella fallan `tips_yields`, parte de `economy` |
| `eia` | No instalado (requiere clave) |
| `equity.profile` (FINRA) | Devuelve "security lookup was not readable" |
| `equity.price.historical` | Los providers estándar (FMP, Polygon, Tiingo, Intrinio) requieren clave. Sin clave, usar `index.price.historical` (cboe) |

---

# Auditoría de integridad (2026-10-19)

| Comprobación | Resultado |
|---|---|
| Dependencias (`uv pip check`) | **243 paquetes, todos compatibles** — 0 conflictos |
| Entry points (`openbb_core_extension`, `openbb_provider_extension`, `openbb_obbject_extension`) | **50 cargados, 0 con error** |
| Paquetes en modo editable | **37**, todos apuntando a `repos\OpenBB` |
| Log del servidor | 0 errores, 0 warnings |
| Tamaño en disco | `repos` 2.631 MB + `venvs` 879 MB = **~3,5 GB** |
| Espacio libre tras la instalación | 40,2 GB |

## Único elemento fuera de esta carpeta

OpenBB crea por diseño su configuración en `C:\Users\DELL\.openbb_platform\`:

```
user_settings.json    102 bytes   ({"credentials": {}, "preferences": {}, "defaults": {...}})
system_settings.json    2 bytes   ({})
```

La ruta está fija en `openbb_core/app/constants.py` (`Path.home() / ".openbb_platform"`), no hay
variable de entorno para cambiarla. **No se ha escrito nada ahí a mano**: lo creó OpenBB en su
primer arranque, y está vacío.

Si se quiere contención estricta, en los lanzadores se puede añadir
`$env:USERPROFILE = $root` antes de arrancar; `Path.home()` pasaría a resolver dentro de la carpeta.
No se ha aplicado porque afecta a la resolución de rutas de todo el proceso.

---

# Fase 4 — Utilidades locales

| Archivo | Para qué |
|---|---|
| `run-openbb-api.ps1` | Arranca la API en `127.0.0.1:6900` con SSL + sin auto-build + UTF-8 |
| `run-openbb-shell.ps1` | Consola Python con `obb` y `consultar()` ya cargados |
| `scripts\obb_env.py` | Configuración + caché local (parquet) por consulta |
| `scripts\verificar_familias.py` | Corre las 8 familias y reporta qué está cubierto |
| `notebooks\verificacion_8_familias.ipynb` | Las 8 familias, ejecutado y verificado sin errores |
| `data\cache\*.parquet` | 27 series cacheadas |
| `data\reporte_familias.txt` | Salida completa de la verificación |

## Resultado de la verificación: 28 pruebas OK, 0 errores, 2 huecos

| Familia | Estado | Fuente usada |
|---|---|---|
| 1 Técnico | ✅ completo | CBOE (S&P 500), TMX (OHLC), indicadores locales (RSI, EMA, MACD, ATR, vol. realizada) |
| 2 Fundamental | ✅ completo | SEC EDGAR (balance, income, cash) |
| 3 Macro | ✅ completo | Reserva Federal, Tesoro, OECD (CPI, PIB), BCE (EUR/USD) |
| 4 Sentimiento | ✅ completo | CFTC (COT: 853 filas), FINRA (short interest), Deribit (funding) |
| 5 Order flow | ⚠️ parcial | Deribit: libro real, ticker y cinta. Acciones nivel 2 → de pago |
| 6 On-chain | ❌ hueco | No hay provider on-chain instalado |
| 7 Cuantitativo | ✅ completo | Fama-French, `quantitative.summary`, `econometrics.ols_regression` |
| 8 Conductual | ⚠️ parcial | Estacionalidad mensual calculada sobre 13.057 sesiones |

**Dato de interés:** el único proveedor gratuito con OHLC completo es TMX (Canadá), lo que habilita
los indicadores que necesitan máximo/mínimo (ATR, volatilidad realizada). CBOE solo da cierre.

---

# Fase 5 — Puente OpenBB → Freqtrade

## Diseño

OpenBB **no reemplaza las velas**: aporta el contexto que Freqtrade no puede dar.
La estrategia técnica sigue decidiendo la entrada.

```
OpenBB (13 series)  ->  data/context/contexto_diario.parquet
                              |
                    merge_asof(direction="backward")
                              |
              velas 4h de Freqtrade + contexto macro
```

**Anti look-ahead:** cada serie se retrasa según su publicación real.

| Serie | Retraso | Motivo |
|---|---|---|
| Tasas, VIX, SPX, EUR/USD | 1 día | cierre del día anterior |
| COT | 3 días | se publica el viernes con datos del martes |
| CPI, PIB | 45 días | rezago estadístico |
| Factores Fama-French | 31 días | el retorno mensual no se conoce hasta que termina |

Además `merge_asof` con `direction="backward"`: cada vela solo puede ver el último dato
publicado **antes** de su fecha. El futuro es inalcanzable por construcción.

## Archivos

| Archivo | Para qué |
|---|---|
| `scripts\puente_freqtrade.py` | Exporta el contexto (`--exportar`), muestra estado vivo (`--estado`) y fusiona velas |
| `data\context\contexto_diario.parquet` | 36.636 filas × 13 columnas (1926 → 2026) |
| `strategies\StrategyContextoOpenBB.py` | Ejemplo: cruce EMA 20/50 + filtro macro |
| `strategies\StrategyContextoOpenBBSinMacro.py` | Grupo de control, sin filtro |
| `freqtrade_bridge\backtest.json` | Config de backtest apuntando a nuestra carpeta |
| `freqtrade_bridge\user_data\data\binance\` | Copia de 7 pares 4h (2,6 MB), solo lectura del original |

## Resultado del backtest (2021-01-01 → 2026-10-17, Binance spot 4h)

| Estrategia | Trades | Total | Drawdown | Win% |
|---|---|---|---|---|
| Con filtro macro | 1.464 | **−49,44%** | 60,13% | 52,4% |
| Sin filtro macro | 2.349 | −28,60% | 45,56% | 52,9% |

**Corrección importante:** la primera medición daba −9,81% vs −11,16% porque
`treasury_rates` devolvía por defecto **solo 1 año**. Con el histórico completo
(`start_date="2000-01-01"`) el filtro macro **empeora** el resultado: menos operaciones
pero peores. La comparación anterior era un artefacto de datos incompletos.

**Lectura honesta:** el filtro macro no aporta alfa; el cruce de medias tampoco.
Esto es justamente el punto del método: **el backtest no confirma una idea, la desmiente**.

---

## Cómo usarlo en tus propias estrategias

```python
import sys
sys.path.insert(0, r"C:\Users\DELL\.ipython\OpenBB\scripts")
from puente_freqtrade import fusionar

def populate_indicators(self, dataframe, metadata):
    dataframe = fusionar(dataframe)   # añade 13 columnas de contexto
    ...
```

Columnas disponibles: `yield_2y`, `yield_10y`, `slope_10y_2y`, `fed_funds`, `vix`, `spx`,
`eurusd`, `cpi_yoy`, `gdp_yoy`, `cot_net`, `ff_mkt_rf`, `ff_smb`, `ff_hml`.

**Refresco:** el contexto se congela al exportarlo. Para actualizarlo:
```powershell
.\venvs\openbb\Scripts\python.exe scripts\puente_freqtrade.py --exportar
```

## Advertencia sobre el Freqtrade en marcha

Hay **7 instancias corriendo** (trade + webservers en 8080/8081). No se escribió **nada** en
`C:\Users\DELL\.ipython\freqtrade\`:

- El backtest usó `user_data_dir` **propio**, dentro de esta carpeta.
- Los 7 feather se **copiaron** desde su carpeta (lectura), no se movieron.
- Verificado: `backtest_results` y `logs` de tu Freqtrade siguen con fecha del 16/10.

Para usar la estrategia en tus bots: copiar `strategies\*.py` a su `user_data\strategies\`
**con los bots detenidos**, o añadir esta carpeta a `strategy_path` en el config correspondiente.

---

# Fase 6 — Validación walk-forward + Monte Carlo

## Por qué antes de integrar

Un backtest único sobre todo el periodo es una ilusión: los parámetros se eligen
mirando el resultado que se quiere obtener. La validación separa entrenamiento de prueba.

## Método

| Pieza | Regla |
|---|---|
| Walk-forward | 18 meses de entrenamiento → 6 meses de prueba, avanzando de 6 en 6 |
| Grilla | EMA rápida {10,20,30} × lenta {50,80,100} × VIX máx {18,25,32} × filtro de curva {sí,no} |
| Selección | Mejor retorno **en entrenamiento**, evaluado **solo** en la ventana siguiente |
| Monte Carlo | 5.000 remuestreos de las operaciones fuera de muestra |
| Sizing | 10% del capital por operación (igual que el bot) |

## Resultado multi-activo (2021-01 → 2026-10, 7 pares)

| Par | OOS | Exposición | Ventanas+ | Acierto | P(pérdida) | Referencia misma exposición |
|---|---|---|---|---|---|---|
| ADA | +3,2% | 35,0% | 5/11 | 31,9% | 43,2% | +5,7% |
| AVAX | +18,9% | 29,5% | 4/11 | 36,2% | 14,6% | +31,9% |
| BNB | +5,2% | 40,7% | 5/11 | 33,0% | 34,4% | +236,3% |
| BTC | +7,6% | 43,8% | 6/11 | 33,3% | 20,6% | +56,7% |
| ETH | +14,1% | 45,6% | 8/11 | 32,2% | 13,0% | +71,3% |
| SOL | +9,0% | 29,4% | 5/11 | 34,4% | 25,4% | +242,0% |
| XRP | +4,2% | 26,5% | 3/11 | 33,1% | 36,0% | +58,9% |

**7 de 7 positivos. 0 de 7 baten la referencia.** En todos los casos, estar invertido
el mismo porcentaje del tiempo en el propio activo habría rendido más.

El 7/7 positivo no es habilidad: es beta de cripto con 10% de sizing. La prueba real
—batir la referencia ajustada por exposición— la falla en los siete.

## Veredicto

```
SIN ventaja consistente entre activos.
El cruce EMA 20/50 no es una base sobre la que integrar el bot.
```

**No integrar todavía.** El puente funciona; la estrategia de ejemplo no tiene alfa.
Integrar ahora sería automatizar una pérdida.

## Qué haría falta para integrar

1. Un gatillo con ventaja **fuera de muestra** en ≥2/3 de los activos.
2. Que esa ventaja bata la referencia ajustada por exposición, no solo que sea positiva.
3. Que sobreviva al Monte Carlo con P(pérdida) < 25% y drawdown p95 < 20%.
4. Recién entonces: dry-run con capital simulado, no real.

## Reproducir

```powershell
# un par, detallado
.\venvs\openbb\Scripts\python.exe scripts\validar_estrategia.py --pair BTC_USDT --stake 0.1

# todos los pares
.\venvs\openbb\Scripts\python.exe scripts\validar_estrategia.py --todos --stake 0.1
```

Salida guardada en `data\reporte_validacion.txt`.
