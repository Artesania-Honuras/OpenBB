"""Entorno y utilidades para OpenBB local.

Resuelve de una vez los tres problemas conocidos de esta instalacion:
  1. SSL del BCE  -> fuerza el bundle de certifi
  2. auto-build   -> lo desactiva (el build ya se ejecuto una vez)
  3. caché        -> guarda cada consulta en data/cache/ como parquet

Uso:
    from obb_env import obb_local, consultar

    obb = obb_local()
    df = consultar("effr", lambda: obb.fixedincome.rate.effr(provider="federal_reserve"))
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = ROOT / "data" / "cache"
CERT_BUNDLE = ROOT / "venvs" / "openbb" / "Lib" / "site-packages" / "certifi" / "cacert.pem"


def preparar_entorno() -> Path:
    """Aplica la configuracion necesaria y devuelve el directorio de cache."""
    if CERT_BUNDLE.exists():
        os.environ.setdefault("SSL_CERT_FILE", str(CERT_BUNDLE))
        os.environ.setdefault("REQUESTS_CA_BUNDLE", str(CERT_BUNDLE))
    os.environ.setdefault("OPENBB_AUTO_BUILD", "false")
    os.environ.setdefault("PYTHONUTF8", "1")
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR


def obb_local():
    """Devuelve el objeto `obb` con el entorno ya preparado."""
    preparar_entorno()
    from openbb import obb  # import tardio: el entorno debe estar listo antes

    return obb


def consultar(nombre: str, fn: Callable, forzar: bool = False):
    """Ejecuta `fn()` y cachea el DataFrame en data/cache/<nombre>.parquet.

    Parameters
    ----------
    nombre : str
        Nombre del archivo de cache (sin extension).
    fn : Callable
        Funcion que devuelve un objeto OpenBB con `.to_df()`.
    forzar : bool
        Si es True, ignora la cache y vuelve a consultar.
    """
    import pandas as pd

    preparar_entorno()
    path = CACHE_DIR / f"{nombre}.parquet"
    if path.exists() and not forzar:
        return pd.read_parquet(path)

    df = fn().to_df()
    try:
        df.to_parquet(path)
    except Exception:
        df.to_csv(CACHE_DIR / f"{nombre}.csv")
    return df


def mostrar(df, n: int = 3) -> None:
    """Imprime las ultimas `n` filas de un DataFrame."""
    print(df.tail(n).to_string()[:1500])
