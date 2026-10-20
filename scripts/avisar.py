"""Aviso externo (Telegram) cuando el contexto falla o pierde historia.

Por que existe
--------------
El 2026-10-20 el refresco devolvio 0 y escribio `OK`, pero perdio el CPI desde
1926. El unico aviso vivia en el panel: si nadie lo mira, no hay aviso. Este
script se ejecuta **despues de cada refresco** (la tarea diaria) y manda un
mensaje solo cuando hay un problema real.

Que considera problema
----------------------
- refresco: `fallo`, `viejo` (> 48 h), `sin_datos`, `ilegible`
- historia rota: el CPI empieza despues de 1990 o hay NaN en 2026

Configuracion (nunca se versiona)
---------------------------------
`data/notificador.json`:

    {"telegram_token": "123456:ABC...", "telegram_chat": "123456789"}

o las variables `OPENBB_TELEGRAM_TOKEN` y `OPENBB_TELEGRAM_CHAT`.
Sin configuracion **no envia y sale con 0**: la falta de token no debe marcar
la tarea como fallida. El envio real se comprueba con `--probar`.

Uso:
    python scripts\\avisar.py              # evalua y avisa si toca
    python scripts\\avisar.py --seco       # imprime el mensaje, no envia
    python scripts\\avisar.py --probar     # mensaje de prueba (requiere token)
    python scripts\\avisar.py --autoprueba
"""

from __future__ import annotations

import json
import os
import ssl
import sys
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from estado_contexto import historia_rota, resumen  # noqa: E402

CONFIG = ROOT / "data" / "notificador.json"
ULTIMO = ROOT / "data" / "aviso_ultimo.json"
LOG = ROOT / "data" / "avisos.log"
HORAS_REPETICION = 12

TITULOS = {
    "fallo": "el ultimo refresco fallo",
    "viejo": "el contexto lleva mas de 48 h sin refrescarse",
    "sin_datos": "no hay contexto exportado",
    "ilegible": "el contexto no se puede leer",
    "historia": "el contexto perdio historia",
}


def _cfg() -> dict:
    cfg: dict = {}
    if CONFIG.exists():
        try:
            cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
        except Exception:
            cfg = {}
    cfg["telegram_token"] = cfg.get("telegram_token") or os.environ.get("OPENBB_TELEGRAM_TOKEN", "")
    cfg["telegram_chat"] = cfg.get("telegram_chat") or os.environ.get("OPENBB_TELEGRAM_CHAT", "")
    return cfg


def _log(nivel: str, mensaje: str) -> None:
    linea = f"{datetime.now():%Y-%m-%d %H:%M:%S}  {nivel:<6} {mensaje}"
    if LOG.exists() and LOG.stat().st_size > 512 * 1024:
        previas = LOG.read_text(encoding="utf-8", errors="replace").splitlines()[-500:]
        LOG.write_text("\n".join(previas) + "\n", encoding="utf-8", newline="\n")
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG, "a", encoding="utf-8", newline="\n") as f:
        f.write(linea + "\n")
    print(linea)


def configurado() -> bool:
    """True si hay token y chat para entregar el aviso."""
    c = _cfg()
    return bool(c["telegram_token"] and c["telegram_chat"])


def motivo(r: dict) -> str | None:
    """Devuelve el problema a avisar, o None si todo esta bien."""
    if r.get("estado") in ("fallo", "sin_datos", "ilegible"):
        return r["estado"]
    if r.get("estado") == "viejo":
        return "viejo"
    if historia_rota(r):
        return "historia"
    return None


def _n(v, suf: str = "") -> str:
    if v is None:
        return "?"
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return f"{v:,}{suf}"
    return f"{v}{suf}"


def componer(r: dict, m: str) -> str:
    horas = "?" if r.get("horas") is None else f"{max(0.0, r['horas']):.1f} h"
    partes = [
        "OpenBB · contexto",
        f"Problema: {TITULOS.get(m, m)}",
        f"Estado: {r.get('estado')} · hace {horas}",
        f"Datos: {_n(r.get('filas'))} × {_n(r.get('columnas'))} · hasta {_n(r.get('ultima_fecha'))}",
        f"Historia: CPI desde {_n(r.get('cpi_desde'))} · NaN 2026: {_n(r.get('nan_2026'))}",
    ]
    if r.get("linea"):
        partes.append(f"Ultimo evento: {str(r['linea'])[:300]}")
    partes.append("Panel: http://127.0.0.1:8501")
    return "\n".join(partes)


def clave(r: dict, m: str, hoy: date) -> str:
    """Identidad del aviso. Incluye el dia: un problema persistente avisa 1/dia."""
    return "|".join([
        f"{hoy:%Y-%m-%d}", m, str(r.get("estado")), str(r.get("ultima_fecha")),
        str(r.get("cpi_desde")), str(r.get("nan_2026")),
    ])


def toca_enviar(k: str, ultimo: dict, ahora: datetime, horas: int = HORAS_REPETICION) -> bool:
    if not ultimo or ultimo.get("clave") != k:
        return True
    try:
        enviado = datetime.fromisoformat(ultimo["enviado"])
    except Exception:
        return True
    return (ahora - enviado) >= timedelta(hours=horas)


def enviar(token: str, chat: str, texto: str, timeout: int = 20) -> None:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    datos = urllib.parse.urlencode({
        "chat_id": chat,
        "text": texto,
        "disable_web_page_preview": "true",
    }).encode()
    req = urllib.request.Request(url, data=datos)
    try:
        import certifi
        ctx = ssl.create_default_context(cafile=certifi.where())
    except Exception:
        ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
        cuerpo = json.loads(resp.read().decode("utf-8", "replace"))
    if not cuerpo.get("ok"):
        raise RuntimeError(cuerpo.get("description", "respuesta no ok"))


def main(seco: bool = False, probar: bool = False) -> int:
    cfg = _cfg()
    configurado = bool(cfg["telegram_token"] and cfg["telegram_chat"])

    if probar:
        if not configurado:
            print("Sin configuracion: crea data/notificador.json con telegram_token y telegram_chat.")
            return 0
        try:
            enviar(cfg["telegram_token"], cfg["telegram_chat"],
                   "OpenBB · prueba de aviso. Si lees esto, el canal funciona.")
        except Exception as e:  # noqa: BLE001
            _log("FALLO", f"prueba de envio: {type(e).__name__}: {e}")
            return 1
        _log("OK", "prueba de envio")
        return 0

    r = resumen()
    m = motivo(r)
    ahora = datetime.now()

    if m is None:
        _log("SIN", "sin problemas")
        return 0

    texto = componer(r, m)
    if seco:
        print(texto)
        _log("SECO", m)
        return 0

    ultimo: dict = {}
    if ULTIMO.exists():
        try:
            ultimo = json.loads(ULTIMO.read_text(encoding="utf-8"))
        except Exception:
            ultimo = {}
    k = clave(r, m, ahora.date())
    if not toca_enviar(k, ultimo, ahora):
        _log("SIN", f"repetido ({m}), no se reenvia")
        return 0

    if not configurado:
        print("Problema detectado, pero falta configurar el aviso:")
        print(texto)
        _log("PEND", f"{m}: falta telegram_token/telegram_chat")
        return 0

    try:
        enviar(cfg["telegram_token"], cfg["telegram_chat"], texto)
    except Exception as e:  # noqa: BLE001
        _log("FALLO", f"envio ({m}): {type(e).__name__}: {e}")
        return 1

    ULTIMO.write_text(
        json.dumps({"clave": k, "enviado": ahora.isoformat(timespec="seconds")}, ensure_ascii=False),
        encoding="utf-8",
    )
    _log("OK", f"enviado ({m})")
    return 0


def autoprueba() -> int:
    sana = {
        "estado": "ok", "horas": 1.2, "filas": 36_637, "columnas": 14,
        "ultima_fecha": date(2026, 10, 20), "cpi_desde": date(1956, 2, 15),
        "nan_2026": 0, "linea": "2026-10-20 12:01:27  OK  36,637 filas", "nivel": "OK",
    }
    fallo = dict(sana, estado="fallo", linea="2026-10-21 09:05:07  FALLO  validacion: cache economy_cpi")
    roto = dict(sana, cpi_desde=date(2026, 6, 15), nan_2026=165)
    viejo = dict(sana, estado="viejo", horas=72.0)

    casos: list[tuple[str, bool]] = [
        ("contexto sano no avisa", motivo(sana) is None),
        ("fallo de refresco avisa", motivo(fallo) == "fallo"),
        ("historia rota avisa", motivo(roto) == "historia"),
        ("mas de 48 h avisa", motivo(viejo) == "viejo"),
        ("el mensaje lleva datos y motivo",
         "fallo" in componer(fallo, "fallo") and "36,637" in componer(fallo, "fallo")),
        ("aviso nuevo se envia", toca_enviar("k1", {}, datetime(2026, 10, 20, 10, 0))),
        ("mismo aviso hace 1 h no se repite",
         not toca_enviar("k1", {"clave": "k1", "enviado": "2026-10-20T09:00:00"}, datetime(2026, 10, 20, 10, 0))),
        ("mismo aviso tras 13 h se repite",
         toca_enviar("k1", {"clave": "k1", "enviado": "2026-10-20T09:00:00"}, datetime(2026, 10, 20, 22, 0))),
    ]

    correctos = 0
    for nombre, bien in casos:
        correctos += int(bien)
        print(f"  {'OK  ' if bien else 'FALLA'}  {nombre}")

    print(f"\n{correctos}/{len(casos)} pruebas del aviso")
    return 0 if correctos == len(casos) else 1


if __name__ == "__main__":
    if "--autoprueba" in sys.argv:
        sys.exit(autoprueba())
    sys.exit(main(seco="--seco" in sys.argv, probar="--probar" in sys.argv))
