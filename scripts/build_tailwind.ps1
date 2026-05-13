# build_tailwind.ps1 - Compila Tailwind CSS
param(
    [switch]$Watch  # Modo watch (recompila automáticamente)
)

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Tailwind CSS Builder                " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

if (-not (Test-Path "package.json")) {
    Write-Host "ERROR: package.json no encontrado." -ForegroundColor Red
    Write-Host "Asegúrate de estar en el directorio raíz del proyecto." -ForegroundColor Yellow
    exit 1
}

# Instalar dependencias si es necesario
if (-not (Test-Path "node_modules")) {
    Write-Host "Instalando dependencias npm..." -ForegroundColor Yellow
    npm install
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Error al instalar dependencias npm" -ForegroundColor Red
        exit 1
    }
}

if ($Watch) {
    Write-Host "`nIniciando modo watch (Ctrl+C para salir)..." -ForegroundColor Cyan
    Write-Host "Recompilando automáticamente cuando cambien los archivos..." -ForegroundColor Gray
    npm run watch:css
} else {
    Write-Host "Compilando CSS de producción..." -ForegroundColor Yellow
    npm run build:css
    if ($LASTEXITCODE -eq 0) {
        Write-Host "`n¡Compilación completada!" -ForegroundColor Green
        Write-Host "CSS generado en: .\app\static\css\output.css" -ForegroundColor Cyan
    } else {
        Write-Host "`nError en la compilación" -ForegroundColor Red
        exit 1
    }
}
