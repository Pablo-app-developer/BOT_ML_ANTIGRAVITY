# Script de despliegue para Windows PowerShell
# Despliegue ultra-rápido al VPS

$VPS_IP = "107.174.133.202"
$VPS_USER = "root"
$VPS_PASS = "8NI8OmrT2rCnz5U6k0"
$REMOTE_DIR = "/root/smc_fusion_ccxt"

Write-Host "🚀 Desplegando SMC FUSION CCXT al VPS..." -ForegroundColor Green

# Función para ejecutar comandos SSH
function SSH-Exec {
    param([string]$Command)
    echo $VPS_PASS | plink -batch -pw $VPS_PASS ${VPS_USER}@${VPS_IP} $Command
}

function SCP-Copy {
    param([string]$LocalFile, [string]$RemotePath)
    echo $VPS_PASS | pscp -batch -pw $VPS_PASS $LocalFile "${VPS_USER}@${VPS_IP}:${RemotePath}"
}

Write-Host "📁 Preparando directorios en VPS..." -ForegroundColor Cyan

# Limpiar y crear directorios
ssh root@${VPS_IP} "rm -rf ${REMOTE_DIR} && mkdir -p ${REMOTE_DIR}/config ${REMOTE_DIR}/src"

Write-Host "📦 Copiando archivos esenciales..." -ForegroundColor Cyan

# Copiar archivos uno por uno usando SCP
scp Dockerfile.ccxt "root@${VPS_IP}:${REMOTE_DIR}/"
scp docker-compose.ccxt.yml "root@${VPS_IP}:${REMOTE_DIR}/docker-compose.yml"
scp requirements_ccxt.txt "root@${VPS_IP}:${REMOTE_DIR}/"
scp .env.ccxt "root@${VPS_IP}:${REMOTE_DIR}/.env"
scp config/settings_ccxt.py "root@${VPS_IP}:${REMOTE_DIR}/config/"
scp src/main_ccxt.py "root@${VPS_IP}:${REMOTE_DIR}/src/"

# Crear __init__.py
ssh root@${VPS_IP} "echo '# Config module' > ${REMOTE_DIR}/config/__init__.py"

Write-Host "🐳 Construyendo imagen Docker (ultra-liviana)..." -ForegroundColor Yellow

# Detener contenedor anterior si existe
ssh root@${VPS_IP} "cd ${REMOTE_DIR} && docker-compose down 2>/dev/null || true"

# Limpiar imágenes antiguas para ahorrar espacio
ssh root@${VPS_IP} "docker system prune -f"

# Construir imagen
ssh root@${VPS_IP} "cd ${REMOTE_DIR} && docker-compose build --no-cache"

Write-Host "▶️  Iniciando bot..." -ForegroundColor Green
ssh root@${VPS_IP} "cd ${REMOTE_DIR} && docker-compose up -d"

Write-Host ""
Write-Host "✅ ¡Bot desplegado exitosamente!" -ForegroundColor Green
Write-Host ""
Write-Host "📊 Comandos útiles:" -ForegroundColor Cyan
Write-Host "   Ver logs:  ssh root@${VPS_IP} 'docker logs -f smc_fusion_ccxt_bot'" -ForegroundColor White
Write-Host "   Detener:   ssh root@${VPS_IP} 'cd ${REMOTE_DIR} && docker-compose down'" -ForegroundColor White
Write-Host "   Reiniciar: ssh root@${VPS_IP} 'cd ${REMOTE_DIR} && docker-compose restart'" -ForegroundColor White
Write-Host ""
Write-Host "💡 IMPORTANTE: Edita el archivo .env.ccxt con tus credenciales de API antes de desplegar!" -ForegroundColor Yellow
Write-Host ""
