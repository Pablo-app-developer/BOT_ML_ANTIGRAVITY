# Bot SMC CCXT - Guía de Despliegue Rápido

## 🎯 Características

- ✅ **Ultra-liviano**: Imagen Docker de solo ~50MB (Alpine Linux)
- ✅ **Mínimas dependencias**: Solo CCXT, pandas, numpy
- ✅ **Multi-exchange**: Binance, Gate.io, KuCoin, Bybit, OKX
- ✅ **Lógica SMC**: Smart Money Concepts (liquidity sweeps, trend bias)
- ✅ **Risk Management**: Guardian con límites diarios
- ✅ **Optimizado para VPS**: Límites de memoria (256MB) y CPU (0.5 cores)

## 📋 Prerequisitos

1. **VPS con Docker instalado** ✅ (ya tienes Docker 29.1.3)
2. **Credenciales de exchange** (API Key, Secret, Password para Gate.io)
3. **SSH configurado** ✅

## ⚡ Despliegue en 3 Pasos

### 1️⃣ Configura tus credenciales

Edita el archivo `.env.ccxt`:

```env
EXCHANGE_NAME=gateio
API_KEY=tu_api_key_aqui
API_SECRET=tu_api_secret_aqui
API_PASSWORD=tu_password_aqui  # Solo para Gate.io, OKX
```

### 2️⃣ Despliega al VPS

**Opción A - Windows (PowerShell):**
```powershell
.\deploy_vps.ps1
```

**Opción B - Manual (cualquier sistema):**
```bash
# Conectarse al VPS
ssh root@107.174.133.202

# Crear directorio
mkdir -p /root/smc_bot

# Copiar archivos (desde tu PC local)
scp Dockerfile.ccxt root@107.174.133.202:/root/smc_bot/
scp docker-compose.ccxt.yml root@107.174.133.202:/root/smc_bot/docker-compose.yml
scp requirements_ccxt.txt root@107.174.133.202:/root/smc_bot/
scp .env.ccxt root@107.174.133.202:/root/smc_bot/.env
scp -r config root@107.174.133.202:/root/smc_bot/
scp -r src root@107.174.133.202:/root/smc_bot/

# En el VPS, construir y ejecutar
cd /root/smc_bot
docker-compose build
docker-compose up -d
```

### 3️⃣ Monitorea el bot

```bash
# Ver logs en tiempo real
ssh root@107.174.133.202 'docker logs -f smc_trading_bot'

# Ver estado
ssh root@107.174.133.202 'docker ps'

# Ver uso de recursos
ssh root@107.174.133.202 'docker stats smc_trading_bot'
```

## 🎛️ Configuración

### Cambiar símbolos a tradear

Edita `config/settings_ccxt.py`:

```python
SYMBOLS = [
    "BTC/USDT",
    "ETH/USDT",
    "SOL/USDT"
]
```

### Ajustar riesgo

```python
RISK_PER_TRADE = 0.01      # 1% por trade
DAILY_LOSS_LIMIT = 0.03    # 3% pérdida máxima diaria
RISK_REWARD_RATIO = 3.0    # RR 1:3
```

### Cambiar timeframes

```python
TIMEFRAME_HTF = "4h"   # Trend: 1h, 4h, 1d
TIMEFRAME_LTF = "15m"  # Entry: 5m, 15m, 1h
```

## 📊 Comandos Útiles

```bash
# Detener bot
ssh root@107.174.133.202 'cd /root/smc_bot && docker-compose down'

# Reiniciar bot
ssh root@107.174.133.202 'cd /root/smc_bot && docker-compose restart'

# Ver journal de trades
ssh root@107.174.133.202 'cat /root/smc_bot/bot_journal.csv'

# Actualizar configuración
# 1. Edita .env.ccxt localmente
# 2. Copia: scp .env.ccxt root@107.174.133.202:/root/smc_bot/.env
# 3. Reinicia: ssh root@107.174.133.202 'cd /root/smc_bot && docker-compose restart'

# Limpiar espacio en disco
ssh root@107.174.133.202 'docker system prune -f'
```

## 🔒 Seguridad

- ✅ **Nunca** subas tus credenciales a Git
- ✅ Usa permisos de API limitados (solo trading, sin withdrawals)
- ✅ Habilita IP whitelist en tu exchange
- ✅ Empieza con pequeñas cantidades para probar

## 📈 Lógica de Trading

El bot implementa **Smart Money Concepts**:

1. **Trend Bias** (H4): EMA 50/200 para determinar dirección
2. **Liquidity Levels** (M15): Detecta swing highs/lows
3. **Entry Signal**: 
   - BUY: Price sweeps low liquidity y reclaims
   - SELL: Price sweeps high liquidity y reclaims down
4. **Risk Management**: Stop-loss basado en liquidity, TP con RR 1:3

## ⚠️ IMPORTANTE

- **Paper trading primero**: Prueba con exchange testnet o pequeñas cantidades
- **Monitorea los primeros días**: Revisa logs y ajusta si es necesario
- **VPS ligero**: El bot usa solo ~100-150MB RAM gracias a Alpine Linux
- **Rate limits**: CCXT maneja automáticamente (enableRateLimit=True)

## 🆘 Solución de Problemas

**Error: "API key invalid"**
- Verifica credenciales en `.env.ccxt`
- Asegúrate que el API key tiene permisos de trading

**Error: "Insufficient balance"**
- Verifica que tienes USDT en tu cuenta spot
- Reduce `RISK_PER_TRADE` para posiciones más pequeñas

**Bot no hace trades**
- Verifica que estás en timeframe y símbolos con liquidez
- Revisa logs: `docker logs -f smc_trading_bot`
- La estrategia espera setups específicos de SMC

**Poco espacio en VPS**
- Limpia Docker: `docker system prune -af`
- El bot usa solo ~50MB de imagen + ~100MB RAM

## 📞 Soporte

Ver logs completos:
```bash
ssh root@107.174.133.202 'docker logs --tail 500 smc_trading_bot'
```
