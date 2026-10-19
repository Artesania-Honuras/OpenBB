# INDICE — Memoria del proyecto OpenBB local

> Última actualización: 2026-10-19 · Sesión S-03
> Este archivo es lo primero que debe leer cualquier sesión nueva.

---

## 1. Qué es este proyecto

Instalación **local** de OpenBB Platform desde el código fuente (clon del monorepo),
con una API en `127.0.0.1:6900` y un **puente de contexto macro hacia Freqtrade**
(que vive fuera, en `C:\Users\DELL\.ipython\freqtrade`).

Objetivo: que OpenBB aporte el contexto (macro, riesgo, posicionamiento, factores)
y Freqtrade decida la entrada técnica y ejecute. Nada sale a la nube salvo las
peticiones de datos públicos a los proveedores.

---

## 2. Reglas vigentes

Están en `CLAUDE.md`, al inicio. Resumen:

| Regla | Qué exige |
|---|---|
| Registro | Todo cambio `C-NN`, todo experimento `E-NN`, toda sesión en el Log, commit + push en la misma sesión |
| Cambios | Medición reproducible + validación fuera de muestra + registro + despliegue verificado |
| Estado | "¿Está todo al 100%?" → ejecutar `estado.py` y pegar la tabla ✅/❌ completa |
| Trabajo | Ubicar la entrada antes de tocar; misma herramienta y condiciones; secretos fuera; lo no verificable es pendiente |

---

## 3. Qué contiene esta memoria

| Archivo | Para qué |
|---|---|
| `INDICE.md` | Este mapa: estado, decisiones, criterios, pendientes, cómo retomar |
| `Manual de cambios.md` | Una entrada `C-NN` por cambio: qué, por qué, evidencia, cómo revertir |
| `Registro de resultados.md` | Una fila `E-NN` por experimento: hipótesis, método, números, veredicto |
| `Log de sesiones.md` | Bitácora: qué se hizo, qué se rompió, qué se decidió, qué quedó abierto |
| `Plantillas.md` | Formatos vacíos para que el registro sea consistente |

---

## 4. Estado actual — decisiones vivas con evidencia

| ID | Decisión | Evidencia | Fecha |
|---|---|---|---|
| D-01 | Python 3.13.12 + venv editable en `venvs\openbb` | 37 paquetes editables, `uv pip check` 243/0 conflictos | 2026-10-19 |
| D-02 | API solo loopback `127.0.0.1:6900`, auth desactivada | HTTP 200, 869 rutas OpenAPI | 2026-10-19 |
| D-03 | Provider `eia` excluido | Su build hook exige `EIA_API_KEY` en vivo y aborta la instalación | 2026-10-19 |
| D-04 | SSL forzado a certifi | `EURUSD` vía BCE devuelve 7.117 filas | 2026-10-19 |
| D-05 | `OPENBB_AUTO_BUILD=false` | Arranque ~60 s sin cuelgues | 2026-10-19 |
| D-06 | Contexto diario con retrasos de publicación | 36.636 filas × 13 columnas, 1926→2026, 0 NaN en 2026 | 2026-10-19 |
| D-07 | Puente por archivo (parquet), no por HTTP | Merge con 14.886 velas 4h sin look-ahead | 2026-10-19 |
| D-08 | **No integrar** la estrategia al bot | Walk-forward: 7/7 OOS positivos, **0/7** baten la referencia ajustada por exposición | 2026-10-19 |

### Capacidades verificadas

- 584 comandos, 18 providers, 869 rutas HTTP.
- 28 pruebas OK, 0 errores, 2 huecos declarados (order flow de equities nivel 2; on-chain).
- Proveedores sin clave que funcionan: `federal_reserve`, `us_treasury`, `sec`,
  `famafrench`, `cftc`, `cboe`, `oecd`, `imf`, `bls`, `ecb`, `deribit`, `jodi`,
  `usda`, `uscongress`, `finra`, `tmx`, `nasdaq`.

### Límites conocidos

- `obb.crypto.price.historical` devuelve vacío → las velas cripto vienen de ccxt/Freqtrade.
- `equity.profile` falla ("FINRA security lookup was not readable").
- Sin `fred_api_key` faltan `tips_yields` y parte de `economy`.
- Sin `EIA_API_KEY` no hay provider `eia`.
- El contexto se refresca **a mano**; no hay tarea programada.

---

## 5. Herramientas fuente de verdad

| Ámbito | Fuente | Nota |
|---|---|---|
| Código | `scripts\`, `strategies\` | Lo que corre |
| Contexto | `data\context\contexto_diario.parquet` | Evidencia del puente; 13 columnas |
| Medición | `scripts\validar_estrategia.py` | La misma herramienta siempre |
| Estado | `estado.py` | Solo lectura, tabla ✅/❌ |
| Historia | `boveda\*` | Cambios, resultados, sesiones |
| Upstream | `repos\OpenBB` @ `78020ee4b86` (develop) | Referencia, no se edita |
| Config de backtest | `freqtrade_bridge\backtest.json` | Sin claves |

---

## 6. Criterios de aceptación

### Del proyecto (infraestructura)

1. API local responde 200 y una llamada funcional en < 60 s.
2. Contexto con 13 columnas y sin NaN desde 2021.
3. `estado.py` sin ❌ críticos.
4. Repo limpio y pusheado.
5. Cualquier cambio nuevo tiene `C-NN` y su evidencia.

### De una estrategia (compuerta de integración)

No se integra ninguna estrategia al bot si no cumple **las cuatro**:

1. Ventaja fuera de muestra en **≥ 2/3** de los activos.
2. Bate la **referencia ajustada por exposición** (no solo ser positivo).
3. Monte Carlo con **P(pérdida) < 25%** y **drawdown p95 < 20%**.
4. Supervivencia en ≥ 60% de las ventanas walk-forward.

Hoy **ninguna** la cumple.

---

## 7. Pendientes priorizados

| Prioridad | Pendiente | Estado |
|---|---|---|
| P1 | Encontrar un gatillo con ventaja OOS real | 🔴 abierto — es el bloqueo principal |
| P2 | Refresco programado del contexto (hoy manual) | 🟡 abierto |
| P3 | Instalar la estrategia en los bots de Freqtrade | 🔴 bloqueado por P1 |
| P4 | Clave FRED gratuita (`fred_api_key`) para `tips_yields` | 🟡 opcional |
| P5 | Provider `eia` con `EIA_API_KEY` | 🟡 opcional |
| P6 | Tests propios (hoy solo verificación funcional) | 🟡 abierto |
| P7 | Revisar los 2 archivos sucios del clon upstream | 🟢 menor |

---

## 8. Cómo retomar en 3 pasos

1. **Estado:** `.\venvs\openbb\Scripts\python.exe estado.py` → leer la tabla.
2. **Contexto:** leer este INDICE (secciones 4 y 7) para saber qué está vivo y qué falta.
3. **Historia:** leer la última entrada de `Log de sesiones.md` y continuar por el pendiente P1.

> Si el paso 1 muestra un ❌ crítico, se atiende antes de cualquier otra cosa.
