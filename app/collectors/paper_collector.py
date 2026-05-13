"""
Paper Collector - Recolector de nivel de papel cada 60s/15s
Monitorea bandejas y detecta eventos: LOW, CRITICAL, EMPTY, REFILLED, JAM
"""
import logging
from datetime import datetime
from typing import List, Optional

from ..database.connection import get_db
from ..collectors.snmp_client import get_snmp_client
from ..services.paper_processor import process_paper_reading, check_paper_alerts

logger = logging.getLogger(__name__)


def collect_paper(force_fast_mode: bool = False) -> dict:
    """
    Ejecuta la recolección de nivel de papel para todas las impresoras activas
    
    Args:
        force_fast_mode: Si True, usa intervalo de 15s (cuando hay alertas activas)
    
    Returns:
        dict con estadísticas de la ejecución
    """
    logger.info("Iniciando recolección de nivel de papel...")
    
    db = get_db()
    cursor = db.cursor()
    
    # Obtener intervalo de configuración
    cursor.execute("""
        SELECT value FROM system_config 
        WHERE key = 'collectors.paper.interval_seconds'
    """)
    result = cursor.fetchone()
    normal_interval = int(result['value']) if result else 60
    
    cursor.execute("""
        SELECT value FROM system_config 
        WHERE key = 'collectors.paper.fast_interval_seconds'
    """)
    result = cursor.fetchone()
    fast_interval = int(result['fast_interval']) if result else 15
    
    # Determinar si usamos modo rápido
    use_fast_mode = force_fast_mode or _has_active_paper_alerts(db)
    current_interval = fast_interval if use_fast_mode else normal_interval
    
    # Obtener impresoras activas con monitoreo de papel habilitado
    cursor.execute("""
        SELECT 
            p.id, p.printer_code, p.ip_address, p.brand, p.profile,
            p.paper_capacity, p.paper_tray_index,
            p.snmp_community, p.snmp_version,
            l.name as location_name
        FROM printers p
        LEFT JOIN locations l ON p.location_id = l.id
        WHERE p.is_capture_active = 1 
          AND p.status IN ('active', 'maintenance')
          AND p.monitor_paper = 1
        ORDER BY p.printer_code
    """)
    
    printers = cursor.fetchall()
    total_printers = len(printers)
    successful = 0
    failed = 0
    events_generated = 0
    errors = []
    
    if total_printers == 0:
        logger.warning("No hay impresoras con monitoreo de papel activo")
        return {
            'total_printers': 0,
            'successful': 0,
            'failed': 0,
            'events_generated': 0,
            'errors': ['No hay impresoras configuradas para papel']
        }
    
    snmp_source = 'local_snmp'
    
    for printer in printers:
        printer_id = printer['id']
        printer_code = printer['printer_code']
        ip_address = printer['ip_address']
        brand = printer['brand']
        profile = printer['profile']
        capacity = printer['paper_capacity'] or 500
        tray_index = printer['paper_tray_index'] or 1.1
        community = printer['snmp_community'] or 'public'
        version = printer['snmp_version'] or 'v2c'
        location = printer['location_name'] or 'Sin ubicación'
        
        try:
            client = get_snmp_client(
                source=snmp_source,
                community=community,
                version=version,
                timeout=3,  # Timeout más corto para papel
                retries=1
            )
            
            # Consultar solo OIDs de papel y alertas
            data = client.collect_printer_data(
                printer_id=printer_id,
                printer_code=printer_code,
                ip_address=ip_address,
                brand=brand,
                profile=profile,
                paper_capacity=capacity
            )
            
            if data and data.paper_sheets_available is not None:
                # Procesar lectura de papel
                result = process_paper_reading(data)
                
                if result['success']:
                    successful += 1
                    
                    # Verificar alertas
                    alert_result = check_paper_alerts(db, printer_id, data)
                    if alert_result.get('alert_generated'):
                        events_generated += 1
                        logger.warning(
                            f"⚠ {printer_code}: {alert_result['alert_type']} - "
                            f"Nivel: {data.paper_level_percent}%"
                        )
                    
                    logger.debug(
                        f"✓ {printer_code}: Papel={data.paper_sheets_available}/{capacity} "
                        f"({data.paper_level_percent}%)"
                    )
                else:
                    failed += 1
                    error_msg = result.get('error', 'Error al procesar')
                    errors.append({'printer_code': printer_code, 'error': error_msg})
                    logger.error(f"✗ {printer_code}: {error_msg}")
            else:
                # Intentar al menos obtener estado de alerta
                if data and data.alert_code:
                    logger.warning(
                        f"⚠ {printer_code}: Alerta SNMP detectada - "
                        f"Código {data.alert_code}: {data.alert_description}"
                    )
                    successful += 1
                else:
                    failed += 1
                    errors.append({
                        'printer_code': printer_code,
                        'error': 'No se obtuvo nivel de papel'
                    })
            
        except Exception as e:
            failed += 1
            error_msg = f"Excepción: {str(e)}"
            errors.append({'printer_code': printer_code, 'error': error_msg})
            logger.error(f"✗ {printer_code}: {error_msg}", exc_info=True)
    
    logger.info(
        f"Recolección de papel completada ({current_interval}s): "
        f"{successful}/{total_printers} exitosas, {events_generated} eventos"
    )
    
    return {
        'total_printers': total_printers,
        'successful': successful,
        'failed': failed,
        'events_generated': events_generated,
        'interval_seconds': current_interval,
        'fast_mode': use_fast_mode,
        'errors': errors,
        'timestamp': datetime.now().isoformat()
    }


def _has_active_paper_alerts(db) -> bool:
    """Verifica si hay alertas de papel activas sin resolver"""
    cursor = db.cursor()
    cursor.execute("""
        SELECT COUNT(*) as count FROM notifications
        WHERE is_active = 1
          AND notification_type LIKE 'PAPER_%'
    """)
    result = cursor.fetchone()
    return result['count'] > 0 if result else False
