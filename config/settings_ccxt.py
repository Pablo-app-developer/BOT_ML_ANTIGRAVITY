import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Project Settings
PROJECT_NAME = "Antigravity CCXT Bot"

# Exchange Configuration
# Supported: 'binance', 'gateio', 'kucoin', 'bybit', 'okx'
EXCHANGE_NAME = os.getenv("EXCHANGE_NAME", "gateio")

# API Credentials (set via .env or environment variables)
API_KEY = os.getenv("API_KEY", "")
API_SECRET = os.getenv("API_SECRET", "")
API_PASSWORD = os.getenv("API_PASSWORD", "")  # For Gate.io, OKX, etc.

# Symbols to trade (use exchange format)
SYMBOLS = [
    "BTC/USDT",
    "ETH/USDT",
    "SOL/USDT"
]

# Timeframes
TIMEFRAME_HTF = "4h"  # Higher timeframe for trend
TIMEFRAME_LTF = "15m"  # Lower timeframe for entry

# Risk Management
RISK_PER_TRADE = 0.01      # 1% risk per trade
DAILY_LOSS_LIMIT = 0.03    # 3% daily hard stop
RISK_REWARD_RATIO = 3.0    # 1:3 RR

# Strategy Parameters
SWING_LOOKBACK = 96  # Lookback period for swing highs/lows

# Telegram Notifications (optional)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8525594644:AAFEI0glCrynMakhHdKZ8cenrNp0RU-9b4Q")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "1127342579")
