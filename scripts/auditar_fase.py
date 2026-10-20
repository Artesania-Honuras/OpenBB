"""Audita la fase del rebalanceo en TODA la cadena de momentum (E-10 .. E-14).

Por que existe
--------------
`E-16` demostro que el +820 % de la regla fija era la mediana de 42 fases de un
parametro que nunca se declaro. Pero `E-10`..`E-13` —el walk-forward, el 7/11,
el Calmar 35,8— se midieron con la MISMA rejilla (fase 0). Si el resultado
depende de la fase, esos numeros tambien son un artefacto, y hay que saberlo
antes de seguir buscando reglas sobre esa base.

Que mide
--------
Repite el walk-forward completo (entrenamiento 18 m / prueba 6 m, 18 combos,
objetivo Calmar) para las **42 fases** de la rejilla semanal, en los dos
universos:

  - 24 pares (E-13, el vigente)
  - 7 pares  (E-10, el original, reproducible con `--pares`)

No cambia nada del protocolo: solo se pregunta CUANDO empieza la rejilla.

Uso:
    python scripts\\auditar_fase.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from validar_momentum import (  # noqa: E402
    BARRAS_POR_DIA, calmar, cargar_matriz, compuesto, max_dd, walk_forward,
)

ROOT = Path(__file__).resolve().parents[1]
VELAS = ROOT / "freqtrade_bridge" / "user_data" / "data" / "binance"
INICIO, FIN = "2021-01-01", "2026-10-01"
FASES = 7 * BARRAS_POR_DIA  # 42 velas de 4h en una semana

# Los 7 pares originales de E-10 (no los 7 primeros por orden alfabetico).
PARES_7 = ["ADA_USDT", "AVAX_USDT", "BNB_USDT", "BTC_USDT", "ETH_USDT", "SOL_USDT", "XRP_USDT"]


def universo(n: int | None = None) -> list[str]:
    pares = sorted(p.name.replace("-4h.feather", "") for p in VELAS.glob("*-4h.feather"))
    if n == 7:
        return PARES_7
    return pares


def cesta(m: pd.DataFrame) -> dict:
    r = m.pct_change().mean(axis=1).fillna(0.0).to_numpy()
    return {"ret_%": compuesto(r) * 100, "dd_%": max_dd(r) * 100, "calmar": calmar(r)}


def auditar(m: pd.DataFrame, nombre: str) -> tuple[pd.DataFrame, dict]:
    filas = []
    for fase in range(FASES):
        wf, oos, _ = walk_forward(m, INICIO, FIN, objetivo="calmar", fase=fase)
        if not len(oos):
            continue
        filas.append({
            "fase": fase,
            "ret_%": compuesto(oos) * 100,
            "dd_%": max_dd(oos) * 100,
            "calmar": calmar(oos),
            "ventanas": int((wf["test_%"] > 0).sum()),
            "n_ventanas": len(wf),
        })
    t = pd.DataFrame(filas)

    ref = cesta(m[(m.index >= pd.Timestamp(INICIO, tz="UTC")) & (m.index < pd.Timestamp(FIN, tz="UTC"))])
    resumen = {
        "universo": nombre,
        "ret_mediana_%": float(t["ret_%"].median()),
        "ret_min_%": float(t["ret_%"].min()),
        "ret_max_%": float(t["ret_%"].max()),
        "calmar_mediana": float(t["calmar"].median()),
        "calmar_min": float(t["calmar"].min()),
        "calmar_max": float(t["calmar"].max()),
        "dd_mediana_%": float(t["dd_%"].median()),
        "dd_peor_%": float(t["dd_%"].min()),
        "ventanas_mediana": float(t["ventanas"].median()),
        "ventanas_max": int(t["ventanas"].max()),
        "fases_positivas": int((t["ret_%"] > 0).sum()),
        "fases_calmar_sobre_cesta": int((t["calmar"] > ref["calmar"]).sum()),
        "cesta_ret_%": ref["ret_%"],
        "cesta_calmar": ref["calmar"],
    }
    return t, resumen


def main() -> None:
    print("=" * 100)
    print(f"AUDITORIA DE FASE — walk-forward completo, {FASES} fases, {INICIO} -> {FIN}")
    print("=" * 100)

    universos = [(universo(), "24 pares (E-13)"), (universo(7), "7 pares (E-10)")]
    resumenes, tablas = [], {}
    for pares, nombre in universos:
        m = cargar_matriz(pares)
        t, r = auditar(m, nombre)
        tablas[nombre] = t
        resumenes.append(r)

        print(f"\n### {nombre} — {len(pares)} pares")
        print(f"  cesta a peso igual: {r['cesta_ret_%']:+.1f}%  Calmar {r['cesta_calmar']:.2f}")
        print(f"  retorno OOS:   mediana {r['ret_mediana_%']:+10.1f}%   "
              f"min {r['ret_min_%']:+10.1f}%   max {r['ret_max_%']:+10.1f}%")
        print(f"  Calmar:        mediana {r['calmar_mediana']:10.2f}    "
              f"min {r['calmar_min']:10.2f}    max {r['calmar_max']:10.2f}")
        print(f"  DD:            mediana {r['dd_mediana_%']:10.1f}%    peor {r['dd_peor_%']:10.1f}%")
        print(f"  ventanas:      mediana {r['ventanas_mediana']:.0f}/{int(t['n_ventanas'].max())}"
              f"   mejor {r['ventanas_max']}/{int(t['n_ventanas'].max())}")
        print(f"  fases positivas: {r['fases_positivas']}/{len(t)}   "
              f"fases con Calmar > cesta: {r['fases_calmar_sobre_cesta']}/{len(t)}")

        print(f"\n  {'fase':>4} {'ret_%':>12} {'dd_%':>9} {'calmar':>8} {'ventanas':>9}")
        for _, f in t.iterrows():
            print(f"  {int(f['fase']):>4} {f['ret_%']:>+12.1f} {f['dd_%']:>9.1f} "
                  f"{f['calmar']:>8.2f} {int(f['ventanas']):>6}/{int(f['n_ventanas'])}")

    comparacion = pd.DataFrame(resumenes).drop(columns=["cesta_ret_%", "cesta_calmar"])
    print("\n" + "=" * 100)
    print("### RESUMEN")
    print(comparacion.round(2).to_string(index=False))

    r24 = next(r for r in resumenes if "24" in r["universo"])
    print("\n### VEREDICTO")
    sobre_cesta = r24["fases_calmar_sobre_cesta"]
    print(f"  De {FASES} fases, el walk-forward de 24 pares supera a la cesta en Calmar "
          f"en {sobre_cesta} ({sobre_cesta / FASES * 100:.0f} %).")
    print(f"  Calmar mediano {r24['calmar_mediana']:.2f} (min {r24['calmar_min']:.2f}, "
          f"max {r24['calmar_max']:.2f}) frente a {r24['cesta_calmar']:.2f} de la cesta.")
    if r24["calmar_mediana"] > r24["cesta_calmar"] and sobre_cesta >= FASES * 0.8:
        print("  ✅ La ventaja del walk-forward NO es un artefacto de fase: sobrevive en casi todas.")
    elif r24["calmar_mediana"] > r24["cesta_calmar"]:
        print("  ⚠️ La ventaja sobrevive en mediana, pero NO en casi todas las fases: el numero")
        print("     agregado esconde una dependencia fuerte del calendario. Se reporta como rango.")
    else:
        print("  ❌ La ventaja del walk-forward TAMBIEN era fase: en mediana no bate a la cesta.")
    print("=" * 100)


if __name__ == "__main__":
    main()
