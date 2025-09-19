#!/usr/bin/env python3
"""
Configuration module for Trader Bot.

Handles loading and saving configuration settings.
"""

import os
import json
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_CONFIG = {
    "api": {
        "binance": {
            "api_key": "",
            "api_secret": "",
            "testnet": True
        }
    },
    "trading": {
        "default_symbol": "BTCUSDT",
        "default_interval": "1m",
        "commission_rate": 0.001,  # 0.1%
        "initial_balance": 1000.0,  # USDT
        "max_position_size": 0.95  # 95% of balance
    },
    "ui": {
        "chart_max_candles": 100,
        "default_ma_periods": [9, 20, 50],
        "default_rsi_period": 14,
        "theme": "dark"
    },
    "strategies": {
        "moving_average_crossover": {
            "fast_period": 9,
            "slow_period": 20
        },
        "rsi_strategy": {
            "period": 14,
            "oversold": 30,
            "overbought": 70
        },
        "macd_strategy": {
            "fast_period": 12,
            "slow_period": 26,
            "signal_period": 9
        }
    }
}

# Configuration file path
CONFIG_FILE = os.path.expanduser("~/.traderbot/config.json")


def load_config() -> Dict[str, Any]:
    """Load configuration from file or create default if not exists."""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                logger.info("Configuration loaded from %s", CONFIG_FILE)
                return config
        else:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
            save_config(DEFAULT_CONFIG)
            logger.info("Default configuration created at %s", CONFIG_FILE)
            return DEFAULT_CONFIG
    except Exception as e:
        logger.error("Error loading configuration: %s", str(e))
        logger.info("Using default configuration")
        return DEFAULT_CONFIG


def save_config(config: Dict[str, Any]) -> bool:
    """Save configuration to file."""
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
        logger.info("Configuration saved to %s", CONFIG_FILE)
        return True
    except Exception as e:
        logger.error("Error saving configuration: %s", str(e))
        return False


def update_config(section: str, key: str, value: Any) -> bool:
    """Update a specific configuration value."""
    config = load_config()
    
    # Create section if it doesn't exist
    if section not in config:
        config[section] = {}
    
    # Update value
    config[section][key] = value
    
    # Save updated config
    return save_config(config)


def get_api_keys() -> tuple:
    """Get Binance API keys from configuration."""
    config = load_config()
    api_key = config.get("api", {}).get("binance", {}).get("api_key", "")
    api_secret = config.get("api", {}).get("binance", {}).get("api_secret", "")
    testnet = config.get("api", {}).get("binance", {}).get("testnet", True)
    
    return api_key, api_secret, testnet
