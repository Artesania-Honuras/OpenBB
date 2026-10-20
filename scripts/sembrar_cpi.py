"""Reconstruye la cache del CPI desde el contexto (reparacion puntual).

Por que existe
--------------
El 2026-10-20 la OECD empezo a devolver solo **20 meses** de CPI (2025-01 ->
2026-09). El refresco diario, que fuerza la descarga, sobrescribio la cache y el
contexto habria perdido el CPI desde 1956: 36.509 NaN y `cpi_yoy` empezando en
junio de 2026. El validador no lo vio porque solo miraba columnas enteras y la
ultima fila.

La cache se reconstruye **sin inventar**: el contexto se construyo como
`value * 100`, desplazado 45 dias por publicacion y rellenado hacia adelante.
Invirtiendo ese proceso se recuperan los meses exactos (comprobado: diferencia
0,0 frente al contexto restaurado en 25.816 dias).

Uso:
    python scripts\\sembrar_cpi.py --autoprueba   # solo comprueba, no escribe
    python scripts\\sembrar_cpi.py                # escribe la cache
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import pandas as pd  # noqa: E402

from obb_env import CACHE_DIR, _combinar, _temporal  # noqa: E402
from puente_freqtrade import CONTEXT_FILE  # noqa: E402

RETRASO_CPI = 45
CACHE = CACHE_DIR / "economy_cpi.parquet"


def reconstruir(contexto: pd.DataFrame) -> pd.Series:
    """Serie mensual (fraccion) invertida del `cpi_yoy` diario del contexto."""
    s = contexto["cpi_yoy"].dropna()
    if s.empty:
        raise ValueError("el contexto no tiene cpi_yoy")
    meses = pd.date_range(s.index.min() - pd.Timedelta(days=RETRASO_CPI), s.index.max(), freq="MS")
    valores: dict[pd.Timestamp, float] = {}
    for mes in meses:
        publicado = mes + pd.Timedelta(days=RETRASO_CPI)
        if publicado in s.index:
            valores[mes] = float(s.loc[publicado])
    rec = pd.Series(valores, name="value").sort_index()
    if rec.isna().any():
        raise ValueError("la reconstruccion dejo huecos")
    return rec / 100.0


def comparar(contexto: pd.DataFrame, rec: pd.Series) -> tuple[int, float]:
    """Devuelve (dias comparados, diferencia maxima) contra el contexto."""
    diario = (rec * 100.0).copy()
    diario.index = diario.index + pd.Timedelta(days=RETRASO_CPI)
    calendario = pd.date_range(contexto.index.min(), contexto.index.max(), freq="D")
    diario = diario.reindex(calendario).ffill()
    real = contexto["cpi_yoy"].dropna()
    comp = pd.DataFrame({"real": real, "rec": diario.reindex(real.index)}).dropna()
    if comp.empty:
        return 0, float("inf")
    return len(comp), float((comp["real"] - comp["rec"]).abs().max())


def sembrar() -> int:
    contexto = pd.read_parquet(CONTEXT_FILE)
    contexto.index = pd.to_datetime(contexto.index)
    contexto = contexto.sort_index()

    rec = reconstruir(contexto)
    dias, dif = comparar(contexto, rec)
    print(f"reconstruccion: {len(rec)} meses · {rec.index.min().date()} -> {rec.index.max().date()}")
    print(f"contraste:      {dias:,} dias · diferencia maxima {dif:.2e}")
    if dif > 1e-9:
        print("FALLA: la reconstruccion no reproduce el contexto; no se escribe nada")
        return 1

    if not CACHE.exists():
        print(f"FALLA: no existe la plantilla {CACHE}")
        return 1
    plantilla = pd.read_parquet(CACHE)
    marco = pd.DataFrame(index=rec.index, columns=plantilla.columns)
    for col in plantilla.columns:
        if col != "value":
            marco[col] = plantilla[col].iloc[-1]
    marco["value"] = rec.to_numpy()
    marco.index.name = plantilla.index.name
    marco.to_parquet(CACHE)

    verificado = pd.read_parquet(CACHE)
    print(f"cache escrita:  {len(verificado)} filas · {verificado.index.min()} -> {verificado.index.max()}")
    if len(verificado) != len(rec):
        print("FALLA: la cache escrita no tiene el tamano esperado")
        return 1
    print("OK: cache del CPI sembrada con la historia del contexto")
    return 0


def autoprueba() -> int:
    contexto = pd.read_parquet(CONTEXT_FILE)
    contexto.index = pd.to_datetime(contexto.index)
    contexto = contexto.sort_index()

    rec = reconstruir(contexto)
    dias, dif = comparar(contexto, rec)

    casos: list[tuple[str, bool]] = []
    casos.append(("reconstruccion cubre >= 800 meses", len(rec) >= 800))
    casos.append(("reconstruccion sin huecos", not rec.isna().any()))
    casos.append((f"reconstruccion exacta ({dias:,} dias, dif {dif:.1e})", dif <= 1e-9))

    idx = pd.date_range("2026-01-01", periods=10, freq="D")
    viejo = pd.DataFrame({"value": [1.0] * 10}, index=idx)
    nuevo = pd.DataFrame({"value": [2.0] * 3}, index=idx[-3:])
    mezcla = _combinar(viejo, nuevo)
    casos.append((
        "la cache no encoge y lo nuevo gana",
        len(mezcla) == 10 and float(mezcla["value"].iloc[0]) == 1.0 and float(mezcla["value"].iloc[-1]) == 2.0,
    ))

    posicional = pd.DataFrame({"value": [9.0] * 3})
    casos.append(("RangeIndex no se mezcla por posicion", len(_combinar(viejo, posicional)) == 3))
    casos.append(("_temporal distingue fechas de posiciones", _temporal(idx) and not _temporal(posicional.index)))

    correctos = 0
    for nombre, bien in casos:
        correctos += int(bien)
        print(f"  {'OK  ' if bien else 'FALLA'}  {nombre}")
    print(f"\n{correctos}/{len(casos)} pruebas del sembrado")
    return 0 if correctos == len(casos) else 1


if __name__ == "__main__":
    sys.exit(autoprueba() if "--autoprueba" in sys.argv else sembrar())
