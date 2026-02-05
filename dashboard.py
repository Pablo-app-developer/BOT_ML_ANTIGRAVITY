import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
from database import get_db_connection, get_bot_summary, get_all_trades

# Configuración de la página
st.set_page_config(
    page_title="Trading Bots Dashboard",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos personalizados
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
    .profit {
        color: #00ff00;
        font-weight: bold;
    }
    .loss {
        color: #ff4444;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown('<div class="main-header">🤖 Antigravity Trading Bots Dashboard</div>', unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.image("https://via.placeholder.com/150x150.png?text=BOT", width=150)
    st.title("⚙️ Configuración")
    
    refresh_rate = st.selectbox("Auto-refresh", ["Manual", "30s", "1min", "5min"], index=2)
    selected_bot = st.selectbox("Filtrar Bot", ["Todos", "BTC", "ETH", "SOL"])
    
    st.markdown("---")
    st.markdown("### 📊 Información")
    st.info(f"Última actualización: {datetime.now().strftime('%H:%M:%S')}")

# Auto-refresh logic
if refresh_rate != "Manual":
    refresh_seconds = {"30s": 30, "1min": 60, "5min": 300}[refresh_rate]
    st.empty()  # Placeholder for auto-refresh

# Obtener datos
try:
    summary = get_bot_summary()
    all_trades = get_all_trades(limit=500)
    
    # Convertir a DataFrame
    df_summary = pd.DataFrame(summary, columns=['bot_name', 'total_trades', 'wins', 'losses', 'avg_pnl', 'current_balance'])
    df_trades = pd.DataFrame(all_trades, columns=['id', 'bot_name', 'timestamp', 'action', 'price', 'pnl_pct', 'balance', 'win_rate', 'daily_drawdown', 'created_at'])
    
    # Métricas generales
    col1, col2, col3, col4 = st.columns(4)
    
    total_balance = df_summary['current_balance'].sum() if not df_summary.empty else 300000
    total_pnl = total_balance - 300000
    total_trades = df_summary['total_trades'].sum() if not df_summary.empty else 0
    avg_win_rate = (df_summary['wins'].sum() / df_summary['total_trades'].sum() * 100) if total_trades > 0 else 0
    
    with col1:
        st.metric("💰 Balance Total", f"${total_balance:,.2f}", f"${total_pnl:+,.2f}")
    
    with col2:
        st.metric("📈 ROI Total", f"{(total_pnl/300000*100):.2f}%", 
                 delta_color="normal" if total_pnl >= 0 else "inverse")
    
    with col3:
        st.metric("🔄 Operaciones Totales", f"{int(total_trades)}")
    
    with col4:
        st.metric("🎯 Win Rate Promedio", f"{avg_win_rate:.1f}%")
    
    st.markdown("---")
    
    # Gráfica de balance por bot
    col_left, col_right = st.columns([2, 1])
    
    with col_left:
        st.subheader("📊 Evolución del Balance por Bot")
        
        if not df_trades.empty:
            df_trades['timestamp'] = pd.to_datetime(df_trades['timestamp'])
            df_balance = df_trades[df_trades['action'] == 'VENTA'].copy()
            
            fig = go.Figure()
            
            for bot in ['BTC', 'ETH', 'SOL']:
                bot_data = df_balance[df_balance['bot_name'] == bot].sort_values('timestamp')
                if not bot_data.empty:
                    fig.add_trace(go.Scatter(
                        x=bot_data['timestamp'],
                        y=bot_data['balance'],
                        mode='lines+markers',
                        name=bot,
                        line=dict(width=2),
                        marker=dict(size=8)
                    ))
            
            fig.update_layout(
                xaxis_title="Fecha",
                yaxis_title="Balance ($)",
                hovermode='x unified',
                template='plotly_dark',
                height=400
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hay datos de operaciones aún")
    
    with col_right:
        st.subheader("🤖 Rendimiento por Bot")
        
        if not df_summary.empty:
            for _, row in df_summary.iterrows():
                bot_pnl = row['current_balance'] - 100000
                bot_roi = (bot_pnl / 100000) * 100
                
                with st.expander(f"**{row['bot_name']}** - ${row['current_balance']:,.2f}", expanded=True):
                    st.metric("ROI", f"{bot_roi:+.2f}%")
                    st.metric("Operaciones", f"{int(row['total_trades'])}")
                    st.metric("Win Rate", f"{(row['wins']/row['total_trades']*100):.1f}%" if row['total_trades'] > 0 else "0%")
                    
                    # Progress bar del balance
                    progress = (row['current_balance'] - 100000) / 1000  # Escala de -1000 a +1000
                    st.progress(max(0, min(1, (progress + 1000) / 2000)))
        else:
            st.info("Esperando datos de los bots...")
    
    st.markdown("---")
    
    # Tabla de operaciones recientes
    st.subheader("📜 Últimas Operaciones")
    
    if not df_trades.empty:
        # Filtrar por bot si se seleccionó
        if selected_bot != "Todos":
            df_display = df_trades[df_trades['bot_name'] == selected_bot].copy()
        else:
            df_display = df_trades.copy()
        
        # Formatear para mostrar
        df_display = df_display[['bot_name', 'timestamp', 'action', 'price', 'pnl_pct', 'balance', 'win_rate']].head(20)
        df_display['timestamp'] = pd.to_datetime(df_display['timestamp']).dt.strftime('%Y-%m-%d %H:%M')
        df_display['price'] = df_display['price'].apply(lambda x: f"${x:,.2f}")
        df_display['pnl_pct'] = df_display['pnl_pct'].apply(lambda x: f"{x:+.2f}%" if pd.notna(x) else "-")
        df_display['balance'] = df_display['balance'].apply(lambda x: f"${x:,.2f}")
        df_display['win_rate'] = df_display['win_rate'].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "-")
        
        df_display.columns = ['Bot', 'Fecha', 'Acción', 'Precio', 'PnL %', 'Balance', 'Win Rate']
        
        st.dataframe(df_display, use_container_width=True, hide_index=True)
    else:
        st.info("No hay operaciones registradas todavía")
    
    # Gráfica de distribución de PnL
    st.markdown("---")
    st.subheader("📊 Distribución de Ganancias/Pérdidas")
    
    if not df_trades.empty:
        df_pnl = df_trades[df_trades['pnl_pct'].notna()].copy()
        
        if not df_pnl.empty:
            fig_pnl = px.histogram(
                df_pnl,
                x='pnl_pct',
                color='bot_name',
                nbins=20,
                title="Distribución de PnL por Operación",
                labels={'pnl_pct': 'PnL (%)', 'count': 'Frecuencia'},
                template='plotly_dark'
            )
            
            st.plotly_chart(fig_pnl, use_container_width=True)

except Exception as e:
    st.error(f"Error al cargar datos: {e}")
    st.info("Asegúrate de que los bots estén guardando datos en la base de datos")

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray;'>Antigravity Trading Bots © 2026 | Powered by Streamlit</div>",
    unsafe_allow_html=True
)
