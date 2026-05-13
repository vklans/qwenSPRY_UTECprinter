"""
Toner Collector - Recolector de nivel de tóner cada 4 horas
Captura niveles CMYK y detecta alertas de tóner bajo/agotado
"""
import logging
from datetime import datetime
from typing import List, Optional

from ..database.connection import get_db
from ..collectors.snmp_client import get_snmp_client
from ..services.toner_processor import process_toner_reading, check_toner_alerts

logger = logging.getLogger(__name__)


def collect_toner() -> dict:
    """
    Ejecuta la recolección de nivel de tóner para todas las impresoras activas
    
    Returns:
        dict con estadísticas de la ejecución
    """
    logger.info("Iniciando recolección de nivel de tóner...")
    
    db = get_db()
    cursor = db.cursor()
    
    # Obtener impresoras activas con monitoreo de tóner habilitado
    cursor.execute("""
        SELECT 
            p.id, p.printer_code, p.ip_address, p.brand, p.profile,
            p.toner_unit_type,
            p.snmp_community, p.snmp_version,
            l.name as location_name
        FROM printers p
        LEFT JOIN locations l ON p.location_id = l.id
        WHERE p.is_capture_active = 1 
          AND p.status IN ('active', 'maintenance')
          AND p.monitor_toner = 1
        ORDER BY p.printer_code
    """)
    
    printers = cursor.fetchall()
    total_printers = len(printers)
    successful = 0
    failed = 0
    alerts_generated = 0
    errors = []
    
    if total_printers == 0:
        logger.warning("No hay impresoras con monitoreo de tóner activo")
        return {
            'total_printers': 0,
            'successful': 0,
            'failed': 0,
            'alerts_generated': 0,
            'errors': ['No hay impresoras configuradas para tóner']
        }
    
    snmp_source = 'local_snmp'
    
    for printer in printers:
        printer_id = printer['id']
        printer_code = printer['printer_code']
        ip_address = printer['ip_address']
        brand = printer['brand']
        profile = printer['profile']
        unit_type = printer['toner_unit_type'] or 'percent'
        community = printer['snmp_community'] or 'public'
        version = printer['snmp_version'] or 'v2c'
        location = printer['location_name'] or 'Sin ubicación'
        
        try:
            client = get_snmp_client(
                source=snmp_source,
                community=community,
                version=version,
                timeout=5,
                retries=2
            )
            
            data = client.collect_printer_data(
                printer_id=printer_id,
                printer_code=printer_code,
                ip_address=ip_address,
                brand=brand,
                profile=profile
            )
            
            if data and (data.toner_black_level is not None or 
                        data.toner_cyan_level is not None):
                # Procesar lectura de tóner
                result = process_toner_reading(data)
                
                if result['success']:
                    successful += 1
                    
                    # Verificar alertas de tóner
                    alert_result = check_toner_alerts(db, printer_id, data, unit_type)
                    if alert_result.get('alerts_generated', 0) > 0:
                        alerts_generated += alert_result['alerts_generated']
                        logger.warning(
                            f"⚠ {printer_code}: {alert_result['alerts_generated']} "
                            f"alertas de tóner generadas"
                        )
                    
                    # Log detallado de niveles
                    levels = []
                    if data.toner_black_level:
                        pct = (data.toner_black_level / data.toner_black_max * 100) if data.toner_black_max else 0
                        levels.append(f"K={pct:.0f}%")
                    if data.toner_cyan_level:
                        pct = (data.toner_cyan_level / data.toner_cyan_max * 100) if data.toner_cyan_max else 0
                        levels.append(f"C={pct:.0f}%")
                    if data.toner_magenta_level:
                        pct = (data.toner_magenta_level / data.toner_magenta_max * 100) if data.toner_magenta_max else 0
                        levels.append(f"M={pct:.0f}%")
                    if data.toner_yellow_level:
                        pct = (data.toner_yellow_level / data.toner_yellow_max * 100) if data.toner_yellow_max else 0
                        levels.append(f"Y={pct:.0f}%")
                    
                    logger.debug(f"✓ {printer_code}: {', '.join(levels)}")
                else:
                    failed += 1
                    error_msg = result.get('error', 'Error al procesar')
                    errors.append({'printer_code': printer_code, 'error': error_msg})
                    logger.error(f"✗ {printer_code}: {error_msg}")
            else:
                failed += 1
                errors.append({
                    'printer_code': printer_code,
                    'error': 'No se obtuvieron datos de tóner'
                })
                logger.error(f"✗ {printer_code}: No se obtuvieron datos de tóner")
            
        except Exception as e:
            failed += 1
            error_msg = f"Excepción: {str(e)}"
            errors.append({'printer_code': printer_code, 'error': error_msg})
            logger.error(f"✗ {printer_code}: {error_msg}", exc_info=True)
    
    logger.info(
        f"Recolección de tóner completada: "
        f"{successful}/{total_printers} exitosas, {alerts_generated} alertas"
    )
    
    return {
        'total_printers': total_printers,
        'successful': successful,
        'failed': failed,
        'alerts_generated': alerts_generated,
        'errors': errors,
        'timestamp': datetime.now().isoformat()
    }
