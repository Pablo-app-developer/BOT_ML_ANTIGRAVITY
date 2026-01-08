import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import json
import os
from stable_baselines3 import PPO
from trading_env import TradingEnv
from config import get_asset_config

def calculate_metrics(net_worths, steps_per_day=96):
    """
    Calculate extensive financial metrics.
    """
    returns = np.diff(net_worths) / net_worths[:-1]
    
    # 1. Total Return
    initial = net_worths[0]
    final = net_worths[-1]
    total_return_pct = ((final - initial) / initial) * 100
    
    # 2. Annualized Return (Approximate)
    days = len(net_worths) / steps_per_day
    years = days / 252
    if years > 0:
        cagr = ((final / initial) ** (1 / years)) - 1
    else:
        cagr = 0
        
    # 3. Sharpe Ratio
    risk_free_rate = 0.0
    excess_returns = returns - risk_free_rate/ (252*steps_per_day)
    sharpe = np.mean(excess_returns) / (np.std(returns) + 1e-9) * np.sqrt(252 * steps_per_day)
    
    # 4. Sortino Ratio
    negative_returns = returns[returns < 0]
    downside_std = np.std(negative_returns) if len(negative_returns) > 0 else 1e-9
    sortino = np.mean(excess_returns) / (downside_std + 1e-9) * np.sqrt(252 * steps_per_day)
    
    # 5. Max Drawdown & Duration
    running_max = np.maximum.accumulate(net_worths)
    drawdowns = (running_max - net_worths) / running_max
    max_drawdown_pct = drawdowns.max() * 100
    
    # Drawdown Duration (in steps)
    is_drawdown = drawdowns > 0
    current_duration = 0
    max_duration = 0
    for in_dd in is_drawdown:
        if in_dd:
            current_duration += 1
        else:
            max_duration = max(max_duration, current_duration)
            current_duration = 0
    max_duration = max(max_duration, current_duration)
    
    # 6. Calmar Ratio
    calmar = cagr / (max_drawdown_pct / 100) if max_drawdown_pct > 0 else 0
    
    return {
        "return_pct": total_return_pct,
        "cagr": cagr * 100,
        "sharpe": sharpe,
        "sortino": sortino,
        "calmar": calmar,
        "max_drawdown_pct": max_drawdown_pct,
        "max_dd_duration_steps": max_duration,
        "max_dd_duration_days": max_duration / steps_per_day
    }

def run_backtest(asset_name="BTC", model_path=None, data_path=None, chart_name=None):
    asset_name = asset_name.upper()
    
    # Default paths if not provided
    if model_path is None:
        model_path = f"models/PRODUCTION/{asset_name}/ppo_{asset_name.lower()}_final.zip"
            
    if data_path is None:
        data_path = f"datos_{asset_name.lower()}_15m_binance.csv"

    if chart_name is None:
        chart_name = f"backtest_{asset_name.lower()}_latest.png"

    print(f"📊 Running Backtest for {asset_name} using {model_path}...")
    
    # Load Data
    if not os.path.exists(data_path):
        print(f"❌ Data file not found: {data_path}")
        return
    df = pd.read_csv(data_path)

    # Load Config (Professional Refactor)
    config = get_asset_config(asset_name)
    if config:
        print(f"🎯 Config loaded for {asset_name}: {config.env_params}")
        env_params = config.env_params
    else:
         # Fallback for BTC or Testing
         env_params = {"commission": 0.0005} 
         print(f"⚠️ No specialist config found. Using default params.")
    
    env = TradingEnv(df, **env_params)
    
    # Load Model
    try:
        model = PPO.load(model_path)
    except Exception as e:
        print(f"❌ Could not load model: {e}")
        return
    
    obs, info = env.reset()
    done = False
    truncated = False
    
    net_worths = []
    real_trades = 0
    
    while not done and not truncated:
        action, _states = model.predict(obs, deterministic=True)
        if hasattr(action, 'item'): action = int(action.item())
        
        obs, reward, done, truncated, info = env.step(action)
        if info.get('trade_executed', False): real_trades += 1
        net_worths.append(info['net_worth'])
        
    # Full Metric Analysis
    net_worths = np.array(net_worths)
    metrics = calculate_metrics(net_worths)
    
    # Save Results Data
    os.makedirs("reports", exist_ok=True)
    results_file = "reports/results_summary.json"
    
    current_results = {}
    if os.path.exists(results_file):
        with open(results_file, 'r') as f:
            try:
                current_results = json.load(f)
            except:
                current_results = {}
                
    current_results[asset_name] = {
        "initial_balance": env.initial_balance,
        "final_balance": net_worths[-1],
        "total_trades": real_trades,
        "chart_path": f"reports/{chart_name}",
        **metrics # Unpack all new metrics
    }
    
    with open(results_file, 'w') as f:
        json.dump(current_results, f, indent=4)
    
    # Plotting
    plt.figure(figsize=(12, 6))
    plt.plot(net_worths, label='Equity Curve', color='#00ffcc', linewidth=2)
    plt.axhline(y=env.initial_balance, color='white', linestyle='--', alpha=0.5)
    
    title_text = (f"{asset_name} | Ret: {metrics['return_pct']:.2f}% | Sharpe: {metrics['sharpe']:.2f} | "
                  f"Sortino: {metrics['sortino']:.2f} | DD: {metrics['max_drawdown_pct']:.2f}%")
    
    plt.title(title_text, fontsize=12, color='white')
    plt.xlabel('Steps', color='white')
    plt.ylabel('Net Worth ($)', color='white')
    plt.grid(True, alpha=0.1)
    plt.legend()
    
    plt.gcf().set_facecolor('#1e1e1e')
    plt.gca().set_facecolor('#2d2d2d')
    plt.gca().tick_params(colors='white')
    
    chart_dest = f"reports/{chart_name}"
    plt.savefig(chart_dest, facecolor='#1e1e1e')
    plt.close()

    print(f"✅ {asset_name} Backtest Complete.")
    print(f"   Return: {metrics['return_pct']:.2f}%")
    print(f"   Sharpe: {metrics['sharpe']:.2f} | Sortino: {metrics['sortino']:.2f}")
    print(f"   Calmar: {metrics['calmar']:.2f} | Max DD: {metrics['max_drawdown_pct']:.2f}%")
    print(f"   Deepest Drawdown Duration: {metrics['max_dd_duration_days']:.1f} days")

if __name__ == "__main__":
    import sys
    asset = sys.argv[1].upper() if len(sys.argv) > 1 else "BTC"
    model = sys.argv[2] if len(sys.argv) > 2 else None
    chart = sys.argv[3] if len(sys.argv) > 3 else None
    run_backtest(asset, model_path=model, chart_name=chart)
