"""
Processor - Procesamiento de lecturas de contómetros
Calcula deltas, detecta anomalías y guarda en BD
"""
import logging
from datetime import datetime
from typing import Optional, Dict

from ..database.connection import get_db

logger = logging.getLogger(__name__)


def process_counter_reading(data) -> Dict:
    """
    Procesa una lectura de contómetros y la guarda en BD
    
    Args:
        data: PrinterData con los datos SNMP
    
    Returns:
        dict con {'success': bool, 'error': str (si falla)}
    """
    db = get_db()
    cursor = db.cursor()
    
    try:
        # Validar datos mínimos
        if data.total_impressions is None:
            return {'success': False, 'error': 'Total de impresiones no disponible'}
        
        # Insertar lectura
        cursor.execute("""
            INSERT INTO counter_readings 
            (printer_id, captured_at, total_impressions, bn_impressions, color_impressions)
            VALUES (?, ?, ?, ?, ?)
        """, (
            data.printer_id,
            data.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            data.total_impressions or 0,
            data.bn_impressions or 0,
            data.color_impressions or 0
        ))
        
        db.commit()
        reading_id = cursor.lastrowid
        
        logger.debug(f"Lectura de contador guardada: ID={reading_id}")
        
        return {
            'success': True,
            'reading_id': reading_id,
            'total': data.total_impressions,
            'bn': data.bn_impressions,
            'color': data.color_impressions
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error al guardar lectura de contador: {e}", exc_info=True)
        return {'success': False, 'error': str(e)}


def calculate_daily_consumption(printer_id: int, date: str) -> Optional[Dict]:
    """
    Calcula el consumo diario para una impresora en una fecha específica
    
    Args:
        printer_id: ID de la impresora
        date: Fecha en formato YYYY-MM-DD
    
    Returns:
        dict con consumos o None si no hay datos
    """
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute("""
        SELECT 
            MIN(total_impressions) as total_start,
            MAX(total_impressions) as total_end,
            MIN(bn_impressions) as bn_start,
            MAX(bn_impressions) as bn_end,
            MIN(color_impressions) as color_start,
            MAX(color_impressions) as color_end,
            COUNT(*) as readings_count
        FROM counter_readings
        WHERE printer_id = ?
          AND DATE(captured_at) = ?
    """, (printer_id, date))
    
    result = cursor.fetchone()
    
    if not result or result['readings_count'] < 2:
        return None
    
    return {
        'date': date,
        'printer_id': printer_id,
        'total_consumption': result['total_end'] - result['total_start'],
        'bn_consumption': result['bn_end'] - result['bn_start'],
        'color_consumption': result['color_end'] - result['color_start'],
        'readings_count': result['readings_count']
    }


def detect_counter_anomaly(printer_id: int, current_total: int) -> Optional[str]:
    """
    Detecta anomalías en contómetros (reset, salto grande, etc.)
    
    Args:
        printer_id: ID de la impresora
        current_total: Valor actual del contador total
    
    Returns:
        str con tipo de anomalía o None si todo está bien
    """
    db = get_db()
    cursor = db.cursor()
    
    # Obtener última lectura
    cursor.execute("""
        SELECT total_impressions, captured_at
        FROM counter_readings
        WHERE printer_id = ?
        ORDER BY captured_at DESC
        LIMIT 1
    """, (printer_id,))
    
    last_reading = cursor.fetchone()
    
    if not last_reading:
        return None  # Primera lectura, no hay anomalía
    
    last_total = last_reading['total_impressions']
    
    # Detectar reset (valor actual menor que anterior)
    if current_total < last_total:
        logger.warning(
            f"Posible reset de contador en impresora {printer_id}: "
            f"{last_total} -> {current_total}"
        )
        return 'COUNTER_RESET'
    
    # Detectar salto anormal (> 10000 impresiones entre lecturas de 8h)
    diff = current_total - last_total
    if diff > 10000:
        logger.warning(
            f"Salto anormal en contador {printer_id}: +{diff} impresiones"
        )
        return 'COUNTER_JUMP'
    
    return None
