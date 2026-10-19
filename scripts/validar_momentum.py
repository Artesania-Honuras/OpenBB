"""Valida momentum transversal (rotacion entre pares) contra el azar.

Que mide y por que asi
----------------------
En cada rebalanceo se mantienen los K pares con mejor retorno de los ultimos L
dias, a peso igual y siempre invertido. La pregunta NO es "gana dinero?" sino
"gana por encima de elegir K pares al azar?".

Esa segunda pregunta es la unica honesta: elegir al azar tiene la misma
exposicion y la misma diversificacion por construccion, asi que cualquier
diferencia se puede atribuir al criterio de seleccion y a nada mas. Es el mismo
tipo de referencia que descarto el cruce EMA en `E-09` (alli: "elegir al azar
ese mismo porcentaje de dias"), pero aplicado a seleccion de activos.

El contraste es una prueba de permutacion: con los parametros que eligio el
entrenamiento en cada ventana, se repite la simulacion eligiendo los pares al
azar (200 semillas por defecto) y se mira en que percentil de esa nube cae la
estrategia. Si cae en el medio, no hay habilidad: hay suerte.

Protocolo (identico al resto del proyecto)
------------------------------------------
- Walk-forward: 18 meses de entrenamiento, 6 de prueba, avanzando de 6 en 6.
  Solo cuentan las ventanas de prueba.
- Comision 0.1% por lado, aplicada sobre el giro real de la cartera.
- Sin apalancamiento. Sin filtros macro (a proposito: se aisla el criterio de
  seleccion, igual que en `E-09` se aislo la salida).

Uso:
    python scripts\\validar_momentum.py
    python scripts\\validar_momentum.py --sims 1000 --stake 1.0
"""

from __future__ import annotations

import argparse
import itertools
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
VELAS = ROOT / "freqtrade_bridge" / "user_data" / "data" / "binance"

FEE = 0.001
BARRAS_POR_DIA = 6  # velas de 4h

# Rejilla de busqueda: se elige en entrenamiento, se juzga en prueba.
GRID_MOMENTUM = {
    "lookback_dias": [30, 60, 90],
    "top_k": [1, 2, 3],
    "rebal_dias": [7, 28],
}


# --------------------------------------------------------------------------
# Datos
# --------------------------------------------------------------------------
def cargar_matriz(pares: list[str]) -> pd.DataFrame:
    """Matriz de cierres alineada por fecha (una columna por par)."""
    series = {}
    for p in pares:
        ruta = VELAS / f"{p}-4h.feather"
        if not ruta.exists():
            raise FileNotFoundError(f"No hay velas en {ruta}")
        df = pd.read_feather(ruta)[["date", "close"]]
        df["date"] = pd.to_datetime(df["date"], utc=True)
        series[p] = df.set_index("date")["close"].astype(float)
    m = pd.DataFrame(series).sort_index()
    return m.ffill().dropna()


# --------------------------------------------------------------------------
# Motor
# --------------------------------------------------------------------------
def simular(m: pd.DataFrame, params: dict, semilla: int | None = None) -> np.ndarray:
    """Retorno de la cartera en cada vela.

    `semilla=None` -> seleccion por momentum. `semilla=int` -> seleccion AL AZAR
    (mismo K, mismo calendario de rebalanceo, mismo coste). Esa es la referencia.
    """
    closes = m.to_numpy(dtype=float)
    rets = np.zeros_like(closes)
    rets[1:] = closes[1:] / closes[:-1] - 1.0

    n, n_act = closes.shape
    L = int(params["lookback_dias"] * BARRAS_POR_DIA)
    rebal = int(params["rebal_dias"] * BARRAS_POR_DIA)
    K = min(int(params["top_k"]), n_act)

    rng = np.random.default_rng(semilla)
    pesos = np.zeros(n_act)
    cartera = np.zeros(n)

    for i in range(n):
        if i > 0:
            cartera[i] = float(pesos @ rets[i])  # pesos vigentes desde la vela anterior

        # Rebalanceo al cierre de la vela i: la decision usa solo datos conocidos.
        if i >= L and (i - L) % rebal == 0:
            if semilla is None:
                momento = closes[i] / closes[i - L] - 1.0
                elegidos = np.argsort(momento)[::-1][:K]
            else:
                elegidos = rng.choice(n_act, size=K, replace=False)
            nuevos = np.zeros(n_act)
            nuevos[elegidos] = 1.0 / K
            cartera[i] -= FEE * np.abs(nuevos - pesos).sum()
            pesos = nuevos

    return cartera


def compuesto(retornos: np.ndarray) -> float:
    return float(np.prod(1 + retornos) - 1) if len(retornos) else 0.0


def max_dd(retornos: np.ndarray) -> float:
    if not len(retornos):
        return 0.0
    eq = np.cumprod(1 + retornos)
    pico = np.maximum.accumulate(eq)
    return float(np.min(eq / pico - 1))


# --------------------------------------------------------------------------
# Walk-forward
# --------------------------------------------------------------------------
def walk_forward(m: pd.DataFrame, inicio: str, fin: str) -> tuple[pd.DataFrame, np.ndarray, list[dict]]:
    combos = [dict(zip(GRID_MOMENTUM.keys(), v)) for v in itertools.product(*GRID_MOMENTUM.values())]
    fechas = pd.date_range(pd.Timestamp(inicio, tz="UTC"), pd.Timestamp(fin, tz="UTC"), freq="6MS")

    filas, oos, ventanas = [], [], []
    for i in range(len(fechas) - 1):
        test_ini, test_fin = fechas[i], fechas[i + 1]
        train_ini = test_ini - pd.DateOffset(months=18)

        train = m[(m.index >= train_ini) & (m.index < test_ini)]
        test = m[(m.index >= test_ini) & (m.index < test_fin)]
        if len(train) < 500 or len(test) < 100:
            continue

        mejor, mejor_ret = None, -np.inf
        for params in combos:
            r = compuesto(simular(train, params))
            if r > mejor_ret:
                mejor, mejor_ret = params, r

        ret_test = simular(test, mejor)
        oos.append(ret_test)
        ventanas.append({"params": mejor, "test": test, "real": compuesto(ret_test)})

        filas.append({
            "periodo": f"{test_ini.date()} -> {test_fin.date()}",
            "L_dias": mejor["lookback_dias"],
            "K": mejor["top_k"],
            "rebal_dias": mejor["rebal_dias"],
            "train_%": round(mejor_ret * 100, 1),
            "test_%": round(compuesto(ret_test) * 100, 1),
        })

    return pd.DataFrame(filas), (np.concatenate(oos) if oos else np.array([])), ventanas


def nube_al_azar(ventanas: list[dict], sims: int) -> np.ndarray:
    """Distribucion del resultado si se eligieran los K pares al azar.

    Usa los mismos parametros (L, K, rebalanceo) que eligio el entrenamiento en
    cada ventana: lo unico que cambia es el criterio de seleccion.
    """
    finales = np.empty(sims)
    for s in range(sims):
        trozos = [simular(v["test"], v["params"], semilla=s) for v in ventanas]
        finales[s] = compuesto(np.concatenate(trozos))
    return finales


# --------------------------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--inicio", default="2021-01-01")
    ap.add_argument("--fin", default="2026-10-01")
    ap.add_argument("--sims", type=int, default=200, help="simulaciones al azar")
    args = ap.parse_args()

    pares = sorted(p.name.replace("-4h.feather", "") for p in VELAS.glob("*-4h.feather"))
    m = cargar_matriz(pares)
    print("=" * 100)
    print(f"MOMENTUM TRANSVERSAL  |  {len(pares)} pares  |  {args.inicio} -> {args.fin}")
    print("=" * 100)
    print(f"pares: {', '.join(pares)}")
    print(f"velas alineadas: {len(m):,}  |  {m.index.min().date()} -> {m.index.max().date()}")

    wf, oos, ventanas = walk_forward(m, args.inicio, args.fin)
    if not len(oos):
        print("sin ventanas suficientes")
        return

    comp = compuesto(oos)
    print("\n### WALK-FORWARD (solo cuentan las columnas de prueba)\n")
    print(wf.to_string(index=False))

    # Referencia 1: comprar y mantener la cesta a peso igual
    bh = m[m.index >= pd.Timestamp(args.inicio, tz="UTC")]
    bh_ret = float((bh.iloc[-1] / bh.iloc[0]).mean() - 1)

    # Referencia 2 (la que importa): elegir los K pares al azar
    nube = nube_al_azar(ventanas, args.sims)
    pct = float((nube < comp).mean() * 100)
    p_azar_mejor = float((nube >= comp).mean())

    print("\n### RESULTADO FUERA DE MUESTRA\n")
    print(f"  retorno compuesto:            {comp*100:+.1f}%")
    print(f"  drawdown maximo:              {max_dd(oos)*100:.1f}%")
    print(f"  ventanas positivas:           {int((wf['test_%'] > 0).sum())}/{len(wf)}")
    print("\n### REFERENCIAS\n")
    print(f"  cesta a peso igual (7 pares): {bh_ret*100:+.1f}%")
    print(f"  azar con el mismo K y calendario ({args.sims} semillas):")
    print(f"    p5 / p50 / p95:             {np.percentile(nube, 5)*100:+.1f}%  /  "
          f"{np.percentile(nube, 50)*100:+.1f}%  /  {np.percentile(nube, 95)*100:+.1f}%")
    print(f"  la estrategia cae en el percentil {pct:.0f} de la nube")
    print(f"  probabilidad de que el azar la iguale o supere: {p_azar_mejor*100:.1f}%")

    print("\n### VEREDICTO")
    if pct >= 95 and comp > 0:
        print("  El criterio de seleccion aporta: cae en el 5% mejor de la nube al azar.")
    elif pct >= 75:
        print("  Indicio debil: por encima del 75% de la nube, pero sin margen para confiar.")
    else:
        print("  SIN habilidad demostrable: el ranking de momentum no supera a elegir al azar.")
    print(f"  (barra del proyecto: >=2/3 de los activos baten la referencia; aqui la referencia es la nube al azar)")


if __name__ == "__main__":
    main()
