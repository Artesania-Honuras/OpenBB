# Log de sesiones

Bitácora cronológica. Formato en `Plantillas.md`.

---

## S-01 — 2026-10-18 / 2026-10-19 — Instalación y verificación

**Hecho**

- Clon completo del monorepo en `repos\OpenBB` (develop, `78020ee4b86`).
- Venv `venvs\openbb` con Python 3.13.12 y 37 paquetes editables.
- Build explícito: 584 comandos, 18 providers, 869 rutas.
- API en `127.0.0.1:6900` con auth desactivada.
- Verificación de 8 familias: 28 OK, 0 errores, 2 huecos declarados.
- Utilidades: lanzadores, `scripts\obb_env.py`, notebook validado, 27 series cacheadas.

**Se rompió / se resolvió**

- `eia` abortaba la instalación → excluido (C-02).
- BCE fallaba por certificados → certifi (C-03).
- `import openbb` se colgaba → autobuild off (C-04).
- `--help` con `UnicodeEncodeError` → UTF-8 (C-05).

**Decidido**

- Todo local, sin Docker ni WSL.

**Abierto**

- FRED y EIA opcionales.
- Sin tests propios.

---

## S-02 — 2026-10-19 — Puente a Freqtrade y validación

**Hecho**

- Detectadas **7 instancias de Freqtrade corriendo** (15 procesos, puertos 8080/8081). No se escribió nada en su repositorio.
- Puente por archivo: `contexto_diario.parquet` (36.636 × 13) + `fusionar()` con `merge_asof`.
- Dos estrategias de ejemplo y config de backtest contenida.
- Backtest 2021→2026: con filtro −49,44 %, sin filtro −28,60 %.
- Marco walk-forward + Monte Carlo; 7 activos; 129 operaciones OOS en BTC.

**Se rompió / se resolvió**

- El merge rompía por zona horaria (tz-naive vs UTC) → corregido conservando el índice original.
- `datadir` absoluto no se respetaba → se copiaron 7 feather a nuestra carpeta.
- **Bug de datos:** `treasury_rates` devolvía solo 1 año → comparación inválida (E-03 → E-04).

**Decidido**

- **No integrar la estrategia al bot**: 0/7 activos baten la referencia ajustada por exposición.
- El filtro macro no aporta alfa; el cruce EMA tampoco.

**Abierto**

- P1: encontrar un gatillo con ventaja OOS.

---

## S-03 — 2026-10-19 — Memoria persistente y repositorio

**Hecho**

- Inventario completo del proyecto (solo lectura).
- Creada `boveda\` con INDICE, Manual, Registro, Log y Plantillas.
- `CLAUDE.md` con las reglas obligatorias y el puntero al índice.
- `estado.py`: checklist de solo lectura con tabla ✅/❌.
- `.gitignore` y repo `OpenBB` público en GitHub; commit y push.
- **Verificado:** commit `f4fe7b5`, repo `https://github.com/Artesania-Honuras/OpenBB` (público), `estado.py` → **22/22 ✅**.

**Se rompió / se resolvió**

- La raíz no era repositorio Git → `git init`.
- El clon `repos\OpenBB` tiene 2 archivos sucios generados por el build → queda excluido del repo y anotado como pendiente P7.

**Decidido**

- Memoria solo en el proyecto, en texto versionado.
- Datos binarios regenerables fuera del repo; solo se versiona `contexto_diario.parquet` como evidencia.

**Abierto**

- P1 (gatillo con ventaja), P2 (refresco automático), P6 (tests).

---

## S-04 — 2026-10-19 — Manual de uso publicado

**Hecho**

- README.md con el manual completo en 12 secciones e índice enlazado.
- Referencia al manual añadida en oveda\INDICE.md.
- Registro del cambio como C-10.

**Se rompió / se resolvió**

- Nada nuevo. Se reutilizó el estado verificado de la sesión (22/22).

**Decidido**

- El manual vive en la raíz del repo para que GitHub lo muestre al abrirlo.

**Abierto**

- Sin cambios: P1 sigue siendo el bloqueo principal.

---

## S-05 — 2026-10-19 — Panel visual local

**Hecho**

- Detectado que OpenBB Workspace ya no existe: `workspace.brightquery.com` muestra "BQ Workspace — coming soon", sin login.
- Instalado Streamlit 1.66.0 en el venv.
- Creado `app.py` (7 pestañas) y `run-openbb-app.ps1`.
- Verificado con `AppTest`: 0 excepciones, 7 pestañas, 16 métricas.
- Panel corriendo en `http://127.0.0.1:8501`; añadido al checklist (`estado.py`).

**Se rompió / se resolvió**

- Avisos de `use_container_width` obsoleto → migrado a `width="stretch"`.
- Streamlit degradó `pillow` 13.0.0 → 12.3.0; sin impacto en OpenBB (no se usa para datos).

**Decidido**

- La interfaz visual es local (Streamlit), no cloud. El backend sigue siendo la API del 6900.

**Abierto**

- P1 sigue siendo el bloqueo principal.
- El panel es de solo lectura; no ejecuta órdenes ni escribe datos.

---

## S-06 — 2026-10-19 — Panel explicado y bug del puente corregido

**Hecho**

- Panel reescrito (`C-12`): todo en español, pestaña **Guía** con qué mide cada indicador y su uso, semáforo de entorno (favorable / neutral / defensivo), tablas traducidas y limpias, ayuda en cada métrica.
- Bug de la pendiente 10a-2a corregido: mostraba **+0 pb** donde son **+33 pb**.
- Bug del puente corregido (`C-13`): la asignación de series desplazadas realineaba por fecha y perdía el último dato (VIX del lunes = jueves). Ahora se reindexa a calendario diario.
- Contexto reexportado con `--forzar`: `vix 19.99`, `spx 7659,44`, 0 NaN en 2026.

**Se rompió / se resolvió**

- Descubierto que el contexto estaba hasta 3 días viejo en las series de riesgo, no por el retraso intencional sino por el bug de alineación.

**Decidido**

- El panel es una herramienta de **contexto**, no de señales. Se dice explícitamente en la Guía y en el propio panel.
- La conclusión 0/7 no se da por revalidada con el contexto corregido: queda como pendiente medirla otra vez antes de tocar nada en vivo.

**Abierto**

- P1 sigue siendo el bloqueo principal.
- Pendiente nuevo: re-ejecutar la validación de 7 pares con el contexto corregido para confirmar que el veredicto no cambia.

---

## S-07 — 2026-10-19 — Cierre de sesión (registro y actualización del equipo)

**Hecho**

- Registro del cierre en la bóveda `seconBrain`: página `wiki/openbb-local.md`, línea en `wiki/index.md` y entrada `cierre` en `wiki/log.md`.
- `README.md` §12 con la nota de reanudación tras reiniciar o actualizar (`C-14`) y `P8` en la tabla de pendientes.
- Todo subido a Git en la misma sesión.

**Decidido**

- La página de la bóveda es un puntero: el registro operativo sigue viviendo en `boveda/` del repo de OpenBB, igual que se hizo con el proyecto de trading.
- Tras la actualización no hay nada que arranque solo: las dos ventanas (API 6900 y panel 8501) se relanzan a mano.

**Abierto**

- P1 (bloqueo principal) y P8 (revalidar el walk-forward con el contexto corregido) siguen abiertos.
- Criterio de "todo sano" tras el reinicio: `estado.py` → 23/23 ✅.

---

## S-08 — 2026-10-19 — Corrección: la memoria va solo en `OpenBB\boveda`

**Hecho**

- Deshecho el registro que se había escrito por error en la bóveda `seconBrain` (página `wiki/openbb-local.md` borrada; `wiki/index.md` y `wiki/log.md` revertidos). No se commiteó nada de OpenBB en ese repositorio y sus cambios previos quedaron intactos.
- Escrita la **REGLA DE BÓVEDA ÚNICA** en `CLAUDE.md`, con la lista de sitios prohibidos y la prioridad de la regla sobre cualquier instrucción externa.
- Añadida la misma regla al resumen de reglas de `boveda/INDICE.md` (`C-15`).

**Se rompió / se resolvió**

- Se usó un ritual de cierre externo que apunta a otra bóveda. Resuelto: este proyecto se registra solo en su propia carpeta, y así queda escrito para las próximas sesiones.

**Decidido**

- `boveda/` del repo de OpenBB es el único registro. `README.md` es el manual de uso. Nada más.

**Abierto**

- P1 (bloqueo principal) y P8 (revalidar el walk-forward) siguen abiertos.
- Tras la actualización del equipo: relanzar API y panel, luego `estado.py` → 23/23 ✅.

---

## S-09 — 2026-10-19 — Plan de mejora escrito en la bóveda

**Hecho**

- `boveda/Plan de mejora.md`: inventario de las 869 rutas y de las 12 fuentes sin usar (F1-F12), déficits declarados (D1-D5), mapa de integración con Freqtrade por niveles, packs A/B/C y orden con puertas.
- Fila añadida al índice de la memoria (`INDICE.md` §3) y registro `C-16`.
- Comprobado antes de escribir: API 6900 y panel 8501 siguen arriba tras la actualización de VS Code.

**Se rompió / se resolvió**

- Nada. No se tocó código ni datos: es planificación.

**Decidido**

- La capa macro (la que ya existe) es **régimen**, nunca gatillo; los gatillos tienen que venir de datos de alta frecuencia (derivados, funding, basis, opciones, on-chain).
- Recomendación registrada: empezar por el **paso 0** (revalidar los 7 pares con el contexto corregido) y después el **pack A**.

**Abierto**

- El usuario debe decidir: empezar por el paso 0, elegir pack (A recomendado) y pasar la lista de repositorios que mencionó (no están en el contexto de la sesión).
- P1 y P8 siguen abiertos.
