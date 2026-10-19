"""Fuentes externas a OpenBB — capa rapida (derivados de cripto).

OpenBB cubre la capa lenta (macro). Los endpoints de derivados de cripto que
trae (`deribit/*`) solo devuelven ventanas cortas: funding 31 dias, volatilidad
realizada 17 dias, indice 1 dia. Eso sirve para el estado en vivo, pero **no**
para validar fuera de muestra con la puerta 2021-2026.

Aqui se traen las mismas magnitudes desde endpoints publicos, sin claves y sin
dependencias nuevas (solo `urllib`), con historial completo:

| Fuente                | Endpoint                          | Historial   |
|-----------------------|-----------------------------------|-------------|
| Funding de perpetuos  | `fapi.binance.com/fapi/v1/fundingRate` | 2019 → hoy |

Todo se cachea en `data/cache/`. Uso:

    from fuentes_externas import funding_historico

    df = funding_historico("BTCUSDT")          # usa cache
    df = funding_historico("BTCUSDT", forzar=True)  # vuelve a descargar
"""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "cache"
BASE = "https://fapi.binance.com"

# El funding de Binance se liquida cada 8 horas -> 3 veces al dia.
FUNDINGS_POR_DIA = 3
DIAS_POR_ANIO = 365


def _get(url: str, timeout: int = 60):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def funding_historico(
    simbolo: str = "BTCUSDT",
    desde: str = "2021-01-01",
    forzar: bool = False,
) -> pd.DataFrame:
    """Funding de perpetuos cada 8 h, indexado por fecha UTC.

    Columnas:
      - `funding_rate`: tasa por liquidacion (decimal, tal como la publica el exchange).
      - `anual`: la misma tasa expresada en % anual (rate x 3 x 365 x 100).

    El endpoint devuelve 1000 registros por llamada; se pagina hasta agotar.
    """
    CACHE.mkdir(parents=True, exist_ok=True)
    ruta = CACHE / f"funding_{simbolo.lower()}.parquet"

    if ruta.exists() and not forzar:
        df = pd.read_parquet(ruta)
    else:
        filas: list[dict] = []
        inicio_ms = int(pd.Timestamp(desde, tz="UTC").timestamp() * 1000)

        while True:
            url = f"{BASE}/fapi/v1/fundingRate?" + urllib.parse.urlencode(
                {"symbol": simbolo, "limit": 1000, "startTime": inicio_ms}
            )
            lote = _get(url)
            if not lote:
                break
            filas.extend(lote)
            if len(lote) < 1000:
                break
            inicio_ms = int(lote[-1]["fundingTime"]) + 1
            time.sleep(0.25)  # cortesia con el endpoint publico

        if not filas:
            raise RuntimeError(f"Binance no devolvio funding para {simbolo}")

        df = pd.DataFrame(filas)
        df["date"] = pd.to_datetime(df["fundingTime"], unit="ms", utc=True)
        df["funding_rate"] = pd.to_numeric(df["fundingRate"], errors="coerce")
        df = (
            df[["date", "funding_rate"]]
            .dropna()
            .sort_values("date")
            .drop_duplicates("date")
            .reset_index(drop=True)
        )
        df.to_parquet(ruta, index=False)

    df["funding_rate"] = pd.to_numeric(df["funding_rate"], errors="coerce")
    df["anual"] = df["funding_rate"] * FUNDINGS_POR_DIA * DIAS_POR_ANIO * 100
    df = df.set_index("date").sort_index()
    df.index = pd.to_datetime(df.index, utc=True)
    return df


def funding_diario(
    simbolo: str = "BTCUSDT",
    desde: str = "2021-01-01",
    forzar: bool = False,
) -> pd.Series:
    """Media diaria del funding anualizado (%), indexada por fecha sin zona horaria.

    Se usa la media del dia porque en el contexto diario cada fila representa
    el dia completo; el retraso anti look-ahead lo aplica el puente.
    """
    df = funding_historico(simbolo, desde=desde, forzar=forzar)
    serie = df["anual"].resample("D").mean().dropna()
    serie.index = serie.index.tz_localize(None)
    serie.name = "funding_btc_anual"
    return serie


if __name__ == "__main__":
    s = funding_diario(forzar="--forzar" in __import__("sys").argv)
    print(f"funding diario anualizado: {len(s):,} filas")
    print(f"  rango: {s.index[0].date()} -> {s.index[-1].date()}")
    print(f"  min {s.min():+.1f}%  max {s.max():+.1f}%  media {s.mean():+.1f}%")
    print(s.tail(5).round(2).to_string())
