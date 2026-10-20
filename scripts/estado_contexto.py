"""Estado del refresco del contexto: una función pura, para el panel y para probar.

Por qué existe
--------------
La pestaña *Contexto Freqtrade* avisaba con la **fecha del archivo** (`mtime`) y
mandaba ejecutar un comando que ya no es el correcto. El refresco ahora es una
tarea programada (`C-38`) y lo que importa no es cuándo se escribió el archivo,
sino **cómo terminó la última ejecución**: un refresco puede escribir un archivo
fresco y fallar antes de guardarlo, o llevar tres días sin correr y parecer
normal porque nadie mira el log.

`resumen()` devuelve un diccionario y no sabe nada de Streamlit. Así se puede
probar sin abrir el panel (`--autoprueba`).

Uso:
    from estado_contexto import resumen
    r = resumen()
    print(r["estado"], r["horas"], r["filas"], r["ultima_fecha"])
"""

from __future__ import annotations

import os
import sys
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTEXT_FILE = ROOT / "data" / "context" / "contexto_diario.parquet"
# `OPENBB_REFRESCO_LOG` existe solo para las pruebas: permite simular fallos y
# retrasos sin tocar el registro real (ver `--autoprueba` y la prueba del panel).
LOG = Path(os.environ.get("OPENBB_REFRESCO_LOG") or (ROOT / "data" / "refresco_contexto.log"))
UMBRAL_HORAS = 48

# Niveles que escribe refrescar_contexto.py en cada línea.
_NIVELES = {"OK", "FALLO"}


def _lineas(log: Path) -> list[str]:
    if not log.exists():
        return []
    return log.read_text(encoding="utf-8", errors="replace").splitlines()


def _ultima_ejecucion(lineas: list[str]) -> tuple[datetime | None, str | None, str | None]:
    """Busca hacia atrás la última línea con fecha y nivel.

    Los fallos de validación escriben el motivo en líneas de continuación, así
    que la última línea del archivo puede no ser el resultado. Se recorre al
    revés hasta encontrar una que empiece por `YYYY-MM-DD HH:MM:SS  NIVEL`.
    """
    for linea in reversed(lineas):
        if len(linea) < 21:
            continue
        try:
            ts = datetime.strptime(linea[:19], "%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
        resto = linea[19:].strip().split()
        if resto and resto[0] in _NIVELES:
            return ts, resto[0], linea
    return None, None, None


def resumen(
    ruta: Path = CONTEXT_FILE,
    log: Path = LOG,
    ahora: datetime | None = None,
    umbral_horas: float = UMBRAL_HORAS,
) -> dict:
    """Estado del contexto y de su último refresco.

    Claves: `estado` (ok | fallo | viejo | sin_datos | sin_registro), `horas`,
    `nivel`, `linea`, `filas`, `columnas`, `ultima_fecha`, `escrito`,
    `lineas_log`. Si el parquet no se puede leer, `estado` = `ilegible`.
    """
    ahora = ahora or datetime.now()
    r: dict = {
        "estado": "ok", "horas": None, "nivel": None, "linea": None,
        "filas": None, "columnas": None, "ultima_fecha": None,
        "escrito": None, "lineas_log": [], "cpi_desde": None, "nan_2026": None,
    }

    if not ruta.exists():
        r["estado"] = "sin_datos"
        r["lineas_log"] = _lineas(log)[-6:]
        return r

    import pandas as pd

    try:
        df = pd.read_parquet(ruta)
        indice = pd.to_datetime(df.index)
        r["filas"] = len(df)
        r["columnas"] = len(df.columns)
        r["ultima_fecha"] = indice.max().date()
        # La historia también se vigila: un refresco puede ser "OK" y haber
        # perdido décadas de CPI (pasó el 2026-10-20, ver C-41).
        if "cpi_yoy" in df.columns:
            cpi = df["cpi_yoy"].dropna()
            r["cpi_desde"] = cpi.index.min().date() if len(cpi) else None
            r["nan_2026"] = int(df.loc[indice >= "2026-01-01"].isna().sum().sum())
    except Exception:  # noqa: BLE001
        r["estado"] = "ilegible"
        r["lineas_log"] = _lineas(log)[-6:]
        return r

    r["escrito"] = datetime.fromtimestamp(ruta.stat().st_mtime)

    lineas = _lineas(log)
    r["lineas_log"] = lineas[-6:]
    ts, nivel, linea = _ultima_ejecucion(lineas)
    r["nivel"] = nivel
    r["linea"] = linea

    referencia = ts or r["escrito"]
    r["horas"] = (ahora - referencia).total_seconds() / 3600

    if nivel == "FALLO":
        r["estado"] = "fallo"
    elif r["horas"] > umbral_horas:
        r["estado"] = "viejo"
    elif nivel is None:
        # Archivo fresco pero sin registro: se puede usar, se declara el hueco.
        r["estado"] = "sin_registro"
    return r


def main() -> int:
    r = resumen()
    print(f"estado        : {r['estado']}")
    if r["horas"] is not None:
        print(f"horas         : {r['horas']:.1f}")
    if r["filas"] is not None:
        print(f"filas         : {r['filas']:,} x {r['columnas']}")
        print(f"ultima fecha  : {r['ultima_fecha']}")
    if r["cpi_desde"]:
        print(f"CPI desde     : {r['cpi_desde']} · NaN 2026: {r['nan_2026']}")
    if r["escrito"]:
        print(f"archivo       : {r['escrito']:%Y-%m-%d %H:%M:%S}")
    if r["linea"]:
        print(f"ultimo evento : {r['linea']}")
    return 0 if r["estado"] in ("ok", "viejo", "sin_registro") else 1


def historia_rota(r: dict, desde: int = 1990) -> bool:
    """True si el CPI empieza tarde o hay NaN en 2026.

    Sin columna `cpi_yoy` no se puede juzgar y no se inventa un veredicto.
    """
    if r.get("cpi_desde") is None:
        return False
    return r["cpi_desde"] > date(desde, 1, 1) or bool(r.get("nan_2026"))


def autoprueba() -> int:
    """Comprueba los cinco estados sin tocar los datos reales."""
    import pandas as pd

    ahora = datetime(2026, 10, 19, 20, 0, 0)
    casos: list[tuple[str, str, str]] = []

    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        parquet = base / "ctx.parquet"
        pd.DataFrame({"vix": [19.0, 19.5, 20.0]},
                     index=pd.date_range("2026-10-17", periods=3, freq="D")).to_parquet(parquet)
        log = base / "log.txt"

        def con_log(*lineas: str) -> None:
            log.write_text("\n".join(lineas) + "\n", encoding="utf-8")

        def sello(horas: float, nivel: str = "OK") -> str:
            t = ahora - timedelta(hours=horas)
            return f"{t:%Y-%m-%d %H:%M:%S}  {nivel:<6} 36,637 filas · 14 columnas"

        con_log(sello(1))
        casos.append(("refresco reciente", resumen(parquet, log, ahora)["estado"], "ok"))

        con_log(sello(1, "FALLO"), "      cache vix: ultimo 2026-10-01 (18 dias, maximo 8)")
        casos.append(("ultimo fallo (con continuacion)", resumen(parquet, log, ahora)["estado"], "fallo"))

        con_log(sello(72))
        casos.append(("72 h sin refrescar", resumen(parquet, log, ahora)["estado"], "viejo"))

        if log.exists():
            log.unlink()
        casos.append(("sin log, archivo fresco", resumen(parquet, log, ahora)["estado"], "sin_registro"))

        casos.append(("sin parquet", resumen(base / "no.parquet", log, ahora)["estado"], "sin_datos"))

        casos.append(("historia sana", str(historia_rota({"cpi_desde": date(1956, 2, 15), "nan_2026": 0})), "False"))
        casos.append(("historia perdida", str(historia_rota({"cpi_desde": date(2026, 6, 15), "nan_2026": 165})), "True"))
        casos.append(("sin columna CPI", str(historia_rota({"cpi_desde": None})), "False"))

    correctos = 0
    for nombre, obtenido, esperado in casos:
        bien = obtenido == esperado
        correctos += int(bien)
        print(f"  {'OK  ' if bien else 'FALLA'}  {nombre:<34} -> {obtenido} (esperado {esperado})")

    print(f"\n{correctos}/{len(casos)} pruebas del resumen")
    return 0 if correctos == len(casos) else 1


if __name__ == "__main__":
    sys.exit(autoprueba() if "--autoprueba" in sys.argv else main())
