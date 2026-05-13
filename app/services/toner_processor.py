"""
Toner Processor - Procesamiento de lecturas de tóner
Normaliza niveles Ricoh/Kyocera y detecta alertas
"""
import logging
from typing import Dict

from ..database.connection import get_db

logger = logging.getLogger(__name__)


def process_toner_reading(data) -> Dict:
    """
    Procesa una lectura de nivel de tóner y la guarda en BD
    
    Args:
        data: PrinterData con los datos SNMP
    
    Returns:
        dict con {'success': bool, 'error': str}
    """
    db = get_db()
    cursor = db.cursor()
    
    try:
        # Validar que al menos un color tenga datos
        has_data = any([
            data.toner_black_level is not None,
            data.toner_cyan_level is not None,
            data.toner_magenta_level is not None,
            data.toner_yellow_level is not None
        ])
        
        if not has_data:
            return {'success': False, 'error': 'No hay datos de tóner'}
        
        # Insertar lectura
        cursor.execute("""
            INSERT INTO toner_readings 
            (printer_id, captured_at, 
             black_level_raw, black_max_raw,
             cyan_level_raw, cyan_max_raw,
             magenta_level_raw, magenta_max_raw,
             yellow_level_raw, yellow_max_raw)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.printer_id,
            data.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            data.toner_black_level,
            data.toner_black_max,
            data.toner_cyan_level,
            data.toner_cyan_max,
            data.toner_magenta_level,
            data.toner_magenta_max,
            data.toner_yellow_level,
            data.toner_yellow_max
        ))
        
        db.commit()
        reading_id = cursor.lastrowid
        
        logger.debug(f"Lectura de tóner guardada: ID={reading_id}")
        
        return {
            'success': True,
            'reading_id': reading_id
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error al guardar lectura de tóner: {e}", exc_info=True)
        return {'success': False, 'error': str(e)}


def check_toner_alerts(db, printer_id: int, data, unit_type: str = 'percent') -> Dict:
    """
    Verifica umbrales y genera alertas de tóner bajo/agotado
    
    Args:
        db: conexión a BD
        printer_id: ID de la impresora
        data: PrinterData con niveles actuales
        unit_type: 'percent' o 'absolute'
    
    Returns:
        dict con {'alerts_generated': int}
    """
    cursor = db.cursor()
    
    # Obtener umbrales de configuración
    cursor.execute("SELECT value FROM system_config WHERE key = 'alerts.toner.low_threshold_percent'")
    result = cursor.fetchone()
    low_threshold = int(result['value']) if result else 20
    
    cursor.execute("SELECT value FROM system_config WHERE key = 'alerts.toner.critical_threshold_percent'")
    result = cursor.fetchone()
    critical_threshold = int(result['value']) if result else 10
    
    alerts_generated = 0
    colors = ['black', 'cyan', 'magenta', 'yellow']
    
    for color in colors:
        level = getattr(data, f'toner_{color}_level')
        max_level = getattr(data, f'toner_{color}_max')
        
        if level is None or max_level is None or max_level == 0:
            continue
        
        # Calcular porcentaje
        pct = (level / max_level) * 100
        
        # Determinar tipo de alerta
        alert_type = None
        severity = None
        
        if pct <= 5:
            alert_type = f'TONER_EMPTY_{color.upper()}'
            severity = 'critical'
        elif pct <= critical_threshold:
            alert_type = f'TONER_CRITICAL_{color.upper()}'
            severity = 'critical'
        elif pct <= low_threshold:
            alert_type = f'TONER_LOW_{color.upper()}'
            severity = 'warning'
        
        if not alert_type:
            continue
        
        # Verificar si ya existe alerta activa
        cursor.execute("""
            SELECT id FROM notifications
            WHERE printer_id = ?
              AND notification_type = ?
              AND is_active = 1
        """, (printer_id, alert_type))
        
        if cursor.fetchone():
            continue
        
        # Crear notificación
        from .notification_service import create_notification
        
        color_name = {
            'black': 'Negro',
            'cyan': 'Cyan',
            'magenta': 'Magenta',
            'yellow': 'Amarillo'
        }.get(color, color)
        
        result = create_notification(
            db=db,
            printer_id=printer_id,
            notification_type=alert_type,
            severity=severity,
            title=f"Tóner {color_name} bajo - {data.printer_code}",
            message=f"Nivel: {pct:.1f}% - Requiere reemplazo pronto",
        )
        
        if result['success']:
            alerts_generated += 1
            logger.info(f"Alerta generada: {alert_type} para {data.printer_code}")
    
    return {'alerts_generated': alerts_generated}
