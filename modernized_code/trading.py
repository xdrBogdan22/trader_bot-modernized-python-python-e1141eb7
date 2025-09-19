#!/usr/bin/env python3
"""
Trading Module

Handles trading logic, including order execution and position management.
"""

import time
import logging
from typing import Dict, List, Optional, Union
from datetime import datetime
from threading import Thread, Event, Lock

from data_provider import BinanceDataProvider
from strategy_interface import TradeStrategyInterface, TradeSignal
from account import Account, SimulatedAccount, BinanceAccount

logger = logging.getLogger(__name__)


class TradingBot:
    """Trading bot that executes strategies on market data."""
    
    def __init__(self, symbol: str, use_real_account: bool = False, api_key: str = "", api_secret: str = "", testnet: bool = True):
        """
        Initialize the trading bot.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTCUSDT')
            use_real_account: Whether to use a real Binance account
            api_key: Binance API key (required for real account)
            api_secret: Binance API secret (required for real account)
            testnet: Whether to use Binance testnet (for real account)
        """
        self.symbol = symbol
        self.use_real_account = use_real_account
        
        # Initialize data provider
        self.data_provider = BinanceDataProvider(
            use_testnet=testnet,
            api_key=api_key if use_real_account else "",
            api_secret=api_secret if use_real_account else ""
        )
        
        # Initialize account
        if use_real_account:
            if not api_key or not api_secret:
                raise ValueError("API key and secret are required for real account trading")
            self.account = BinanceAccount(api_key, api_secret, testnet)
        else:
            self.account = SimulatedAccount(initial_balance=1000.0)
        
        # Trading state
        self.strategy = None
        self.running = False
        self.stop_event = Event()
        self.trading_thread = None
        self.lock = Lock()
        
        # Performance tracking
        self.trades = []
        self.start_balance = self.account.get_balance()
        
        logger.info(f"Initialized trading bot for {symbol} (real account: {use_real_account})")
    
    def set_strategy(self, strategy: TradeStrategyInterface):
        """
        Set the trading strategy.
        
        Args:
            strategy: Strategy instance
        """
        self.strategy = strategy
        logger.info(f"Set strategy to {strategy.name}")
    
    def start(self):
        """
        Start the trading bot.
        """
        if not self.strategy:
            raise ValueError("Strategy must be set before starting")
        
        with self.lock:
            if self.running:
                logger.warning("Trading bot is already running")
                return
            
            self.running = True
            self.stop_event.clear()
        
        # Connect to WebSocket for real-time data
        self.data_provider.connect_websocket(self.symbol, {
            "kline": self._on_kline,
            "trade": self._on_trade,
            "depth": self._on_depth
        })
        
        # Start trading thread
        self.trading_thread = Thread(target=self._trading_loop)
        self.trading_thread.daemon = True
        self.trading_thread.start()
        
        logger.info(f"Trading bot started with {self.strategy.name} strategy")
    
    def stop(self):
        """
        Stop the trading bot.
        """
        with self.lock:
            if not self.running:
                logger.warning("Trading bot is not running")
                return
            
            self.running = False
            self.stop_event.set()
        
        # Disconnect from WebSocket
        self.data_provider.disconnect_websocket()
        
        # Wait for trading thread to finish
        if self.trading_thread and self.trading_thread.is_alive():
            self.trading_thread.join(timeout=5.0)
        
        logger.info("Trading bot stopped")
        
        # Log performance summary
        self._log_performance_summary()
    
    def _trading_loop(self):
        """
        Main trading loop.
        """
        while not self.stop_event.is_set():
            try:
                # Get current price
                current_price = self.data_provider.get_current_price(self.symbol)
                
                # Check if we have a position
                in_position = self.account.has_position(self.symbol)
                
                # Execute strategy
                signal = self.strategy.execute(current_price, in_position)
                
                # Process signal
                if signal:
                    self._process_signal(signal)
                
                # Sleep to avoid excessive CPU usage
                time.sleep(1.0)
                
            except Exception as e:
                logger.error(f"Error in trading loop: {str(e)}")
                time.sleep(5.0)  # Sleep longer on error
    
    def _process_signal(self, signal: TradeSignal):
        """
        Process a trading signal.
        
        Args:
            signal: Trading signal
        """
        try:
            if signal.type == TradeSignal.BUY:
                # Execute buy order
                order_result = self.account.buy(self.symbol, signal.price)
                
                if order_result["success"]:
                    logger.info(f"Buy order executed at {signal.price}")
                    
                    # Record trade
                    self.trades.append({
                        "type": "BUY",
                        "price": signal.price,
                        "timestamp": signal.timestamp,
                        "quantity": order_result.get("quantity", 0.0)
                    })
                else:
                    logger.error(f"Buy order failed: {order_result.get('error', 'Unknown error')}")
            
            elif signal.type == TradeSignal.SELL:
                # Execute sell order
                order_result = self.account.sell(self.symbol, signal.price)
                
                if order_result["success"]:
                    logger.info(f"Sell order executed at {signal.price}")
                    
                    # Record trade
                    self.trades.append({
                        "type": "SELL",
                        "price": signal.price,
                        "timestamp": signal.timestamp,
                        "quantity": order_result.get("quantity", 0.0),
                        "profit": order_result.get("profit", 0.0)
                    })
                else:
                    logger.error(f"Sell order failed: {order_result.get('error', 'Unknown error')}")
        
        except Exception as e:
            logger.error(f"Error processing signal: {str(e)}")
    
    def _on_kline(self, kline: Dict):
        """
        Handle kline (candlestick) update.
        
        Args:
            kline: Kline data
        """
        if self.strategy and self.running:
            # Only feed closed candles to strategy
            if kline.get("is_closed", False):
                self.strategy.feed_ohlc([kline])
    
    def _on_trade(self, trade: Dict):
        """
        Handle trade update.
        
        Args:
            trade: Trade data
        """
        if self.strategy and self.running:
            self.strategy.feed_price_quantity_volume(
                trade["price"],
                trade["quantity"],
                trade["quantity"] * trade["price"]
            )
    
    def _on_depth(self, depth: Dict):
        """
        Handle market depth update.
        
        Args:
            depth: Market depth data
        """
        if self.strategy and self.running:
            self.strategy.feed_depth(depth)
    
    def _log_performance_summary(self):
        """
        Log performance summary.
        """
        current_balance = self.account.get_balance()
        profit = current_balance - self.start_balance
        profit_percent = (profit / self.start_balance) * 100
        
        buy_trades = [t for t in self.trades if t["type"] == "BUY"]
        sell_trades = [t for t in self.trades if t["type"] == "SELL"]
        
        logger.info("=== Performance Summary ===")
        logger.info(f"Starting balance: {self.start_balance:.2f}")
        logger.info(f"Current balance: {current_balance:.2f}")
        logger.info(f"Profit: {profit:.2f} ({profit_percent:.2f}%)")
        logger.info(f"Number of trades: {len(self.trades)}")
        logger.info(f"Buy trades: {len(buy_trades)}")
        logger.info(f"Sell trades: {len(sell_trades)}")
        
        # Calculate win rate if we have sell trades
        if sell_trades:
            winning_trades = [t for t in sell_trades if t.get("profit", 0.0) > 0.0]
            win_rate = (len(winning_trades) / len(sell_trades)) * 100
            logger.info(f"Win rate: {win_rate:.2f}%")
        
        logger.info("===========================")
    
    def get_performance_metrics(self) -> Dict:
        """
        Get performance metrics.
        
        Returns:
            Dictionary of performance metrics
        """
        current_balance = self.account.get_balance()
        profit = current_balance - self.start_balance
        profit_percent = (profit / self.start_balance) * 100
        
        buy_trades = [t for t in self.trades if t["type"] == "BUY"]
        sell_trades = [t for t in self.trades if t["type"] == "SELL"]
        
        metrics = {
            "start_balance": self.start_balance,
            "current_balance": current_balance,
            "profit": profit,
            "profit_percent": profit_percent,
            "num_trades": len(self.trades),
            "num_buy_trades": len(buy_trades),
            "num_sell_trades": len(sell_trades),
            "win_rate": 0.0
        }
        
        # Calculate win rate if we have sell trades
        if sell_trades:
            winning_trades = [t for t in sell_trades if t.get("profit", 0.0) > 0.0]
            metrics["win_rate"] = (len(winning_trades) / len(sell_trades)) * 100
        
        return metrics
    
    def manual_buy(self) -> Dict:
        """
        Execute a manual buy order.
        
        Returns:
            Order result
        """
        current_price = self.data_provider.get_current_price(self.symbol)
        result = self.account.buy(self.symbol, current_price)
        
        if result["success"]:
            logger.info(f"Manual buy order executed at {current_price}")
            
            # Record trade
            self.trades.append({
                "type": "BUY",
                "price": current_price,
                "timestamp": int(time.time()),
                "quantity": result.get("quantity", 0.0),
                "manual": True
            })
        else:
            logger.error(f"Manual buy order failed: {result.get('error', 'Unknown error')}")
        
        return result
    
    def manual_sell(self) -> Dict:
        """
        Execute a manual sell order.
        
        Returns:
            Order result
        """
        current_price = self.data_provider.get_current_price(self.symbol)
        result = self.account.sell(self.symbol, current_price)
        
        if result["success"]:
            logger.info(f"Manual sell order executed at {current_price}")
            
            # Record trade
            self.trades.append({
                "type": "SELL",
                "price": current_price,
                "timestamp": int(time.time()),
                "quantity": result.get("quantity", 0.0),
                "profit": result.get("profit", 0.0),
                "manual": True
            })
        else:
            logger.error(f"Manual sell order failed: {result.get('error', 'Unknown error')}")
        
        return result
