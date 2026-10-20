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
import time
from datetime import datetime
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
def _http(url: str, timeout: int = 10, reintentos: int = 1) -> tuple[bool, str, float]:
    """Devuelve (ok, detalle, milisegundos).

    Un 2xx/3xx cuenta como alcanzable. Un 4xx/5xx **no**: que el servidor
    conteste con un error no es que el dato esté disponible (un 504 de la BCE
    se marcaba ✅). Los 5xx se reintentan una vez porque son la forma típica
    de un fallo transitorio de pasarela.
    """
    for intento in range(reintentos + 1):
        inicio = datetime.now()
        try:
            req = Request(url, headers={"User-Agent": "estado-openbb/1.0"})
            with urlopen(req, timeout=timeout) as r:
                ms = (datetime.now() - inicio).total_seconds() * 1000
                return 200 <= r.status < 400, f"HTTP {r.status} en {ms:.0f} ms", ms
        except HTTPError as e:
            ms = (datetime.now() - inicio).total_seconds() * 1000
            if e.code >= 500 and intento < reintentos:
                time.sleep(1.0)
                continue
            return (200 <= e.code < 400), f"HTTP {e.code} en {ms:.0f} ms", ms
        except (URLError, TimeoutError, OSError) as e:
            ms = (datetime.now() - inicio).total_seconds() * 1000
            if intento < reintentos:
                time.sleep(1.0)
                continue
            return False, f"{type(e).__name__} tras {ms:.0f} ms", ms
    return False, "sin respuesta", 0.0


def _puerto(puerto: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", puerto), timeout=2):
            return True
    except OSError:
        return False


def _git(*args: str) -> tuple[int, str]:
    try:
        # Sin `text=True`: con PYTHONUTF8=1 la decodificacion automatica falla
        # si git (o tasklist) responde en la codificacion OEM de Windows.
        r = subprocess.run(
            ["git", *args], cwd=ROOT, capture_output=True, timeout=20
        )
        salida = (r.stdout or r.stderr).decode("utf-8", errors="replace")
        return r.returncode, salida.strip()
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
            edad = (datetime.now().date() - ultima).days
            # El contexto termina mañana por diseño: cada serie lleva su retraso
            # de publicación, así que el cierre de hoy se etiqueta como mañana.
            cuando = ("mañana" if edad == -1 else "hoy" if edad == 0 else f"{edad} d")
            add("Datos", "contexto_diario.parquet", edad <= 2,
                f"{len(df):,} x {len(df.columns)} · ultimo {ultima} ({cuando})",
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

    # Velas del puente: tienen que ser homogeneas. Si un par termina antes que
    # los demas, `ffill` le congela el precio en la cola y la medicion miente
    # (paso de verdad: 4 de 7 pares, 29 dias congelados, `E-13`).
    velas = sorted((ROOT / "freqtrade_bridge" / "user_data" / "data" / "binance").glob("*-4h.feather"))
    if not velas:
        add("Datos", "Velas 4h del puente", False, "no hay archivos")
    else:
        try:
            import pandas as pd

            finales = {}
            for f in velas:
                ts = pd.to_datetime(pd.read_feather(f, columns=["date"])["date"], utc=True)
                finales[f.name.replace("-4h.feather", "")] = ts.max()
            fin = max(finales.values())
            rezagados = [p for p, t in finales.items() if (fin - t).days > 0]
            add("Datos", "Velas 4h del puente", len(rezagados) == 0,
                f"{len(velas)} pares · ultima {fin.date()}"
                + (f" · rezagados: {', '.join(sorted(rezagados))}" if rezagados else ""))
        except Exception as e:  # noqa: BLE001
            add("Datos", "Velas 4h del puente", False, type(e).__name__)

    # Reportes: si vuelven a generarse con `>` o `Tee-Object` de PowerShell 5.1,
    # salen en UTF-16 y el panel los pinta con un byte nulo entre letras
    # (`D I M E N S I O N A D O`). Se comprueba aqui para que no pase inadvertido.
    reportes = sorted((ROOT / "data").glob("reporte_*.txt"))
    if reportes:
        malos = [r.name for r in reportes if b"\x00" in r.read_bytes()]
        add("Datos", "Reportes en UTF-8", not malos,
            f"{len(reportes)} reportes"
            + (f" · UTF-16: {', '.join(malos[:3])}" if malos else ""))

    # Refresco programado (P2). Una tarea que falla en silencio es peor que no
    # tenerla: se comprueba que existe, que corrio hace menos de 48 h y que su
    # ultimo resultado fue 0.
    try:
        ps = (
            "$n = 'OpenBB - refresco de contexto'; "
            "$t = Get-ScheduledTask -TaskName $n -ErrorAction SilentlyContinue; "
            "if (-not $t) { 'NO'; exit }; "
            "$i = Get-ScheduledTaskInfo -TaskName $n; "
            "$t.State.ToString() + '|' + $i.LastTaskResult + '|' + $i.LastRunTime.ToString('yyyy-MM-dd HH:mm')"
        )
        salida = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True, timeout=40,
        ).stdout.decode("utf-8", errors="replace").strip()
        if not salida or salida == "NO":
            add("Datos", "Refresco programado", False,
                "sin registrar (scripts\\instalar_refresco.ps1)")
        else:
            estado_t, resultado, ultima_ejec = (salida.split("|") + ["", "", ""])[:3]
            try:
                horas = (datetime.now() - datetime.strptime(ultima_ejec, "%Y-%m-%d %H:%M")
                         ).total_seconds() / 3600
            except ValueError:
                horas = 1e9
            en_curso = resultado.strip() == "267009"
            ok_tarea = (resultado.strip() == "0" or en_curso) and horas <= 48
            add("Datos", "Refresco programado", ok_tarea,
                f"{estado_t} · hace {horas:.0f} h · resultado {resultado.strip()}"
                + (" (en curso)" if en_curso else ""))
    except Exception as e:  # noqa: BLE001
        add("Datos", "Refresco programado", False, f"{type(e).__name__}")

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
    # OJO: los bots NO se llaman `freqtrade.exe` en el administrador de tareas:
    # corren como `python.exe` con `freqtrade.exe trade ...` en la linea de
    # comandos. Buscar por nombre de imagen daba 0 procesos con los bots vivos.
    try:
        ps = (
            "Get-CimInstance Win32_Process -Filter \"Name like '%python%'\" | "
            "Where-Object { $_.CommandLine -match 'freqtrade.exe' -and "
            "$_.CommandLine -match '(trade|webserver)' } | "
            "Measure-Object | Select-Object -ExpandProperty Count"
        )
        salida = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True, timeout=40,
        ).stdout.decode("utf-8", errors="replace").strip()
        n = int(salida or 0)
        add("Freqtrade", "Procesos", n > 0, f"{n} procesos")
    except Exception as e:  # noqa: BLE001
        add("Freqtrade", "Procesos", False, f"{type(e).__name__}: {e}")

    puertos = [p for p in (8080, 8081, 8082) if _puerto(p)]
    add("Freqtrade", "Puertos 8080/8081/8082", bool({8080, 8081} & set(puertos)),
        f"{len(puertos)} escuchando ({', '.join(map(str, puertos))})" if puertos else "ninguno")

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
