"""Verificacion de las 8 familias de analisis contra OpenBB local.

Corre todas las consultas SIN claves de API, guarda los resultados en
data/cache/ y reporta que esta cubierto y que no.

    .\\venvs\\openbb\\Scripts\\python.exe scripts\\verificar_familias.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from obb_env import consultar, obb_local  # noqa: E402

obb = obb_local()

OK, ERR, HUECO = "OK  ", "ERR ", "HUECO"
resultados: list[tuple[str, str, str, str]] = []


def _slug(texto: str) -> str:
    """Convierte un titulo legible en un nombre de archivo valido."""
    limpio = "".join(c if c.isalnum() else "_" for c in texto.lower())
    while "__" in limpio:
        limpio = limpio.replace("__", "_")
    return limpio.strip("_")


def probar(familia: str, nombre: str, fn, forzar: bool = False):
    """Ejecuta una consulta y registra el resultado."""
    try:
        df = consultar(_slug(nombre), fn, forzar=forzar)
        print(f"[{OK}] {familia:<20} {nombre:<26} filas={df.shape[0]:>6}  cols={df.shape[1]}")
        resultados.append((familia, nombre, OK, f"{df.shape[0]}x{df.shape[1]}"))
        return df
    except Exception as e:  # noqa: BLE001
        msg = f"{type(e).__name__}: {str(e)[:80]}".replace("\n", " ")
        print(f"[{ERR}] {familia:<20} {nombre:<26} {msg}")
        resultados.append((familia, nombre, ERR, msg))
        return None


def hueco(familia: str, nombre: str, motivo: str) -> None:
    print(f"[{HUECO}] {familia:<19} {nombre:<26} {motivo}")
    resultados.append((familia, nombre, HUECO, motivo))


print("=" * 100)
print("VERIFICACION DE LAS 8 FAMILIAS  |  OpenBB local (127.0.0.1:6900)  |  sin claves de API")
print("=" * 100)

# ---------------------------------------------------------------- 1. TECNICO
print("\n### 1. TECNICO (S&P 500 via CBOE + indicadores locales)")
spx = probar("1 Tecnico", "index.price.historical SPX",
             lambda: obb.index.price.historical("SPX", provider="cboe"))
if spx is not None:
    serie = spx.reset_index()
    probar("1 Tecnico", "technical.rsi(14)",
           lambda: obb.technical.rsi(data=serie, index="date", target="close"))
    probar("1 Tecnico", "technical.ema(20)",
           lambda: obb.technical.ema(data=serie, index="date", target="close", length=20))
    probar("1 Tecnico", "technical.macd",
           lambda: obb.technical.macd(data=serie, index="date", target="close"))

# OHLC sin clave: la unica fuente gratuita del set instalado es TMX (Canadá).
# Los indicadores que necesitan maximo/minimo (ATR, volatilidad realizada) van aquí.
equity = probar("1 Tecnico", "equity.price.historical SHOP",
                lambda: obb.equity.price.historical("SHOP", provider="tmx"))
if equity is not None:
    e = equity.reset_index()
    probar("1 Tecnico", "technical.atr(14)",
           lambda: obb.technical.atr(data=e, index="date", high="high", low="low", close="close"))
    probar("1 Tecnico", "technical.realized_vol",
           lambda: obb.technical.realized_volatility(
               data=e, index="date", high="high", low="low", close="close"))

# ------------------------------------------------------------ 2. FUNDAMENTAL
print("\n### 2. FUNDAMENTAL (SEC EDGAR, sin clave)")
probar("2 Fundamental", "equity.fundamental.balance",
       lambda: obb.equity.fundamental.balance("AAPL", provider="sec", limit=4))
probar("2 Fundamental", "equity.fundamental.income",
       lambda: obb.equity.fundamental.income("AAPL", provider="sec", limit=4))
probar("2 Fundamental", "equity.fundamental.cash",
       lambda: obb.equity.fundamental.cash("AAPL", provider="sec", limit=4))

# ------------------------------------------------------------------ 3. MACRO
print("\n### 3. MACRO (Reserva Federal, Tesoro, OECD, BLS)")
probar("3 Macro", "fixedincome.rate.effr",
       lambda: obb.fixedincome.rate.effr(provider="federal_reserve"))
probar("3 Macro", "government.yield_curve",
       lambda: obb.fixedincome.government.yield_curve(provider="federal_reserve"))
probar("3 Macro", "government.treasury_rates",
       lambda: obb.fixedincome.government.treasury_rates(provider="federal_reserve"))
probar("3 Macro", "economy.cpi",
       lambda: obb.economy.cpi(provider="oecd"))
probar("3 Macro", "economy.gdp.real",
       lambda: obb.economy.gdp.real(provider="oecd"))
probar("3 Macro", "currency.price.historical EURUSD",
       lambda: obb.currency.price.historical("EURUSD", provider="ecb"))

# ------------------------------------------------------------- 4. SENTIMIENTO
print("\n### 4. SENTIMIENTO / POSICIONAMIENTO (CFTC COT, Deribit)")
probar("4 Sentimiento", "cftc.cot_search",
       lambda: obb.cftc.cot_search(provider="cftc"))
probar("4 Sentimiento", "cftc.cot_positioning",
       lambda: obb.cftc.cot_positioning(provider="cftc"))
probar("4 Sentimiento", "deribit.rates.funding_history",
       lambda: obb.deribit.rates.funding_history(provider="deribit"))
probar("4 Sentimiento", "equity.shorts.short_interest",
       lambda: obb.equity.shorts.short_interest(symbol="AAPL"))

# ------------------------------------------------------------- 5. ORDER FLOW
print("\n### 5. ORDER FLOW (libro de ordenes real)")
probar("5 Order flow", "deribit.market.order_book",
       lambda: obb.deribit.market.order_book(symbol="BTC-PERPETUAL", provider="deribit"))
probar("5 Order flow", "deribit.market.ticker",
       lambda: obb.deribit.market.ticker(symbol="BTC-PERPETUAL", provider="deribit"))
probar("5 Order flow", "deribit.market.trades",
       lambda: obb.deribit.market.trades(provider="deribit"))
hueco("5 Order flow", "DOM/footprint acciones", "requiere datos nivel 2 de pago")

# ---------------------------------------------------------------- 6. ON-CHAIN
print("\n### 6. ON-CHAIN")
hueco("6 On-chain", "MVRV / netflow / SOPR", "no hay provider on-chain instalado")

# ------------------------------------------------------------ 7. CUANTITATIVO
print("\n### 7. CUANTITATIVO / ESTADISTICO")
probar("7 Cuantitativo", "famafrench.factors",
       lambda: obb.famafrench.factors(provider="famafrench"))
if spx is not None:
    probar("7 Cuantitativo", "quantitative.summary",
           lambda: obb.quantitative.summary(data=spx.reset_index(), index="date", target="close"))
    probar("7 Cuantitativo", "econometrics.ols_regression",
           lambda: obb.econometrics.ols_regression(
               data=obb.famafrench.factors(provider="famafrench").to_df().reset_index(),
               y_column="mkt_rf", x_columns=["smb", "hml"]))
probar("7 Cuantitativo", "famafrench.us_portfolio_returns",
       lambda: obb.famafrench.us_portfolio_returns(provider="famafrench"))

# -------------------------------------------------- 8. CONDUCTUAL/ESTACIONAL
print("\n### 8. CONDUCTUAL / ESTACIONALIDAD")
if spx is not None:
    import pandas as pd

    s = spx.copy()
    s.index = pd.to_datetime(s.index)
    mensual = s["close"].resample("ME").last().pct_change().dropna() * 100
    tabla = mensual.groupby(mensual.index.month).agg(["mean", "count"]).round(2)
    tabla.index = [pd.Timestamp(2024, m, 1).strftime("%b") for m in tabla.index]
    print("[OK  ] 8 Conductual        estacionalidad SPX         estacional mensual de 13057 dias")
    print(tabla.to_string())
    resultados.append(("8 Conductual", "estacionalidad SPX", OK, f"{len(tabla)} meses"))

# ------------------------------------------------------------------- RESUMEN
print("\n" + "=" * 100)
print("RESUMEN")
print("=" * 100)
conteo = {k: sum(1 for r in resultados if r[2] == k) for k in (OK, ERR, HUECO)}
print(f"  funcionando: {conteo[OK]}   con error: {conteo[ERR]}   huecos: {conteo[HUECO]}")
print(f"  cache en:    {Path(__file__).resolve().parents[1] / 'data' / 'cache'}")
print("\n  Detalle de errores:")
for fam, nom, est, msg in resultados:
    if est != OK:
        print(f"    [{est}] {fam:<20} {nom:<26} {msg}")
