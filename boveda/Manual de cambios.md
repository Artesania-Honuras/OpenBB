# Manual de cambios

Cada cambio aplicado tiene una entrada `C-NN`. Formato en `Plantillas.md`.
Un cambio sin evidencia numérica no entra aquí: es una hipótesis.

---

## C-01 — Instalación editable del monorepo con uv

- **Fecha:** 2026-10-19
- **Qué:** venv `venvs\openbb` con Python 3.13.12 y 37 paquetes instalados en modo editable desde `repos\OpenBB`, usando `openbb_platform\dev_install.py --routers`.
- **Por qué:** correr todo desde el código fuente y en local, sin depender del paquete publicado ni de servicios cloud.
- **Evidencia:** `uv pip check` → 243 paquetes compatibles, 0 conflictos; build reporta 584 comandos, 18 providers.
- **Reversión:** borrar `venvs\openbb` y recrear con `uv venv --python 3.13` + el instalador.

---

## C-02 — Excluir el provider `eia`

- **Fecha:** 2026-10-19
- **Qué:** el provider `eia` no se instala.
- **Por qué:** su `hatch_build.py` regenera un catálogo contra la API en vivo y falla sin `EIA_API_KEY`, abortando toda la instalación.
- **Evidencia:** la instalación completa termina correctamente al excluirlo.
- **Reversión:** instalarlo con `EIA_API_KEY` disponible y reconstruir.

---

## C-03 — Forzar SSL a certifi

- **Fecha:** 2026-10-19
- **Qué:** `SSL_CERT_FILE` y `REQUESTS_CA_BUNDLE` apuntan a `venvs\openbb\Lib\site-packages\certifi\cacert.pem` en los lanzadores.
- **Por qué:** el almacén de certificados de Windows falla contra `data-api.ecb.europa.eu`.
- **Evidencia:** `EURUSD` por `ecb` devuelve 7.117 filas (antes fallaba).
- **Reversión:** quitar las dos variables de `run-openbb-api.ps1` y `run-openbb-shell.ps1`.

---

## C-04 — `OPENBB_AUTO_BUILD=false`

- **Fecha:** 2026-10-19
- **Qué:** se desactiva el autobuild permanente; el build se ejecutó una sola vez de forma explícita.
- **Por qué:** `import openbb` se colgaba durante el auto-build en este equipo.
- **Evidencia:** arranque de la API en ~60 s, sin cuelgues; 50 entry points cargan con 0 errores.
- **Reversión:** quitar la variable del entorno (volverá a intentar autobuild).

---

## C-05 — UTF-8 forzado

- **Fecha:** 2026-10-19
- **Qué:** `PYTHONUTF8=1` y `PYTHONIOENCODING=utf-8` en los lanzadores.
- **Por qué:** `openbb-api --help` lanzaba `UnicodeEncodeError` con cp1252.
- **Evidencia:** ayuda y consola sin errores de codificación.
- **Reversión:** quitar ambas variables.

---

## C-06 — Puente OpenBB → Freqtrade

- **Fecha:** 2026-10-19
- **Qué:** `scripts\puente_freqtrade.py` (exportar/fusionar), dos estrategias de ejemplo y `freqtrade_bridge\backtest.json`.
- **Por qué:** aportar contexto macro a Freqtrade sin tocar los bots en marcha (7 instancias activas).
- **Evidencia:** contexto de 36.636 filas × 13 columnas; merge con 14.886 velas 4h; 0 NaN en 2026.
- **Reversión:** borrar los tres artefactos. No afecta a Freqtrade: nada se escribió en su repositorio.

---

## C-07 — Histórico completo en `treasury_rates` y `effr`

- **Fecha:** 2026-10-19
- **Qué:** `start_date="2000-01-01"` en ambas consultas.
- **Por qué:** el valor por defecto devolvía **solo 1 año**, dejando el filtro macro inactivo casi todo el periodo y falseando la comparación (E-03).
- **Evidencia:** de 248 a 6.700 filas; cobertura del 100 % desde 2021.
- **Reversión:** quitar el parámetro (vuelve al default de 1 año).

---

## C-08 — Marco de validación walk-forward + Monte Carlo

- **Fecha:** 2026-10-19
- **Qué:** `scripts\validar_estrategia.py` con `--pair`, `--todos` y `--stake`; reporta exposición, ventanas positivas, Monte Carlo y referencia ajustada.
- **Por qué:** un backtest único elige parámetros mirando el resultado; hay que separar entrenamiento de prueba.
- **Evidencia:** 11 ventanas, 129 operaciones fuera de muestra en BTC; 7/7 activos positivos y **0/7** baten la referencia.
- **Reversión:** borrar el script; no altera datos ni configuración.

---

## C-09 — Memoria persistente y repositorio Git

- **Fecha:** 2026-10-19
- **Qué:** `boveda\` con 5 archivos, `CLAUDE.md` con reglas, `estado.py` (checklist de solo lectura), `.gitignore`, repo `OpenBB` público en GitHub.
- **Por qué:** memoria auditable dentro del propio proyecto, versionada, sin dependencias de terceros.
- **Evidencia:** repo público `https://github.com/Artesania-Honuras/OpenBB`, commit inicial `f4fe7b5` con 22 archivos (0,6 MB); `estado.py` → 22/22 chequeos ✅.
- **Reversión:** `git revert` del commit de memoria o borrar `boveda\` y `CLAUDE.md`.
