# BOT_ML_ANTIGRAVITY

## 📈 Descripción General
Un bot de trading multi-activo basado en **Aprendizaje por Refuerzo (Reinforcement Learning)** utilizando **Stable-Baselines3 PPO**. Soporta Bitcoin (BTC), Solana (SOL) y Ethereum (ETH) con parámetros de entorno específicos por activo y controles de riesgo de grado institucional (Filtro de tendencia EMA-200, Stop Loss, Trailing Stop, Cooldown y penalizaciones por volatilidad).

## 🚀 Características
- **Configuración modular de activos**: `train_production.py` selecciona automáticamente los hiperparámetros y la configuración del entorno para cada criptomoneda.
- **Control de riesgo institucional**: Incluye muros de tendencia, stops dinámicos y aversión al riesgo adaptativa.
- **Optimización de Hiperparámetros**: Utiliza Optuna para encontrar la configuración "Diamante", guardada en `best_hyperparams_*.json`.
- **Reportes Completos**: `generate_report.py` genera `ESTADO_DE_LAS_PRUEBAS.md` con tablas de rendimiento y curvas de equidad.
- **Evolución Versionada**: `HISTORIAL_DE_FASES.md` documenta cada cambio estratégico paso a paso.
- **Soporte Docker**: Despliegue agnóstico a la plataforma (Windows/Linux/Mac) con `docker-compose`.

## 📦 Instalación

### Requisitos Previos
- Python 3.10+
- Git

```bash
# 1. Clonar el repositorio
git clone https://github.com/Pablo-app-developer/BOT_ML_ANTIGRAVITY.git
cd BOT_ML_ANTIGRAVITY

# 2. Crear un entorno virtual (Recomendado)
python -m venv .venv

# Activar en Windows:
.venv\Scripts\activate
# Activar en Linux/Mac:
# source .venv/bin/activate

# 3. Instalar dependencias
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Para desarrollo y tests
```

> **Nota:** El repositorio incluye un `.gitignore` que excluye archivos de modelos pesados (.zip) y credenciales sensibles para seguridad.

## 🛠️ Manual de Uso (Paso a Paso)

### 1️⃣ Entrenar un Modelo (Modo Producción)
El script es modular y carga la configuración desde `config/assets.py`. Si ya existe un modelo previo, hará **Transfer Learning** para mejorarlo.

**Comandos:**
```bash
# Entrenar Bitcoin (Estrategia: Estándar de Oro - Conservadora)
python train_production.py BTC

# Entrenar Solana (Estrategia: Élite Híbrida - Agresiva >5%)
python train_production.py SOL

# Entrenar Ethereum (Estrategia: Élite Rescue - Equilibrada)
# Puedes especificar pasos personalizados si deseas un entrenamiento más largo
python train_production.py ETH --steps 200000
```
**¿Qué hace el script?**
1. Carga los datos históricos (`datos_<activo>_15m_binance.csv`).
2. Aplica los parámetros de riesgo específicos del activo.
3. Carga el mejor modelo base disponible (o empieza de cero si no hay ninguno).
4. Entrena durante los pasos configurados (150k por defecto).
5. Guarda el modelo final en `models/PRODUCTION/<ACTIVO>/`.

---

### 2️⃣ Backtesting (Prueba con Datos Históricos)
Una vez entrenado el modelo, debes validar su rendimiento simulando operaciones pasadas. El script calcula métricas profesionales: Retorno Total, **Sharpe Ratio**, **Sortino Ratio**, **Calmar Ratio** y **Duración del Drawdown**.

**Comandos:**
```bash
# Probar Bitcoin
python backtest.py BTC

# Probar Solana
python backtest.py SOL

# Probar Ethereum
python backtest.py ETH
```
Esto generará:
- Un gráfico de la curva de equidad en `reports/backtest_<activo>_latest.png`.
- Un resumen de métricas en la consola.
- Datos crudos en `reports/results_summary.json`.

---

### 3️⃣ Generar Informe Ejecutivo
Crea un resumen visual en Markdown con todos los resultados actuales.

```bash
python generate_report.py
```
El archivo generado es `ESTADO_DE_LAS_PRUEBAS.md`. Puedes abrirlo para ver una tabla comparativa y los gráficos.

---

### 4️⃣ Optimización Avanzada (Opcional)
Si quieres encontrar una mejor configuración de IA para ETH (o cualquier activo), usa el script de optimización evolutiva.

```bash
python optimize_eth.py
```
Esto ejecutará múltiples pruebas con **Optuna** y guardará los mejores parámetros en `best_hyperparams_eth.json`.

---

## 🐳 Despliegue en VPS (Guía Avanzada)

### 1. Requisitos del Servidor
- **Mínimo Absoluto**: 2 vCPU, 4GB RAM, 30GB Disco.
- **Recomendado**: 50GB+ Disco para evitar problemas de espacio con Docker.

### 2. Preparación (Optimización de Recursos)
Si tienes un VPS pequeño (<4GB RAM), activa Swap antes de nada:
```bash
# Crear 2GB de memoria virtual
fallocate -l 2G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
```

### 3. Instalación "Ligera" (Para servidores pequeños)
Para ahorrar 2GB de espacio, usamos la versión CPU-Only de PyTorch.

1. Editar `Dockerfile`:
   Cambiar `COPY requirements.txt .` por `COPY requirements-server.txt requirements.txt`.
2. O instalar manualmente en el Dockerfile:
   ```dockerfile
   RUN pip install --no-cache-dir -r requirements-server.txt
   ```

### 4. Lanzar en Producción (Live Trading)
El bot descargará datos de Yahoo Finance para generar señales (evitando bloqueos de IP).

```bash
# Modo Silencioso (Segundo plano)
docker compose run -d --name trader_eth bot python run_live_trader.py ETH

# Ver logs en vivo
docker logs -f trader_eth
```

## 🚨 Solución de Problemas (Troubleshooting)

### "No space left on device"
Docker consume mucho espacio al construir.
1. **Limpiar todo**: `docker system prune -a --volumes -f`
2. **Construir sin caché**: `docker compose build --no-cache`

### "Service unavailable / Geo-blocking"
Si tu VPS está en EE. UU., Binance bloqueará la conexión.
- **Solución**: El script `run_live_trader.py` ahora usa `yfinance` automáticamente para evitar este problema.

### "Killed" o "Exited (137)"
El bot se quedó sin memoria RAM.
- **Solución**: Aumenta el Swap o corre solo un bot a la vez.

## � Monitoreo y Vigilancia

Tienes tres niveles para controlar tu ejército de bots:

### 1. Nivel Táctico (En Vivo)
Para ver qué decisión está tomando el bot en este preciso instante (cada minuto).
```bash
# Ver las últimas 50 líneas y seguir en vivo
docker logs -f --tail 50 trader_eth
```
*Salida esperada:* `🟢 [COMPRA] SEÑAL DETECTADA` o `💤 Hold`.

### 2. Nivel Estratégico (Entrenamiento)
Para vigilar la evolución de la inteligencia del bot (Gráficas de retorno).
- Accede desde tu navegador: `http://<TU_IP_VPS>:6006`
- Fíjate en **`rollout/ep_rew_mean`** (Debe ser ascendente 📈).

### 3. Nivel Forense (Auditoría)
Para descargar el historial completo de operaciones a un archivo y analizarlo.
```bash
# Extraer el log interno del contenedor
docker cp trader_eth:/app/live_trader.log ./auditoria_operaciones.txt

# Leerlo
cat auditoria_operaciones.txt
```

## �📊 Resultados Actuales (Enero 2026)
| Activo | Retorno | Sharpe | Max Drawdown | Trades | Balance Final |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **BTC** | **+3.11%** | **2.47** | **0.47%** | 212 | $10,310.51 |
| **SOL** | **+8.37%** | **1.06** | **3.68%** | 202 | $10,837.02 |
| **ETH** | **+5.04%** | **1.40** | **1.90%** | 748 | $10,503.80 |

## 🧹 Seguridad y Limpieza
- Todas las claves y archivos `.env` están ignorados por git.
- Los modelos pesados no se suben al repositorio para mantenerlo ligero.

## 📜 Licencia
Este proyecto está bajo la Licencia **MIT**. Ver el archivo `LICENSE` para más detalles.

---
*Generado por Antigravity Agent - Tu socio de desarrollo IA.*
