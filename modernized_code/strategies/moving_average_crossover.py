#!/usr/bin/env python3
"""
Moving Average Crossover Strategy

A strategy that generates buy signals when a fast moving average crosses above
a slow moving average, and sell signals when it crosses below.
"""

import time
import logging
import numpy as np
from typing import Dict, List, Optional, Union

from strategy_interface import TradeStrategyInterface, TradeSignal

logger = logging.getLogger(__name__)


class MovingAverageCrossover(TradeStrategyInterface):
    """Moving Average Crossover Strategy."""
    
    def __init__(self, fast_period: int = 9, slow_period: int = 20):
        """
        Initialize the strategy.
        
        Args:
            fast_period: Period for the fast moving average
            slow_period: Period for the slow moving average
        """
        super().__init__(name="Moving Average Crossover")
        
        self.parameters = {
            "fast_period": fast_period,
            "slow_period": slow_period
        }
        
        # Initialize data storage
        self.prices = []
        self.fast_ma = []
        self.slow_ma = []
        self.last_crossover = None  # 'bullish' or 'bearish'
        
        logger.info(f"Initialized Moving Average Crossover strategy with fast_period={fast_period}, slow_period={slow_period}")
    
    def execute(self, current_price: float, in_position: bool) -> Optional[TradeSignal]:
        """
        Execute the strategy and generate a trading signal.
        
        Args:
            current_price: Current price of the asset
            in_position: Whether we currently hold a position
            
        Returns:
            A TradeSignal object or None if no action should be taken
        """
        # Need at least two MA values to detect crossover
        if len(self.fast_ma) < 2 or len(self.slow_ma) < 2:
            return None
        
        # Check for crossover
        current_fast = self.fast_ma[-1]
        current_slow = self.slow_ma[-1]
        previous_fast = self.fast_ma[-2]
        previous_slow = self.slow_ma[-2]
        
        # Bullish crossover (fast crosses above slow)
        if previous_fast <= previous_slow and current_fast > current_slow:
            if not in_position:
                logger.info(f"Bullish crossover detected at price {current_price}")
                self.last_crossover = 'bullish'
                return TradeSignal(TradeSignal.BUY, current_price, int(time.time()))
        
        # Bearish crossover (fast crosses below slow)
        elif previous_fast >= previous_slow and current_fast < current_slow:
            if in_position:
                logger.info(f"Bearish crossover detected at price {current_price}")
                self.last_crossover = 'bearish'
                return TradeSignal(TradeSignal.SELL, current_price, int(time.time()))
        
        return None
    
    def feed_ohlc(self, ohlc_data: List[Dict[str, Union[float, int]]]):
        """
        Feed OHLC data to the strategy and update moving averages.
        
        Args:
            ohlc_data: List of OHLC candles
        """
        # Extract close prices
        self.prices = [candle['close'] for candle in ohlc_data]
        
        # Calculate moving averages
        self._calculate_moving_averages()
        
        logger.debug(f"Fed {len(ohlc_data)} OHLC candles to Moving Average Crossover strategy")
    
    def feed_depth(self, depth_data: Dict[str, List[List[float]]]):
        """
        Feed market depth data to the strategy.
        
        Args:
            depth_data: Market depth data with 'bids' and 'asks' lists
        """
        # This strategy doesn't use depth data
        pass
    
    def feed_price_quantity_volume(self, price: float, quantity: float, volume: float):
        """
        Feed real-time price, quantity, and volume data to the strategy.
        
        Args:
            price: Current price
            quantity: Last trade quantity
            volume: Current volume
        """
        # Add price to prices list
        self.prices.append(price)
        
        # Keep only the necessary number of prices
        max_period = max(self.parameters["fast_period"], self.parameters["slow_period"])
        if len(self.prices) > max_period * 2:  # Keep some extra for calculation
            self.prices = self.prices[-max_period*2:]
        
        # Recalculate moving averages
        self._calculate_moving_averages()
    
    def _calculate_moving_averages(self):
        """
        Calculate fast and slow moving averages from prices.
        """
        fast_period = self.parameters["fast_period"]
        slow_period = self.parameters["slow_period"]
        
        # Need enough prices to calculate both MAs
        if len(self.prices) >= slow_period:
            # Calculate fast MA
            self.fast_ma = self._calculate_simple_ma(self.prices, fast_period)
            
            # Calculate slow MA
            self.slow_ma = self._calculate_simple_ma(self.prices, slow_period)
    
    @staticmethod
    def _calculate_simple_ma(data: List[float], period: int) -> List[float]:
        """
        Calculate Simple Moving Average.
        
        Args:
            data: List of price data
            period: MA period
            
        Returns:
            List of moving average values
        """
        result = []
        for i in range(len(data) - period + 1):
            window = data[i:i+period]
            result.append(sum(window) / period)
        return result
    
    def reset(self):
        """
        Reset the strategy state.
        """
        super().reset()
        self.prices = []
        self.fast_ma = []
        self.slow_ma = []
        self.last_crossover = None
