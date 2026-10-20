"""Normaliza los reportes crudos a UTF-8.

Por que existe
--------------
`Tee-Object` y `>` de PowerShell 5.1 escriben **UTF-16LE** por defecto. El panel
leia con `encoding="utf-8"`, asi que cada caracter ASCII venia seguido de un byte
nulo: en pantalla se veia `D I M E N S I O N A D O` y los `\ufffd` del BOM.
No era un fallo de los datos, era un fallo de codificacion.

Este script:
  - detecta la codificacion real de cada `data/reporte_*.txt` (BOM UTF-16/UTF-8,
    UTF-8 valido o cp1252 como ultimo recurso),
  - reescribe el mismo texto en UTF-8 sin BOM y con saltos LF,
  - informa que hizo con cada archivo.

Es idempotente: volver a ejecutarlo no cambia nada.

Uso:
    python scripts\\normalizar_reportes.py
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def leer(ruta: Path) -> tuple[str, str]:
    b = ruta.read_bytes()
    if b[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return b.decode("utf-16"), "utf-16"
    if b[:3] == b"\xef\xbb\xbf":
        return b.decode("utf-8-sig"), "utf-8 con BOM"
    try:
        return b.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        return b.decode("cp1252"), "cp1252"


def reparar_mojibake(texto: str) -> tuple[str, bool]:
    """Deshace UTF-8 leido como cp850 y vuelto a guardar.

    La cadena real fue: Python escribe UTF-8 -> la consola de PowerShell lo
    interpreta como cp850 -> `Tee-Object` lo guarda en UTF-16. El texto queda
    con `ÔÇö` donde habia un guion largo. Se revierte codificando a cp850 y
    decodificando UTF-8. Si el resultado no es valido, se deja como estaba.
    """
    señales = ("ÔÇ", "â€", "Ã", "Â", "\u251c", "\u2502")
    if not any(s in texto for s in señales):
        return texto, False
    try:
        return texto.encode("cp850").decode("utf-8"), True
    except (UnicodeEncodeError, UnicodeDecodeError):
        return texto, False


def main() -> None:
    rutas = sorted(DATA.glob("reporte_*.txt"))
    if not rutas:
        print("no hay reportes en data/")
        return

    print(f"{'archivo':<42} {'origen':<14} {'lineas':>7}  resultado")
    print("-" * 90)
    cambiados = 0
    for ruta in rutas:
        texto, origen = leer(ruta)
        limpio = texto.replace("\r\n", "\n").replace("\r", "\n").lstrip("\ufeff")
        limpio, reparado = reparar_mojibake(limpio)
        n = len(limpio.splitlines())
        ya = origen == "utf-8" and b"\x00" not in ruta.read_bytes() and not reparado
        if ya:
            print(f"{ruta.name:<42} {origen:<14} {n:>7}  ya estaba")
            continue
        with open(ruta, "w", encoding="utf-8", newline="\n") as f:
            f.write(limpio)
        cambiados += 1
        que = "convertido + mojibake" if reparado else "convertido"
        print(f"{ruta.name:<42} {origen:<14} {n:>7}  {que}")

    print("-" * 90)
    print(f"{len(rutas)} reportes · {cambiados} convertidos · {len(rutas) - cambiados} intactos")


if __name__ == "__main__":
    main()
