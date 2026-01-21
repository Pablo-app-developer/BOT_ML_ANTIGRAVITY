#!/bin/bash

# Script de despliegue ultra-rápido para VPS
set -e

echo "🚀 Desplegando bot al VPS..."

# Variables
VPS_IP="107.174.133.202"
VPS_USER="root"
REMOTE_DIR="/root/smc_bot"

# Crear directorio remoto
echo "📁 Creando directorio en VPS..."
ssh ${VPS_USER}@${VPS_IP} "mkdir -p ${REMOTE_DIR}/config ${REMOTE_DIR}/src"

# Copiar solo archivos esenciales
echo "📦 Copiando archivos..."
scp Dockerfile.ccxt ${VPS_USER}@${VPS_IP}:${REMOTE_DIR}/
scp docker-compose.ccxt.yml ${VPS_USER}@${VPS_IP}:${REMOTE_DIR}/docker-compose.yml
scp requirements_ccxt.txt ${VPS_USER}@${VPS_IP}:${REMOTE_DIR}/
scp .env.ccxt ${VPS_USER}@${VPS_IP}:${REMOTE_DIR}/.env
scp config/settings_ccxt.py ${VPS_USER}@${VPS_IP}:${REMOTE_DIR}/config/
scp src/main_ccxt.py ${VPS_USER}@${VPS_IP}:${REMOTE_DIR}/src/

# Crear __init__.py
ssh ${VPS_USER}@${VPS_IP} "touch ${REMOTE_DIR}/config/__init__.py"

# Construir y ejecutar
echo "🐳 Construyendo imagen Docker..."
ssh ${VPS_USER}@${VPS_IP} "cd ${REMOTE_DIR} && docker-compose down 2>/dev/null || true"
ssh ${VPS_USER}@${VPS_IP} "cd ${REMOTE_DIR} && docker-compose build --no-cache"

echo "▶️  Iniciando bot..."
ssh ${VPS_USER}@${VPS_IP} "cd ${REMOTE_DIR} && docker-compose up -d"

echo ""
echo "✅ ¡Bot desplegado exitosamente!"
echo ""
echo "📊 Ver logs en tiempo real:"
echo "   ssh ${VPS_USER}@${VPS_IP} 'docker logs -f smc_trading_bot'"
echo ""
echo "🛑 Detener bot:"
echo "   ssh ${VPS_USER}@${VPS_IP} 'cd ${REMOTE_DIR} && docker-compose down'"
echo ""
