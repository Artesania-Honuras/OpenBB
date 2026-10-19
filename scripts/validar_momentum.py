"""Valida momentum transversal (rotacion entre pares) contra el azar, con y sin control de riesgo.

Que mide y por que asi
----------------------
En cada rebalanceo se mantienen los K pares con mejor retorno de los ultimos L
dias, a peso igual. La pregunta NO es "gana dinero?" sino "gana por encima de
elegir K pares al azar?".

Esa segunda pregunta es la unica honesta: elegir al azar tiene la misma
exposicion y la misma diversificacion por construccion, asi que cualquier
diferencia se puede atribuir al criterio de seleccion y a nada mas.

El contraste es una prueba de permutacion: con los parametros que eligio el
entrenamiento en cada ventana, se repite la simulacion eligiendo los pares al
azar (200 semillas por defecto) y se mira en que percentil de esa nube cae la
estrategia. Si cae en el medio, no hay habilidad: hay suerte.

Control de riesgo (tres piezas independientes)
----------------------------------------------
1. Filtro de regimen: si la cesta a peso igual pierde su media de `ma_dias`,
   se pasa a caja. La venta es inmediata; la vuelta solo en rebalanceo.
2. Volatilidad objetivo: el peso se escala por `vol_objetivo / vol_realizada`,
   con tope 1 (sin apalancamiento). El resto queda en caja.
3. Criterio de seleccion en entrenamiento: `retorno` (bruto) o `calmar`
   (retorno / drawdown). El bruto premia el maximo riesgo.

El control de riesgo se prueba como INTERRUPTOR, no como parametro a optimizar:
asi el espacio de busqueda no crece y la comparacion entre variantes es limpia.

Protocolo (identico al resto del proyecto)
------------------------------------------
- Walk-forward: 18 meses de entrenamiento, 6 de prueba, avanzando de 6 en 6.
  Solo cuentan las ventanas de prueba.
- Comision 0.1% por lado, aplicada sobre el giro real de la cartera.
- Sin apalancamiento. Sin filtros macro externos: la cesta es su propio regimen.

Uso:
    python scripts\\validar_momentum.py                 # linea base (E-10)
    python scripts\\validar_momentum.py --riesgo        # tabla de variantes (E-11)
"""

from __future__ import annotations

import argparse
import itertools
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
VELAS = ROOT / "freqtrade_bridge" / "user_data" / "data" / "binance"

FEE = 0.001
BARRAS_POR_DIA = 6  # velas de 4h
DIAS_POR_ANIO = 365

# Rejilla de busqueda: se elige en entrenamiento, se juzga en prueba.
GRID_MOMENTUM = {
    "lookback_dias": [30, 60, 90],
    "top_k": [1, 2, 3],
    "rebal_dias": [7, 28],
}

# Variantes del experimento de riesgo. Interruptores fijos, no parametros.
VARIANTES_RIESGO = {
    "A) retorno bruto, sin control": dict(objetivo="retorno", ma=None, vol=None),
    "B) Calmar, sin control": dict(objetivo="calmar", ma=None, vol=None),
    "C) Calmar + regimen 200d": dict(objetivo="calmar", ma=200, vol=None),
    "D) Calmar + regimen 200d + vol 60%": dict(objetivo="calmar", ma=200, vol=0.60),
    "E) Calmar + vol 60%": dict(objetivo="calmar", ma=None, vol=0.60),
    "F) Calmar + regimen 100d + vol 40%": dict(objetivo="calmar", ma=100, vol=0.40),
}


# --------------------------------------------------------------------------
# Datos y senales
# --------------------------------------------------------------------------
def cargar_matriz(pares: list[str]) -> pd.DataFrame:
    """Matriz de cierres alineada por fecha (una columna por par)."""
    series = {}
    for p in pares:
        ruta = VELAS / f"{p}-4h.feather"
        if not ruta.exists():
            raise FileNotFoundError(f"No hay velas en {ruta}")
        df = pd.read_feather(ruta)[["date", "close"]]
        df["date"] = pd.to_datetime(df["date"], utc=True)
        series[p] = df.set_index("date")["close"].astype(float)
    m = pd.DataFrame(series).sort_index()
    return m.ffill().dropna()


def index_cesta(m: pd.DataFrame) -> pd.Series:
    """Indice de la cesta a peso igual (media de retornos acumulada)."""
    rets = m.pct_change().mean(axis=1).fillna(0.0)
    return (1 + rets).cumprod()


def preparar_senales(
    m: pd.DataFrame, ma_dias: int | None = None,
    vol_dias: int = 30, vol_objetivo: float | None = None,
) -> pd.DataFrame:
    """Senales de riesgo alineadas con `m`.

    Se calculan sobre la serie COMPLETA y luego se recortan por ventana. Es
    correcto: en cada fecha la senal usa solo datos pasados, pero necesita
    historial caliente (una media de 200 dias no cabe en una ventana de 6 meses).
    """
    s = pd.DataFrame(index=m.index)
    cesta = index_cesta(m)

    if ma_dias:
        s["en_mercado"] = (cesta > cesta.rolling(int(ma_dias * BARRAS_POR_DIA)).mean()).fillna(False)
    else:
        s["en_mercado"] = True

    if vol_objetivo:
        rets = m.pct_change().mean(axis=1)
        vol = rets.rolling(int(vol_dias * BARRAS_POR_DIA)).std() * np.sqrt(BARRAS_POR_DIA * DIAS_POR_ANIO)
        s["escala"] = (vol_objetivo / vol).clip(upper=1.0).fillna(0.0)
    else:
        s["escala"] = 1.0

    return s


# --------------------------------------------------------------------------
# Motor
# --------------------------------------------------------------------------
def simular(
    m: pd.DataFrame, params: dict, semilla: int | None = None,
    senales: pd.DataFrame | None = None,
) -> np.ndarray:
    """Retorno de la cartera en cada vela.

    `semilla=None` -> seleccion por momentum. `semilla=int` -> seleccion AL AZAR
    (mismo K, mismo calendario, mismo coste, mismas senales de riesgo). Esa es
    la referencia: el control de riesgo se aplica igual a los dos.
    """
    closes = m.to_numpy(dtype=float)
    rets = np.zeros_like(closes)
    rets[1:] = closes[1:] / closes[:-1] - 1.0

    n, n_act = closes.shape
    L = int(params["lookback_dias"] * BARRAS_POR_DIA)
    rebal = int(params["rebal_dias"] * BARRAS_POR_DIA)
    K = min(int(params["top_k"]), n_act)

    if senales is None:
        en_mercado = np.ones(n, dtype=bool)
        escala = np.ones(n)
    else:
        s = senales.reindex(m.index)
        en_mercado = s["en_mercado"].to_numpy(dtype=bool)
        escala = s["escala"].to_numpy(dtype=float)

    rng = np.random.default_rng(semilla)
    pesos = np.zeros(n_act)
    cartera = np.zeros(n)

    for i in range(n):
        if i > 0:
            cartera[i] = float(pesos @ rets[i])  # pesos vigentes desde la vela anterior

        # 1. Perder el regimen: salir a caja en el acto, con su coste
        if not en_mercado[i] and pesos.sum() > 0:
            cartera[i] -= FEE * float(np.abs(pesos).sum())
            pesos = np.zeros(n_act)

        # 2. Rebalanceo al cierre de la vela i (solo datos conocidos) y solo si hay regimen
        if i >= L and (i - L) % rebal == 0 and en_mercado[i]:
            if semilla is None:
                momento = closes[i] / closes[i - L] - 1.0
                elegidos = np.argsort(momento)[::-1][:K]
            else:
                elegidos = rng.choice(n_act, size=K, replace=False)
            nuevos = np.zeros(n_act)
            nuevos[elegidos] = escala[i] / K  # el resto, en caja
            cartera[i] -= FEE * float(np.abs(nuevos - pesos).sum())
            pesos = nuevos

    return cartera


def compuesto(retornos: np.ndarray) -> float:
    return float(np.prod(1 + retornos) - 1) if len(retornos) else 0.0


def max_dd(retornos: np.ndarray) -> float:
    if not len(retornos):
        return 0.0
    eq = np.cumprod(1 + retornos)
    pico = np.maximum.accumulate(eq)
    return float(np.min(eq / pico - 1))


def calmar(retornos: np.ndarray) -> float:
    """Retorno partido por el dolor: cuanto se gana por cada punto de drawdown."""
    return compuesto(retornos) / max(abs(max_dd(retornos)), 0.05)


def objetivo_entrenamiento(retornos: np.ndarray, tipo: str) -> float:
    return compuesto(retornos) if tipo == "retorno" else calmar(retornos)


# --------------------------------------------------------------------------
# Walk-forward
# --------------------------------------------------------------------------
def walk_forward(
    m: pd.DataFrame, inicio: str, fin: str,
    senales: pd.DataFrame | None = None, objetivo: str = "retorno",
) -> tuple[pd.DataFrame, np.ndarray, list[dict]]:
    combos = [dict(zip(GRID_MOMENTUM.keys(), v)) for v in itertools.product(*GRID_MOMENTUM.values())]
    fechas = pd.date_range(pd.Timestamp(inicio, tz="UTC"), pd.Timestamp(fin, tz="UTC"), freq="6MS")

    filas, oos, ventanas = [], [], []
    for i in range(len(fechas) - 1):
        test_ini, test_fin = fechas[i], fechas[i + 1]
        train_ini = test_ini - pd.DateOffset(months=18)

        train = m[(m.index >= train_ini) & (m.index < test_ini)]
        test = m[(m.index >= test_ini) & (m.index < test_fin)]
        if len(train) < 500 or len(test) < 100:
            continue

        mejor, mejor_val = None, -np.inf
        for params in combos:
            val = objetivo_entrenamiento(simular(train, params, senales=senales), objetivo)
            if val > mejor_val:
                mejor, mejor_val = params, val

        ret_test = simular(test, mejor, senales=senales)
        oos.append(ret_test)
        ventanas.append({"params": mejor, "test": test, "real": compuesto(ret_test)})

        filas.append({
            "periodo": f"{test_ini.date()} -> {test_fin.date()}",
            "L_dias": mejor["lookback_dias"],
            "K": mejor["top_k"],
            "rebal_dias": mejor["rebal_dias"],
            "train_calmar": round(calmar(simular(train, mejor, senales=senales)), 2),
            "test_%": round(compuesto(ret_test) * 100, 1),
            "test_dd_%": round(max_dd(ret_test) * 100, 1),
        })

    return pd.DataFrame(filas), (np.concatenate(oos) if oos else np.array([])), ventanas


def nube_al_azar(ventanas: list[dict], sims: int, senales: pd.DataFrame | None = None) -> np.ndarray:
    """Distribucion del resultado si se eligieran los K pares al azar.

    Usa los mismos parametros (L, K, rebalanceo) que eligio el entrenamiento en
    cada ventana, y las mismas senales de riesgo: lo unico que cambia es el
    criterio de seleccion.
    """
    finales = np.empty(sims)
    for s in range(sims):
        trozos = [simular(v["test"], v["params"], semilla=s, senales=senales) for v in ventanas]
        finales[s] = compuesto(np.concatenate(trozos))
    return finales


def evaluar_config(
    m: pd.DataFrame, inicio: str, fin: str, sims: int,
    objetivo: str = "retorno", ma: int | None = None, vol: float | None = None,
) -> dict:
    senales = preparar_senales(m, ma_dias=ma, vol_objetivo=vol)
    wf, oos, ventanas = walk_forward(m, inicio, fin, senales=senales, objetivo=objetivo)
    if not len(oos):
        return {}

    comp, dd = compuesto(oos), max_dd(oos)
    nube = nube_al_azar(ventanas, sims, senales=senales)
    pct = float((nube < comp).mean() * 100)
    return {
        "oos_%": comp * 100,
        "dd_%": dd * 100,
        "calmar": calmar(oos),
        "ventanas": f"{int((wf['test_%'] > 0).sum())}/{len(wf)}",
        "percentil_azar": pct,
        "azar_p50_%": float(np.percentile(nube, 50)) * 100,
        "P(azar>=esta)": float((nube >= comp).mean() * 100),
        "_wf": wf,
    }


# --------------------------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--inicio", default="2021-01-01")
    ap.add_argument("--fin", default="2026-10-01")
    ap.add_argument("--sims", type=int, default=200, help="simulaciones al azar")
    ap.add_argument("--riesgo", action="store_true", help="tabla de variantes de control de riesgo (E-11)")
    ap.add_argument("--ma", type=int, default=None, help="media de regimen en dias (None = sin filtro)")
    ap.add_argument("--vol", type=float, default=None, help="volatilidad objetivo anualizada (None = sin control)")
    ap.add_argument("--objetivo", choices=["retorno", "calmar"], default="calmar",
                    help="criterio de seleccion en entrenamiento (E-11: calmar es mejor)")
    args = ap.parse_args()

    pares = sorted(p.name.replace("-4h.feather", "") for p in VELAS.glob("*-4h.feather"))
    m = cargar_matriz(pares)
    print("=" * 104)
    print(f"MOMENTUM TRANSVERSAL  |  {len(pares)} pares  |  {args.inicio} -> {args.fin}")
    print("=" * 104)
    print(f"pares: {', '.join(pares)}")
    print(f"velas alineadas: {len(m):,}  |  {m.index.min().date()} -> {m.index.max().date()}")

    # Referencia: comprar los 7 y no tocar (siempre 100% invertido)
    bh_m = m[m.index >= pd.Timestamp(args.inicio, tz="UTC")]
    r_bh = np.zeros(len(bh_m))
    r_bh[1:] = (bh_m.to_numpy()[1:] / bh_m.to_numpy()[:-1] - 1).mean(axis=1)
    print(f"cesta a peso igual: {compuesto(r_bh)*100:+.1f}%  |  DD {max_dd(r_bh)*100:.1f}%  "
          f"|  Calmar {calmar(r_bh):.2f}")

    if args.riesgo:
        print("\n### VARIANTES DE CONTROL DE RIESGO (18 combinaciones por variante, azar = 200 semillas)\n")
        filas = []
        for nombre, cfg in VARIANTES_RIESGO.items():
            r = evaluar_config(m, args.inicio, args.fin, args.sims, **cfg)
            if not r:
                continue
            r.pop("_wf")
            filas.append({"variante": nombre, **r})
        t = pd.DataFrame(filas)
        print(t.round(2).to_string(index=False))
        print("\n  columnas: oos_% = retorno fuera de muestra · dd_% = drawdown maximo")
        print("            calmar = retorno / |drawdown| · percentil_azar = posicion frente a elegir K pares al azar")
        print(f"            referencia de la cesta: Calmar {calmar(r_bh):.2f}, DD {max_dd(r_bh)*100:.1f}%")
        print("\n### VEREDICTO")
        ok = t[(t["dd_%"] > -20) & (t["percentil_azar"] >= 95) & (t["calmar"] > calmar(r_bh))]
        if len(ok):
            print(f"  {len(ok)} variante(s) cumplen las tres condiciones (DD > -20%, percentil >= 95, Calmar > cesta):")
            print(ok[["variante", "oos_%", "dd_%", "calmar", "percentil_azar"]].round(2).to_string(index=False))
        else:
            print("  Ninguna variante cumple las tres condiciones a la vez:")
            print("  DD mejor que -20%, percentil frente al azar >= 95 y Calmar mejor que la cesta.")
        return

    r = evaluar_config(m, args.inicio, args.fin, args.sims,
                       objetivo=args.objetivo, ma=args.ma, vol=args.vol)
    if not r:
        print("sin ventanas suficientes")
        return
    wf = r.pop("_wf")
    print("\n### WALK-FORWARD (solo cuentan las columnas de prueba)\n")
    print(wf.to_string(index=False))
    print("\n### RESULTADO FUERA DE MUESTRA\n")
    print(f"  retorno compuesto:            {r['oos_%']:+.1f}%")
    print(f"  drawdown maximo:              {r['dd_%']:.1f}%")
    print(f"  calmar:                       {r['calmar']:.2f}  (cesta: {calmar(r_bh):.2f})")
    print(f"  ventanas positivas:           {r['ventanas']}")
    print("\n### REFERENCIA (elegir K pares al azar, mismo calendario y senales)\n")
    print(f"  mediana del azar:             {r['azar_p50_%']:+.1f}%")
    print(f"  la estrategia cae en el percentil {r['percentil_azar']:.0f}")
    print(f"  probabilidad de que el azar la iguale o supere: {r['P(azar>=esta)']:.1f}%")


if __name__ == "__main__":
    main()
