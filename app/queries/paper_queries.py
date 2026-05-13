"""
Consultas SQL para el módulo de papel
Todas las consultas usan parámetros posicionales (?) para prevenir inyección SQL
"""

from typing import List, Dict, Any, Optional


def get_paper_readings(
    db,
    printer_id: Optional[int] = None,
    location_id: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 1000
) -> List[Dict[str, Any]]:
    """Obtener lecturas de papel con filtros"""
    
    query = """
        SELECT 
            pr.id,
            pr.printer_id,
            p.printer_code,
            p.name as printer_name,
            l.name as location_name,
            pr.captured_at,
            pr.sheets_available,
            pr.capacity,
            pr.level_percent,
            pr.alert_code,
            pr.alert_description
        FROM paper_readings pr
        JOIN printers p ON pr.printer_id = p.id
        LEFT JOIN locations l ON p.location_id = l.id
        WHERE 1=1
    """
    params = []
    
    if printer_id:
        query += " AND pr.printer_id = ?"
        params.append(printer_id)
    
    if location_id:
        query += " AND p.location_id = ?"
        params.append(location_id)
    
    if start_date:
        query += " AND pr.captured_at >= ?"
        params.append(start_date)
    
    if end_date:
        query += " AND pr.captured_at <= ?"
        params.append(end_date)
    
    query += " ORDER BY pr.captured_at DESC LIMIT ?"
    params.append(limit)
    
    cursor = db.execute(query, params)
    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def get_current_paper_status(db) -> List[Dict[str, Any]]:
    """Obtener estado actual de papel para todas las impresoras (última lectura)"""
    
    query = """
        WITH latest_readings AS (
            SELECT 
                pr.printer_id,
                MAX(pr.captured_at) as max_time
            FROM paper_readings pr
            GROUP BY pr.printer_id
        )
        SELECT 
            lr.printer_id,
            p.printer_code,
            p.name as printer_name,
            l.name as location_name,
            pr.sheets_available,
            pr.capacity,
            pr.level_percent,
            pr.captured_at,
            CASE 
                WHEN pr.level_percent IS NULL THEN 'OFFLINE'
                WHEN pr.level_percent <= 5 THEN 'EMPTY'
                WHEN pr.level_percent <= 10 THEN 'CRITICAL'
                WHEN pr.level_percent <= 20 THEN 'LOW'
                ELSE 'OK'
            END as status
        FROM latest_readings lr
        JOIN paper_readings pr ON lr.printer_id = pr.printer_id AND lr.max_time = pr.captured_at
        JOIN printers p ON pr.printer_id = p.id
        LEFT JOIN locations l ON p.location_id = l.id
        ORDER BY pr.level_percent ASC NULLS LAST
    """
    
    cursor = db.execute(query)
    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def get_paper_events(
    db,
    printer_id: Optional[int] = None,
    event_type: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    unresolved_only: bool = False,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """Obtener eventos de papel con filtros"""
    
    query = """
        SELECT 
            pe.id,
            pe.printer_id,
            p.printer_code,
            p.name as printer_name,
            l.name as location_name,
            pe.event_type,
            pe.occurred_at,
            pe.previous_level,
            pe.new_level,
            pe.alert_code,
            pe.resolved_at,
            u.username as resolved_by_username,
            pe.auto_resolved
        FROM paper_events pe
        JOIN printers p ON pe.printer_id = p.id
        LEFT JOIN locations l ON p.location_id = l.id
        LEFT JOIN users u ON pe.resolved_by = u.id
        WHERE 1=1
    """
    params = []
    
    if printer_id:
        query += " AND pe.printer_id = ?"
        params.append(printer_id)
    
    if event_type:
        query += " AND pe.event_type = ?"
        params.append(event_type)
    
    if start_date:
        query += " AND pe.occurred_at >= ?"
        params.append(start_date)
    
    if end_date:
        query += " AND pe.occurred_at <= ?"
        params.append(end_date)
    
    if unresolved_only:
        query += " AND pe.resolved_at IS NULL"
    
    query += " ORDER BY pe.occurred_at DESC LIMIT ?"
    params.append(limit)
    
    cursor = db.execute(query, params)
    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def insert_paper_reading(
    db,
    printer_id: int,
    sheets_available: Optional[int],
    capacity: int,
    alert_code: Optional[int] = None,
    alert_description: Optional[str] = None,
    captured_at: Optional[str] = None
) -> int:
    """Insertar una nueva lectura de papel"""
    
    if captured_at is None:
        query = """
            INSERT INTO paper_readings (printer_id, sheets_available, capacity, alert_code, alert_description, captured_at)
            VALUES (?, ?, ?, ?, ?, strftime('%Y-%m-%d %H:%M:%S','now','localtime'))
        """
        params = (printer_id, sheets_available, capacity, alert_code, alert_description)
    else:
        query = """
            INSERT INTO paper_readings (printer_id, sheets_available, capacity, alert_code, alert_description, captured_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        params = (printer_id, sheets_available, capacity, alert_code, alert_description, captured_at)
    
    cursor = db.execute(query, params)
    db.commit()
    return cursor.lastrowid


def insert_paper_event(
    db,
    printer_id: int,
    event_type: str,
    previous_level: Optional[int],
    new_level: Optional[int],
    alert_code: Optional[int] = None,
    occurred_at: Optional[str] = None
) -> int:
    """Insertar un nuevo evento de papel"""
    
    if occurred_at is None:
        query = """
            INSERT INTO paper_events (printer_id, event_type, previous_level, new_level, alert_code, occurred_at)
            VALUES (?, ?, ?, ?, ?, strftime('%Y-%m-%d %H:%M:%S','now','localtime'))
        """
        params = (printer_id, event_type, previous_level, new_level, alert_code)
    else:
        query = """
            INSERT INTO paper_events (printer_id, event_type, previous_level, new_level, alert_code, occurred_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        params = (printer_id, event_type, previous_level, new_level, alert_code, occurred_at)
    
    cursor = db.execute(query, params)
    db.commit()
    return cursor.lastrowid


def resolve_paper_event(
    db,
    event_id: int,
    resolved_by: int,
    resolved_at: Optional[str] = None
) -> bool:
    """Marcar un evento de papel como resuelto"""
    
    if resolved_at is None:
        query = """
            UPDATE paper_events
            SET resolved_at = strftime('%Y-%m-%d %H:%M:%S','now','localtime'),
                resolved_by = ?
            WHERE id = ? AND resolved_at IS NULL
        """
        params = (resolved_by, event_id)
    else:
        query = """
            UPDATE paper_events
            SET resolved_at = ?,
                resolved_by = ?
            WHERE id = ? AND resolved_at IS NULL
        """
        params = (resolved_at, resolved_by, event_id)
    
    cursor = db.execute(query, params)
    db.commit()
    return cursor.rowcount > 0


def get_paper_summary_counts(db) -> Dict[str, int]:
    """Obtener conteo de impresoras por estado de papel"""
    
    query = """
        WITH latest_readings AS (
            SELECT 
                pr.printer_id,
                MAX(pr.captured_at) as max_time
            FROM paper_readings pr
            GROUP BY pr.printer_id
        ),
        status_counts AS (
            SELECT 
                CASE 
                    WHEN pr.level_percent IS NULL THEN 'OFFLINE'
                    WHEN pr.level_percent <= 5 THEN 'EMPTY'
                    WHEN pr.level_percent <= 10 THEN 'CRITICAL'
                    WHEN pr.level_percent <= 20 THEN 'LOW'
                    ELSE 'OK'
                END as status,
                COUNT(*) as count
            FROM latest_readings lr
            JOIN paper_readings pr ON lr.printer_id = pr.printer_id AND lr.max_time = pr.captured_at
            JOIN printers p ON pr.printer_id = p.id
            WHERE p.is_capture_active = 1 AND p.monitor_paper = 1
            GROUP BY 
                CASE 
                    WHEN pr.level_percent IS NULL THEN 'OFFLINE'
                    WHEN pr.level_percent <= 5 THEN 'EMPTY'
                    WHEN pr.level_percent <= 10 THEN 'CRITICAL'
                    WHEN pr.level_percent <= 20 THEN 'LOW'
                    ELSE 'OK'
                END
        )
        SELECT 
            COALESCE(SUM(CASE WHEN status = 'OK' THEN count ELSE 0 END), 0) as ok_count,
            COALESCE(SUM(CASE WHEN status = 'LOW' THEN count ELSE 0 END), 0) as low_count,
            COALESCE(SUM(CASE WHEN status = 'CRITICAL' THEN count ELSE 0 END), 0) as critical_count,
            COALESCE(SUM(CASE WHEN status = 'EMPTY' THEN count ELSE 0 END), 0) as empty_count,
            COALESCE(SUM(CASE WHEN status = 'OFFLINE' THEN count ELSE 0 END), 0) as offline_count
        FROM status_counts
    """
    
    cursor = db.execute(query)
    row = cursor.fetchone()
    
    return {
        'ok': row[0],
        'low': row[1],
        'critical': row[2],
        'empty': row[3],
        'offline': row[4]
    }


def get_unresolved_paper_events(db) -> List[Dict[str, Any]]:
    """Obtener eventos de papel sin resolver"""
    
    query = """
        SELECT 
            pe.id,
            pe.printer_id,
            p.printer_code,
            p.name as printer_name,
            l.name as location_name,
            pe.event_type,
            pe.occurred_at,
            pe.previous_level,
            pe.new_level,
            pe.alert_code
        FROM paper_events pe
        JOIN printers p ON pe.printer_id = p.id
        LEFT JOIN locations l ON p.location_id = l.id
        WHERE pe.resolved_at IS NULL
        ORDER BY pe.occurred_at DESC
    """
    
    cursor = db.execute(query)
    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def get_paper_consumption_today(
    db,
    printer_id: Optional[int] = None
) -> List[Dict[str, Any]]:
    """Obtener consumo de papel hoy (diferencia entre primera y última lectura)"""
    
    query = """
        WITH today_readings AS (
            SELECT 
                printer_id,
                MIN(sheets_available) as min_sheets,
                MAX(sheets_available) as max_sheets,
                MIN(captured_at) as first_reading,
                MAX(captured_at) as last_reading
            FROM paper_readings
            WHERE DATE(captured_at) = DATE('now', 'localtime')
            GROUP BY printer_id
        )
        SELECT 
            tr.printer_id,
            p.printer_code,
            p.name as printer_name,
            l.name as location_name,
            tr.max_sheets - tr.min_sheets as consumed_today,
            tr.min_sheets as current_level,
            tr.last_reading as last_update
        FROM today_readings tr
        JOIN printers p ON tr.printer_id = p.id
        LEFT JOIN locations l ON p.location_id = l.id
        WHERE tr.consumed_today > 0
    """
    params = []
    
    if printer_id:
        query += " AND tr.printer_id = ?"
        params.append(printer_id)
    
    cursor = db.execute(query, params)
    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def get_paper_readings_for_export(
    db,
    start_date: str,
    end_date: str,
    printer_id: Optional[int] = None,
    location_id: Optional[int] = None
) -> List[Dict[str, Any]]:
    """Obtener datos de papel para exportación"""
    
    query = """
        SELECT 
            DATE(pr.captured_at) as fecha,
            p.printer_code as impresora,
            l.name as ubicacion,
            pr.sheets_available as nivel,
            pr.capacity as capacidad,
            ROUND(pr.level_percent, 1) as porcentaje
        FROM paper_readings pr
        JOIN printers p ON pr.printer_id = p.id
        LEFT JOIN locations l ON p.location_id = l.id
        WHERE DATE(pr.captured_at) BETWEEN ? AND ?
    """
    params = [start_date, end_date]
    
    if printer_id:
        query += " AND pr.printer_id = ?"
        params.append(printer_id)
    
    if location_id:
        query += " AND p.location_id = ?"
        params.append(location_id)
    
    query += " ORDER BY pr.captured_at DESC"
    
    cursor = db.execute(query, params)
    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]
