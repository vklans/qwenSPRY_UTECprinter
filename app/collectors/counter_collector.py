"""
Counter Collector - Recolector de contómetros cada 8 horas
Captura: total, BN y color de cada impresora activa
"""
import logging
from datetime import datetime
from typing import List, Optional

from ..database.connection import get_db
from ..collectors.snmp_client import get_snmp_client
from ..services.processor import process_counter_reading

logger = logging.getLogger(__name__)


def collect_counters() -> dict:
    """
    Ejecuta la recolección de contómetros para todas las impresoras activas
    
    Returns:
        dict con estadísticas de la ejecución:
        - total_printers: total de impresoras a consultar
        - successful: cantidad exitosas
        - failed: cantidad fallidas
        - errors: lista de errores por impresora
    """
    logger.info("Iniciando recolección de contómetros...")
    
    db = get_db()
    cursor = db.cursor()
    
    # Obtener impresoras activas con captura habilitada
    cursor.execute("""
        SELECT 
            p.id, p.printer_code, p.ip_address, p.brand, p.profile,
            p.snmp_community, p.snmp_version,
            l.name as location_name
        FROM printers p
        LEFT JOIN locations l ON p.location_id = l.id
        WHERE p.is_capture_active = 1 
          AND p.status IN ('active', 'maintenance')
        ORDER BY p.printer_code
    """)
    
    printers = cursor.fetchall()
    total_printers = len(printers)
    successful = 0
    failed = 0
    errors = []
    
    if total_printers == 0:
        logger.warning("No hay impresoras activas para monitorear")
        return {
            'total_printers': 0,
            'successful': 0,
            'failed': 0,
            'errors': ['No hay impresoras configuradas']
        }
    
    # Obtener configuración SNMP del sistema
    snmp_source = 'local_snmp'  # Por defecto en servidor
    
    for printer in printers:
        printer_id = printer['id']
        printer_code = printer['printer_code']
        ip_address = printer['ip_address']
        brand = printer['brand']
        profile = printer['profile']
        community = printer['snmp_community'] or 'public'
        version = printer['snmp_version'] or 'v2c'
        location = printer['location_name'] or 'Sin ubicación'
        
        try:
            logger.info(f"Consultando impresora {printer_code} ({ip_address}) - {location}")
            
            # Crear cliente SNMP
            client = get_snmp_client(
                source=snmp_source,
                community=community,
                version=version,
                timeout=5,
                retries=2
            )
            
            # Recolectar datos
            data = client.collect_printer_data(
                printer_id=printer_id,
                printer_code=printer_code,
                ip_address=ip_address,
                brand=brand,
                profile=profile
            )
            
            if data and (data.total_impressions is not None):
                # Procesar y guardar lectura
                result = process_counter_reading(data)
                
                if result['success']:
                    successful += 1
                    logger.info(
                        f"✓ {printer_code}: Total={data.total_impressions}, "
                        f"BN={data.bn_impressions}, Color={data.color_impressions}"
                    )
                else:
                    failed += 1
                    error_msg = result.get('error', 'Error desconocido al procesar')
                    errors.append({
                        'printer_code': printer_code,
                        'error': error_msg
                    })
                    logger.error(f"✗ {printer_code}: {error_msg}")
            else:
                failed += 1
                error_msg = "No se obtuvieron datos del contador"
                errors.append({
                    'printer_code': printer_code,
                    'error': error_msg
                })
                logger.error(f"✗ {printer_code}: {error_msg}")
            
        except Exception as e:
            failed += 1
            error_msg = f"Excepción: {str(e)}"
            errors.append({
                'printer_code': printer_code,
                'error': error_msg
            })
            logger.error(f"✗ {printer_code}: {error_msg}", exc_info=True)
    
    # Registrar resumen en log
    logger.info(
        f"Recolección de contómetros completada: "
        f"{successful}/{total_printers} exitosas, {failed} fallidas"
    )
    
    return {
        'total_printers': total_printers,
        'successful': successful,
        'failed': failed,
        'errors': errors,
        'timestamp': datetime.now().isoformat()
    }


def test_single_printer(printer_id: int) -> dict:
    """
    Prueba de recolección para una sola impresora (debug)
    
    Args:
        printer_id: ID de la impresora a probar
    
    Returns:
        dict con los datos obtenidos o error
    """
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute("""
        SELECT 
            p.id, p.printer_code, p.ip_address, p.brand, p.profile,
            p.snmp_community, p.snmp_version,
            l.name as location_name
        FROM printers p
        LEFT JOIN locations l ON p.location_id = l.id
        WHERE p.id = ?
    """, (printer_id,))
    
    printer = cursor.fetchone()
    
    if not printer:
        return {'success': False, 'error': 'Impresora no encontrada'}
    
    community = printer['snmp_community'] or 'public'
    version = printer['snmp_version'] or 'v2c'
    
    try:
        client = get_snmp_client(
            source='local_snmp',
            community=community,
            version=version,
            timeout=5,
            retries=2
        )
        
        logger.info(f"Probando conexión SNMP con {printer['printer_code']}...")
        
        # Test de conectividad básico
        if not client.test_connection(printer['ip_address']):
            return {
                'success': False,
                'error': 'No se pudo establecer conexión SNMP'
            }
        
        # Recolectar datos completos
        data = client.collect_printer_data(
            printer_id=printer['id'],
            printer_code=printer['printer_code'],
            ip_address=printer['ip_address'],
            brand=printer['brand'],
            profile=printer['profile']
        )
        
        if data:
            return {
                'success': True,
                'data': {
                    'printer_code': data.printer_code,
                    'ip_address': data.ip_address,
                    'timestamp': data.timestamp.isoformat(),
                    'total_impressions': data.total_impressions,
                    'bn_impressions': data.bn_impressions,
                    'color_impressions': data.color_impressions,
                    'paper_level_percent': data.paper_level_percent,
                    'toner_black_pct': (
                        (data.toner_black_level / data.toner_black_max * 100)
                        if data.toner_black_max and data.toner_black_level else None
                    ),
                    'alert_code': data.alert_code,
                    'alert_description': data.alert_description
                }
            }
        else:
            return {
                'success': False,
                'error': 'No se obtuvieron datos de la impresora'
            }
    
    except Exception as e:
        logger.error(f"Error en test de impresora {printer_id}: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e)
        }
