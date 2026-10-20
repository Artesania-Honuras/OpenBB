"""¿Mejora el Calmar de la cesta si solo se está invertido con régimen macro favorable?

La pregunta
-----------
Todo lo medido hasta ahora intentaba encontrar una regla de selección. Esta es
otra cosa: **no elegir pares, sino decidir cuándo estar dentro**. La cesta a peso
igual de los 24 pares es la referencia (Calmar 4,52, DD -81,9 %). Si el contexto
macro sirve para algo, debería mejorar el Calmar **sin cambiar la cesta**.

Dos protecciones obligatorias
-----------------------------
1. **Lag.** El VIX del día d se conoce al cierre de d (21:00 UTC). Usarlo a las
   00:00 de d es mirar el futuro. La señal se desplaza `lag` días (1 por defecto;
   se mide también 2, que es lo que tarda FRED en publicar los rendimientos).
2. **Contraste con el mismo patrón.** Un filtro que te saca del mercado el 30 %
   del tiempo **baja el DD aunque no sepa nada**: es diversificación temporal,
   no información. El control es la MISMA serie de entradas/salidas desplazada
   circularmente en el tiempo: mismo número de días dentro, mismos cambios,
   otras fechas. Si la regla macro no supera esa nube, no aporta.

La regla es la de `E-07`, elegida antes de medir: `VIX < 25` y `pendiente 10a-2a > 0`.
Los umbrales se prueban como **sensibilidad declarada**, no como búsqueda.

Uso:
    python scripts\\validar_macro_cesta.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validar_momentum import FEE, calmar, cargar_matriz, compuesto, max_dd  # noqa: E402

INICIO, FIN = "2021-01-01", "2026-10-01"
CONTEXTO = ROOT / "data" / "context" / "contexto_diario.parquet"
SIMULACIONES = 500


def universo() -> list[str]:
    velas = ROOT / "freqtrade_bridge" / "user_data" / "data" / "binance"
    return sorted(p.name.replace("-4h.feather", "") for p in velas.glob("*-4h.feather"))


def cesta_diaria() -> pd.Series:
    """Retorno diario de la cesta a peso igual (24 pares)."""
    m = cargar_matriz(universo())
    diario = m.resample("1D").last().ffill()
    return diario.pct_change().mean(axis=1).fillna(0.0)


def regimen(contexto: pd.DataFrame, indice: pd.DatetimeIndex,
            vix: float, pendiente: bool, lag: int) -> pd.Series:
    """Booleano por día: se puede estar invertido.

    `lag` desplaza la señal hacia atrás: la posición del día d se decide con el
    dato de d-lag, que es el último publicado.
    """
    c = contexto.copy()
    idx = pd.DatetimeIndex(c.index)
    if idx.tz is None:  # el parquet guarda fechas naive; las velas son UTC
        idx = idx.tz_localize("UTC")
    c = c.set_axis(idx).reindex(indice).ffill()
    ok = c["vix"] < vix
    if pendiente:
        ok &= c["slope_10y_2y"] > 0
    pos = ok.shift(int(lag))
    return pos.fillna(False).astype(bool)


def simular(r_cesta: pd.Series, pos: pd.Series) -> dict:
    """Cesta dentro/caja según `pos`, con coste 0,1 % por cambio de estado."""
    p = pos.astype(float)
    cambios = p.diff().abs().fillna(0.0)
    r = p * r_cesta - FEE * cambios
    eq = (1 + r).cumprod()
    dias = (r_cesta.index[-1] - r_cesta.index[0]).days
    return {
        "ret_%": compuesto(r.to_numpy()) * 100,
        "dd_%": max_dd(r.to_numpy()) * 100,
        "calmar": calmar(r.to_numpy()),
        "cagr_%": ((1 + compuesto(r.to_numpy())) ** (1 / max(dias / 365.25, 1e-9)) - 1) * 100,
        "en_mercado_%": p.mean() * 100,
        "cambios": int(cambios.sum()),
    }


def nube(r_cesta: pd.Series, pos: pd.Series, sims: int, semilla: int = 7) -> np.ndarray:
    """Misma serie de posiciones, desplazada circularmente: mismas fechas dentro, otras."""
    rng = np.random.default_rng(semilla)
    p = pos.to_numpy()
    n = len(p)
    vals = np.empty(sims)
    for s in range(sims):
        k = int(rng.integers(1, n))
        pr = np.roll(p, k)
        # Sin coste en el punto de corte: el desplazamiento es circular, no una entrada.
        cambios = np.abs(np.diff(pr, prepend=pr[0]))
        vals[s] = calmar(pr * r_cesta.to_numpy() - FEE * cambios)
    return vals


def main() -> None:
    lineas: list[str] = []

    def out(texto: str = "") -> None:
        print(texto)
        lineas.append(texto)

    r_cesta = cesta_diaria()
    r_cesta = r_cesta[(r_cesta.index >= pd.Timestamp(INICIO, tz="UTC"))
                      & (r_cesta.index < pd.Timestamp(FIN, tz="UTC"))]
    contexto = pd.read_parquet(CONTEXTO)

    base = simular(r_cesta, pd.Series(True, index=r_cesta.index))
    out("=" * 100)
    out(f"MACRO SOBRE LA CESTA — 24 pares, {INICIO} -> {FIN}, {len(r_cesta)} dias")
    out("=" * 100)
    out(f"cesta a peso igual: {base['ret_%']:+.1f}%  DD {base['dd_%']:.1f}%  "
        f"Calmar {base['calmar']:.2f}  CAGR {base['cagr_%']:+.1f}%")
    out("")

    # --- Sensibilidad declarada (no busqueda) -----------------------------
    out("### VARIANTES (umbrales fijados antes de medir; el lag 1 es el realista)")
    out(f"{'variante':<34} {'ret_%':>10} {'dd_%':>8} {'calmar':>8} {'cagr_%':>8} "
        f"{'dentro_%':>9} {'cambios':>8}")
    filas = []
    for lag in (1, 2):
        for vix in (20.0, 25.0, 30.0):
            for pendiente in (True, False):
                nombre = f"VIX<{vix:.0f}" + (" + pendiente>0" if pendiente else "") + f" · lag {lag}"
                pos = regimen(contexto, r_cesta.index, vix, pendiente, lag)
                r = simular(r_cesta, pos)
                filas.append({"variante": nombre, **r, "_pos": pos})
                out(f"{nombre:<34} {r['ret_%']:>+10.1f} {r['dd_%']:>8.1f} "
                    f"{r['calmar']:>8.2f} {r['cagr_%']:>+8.1f} "
                    f"{r['en_mercado_%']:>8.1f}% {r['cambios']:>8d}")
    out("")

    # --- El contraste que decide ------------------------------------------
    # Se contrasta la regla PRE-REGISTRADA y, ademas, TODA variante que bata a
    # la cesta: si gana la mejor de 12, tiene que pasar el mismo examen que la
    # pre-registrada. De lo contrario se estaria eligiendo despues de ver.
    principal = next(f for f in filas if f["variante"].startswith("VIX<25 + pendiente>0 · lag 1"))
    out("### CONTRASTE — mismo patrón de entradas/salidas, fechas al azar")
    out(f"  {SIMULACIONES} desplazamientos circulares de la MISMA serie de posiciones")
    out(f"  (mismos cambios, mismo tiempo dentro; solo cambian las fechas)")
    out("")

    def contraste(f: dict) -> tuple[np.ndarray, float]:
        n = nube(r_cesta, f["_pos"], SIMULACIONES)
        return n, float((n < f["calmar"]).mean() * 100)

    n_pri, pct_pri = contraste(principal)
    out(f"  {principal['variante']}")
    out(f"    Calmar {principal['calmar']:.2f} · nube p5 {np.percentile(n_pri, 5):.2f} · "
        f"p50 {np.percentile(n_pri, 50):.2f} · p95 {np.percentile(n_pri, 95):.2f} · "
        f"max {n_pri.max():.2f}")
    out(f"    percentil {pct_pri:.0f} · P(azar >= regla) "
        f"{float((n_pri >= principal['calmar']).mean() * 100):.1f} %")
    out("")

    ganadoras = [f for f in filas if f["calmar"] > base["calmar"]]
    out(f"  Variantes que baten a la cesta en Calmar: {len(ganadoras)} de {len(filas)}")
    detalle = []
    for f in ganadoras:
        n, pct = contraste(f)
        p = float((n >= f["calmar"]).mean() * 100)
        detalle.append((f, pct, p))
        out(f"    {f['variante']:<34} Calmar {f['calmar']:.2f} · percentil {pct:>3.0f} · "
            f"P(azar>=) {p:>4.1f} % · {'✅' if pct >= 95 else '❌'}")
    out("")

    # --- Inversa: si el signo fuera casualidad -----------------------------
    inv = simular(r_cesta, ~principal["_pos"])
    out("### CONTROL DE SIGNO — la regla invertida (dentro cuando el régimen es MALO)")
    out(f"  retorno {inv['ret_%']:+.1f}%  DD {inv['dd_%']:.1f}%  Calmar {inv['calmar']:.2f}")
    out("")

    # --- Veredicto ---------------------------------------------------------
    out("=" * 100)
    bate_cesta = principal["calmar"] > base["calmar"]
    bate_nube = pct_pri >= 95
    out(f"Regla PRE-REGISTRADA (VIX<25 + pendiente>0, lag 1):")
    out(f"  ¿Mejora el Calmar de la cesta?  {'SI' if bate_cesta else 'NO'} "
        f"({principal['calmar']:.2f} vs {base['calmar']:.2f})")
    out(f"  ¿Supera al mismo patrón con fechas al azar?  {'SI' if bate_nube else 'NO'} "
        f"(percentil {pct_pri:.0f}; se exige >= 95)")
    aprobadas = [f for f, pct, _ in detalle if pct >= 95]
    out("")
    out(f"Variantes que baten la cesta: {len(ganadoras)}; de ellas, significativas: {len(aprobadas)}.")
    if aprobadas:
        for f in aprobadas:
            out(f"  ✅ {f['variante']} — Calmar {f['calmar']:.2f}, pero es la mejor de {len(filas)}:")
            out("     exige validación fuera de muestra antes de usarla.")
    out("")
    if bate_cesta and bate_nube:
        out("VEREDICTO: ✅ el macro aporta, y no solo por estar fuera del mercado.")
    elif ganadoras and not aprobadas:
        out("VEREDICTO: ❌ no hay ventaja demostrable. Las variantes que baten a la cesta")
        out("           NO se distinguen de estar fuera del mercado en fechas cualesquiera:")
        out("           el merito es la exposicion, no la señal.")
    elif bate_cesta:
        out("VEREDICTO: ⚠️ mejora el Calmar, pero NO se distingue de estar fuera del")
        out("           mercado en fechas cualesquiera. El merito es la exposicion, no la señal.")
    else:
        out("VEREDICTO: ❌ no mejora el Calmar de la cesta. El macro no sirve para esto.")
    out("=" * 100)

    ruta = ROOT / "data" / "reporte_macro_cesta.txt"
    ruta.write_text("\n".join(lineas) + "\n", encoding="utf-8", newline="\n")
    print(f"\nReporte escrito: {ruta.name}")


if __name__ == "__main__":
    main()
