#!/usr/bin/env python3
"""
RSI Strategy

A strategy that generates buy signals when RSI is oversold and sell signals when RSI is overbought.
"""

import time
import logging
import numpy as np
from typing import Dict, List, Optional, Union

from strategy_interface import TradeStrategyInterface, TradeSignal

logger = logging.getLogger(__name__)


class RSIStrategy(TradeStrategyInterface):
    """RSI (Relative Strength Index) Strategy."""
    
    def __init__(self, period: int = 14, oversold: int = 30, overbought: int = 70):
        """
        Initialize the strategy.
        
        Args:
            period: Period for RSI calculation
            oversold: RSI level considered oversold
            overbought: RSI level considered overbought
        """
        super().__init__(name="RSI Strategy")
        
        self.parameters = {
            "period": period,
            "oversold": oversold,
            "overbought": overbought
        }
        
        # Initialize data storage
        self.prices = []
        self.rsi_values = []
        self.last_action = None  # 'buy' or 'sell'
        
        logger.info(f"Initialized RSI strategy with period={period}, oversold={oversold}, overbought={overbought}")
    
    def execute(self, current_price: float, in_position: bool) -> Optional[TradeSignal]:
        """
        Execute the strategy and generate a trading signal.
        
        Args:
            current_price: Current price of the asset
            in_position: Whether we currently hold a position
            
        Returns:
            A TradeSignal object or None if no action should be taken
        """
        # Need at least one RSI value
        if not self.rsi_values:
            return None
        
        current_rsi = self.rsi_values[-1]
        
        # Buy when RSI is oversold
        if current_rsi <= self.parameters["oversold"] and not in_position and self.last_action != 'buy':
            logger.info(f"Oversold condition detected: RSI = {current_rsi} at price {current_price}")
            self.last_action = 'buy'
            confidence = 1.0 - (current_rsi / self.parameters["oversold"])  # Higher confidence when RSI is lower
            confidence = max(0.1, min(confidence, 1.0))  # Clamp between 0.1 and 1.0
            return TradeSignal(TradeSignal.BUY, current_price, int(time.time()), confidence)
        
        # Sell when RSI is overbought
        elif current_rsi >= self.parameters["overbought"] and in_position and self.last_action != 'sell':
            logger.info(f"Overbought condition detected: RSI = {current_rsi} at price {current_price}")
            self.last_action = 'sell'
            confidence = (current_rsi - self.parameters["overbought"]) / (100 - self.parameters["overbought"])  # Higher confidence when RSI is higher
            confidence = max(0.1, min(confidence, 1.0))  # Clamp between 0.1 and 1.0
            return TradeSignal(TradeSignal.SELL, current_price, int(time.time()), confidence)
        
        return None
    
    def feed_ohlc(self, ohlc_data: List[Dict[str, Union[float, int]]]):
        """
        Feed OHLC data to the strategy and update RSI.
        
        Args:
            ohlc_data: List of OHLC candles
        """
        # Extract close prices
        self.prices = [candle['close'] for candle in ohlc_data]
        
        # Calculate RSI
        self._calculate_rsi()
        
        logger.debug(f"Fed {len(ohlc_data)} OHLC candles to RSI strategy")
    
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
        period = self.parameters["period"]
        if len(self.prices) > period * 3:  # Keep some extra for calculation
            self.prices = self.prices[-period*3:]
        
        # Recalculate RSI
        self._calculate_rsi()
    
    def _calculate_rsi(self):
        """
        Calculate RSI from prices.
        """
        period = self.parameters["period"]
        
        # Need at least period+1 prices to calculate RSI
        if len(self.prices) <= period:
            return
        
        # Calculate price changes
        deltas = np.diff(self.prices)
        
        # Split gains and losses
        gains = np.clip(deltas, 0, None)
        losses = np.clip(-deltas, 0, None)
        
        # Calculate average gains and losses
        avg_gain = []
        avg_loss = []
        
        # First average is simple average
        avg_gain.append(np.sum(gains[:period]) / period)
        avg_loss.append(np.sum(losses[:period]) / period)
        
        # Subsequent averages use smoothing formula
        for i in range(period, len(deltas)):
            avg_gain.append((avg_gain[-1] * (period - 1) + gains[i]) / period)
            avg_loss.append((avg_loss[-1] * (period - 1) + losses[i]) / period)
        
        # Calculate RS and RSI
        rs = np.array(avg_gain) / np.array(avg_loss)
        rsi = 100 - (100 / (1 + rs))
        
        self.rsi_values = rsi.tolist()
    
    def reset(self):
        """
        Reset the strategy state.
        """
        super().reset()
        self.prices = []
        self.rsi_values = []
        self.last_action = None
