# run_server.ps1 - Ejecuta PrintWatch Pro en modo servidor (producción)
param(
    [string]$HostAddress = "0.0.0.0",
    [int]$Port = 5000,
    [switch]$CollectorsOnly
)

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  PrintWatch Pro - Modo Servidor      " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Verificar que la BD existe
$dbPath = ".\data\printwatch.db"
if (-not (Test-Path $dbPath)) {
    Write-Host "ERROR: Base de datos no encontrada en $dbPath" -ForegroundColor Red
    Write-Host "Ejecuta primero: .\scripts\init_db.ps1" -ForegroundColor Yellow
    exit 1
}

# Verificar requirements críticos
Write-Host "Verificando dependencias Python..." -ForegroundColor Yellow
$critical_requirements = @("flask", "bcrypt", "apscheduler", "pysnmp")
$missing = @()

foreach ($req in $critical_requirements) {
    python -c "import $req" 2>$null
    if ($LASTEXITCODE -ne 0) {
        $missing += $req
    }
}

if ($missing.Count -gt 0) {
    Write-Host "Instalando dependencias críticas: $($missing -join ', ')" -ForegroundColor Yellow
    pip install -r requirements.txt --quiet
}

# Verificar pysnmp específicamente
Write-Host "Verificando módulo SNMP..." -ForegroundColor Yellow
python -c "from pysnmp.hlapi import SnmpEngine, UdpTransportTarget" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: pysnmp no está instalado correctamente." -ForegroundColor Red
    Write-Host "Ejecuta: pip install pysnmp" -ForegroundColor Yellow
    exit 1
}
Write-Host "SNMP verificado correctamente" -ForegroundColor Green

# Configurar variables de entorno para producción
$env:PRINTWATCH_ENV = "production"
$env:PRINTWATCH_SNMP_SOURCE = "local_snmp"  # Servidor hace SNMP directo
$env:PRINTWATCH_DB_PATH = $dbPath
$env:FLASK_DEBUG = "0"

# Compilar Tailwind (solo si hay cambios)
if (Test-Path "package.json") {
    Write-Host "Verificando Tailwind CSS..." -ForegroundColor Yellow
    npm run build:css --silent 2>$null
}

# Instalar waitress para producción si es necesario
$waitress_installed = $false
python -c "import waitress" 2>$null
if ($LASTEXITCODE -eq 0) {
    $waitress_installed = $true
} else {
    Write-Host "Instalando waitress (servidor WSGI producción)..." -ForegroundColor Yellow
    pip install waitress --quiet
    $waitress_installed = $true
}

# Determinar modo de ejecución
if ($CollectorsOnly) {
    Write-Host "`nModo: Solo Colectores SNMP (sin servidor web)" -ForegroundColor Cyan
    
    python -c @"
from app import create_app
from app.scheduler import start_collectors_only

app = create_app()
with app.app_context():
    start_collectors_only()
"@
} else {
    Write-Host "`nModo: Servidor Completo (Web + Colectores)" -ForegroundColor Cyan
    Write-Host "Escuchando en http://$HostAddress`: $Port" -ForegroundColor Green
    Write-Host "Usando Waitress WSGI Server (producción)" -ForegroundColor Cyan
    
    python -c @"
from app import create_app
from waitress import serve

app = create_app(enable_collectors=True)

print('Iniciando servidor de producción con Waitress...')
print(f'Bind: $HostAddress:$Port')
print(f'Threads: 4')
print(f'Channel timeout: 120s')
print('')
serve(app, host='$HostAddress', port=$Port, threads=4, channel_timeout=120)
"@
}

if ($LASTEXITCODE -ne 0) {
    Write-Host "`nError al iniciar el servidor." -ForegroundColor Red
    Write-Host "Revisa los logs en: .\logs\errors.log" -ForegroundColor Yellow
    exit 1
}
