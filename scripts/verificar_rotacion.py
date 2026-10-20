"""Verifica, SIN Freqtrade, que la estrategia de rotacion decide lo mismo que el validador.

Que comprueba
-------------
1. **Misma seleccion**: en cada fecha de rebalanceo, el conjunto de 3 pares que
   elige `strategies/rotacion_nucleo.py` (el codigo que correra dentro del bot)
   coincide con el que elige el validador (`validar_momentum.simular`) con los
   mismos datos. Compara `rank` contra `argsort` y el manejo de huecos.
2. **Shift exacto**: que `close / close.shift(180)` sean 30 dias de calendario y
   no 179 ni 181 velas. Un off-by-one aqui es el error clasico y no se ve en
   el resultado: solo cambia el numero.
3. **Mismo numero**: la simulacion con calendario (lunes 00:00) frente a la del
   validador (fase arbitraria cada 7 dias). Deben ser parecidas, no identicas:
   el desfase de fase cambia que semana se compra.
4. **Supervivencia**: ventanas de 6 meses, cada una desde caja, como en E-14.

Lo que NO comprueba: que Freqtrade ejecute bien. Eso exige el backtest real con
los bots parados. Este script valida la decision, no el motor.

Uso:
    python scripts\\verificar_rotacion.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "strategies"))

from rotacion_nucleo import VELAS_POR_DIA, es_rebalanceo, tabla_senales, velas_de  # noqa: E402
from validar_momentum import (  # noqa: E402
    FEE, calmar, cargar_matriz, compuesto, max_dd, simular,
)

INICIO = "2021-01-01"
FIN = "2026-10-01"
L_DIAS, K, REBAL_DIAS = 30, 3, 7


def universo() -> list[str]:
    velas = ROOT / "freqtrade_bridge" / "user_data" / "data" / "binance"
    return sorted(p.name.replace("-4h.feather", "") for p in velas.glob("*-4h.feather"))


def simular_calendario(m: pd.DataFrame, velas: int, k: int) -> tuple[np.ndarray, dict]:
    """Igual que `simular`, pero rebalanceando en las velas de lunes 00:00.

    Copia deliberada del motor del validador con otro calendario: la unica
    diferencia es CUANDO se decide, para poder medir el efecto de la fase.
    """
    return simular_fase(m, velas, k, fechas_reb=es_rebalanceo(m.index).to_numpy())


def simular_fase(
    m: pd.DataFrame, velas: int, k: int,
    offset: int | None = None, fechas_reb: np.ndarray | None = None,
) -> tuple[np.ndarray, dict]:
    """Motor de la rotacion con la fase del rebalanceo como parametro.

    `offset=0` reproduce al validador: rebalancea cuando `(i - L) % 42 == 0`.
    `offset=n` desplaza esa rejilla n velas. `fechas_reb` permite pasar un
    calendario explicito (lunes 00:00).
    """
    cierres = m.to_numpy(dtype=float)
    n, n_act = cierres.shape
    rets = np.zeros_like(cierres)
    rets[1:] = cierres[1:] / cierres[:-1] - 1.0

    if fechas_reb is None:
        paso = int(round(7 * VELAS_POR_DIA))
        reb = np.array([i >= velas and (i - velas) % paso == (offset or 0) for i in range(n)])
    else:
        reb = np.asarray(fechas_reb, dtype=bool)

    pesos = np.zeros(n_act)
    cartera = np.zeros(n)
    elegidos: dict[pd.Timestamp, set[str]] = {}

    for i in range(n):
        if i > 0:
            cartera[i] = float(pesos @ rets[i])

        if reb[i] and i >= velas:
            mom = cierres[i] / cierres[i - velas] - 1.0
            orden = np.argsort(mom)[::-1]
            orden = orden[np.isfinite(mom[orden])]
            eleg = orden[:k]
            if len(eleg):
                nuevos = np.zeros(n_act)
                nuevos[eleg] = 1.0 / len(eleg)
                cartera[i] -= FEE * float(np.abs(nuevos - pesos).sum())
                pesos = nuevos
                elegidos[m.index[i]] = set(m.columns[eleg])

    return cartera, elegidos


def ventanas_6m(m: pd.DataFrame, velas: int, k: int) -> list[dict]:
    fechas = pd.date_range(pd.Timestamp(INICIO, tz="UTC"), pd.Timestamp(FIN, tz="UTC"), freq="6MS")
    filas = []
    for i in range(len(fechas) - 1):
        t = m[(m.index >= fechas[i]) & (m.index < fechas[i + 1])]
        if len(t) < 100:
            continue
        r, _ = simular_calendario(t, velas, k)
        filas.append({
            "periodo": f"{fechas[i].date()} -> {fechas[i + 1].date()}",
            "ret_%": round(compuesto(r) * 100, 1),
            "dd_%": round(max_dd(r) * 100, 1),
        })
    return filas


def main() -> None:
    pares = universo()
    m = cargar_matriz(pares)
    V = velas_de(L_DIAS)

    print("=" * 100)
    print(f"ROTACION — verificacion offline  |  {len(pares)} pares  |  {INICIO} -> {FIN}")
    print("=" * 100)
    print(f"velas alineadas: {len(m):,}  |  {m.index.min().date()} -> {m.index.max().date()}")
    print(f"parametros: L={L_DIAS}d ({V} velas)  K={K}  rebalanceo semanal\n")

    m_oos = m[(m.index >= pd.Timestamp(INICIO, tz="UTC")) & (m.index < pd.Timestamp(FIN, tz="UTC"))]

    # --- 1. Seleccion: nucleo (rank) vs validador (argsort) -----------------
    tabla = tabla_senales(m_oos, V, K)
    _, elegidos = simular_calendario(m_oos, V, K)

    coinciden, total, ejemplos = 0, 0, []
    for fecha, esperado in elegidos.items():
        fila = tabla.loc[fecha]
        obtenido = set(fila[fila].index)
        total += 1
        if obtenido == esperado:
            coinciden += 1
        elif len(ejemplos) < 3:
            ejemplos.append((fecha, sorted(esperado), sorted(obtenido)))

    print("### 1. SELECCION: el nucleo del bot contra el validador")
    print(f"  fechas de rebalanceo comparadas: {total}")
    print(f"  coincidencias exactas:           {coinciden}/{total} "
          f"({coinciden / max(total, 1) * 100:.1f} %)")
    for f, e, o in ejemplos:
        print(f"    {f}  esperado {e}  obtenido {o}")

    # --- 2. Shift exacto: 180 velas = 30 dias ------------------------------
    pos = {f: i for i, f in enumerate(m_oos.index)}
    desvios = []
    for fecha in elegidos:
        i = pos[fecha]
        if i - V >= 0:
            dias = (m_oos.index[i] - m_oos.index[i - V]).total_seconds() / 86400
            desvios.append(dias)
    print("\n### 2. SHIFT: 180 velas hacia atras")
    if desvios:
        print(f"  distancia en dias: min {min(desvios):.2f}  max {max(desvios):.2f}  "
              f"(esperado 30,00)")
        print(f"  {'✅' if abs(max(desvios) - 30) < 0.01 and abs(min(desvios) - 30) < 0.01 else '❌'} "
              f"el momento se mide siempre a 30 dias exactos")
    else:
        print("  sin rebalanceos suficientes")

    # --- 3. Mismo numero: calendario vs fase fija --------------------------
    params = dict(lookback_dias=L_DIAS, top_k=K, rebal_dias=REBAL_DIAS)
    r_val = simular(m_oos, params)
    r_cal, _ = simular_calendario(m_oos, V, K)

    def bloque(nombre: str, r: np.ndarray) -> dict:
        c, d = compuesto(r), max_dd(r)
        dias = (m_oos.index[-1] - m_oos.index[0]).days
        cagr = ((1 + c) ** (1 / max(dias / 365.25, 1e-9)) - 1) * 100
        return {"variante": nombre, "ret_%": round(c * 100, 1), "cagr_%": round(cagr, 1),
                "dd_%": round(d * 100, 1), "calmar": round(calmar(r), 2)}

    comparacion = pd.DataFrame([bloque("validador (fase E-14)", r_val),
                                bloque("estrategia (lunes 00:00)", r_cal)])
    print("\n### 3. MISMO MOTOR, DISTINTA FASE")
    print(comparacion.to_string(index=False))
    print("\n  No tienen que coincidir: el validador rebalancea cada 7 dias desde una")
    print("  fase arbitraria; la estrategia, siempre en lunes. Si difieren mucho,")
    print("  el resultado depende de la fase y eso hay que decirlo, no esconderlo.")

    # --- 3b. La fase como parametro oculto --------------------------------
    # El validador elige "cada 42 velas desde el inicio de la ventana". Esa
    # rejilla tiene 42 fases posibles (una por vela de la semana) y E-14 midio
    # UNA. Se miden las 42 para saber si el numero era una regla o un billete
    # de loteria.
    paso = int(round(REBAL_DIAS * VELAS_POR_DIA))
    fases = []
    for off in range(paso):
        r, _ = simular_fase(m_oos, V, K, offset=off)
        fases.append({"fase": off, "ret_%": compuesto(r) * 100, "dd_%": max_dd(r) * 100,
                      "calmar": calmar(r)})
    t_fases = pd.DataFrame(fases)
    q = t_fases["ret_%"].quantile([0.1, 0.25, 0.5, 0.75, 0.9])

    print("\n### 3b. LA FASE DEL REBALANCEO (42 fases posibles, una por vela)")
    print(f"  minimo     {t_fases['ret_%'].min():+12.1f}%   DD {t_fases.loc[t_fases['ret_%'].idxmin(), 'dd_%']:6.1f}%")
    print(f"  p10        {q[0.1]:+12.1f}%")
    print(f"  p25        {q[0.25]:+12.1f}%")
    print(f"  MEDIANA    {q[0.5]:+12.1f}%   <-- el numero honesto")
    print(f"  p75        {q[0.75]:+12.1f}%")
    print(f"  p90        {q[0.9]:+12.1f}%")
    print(f"  maximo     {t_fases['ret_%'].max():+12.1f}%   DD {t_fases.loc[t_fases['ret_%'].idxmax(), 'dd_%']:6.1f}%")
    print(f"  fases positivas: {int((t_fases['ret_%'] > 0).sum())}/{len(t_fases)}")
    print(f"  E-14 usa la fase 0: {t_fases.loc[0, 'ret_%']:+.1f}%  |  "
          f"la estrategia (lunes): {compuesto(r_cal) * 100:+.1f}%  |  "
          f"mediana: {q[0.5]:+.1f}%")

    # --- 4. Supervivencia ---------------------------------------------------
    filas = ventanas_6m(m_oos, V, K)
    vivas = sum(1 for f in filas if f["ret_%"] > 0)
    print("\n### 4. VENTANAS DE 6 MESES (cada una desde caja)")
    for f in filas:
        marca = "✅" if f["ret_%"] > 0 else "❌"
        print(f"  {marca} {f['periodo']}   {f['ret_%']:+8.1f}%   DD {f['dd_%']:6.1f}%")
    print(f"\n  ventanas positivas: {vivas}/{len(filas)}   "
          f"peor: {min((f['ret_%'] for f in filas), default=0):+.1f}%")

    # --- Veredicto ----------------------------------------------------------
    ok = coinciden == total and total > 0
    print("\n" + "=" * 100)
    print(f"VEREDICTO: {'✅ el nucleo decide lo mismo que el validador' if ok else '❌ la seleccion NO coincide'}")
    print("  Pendiente (no medido aqui): ejecucion real dentro de Freqtrade.")
    print("=" * 100)


if __name__ == "__main__":
    main()
