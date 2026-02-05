import sqlite3
import os
from datetime import datetime
from contextlib import contextmanager

DB_PATH = "data/trading_history.db"

def init_database():
    """Inicializa la base de datos con las tablas necesarias."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Tabla de operaciones
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bot_name TEXT NOT NULL,
            timestamp DATETIME NOT NULL,
            action TEXT NOT NULL,
            price REAL NOT NULL,
            pnl_pct REAL,
            balance REAL NOT NULL,
            win_rate REAL,
            daily_drawdown REAL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Tabla de métricas diarias
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bot_name TEXT NOT NULL,
            date DATE NOT NULL,
            total_trades INTEGER DEFAULT 0,
            winning_trades INTEGER DEFAULT 0,
            losing_trades INTEGER DEFAULT 0,
            total_pnl REAL DEFAULT 0,
            max_drawdown REAL DEFAULT 0,
            final_balance REAL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(bot_name, date)
        )
    ''')
    
    conn.commit()
    conn.close()

@contextmanager
def get_db_connection():
    """Context manager para conexiones a la base de datos."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def save_trade(bot_name, action, price, pnl_pct=None, balance=0, win_rate=0, daily_drawdown=0):
    """Guarda una operación en la base de datos."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO trades (bot_name, timestamp, action, price, pnl_pct, balance, win_rate, daily_drawdown)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (bot_name, datetime.now(), action, price, pnl_pct, balance, win_rate, daily_drawdown))
        conn.commit()

def update_daily_metrics(bot_name, date, trades_count, winning_count, losing_count, total_pnl, max_dd, final_balance):
    """Actualiza las métricas diarias de un bot."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO daily_metrics (bot_name, date, total_trades, winning_trades, losing_trades, total_pnl, max_drawdown, final_balance)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(bot_name, date) DO UPDATE SET
                total_trades = excluded.total_trades,
                winning_trades = excluded.winning_trades,
                losing_trades = excluded.losing_trades,
                total_pnl = excluded.total_pnl,
                max_drawdown = excluded.max_drawdown,
                final_balance = excluded.final_balance
        ''', (bot_name, date, trades_count, winning_count, losing_count, total_pnl, max_dd, final_balance))
        conn.commit()

def get_all_trades(bot_name=None, limit=100):
    """Obtiene las últimas operaciones."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if bot_name:
            cursor.execute('SELECT * FROM trades WHERE bot_name = ? ORDER BY timestamp DESC LIMIT ?', (bot_name, limit))
        else:
            cursor.execute('SELECT * FROM trades ORDER BY timestamp DESC LIMIT ?', (limit,))
        return cursor.fetchall()

def get_bot_summary():
    """Obtiene un resumen del rendimiento de todos los bots."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT 
                bot_name,
                COUNT(*) as total_trades,
                SUM(CASE WHEN pnl_pct > 0 THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN pnl_pct < 0 THEN 1 ELSE 0 END) as losses,
                AVG(pnl_pct) as avg_pnl,
                MAX(balance) as current_balance
            FROM trades
            WHERE action = 'VENTA'
            GROUP BY bot_name
        ''')
        return cursor.fetchall()
