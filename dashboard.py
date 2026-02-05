import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
from database import get_bot_summary, get_all_trades

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Antigravity | Pro Terminal",
    page_icon="💸",
    layout="wide",
    initial_sidebar_state="collapsed"  # Más espacio para datos
)

# --- ESTILOS CSS PERSONALIZADOS (MODERN DARK UI) ---
st.markdown("""
<style>
    /* Fondo General */
    .stApp {
        background-color: #0e1117;
    }
    
    /* Métricas Principales (KPIs) */
    div[data-testid="metric-container"] {
        background-color: #1a1c24;
        border: 1px solid #2d2f36;
        padding: 15px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        transition: transform 0.2s;
    }
    div[data-testid="metric-container"]:hover {
        transform: translateY(-2px);
        border-color: #4e5d6c;
    }
    
    /* Títulos Grandes */
    .big-font {
        font-size: 24px !important;
        font-weight: 600;
        color: #e0e0e0;
        margin-bottom: 20px;
    }
    
    /* Tablas */
    div[data-testid="stDataFrame"] {
        background-color: #1a1c24;
        border-radius: 8px;
        padding: 10px;
    }
    
    /* Badge de Estado */
    .status-badge {
        padding: 4px 8px;
        border-radius: 4px;
        font-weight: bold;
        font-size: 12px;
    }
    .status-long { background-color: #00c853; color: white; }
    .status-flat { background-color: #78909c; color: white; }
    
</style>
""", unsafe_allow_html=True)

# --- HEADER PROFESIONAL ---
col_head1, col_head2 = st.columns([3, 1])
with col_head1:
    st.markdown("## 🛰️ Antigravity AI Fund <span style='font-size:14px; color:gray;'>| Live Trading Terminal</span>", unsafe_allow_html=True)
with col_head2:
    st.markdown(f"<div style='text-align:right; color:#78909c;'>Updated: {datetime.now().strftime('%H:%M:%S')}</div>", unsafe_allow_html=True)
    if st.button("🔄 Actualizar Datos", use_container_width=True):
        st.rerun()

# --- CARGA DE DATOS ---
try:
    summary_data = get_bot_summary()
    trades_data = get_all_trades(limit=1000)
    
    # DataFrames
    df_summary = pd.DataFrame(summary_data, columns=['bot_name', 'total_trades', 'wins', 'losses', 'avg_pnl', 'current_balance'])
    df_trades = pd.DataFrame(trades_data, columns=['id', 'bot_name', 'timestamp', 'action', 'price', 'pnl_pct', 'balance', 'win_rate', 'daily_drawdown', 'created_at'])

    # --- CALCULOS GLOBALES ---
    initial_capital = 300000.00
    current_total_balance = df_summary['current_balance'].sum() if not df_summary.empty else initial_capital
    total_pnl_abs = current_total_balance - initial_capital
    total_roi_pct = (total_pnl_abs / initial_capital) * 100
    
    active_bots_count = len(df_summary)

    # --- TOP ROW: GLOBAL KPIs ---
    st.markdown("---")
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)

    kpi1.metric(
        label="💰 Capital Total (NAV)",
        value=f"${current_total_balance:,.2f}",
        delta=f"${total_pnl_abs:,.2f} ({total_roi_pct:+.2f}%)",
        delta_color="normal"
    )

    # Calcular PnL de hoy (aprox)
    today_str = datetime.now().strftime('%Y-%m-%d')
    df_trades['timestamp'] = pd.to_datetime(df_trades['timestamp'])
    today_pnl = 0.0
    
    if not df_trades.empty:
        today_trades = df_trades[df_trades['timestamp'].dt.date == datetime.now().date()]
        # Aproximación basada en logs de VENTA hoy
        today_sells = today_trades[today_trades['action'] == 'VENTA']
        # El PnL real por operación no está explícito en monto, pero podemos estimarlo o sumarlo si lo tuviéramos
        # Por ahora usaremos el conteo de operaciones hoy
        ops_today = len(today_trades)
    
    kpi2.metric(
        label="📊 Operaciones Hoy",
        value=ops_today if 'ops_today' in locals() else 0,
        delta="Actividad Reciente",
        delta_color="off"
    )

    best_bot = df_summary.loc[df_summary['current_balance'].idxmax()] if not df_summary.empty else None
    kpi3.metric(
        label="🏆 Bot Líder",
        value=best_bot['bot_name'] if best_bot is not None else "-",
        delta=f"${best_bot['current_balance']:,.2f}" if best_bot is not None else "-"
    )

    kpi4.metric(
        label="🤖 Bots Activos",
        value=active_bots_count,
        delta="En línea",
        delta_color="off"
    )

    # --- SECCIÓN GRAFICA ---
    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
    c_chart, c_details = st.columns([2, 1])

    with c_chart:
        st.subheader("📈 Curva de Rendimiento Comparada")
        if not df_trades.empty:
            # Filtrar solo entradas de venta o sync que actualizan balance
            df_balance_hist = df_trades[df_trades['action'].isin(['VENTA', 'SYNC'])].copy()
            
            # Crear gráfica multilínea
            fig = px.line(
                df_balance_hist, 
                x="timestamp", 
                y="balance", 
                color="bot_name",
                markers=True,
                color_discrete_map={
                    "BTC": "#f7931a",
                    "ETH": "#627eea",
                    "SOL": "#00ffbd"
                }
            )
            fig.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font_color='#e0e0e0',
                xaxis_title="",
                yaxis_title="Balance ($)",
                legend_title_text="",
                hovermode="x unified",
                margin=dict(l=0, r=0, t=20, b=0)
            )
            fig.update_xaxes(showgrid=False)
            fig.update_yaxes(showgrid=True, gridcolor='#2d2f36')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Esperando datos para generar gráfica...")

    with c_details:
        st.subheader("📋 Estado por Activo")
        if not df_summary.empty:
            for index, row in df_summary.iterrows():
                # Card Individual
                with st.container():
                    # Definir color según PnL
                    roi = ((row['current_balance'] - 100000) / 100000) * 100
                    color = "#00c853" if roi >= 0 else "#ff5252"
                    
                    st.markdown(f"""
                    <div style="background-color: #1a1c24; padding: 12px; border-radius: 8px; margin-bottom: 10px; border-left: 4px solid {color};">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <h3 style="margin: 0; color: white;">{row['bot_name']}</h3>
                            <span style="font-size: 18px; font-weight: bold; color: {color};">{roi:+.2f}%</span>
                        </div>
                        <div style="display: flex; justify-content: space-between; margin-top: 5px; font-size: 14px; color: #b0bec5;">
                            <span>Balance: ${row['current_balance']:,.2f}</span>
                            <span>Trades: {int(row['total_trades'])}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

    # --- TABLA DE OPERACIONES RECIENTES ---
    st.markdown("---")
    st.subheader("📜 Historial de Operaciones (Live Feed)")

    if not df_trades.empty:
        # Formatear tabla para visualización
        df_display = df_trades.copy()
        df_display['timestamp'] = df_display['timestamp'].dt.strftime('%d %b %H:%M')
        
        # Colorear PnL
        def color_pnl(val):
            if isinstance(val, float):
                color = '#00c853' if val > 0 else '#ff5252' if val < 0 else 'gray'
                return f'color: {color}; font-weight: bold;'
            return ''

        # Seleccionar columnas clave
        df_show = df_display[['timestamp', 'bot_name', 'action', 'price', 'pnl_pct', 'balance', 'win_rate']].head(15)
        df_show.columns = ['Fecha/Hora', 'Activo', 'Acción', 'Precio ($)', 'PnL %', 'Balance ($)', 'Win Rate %']

        st.dataframe(
            df_show.style.applymap(color_pnl, subset=['PnL %']),
            use_container_width=True,
            hide_index=True
        )

except Exception as e:
    st.error(f"Error cargando dashboard: {e}")
    st.code("Puede que la base de datos esté vacía o bloqueada. Intenta recargar.")

