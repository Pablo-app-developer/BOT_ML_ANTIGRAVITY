import sys
import time
import os
# Add parent dir to sys path to locate config and src if run from src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# --- Helper for Journaling ---
import csv
import os

def log_trade_to_csv(trade_data):
    file_exists = os.path.isfile('bot_journal.csv')
    try:
        with open('bot_journal.csv', 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'timestamp', 'symbol', 'action', 'entry', 'sl', 'tp', 'lots', 'reason'
            ])
            if not file_exists:
                writer.writeheader()
            writer.writerow(trade_data)
    except Exception as e:
        print(f"[!] Journal Error: {e}")

from datetime import datetime
import MetaTrader5 as mt5

from config import settings
from src.smc_analyst import SMCAnalyst
from src.execution_bridge import MT5Handler, ExecutionManager
from src.risk_guardian import RiskGuardian
from src.notifications import TelegramNotifier

def main():
    print("Starting Antigravity Fusion Bot...")
    
    # 1. Initialize Components
    guardian = RiskGuardian()
    bridge = MT5Handler(login=settings.MT5_LOGIN, password=settings.MT5_PASSWORD, server=settings.MT5_SERVER)
    analyst = SMCAnalyst(swing_lookback=settings.SWING_LOOKBACK) 
    exec_manager = ExecutionManager()
    notifier = TelegramNotifier(token=settings.TELEGRAM_TOKEN, chat_id=settings.TELEGRAM_CHAT_ID) # Alert System

    if not bridge.connect():
        print("Failed to connect to MT5. Exiting...")
        return
    
    # Send Startup Alert
    notifier.send_alert(f"🤖 Antigravity Bot STARTED\nRisk: {settings.RISK_PER_TRADE*100}%\nMode: {settings.PROJECT_NAME}")

    print("Connected to MT5 Terminal")
    print("All systems GREEN. Entering main loop...")
    
    try:
        while True:
            # Check Connection
            if not mt5.terminal_info():
                print("MT5 Disconnected. Attempting reconnect...")
                bridge.connect()
                time.sleep(5)
                continue
            
            # --- AUTO-PROTECTION (TRAILING STOP) ---
            exec_manager.update_trailing_stops()
            
            # --- RISK GUARDIAN LIVE UPDATE ---
            account_info = bridge.get_account_info()
            if account_info:
                guardian.update_daily_pnl(account_info.balance)

            # Check Risk Guardian GLOBAL
            if not guardian.can_trade():
                print(f"Risk Guardian has blocked trading. Current PnL: {guardian.current_daily_loss:.2f}%")
                time.sleep(300)
                continue
            
            # Check Killzones
            # We use MT5 Symbol Info to get current server time for one symbol
            time_struct = mt5.symbol_info_tick("EURUSD").time
            server_time = datetime.fromtimestamp(time_struct)
            current_hour = server_time.hour
            
            in_killzone = current_hour in settings.KILLZONES
            
            if not in_killzone:
                print(f". [Zzz] Outside Killzone (Date: {server_time}). Waiting...", end='\r')
                time.sleep(60)
                continue

            # --- MULTI-ASSET SCANNING LOOP ---
            # Memory to prevent duplicate trades on same candle
            if 'processed_signals' not in locals(): processed_signals = {}
            if 'processed_logs' not in locals(): processed_logs = {}
            
            for symbol in settings.SYMBOLS:
                # 2. Data Ingestion
                # Fetch LTF (Execution)
                df_ltf = bridge.get_data(symbol, settings.TIMEFRAME_LTF, n_bars=500)
                
                # Fetch HTF (Structure) - Increased to 300 for 200 EMA
                df_htf = bridge.get_data(symbol, settings.TIMEFRAME_HTF, n_bars=300)
                
                if df_ltf is None or df_ltf.empty: continue
                
                # Determine HTF Trend (EMA 50 & EMA 200)
                trend_bias = 0
                if df_htf is not None and not df_htf.empty:
                    close_htf = df_htf['Close']
                    if len(close_htf) > 200:
                        ema_50 = close_htf.ewm(span=50, adjust=False).mean().iloc[-1]
                        ema_200 = close_htf.ewm(span=200, adjust=False).mean().iloc[-1]
                        last_close = close_htf.iloc[-1]
                        
                        # Strong Trend Layout
                        if last_close > ema_50 and last_close > ema_200: 
                            trend_bias = 1   # BUY ONLY (Strong Bull)
                        elif last_close < ema_50 and last_close < ema_200:
                            trend_bias = -1  # SELL ONLY (Strong Bear)
                        else:
                            # Mixed Trend - Be careful or Neutral
                            # For safety in recovery mode, we prefer to stay out or follow EMA 200
                            if last_close > ema_200: trend_bias = 1
                            else: trend_bias = -1
                        
                        # print(f"      [Structure] {symbol} {settings.TIMEFRAME_HTF} Trend: {'BULL' if trend_bias==1 else 'BEAR'}")

                        # print(f"      [Structure] {symbol} {settings.TIMEFRAME_HTF} Trend: {'BULL' if trend_bias==1 else 'BEAR'}")

                # Get Symbol Info for Point Value (Correct JPY support)
                symbol_info = mt5.symbol_info(symbol)
                point_val = symbol_info.point if symbol_info else 0.0001

                # Run the full analysis pipeline with Trend Filter
                analysis_result = analyst.analyze(df_ltf, trend_bias=trend_bias, point=point_val)
                
                trap = analysis_result['trap_zone']
                signal = analysis_result['signal']
                
                # --- [VERBOSE] Heartbeat Status ---
                last_time = df_ltf.index[-1]
                # Check against processed_logs, NOT processed_signals
                if last_time != processed_logs.get(symbol):
                    # Si 'trap' existe, muestra los niveles de liquidez
                    if trap:
                        # Formatear niveles con 4 o 5 decimales
                        h_liq = f"{trap['high_liq']:.5f}"
                        l_liq = f"{trap['low_liq']:.5f}"
                        status_msg = f"[Watching Liq: {h_liq}/{l_liq}]"
                    else:
                        status_msg = "[Initializing]"

                    current_price = df_ltf['Close'].iloc[-1]
                    print(f"[{symbol} @ {current_price:.5f}] Status: {status_msg} | Bias: {trend_bias}")
                    sys.stdout.flush()
                    
                    # Update log state
                    processed_logs[symbol] = last_time
                
                # Logging Status (Only if trap exists to reduce noise)
                if trap:
                    # Note: We don't store global 'active_trap' per symbol in this simple loop yet
                    # For production, we should have a dict: active_traps[symbol]
                    # For now, just print the opportunity
                    # print(f"      [{symbol}] Liq Range: {trap['high_liq']} - {trap['low_liq']}")
                    pass
                
                # 4. Signal Execution
                if signal:
                    # Filter 1: One Trade Per Candle
                    signal_time = signal['timestamp'] # Using validation timestamp (time of candle analyzed)
                    
                    if symbol in processed_signals and processed_signals[symbol] == signal_time:
                        # Already traded this signal on this bar
                        continue
                        
                    # Filter 2: Anti-Hedging
                    positions = mt5.positions_get(symbol=symbol)
                    if positions:
                         # Simple check: if ANY position exists, skip. Keep it simple.
                         processed_signals[symbol] = signal_time
                         continue

                    # Filter 3: Slippage Guard (New!)
                    tick = mt5.symbol_info_tick(symbol)
                    if not tick: continue
                    
                    current_market_price = tick.ask if signal['action'] == 'BUY' else tick.bid
                    entry_price = signal['price'] # Signal price (Close of candle)
                    
                    # Diff in price
                    price_diff = abs(current_market_price - entry_price)
                    max_allowed_slippage = 0.0003 # 3 pips max (Safe for M15)
                    
                    if price_diff > max_allowed_slippage:
                         print(f"      [Shield] Slippage Too High. Skip.")
                         # We don't mark as processed effectively, allowing retry if price comes back?
                         # Or safer to skip this candle entirely? Let's skip.
                         processed_signals[symbol] = signal_time
                         continue

                    print(f"\n[$$$] ENTRY SIGNAL: {symbol} {signal['action']} @ {signal['price']}")
                    print(f"      Reason: {signal['reason']}")
                    
                    # Check Risk & Calculate Size
                    sl_price = signal['sl']
                    
                    # Dynamic lot size calculation based on risk
                    # Updated for multi-asset support (Gold/Indices)
                    tp_price = entry_price + (abs(entry_price - sl_price) * settings.RISK_REWARD_RATIO) if signal['action'] == 'BUY' else entry_price - (abs(entry_price - sl_price) * settings.RISK_REWARD_RATIO)
                    
                    balance = bridge.get_account_info().balance
                    lot_size = guardian.calculate_lot_size(symbol, entry_price, sl_price, settings.RISK_PER_TRADE, balance)
                    
                    # Debug Info
                    print(f"      Calculated Lot Size: {lot_size}")
                    
                    # EXECUTION (LIVE DEMO)
                    if lot_size > 0:
                        print(f"      [>>>] PLACING LIVE ORDER ({lot_size} lots)...")
                        
                        # Send Order
                        action_type = mt5.ORDER_TYPE_BUY if signal['action'] == 'BUY' else mt5.ORDER_TYPE_SELL
                        
                        # Since we are reacting to a completed candle Close, we use Market Order or aggressive Limit
                        # For simplicity and guarantee fill on sweep reclaim: Market Order
                        res = bridge.place_market_order(symbol, action_type, lot_size, sl_price, tp_price)
                        
                        if res: 
                            exec_manager.register_primary_entry(res.order)
                            print(f"      [V] ORDER FILLED! Ticket: {res.order}")
                            
                            # Log to Journal (CSV)
                            log_data = {
                                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                'symbol': symbol,
                                'action': signal['action'],
                                'entry': entry_price,
                                'sl': sl_price,
                                'tp': tp_price,
                                'lots': lot_size,
                                'reason': signal['reason']
                            }
                            log_trade_to_csv(log_data)
                            
                            # TELEGRAM ALERT (SPECTACULAR VISUALS)
                            try:
                                from src.visual_backtest import draw_spectacular_trade
                                
                                # Extract REAL Liquidity Levels seen by Analyst
                                real_liq_high = trap['high_liq'] if trap else 0.0
                                real_liq_low = trap['low_liq'] if trap else 0.0
                                
                                # Prepare Trade Info for the Chart
                                trade_info = {
                                    'symbol': symbol,
                                    'action': signal['action'],
                                    'entry': entry_price,
                                    'sl': sl_price,
                                    'tp': tp_price,
                                    'reason': signal['reason'],
                                    'rr': settings.RISK_REWARD_RATIO,
                                    'real_liq_high': real_liq_high, # <--- DATA REAL
                                    'real_liq_low': real_liq_low    # <--- DATA REAL
                                }
                                
                                chart_name = f"AUDIT_{symbol}_{res.order}_{datetime.now().strftime('%H%M%S')}.png"
                                draw_spectacular_trade(df_ltf, trade_info, output_file=chart_name)
                                
                                # Send Rich Message
                                msg = (
                                    f"🎯 **SMC EXECUTION**\n\n"
                                    f"🛡️ **Symbol:** {symbol}\n"
                                    f"🕹️ **Action:** {signal['action']}\n"
                                    f"💰 **Entry:** {entry_price}\n"
                                    f"🛑 **SL:** {sl_price} ({abs(entry_price-sl_price)*10000:.1f} pips)\n"
                                    f"🎯 **TP:** {tp_price} (RR 1:{settings.RISK_REWARD_RATIO})\n"
                                    f"📊 **Lots:** {lot_size}\n"
                                    f"🧠 **Logic:** {signal['reason']}"
                                )
                                
                                notifier.send_alert(msg, image_path=chart_name)
                                
                                # Clean up
                                if os.path.exists(chart_name): os.remove(chart_name)
                                
                            except Exception as e:
                                print(f"      [!] Alert Error: {e}")
                        else:
                            print("      [X] Order Failed")
                        
                    processed_signals[symbol] = signal_time # Mark as processed
            
            print(f". Scanning {len(settings.SYMBOLS)} assets... {datetime.now().strftime('%H:%M:%S')}", end='\r')
            time.sleep(10) # Scan every 10s
            
    except KeyboardInterrupt:
        print("Shutdown signal received.")
        bridge.shutdown()

if __name__ == "__main__":
    main()
