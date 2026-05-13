"""
Sistema de migraciones de base de datos
"""

import sqlite3
from pathlib import Path
from typing import List


MIGRATIONS_DIR = Path(__file__).parent / 'migrations'


def get_applied_migrations(conn: sqlite3.Connection) -> List[str]:
    """Obtener lista de migraciones ya aplicadas"""
    
    # Verificar si la tabla existe
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
    )
    if not cursor.fetchone():
        return []
    
    cursor = conn.execute("SELECT version FROM schema_migrations ORDER BY version")
    return [row[0] for row in cursor.fetchall()]


def apply_migration(conn: sqlite3.Connection, version: str, sql: str):
    """Aplicar una migración específica"""
    
    conn.executescript(sql)
    conn.execute("INSERT INTO schema_migrations (version) VALUES (?)", (version,))
    conn.commit()


def ensure_migrated(db_path: str):
    """Asegurar que todas las migraciones estén aplicadas"""
    
    conn = sqlite3.connect(db_path)
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA foreign_keys=ON')
    
    try:
        applied = get_applied_migrations(conn)
        
        # Obtener lista de archivos de migración ordenados
        migration_files = sorted(MIGRATIONS_DIR.glob('*.sql'))
        
        for migration_file in migration_files:
            version = migration_file.stem.split('_')[0]  # ej: '001' de '001_core.sql'
            
            if version not in applied:
                print(f"Aplicando migración {version} ({migration_file.name})...")
                
                with open(migration_file, 'r', encoding='utf-8') as f:
                    sql = f.read()
                
                apply_migration(conn, version, sql)
                print(f"Migración {version} aplicada exitosamente.")
        
        if not migration_files:
            print("No se encontraron migraciones en el directorio.")
        elif len(applied) == len(migration_files):
            print("Base de datos actualizada. Todas las migraciones aplicadas.")
        
    finally:
        conn.close()


def run_migrations_interactive(db_path: str):
    """Ejecutar migraciones con output detallado (para init_db.ps1)"""
    
    print(f"Verificando migraciones para: {db_path}")
    print("=" * 50)
    
    conn = sqlite3.connect(db_path)
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA foreign_keys=ON')
    
    try:
        applied = get_applied_migrations(conn)
        migration_files = sorted(MIGRATIONS_DIR.glob('*.sql'))
        
        if not migration_files:
            print("ERROR: No se encontraron archivos de migración.")
            return False
        
        pending = [f for f in migration_files 
                   if f.stem.split('_')[0] not in applied]
        
        if not pending:
            print("✓ La base de datos está actualizada.")
            return True
        
        print(f"\nMigraciones pendientes: {len(pending)}")
        
        for migration_file in pending:
            version = migration_file.stem.split('_')[0]
            print(f"\n→ Aplicando {version} ({migration_file.name})...")
            
            try:
                with open(migration_file, 'r', encoding='utf-8') as f:
                    sql = f.read()
                
                apply_migration(conn, version, sql)
                print(f"  ✓ Migración {version} completada.")
                
            except Exception as e:
                print(f"  ✗ Error en migración {version}: {e}")
                return False
        
        print("\n" + "=" * 50)
        print("✓ Todas las migraciones aplicadas exitosamente.")
        return True
        
    except Exception as e:
        print(f"✗ Error general: {e}")
        return False
        
    finally:
        conn.close()
