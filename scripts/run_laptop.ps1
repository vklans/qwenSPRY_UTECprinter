# run_laptop.ps1 - Ejecuta PrintWatch Pro en modo desarrollo (laptop)
param(
    [string]$HostAddress = "127.0.0.1",
    [int]$Port = 8000,
    [switch]$Debug,
    [switch]$CollectorsOnly,
    [switch]$DashboardOnly
)

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  PrintWatch Pro - Modo Laptop        " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Verificar que la BD existe
$dbPath = ".\data\printwatch.db"
if (-not (Test-Path $dbPath)) {
    Write-Host "ERROR: Base de datos no encontrada en $dbPath" -ForegroundColor Red
    Write-Host "Ejecuta primero: .\scripts\init_db.ps1" -ForegroundColor Yellow
    exit 1
}

# Verificar requirements
Write-Host "Verificando dependencias Python..." -ForegroundColor Yellow
$requirements = @("flask", "bcrypt", "apscheduler", "pysnmp")
$missing = @()

foreach ($req in $requirements) {
    python -c "import $req" 2>$null
    if ($LASTEXITCODE -ne 0) {
        $missing += $req
    }
}

if ($missing.Count -gt 0) {
    Write-Host "Instalando dependencias faltantes: $($missing -join ', ')" -ForegroundColor Yellow
    pip install -r requirements.txt --quiet
}

# Configurar variables de entorno
$env:PRINTWATCH_ENV = "development"
$env:PRINTWATCH_SNMP_SOURCE = "api"  # Laptop consulta al servidor via API
$env:PRINTWATCH_API_URL = "http://10.100.120.100:5000"  # IP del servidor SNMP (configurar según red)
$env:PRINTWATCH_DB_PATH = $dbPath
$env:FLASK_DEBUG = "1" if ($Debug) else "0"

# Compilar Tailwind si es necesario
if (-not (Test-Path ".\app\static\css\output.css")) {
    Write-Host "Compilando Tailwind CSS..." -ForegroundColor Yellow
    if (Test-Path "package.json") {
        npm install --silent
        npm run build:css --silent
        if ($LASTEXITCODE -eq 0) {
            Write-Host "Tailwind CSS compilado correctamente" -ForegroundColor Green
        } else {
            Write-Host "WARNING: Error al compilar Tailwind. Usando CSS por defecto." -ForegroundColor Yellow
        }
    } else {
        Write-Host "WARNING: package.json no encontrado. Usando CSS por defecto." -ForegroundColor Yellow
    }
}

# Determinar modo de ejecución
$mode = ""
if ($CollectorsOnly) {
    $mode = "Solo Colectores SNMP"
} elseif ($DashboardOnly) {
    $mode = "Solo Dashboard (sin colectores)"
} else {
    $mode = "Completo (Dashboard + Colectores)"
}

Write-Host "`nModo: $mode" -ForegroundColor Cyan
Write-Host "Iniciando aplicación en http://$HostAddress`: $Port" -ForegroundColor Green
Write-Host "Presiona Ctrl+C para detener`n" -ForegroundColor Gray

# Construir y ejecutar comando Python
if ($CollectorsOnly) {
    python -c @"
from app import create_app
from app.scheduler import start_collectors_only

app = create_app()
with app.app_context():
    start_collectors_only()
"@
} elseif ($DashboardOnly) {
    python -c @"
from app import create_app

app = create_app(enable_collectors=False)
app.run(host='$HostAddress', port=$Port, debug=True, use_reloader=False)
"@
} else {
    python -c @"
from app import create_app

app = create_app(enable_collectors=True)
app.run(host='$HostAddress', port=$Port, debug=True, use_reloader=False)
"@
}

if ($LASTEXITCODE -ne 0) {
    Write-Host "`nError al ejecutar la aplicación." -ForegroundColor Red
    exit 1
}
