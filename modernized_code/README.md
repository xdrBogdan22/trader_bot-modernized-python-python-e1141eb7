# Trader Bot - Cryptocurrency Trading Platform

## Project Overview
Trader Bot is a high-performance cryptocurrency trading bot designed to execute automated trading strategies on the Binance exchange. It provides a complete environment for developing, testing, and executing trading strategies with real-time data visualization, backtesting capabilities, and direct integration with Binance.

## Architecture

### Core Components
- **Main Application**: Entry point with GUI interface and tab-based navigation
- **Trading Strategies**: Modular strategy implementations with a common interface
- **Data Providers**: Real-time and historical data fetching from Binance
- **Visualization**: Real-time charts and indicators
- **Account Management**: Handling real and simulated trading accounts

### Business Flow Implementation
- **Strategy Backtesting**: Implemented in `backtesting.py` and `history_tab.py`
- **Real-time Trading**: Implemented in `trading.py`, `binance_tab.py`, and `fake_account_tab.py`
- **Manual Trading**: Implemented in `trading.py` with UI controls in tab modules
- **Strategy Development**: Base interface in `strategy_interface.py` with implementations in `strategies/`

## Installation Instructions

### Prerequisites
- Python 3.8 or higher
- Binance account (for real trading)

### Setup
1. Clone the repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Configure your Binance API keys in `config.py` (optional for real trading)
4. Run the application:
   ```
   python main.py
   ```

## Usage Examples

### Running a Backtest
```python
from backtesting import Backtester
from strategies.moving_average_crossover import MovingAverageCrossover

backtester = Backtester("BTCUSDT", "2023-01-01", "2023-02-01")
strategy = MovingAverageCrossover(fast_period=10, slow_period=30)
results = backtester.run(strategy)
print(f"Total profit: {results['total_profit']}%")
```

### Running a Live Trading Strategy
```python
from trading import TradingBot
from strategies.rsi_strategy import RSIStrategy

bot = TradingBot("BTCUSDT", use_real_account=False)
strategy = RSIStrategy(oversold=30, overbought=70)
bot.set_strategy(strategy)
bot.start()
# Let it run for a while
bot.stop()
```

## API Documentation

### Strategy Interface
All trading strategies must implement the `TradeStrategyInterface` class:

```python
class TradeStrategyInterface:
    def execute(self, current_price, in_position):
        # Return buy/sell signal or None
        pass
        
    def feed_ohlc(self, ohlc_data):
        # Process OHLC data
        pass
        
    def feed_depth(self, depth_data):
        # Process market depth data
        pass
        
    def feed_price_quantity_volume(self, price, quantity, volume):
        # Process real-time price updates
        pass
```

### Data Provider API
The `BinanceDataProvider` class handles all data fetching:

```python
from data_provider import BinanceDataProvider

provider = BinanceDataProvider()
historical_data = provider.get_historical_data("BTCUSDT", "1h", "2023-01-01", "2023-02-01")
```

## Business Logic Mapping

| Business Requirement | Implementation Module |
|---------------------|------------------------|
| Strategy Backtesting | `backtesting.py` |
| Real-time Trading | `trading.py` |
| Market Data Visualization | `visualization.py` |
| Account Management | `account.py` |
| Performance Tracking | `performance.py` |

## Dependencies

- **Binance API Client**: For interacting with Binance exchange
- **Pandas**: For data manipulation and analysis
- **NumPy**: For numerical computations
- **Matplotlib**: For chart visualization in backtesting
- **PyQt5**: For GUI implementation
- **websocket-client**: For real-time data streaming
- **ta**: Technical analysis library for indicators

## Implementation Notes

### Technical Decisions
- **Modular Architecture**: Each component is designed to be independent and reusable
- **Strategy Pattern**: Used for implementing different trading strategies with a common interface
- **Observer Pattern**: Used for real-time data updates and UI notifications
- **Factory Pattern**: Used for creating different types of charts and indicators

### Performance Considerations
- Real-time data processing is optimized for low latency
- Historical data is cached to improve backtesting performance
- Indicators are calculated incrementally when possible to avoid redundant computations

### Future Improvements
- Add machine learning-based strategies
- Implement portfolio management for multiple coins
- Add risk management features
- Improve visualization with more advanced charts
