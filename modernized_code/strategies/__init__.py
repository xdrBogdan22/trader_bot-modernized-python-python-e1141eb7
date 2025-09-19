#!/usr/bin/env python3
"""
Trading strategies package.
"""

from .moving_average_crossover import MovingAverageCrossover
from .rsi_strategy import RSIStrategy
from .macd_strategy import MACDStrategy

# Dictionary of available strategies
AVAILABLE_STRATEGIES = {
    "Moving Average Crossover": MovingAverageCrossover,
    "RSI Strategy": RSIStrategy,
    "MACD Strategy": MACDStrategy
}


def get_strategy_names():
    """Get list of available strategy names."""
    return list(AVAILABLE_STRATEGIES.keys())


def create_strategy(strategy_name, **kwargs):
    """Create a strategy instance by name."""
    if strategy_name in AVAILABLE_STRATEGIES:
        return AVAILABLE_STRATEGIES[strategy_name](**kwargs)
    else:
        raise ValueError(f"Unknown strategy: {strategy_name}")
