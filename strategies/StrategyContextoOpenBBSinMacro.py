"""Misma estrategia pero SIN el filtro de contexto de OpenBB.

Sirve de control experimental: la unica diferencia con StrategyContextoOpenBB
es `use_macro_filter = False`, asi que comparar ambas aisla el efecto del
contexto macro sobre el mismo gatillo tecnico.

    freqtrade backtesting --config freqtrade_bridge/backtest.json \
        --strategy StrategyContextoOpenBBSinMacro --timerange 20250101- --export none
"""

from __future__ import annotations

from StrategyContextoOpenBB import StrategyContextoOpenBB


class StrategyContextoOpenBBSinMacro(StrategyContextoOpenBB):
    """Cruce EMA 20/50 puro, sin filtro macro."""

    use_macro_filter = False
