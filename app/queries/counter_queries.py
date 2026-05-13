"""
Consultas SQL para el módulo de contómetros
Todas las consultas usan parámetros posicionales (?) para prevenir inyección SQL
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta


def get_counter_readings(
    db, 
    printer_id: Optional[int] = None, 
    location_id: Optional[int] = None,
    start_date: Optional[str] = None, 
    end_date: Optional[str] = None,
    limit: int = 1000
) -> List[Dict[str, Any]]:
    """Obtener lecturas de contómetros con filtros"""
    
    query = """
        SELECT 
            cr.id,
            cr.printer_id,
            p.printer_code,
            p.name as printer_name,
            l.name as location_name,
            cr.captured_at,
            cr.total_impressions,
            cr.bn_impressions,
            cr.color_impressions
        FROM counter_readings cr
        JOIN printers p ON cr.printer_id = p.id
        LEFT JOIN locations l ON p.location_id = l.id
        WHERE 1=1
    """
    params = []
    
    if printer_id:
        query += " AND cr.printer_id = ?"
        params.append(printer_id)
    
    if location_id:
        query += " AND p.location_id = ?"
        params.append(location_id)
    
    if start_date:
        query += " AND cr.captured_at >= ?"
        params.append(start_date)
    
    if end_date:
        query += " AND cr.captured_at <= ?"
        params.append(end_date)
    
    query += " ORDER BY cr.captured_at DESC LIMIT ?"
    params.append(limit)
    
    cursor = db.execute(query, params)
    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def get_daily_consumption(
    db,
    printer_id: Optional[int] = None,
    location_id: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Obtener consumo diario usando la vista daily_consumption"""
    
    query = """
        SELECT 
            dc.date,
            p.printer_code,
            p.name as printer_name,
            l.name as location_name,
            dc.total_start,
            dc.total_end,
            dc.daily_consumption,
            dc.bn_start,
            dc.bn_end,
            dc.bn_consumption,
            dc.color_start,
            dc.color_end,
            dc.color_consumption,
            dc.reading_count
        FROM daily_consumption dc
        JOIN printers p ON dc.printer_id = p.id
        LEFT JOIN locations l ON p.location_id = l.id
        WHERE 1=1
    """
    params = []
    
    if printer_id:
        query += " AND dc.printer_id = ?"
        params.append(printer_id)
    
    if location_id:
        query += " AND p.location_id = ?"
        params.append(location_id)
    
    if start_date:
        query += " AND dc.date >= ?"
        params.append(start_date)
    
    if end_date:
        query += " AND dc.date <= ?"
        params.append(end_date)
    
    query += " ORDER BY dc.date DESC, p.printer_code"
    
    cursor = db.execute(query, params)
    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def get_consumption_summary(
    db,
    start_date: str,
    end_date: str,
    printer_id: Optional[int] = None,
    location_id: Optional[int] = None
) -> Dict[str, Any]:
    """Obtener resumen de consumo para el dashboard"""
    
    query = """
        SELECT 
            SUM(dc.daily_consumption) as total_consumption,
            SUM(dc.bn_consumption) as bn_consumption,
            SUM(dc.color_consumption) as color_consumption,
            COUNT(DISTINCT dc.printer_id) as active_printers,
            COUNT(*) as total_days
        FROM daily_consumption dc
        JOIN printers p ON dc.printer_id = p.id
        WHERE dc.date BETWEEN ? AND ?
    """
    params = [start_date, end_date]
    
    if printer_id:
        query += " AND dc.printer_id = ?"
        params.append(printer_id)
    
    if location_id:
        query += " AND p.location_id = ?"
        params.append(location_id)
    
    cursor = db.execute(query, params)
    row = cursor.fetchone()
    
    if not row or row[0] is None:
        return {
            'total_consumption': 0,
            'bn_consumption': 0,
            'color_consumption': 0,
            'active_printers': 0,
            'total_days': 0
        }
    
    return {
        'total_consumption': row[0] or 0,
        'bn_consumption': row[1] or 0,
        'color_consumption': row[2] or 0,
        'active_printers': row[3] or 0,
        'total_days': row[4] or 0
    }


def get_top_printers_by_consumption(
    db,
    start_date: str,
    end_date: str,
    location_id: Optional[int] = None,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """Obtener top impresoras por consumo"""
    
    query = """
        SELECT 
            p.printer_code,
            p.name as printer_name,
            l.name as location_name,
            SUM(dc.daily_consumption) as total_consumption,
            SUM(dc.bn_consumption) as bn_consumption,
            SUM(dc.color_consumption) as color_consumption
        FROM daily_consumption dc
        JOIN printers p ON dc.printer_id = p.id
        LEFT JOIN locations l ON p.location_id = l.id
        WHERE dc.date BETWEEN ? AND ?
    """
    params = [start_date, end_date]
    
    if location_id:
        query += " AND p.location_id = ?"
        params.append(location_id)
    
    query += """
        GROUP BY p.id, p.printer_code, p.name, l.name
        ORDER BY total_consumption DESC
        LIMIT ?
    """
    params.append(limit)
    
    cursor = db.execute(query, params)
    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def get_top_locations_by_consumption(
    db,
    start_date: str,
    end_date: str,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """Obtener top ubicaciones por consumo"""
    
    query = """
        SELECT 
            l.name as location_name,
            l.building,
            l.floor,
            SUM(dc.daily_consumption) as total_consumption,
            SUM(dc.bn_consumption) as bn_consumption,
            SUM(dc.color_consumption) as color_consumption,
            COUNT(DISTINCT dc.printer_id) as printer_count
        FROM daily_consumption dc
        JOIN printers p ON dc.printer_id = p.id
        LEFT JOIN locations l ON p.location_id = l.id
        WHERE dc.date BETWEEN ? AND ? AND l.id IS NOT NULL
        GROUP BY l.id, l.name, l.building, l.floor
        ORDER BY total_consumption DESC
        LIMIT ?
    """
    params = [start_date, end_date, limit]
    
    cursor = db.execute(query, params)
    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def get_today_consumption(
    db,
    printer_id: Optional[int] = None,
    location_id: Optional[int] = None
) -> List[Dict[str, Any]]:
    """Obtener consumo del día actual (lecturas de hoy)"""
    
    query = """
        SELECT 
            DATE(cr.captured_at) as date,
            p.printer_code,
            p.name as printer_name,
            l.name as location_name,
            cr.total_impressions,
            cr.bn_impressions,
            cr.color_impressions,
            cr.captured_at
        FROM counter_readings cr
        JOIN printers p ON cr.printer_id = p.id
        LEFT JOIN locations l ON p.location_id = l.id
        WHERE DATE(cr.captured_at) = DATE('now', 'localtime')
    """
    params = []
    
    if printer_id:
        query += " AND cr.printer_id = ?"
        params.append(printer_id)
    
    if location_id:
        query += " AND p.location_id = ?"
        params.append(location_id)
    
    query += " ORDER BY cr.captured_at DESC"
    
    cursor = db.execute(query, params)
    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def insert_counter_reading(
    db,
    printer_id: int,
    total_impressions: int,
    bn_impressions: int,
    color_impressions: int,
    captured_at: Optional[str] = None
) -> int:
    """Insertar una nueva lectura de contómetro"""
    
    if captured_at is None:
        captured_at = "strftime('%Y-%m-%d %H:%M:%S','now','localtime')"
        query = """
            INSERT INTO counter_readings (printer_id, total_impressions, bn_impressions, color_impressions, captured_at)
            VALUES (?, ?, ?, ?, strftime('%Y-%m-%d %H:%M:%S','now','localtime'))
        """
        params = (printer_id, total_impressions, bn_impressions, color_impressions)
    else:
        query = """
            INSERT INTO counter_readings (printer_id, total_impressions, bn_impressions, color_impressions, captured_at)
            VALUES (?, ?, ?, ?, ?)
        """
        params = (printer_id, total_impressions, bn_impressions, color_impressions, captured_at)
    
    cursor = db.execute(query, params)
    db.commit()
    return cursor.lastrowid


def get_last_counter_reading(db, printer_id: int) -> Optional[Dict[str, Any]]:
    """Obtener la última lectura de contómetro para una impresora"""
    
    query = """
        SELECT 
            cr.id,
            cr.printer_id,
            cr.captured_at,
            cr.total_impressions,
            cr.bn_impressions,
            cr.color_impressions
        FROM counter_readings cr
        WHERE cr.printer_id = ?
        ORDER BY cr.captured_at DESC
        LIMIT 1
    """
    
    cursor = db.execute(query, (printer_id,))
    row = cursor.fetchone()
    
    if not row:
        return None
    
    columns = [desc[0] for desc in cursor.description]
    return dict(zip(columns, row))


def get_counter_readings_for_export(
    db,
    start_date: str,
    end_date: str,
    printer_id: Optional[int] = None,
    location_id: Optional[int] = None
) -> List[Dict[str, Any]]:
    """Obtener datos de contómetros para exportación (formato CSV/XLSX)"""
    
    query = """
        WITH daily_data AS (
            SELECT 
                DATE(cr.captured_at) as date,
                cr.printer_id,
                MIN(cr.captured_at) as first_capture,
                MAX(cr.captured_at) as last_capture,
                MIN(cr.total_impressions) as total_start,
                MAX(cr.total_impressions) as total_end,
                MIN(cr.bn_impressions) as bn_start,
                MAX(cr.bn_impressions) as bn_end,
                MIN(cr.color_impressions) as color_start,
                MAX(cr.color_impressions) as color_end
            FROM counter_readings cr
            WHERE DATE(cr.captured_at) BETWEEN ? AND ?
            GROUP BY DATE(cr.captured_at), cr.printer_id
        )
        SELECT 
            dd.date,
            p.printer_code as impresora,
            l.name as ubicacion,
            dd.total_end as total,
            dd.bn_end as bn,
            dd.color_end as color,
            (dd.total_end - dd.total_start) as consumo_diario
        FROM daily_data dd
        JOIN printers p ON dd.printer_id = p.id
        LEFT JOIN locations l ON p.location_id = l.id
        WHERE (dd.total_end - dd.total_start) > 0
    """
    params = [start_date, end_date]
    
    if printer_id:
        query += " AND dd.printer_id = ?"
        params.append(printer_id)
    
    if location_id:
        query += " AND p.location_id = ?"
        params.append(location_id)
    
    query += " ORDER BY dd.date DESC, p.printer_code"
    
    cursor = db.execute(query, params)
    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]
