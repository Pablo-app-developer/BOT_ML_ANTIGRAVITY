
import MetaTrader5 as mt5
from datetime import datetime, timedelta
import pandas as pd
from config import settings

def audit_today():
    if not mt5.initialize():
        print("Failed to init MT5")
        return

    # Login check
    if not mt5.login(settings.MT5_LOGIN, password=settings.MT5_PASSWORD, server=settings.MT5_SERVER):
        print("Login failed")
        return

    # Definir "Hoy" (Desde medianoche server)
    now = datetime.now()
    today_start = datetime(now.year, now.month, now.day)
    
    # Obtener historial de DEALS (Operaciones cerradas)
    deals = mt5.history_deals_get(today_start, now)
    
    total_profit = 0.0
    print(f"\n--- AUDITORÍA DE HOY ({today_start.date()}) ---")
    
    if deals:
        df = pd.DataFrame(list(deals), columns=deals[0]._asdict().keys())
        # Filtrar solo entradas/salidas (ignorar balance inicial si aparece como deal)
        # Entry in/out logic is complex, simpler to just sum 'profit' + 'commission' + 'swap'
        
        for deal in deals:
            # Tipos: 0=BUY, 1=SELL, but deals are execution steps.
            # Entry=0, Entry_Out=1. 
            # Profit logic: Only deals with profit != 0 are usually exits.
            if deal.profit != 0:
                pnl = deal.profit + deal.swap + deal.commission
                total_profit += pnl
                symbol = deal.symbol
                type_str = "WIN" if pnl > 0 else "LOSS"
                print(f"[{symbol}] {type_str}: ${pnl:.2f}")
    else:
        print("No closed trades today.")

    # Verificar posiciones ABIERTAS (Floating PnL)
    positions = mt5.positions_get()
    floating_pnl = 0.0
    print("\n--- POSICIONES ABIERTAS ---")
    if positions:
        for pos in positions:
            floating_pnl += pos.profit
            print(f"[{pos.symbol}] Floating: ${pos.profit:.2f} (Price: {pos.price_current})")
    else:
        print("No open positions.")
        
    print("\n" + "="*30)
    print(f"CLOSED PnL:   ${total_profit:.2f}")
    print(f"FLOATING PnL: ${floating_pnl:.2f}")
    print(f"NET EQUITY:   ${mt5.account_info().equity:.2f}")
    print("="*30)

    mt5.shutdown()

if __name__ == "__main__":
    audit_today()
