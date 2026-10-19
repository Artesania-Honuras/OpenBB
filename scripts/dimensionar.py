"""Dimensionado del sleeve: traducir la caida del 82 % a un numero de cartera.

Que hace
--------
Toma la curva de la configuracion FIJA (la que se instalaria) y la somete a
bootstrap por bloques para responder una pregunta que el backtest no responde:
**si le doy el X % de mi capital, que drawdown ve mi cartera entera?**

Modelo, declarado
-----------------
Cartera = fraccion **constante** `s` en el sleeve y `(1-s)` en caja, rebalanceada
en cada vela. El retorno de la cartera es `s * r(t)` y la caja no rinde. Es el
modelo que corresponde a operar de verdad (se mantiene el porcentaje), y es el
que hace que un sleeve del 5 % no pueda caer mas del 5 %.

(La version sin rebalanceo es enganosa: un sleeve que crece 50x acaba siendo el
80 % de la cartera, y entonces su drawdown pasa a ser el de la cartera. Eso no
es un sleeve, es una posicion que se dejo correr. Se probo y se descarto porque
el bootstrap producia drawdowns del 31 % con un 5 % invertido: imposible, y
senal de que el modelo estaba mal, no de que el riesgo fuera alto.)

Bootstrap por bloques de 7 dias para conservar la autocorrelacion: si se
remuestrearan velas sueltas se destruiria justo el efecto que produce el
drawdown (las rachas), y saldria un riesgo falsamente bajo.

    python scripts/dimensionar.py
    python scripts/dimensionar.py --sleeves 5,10,15,20,25 --sims 1000
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validar_momentum import VELAS, cargar_matriz, simular  # noqa: E402

BARRAS_DIA = 6          # velas de 4h
DIAS_ANIO = 365


def drawdown(e: np.ndarray) -> float:
    pico = np.maximum.accumulate(e)
    return float((e / pico - 1.0).min())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--inicio", default="2021-01-01")
    ap.add_argument("--fin", default="2026-10-01")
    ap.add_argument("--L", type=int, default=30)
    ap.add_argument("--K", type=int, default=3)
    ap.add_argument("--rebal", type=int, default=7)
    ap.add_argument("--sleeves", default="5,10,15,20,25,30")
    ap.add_argument("--sims", type=int, default=1000)
    ap.add_argument("--bloque", type=int, default=7, help="dias por bloque del bootstrap")
    args = ap.parse_args()

    pares = sorted(p.name.replace("-4h.feather", "") for p in VELAS.glob("*-4h.feather"))
    m = cargar_matriz(pares)
    desde = pd.Timestamp(args.inicio, tz="UTC")
    hasta = pd.Timestamp(args.fin, tz="UTC")
    m_oos = m[(m.index >= desde) & (m.index < hasta)]

    params = dict(lookback_dias=args.L, top_k=args.K, rebal_dias=args.rebal)
    r = simular(m_oos, params)
    e = np.cumprod(1.0 + r)
    anios = (m_oos.index[-1] - m_oos.index[0]).days / 365.25

    print("=" * 100)
    print(f"DIMENSIONADO DEL SLEEVE  |  L={args.L} K={args.K} rebal={args.rebal}  |  "
          f"{len(pares)} pares  |  {anios:.2f} anios")
    print("=" * 100)
    print(f"  sleeve al 100 %:   retorno {e[-1] - 1:+.1%}   DD {drawdown(e):.1%}   "
          f"CAGR {(e[-1] ** (1 / anios) - 1):+.1%}")
    print(f"  bootstrap: {args.sims} caminos, bloques de {args.bloque} dias (conserva rachas)\n")

    rng = np.random.default_rng(7)
    n = len(r)
    bloque = args.bloque * BARRAS_DIA
    n_bloques = int(np.ceil(n / bloque))

    # Caminos completos (para el DD) y caminos de 1 anio (para P(perdida a 1 anio))
    completos = np.empty((args.sims, n))
    for s in range(args.sims):
        inicios = rng.integers(0, n - bloque, n_bloques)
        completos[s] = np.concatenate([r[i:i + bloque] for i in inicios])[:n]

    un_anio = int(DIAS_ANIO * BARRAS_DIA)
    cortos = np.empty((args.sims, un_anio))
    for s in range(args.sims):
        inicios = rng.integers(0, n - bloque, int(np.ceil(un_anio / bloque)))
        cortos[s] = np.concatenate([r[i:i + bloque] for i in inicios])[:un_anio]

    sleeves = [float(x) for x in args.sleeves.split(",")]
    filas = []
    for s in sleeves:
        p = s / 100.0
        dds, cagrs, un_anio_pnl = [], [], []
        for k in range(args.sims):
            eq = np.cumprod(1.0 + p * completos[k])
            dds.append(drawdown(eq))
            cagrs.append(eq[-1] ** (1 / anios) - 1)
            e1 = np.cumprod(1.0 + p * cortos[k])
            un_anio_pnl.append(e1[-1] - 1)
        dds = np.array(dds)
        cagrs = np.array(cagrs)
        un_anio_pnl = np.array(un_anio_pnl)
        filas.append({
            "sleeve_%": s,
            "CAGR_p50_%": np.percentile(cagrs, 50) * 100,
            "DD_p50_%": np.percentile(dds, 50) * 100,
            "DD_p95_%": np.percentile(dds, 5) * 100,   # 5 % peor
            "P(DD>20%)_%": (dds < -0.20).mean() * 100,
            "P(perdida_1a)_%": (un_anio_pnl < 0).mean() * 100,
            "P(perdida_1a>25%)_%": (un_anio_pnl < -0.25).mean() * 100,
        })

    tabla = pd.DataFrame(filas)
    print("  columnas: DD_p95 = el 5 % peor de los caminos (peor que el DD_p50)\n")
    print("  " + tabla.to_string(index=False, float_format=lambda x: f"{x:,.1f}").replace("\n", "\n  "))

    cumple = tabla[tabla["DD_p95_%"] > -20.0]
    print("\n### LECTURA")
    if len(cumple):
        s_max = cumple["sleeve_%"].max()
        print(f"  El mayor sleeve con DD al 5 % peor mejor que -20 % es: {s_max:.0f} % del capital.")
        fila = cumple.iloc[-1]
        print(f"  Ahi el drawdown tipico de la cartera es {fila['DD_p50_%']:.1f} % y el 5 % peor "
              f"{fila['DD_p95_%']:.1f} %, con un CAGR mediano de {fila['CAGR_p50_%']:.1f} %.")
    else:
        print("  Ni siquiera el sleeve mas pequenio cumple DD al 5 % peor mejor que -20 %.")

    tabla.to_csv(Path("data") / "reporte_dimensionado.csv", index=False)
    print("\n  (tabla guardada en data/reporte_dimensionado.csv)")


if __name__ == "__main__":
    main()
