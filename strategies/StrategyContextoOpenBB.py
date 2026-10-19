"""Estrategia de ejemplo: tecnico + contexto OpenBB.

Demuestra la cadena completa:
    contexto macro (OpenBB)  ->  filtro de direccion
    cruce de medias (tecnico) ->  gatillo de entrada
    stoploss / ROI            ->  gestion

No pretende ser rentable: es la prueba de que el puente funciona dentro de
Freqtrade. Para usarla: copiala a tu user_data/strategies o apunta
`strategy_path` a esta carpeta.
"""

from __future__ import annotations

import sys
from pathlib import Path

from pandas import DataFrame

from freqtrade.strategy import IStrategy

# Ruta al puente (unica linea a cambiar si mueves la carpeta)
PUENTE = Path(r"C:\Users\DELL\.ipython\OpenBB\scripts")
if str(PUENTE) not in sys.path:
    sys.path.insert(0, str(PUENTE))

from puente_freqtrade import fusionar  # noqa: E402


class StrategyContextoOpenBB(IStrategy):
    """Cruce EMA 20/50 filtrado por regimen macro."""

    INTERFACE_VERSION = 3

    timeframe = "4h"
    can_short = False

    minimal_roi = {"0": 0.15, "240": 0.05}
    stoploss = -0.08
    trailing_stop = False

    process_only_new_candles = True
    startup_candle_count = 200

    # Interruptor para comparar con/sin el filtro de contexto
    use_macro_filter: bool = True

    def informative_pairs(self):
        # El contexto no es un par de exchange: se lee de disco en populate_indicators.
        return []

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["ema20"] = dataframe["close"].ewm(span=20, adjust=False).mean()
        dataframe["ema50"] = dataframe["close"].ewm(span=50, adjust=False).mean()

        dataframe = fusionar(dataframe)

        # Regimen macro: riesgo controlado (VIX bajo) y curva no invertida
        dataframe["macro_ok"] = (
            (dataframe["vix"] < 25) & (dataframe["slope_10y_2y"] > 0)
        ).astype(int)

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        condicion = dataframe["ema20"] > dataframe["ema50"]
        if self.use_macro_filter:
            condicion = condicion & (dataframe["macro_ok"] == 1)
        dataframe.loc[condicion, "enter_long"] = 1
        dataframe.loc[condicion, "enter_tag"] = (
            "ema_cross_macro_ok" if self.use_macro_filter else "ema_cross"
        )
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        condicion = dataframe["ema20"] < dataframe["ema50"]
        dataframe.loc[condicion, "exit_long"] = 1
        dataframe.loc[condicion, "exit_tag"] = "ema_cross_down"
        return dataframe
