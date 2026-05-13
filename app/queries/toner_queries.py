"""
Consultas SQL para el módulo de tóner
Todas las consultas usan parámetros posicionales (?) para prevenir inyección SQL
"""

from typing import List, Dict, Any, Optional


def get_toner_readings(
    db,
    printer_id: Optional[int] = None,
    location_id: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 1000
) -> List[Dict[str, Any]]:
    """Obtener lecturas de tóner con filtros"""
    
    query = """
        SELECT 
            tr.id,
            tr.printer_id,
            p.printer_code,
            p.name as printer_name,
            l.name as location_name,
            tr.captured_at,
            tr.black_level_raw,
            tr.black_max_raw,
            tr.black_pct,
            tr.cyan_level_raw,
            tr.cyan_max_raw,
            tr.cyan_pct,
            tr.magenta_level_raw,
            tr.magenta_max_raw,
            tr.magenta_pct,
            tr.yellow_level_raw,
            tr.yellow_max_raw,
            tr.yellow_pct
        FROM toner_readings tr
        JOIN printers p ON tr.printer_id = p.id
        LEFT JOIN locations l ON p.location_id = l.id
        WHERE 1=1
    """
    params = []
    
    if printer_id:
        query += " AND tr.printer_id = ?"
        params.append(printer_id)
    
    if location_id:
        query += " AND p.location_id = ?"
        params.append(location_id)
    
    if start_date:
        query += " AND tr.captured_at >= ?"
        params.append(start_date)
    
    if end_date:
        query += " AND tr.captured_at <= ?"
        params.append(end_date)
    
    query += " ORDER BY tr.captured_at DESC LIMIT ?"
    params.append(limit)
    
    cursor = db.execute(query, params)
    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def get_current_toner_status(db) -> List[Dict[str, Any]]:
    """Obtener estado actual de tóner para todas las impresoras (última lectura)"""
    
    query = """
        WITH latest_readings AS (
            SELECT 
                tr.printer_id,
                MAX(tr.captured_at) as max_time
            FROM toner_readings tr
            GROUP BY tr.printer_id
        )
        SELECT 
            lr.printer_id,
            p.printer_code,
            p.name as printer_name,
            l.name as location_name,
            tr.black_pct,
            tr.cyan_pct,
            tr.magenta_pct,
            tr.yellow_pct,
            tr.captured_at,
            CASE 
                WHEN tr.black_pct IS NULL THEN 'OFFLINE'
                WHEN tr.black_pct <= 5 OR tr.cyan_pct <= 5 OR tr.magenta_pct <= 5 OR tr.yellow_pct <= 5 THEN 'CRITICAL'
                WHEN tr.black_pct <= 10 OR tr.cyan_pct <= 10 OR tr.magenta_pct <= 10 OR tr.yellow_pct <= 10 THEN 'LOW'
                ELSE 'OK'
            END as status
        FROM latest_readings lr
        JOIN toner_readings tr ON lr.printer_id = tr.printer_id AND lr.max_time = tr.captured_at
        JOIN printers p ON tr.printer_id = p.id
        LEFT JOIN locations l ON p.location_id = l.id
        ORDER BY 
            CASE 
                WHEN tr.black_pct IS NULL THEN 999
                ELSE COALESCE(tr.black_pct, tr.cyan_pct, tr.magenta_pct, tr.yellow_pct, 100)
            END ASC
    """
    
    cursor = db.execute(query)
    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def get_toner_catalog(db, include_inactive: bool = False) -> List[Dict[str, Any]]:
    """Obtener catálogo de tóners"""
    
    query = """
        SELECT 
            id,
            part_number,
            brand,
            color,
            yield_pages,
            compatible_printers,
            is_active,
            created_at,
            updated_at
        FROM toner_catalog
    """
    
    if not include_inactive:
        query += " WHERE is_active = 1"
    
    query += " ORDER BY brand, part_number"
    
    cursor = db.execute(query)
    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def insert_toner_reading(
    db,
    printer_id: int,
    black_level_raw: Optional[int],
    black_max_raw: Optional[int],
    cyan_level_raw: Optional[int],
    cyan_max_raw: Optional[int],
    magenta_level_raw: Optional[int],
    magenta_max_raw: Optional[int],
    yellow_level_raw: Optional[int],
    yellow_max_raw: Optional[int],
    captured_at: Optional[str] = None
) -> int:
    """Insertar una nueva lectura de tóner"""
    
    if captured_at is None:
        query = """
            INSERT INTO toner_readings (
                printer_id, black_level_raw, black_max_raw, cyan_level_raw, cyan_max_raw,
                magenta_level_raw, magenta_max_raw, yellow_level_raw, yellow_max_raw, captured_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, strftime('%Y-%m-%d %H:%M:%S','now','localtime'))
        """
        params = (
            printer_id, black_level_raw, black_max_raw, cyan_level_raw, cyan_max_raw,
            magenta_level_raw, magenta_max_raw, yellow_level_raw, yellow_max_raw
        )
    else:
        query = """
            INSERT INTO toner_readings (
                printer_id, black_level_raw, black_max_raw, cyan_level_raw, cyan_max_raw,
                magenta_level_raw, magenta_max_raw, yellow_level_raw, yellow_max_raw, captured_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            printer_id, black_level_raw, black_max_raw, cyan_level_raw, cyan_max_raw,
            magenta_level_raw, magenta_max_raw, yellow_level_raw, yellow_max_raw, captured_at
        )
    
    cursor = db.execute(query, params)
    db.commit()
    return cursor.lastrowid


def insert_toner_catalog_item(
    db,
    part_number: str,
    brand: str,
    color: str,
    yield_pages: int,
    compatible_printers: str
) -> int:
    """Insertar un nuevo ítem en el catálogo de tóners"""
    
    query = """
        INSERT INTO toner_catalog (part_number, brand, color, yield_pages, compatible_printers)
        VALUES (?, ?, ?, ?, ?)
    """
    
    cursor = db.execute(query, (part_number, brand, color, yield_pages, compatible_printers))
    db.commit()
    return cursor.lastrowid


def update_toner_catalog_item(
    db,
    item_id: int,
    part_number: Optional[str] = None,
    brand: Optional[str] = None,
    color: Optional[str] = None,
    yield_pages: Optional[int] = None,
    compatible_printers: Optional[str] = None,
    is_active: Optional[int] = None
) -> bool:
    """Actualizar un ítem del catálogo de tóners"""
    
    updates = []
    params = []
    
    if part_number is not None:
        updates.append("part_number = ?")
        params.append(part_number)
    if brand is not None:
        updates.append("brand = ?")
        params.append(brand)
    if color is not None:
        updates.append("color = ?")
        params.append(color)
    if yield_pages is not None:
        updates.append("yield_pages = ?")
        params.append(yield_pages)
    if compatible_printers is not None:
        updates.append("compatible_printers = ?")
        params.append(compatible_printers)
    if is_active is not None:
        updates.append("is_active = ?")
        params.append(is_active)
    
    if not updates:
        return False
    
    updates.append("updated_at = strftime('%Y-%m-%d %H:%M:%S','now','localtime')")
    params.append(item_id)
    
    query = f"UPDATE toner_catalog SET {', '.join(updates)} WHERE id = ?"
    
    cursor = db.execute(query, params)
    db.commit()
    return cursor.rowcount > 0


def delete_toner_catalog_item(db, item_id: int) -> bool:
    """Eliminar (desactivar) un ítem del catálogo"""
    
    # Soft delete: desactivar en lugar de eliminar
    query = """
        UPDATE toner_catalog
        SET is_active = 0, updated_at = strftime('%Y-%m-%d %H:%M:%S','now','localtime')
        WHERE id = ?
    """
    
    cursor = db.execute(query, (item_id,))
    db.commit()
    return cursor.rowcount > 0


def get_toner_low_alerts(db) -> List[Dict[str, Any]]:
    """Obtener alertas de tóner bajo (últimas lecturas con % bajo)"""
    
    query = """
        WITH latest_readings AS (
            SELECT 
                tr.printer_id,
                MAX(tr.captured_at) as max_time
            FROM toner_readings tr
            GROUP BY tr.printer_id
        )
        SELECT 
            lr.printer_id,
            p.printer_code,
            p.name as printer_name,
            l.name as location_name,
            tr.black_pct,
            tr.cyan_pct,
            tr.magenta_pct,
            tr.yellow_pct,
            tr.captured_at,
            CASE 
                WHEN tr.black_pct <= 5 THEN 'CRITICAL'
                WHEN tr.black_pct <= 20 THEN 'LOW'
                ELSE 'OK'
            END as black_status,
            CASE 
                WHEN tr.cyan_pct <= 5 THEN 'CRITICAL'
                WHEN tr.cyan_pct <= 20 THEN 'LOW'
                ELSE 'OK'
            END as cyan_status,
            CASE 
                WHEN tr.magenta_pct <= 5 THEN 'CRITICAL'
                WHEN tr.magenta_pct <= 20 THEN 'LOW'
                ELSE 'OK'
            END as magenta_status,
            CASE 
                WHEN tr.yellow_pct <= 5 THEN 'CRITICAL'
                WHEN tr.yellow_pct <= 20 THEN 'LOW'
                ELSE 'OK'
            END as yellow_status
        FROM latest_readings lr
        JOIN toner_readings tr ON lr.printer_id = tr.printer_id AND lr.max_time = tr.captured_at
        JOIN printers p ON tr.printer_id = p.id
        LEFT JOIN locations l ON p.location_id = l.id
        WHERE tr.black_pct <= 20 
           OR tr.cyan_pct <= 20 
           OR tr.magenta_pct <= 20 
           OR tr.yellow_pct <= 20
        ORDER BY 
            LEAST(
                COALESCE(tr.black_pct, 100),
                COALESCE(tr.cyan_pct, 100),
                COALESCE(tr.magenta_pct, 100),
                COALESCE(tr.yellow_pct, 100)
            ) ASC
    """
    
    cursor = db.execute(query)
    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def get_toner_history_by_printer(
    db,
    printer_id: int,
    days: int = 30
) -> List[Dict[str, Any]]:
    """Obtener histórico de niveles de tóner para una impresora"""
    
    query = """
        SELECT 
            DATE(tr.captured_at) as date,
            AVG(tr.black_pct) as avg_black,
            AVG(tr.cyan_pct) as avg_cyan,
            AVG(tr.magenta_pct) as avg_magenta,
            AVG(tr.yellow_pct) as avg_yellow,
            MIN(tr.black_pct) as min_black,
            MAX(tr.black_pct) as max_black
        FROM toner_readings tr
        WHERE tr.printer_id = ?
          AND DATE(tr.captured_at) >= DATE('now', 'localtime', ? || ' days')
        GROUP BY DATE(tr.captured_at)
        ORDER BY date DESC
    """
    
    cursor = db.execute(query, (printer_id, f'-{days}'))
    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def get_toner_readings_for_export(
    db,
    start_date: str,
    end_date: str,
    printer_id: Optional[int] = None,
    location_id: Optional[int] = None
) -> List[Dict[str, Any]]:
    """Obtener datos de tóner para exportación"""
    
    query = """
        SELECT 
            DATE(tr.captured_at) as fecha,
            p.printer_code as impresora,
            l.name as ubicacion,
            ROUND(AVG(tr.black_pct), 1) as nivel_promedio,
            ROUND(AVG(tr.cyan_pct), 1) as cyan,
            ROUND(AVG(tr.magenta_pct), 1) as magenta,
            ROUND(AVG(tr.yellow_pct), 1) as yellow
        FROM toner_readings tr
        JOIN printers p ON tr.printer_id = p.id
        LEFT JOIN locations l ON p.location_id = l.id
        WHERE DATE(tr.captured_at) BETWEEN ? AND ?
    """
    params = [start_date, end_date]
    
    if printer_id:
        query += " AND tr.printer_id = ?"
        params.append(printer_id)
    
    if location_id:
        query += " AND p.location_id = ?"
        params.append(location_id)
    
    query += " GROUP BY DATE(tr.captured_at), p.printer_code, l.name ORDER BY tr.captured_at DESC"
    
    cursor = db.execute(query, params)
    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]
