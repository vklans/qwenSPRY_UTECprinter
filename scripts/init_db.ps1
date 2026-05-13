# init_db.ps1 - Inicializa base de datos y crea primer usuario administrador
param(
    [string]$DataPath = ".\data",
    [string]$DbName = "printwatch.db"
)

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  PrintWatch Pro - Inicialización DB  " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Crear directorio data si no existe
if (-not (Test-Path $DataPath)) {
    Write-Host "Creando directorio $DataPath..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $DataPath | Out-Null
}

$dbPath = Join-Path $DataPath $DbName

# Si ya existe, preguntar si sobrescribir
if (Test-Path $dbPath) {
    $overwrite = Read-Host "La base de datos ya existe. ¿Desea sobrescribirla? (s/n)"
    if ($overwrite -ne 's' -and $overwrite -ne 'S') {
        Write-Host "Operación cancelada." -ForegroundColor Red
        exit 0
    }
    Remove-Item $dbPath -Force
    Write-Host "Base de datos anterior eliminada." -ForegroundColor Green
}

# Eliminar archivos WAL si existen
$walFiles = @("$dbPath-wal", "$dbPath-shm")
foreach ($file in $walFiles) {
    if (Test-Path $file) {
        Remove-Item $file -Force
    }
}

Write-Host "`nInicializando base de datos..." -ForegroundColor Yellow

# Ejecutar script Python de inicialización
$pythonScript = @"
import sqlite3
import os
from pathlib import Path
import sys

db_path = '$dbPath'
project_root = Path(__file__).parent.parent if '__file__' in dir() else Path('.')
migrations_dir = project_root / 'app' / 'database' / 'migrations'

if not migrations_dir.exists():
    migrations_dir = Path('app/database/migrations')

print(f'Buscando migraciones en: {migrations_dir}')

if not migrations_dir.exists():
    print('ERROR: Directorio de migraciones no encontrado')
    sys.exit(1)

conn = sqlite3.connect(db_path)
conn.execute('PRAGMA journal_mode=WAL')
conn.execute('PRAGMA synchronous=NORMAL')
conn.execute('PRAGMA foreign_keys=ON')

print('Configuración WAL aplicada correctamente')

# Ejecutar migraciones en orden
migration_files = sorted(migrations_dir.glob('*.sql'))
if not migration_files:
    print('ERROR: No se encontraron archivos de migración')
    sys.exit(1)

for migration in migration_files:
    print(f'Ejecutando {migration.name}...')
    with open(migration, 'r', encoding='utf-8') as f:
        sql = f.read()
    try:
        conn.executescript(sql)
    except Exception as e:
        print(f'Error en {migration.name}: {e}')
        sys.exit(1)

conn.commit()
conn.close()
print('Base de datos inicializada correctamente.')
"@

python -c $pythonScript

if ($LASTEXITCODE -ne 0) {
    Write-Host "Error al inicializar la base de datos." -ForegroundColor Red
    exit 1
}

Write-Host "`nBase de datos creada en: $dbPath" -ForegroundColor Green

# Crear primer usuario superadmin
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  Creación de Usuario Administrador   " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$username = Read-Host "Nombre de usuario (admin)"
if (-not $username) { $username = "admin" }

$fullName = Read-Host "Nombre completo"
while (-not $fullName) {
    Write-Host "El nombre completo es obligatorio" -ForegroundColor Red
    $fullName = Read-Host "Nombre completo"
}

$email = Read-Host "Email (opcional)"
$password = Read-Host "Contraseña (mínimo 8 caracteres)" -AsSecureString
while ([System.Runtime.InteropServices.Marshal]::PtrToStringAuto(
    [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($password)).Length -lt 8) {
    Write-Host "La contraseña debe tener al menos 8 caracteres" -ForegroundColor Red
    $password = Read-Host "Contraseña (mínimo 8 caracteres)" -AsSecureString
}

$passwordConfirm = Read-Host "Confirmar contraseña" -AsSecureString

# Verificar que las contraseñas coinciden
$bstr1 = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($password)
$bstr2 = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($passwordConfirm)
$pass1 = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr1)
$pass2 = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr2)

if ($pass1 -ne $pass2) {
    Write-Host "Las contraseñas no coinciden." -ForegroundColor Red
    exit 1
}

# Hash de contraseña con bcrypt
Write-Host "`nCreando usuario..." -ForegroundColor Yellow

$createUserScript = @"
import sqlite3
import bcrypt
import sys

db_path = '$dbPath'
username = '$username'
full_name = '$fullName'
email = '$email' if '$email' else None
password = '$pass1'

try:
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=12)).decode('utf-8')
except Exception as e:
    print(f'Error generando hash: {e}')
    sys.exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    cursor.execute('''
        INSERT INTO users (username, password_hash, full_name, role, email, is_active)
        VALUES (?, ?, ?, 'superadmin', ?, 1)
    ''', (username, password_hash, full_name, email, email))
    conn.commit()
    print('Usuario creado exitosamente.')
except sqlite3.IntegrityError as e:
    print(f'Error: El usuario ya existe. {e}')
    sys.exit(1)
except Exception as e:
    print(f'Error inesperado: {e}')
    sys.exit(1)
finally:
    conn.close()
"@

python -c $createUserScript

if ($LASTEXITCODE -ne 0) {
    Write-Host "Error al crear el usuario." -ForegroundColor Red
    exit 1
}

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "  ¡Inicialización completada!         " -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host "`nResumen:" -ForegroundColor Cyan
Write-Host "  • Base de datos: $dbPath" -ForegroundColor White
Write-Host "  • Usuario: $username" -ForegroundColor White
Write-Host "  • Rol: superadmin" -ForegroundColor White
Write-Host "`nAhora puedes ejecutar:" -ForegroundColor Cyan
Write-Host "  .\scripts\run_laptop.ps1  (para desarrollo)" -ForegroundColor White
Write-Host "  .\scripts\run_server.ps1  (para producción)" -ForegroundColor White
