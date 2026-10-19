"""Puente OpenBB -> Freqtrade.

Exporta el *contexto* (macro, riesgo, posicionamiento, factores) como un
DataFrame diario y lo fusiona con las velas de Freqtrade SIN look-ahead.

La idea de diseno: OpenBB no reemplaza las velas. Aporta lo que Freqtrade no
puede dar — tipos, curva, VIX, inflacion, posicionamiento — y la estrategia
tecnica sigue decidiendo la entrada.

Reglas anti look-ahead
----------------------
Cada serie se retrasa segun cuando se publica de verdad:

| Serie              | Retraso | Motivo                                  |
|--------------------|---------|-----------------------------------------|
| tasas, VIX, SPX, FX| 1 dia   | cierre del dia anterior                 |
| COT                | 3 dias  | se publica el viernes con datos del martes |
| CPI, PIB           | 45 dias | rezago estadistico real                 |
| factores Fama-French | 31 dias | el retorno del mes no se conoce hasta que termina |

Uso:
    from puente_freqtrade import construir_contexto, cargar_contexto, fusionar
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from obb_env import consultar, obb_local  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CONTEXT_DIR = ROOT / "data" / "context"
CONTEXT_FILE = CONTEXT_DIR / "contexto_diario.parquet"

# Retrasos de publicacion en dias (ver tabla del docstring)
DELAYS = {"cpi_yoy": 45, "gdp_yoy": 45, "cot_net": 3}
DELAY_DEFAULT = 1
DELAY_PREFIX = {"ff_": 31}


def _retraso(columna: str) -> int:
    if columna in DELAYS:
        return DELAYS[columna]
    for prefijo, dias in DELAY_PREFIX.items():
        if columna.startswith(prefijo):
            return dias
    return DELAY_DEFAULT


def construir_contexto(forzar: bool = False) -> pd.DataFrame:
    """Descarga (o lee de cache) y normaliza el contexto diario."""
    obb = obb_local()
    piezas: dict[str, pd.Series] = {}

    # --- macro: tipos y curva -------------------------------------------------
    tasas = consultar(
        "government_treasury_rates",
        lambda: obb.fixedincome.government.treasury_rates(
            provider="federal_reserve", start_date="2000-01-01"
        ),
        forzar,
    )
    tasas.index = pd.to_datetime(tasas.index)
    piezas["yield_2y"] = tasas["year_2"].astype(float)
    piezas["yield_10y"] = tasas["year_10"].astype(float)
    piezas["slope_10y_2y"] = piezas["yield_10y"] - piezas["yield_2y"]

    effr = consultar(
        "fixedincome_rate_effr",
        lambda: obb.fixedincome.rate.effr(provider="federal_reserve", start_date="2000-01-01"),
        forzar,
    )
    effr.index = pd.to_datetime(effr.index)
    piezas["fed_funds"] = effr["rate"].astype(float)

    # --- riesgo de mercado ----------------------------------------------------
    vix = consultar("vix", lambda: obb.index.price.historical("VIX", provider="cboe"), forzar)
    vix.index = pd.to_datetime(vix.index)
    piezas["vix"] = vix["close"].astype(float)

    spx = consultar("spx", lambda: obb.index.price.historical("SPX", provider="cboe"), forzar)
    spx.index = pd.to_datetime(spx.index)
    piezas["spx"] = spx["close"].astype(float)

    fx = consultar(
        "currency_price_historical_eurusd",
        lambda: obb.currency.price.historical("EURUSD", provider="ecb"),
        forzar,
    )
    fx.index = pd.to_datetime(fx.index)
    piezas["eurusd"] = fx["close"].astype(float)

    # --- inflacion y actividad ------------------------------------------------
    cpi = consultar("economy_cpi", lambda: obb.economy.cpi(provider="oecd"), forzar)
    cpi.index = pd.to_datetime(cpi.index)
    piezas["cpi_yoy"] = cpi["value"].astype(float) * 100

    gdp = consultar("economy_gdp_real", lambda: obb.economy.gdp.real(provider="oecd"), forzar)
    gdp.index = pd.to_datetime(gdp.index)
    piezas["gdp_yoy"] = gdp["value"].astype(float).pct_change(4, fill_method=None) * 100

    # --- posicionamiento ------------------------------------------------------
    cot = consultar("cftc_cot_positioning", lambda: obb.cftc.cot_positioning(provider="cftc"), forzar)
    cot.index = pd.to_datetime(cot["report_date"])
    piezas["cot_net"] = cot["large_specs_net"].astype(float) / 1000.0

    # --- factores -------------------------------------------------------------
    ff = consultar("famafrench_factors", lambda: obb.famafrench.factors(provider="famafrench"), forzar)
    ff.index = pd.to_datetime(ff.index)
    for col in ("mkt_rf", "smb", "hml"):
        piezas[f"ff_{col}"] = ff[col].astype(float)

    contexto = pd.DataFrame(piezas).sort_index()

    # Retraso por fecha de publicacion + relleno diario hacia adelante
    for col in contexto.columns:
        contexto[col] = contexto[col].shift(freq=pd.Timedelta(days=_retraso(col)))

    contexto = contexto.resample("D").last().ffill()
    contexto.index.name = "date"
    return contexto


def guardar_contexto(contexto: pd.DataFrame) -> Path:
    """Guarda el contexto en parquet (y CSV legible)."""
    CONTEXT_DIR.mkdir(parents=True, exist_ok=True)
    contexto.to_parquet(CONTEXT_FILE)
    contexto.to_csv(CONTEXT_DIR / "contexto_diario.csv")
    return CONTEXT_FILE


def cargar_contexto() -> pd.DataFrame:
    """Carga el contexto exportado. Falla con mensaje claro si no existe."""
    if not CONTEXT_FILE.exists():
        raise FileNotFoundError(
            f"No hay contexto exportado en {CONTEXT_FILE}. "
            "Ejecuta: python scripts\\puente_freqtrade.py --exportar"
        )
    ctx = pd.read_parquet(CONTEXT_FILE)
    ctx.index = pd.to_datetime(ctx.index)
    return ctx


def fusionar(velas: pd.DataFrame, contexto: pd.DataFrame | None = None) -> pd.DataFrame:
    """Añade el contexto a un DataFrame de velas de Freqtrade.

    Usa merge_asof hacia atras: cada vela solo ve el ultimo dato publicado
    antes de su fecha. Es imposible que vea el futuro.
    """
    contexto = cargar_contexto() if contexto is None else contexto

    v = velas.copy()
    v["date"] = pd.to_datetime(v["date"], utc=True)

    c = contexto.reset_index().rename(columns={"date": "ctx_date"})
    c["ctx_date"] = pd.to_datetime(c["ctx_date"]).dt.tz_localize("UTC")

    ordenado = v.sort_values("date")
    fusion = pd.merge_asof(
        ordenado,
        c.sort_values("ctx_date"),
        left_on="date",
        right_on="ctx_date",
        direction="backward",
    )
    # merge_asof devuelve un RangeIndex: se restaura el original de Freqtrade
    fusion.index = ordenado.index
    return fusion.drop(columns=["ctx_date"]).sort_index()


def estado_actual() -> dict:
    """Foto del contexto vivo (para el bot en marcha, no para backtest)."""
    obb = obb_local()

    def ultimo(df, col):
        try:
            return float(df[col].dropna().iloc[-1])
        except Exception:  # noqa: BLE001
            return None

    ctx = construir_contexto()
    ultima = ctx.iloc[-1]

    libro = obb.deribit.market.order_book(symbol="BTC-PERPETUAL", provider="deribit").to_df()
    compras = libro.loc[libro["side"] == "buy", "size"].sum()
    ventas = libro.loc[libro["side"] == "sell", "size"].sum()
    desequilibrio = (compras - ventas) / (compras + ventas) if (compras + ventas) else None

    funding = obb.deribit.rates.funding_history(provider="deribit").to_df()

    return {
        "vix": ultima.get("vix"),
        "fed_funds": ultima.get("fed_funds"),
        "yield_10y": ultima.get("yield_10y"),
        "slope_10y_2y": ultima.get("slope_10y_2y"),
        "cpi_yoy": ultima.get("cpi_yoy"),
        "cot_net": ultima.get("cot_net"),
        "eurusd": ultima.get("eurusd"),
        "funding_btc_8h": ultimo(funding, "interest_8h"),
        "order_book_imbalance": desequilibrio,
    }


def _main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Puente OpenBB -> Freqtrade")
    parser.add_argument("--exportar", action="store_true", help="Descarga y guarda el contexto")
    parser.add_argument("--forzar", action="store_true", help="Ignora la cache")
    parser.add_argument("--estado", action="store_true", help="Muestra el estado actual")
    args = parser.parse_args()

    if args.exportar:
        ctx = construir_contexto(forzar=args.forzar)
        ruta = guardar_contexto(ctx)
        print(f"Contexto exportado: {ruta}")
        print(f"  filas: {len(ctx):,}  |  columnas: {len(ctx.columns)}")
        print(f"  rango: {ctx.index[0].date()} -> {ctx.index[-1].date()}")
        print("\nUltimos valores:")
        print(ctx.tail(3).T.to_string())

    if args.estado:
        print("\nEstado actual:")
        for k, v in estado_actual().items():
            print(f"  {k:<22} {v}")

    if not (args.exportar or args.estado):
        parser.print_help()


if __name__ == "__main__":
    _main()
