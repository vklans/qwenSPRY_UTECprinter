"""
Notification Service - Gestión de notificaciones y alertas
Crea, actualiza, cierra y hace polling de notificaciones
"""
import logging
from datetime import datetime
from typing import Optional, Dict, List

from ..database.connection import get_db

logger = logging.getLogger(__name__)


def create_notification(
    db,
    printer_id: int,
    notification_type: str,
    severity: str,
    title: str,
    message: str,
    alert_code: Optional[int] = None,
    alert_description: Optional[str] = None
) -> Dict:
    """
    Crea una nueva notificación
    
    Returns:
        dict con {'success': bool, 'notification_id': int, 'error': str}
    """
    cursor = db.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO notifications 
            (printer_id, notification_type, severity, title, message,
             alert_code, alert_description, is_active, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)
        """, (
            printer_id,
            notification_type,
            severity,
            title,
            message,
            alert_code,
            alert_description,
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ))
        
        db.commit()
        notification_id = cursor.lastrowid
        
        return {
            'success': True,
            'notification_id': notification_id
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error al crear notificación: {e}", exc_info=True)
        return {'success': False, 'error': str(e)}


def get_active_notifications(printer_id: Optional[int] = None) -> List[Dict]:
    """
    Obtiene notificaciones activas (para polling)
    
    Args:
        printer_id: Filtrar por impresora (opcional)
    
    Returns:
        lista de notificaciones
    """
    db = get_db()
    cursor = db.cursor()
    
    query = """
        SELECT 
            n.id, n.printer_id, p.printer_code, p.name as printer_name,
            n.notification_type, n.severity, n.title, n.message,
            n.alert_code, n.alert_description,
            n.created_at, l.name as location_name
        FROM notifications n
        JOIN printers p ON n.printer_id = p.id
        LEFT JOIN locations l ON p.location_id = l.id
        WHERE n.is_active = 1
    """
    
    params = []
    if printer_id:
        query += " AND n.printer_id = ?"
        params.append(printer_id)
    
    query += " ORDER BY n.created_at DESC"
    
    cursor.execute(query, params)
    return cursor.fetchall()


def dismiss_notification(notification_id: int, user_id: int) -> Dict:
    """
    Marca una notificación como reconocida/cerrada por usuario
    
    Returns:
        dict con {'success': bool, 'error': str}
    """
    db = get_db()
    cursor = db.cursor()
    
    try:
        cursor.execute("""
            UPDATE notifications
            SET is_acknowledged = 1,
                acknowledged_by = ?,
                acknowledged_at = ?,
                is_active = 0
            WHERE id = ?
        """, (
            user_id,
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            notification_id
        ))
        
        db.commit()
        
        if cursor.rowcount == 0:
            return {'success': False, 'error': 'Notificación no encontrada'}
        
        return {'success': True}
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error al cerrar notificación: {e}")
        return {'success': False, 'error': str(e)}


def resolve_notification(notification_id: int, user_id: int) -> Dict:
    """
    Marca una notificación como resuelta (problema solucionado)
    
    Returns:
        dict con {'success': bool, 'error': str}
    """
    db = get_db()
    cursor = db.cursor()
    
    try:
        cursor.execute("""
            UPDATE notifications
            SET is_active = 0,
                resolved_by = ?,
                resolved_at = ?,
                is_auto_resolved = 0
            WHERE id = ?
        """, (
            user_id,
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            notification_id
        ))
        
        db.commit()
        
        if cursor.rowcount == 0:
            return {'success': False, 'error': 'Notificación no encontrada'}
        
        return {'success': True}
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error al resolver notificación: {e}")
        return {'success': False, 'error': str(e)}


def auto_resolve_paper_alerts(db, printer_id: int, current_level: float) -> int:
    """
    Auto-resuelve alertas de papel cuando el nivel se recupera
    
    Returns:
        cantidad de alertas auto-resueltas
    """
    cursor = db.cursor()
    
    # Si el nivel está por encima del threshold crítico, resolver alertas
    cursor.execute("""
        SELECT value FROM system_config 
        WHERE key = 'alerts.paper.low_threshold_percent'
    """)
    result = cursor.fetchone()
    low_threshold = int(result['value']) if result else 20
    
    if current_level > low_threshold:
        # Resolver alertas PAPER_LOW, PAPER_CRITICAL, PAPER_EMPTY
        cursor.execute("""
            UPDATE notifications
            SET is_active = 0,
                is_auto_resolved = 1,
                resolved_at = ?
            WHERE printer_id = ?
              AND is_active = 1
              AND notification_type IN ('PAPER_LOW', 'PAPER_CRITICAL', 'PAPER_EMPTY')
        """, (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), printer_id))
        
        db.commit()
        return cursor.rowcount
    
    return 0


def get_notification_history(
    printer_id: Optional[int] = None,
    limit: int = 100,
    offset: int = 0
) -> List[Dict]:
    """
    Obtiene histórico de notificaciones con paginación
    
    Returns:
        lista de notificaciones
    """
    db = get_db()
    cursor = db.cursor()
    
    query = """
        SELECT 
            n.id, n.printer_id, p.printer_code, p.name as printer_name,
            n.notification_type, n.severity, n.title, n.message,
            n.is_active, n.is_acknowledged, n.is_auto_resolved,
            n.created_at, n.resolved_at,
            u1.full_name as acknowledged_by_name,
            u2.full_name as resolved_by_name,
            l.name as location_name
        FROM notifications n
        JOIN printers p ON n.printer_id = p.id
        LEFT JOIN locations l ON p.location_id = l.id
        LEFT JOIN users u1 ON n.acknowledged_by = u1.id
        LEFT JOIN users u2 ON n.resolved_by = u2.id
        WHERE 1=1
    """
    
    params = []
    if printer_id:
        query += " AND n.printer_id = ?"
        params.append(printer_id)
    
    query += " ORDER BY n.created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    cursor.execute(query, params)
    return cursor.fetchall()
