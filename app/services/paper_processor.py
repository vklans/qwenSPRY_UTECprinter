"""
Paper Processor - Procesamiento de lecturas de papel
Detecta eventos: LOW, CRITICAL, EMPTY, REFILLED, JAM
"""
import logging
from datetime import datetime
from typing import Optional, Dict

from ..database.connection import get_db

logger = logging.getLogger(__name__)


def process_paper_reading(data) -> Dict:
    """
    Procesa una lectura de nivel de papel y la guarda en BD
    
    Args:
        data: PrinterData con los datos SNMP
    
    Returns:
        dict con {'success': bool, 'error': str}
    """
    db = get_db()
    cursor = db.cursor()
    
    try:
        if data.paper_sheets_available is None:
            return {'success': False, 'error': 'Nivel de papel no disponible'}
        
        # Calcular porcentaje si no viene calculado
        level_percent = data.paper_level_percent
        if level_percent is None and data.paper_capacity:
            level_percent = round((data.paper_sheets_available / data.paper_capacity) * 100, 2)
        
        # Insertar lectura
        cursor.execute("""
            INSERT INTO paper_readings 
            (printer_id, captured_at, sheets_available, capacity, level_percent, 
             alert_code, alert_description)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            data.printer_id,
            data.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            data.paper_sheets_available,
            data.paper_capacity or 500,
            level_percent,
            data.alert_code,
            data.alert_description
        ))
        
        db.commit()
        reading_id = cursor.lastrowid
        
        logger.debug(f"Lectura de papel guardada: ID={reading_id}, Level={level_percent}%")
        
        return {
            'success': True,
            'reading_id': reading_id,
            'sheets': data.paper_sheets_available,
            'capacity': data.paper_capacity,
            'level_percent': level_percent
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error al guardar lectura de papel: {e}", exc_info=True)
        return {'success': False, 'error': str(e)}


def check_paper_alerts(db, printer_id: int, data) -> Dict:
    """
    Verifica umbrales y genera alertas de papel
    
    Args:
        db: conexión a BD
        printer_id: ID de la impresora
        data: PrinterData con niveles actuales
    
    Returns:
        dict con {'alert_generated': bool, 'alert_type': str}
    """
    cursor = db.cursor()
    
    # Obtener umbrales de configuración
    cursor.execute("SELECT value FROM system_config WHERE key = 'alerts.paper.low_threshold_percent'")
    low_threshold = int(cursor.fetchone()['value']) if cursor.fetchone() else 20
    
    cursor.execute("SELECT value FROM system_config WHERE key = 'alerts.paper.critical_threshold_percent'")
    critical_threshold = int(cursor.fetchone()['value']) if cursor.fetchone() else 10
    
    if data.paper_level_percent is None:
        return {'alert_generated': False}
    
    level = data.paper_level_percent
    
    # Determinar tipo de alerta
    alert_type = None
    severity = None
    
    if level == 0 or (data.alert_code and _is_paper_empty_code(data.alert_code)):
        alert_type = 'PAPER_EMPTY'
        severity = 'critical'
    elif level <= critical_threshold:
        alert_type = 'PAPER_CRITICAL'
        severity = 'critical'
    elif level <= low_threshold:
        alert_type = 'PAPER_LOW'
        severity = 'warning'
    
    # Detectar atasco por código de alerta
    if data.alert_code and _is_paper_jam_code(data.alert_code):
        alert_type = 'PAPER_JAM'
        severity = 'critical'
    
    if not alert_type:
        return {'alert_generated': False}
    
    # Verificar si ya existe una alerta activa del mismo tipo
    cursor.execute("""
        SELECT id FROM notifications
        WHERE printer_id = ?
          AND notification_type = ?
          AND is_active = 1
    """, (printer_id, alert_type))
    
    if cursor.fetchone():
        logger.debug(f"Alerta {alert_type} ya activa para impresora {printer_id}")
        return {'alert_generated': False}
    
    # Crear notificación
    from .notification_service import create_notification
    
    result = create_notification(
        db=db,
        printer_id=printer_id,
        notification_type=alert_type,
        severity=severity,
        title=f"{'Atasco' if alert_type == 'PAPER_JAM' else 'Nivel de papel'} - {data.printer_code}",
        message=_get_alert_message(alert_type, data),
        alert_code=data.alert_code,
        alert_description=data.alert_description
    )
    
    if result['success']:
        logger.info(f"Alerta generada: {alert_type} para {data.printer_code}")
        return {
            'alert_generated': True,
            'alert_type': alert_type,
            'notification_id': result['notification_id']
        }
    
    return {'alert_generated': False, 'error': result.get('error')}


def _is_paper_empty_code(code: int) -> bool:
    """Verifica si el código SNMP indica bandeja vacía"""
    # Códigos comunes de bandeja vacía
    empty_codes = [0, 3, 4, 5]  # Depende del fabricante
    return code in empty_codes


def _is_paper_jam_code(code: int) -> bool:
    """Verifica si el código SNMP indica atasco de papel"""
    # Códigos comunes de atasco (varían por fabricante)
    jam_codes = list(range(100, 110)) + list(range(200, 210))
    return code in jam_codes


def _get_alert_message(alert_type: str, data) -> str:
    """Genera mensaje descriptivo para la alerta"""
    messages = {
        'PAPER_LOW': f"Nivel bajo: {data.paper_level_percent}% ({data.paper_sheets_available} hojas)",
        'PAPER_CRITICAL': f"Nivel crítico: {data.paper_level_percent}% ({data.paper_sheets_available} hojas)",
        'PAPER_EMPTY': "Bandeja vacía - Requiere refill inmediato",
        'PAPER_JAM': f"Atasco detectado: {data.alert_description or 'Código ' + str(data.alert_code)}"
    }
    return messages.get(alert_type, "Alerta de papel detectada")
