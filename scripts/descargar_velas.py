"""Descarga de velas 4h desde Binance (endpoint publico) para ampliar el universo.

Por que asi
-----------
Hacia falta el mismo dato para 25 pares y, sobre todo, con la MISMA fecha final:
los 7 archivos originales terminaban en dos fechas distintas (BTC/ETH/XRP el
2026-10-17; ADA/BNB/SOL/AVAX el 2026-09-18) y `cargar_matriz` rellena hacia
adelante, asi que el ultimo mes tenia cuatro pares con el precio congelado.

Se usa el endpoint publico de Binance con `urllib`, igual que
`fuentes_externas.py`: una sola fuente, una sola temporalidad, sin claves y sin
dependencias nuevas. `CCXT` sigue siendo el camino si algun dia hace falta mas
de un exchange o mas temporalidades; hoy no aporta nada aqui.

Escribe `data/reporte_velas.txt` con la verificacion de lo descargado: numero de
velas, primera y ultima fecha, huecos, duplicados y dias de retraso. Un par solo
se considera utilizable si termina a la par que los demas y sin huecos raros.

    python scripts/descargar_velas.py
    python scripts/descargar_velas.py --pares BTC_USDT,LTC_USDT
    python scripts/descargar_velas.py --verificar          # no descarga, solo revisa
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
VELAS = ROOT / "freqtrade_bridge" / "user_data" / "data" / "binance"
REPORTE = ROOT / "data" / "reporte_velas.txt"

BASE = "https://api.binance.com"
INTERVALO = "4h"
MS_VELA = 4 * 60 * 60 * 1000

# 25 pares: los 7 originales + 18 que ya cotizaban en Binance antes del
# 2020-09-21 (la fecha en que arranca AVAX, que es la que fija el inicio comun
# de la matriz). Se excluyen a proposito los renombrados o retirados
# (MATIC->POL, FTT, SRM): dejarian la cola congelada, que es el defecto que
# venimos a corregir.
LISTA = [
    "BTC_USDT", "ETH_USDT", "BNB_USDT", "ADA_USDT", "XRP_USDT", "SOL_USDT", "AVAX_USDT",
    "LTC_USDT", "LINK_USDT", "DOT_USDT", "BCH_USDT", "ETC_USDT", "XLM_USDT", "TRX_USDT",
    "EOS_USDT", "ATOM_USDT", "NEO_USDT", "DASH_USDT", "ZEC_USDT", "VET_USDT",
    "THETA_USDT", "ALGO_USDT", "DOGE_USDT", "UNI_USDT", "COMP_USDT",
]


def _get(url: str, timeout: int = 60):
    peticion = urllib.request.Request(url, headers={"User-Agent": "openbb-bridge/1.0"})
    with urllib.request.urlopen(peticion, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def bajar_par(par: str, desde_ms: int, hasta_ms: int, pausa: float = 0.25) -> pd.DataFrame:
    """Velas 4h del par, paginando de 1000 en 1000 hasta `hasta_ms`."""
    simbolo = par.replace("_", "")
    filas: list[list] = []
    cursor = desde_ms
    while cursor < hasta_ms:
        url = (
            f"{BASE}/api/v3/klines?symbol={simbolo}&interval={INTERVALO}"
            f"&startTime={cursor}&limit=1000"
        )
        datos = _get(url)
        if not datos:
            break
        filas.extend(datos)
        cursor = int(datos[-1][0]) + MS_VELA
        if len(datos) < 1000:
            break
        time.sleep(pausa)

    if not filas:
        return pd.DataFrame()

    df = pd.DataFrame(
        filas,
        columns=["ot", "open", "high", "low", "close", "volume",
                 "ct", "qv", "n", "tb", "tq", "x"],
    )
    df["date"] = pd.to_datetime(df["ot"].astype("int64"), unit="ms", utc=True)
    for c in ("open", "high", "low", "close", "volume"):
        df[c] = df[c].astype(float)
    df = (
        df[["date", "open", "high", "low", "close", "volume"]]
        .drop_duplicates("date")
        .sort_values("date")
        .reset_index(drop=True)
    )
    try:  # mismo tipo que los archivos originales (datetime64[ms, UTC])
        df["date"] = df["date"].astype("datetime64[ms, UTC]")
    except TypeError:
        pass
    return df


def verificar(par: str, df: pd.DataFrame) -> dict:
    """Metricas de calidad de un par. No juzga: describe."""
    ts = pd.to_datetime(df["date"], utc=True)
    paso_h = ts.diff().dt.total_seconds().div(3600.0)
    retraso_d = (pd.Timestamp.now(tz="UTC") - ts.max()).total_seconds() / 86400.0
    return {
        "par": par,
        "n": len(df),
        "primera": ts.min(),
        "ultima": ts.max(),
        "duplicados": int(ts.duplicated().sum()),
        "huecos": int((paso_h > 4.0).sum()),
        "mayor_paso_h": float(paso_h.max()) if len(ts) > 1 else 0.0,
        "retraso_dias": round(retraso_d, 1),
        "kb": round(len(df) * df.memory_usage(deep=True).sum() / len(df) / 1024) if len(df) else 0,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pares", default=",".join(LISTA),
                    help="lista separada por comas (por defecto, los 25)")
    ap.add_argument("--desde", default="2020-01-01", help="primera fecha (YYYY-MM-DD)")
    ap.add_argument("--verificar", action="store_true",
                    help="no descarga: solo revisa los archivos que ya hay")
    ap.add_argument("--pausa", type=float, default=0.25, help="segundos entre peticiones")
    args = ap.parse_args()

    pares = [p.strip().upper() for p in args.pares.split(",") if p.strip()]
    desde_ms = int(pd.Timestamp(args.desde, tz="UTC").timestamp() * 1000)
    hasta_ms = int(pd.Timestamp.now(tz="UTC").timestamp() * 1000)

    lineas: list[str] = []
    def decir(t: str = "") -> None:
        print(t)
        lineas.append(t)

    decir("=" * 104)
    decir(f"VELAS 4h DESDE BINANCE  |  {len(pares)} pares  |  desde {args.desde}  |  {'solo verificar' if args.verificar else 'descarga'}")
    decir("=" * 104)

    filas = []
    for par in pares:
        ruta = VELAS / f"{par}-4h.feather"
        try:
            if args.verificar:
                if not ruta.exists():
                    decir(f"  {par:12s} FALTA el archivo")
                    continue
                df = pd.read_feather(ruta)
            else:
                df = bajar_par(par, desde_ms, hasta_ms, pausa=args.pausa)
                if df.empty:
                    decir(f"  {par:12s} SIN DATOS (par retirado o renombrado?)")
                    continue
                df.to_feather(ruta)
        except Exception as e:  # noqa: BLE001
            decir(f"  {par:12s} ERROR: {e}")
            continue

        m = verificar(par, df)
        filas.append(m)
        decir(
            f"  {m['par']:12s} n={m['n']:6,d}  {m['primera'].date()} -> {m['ultima'].date()}"
            f"  huecos={m['huecos']:3d} (max {m['mayor_paso_h']:.0f}h)"
            f"  dup={m['duplicados']}  retraso={m['retraso_dias']:.1f}d"
        )

    if not filas:
        decir("\nNo hay nada que informar.")
    else:
        tabla = pd.DataFrame(filas)
        comunes = tabla["ultima"].value_counts()
        fin_comun = comunes.index[0]
        decir("")
        decir(f"ultima vela mas repetida: {fin_comun}  ({comunes.iloc[0]} de {len(tabla)} pares)")
        rezagados = tabla[tabla["ultima"] < fin_comun]
        if len(rezagados):
            decir(f"pares que NO llegan a esa fecha ({len(rezagados)}): "
                  + ", ".join(f"{r.par} ({r.ultima.date()})" for r in rezagados.itertuples()))
            decir("  -> con `ffill` tendrian el precio congelado en la cola. Excluirlos del universo.")
        inicio_comun = tabla["primera"].max()
        decir(f"inicio comun de la matriz: {inicio_comun.date()}"
              f"  (lo fija {tabla.loc[tabla['primera'].idxmax(), 'par']})")
        decir(f"velas utiles por par (desde el inicio comun): "
              f"~{int((fin_comun - inicio_comun).total_seconds() // 3600 // 4) + 1:,}")

    REPORTE.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print(f"\nreporte escrito en {REPORTE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
