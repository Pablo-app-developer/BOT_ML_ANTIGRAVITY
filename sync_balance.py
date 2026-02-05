from database import init_database, save_trade

# Balances reales obtenidos de los logs (2026-02-04)
current_balances = {
    "BTC": 100042.82,
    "ETH": 100180.69,
    "SOL": 99964.57
}

print("🔄 Sincronizando base de datos con saldos reales...")

# Asegurar que la DB existe
init_database()

for symbol, balance in current_balances.items():
    print(f"👉 Actualizando {symbol} a ${balance:,.2f}")
    
    # Insertamos una operación especial de tipo "SYNC"
    # Ponemos precio 0 y pnl 0 para que no afecte estadísticas de trading, solo el balance
    save_trade(
        bot_name=symbol, 
        action="SYNC", 
        price=0.0, 
        pnl_pct=0.0, 
        balance=balance, 
        win_rate=0.0, 
        daily_drawdown=0.0
    )

print("✅ ¡Sincronización completada! El dashboard ahora mostrará los saldos correctos.")
