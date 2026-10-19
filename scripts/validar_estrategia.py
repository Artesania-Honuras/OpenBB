"""Validacion walk-forward + Monte Carlo.

No busca la estrategia perfecta: busca demostrar si una regla tiene ventaja
fuera de muestra, o si solo se ajusto al pasado.

Metodo
------
1. Walk-forward: se optimizan parametros con 18 meses y se evaluan en los 6
   meses siguientes, avanzando de 6 en 6. Los resultados que cuentan son
   SIEMPRE los de la ventana de prueba, nunca los de entrenamiento.
2. Monte Carlo: se remuestrean las operaciones fuera de muestra 5.000 veces
   para ver el rango de resultados posibles, no un unico numero.

Supuestos (documentados a proposito)
------------------------------------
- Backtest vectorizado independiente de Freqtrade: no reemplaza su motor,
  sirve como segunda opinion rapida.
- Comision 0.1% por lado.
- Stop loss y take profit chequeados en cada vela; si ambos caben en la misma
  vela se asume primero el stop (conservador).
- Sin apalancamiento, una posicion a la vez por par.
- `--stake` controla que fraccion del capital arriesga cada operacion.
  Con 0.1 se replica el sizing del bot (100 de 1000 USDT).

Uso:
    python scripts\\validar_estrategia.py --stake 0.1
    python scripts\\validar_estrategia.py --pair ETH_USDT --sims 10000
"""

from __future__ import annotations

import argparse
import itertools
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from puente_freqtrade import cargar_contexto  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
VELAS = ROOT / "freqtrade_bridge" / "user_data" / "data" / "binance"

FEE = 0.001
STOPLOSS = -0.08
TAKE_PROFIT = 0.15

GRID = {
    "ema_fast": [10, 20, 30],
    "ema_slow": [50, 80, 100],
    "vix_max": [18, 25, 32],
    "usar_slope": [False, True],
}


# --------------------------------------------------------------------------
# Datos
# --------------------------------------------------------------------------
def cargar_par(pair: str) -> pd.DataFrame:
    """Carga velas 4h y les anade el contexto de OpenBB."""
    ruta = VELAS / f"{pair}-4h.feather"
    if not ruta.exists():
        raise FileNotFoundError(f"No hay velas en {ruta}")

    df = pd.read_feather(ruta)
    df["date"] = pd.to_datetime(df["date"], utc=True)
    df = df.sort_values("date").reset_index(drop=True)

    ctx = cargar_contexto()
    c = ctx.reset_index().rename(columns={"date": "ctx_date"})
    c["ctx_date"] = pd.to_datetime(c["ctx_date"]).dt.tz_localize("UTC")
    df = pd.merge_asof(
        df, c.sort_values("ctx_date"),
        left_on="date", right_on="ctx_date", direction="backward",
    )
    return df.drop(columns=["ctx_date"])


def agregar_medias(df: pd.DataFrame, rapida: int, lenta: int) -> pd.DataFrame:
    df = df.copy()
    df["ema_fast"] = df["close"].ewm(span=rapida, adjust=False).mean()
    df["ema_slow"] = df["close"].ewm(span=lenta, adjust=False).mean()
    return df


# --------------------------------------------------------------------------
# Motor vectorizado
# --------------------------------------------------------------------------
def simular(df: pd.DataFrame, params: dict) -> tuple[np.ndarray, float]:
    """Devuelve (retorno neto de cada operacion, fraccion de tiempo en mercado)."""
    d = agregar_medias(df, params["ema_fast"], params["ema_slow"])

    entrada = (d["ema_fast"] > d["ema_slow"]).to_numpy()
    salida = (d["ema_fast"] < d["ema_slow"]).to_numpy()
    if params["usar_slope"]:
        entrada = entrada & (d["slope_10y_2y"].to_numpy() > 0)
    entrada = entrada & (d["vix"].to_numpy() < params["vix_max"])

    close = d["close"].to_numpy()
    low = d["low"].to_numpy()
    high = d["high"].to_numpy()

    retornos = []
    en_posicion = False
    precio_entrada = 0.0
    barras_dentro = 0

    for i in range(len(d)):
        if not en_posicion:
            if entrada[i]:
                en_posicion = True
                precio_entrada = close[i] * (1 + FEE)
            continue

        barras_dentro += 1
        stop = precio_entrada * (1 + STOPLOSS)
        objetivo = precio_entrada * (1 + TAKE_PROFIT)

        if low[i] <= stop:  # conservador: el stop se asume primero
            retornos.append(stop / precio_entrada - 1 - FEE)
            en_posicion = False
        elif high[i] >= objetivo:
            retornos.append(objetivo / precio_entrada - 1 - FEE)
            en_posicion = False
        elif salida[i]:
            retornos.append(close[i] * (1 - FEE) / precio_entrada - 1)
            en_posicion = False

    exposicion = barras_dentro / len(d) if len(d) else 0.0
    return np.array(retornos, dtype=float), exposicion


def retorno_compuesto(retornos: np.ndarray, stake: float = 1.0) -> float:
    if len(retornos) == 0:
        return 0.0
    return float(np.prod(1 + stake * retornos) - 1)


# --------------------------------------------------------------------------
# Walk-forward
# --------------------------------------------------------------------------
def walk_forward(
    df: pd.DataFrame, inicio: str, fin: str, stake: float = 1.0
) -> tuple[pd.DataFrame, np.ndarray]:
    combos = [
        dict(zip(GRID.keys(), valores))
        for valores in itertools.product(*GRID.values())
    ]

    fechas = pd.date_range(
        pd.Timestamp(inicio, tz="UTC"), pd.Timestamp(fin, tz="UTC"), freq="6MS"
    )

    filas = []
    oos_trades: list[np.ndarray] = []

    for i in range(len(fechas) - 1):
        test_ini, test_fin = fechas[i], fechas[i + 1]
        train_ini = test_ini - pd.DateOffset(months=18)

        train = df[(df["date"] >= train_ini) & (df["date"] < test_ini)]
        test = df[(df["date"] >= test_ini) & (df["date"] < test_fin)]
        if len(train) < 500 or len(test) < 100:
            continue

        mejor, mejor_ret = None, -np.inf
        for params in combos:
            ret = retorno_compuesto(simular(train, params)[0], stake)
            if ret > mejor_ret:
                mejor, mejor_ret = params, ret

        ret_test, exp_test = simular(test, mejor)
        oos_trades.append(ret_test)

        filas.append({
            "periodo": f"{test_ini.date()} -> {test_fin.date()}",
            "ema": f"{mejor['ema_fast']}/{mejor['ema_slow']}",
            "vix_max": mejor["vix_max"],
            "slope": "si" if mejor["usar_slope"] else "no",
            "train_%": round(mejor_ret * 100, 1),
            "test_%": round(retorno_compuesto(ret_test, stake) * 100, 1),
            "exp_%": round(exp_test * 100, 1),
            "trades": len(ret_test),
        })

    if not filas:
        return pd.DataFrame(), np.array([])

    return pd.DataFrame(filas), np.concatenate(oos_trades)


# --------------------------------------------------------------------------
# Monte Carlo
# --------------------------------------------------------------------------
def monte_carlo(retornos: np.ndarray, sims: int = 5000, stake: float = 1.0) -> dict:
    if len(retornos) < 10:
        return {}

    rng = np.random.default_rng(42)
    n = len(retornos)
    finales = np.empty(sims)
    drawdowns = np.empty(sims)

    for s in range(sims):
        muestra = rng.choice(retornos, size=n, replace=True)
        equity = np.cumprod(1 + stake * muestra)
        finales[s] = equity[-1] - 1
        pico = np.maximum.accumulate(equity)
        drawdowns[s] = float(np.min(equity / pico - 1))

    return {
        "p5": float(np.percentile(finales, 5)),
        "p50": float(np.percentile(finales, 50)),
        "p95": float(np.percentile(finales, 95)),
        "dd_medio": float(np.mean(drawdowns)),
        "dd_p95": float(np.percentile(drawdowns, 5)),  # 5% peor
        "prob_perder": float(np.mean(finales < 0)),
        "prob_ruina": float(np.mean(finales < -0.5)),
        "prob_dd_20": float(np.mean(drawdowns < -0.20)),
    }


# --------------------------------------------------------------------------
def evaluar_par(pair: str, inicio: str, fin: str, sims: int, stake: float,
                verbose: bool = True) -> dict:
    """Corre la validacion completa de un par y devuelve el resumen."""
    df = cargar_par(pair)

    if verbose:
        print("=" * 92)
        print(f"VALIDACION  |  {pair} 4h  |  {inicio} -> {fin}")
        print(f"sizing: {stake * 100:.0f}% del capital por operacion")
        print("=" * 92)
        print(f"velas: {len(df):,}  |  {df['date'].min().date()} -> {df['date'].max().date()}")

    wf, oos = walk_forward(df, inicio, fin, stake)
    if not len(oos):
        return {"pair": pair, "oos_%": 0.0, "exp_%": 0.0, "ventanas": "0/0",
                "acierto_%": 0.0, "p50_%": 0.0, "p_perder_%": 100.0,
                "bh_%": 0.0, "bh_ajustado_%": 0.0}

    compuesto = retorno_compuesto(oos, stake)
    mc = monte_carlo(oos, sims, stake)
    exp_media = float(wf["exp_%"].mean())
    positivos = int((wf["test_%"] > 0).sum())

    bh = df[df["date"] >= pd.Timestamp(inicio, tz="UTC")]
    bh_ret = bh["close"].iloc[-1] / bh["close"].iloc[0] - 1

    # Referencia honesta: mismo tiempo en mercado que la estrategia
    bh_ajustado = (1 + bh_ret) ** (exp_media / 100) - 1

    if verbose:
        print("\n### WALK-FORWARD (solo cuentan las columnas de prueba)\n")
        print(wf.to_string(index=False))
        print(f"\n  operaciones fuera de muestra: {len(oos):,}")
        print(f"  retorno compuesto OOS:        {compuesto * 100:+.1f}%")
        print(f"  exposicion media:             {exp_media:.1f}% del tiempo")
        print(f"  ventanas positivas:           {positivos}/{len(wf)}")
        print(f"  acierto:                      {(oos > 0).mean() * 100:.1f}%")
        print(f"  mejor / peor operacion:       {oos.max()*100:+.1f}% / {oos.min()*100:+.1f}%")
        print(f"\n### MONTE CARLO ({sims:,} simulaciones)\n")
        print(f"  retorno final p5 / p50 / p95: {mc['p5']*100:+.1f}%  /  "
              f"{mc['p50']*100:+.1f}%  /  {mc['p95']*100:+.1f}%")
        print(f"  drawdown medio:               {mc['dd_medio']*100:.1f}%")
        print(f"  drawdown (5% peor):           {mc['dd_p95']*100:.1f}%")
        print(f"  probabilidad de perder:       {mc['prob_perder']*100:.1f}%")
        print(f"  probabilidad de DD > 20%:     {mc['prob_dd_20']*100:.1f}%")
        print(f"  probabilidad de ruina (-50%): {mc['prob_ruina']*100:.1f}%")
        print(f"\n### REFERENCIA\n")
        print(f"  comprar y mantener:           {bh_ret*100:+.1f}%")
        print(f"  misma exposicion (~{exp_media:.0f}%):     {bh_ajustado*100:+.1f}%")
        print("\n### VEREDICTO")
        if compuesto > 0 and mc["prob_perder"] < 0.4 and positivos >= len(wf) * 0.6:
            print("  Positivo fuera de muestra, pero revisar contra la referencia.")
        else:
            print("  SIN ventaja fuera de muestra. No integrar al bot todavia.")
        print()

    return {
        "pair": pair,
        "oos_%": compuesto * 100,
        "exp_%": exp_media,
        "ventanas": f"{positivos}/{len(wf)}",
        "acierto_%": (oos > 0).mean() * 100,
        "p50_%": mc["p50"] * 100,
        "p_perder_%": mc["prob_perder"] * 100,
        "bh_%": bh_ret * 100,
        "bh_ajustado_%": bh_ajustado * 100,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pair", default="BTC_USDT")
    parser.add_argument("--todos", action="store_true", help="valida todos los pares disponibles")
    parser.add_argument("--inicio", default="2021-01-01")
    parser.add_argument("--fin", default="2026-10-01")
    parser.add_argument("--sims", type=int, default=5000)
    parser.add_argument(
        "--stake", type=float, default=1.0,
        help="fraccion del capital por operacion (0.1 = sizing del bot)",
    )
    args = parser.parse_args()

    pares = [args.pair]
    if args.todos:
        pares = sorted(p.name.replace("-4h.feather", "") for p in VELAS.glob("*-4h.feather"))

    filas = [evaluar_par(p, args.inicio, args.fin, args.sims, args.stake,
                         verbose=not args.todos) for p in pares]

    if not args.todos:
        return

    tabla = pd.DataFrame(filas)
    print("=" * 100)
    print(f"RESUMEN MULTI-ACTIVO  |  {args.inicio} -> {args.fin}  |  sizing {args.stake*100:.0f}%")
    print("=" * 100)
    print(tabla.round(1).to_string(index=False))

    gana = tabla["oos_%"] > 0
    bate = tabla["oos_%"] > tabla["bh_ajustado_%"]
    print(f"\n  activos con retorno OOS positivo:       {int(gana.sum())}/{len(tabla)}")
    print(f"  activos que baten su referencia:        {int(bate.sum())}/{len(tabla)}")

    print("\n### VEREDICTO GLOBAL")
    if bate.mean() >= 2 / 3 and mc_mediana(tabla) > 0:
        print("  Ventaja consistente entre activos. Candidata a dry-run.")
    else:
        print("  SIN ventaja consistente entre activos.")
        print("  El cruce EMA 20/50 no es una base sobre la que integrar el bot.")


def mc_mediana(tabla: pd.DataFrame) -> float:
    return float(tabla["p50_%"].median())


if __name__ == "__main__":
    main()


