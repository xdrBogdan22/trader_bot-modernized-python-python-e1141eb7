#!/usr/bin/env python3
"""
MACD Strategy

A strategy that generates buy signals when MACD line crosses above the signal line,
and sell signals when it crosses below.
"""

import time
import logging
import numpy as np
from typing import Dict, List, Optional, Union

from strategy_interface import TradeStrategyInterface, TradeSignal

logger = logging.getLogger(__name__)


class MACDStrategy(TradeStrategyInterface):
    """MACD (Moving Average Convergence Divergence) Strategy."""
    
    def __init__(self, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9):
        """
        Initialize the strategy.
        
        Args:
            fast_period: Period for the fast EMA
            slow_period: Period for the slow EMA
            signal_period: Period for the signal line
        """
        super().__init__(name="MACD Strategy")
        
        self.parameters = {
            "fast_period": fast_period,
            "slow_period": slow_period,
            "signal_period": signal_period
        }
        
        # Initialize data storage
        self.prices = []
        self.macd_line = []
        self.signal_line = []
        self.histogram = []
        self.last_crossover = None  # 'bullish' or 'bearish'
        
        logger.info(f"Initialized MACD strategy with fast_period={fast_period}, slow_period={slow_period}, signal_period={signal_period}")
    
    def execute(self, current_price: float, in_position: bool) -> Optional[TradeSignal]:
        """
        Execute the strategy and generate a trading signal.
        
        Args:
            current_price: Current price of the asset
            in_position: Whether we currently hold a position
            
        Returns:
            A TradeSignal object or None if no action should be taken
        """
        # Need at least two values to detect crossover
        if len(self.macd_line) < 2 or len(self.signal_line) < 2:
            return None
        
        # Check for crossover
        current_macd = self.macd_line[-1]
        current_signal = self.signal_line[-1]
        previous_macd = self.macd_line[-2]
        previous_signal = self.signal_line[-2]
        
        # Bullish crossover (MACD crosses above signal)
        if previous_macd <= previous_signal and current_macd > current_signal:
            if not in_position:
                logger.info(f"Bullish MACD crossover detected at price {current_price}")
                self.last_crossover = 'bullish'
                # Calculate confidence based on histogram strength
                confidence = min(abs(self.histogram[-1]) / 0.5, 1.0)  # Normalize to 0-1 range
                return TradeSignal(TradeSignal.BUY, current_price, int(time.time()), confidence)
        
        # Bearish crossover (MACD crosses below signal)
        elif previous_macd >= previous_signal and current_macd < current_signal:
            if in_position:
                logger.info(f"Bearish MACD crossover detected at price {current_price}")
                self.last_crossover = 'bearish'
                # Calculate confidence based on histogram strength
                confidence = min(abs(self.histogram[-1]) / 0.5, 1.0)  # Normalize to 0-1 range
                return TradeSignal(TradeSignal.SELL, current_price, int(time.time()), confidence)
        
        return None
    
    def feed_ohlc(self, ohlc_data: List[Dict[str, Union[float, int]]]):
        """
        Feed OHLC data to the strategy and update MACD.
        
        Args:
            ohlc_data: List of OHLC candles
        """
        # Extract close prices
        self.prices = [candle['close'] for candle in ohlc_data]
        
        # Calculate MACD
        self._calculate_macd()
        
        logger.debug(f"Fed {len(ohlc_data)} OHLC candles to MACD strategy")
    
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
        max_period = max(self.parameters["fast_period"], self.parameters["slow_period"]) * 3
        if len(self.prices) > max_period:  # Keep some extra for calculation
            self.prices = self.prices[-max_period:]
        
        # Recalculate MACD
        self._calculate_macd()
    
    def _calculate_macd(self):
        """
        Calculate MACD from prices.
        """
        fast_period = self.parameters["fast_period"]
        slow_period = self.parameters["slow_period"]
        signal_period = self.parameters["signal_period"]
        
        # Need enough prices to calculate both EMAs
        if len(self.prices) <= slow_period:
            return
        
        # Calculate fast EMA
        fast_ema = self._calculate_ema(self.prices, fast_period)
        
        # Calculate slow EMA
        slow_ema = self._calculate_ema(self.prices, slow_period)
        
        # Calculate MACD line (fast EMA - slow EMA)
        # Align the arrays since they have different lengths
        macd_line = [fast - slow for fast, slow in zip(fast_ema[-len(slow_ema):], slow_ema)]
        
        # Calculate signal line (EMA of MACD line)
        if len(macd_line) >= signal_period:
            signal_line = self._calculate_ema(macd_line, signal_period)
            
            # Calculate histogram (MACD line - signal line)
            # Align the arrays
            histogram = [macd - signal for macd, signal in zip(macd_line[-len(signal_line):], signal_line)]
            
            self.macd_line = macd_line[-len(signal_line):]
            self.signal_line = signal_line
            self.histogram = histogram
    
    @staticmethod
    def _calculate_ema(data: List[float], period: int) -> List[float]:
        """
        Calculate Exponential Moving Average.
        
        Args:
            data: List of price data
            period: EMA period
            
        Returns:
            List of EMA values
        """
        if len(data) < period:
            return []
        
        # Calculate multiplier
        multiplier = 2 / (period + 1)
        
        # Calculate first EMA as SMA
        ema = [sum(data[:period]) / period]
        
        # Calculate subsequent EMAs
        for i in range(period, len(data)):
            ema.append((data[i] - ema[-1]) * multiplier + ema[-1])
        
        return ema
    
    def reset(self):
        """
        Reset the strategy state.
        """
        super().reset()
        self.prices = []
        self.macd_line = []
        self.signal_line = []
        self.histogram = []
        self.last_crossover = None
