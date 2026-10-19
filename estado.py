"""Checklist de estado del proyecto OpenBB local.

Solo lectura: no escribe, no reinicia, no modifica nada.
Imprime una tabla con ✅/❌ y un veredicto.

Uso:
    .\\venvs\\openbb\\Scripts\\python.exe estado.py

Codigos de salida:
    0 = todo OK
    1 = fallo critico (API, datos, config o repo)
    2 = degradado (fallo no critico: externos, freqtrade, maquina)
"""

from __future__ import annotations

import ast
import ctypes
import json
import os
import socket
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
API = "http://127.0.0.1:6900"

# Mismo arreglo que los lanzadores: el almacen de Windows falla con la BCE.
_CERT = ROOT / "venvs" / "openbb" / "Lib" / "site-packages" / "certifi" / "cacert.pem"
if _CERT.exists():
    os.environ.setdefault("SSL_CERT_FILE", str(_CERT))
    os.environ.setdefault("REQUESTS_CA_BUNDLE", str(_CERT))

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass


# --------------------------------------------------------------------------
# Utilidades
# --------------------------------------------------------------------------
def _http(url: str, timeout: int = 10) -> tuple[bool, str, float]:
    """Devuelve (alcanzable, detalle, milisegundos). Cualquier HTTP cuenta."""
    inicio = datetime.now()
    try:
        req = Request(url, headers={"User-Agent": "estado-openbb/1.0"})
        with urlopen(req, timeout=timeout) as r:
            ms = (datetime.now() - inicio).total_seconds() * 1000
            return True, f"HTTP {r.status} en {ms:.0f} ms", ms
    except HTTPError as e:
        ms = (datetime.now() - inicio).total_seconds() * 1000
        return True, f"HTTP {e.code} en {ms:.0f} ms", ms
    except (URLError, TimeoutError, OSError) as e:
        ms = (datetime.now() - inicio).total_seconds() * 1000
        return False, f"{type(e).__name__} tras {ms:.0f} ms", ms


def _puerto(puerto: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", puerto), timeout=2):
            return True
    except OSError:
        return False


def _git(*args: str) -> tuple[int, str]:
    try:
        r = subprocess.run(
            ["git", *args], cwd=ROOT, capture_output=True, text=True, timeout=20
        )
        return r.returncode, (r.stdout or r.stderr).strip()
    except Exception as e:  # noqa: BLE001
        return 1, str(e)


def _ram() -> tuple[float, float]:
    class Memoria(ctypes.Structure):
        _fields_ = [
            ("dwLength", ctypes.c_ulong),
            ("dwMemoryLoad", ctypes.c_ulong),
            ("ullTotalPhys", ctypes.c_ulonglong),
            ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong),
            ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong),
            ("ullAvailVirtual", ctypes.c_ulonglong),
            ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
        ]

    m = Memoria()
    m.dwLength = ctypes.sizeof(Memoria)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
    gb = 1024 ** 3
    return m.ullTotalPhys / gb, m.ullAvailPhys / gb


# --------------------------------------------------------------------------
# Chequeos
# --------------------------------------------------------------------------
def revisar() -> list[dict]:
    filas: list[dict] = []

    def add(bloque: str, chequeo: str, ok: bool, evidencia: str, critico: bool = False):
        filas.append(
            {"bloque": bloque, "chequeo": chequeo, "ok": ok,
             "evidencia": evidencia, "critico": critico}
        )

    # --- Servicio ---------------------------------------------------------
    add("Servicio", "Puerto 6900", _puerto(6900),
        "escuchando" if _puerto(6900) else "sin respuesta", critico=True)

    ok, detalle, _ = _http(f"{API}/", timeout=10)
    add("Servicio", "HTTP raiz", ok, detalle, critico=True)

    ok, detalle, _ = _http(f"{API}/docs", timeout=10)
    add("Servicio", "Swagger /docs", ok, detalle)

    add("Servicio", "Panel visual 8501", _puerto(8501),
        "escuchando" if _puerto(8501) else "detenido (run-openbb-app.ps1)")

    try:
        with urlopen(
            f"{API}/api/v1/fixedincome/rate/effr?provider=federal_reserve", timeout=60
        ) as r:
            data = json.loads(r.read())
        n = len(data.get("results", []))
        add("Servicio", "Llamada funcional (effr)", n > 0, f"{n} filas", critico=True)
    except Exception as e:  # noqa: BLE001
        add("Servicio", "Llamada funcional (effr)", False, type(e).__name__, critico=True)

    # --- Datos ------------------------------------------------------------
    ruta = ROOT / "data" / "context" / "contexto_diario.parquet"
    if ruta.exists():
        try:
            import pandas as pd

            df = pd.read_parquet(ruta)
            ultima = pd.to_datetime(df.index).max().date()
            edad = (datetime.now(timezone.utc).date() - ultima).days
            add("Datos", "contexto_diario.parquet", edad <= 2,
                f"{len(df):,} x {len(df.columns)} · ultimo {ultima} ({edad} d)",
                critico=True)
            faltan = 14 - len(df.columns)
            add("Datos", "Esquema 14 columnas", faltan <= 0,
                f"{len(df.columns)} columnas, faltan {max(0, faltan)}")
        except Exception as e:  # noqa: BLE001
            add("Datos", "contexto_diario.parquet", False, type(e).__name__, critico=True)
    else:
        add("Datos", "contexto_diario.parquet", False, "no existe", critico=True)

    if (ROOT / "data" / "cache").exists():
        n = len(list((ROOT / "data" / "cache").glob("*.parquet")))
        add("Datos", "Cache parquet", n > 0, f"{n} archivos")
    else:
        add("Datos", "Cache parquet", False, "no existe")

    # --- Configuracion ----------------------------------------------------
    cfg = ROOT / "freqtrade_bridge" / "backtest.json"
    if cfg.exists():
        try:
            j = json.loads(cfg.read_text(encoding="utf-8"))
            pares = len(j.get("exchange", {}).get("pair_whitelist", []))
            add("Config", "backtest.json", pares > 0,
                f"JSON valido · {pares} pares · {j.get('timeframe')}", critico=True)
        except Exception as e:  # noqa: BLE001
            add("Config", "backtest.json", False, type(e).__name__, critico=True)
    else:
        add("Config", "backtest.json", False, "no existe", critico=True)

    estrategias = sorted((ROOT / "strategies").glob("*.py"))
    if estrategias:
        malas = []
        for p in estrategias:
            try:
                ast.parse(p.read_text(encoding="utf-8"))
            except SyntaxError:
                malas.append(p.name)
        add("Config", "Estrategias (sintaxis)", not malas,
            f"{len(estrategias) - len(malas)}/{len(estrategias)} validas"
            + (f" · fallan: {', '.join(malas)}" if malas else ""))
    else:
        add("Config", "Estrategias (sintaxis)", False, "no hay archivos")

    # --- Externos ---------------------------------------------------------
    externos = [
        ("Fed", "https://markets.newyorkfed.org/api/rates/unsecured/effr/last/1.json"),
        ("BCE", "https://data-api.ecb.europa.eu/service/data/EXR/D.USD.EUR.SP00.A?lastNObservations=1"),
        ("CBOE", "https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv"),
        ("CFTC", "https://www.cftc.gov/"),
    ]
    for nombre, url in externos:
        ok, detalle, _ = _http(url, timeout=12)
        add("Externos", nombre, ok, detalle)

    # --- Freqtrade (solo observacion) -------------------------------------
    try:
        out = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq freqtrade.exe", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, timeout=20,
        ).stdout
        n = sum(1 for linea in out.splitlines() if linea.startswith('"freqtrade.exe"'))
        add("Freqtrade", "Procesos", n > 0, f"{n} procesos")
    except Exception as e:  # noqa: BLE001
        add("Freqtrade", "Procesos", False, type(e).__name__)

    puertos = [p for p in (8080, 8081) if _puerto(p)]
    add("Freqtrade", "Puertos 8080/8081", bool(puertos),
        f"{len(puertos)} escuchando" if puertos else "ninguno")

    # --- Repo -------------------------------------------------------------
    codigo, rama = _git("rev-parse", "--abbrev-ref", "HEAD")
    if codigo != 0:
        add("Repo", "Git inicializado", False, "no es un repositorio", critico=True)
    else:
        add("Repo", "Git inicializado", True, f"rama {rama}", critico=True)

        _, status = _git("status", "--porcelain")
        add("Repo", "Sin cambios pendientes", status == "",
            "limpio" if status == "" else f"{len(status.splitlines())} archivos",
            critico=True)

        _, remoto = _git("remote", "get-url", "origin")
        add("Repo", "Remoto origin", bool(remoto), remoto.split("//")[-1] if remoto else "sin remoto")

        if remoto:
            _, ahead = _git("rev-list", "--count", "@{u}..HEAD")
            if not ahead.isdigit():
                _, ahead = _git("rev-list", "--count", "origin/main..HEAD")
            try:
                n = int(ahead)
                add("Repo", "Sincronizado (ahead)", n == 0, f"{n} commits sin subir")
            except ValueError:
                add("Repo", "Sincronizado (ahead)", False, ahead[:60])

    # --- Maquina ----------------------------------------------------------
    uso = __import__("shutil").disk_usage("C:\\")
    libre_gb = uso.free / 1024 ** 3
    add("Maquina", "Disco C:", libre_gb >= 5,
        f"{libre_gb:.1f} GB libres de {uso.total / 1024 ** 3:.1f}")

    total, disponible = _ram()
    add("Maquina", "RAM", disponible >= 0.5,
        f"{disponible:.1f} GB libres de {total:.1f}")

    try:
        ms = ctypes.windll.kernel32.GetTickCount64()
        horas, minutos = divmod(ms // 1000 // 60, 60)
        add("Maquina", "Uptime", True, f"{horas} h {minutos} min")
    except Exception:  # noqa: BLE001
        add("Maquina", "Uptime", True, "n/d")

    return filas


# --------------------------------------------------------------------------
def main() -> int:
    filas = revisar()

    ancho_bloque, ancho_chequeo = 12, 30
    print("=" * 100)
    print(f" ESTADO DEL SISTEMA — OpenBB local   ·   {datetime.now():%Y-%m-%d %H:%M:%S}")
    print("=" * 100)
    print(f" {'BLOQUE':<{ancho_bloque}} {'CHEQUEO':<{ancho_chequeo}} ESTADO  EVIDENCIA")
    print("-" * 100)
    for f in filas:
        estado = "✅" if f["ok"] else "❌"
        print(f" {f['bloque']:<{ancho_bloque}} {f['chequeo']:<{ancho_chequeo}} "
              f"{estado:<6}  {f['evidencia']}")
    print("=" * 100)

    fallos = [f for f in filas if not f["ok"]]
    criticos = [f for f in fallos if f["critico"]]

    if criticos:
        print(f" VEREDICTO: ❌ CRITICO — {len(criticos)} fallo(s) esencial(es): "
              + ", ".join(f["chequeo"] for f in criticos))
        return 1
    if fallos:
        print(f" VEREDICTO: ⚠️  DEGRADADO — {len(fallos)} fallo(s) no critico(s): "
              + ", ".join(f["chequeo"] for f in fallos))
        return 2

    print(f" VEREDICTO: ✅ TODO OK — {len(filas)}/{len(filas)} chequeos")
    return 0


if __name__ == "__main__":
    sys.exit(main())
