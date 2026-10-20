"""Rotacion semanal de los 3 pares con mas momento a 30 dias (E-14).

Que es
-------
Cada lunes a las 00:00 UTC se eligen los 3 pares, de los 24, con mayor retorno
en los ultimos 30 dias. Peso igual entre los 3. Se mantienen hasta el lunes
siguiente, sin stop y sin objetivo de beneficio. El que sale del top 3 se vende.

Numeros medidos (E-14, 2021-01-01 -> 2026-10-01, 24 pares, comision 0,1 %/lado):
    +820,4 %   CAGR +47,2 %   DD -82,5 %   Calmar 9,95   7/11 ventanas de 6 meses
    P(azar >= esta) 0,5 %

Lo que esto NO es: no es una estrategia de bajo riesgo. El drawdown medido es
del -82,5 %. Por eso el tamano importa mas que la senal: `D-25` fija un sleeve
del 10 %, que en el bootstrap (`E-15`) deja el DD p95 del patrimonio total en
-22,0 % (fallando por 2 puntos el criterio de < -20 %, declarado).

El sleeve NO se implementa aqui
-------------------------------
No hay stake fijo ni porcentaje magico en la estrategia: `stake_amount =
"unlimited"` con `max_open_trades = 3` reparte la cartera del bot en tercios
iguales. El 10 % se impone FUERA, financiando la cuenta del bot con el 10 % del
capital. Un stake fijo dentro del codigo se desincroniza con el saldo real; la
cartera, no.

Diferencias declaradas frente al validador
------------------------------------------
1. Una vela de 4 h: la senal se marca a las 00:00 y Freqtrade entra a las 04:00.
2. Freqtrade no re-igual los pesos de las posiciones abiertas; el validador si
   lo hace cada semana (y paga comision por ello). Aqui el peso deriva con el
   precio. Menos coste, riesgo algo distinto.
3. En vivo, la senal usa la ultima vela CERRADA: si el bot evalua una vela en
   formacion, ese cierre es un precio a medias y no se usa.

Como probarla
-------------
    python scripts\\verificar_rotacion.py        # offline, contra E-14

Para instalar (con los bots parados, nunca con posiciones abiertas):
    copiar rotacion_momentum.py y rotacion_nucleo.py a user_data/strategies/
    freqtrade backtesting --config <config> --strategy RotacionMomentum24 ^
        --timerange 20210101-20261001

Requiere `max_open_trades = 3` y `stake_amount = "unlimited"` en la config.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
from pandas import DataFrame

from freqtrade.strategy import IStrategy

# El nucleo vive al lado. En Freqtrade, el directorio de estrategias ya esta en
# sys.path; el respaldo sirve para lanzarla desde el repo de OpenBB.
try:
    from rotacion_nucleo import es_rebalanceo, tabla_senales, velas_de
except ImportError:  # pragma: no cover - solo si se ejecuta desde otra ruta
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from rotacion_nucleo import es_rebalanceo, tabla_senales, velas_de


class RotacionMomentum24(IStrategy):
    """Los 3 pares con mas momento a 30 dias, rebalanceo semanal."""

    INTERFACE_VERSION = 3

    timeframe = "4h"
    can_short = False

    lookback_dias = 30
    top_k = 3

    # Sin gestion de salida: la unica salida es "dejo de estar en el top 3".
    # `stoploss` casi -1 y `minimal_roi` inalcanzable reproducen el backtest,
    # que no tiene stop. Poner un stop aqui cambiaria la estrategia medida.
    stoploss = -0.99
    minimal_roi = {"0": 100.0}
    trailing_stop = False
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = True

    process_only_new_candles = True
    startup_candle_count = 200

    order_types = {
        "entry": "market",
        "exit": "market",
        "stoploss": "market",
        "stake": "market",
    }
    order_time_in_force = {"entry": "gtc", "exit": "gtc"}

    # Cache de la tabla de senales: se reconstruye una vez por rebalanceo, no
    # una vez por vela ni una vez por par.
    _tabla: DataFrame | None = None
    _tabla_pares: tuple[str, ...] = ()
    _ultimo_reb = None

    def informative_pairs(self):
        # No hacen falta: el ranking se calcula con `dp.get_pair_dataframe`
        # sobre la whitelist, dentro de populate_indicators.
        return []

    # ------------------------------------------------------------------
    def _matriz_cierres(self, dp) -> DataFrame:
        """Cierres de todos los pares de la whitelist, alineados por fecha."""
        cierres = {}
        for par in dp.current_whitelist():
            velas = dp.get_pair_dataframe(par, self.timeframe)
            if velas is None or velas.empty:
                continue
            fechas = pd.to_datetime(velas["date"], utc=True)
            cierres[par] = velas.set_index(fechas)["close"].astype(float)
        if not cierres:
            return DataFrame()
        m = DataFrame(cierres).sort_index()

        # En vivo la ultima vela esta a medias: su "cierre" es el precio actual.
        # Usarla seria decidir con un precio que todavia se mueve.
        if getattr(dp, "runmode", None) is not None and dp.runmode.value in ("live", "dry_run"):
            ahora = pd.Timestamp.now(tz="UTC")
            m = m[m.index + pd.Timedelta(hours=4) <= ahora]

        return m

    def _tabla_del_momento(self, dp, t: pd.Timestamp) -> DataFrame:
        """Tabla de membresia, reconstruida solo cuando toca rebalanceo."""
        pares = tuple(dp.current_whitelist())
        if self._tabla is None or pares != self._tabla_pares:
            self._tabla, self._tabla_pares, self._ultimo_reb = None, pares, None

        toca = bool(es_rebalanceo(pd.Series([t])).iloc[0])
        if self._tabla is None or (toca and (self._ultimo_reb is None or t > self._ultimo_reb)):
            m = self._matriz_cierres(dp)
            if m.empty:
                return DataFrame()
            self._tabla = tabla_senales(m, velas_de(self.lookback_dias), self.top_k)
            self._ultimo_reb = t

        return self._tabla

    # ------------------------------------------------------------------
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        fechas = pd.to_datetime(dataframe["date"], utc=True)
        t = fechas.iloc[-1]

        tabla = self._tabla_del_momento(self.dp, t)

        if tabla.empty or metadata["pair"] not in tabla.columns:
            dataframe["en_top_k"] = False
        else:
            # `ffill` cubre las velas posteriores al ultimo rebalanceo: la
            # membresia vale hasta que se vuelva a decidir.
            serie = tabla[metadata["pair"]].reindex(pd.DatetimeIndex(fechas), method="ffill")
            dataframe["en_top_k"] = serie.fillna(False).to_numpy()

        dataframe["rebalanceo"] = es_rebalanceo(fechas).to_numpy()
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        condicion = (
            dataframe["rebalanceo"]
            & dataframe["en_top_k"]
            & (dataframe["volume"] > 0)
        )
        dataframe.loc[condicion, "enter_long"] = 1
        dataframe.loc[condicion, "enter_tag"] = "top3_semanal"
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        condicion = dataframe["rebalanceo"] & ~dataframe["en_top_k"]
        dataframe.loc[condicion, "exit_long"] = 1
        dataframe.loc[condicion, "exit_tag"] = "fuera_top3"
        return dataframe
