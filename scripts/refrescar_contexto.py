"""Refresco diario del contexto macro (P2).

Por qué existe
--------------
Hasta hoy `contexto_diario.parquet` se reconstruia a mano:

    .\\venvs\\openbb\\Scripts\\python.exe scripts\\puente_freqtrade.py --exportar --forzar

Un contexto que envejece no avisa: el panel sigue enseñando el ultimo dato y
las validaciones siguen corriendo. Este script convierte el refresco en un
trabajo diario **verificado**, no en una costumbre.

Que hace, en orden
------------------
1. Descarga las 10 fuentes con `forzar=True` (ignora la cache: si no, no
   refresca nada).
2. **Valida** antes de guardar: columnas, filas que no retroceden, fecha final,
   rangos plausibles, saltos imposibles frente al contexto anterior y frescura
   de cada cache. Un proveedor que devuelve ceros o cambia de unidades se
   detecta aqui, no dentro de tres meses.
3. Si algo falla, **conserva el contexto anterior** y sale con codigo 1.
4. Si todo pasa, guarda con **escritura atomica** (temporal + `os.replace`) y
   deja una copia del anterior en `contexto_diario_anterior.parquet`.
5. Escribe una linea de resultado en `data/refresco_contexto.log`.

Uso:
    python scripts\\refrescar_contexto.py
    python scripts\\refrescar_contexto.py --autoprueba   # prueba el validador
"""

from __future__ import annotations

import os
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

os.environ.setdefault("PYTHONUTF8", "1")
os.environ.setdefault("OPENBB_AUTO_BUILD", "false")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import pandas as pd  # noqa: E402

from puente_freqtrade import CONTEXT_FILE, construir_contexto  # noqa: E402

CACHE = ROOT / "data" / "cache"
LOG = ROOT / "data" / "refresco_contexto.log"
ANTERIOR = CONTEXT_FILE.with_name("contexto_diario_anterior.parquet")
CSV = CONTEXT_FILE.with_suffix(".csv")

COLUMNAS = [
    "yield_2y", "yield_10y", "slope_10y_2y", "fed_funds", "vix", "spx",
    "eurusd", "cpi_yoy", "gdp_yoy", "cot_net", "ff_mkt_rf", "ff_smb",
    "ff_hml", "funding_btc_anual",
]

# Edad maxima (dias) del ULTIMO dato de cada cache, segun su calendario de
# publicacion. No es la del contexto (que va relleno hacia adelante): es la de
# la fuente. Si una fuente se para, esto lo dice.
FRESCURA_CACHE = {
    "government_treasury_rates": 8,
    "fixedincome_rate_effr": 8,
    "vix": 8,
    "spx": 8,
    "currency_price_historical_eurusd": 8,
    "economy_cpi": 90,
    "economy_gdp_real": 240,
    "cftc_cot_positioning": 21,
    "famafrench_factors": 110,
    "funding_btcusdt": 4,
}

# Rangos plausibles del ultimo valor. Atrapan unidades equivocadas (4,77 en vez
# de 0,0477) y proveedores que devuelven ceros.
RANGOS = {
    "vix": (5.0, 120.0),
    "yield_2y": (-0.02, 0.25),
    "yield_10y": (-0.02, 0.25),
    "slope_10y_2y": (-0.03, 0.05),
    "fed_funds": (0.0, 0.25),
    "spx": (100.0, 50_000.0),
    "eurusd": (0.5, 2.5),
    "cpi_yoy": (-5.0, 30.0),
    "gdp_yoy": (-20.0, 30.0),
    "cot_net": (-1_000.0, 1_000.0),
    "ff_mkt_rf": (-50.0, 50.0),
    "ff_smb": (-50.0, 50.0),
    "ff_hml": (-50.0, 50.0),
    "funding_btc_anual": (-500.0, 5_000.0),
}

# Cambio relativo maximo del ultimo valor frente al contexto anterior. Generoso:
# no mide volatilidad normal, mide un cambio de unidad o de escala.
CAMBIO_MAX = {
    "vix": 2.0,
    "spx": 0.5,
    "eurusd": 0.5,
    "yield_2y": 5.0,
    "yield_10y": 5.0,
    "slope_10y_2y": 5.0,
    "fed_funds": 5.0,
    "cpi_yoy": 2.0,
    "gdp_yoy": 2.0,
    "cot_net": 5.0,
    "funding_btc_anual": 10.0,
}


# --------------------------------------------------------------------------
def _log(nivel: str, mensaje: str) -> None:
    """Anade una linea al log (UTF-8) y la imprime."""
    LOG.parent.mkdir(parents=True, exist_ok=True)
    linea = f"{datetime.now():%Y-%m-%d %H:%M:%S}  {nivel:<6} {mensaje}"
    if LOG.exists() and LOG.stat().st_size > 2 * 1024 * 1024:
        previas = LOG.read_text(encoding="utf-8", errors="replace").splitlines()[-500:]
        LOG.write_text("\n".join(previas) + "\n", encoding="utf-8", newline="\n")
    with open(LOG, "a", encoding="utf-8", newline="\n") as f:
        f.write(linea + "\n")
    print(linea)


def _fechas(df: pd.DataFrame) -> pd.DatetimeIndex:
    """Saca la columna de fecha de una cache, sea indice o columna."""
    if "report_date" in df.columns:
        s = pd.DatetimeIndex(pd.to_datetime(df["report_date"]))
    elif "date" in df.columns:
        s = pd.DatetimeIndex(pd.to_datetime(df["date"]))
    else:
        s = pd.DatetimeIndex(pd.to_datetime(df.index))
    if s.tz is not None:
        s = s.tz_convert("UTC").tz_localize(None)
    return s


def revisar_caches(hoy: pd.Timestamp) -> list[str]:
    """Devuelve los problemas de frescura de las fuentes."""
    problemas: list[str] = []
    for nombre, maximo in FRESCURA_CACHE.items():
        ruta = CACHE / f"{nombre}.parquet"
        if not ruta.exists():
            problemas.append(f"cache {nombre}: no existe")
            continue
        try:
            ultimo = _fechas(pd.read_parquet(ruta)).max().normalize()
        except Exception as e:  # noqa: BLE001
            problemas.append(f"cache {nombre}: no se pudo leer ({type(e).__name__})")
            continue
        edad = (hoy - ultimo).days
        if edad > maximo:
            problemas.append(
                f"cache {nombre}: ultimo {ultimo.date()} ({edad} dias, maximo {maximo})"
            )
    return problemas


def validar(
    nuevo: pd.DataFrame,
    anterior: pd.DataFrame | None,
    hoy: pd.Timestamp,
    revisar_fuentes: bool = True,
) -> list[str]:
    """Lista de problemas. Vacia = se puede guardar."""
    problemas: list[str] = []

    faltan = [c for c in COLUMNAS if c not in nuevo.columns]
    sobran = [c for c in nuevo.columns if c not in COLUMNAS]
    if faltan:
        problemas.append(f"faltan columnas: {', '.join(faltan)}")
    if sobran:
        problemas.append(f"columnas de mas: {', '.join(sobran)}")

    if anterior is not None and len(nuevo) < len(anterior):
        problemas.append(f"filas: {len(nuevo)} < {len(anterior)} (el contexto no debe encoger)")

    fin = pd.Timestamp(nuevo.index.max()).normalize()
    # El contexto NO termina hoy: cada serie se desplaza segun su retraso de
    # publicacion, asi que el cierre de hoy queda etiquetado como manana. Es
    # correcto y es lo que hace `merge_asof`: una vela de manana 00:00 puede
    # ver el cierre de hoy. Lo que no vale es quedarse corto ni irse de largo.
    if fin < hoy:
        problemas.append(f"fecha final {fin.date()} anterior a hoy {hoy.date()}")
    elif fin > hoy + pd.Timedelta(days=1):
        problemas.append(f"fecha final {fin.date()} en el futuro (hoy {hoy.date()})")

    vacias = [c for c in nuevo.columns if nuevo[c].isna().all()]
    if vacias:
        problemas.append(f"columnas enteras a NaN: {', '.join(vacias)}")

    # Un proveedor que recorta su ventana no debe borrar historia ya validada.
    # Esto habría cazado el CPI de octubre de 2026: la OECD devolvió 20 meses y
    # el contexto perdió 1956-2025 sin que ninguna otra comprobación lo viera.
    if anterior is not None and len(anterior) and len(nuevo):
        comunes = nuevo.index.intersection(anterior.index)
        for col in nuevo.columns:
            if col not in anterior.columns:
                continue
            perdidos = anterior.loc[comunes, col].notna() & nuevo.loc[comunes, col].isna()
            n = int(perdidos.sum())
            if n:
                ejemplo = pd.Timestamp(perdidos[perdidos].index[0]).date()
                problemas.append(
                    f"{col}: {n} valores historicos pasan a NaN (p. ej. {ejemplo})"
                )

    if len(nuevo):
        ultima = nuevo.iloc[-1]
        claves = ["vix", "yield_2y", "yield_10y", "slope_10y_2y", "spx", "eurusd",
                  "funding_btc_anual"]
        nulos = [c for c in claves if c in nuevo.columns and pd.isna(ultima[c])]
        if nulos:
            problemas.append(f"ultima fila con NaN en: {', '.join(nulos)}")

        for col, (minimo, maximo) in RANGOS.items():
            if col not in nuevo.columns or pd.isna(ultima[col]):
                continue
            valor = float(ultima[col])
            if not (minimo <= valor <= maximo):
                problemas.append(
                    f"{col}={valor:.6g} fuera de rango [{minimo:g}, {maximo:g}]"
                )

    if anterior is not None and len(anterior) and len(nuevo):
        for col, maximo in CAMBIO_MAX.items():
            if col not in nuevo.columns or col not in anterior.columns:
                continue
            a, b = float(anterior[col].iloc[-1]), float(nuevo[col].iloc[-1])
            if pd.isna(a) or pd.isna(b):
                continue
            rel = abs(b - a) / max(abs(a), 1e-9)
            if rel > maximo:
                problemas.append(
                    f"{col}: variacion {rel:.1f}x frente al anterior ({a:.6g} -> {b:.6g})"
                )

    if revisar_fuentes:
        problemas.extend(revisar_caches(hoy))

    return problemas


def _guardar_atomico(contexto: pd.DataFrame) -> None:
    """Escribe parquet y CSV sin dejar el archivo a medias si falla."""
    if CONTEXT_FILE.exists():
        shutil.copy2(CONTEXT_FILE, ANTERIOR)
    temporal = CONTEXT_FILE.with_suffix(".tmp.parquet")
    contexto.to_parquet(temporal)
    os.replace(temporal, CONTEXT_FILE)
    contexto.to_csv(CSV)


# --------------------------------------------------------------------------
def autoprueba() -> int:
    """Comprueba que el validador RECHAZA contextos malos. Sin red."""
    ctx = pd.read_parquet(CONTEXT_FILE)
    ctx.index = pd.to_datetime(ctx.index)
    hoy = pd.Timestamp.today().normalize()

    casos: list[tuple[str, pd.DataFrame, str]] = []

    casos.append(("falta una columna", ctx.drop(columns=["vix"]), "columna"))

    c = ctx.copy()
    c.loc[c.index[-1], "vix"] = 0.0
    casos.append(("vix = 0", c, "vix"))

    casos.append(("fecha final atrasada", ctx.iloc[:-3], "fecha"))

    c = ctx.copy()
    c.loc[c.index[-1], "vix"] = float(ctx["vix"].iloc[-1]) * 10
    casos.append(("vix x10", c, "vix"))

    c = ctx.copy()
    c["spx"] = float("nan")
    casos.append(("columna entera NaN", c, "NaN"))

    c = ctx.copy()
    c.loc["2010-01-01":"2010-03-01", "cpi_yoy"] = float("nan")
    casos.append(("historia a NaN", c, "NaN"))

    c = ctx.copy()
    c["columna_extra"] = 1.0
    casos.append(("columna de mas", c, "columna"))

    correctos = 0
    for nombre, roto, esperado in casos:
        problemas = validar(roto, ctx, hoy, revisar_fuentes=False)
        detectado = any(esperado in p for p in problemas)
        correctos += int(detectado)
        print(f"  {'OK  ' if detectado else 'FALLA'}  {nombre:<24} -> "
              f"{problemas[0] if problemas else 'no detectado'}")

    bueno = validar(ctx, ctx, hoy, revisar_fuentes=False)
    correctos += int(not bueno)
    print(f"  {'OK  ' if not bueno else 'FALLA'}  {'contexto sano':<24} -> "
          f"{'sin problemas' if not bueno else bueno[0]}")

    total = len(casos) + 1
    print(f"\n{correctos}/{total} pruebas del validador")
    return 0 if correctos == total else 1


def main(forzar_prueba: bool = False) -> int:
    if forzar_prueba:
        return autoprueba()

    hoy = pd.Timestamp.today().normalize()
    anterior = None
    if CONTEXT_FILE.exists():
        anterior = pd.read_parquet(CONTEXT_FILE)
        anterior.index = pd.to_datetime(anterior.index)

    t0 = time.time()
    try:
        contexto = construir_contexto(forzar=True)
    except Exception as e:  # noqa: BLE001
        segundos = time.time() - t0
        _log("FALLO", f"descarga ({segundos:.0f} s): {type(e).__name__}: {e} · "
                      "se conserva el contexto anterior")
        return 1

    problemas = validar(contexto, anterior, hoy)
    if problemas:
        segundos = time.time() - t0
        _log("FALLO", f"validacion ({segundos:.0f} s): {problemas[0]} · "
                      "se conserva el contexto anterior")
        for p in problemas[1:5]:
            _log("      ", p)
        return 1

    try:
        _guardar_atomico(contexto)
    except Exception as e:  # noqa: BLE001
        _log("FALLO", f"guardado: {type(e).__name__}: {e}")
        return 1

    segundos = time.time() - t0
    _log(
        "OK",
        f"{len(contexto):,} filas · {len(contexto.columns)} columnas · "
        f"ultimo {contexto.index[-1].date()} · "
        f"vix {contexto['vix'].iloc[-1]:.2f} · "
        f"{segundos:.0f} s",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(forzar_prueba="--autoprueba" in sys.argv))
