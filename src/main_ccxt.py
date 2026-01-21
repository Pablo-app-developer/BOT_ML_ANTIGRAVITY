import sys
import time
import os
import csv
from datetime import datetime
import ccxt
import pandas as pd
import numpy as np

# Add parent dir to sys path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import settings_ccxt as settings

# --- Helper for Journaling ---
def log_trade_to_csv(trade_data):
    file_exists = os.path.isfile('bot_journal.csv')
    try:
        with open('bot_journal.csv', 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'timestamp', 'symbol', 'action', 'entry', 'sl', 'tp', 'size', 'reason'
            ])
            if not file_exists:
                writer.writeheader()
            writer.writerow(trade_data)
    except Exception as e:
        print(f"[!] Journal Error: {e}")

# --- Simple SMC Analyst (Lightweight version) ---
class SimpleSMCAnalyst:
    def __init__(self, swing_lookback=96):
        self.swing_lookback = swing_lookback
    
    def find_swing_high_low(self, df, lookback):
        """Find swing highs and lows"""
        highs = df['high'].rolling(window=lookback, center=True).max()
        lows = df['low'].rolling(window=lookback, center=True).min()
        return highs, lows
    
    def analyze(self, df, trend_bias=0):
        """Simple SMC Analysis"""
        if len(df) < self.swing_lookback:
            return {'trap_zone': None, 'signal': None}
        
        # Find liquidity levels
        highs, lows = self.find_swing_high_low(df, self.swing_lookback)
        high_liq = highs.max()
        low_liq = lows.min()
        
        # Current price
        current_close = df['close'].iloc[-1]
        current_high = df['high'].iloc[-1]
        current_low = df['low'].iloc[-1]
        
        # Simple breakout detection
        prev_close = df['close'].iloc[-2]
        
        signal = None
        
        # BUY: Price swept low and reclaimed
        if trend_bias >= 0:
            if current_low <= low_liq * 1.0005 and current_close > low_liq:
                signal = {
                    'action': 'BUY',
                    'price': current_close,
                    'sl': low_liq * 0.999,
                    'reason': 'Low Sweep + Reclaim',
                    'timestamp': df.index[-1]
                }
        
        # SELL: Price swept high and reclaimed down
        if trend_bias <= 0:
            if current_high >= high_liq * 0.9995 and current_close < high_liq:
                signal = {
                    'action': 'SELL',
                    'price': current_close,
                    'sl': high_liq * 1.001,
                    'reason': 'High Sweep + Reclaim',
                    'timestamp': df.index[-1]
                }
        
        return {
            'trap_zone': {'high_liq': high_liq, 'low_liq': low_liq},
            'signal': signal
        }

# --- Risk Guardian ---
class RiskGuardian:
    def __init__(self):
        self.starting_balance = None
        self.current_daily_loss = 0.0
    
    def update_daily_pnl(self, current_balance):
        if self.starting_balance is None or self.starting_balance == 0:
            self.starting_balance = current_balance
        
        if self.starting_balance > 0:
            pnl = (current_balance - self.starting_balance) / self.starting_balance
            self.current_daily_loss = pnl
        else:
            self.current_daily_loss = 0.0
    
    def can_trade(self):
        return self.current_daily_loss > -settings.DAILY_LOSS_LIMIT
    
    def calculate_position_size(self, symbol, entry_price, sl_price, balance):
        """Calculate position size based on risk"""
        # Validar balance válido
        if balance <= 0:
            print(f"[!] Balance inválido: {balance}")
            return 0
        
        risk_amount = balance * settings.RISK_PER_TRADE
        sl_distance = abs(entry_price - sl_price)
        
        # Evitar división por cero
        if sl_distance == 0 or sl_distance < 0.0001:
            print(f"[!] SL distance muy pequeña: {sl_distance}")
            return 0
        
        # For crypto, size is in base currency
        position_size = risk_amount / sl_distance
        
        # Minimum 0.001 for most exchanges
        min_size = 0.001
        
        # Maximum reasonable size (safety check)
        max_size = (balance * 0.1) / entry_price  # Max 10% of balance
        
        final_size = max(min(position_size, max_size), min_size)
        return round(final_size, 6)

# --- Main Bot ---
class CCXTSMCBot:
    def __init__(self):
        self.exchange = self.init_exchange()
        self.guardian = RiskGuardian()
        self.analyst = SimpleSMCAnalyst(swing_lookback=settings.SWING_LOOKBACK)
        self.processed_signals = {}
        self.processed_logs = {}
        
        print(f"✅ Bot iniciado con {settings.EXCHANGE_NAME}")
        print(f"💰 Símbolos: {', '.join(settings.SYMBOLS)}")
        print(f"⚡ Timeframe: {settings.TIMEFRAME_LTF} / {settings.TIMEFRAME_HTF}")
    
    def init_exchange(self):
        """Initialize CCXT exchange"""
        exchange_class = getattr(ccxt, settings.EXCHANGE_NAME)
        
        exchange = exchange_class({
            'apiKey': settings.API_KEY,
            'secret': settings.API_SECRET,
            'enableRateLimit': True,
            'options': {'defaultType': 'spot'}  # or 'future' for futures
        })
        
        if hasattr(settings, 'API_PASSWORD') and settings.API_PASSWORD:
            exchange.password = settings.API_PASSWORD
        
        return exchange
    
    def get_balance(self):
        """Get account balance"""
        try:
            balance = self.exchange.fetch_balance()
            return balance['USDT']['free'] if 'USDT' in balance else 0
        except Exception as e:
            print(f"[!] Error fetching balance: {e}")
            return 0
    
    def get_ohlcv(self, symbol, timeframe, limit=500):
        """Fetch OHLCV data"""
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            return df
        except Exception as e:
            print(f"[!] Error fetching {symbol} data: {e}")
            return None
    
    def place_order(self, symbol, side, amount, price, sl_price, tp_price):
        """Place market order with SL/TP"""
        try:
            # Place market order
            order = self.exchange.create_order(
                symbol=symbol,
                type='market',
                side=side.lower(),
                amount=amount
            )
            
            print(f"✅ Order placed: {order['id']}")
            
            # Note: SL/TP handling depends on exchange
            # Some exchanges support SL/TP in create_order params
            # Others require separate stop-loss orders
            # For simplicity, we'll log them but not place (you can enhance this)
            
            return order
        except Exception as e:
            print(f"❌ Order failed: {e}")
            return None
    
    def has_open_position(self, symbol):
        """Check if we have open position for symbol"""
        try:
            # For spot: check if we have base currency balance
            base = symbol.split('/')[0]
            balance = self.exchange.fetch_balance()
            return balance.get(base, {}).get('free', 0) > 0
        except:
            return False
    
    def run(self):
        """Main loop"""
        print("\n🚀 Bot corriendo...\n")
        
        try:
            while True:
                # Update balance and risk
                balance = self.get_balance()
                self.guardian.update_daily_pnl(balance)
                
                if not self.guardian.can_trade():
                    print(f"🛑 Risk Guardian bloqueó trading. PnL: {self.guardian.current_daily_loss:.2%}")
                    time.sleep(300)
                    continue
                
                # Scan symbols
                for symbol in settings.SYMBOLS:
                    try:
                        # Fetch data
                        df_ltf = self.get_ohlcv(symbol, settings.TIMEFRAME_LTF, 500)
                        df_htf = self.get_ohlcv(symbol, settings.TIMEFRAME_HTF, 300)
                        
                        if df_ltf is None or df_htf is None:
                            continue
                        
                        # Determine trend bias (simple EMA)
                        trend_bias = 0
                        if len(df_htf) > 200:
                            ema_50 = df_htf['close'].ewm(span=50, adjust=False).mean().iloc[-1]
                            ema_200 = df_htf['close'].ewm(span=200, adjust=False).mean().iloc[-1]
                            last_close = df_htf['close'].iloc[-1]
                            
                            if last_close > ema_50 and last_close > ema_200:
                                trend_bias = 1  # Bullish
                            elif last_close < ema_50 and last_close < ema_200:
                                trend_bias = -1  # Bearish
                        
                        # Analyze
                        result = self.analyst.analyze(df_ltf, trend_bias)
                        trap = result['trap_zone']
                        signal = result['signal']
                        
                        # Log status
                        last_time = df_ltf.index[-1]
                        if last_time != self.processed_logs.get(symbol):
                            current_price = df_ltf['close'].iloc[-1]
                            bias_str = "BULL" if trend_bias == 1 else "BEAR" if trend_bias == -1 else "NEUTRAL"
                            
                            if trap:
                                print(f"[{symbol} @ ${current_price:.4f}] Liq: {trap['low_liq']:.4f}/{trap['high_liq']:.4f} | {bias_str}")
                            else:
                                print(f"[{symbol} @ ${current_price:.4f}] Inicializando... | {bias_str}")
                            
                            self.processed_logs[symbol] = last_time
                        
                        # Execute signal
                        if signal:
                            signal_time = signal['timestamp']
                            
                            # Check if already processed
                            if symbol in self.processed_signals and self.processed_signals[symbol] == signal_time:
                                continue
                            
                            # Check if we have position
                            if self.has_open_position(symbol):
                                self.processed_signals[symbol] = signal_time
                                continue
                            
                            # Calculate position size
                            entry_price = signal['price']
                            sl_price = signal['sl']
                            tp_price = entry_price + (abs(entry_price - sl_price) * settings.RISK_REWARD_RATIO) if signal['action'] == 'BUY' else entry_price - (abs(entry_price - sl_price) * settings.RISK_REWARD_RATIO)
                            
                            position_size = self.guardian.calculate_position_size(symbol, entry_price, sl_price, balance)
                            
                            if position_size > 0:
                                print(f"\n🎯 SEÑAL: {symbol} {signal['action']} @ ${entry_price:.4f}")
                                print(f"   SL: ${sl_price:.4f} | TP: ${tp_price:.4f}")
                                print(f"   Tamaño: {position_size:.6f}")
                                print(f"   Razón: {signal['reason']}")
                                
                                # Place order
                                order = self.place_order(
                                    symbol,
                                    signal['action'],
                                    position_size,
                                    entry_price,
                                    sl_price,
                                    tp_price
                                )
                                
                                if order:
                                    # Log to CSV
                                    log_trade_to_csv({
                                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                        'symbol': symbol,
                                        'action': signal['action'],
                                        'entry': entry_price,
                                        'sl': sl_price,
                                        'tp': tp_price,
                                        'size': position_size,
                                        'reason': signal['reason']
                                    })
                            
                            self.processed_signals[symbol] = signal_time
                    
                    except Exception as e:
                        print(f"[!] Error procesando {symbol}: {e}")
                        continue
                
                # Sleep between scans
                time.sleep(10)
        
        except KeyboardInterrupt:
            print("\n👋 Bot detenido por usuario")

if __name__ == "__main__":
    bot = CCXTSMCBot()
    bot.run()
