#!/usr/bin/env python3
"""
Data Provider Module

Handles fetching data from Binance API, both real-time and historical.
"""

import time
import logging
import json
from typing import Dict, List, Optional, Union, Tuple
from datetime import datetime, timedelta
import requests
import websocket
from threading import Thread, Lock

logger = logging.getLogger(__name__)


class BinanceDataProvider:
    """Provider for Binance market data."""
    
    # API endpoints
    BASE_URL = "https://api.binance.com"
    BASE_URL_TESTNET = "https://testnet.binance.vision"
    WS_URL = "wss://stream.binance.com:9443/ws"
    WS_URL_TESTNET = "wss://testnet.binance.vision/ws"
    
    # Kline intervals
    INTERVALS = {
        "1m": 60,
        "3m": 180,
        "5m": 300,
        "15m": 900,
        "30m": 1800,
        "1h": 3600,
        "2h": 7200,
        "4h": 14400,
        "6h": 21600,
        "8h": 28800,
        "12h": 43200,
        "1d": 86400,
        "3d": 259200,
        "1w": 604800,
        "1M": 2592000
    }
    
    def __init__(self, use_testnet: bool = False, api_key: str = "", api_secret: str = ""):
        """
        Initialize the data provider.
        
        Args:
            use_testnet: Whether to use Binance testnet
            api_key: Binance API key
            api_secret: Binance API secret
        """
        self.use_testnet = use_testnet
        self.api_key = api_key
        self.api_secret = api_secret
        
        # Set base URLs based on testnet flag
        self.base_url = self.BASE_URL_TESTNET if use_testnet else self.BASE_URL
        self.ws_url = self.WS_URL_TESTNET if use_testnet else self.WS_URL
        
        # WebSocket connection
        self.ws = None
        self.ws_thread = None
        self.ws_connected = False
        self.ws_lock = Lock()
        
        # Callbacks
        self.on_kline_callback = None
        self.on_trade_callback = None
        self.on_depth_callback = None
        
        logger.info(f"Initialized Binance data provider (testnet: {use_testnet})")
    
    def get_historical_data(self, symbol: str, interval: str, start_time: str, end_time: str) -> List[Dict]:
        """
        Get historical kline (candlestick) data.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTCUSDT')
            interval: Kline interval (e.g., '1m', '1h')
            start_time: Start time in ISO format (e.g., '2023-01-01T00:00:00')
            end_time: End time in ISO format
            
        Returns:
            List of OHLC candles
        """
        # Convert ISO format to milliseconds timestamp
        start_ts = int(datetime.fromisoformat(start_time).timestamp() * 1000)
        end_ts = int(datetime.fromisoformat(end_time).timestamp() * 1000)
        
        # Calculate number of candles
        interval_seconds = self.INTERVALS[interval]
        total_seconds = (end_ts - start_ts) / 1000
        num_candles = int(total_seconds / interval_seconds)
        
        logger.info(f"Fetching {num_candles} historical candles for {symbol} ({interval}) from {start_time} to {end_time}")
        
        # Binance has a limit of 1000 candles per request
        # If we need more, we need to make multiple requests
        all_candles = []
        current_start = start_ts
        
        while current_start < end_ts:
            # Make API request
            endpoint = "/api/v3/klines"
            params = {
                "symbol": symbol,
                "interval": interval,
                "startTime": current_start,
                "endTime": end_ts,
                "limit": 1000
            }
            
            response = requests.get(f"{self.base_url}{endpoint}", params=params)
            
            if response.status_code != 200:
                logger.error(f"Error fetching historical data: {response.text}")
                return []
            
            # Parse response
            candles = response.json()
            
            if not candles:
                break
            
            # Convert to OHLC format
            ohlc_candles = [{
                "timestamp": candle[0],
                "open": float(candle[1]),
                "high": float(candle[2]),
                "low": float(candle[3]),
                "close": float(candle[4]),
                "volume": float(candle[5]),
                "close_time": candle[6],
                "quote_asset_volume": float(candle[7]),
                "number_of_trades": int(candle[8]),
                "taker_buy_base_asset_volume": float(candle[9]),
                "taker_buy_quote_asset_volume": float(candle[10])
            } for candle in candles]
            
            all_candles.extend(ohlc_candles)
            
            # Update start time for next request
            current_start = candles[-1][0] + 1
            
            # Add a small delay to avoid API rate limits
            time.sleep(0.5)
        
        logger.info(f"Fetched {len(all_candles)} historical candles for {symbol}")
        return all_candles
    
    def get_current_price(self, symbol: str) -> float:
        """
        Get current price for a symbol.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTCUSDT')
            
        Returns:
            Current price
        """
        endpoint = "/api/v3/ticker/price"
        params = {"symbol": symbol}
        
        response = requests.get(f"{self.base_url}{endpoint}", params=params)
        
        if response.status_code != 200:
            logger.error(f"Error fetching current price: {response.text}")
            return 0.0
        
        data = response.json()
        return float(data["price"])
    
    def get_order_book(self, symbol: str, limit: int = 100) -> Dict:
        """
        Get order book (market depth) for a symbol.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTCUSDT')
            limit: Number of bids and asks to return
            
        Returns:
            Order book with bids and asks
        """
        endpoint = "/api/v3/depth"
        params = {"symbol": symbol, "limit": limit}
        
        response = requests.get(f"{self.base_url}{endpoint}", params=params)
        
        if response.status_code != 200:
            logger.error(f"Error fetching order book: {response.text}")
            return {"bids": [], "asks": []}
        
        data = response.json()
        
        # Convert strings to floats
        bids = [[float(price), float(qty)] for price, qty in data["bids"]]
        asks = [[float(price), float(qty)] for price, qty in data["asks"]]
        
        return {"bids": bids, "asks": asks}
    
    def connect_websocket(self, symbol: str, callbacks: Dict = None):
        """
        Connect to Binance WebSocket for real-time data.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTCUSDT')
            callbacks: Dictionary of callback functions for different stream types
        """
        if callbacks:
            self.on_kline_callback = callbacks.get("kline")
            self.on_trade_callback = callbacks.get("trade")
            self.on_depth_callback = callbacks.get("depth")
        
        # Create WebSocket connection
        streams = [
            f"{symbol.lower()}@kline_1m",
            f"{symbol.lower()}@trade",
            f"{symbol.lower()}@depth20@100ms"
        ]
        
        stream_url = f"{self.ws_url}/stream?streams={'/'.join(streams)}"
        
        # Close existing connection if any
        self.disconnect_websocket()
        
        # Create new connection
        self.ws = websocket.WebSocketApp(
            stream_url,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
            on_open=self._on_open
        )
        
        # Start WebSocket in a separate thread
        self.ws_thread = Thread(target=self.ws.run_forever)
        self.ws_thread.daemon = True
        self.ws_thread.start()
        
        logger.info(f"WebSocket connection initiated for {symbol}")
    
    def disconnect_websocket(self):
        """
        Disconnect from Binance WebSocket.
        """
        with self.ws_lock:
            if self.ws:
                self.ws.close()
                self.ws = None
                self.ws_connected = False
                logger.info("WebSocket connection closed")
    
    def _on_open(self, ws):
        """
        WebSocket connection opened.
        """
        with self.ws_lock:
            self.ws_connected = True
        logger.info("WebSocket connection opened")
    
    def _on_message(self, ws, message):
        """
        WebSocket message received.
        """
        try:
            data = json.loads(message)
            
            # Extract stream name and data
            stream = data.get("stream", "")
            stream_data = data.get("data", {})
            
            # Process based on stream type
            if "kline" in stream and self.on_kline_callback:
                kline = stream_data.get("k", {})
                ohlc = {
                    "timestamp": kline.get("t"),
                    "open": float(kline.get("o")),
                    "high": float(kline.get("h")),
                    "low": float(kline.get("l")),
                    "close": float(kline.get("c")),
                    "volume": float(kline.get("v")),
                    "close_time": kline.get("T"),
                    "is_closed": kline.get("x", False)
                }
                self.on_kline_callback(ohlc)
            
            elif "trade" in stream and self.on_trade_callback:
                trade = {
                    "timestamp": stream_data.get("T"),
                    "price": float(stream_data.get("p")),
                    "quantity": float(stream_data.get("q")),
                    "is_buyer_maker": stream_data.get("m", False)
                }
                self.on_trade_callback(trade)
            
            elif "depth" in stream and self.on_depth_callback:
                depth = {
                    "bids": [[float(p), float(q)] for p, q in stream_data.get("bids", [])],
                    "asks": [[float(p), float(q)] for p, q in stream_data.get("asks", [])]
                }
                self.on_depth_callback(depth)
        
        except Exception as e:
            logger.error(f"Error processing WebSocket message: {str(e)}")
    
    def _on_error(self, ws, error):
        """
        WebSocket error occurred.
        """
        logger.error(f"WebSocket error: {str(error)}")
    
    def _on_close(self, ws, close_status_code, close_msg):
        """
        WebSocket connection closed.
        """
        with self.ws_lock:
            self.ws_connected = False
        logger.info(f"WebSocket connection closed: {close_status_code} {close_msg}")
