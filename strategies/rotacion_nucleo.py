"""Nucleo de la rotacion transversal, SIN dependencias de Freqtrade.

Por que esta separado
---------------------
La decision ("quien esta en el top 3") tiene que poder ejecutarse en dos sitios:

  1. dentro de Freqtrade, para operar;
  2. fuera de Freqtrade, en `scripts/verificar_rotacion.py`, para comprobar
     contra el validador que decide lo mismo.

Si la logica viviera dentro de la clase `IStrategy` habria que importar
Freqtrade para probarla, y el entorno de OpenBB no lo tiene. Duplicar la logica
en el verificador seria peor: se estaria comprobando una copia, no el codigo
que opera. Por eso: un solo nucleo, dos consumidores.

Reglas (E-14, lo unico que se puede desplegar)
----------------------------------------------
- Momento: retorno de los ultimos 30 dias (180 velas de 4h).
- Seleccion: los 3 pares con mayor momento de los 24.
- Rebalanceo: semanal, a peso igual, sin apalancamiento, sin stop.
- Coste: 0,1 % por lado sobre el giro real de la cartera.
"""

from __future__ import annotations

import pandas as pd

VELAS_POR_DIA = 6  # velas de 4h


def velas_de(dias: int, velas_por_dia: int = VELAS_POR_DIA) -> int:
    """Convierte dias a velas. 30 dias -> 180 velas."""
    return int(round(dias * velas_por_dia))


def momento(cierres: pd.DataFrame, velas: int) -> pd.DataFrame:
    """Retorno de las ultimas `velas` velas, par a par.

    Es el mismo calculo que el validador (`close[i] / close[i-L] - 1`): usa
    solo el cierre de la vela actual y el de `velas` atras. No mira el futuro.
    """
    return cierres / cierres.shift(int(velas)) - 1.0


def es_rebalanceo(fechas) -> pd.Series:
    """Velas cuyo Cierre cae en lunes 00:00 UTC.

    Se elige ese instante por una razon concreta: Freqtrade ejecuta la orden al
    abrir la vela siguiente. Si la senal se marca en la vela de lunes 00:00,
    la entrada ocurre al abrir la de las 04:00. En el validador la posicion
    empieza en el cierre semanal; la diferencia es una vela de 4 h.

    No se usa "domingo 20:00" porque en vivo esa vela todavia se esta formando
    cuando el bot la evalua: el cierre seria un precio incompleto.
    """
    idx = pd.DatetimeIndex(pd.to_datetime(fechas, utc=True))
    return pd.Series((idx.dayofweek == 0) & (idx.hour == 0), index=idx)


def en_top_k(cierres: pd.DataFrame, velas: int, k: int) -> pd.DataFrame:
    """True si el par esta entre los `k` de mayor momento en esa vela.

    `method="first"` desempata por orden de columna. Con precios reales los
    empates exactos son practicamente imposibles; se fija la regla para que
    el resultado sea reproducible y no dependa del orden del diccionario.
    """
    m = momento(cierres, velas)
    orden = m.rank(axis=1, ascending=False, method="first")
    return (orden <= int(k)) & m.notna()


def tabla_senales(cierres: pd.DataFrame, velas: int, k: int) -> pd.DataFrame:
    """Membresia del top-k, mantenida entre rebalanceos.

    Solo se rankea en las velas de rebalanceo (unas 300 en 6 anos) y el
    resultado se arrastra (`ffill`) hasta el siguiente. Es lo que hace que el
    coste sea despreciable y, sobre todo, es fiel a la regla: la cartera NO se
    toca entre domingos, aunque el ranking cambie el martes.

    Devuelve un DataFrame booleano con el mismo indice que `cierres`.
    """
    reb = es_rebalanceo(cierres.index)
    sub = momento(cierres, velas)[reb]
    orden = sub.rank(axis=1, ascending=False, method="first")
    dentro = (orden <= int(k)) & sub.notna()
    return dentro.reindex(cierres.index, method="ffill").fillna(False).astype(bool)
