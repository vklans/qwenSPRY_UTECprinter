"""
Módulo de base de datos - Conexión y utilidades
"""

import sqlite3
from pathlib import Path
from typing import Optional


def get_connection(db_path: str) -> sqlite3.Connection:
    """Crear conexión a SQLite con configuración optimizada"""
    
    conn = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row  # Permite acceso por nombre de columna
    
    # Configurar para rendimiento y concurrencia
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA synchronous=NORMAL')
    conn.execute('PRAGMA foreign_keys=ON')
    conn.execute('PRAGMA cache_size=-64000')  # 64MB cache
    
    return conn


def get_db():
    """Obtener conexión desde el contexto de Flask"""
    from flask import g
    
    if 'db' not in g or g.db is None:
        db_path = g.get('db_path', './data/printwatch.db')
        g.db = get_connection(db_path)
    
    return g.db


def query_db(query, args=(), one=False):
    """Ejecutar query y retornar resultados"""
    from flask import current_app
    
    db_path = current_app.config['DATABASE_PATH']
    conn = get_connection(db_path)
    
    try:
        cur = conn.execute(query, args)
        rv = cur.fetchall()
        cur.close()
        return (rv[0] if rv else None) if one else rv
    finally:
        conn.close()


def execute_db(query, args=()):
    """Ejecutar query que modifica datos (INSERT, UPDATE, DELETE)"""
    from flask import current_app
    
    db_path = current_app.config['DATABASE_PATH']
    conn = get_connection(db_path)
    
    try:
        cur = conn.execute(query, args)
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def init_db():
    """Inicializar base de datos con migraciones"""
    from app.database.migrations import ensure_migrated
    from flask import current_app
    
    db_path = current_app.config['DATABASE_PATH']
    ensure_migrated(db_path)
