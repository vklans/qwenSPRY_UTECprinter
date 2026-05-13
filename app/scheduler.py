"""
Scheduler - Sistema de tareas programadas con APScheduler
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from flask import Flask
import logging

logger = logging.getLogger(__name__)

# Variable global para el scheduler
scheduler = None


def init_scheduler(app: Flask):
    """Inicializar el scheduler con la app Flask"""
    global scheduler
    
    scheduler = BackgroundScheduler()
    
    # Leer intervalos desde configuración DB (valores por defecto si no existe DB)
    try:
        from app.services.config_service import get_config
        
        counter_interval = int(get_config('collectors.counters.interval_hours', '8'))
        paper_interval = int(get_config('collectors.paper.interval_seconds', '60'))
        toner_interval = int(get_config('collectors.toner.interval_hours', '4'))
        
    except Exception:
        counter_interval = 8
        paper_interval = 60
        toner_interval = 4
    
    with app.app_context():
        # Job: Captura de contómetros cada 8 horas
        scheduler.add_job(
            func=run_counter_collection,
            trigger=IntervalTrigger(hours=counter_interval),
            id='collect_counters',
            name='Captura de contómetros SNMP',
            replace_existing=True,
            max_instances=1
        )
        
        # Job: Captura de papel cada 60 segundos (dinámico a 15s si hay alertas)
        scheduler.add_job(
            func=run_paper_collection,
            trigger=IntervalTrigger(seconds=paper_interval),
            id='collect_paper',
            name='Monitoreo de papel SNMP',
            replace_existing=True,
            max_instances=1
        )
        
        # Job: Captura de tóner cada 4 horas
        scheduler.add_job(
            func=run_toner_collection,
            trigger=IntervalTrigger(hours=toner_interval),
            id='collect_toner',
            name='Captura de niveles de tóner SNMP',
            replace_existing=True,
            max_instances=1
        )
        
        # Job: Procesamiento de notificaciones cada 30 segundos
        scheduler.add_job(
            func=process_notifications,
            trigger=IntervalTrigger(seconds=30),
            id='process_notifications',
            name='Procesar notificaciones y alertas',
            replace_existing=True,
            max_instances=1
        )
        
        # Job: Limpieza diaria de lecturas antiguas de papel (3 AM)
        scheduler.add_job(
            func=cleanup_old_data,
            trigger=CronTrigger(hour=3, minute=0),
            id='cleanup_old_data',
            name='Limpieza de datos antiguos',
            replace_existing=True,
            max_instances=1
        )
        
        # Iniciar scheduler
        scheduler.start()
        logger.info("Scheduler iniciado con jobs configurados")
        logger.info(f"  - Contómetros: cada {counter_interval} horas")
        logger.info(f"  - Papel: cada {paper_interval} segundos")
        logger.info(f"  - Tóner: cada {toner_interval} horas")


def start_collectors_only():
    """Iniciar solo los colectores sin servidor web (para modo standalone)"""
    import signal
    import sys
    import time
    from pathlib import Path
    
    # Configurar path de DB
    db_path = Path('./data/printwatch.db')
    
    if not db_path.exists():
        print(f"ERROR: Base de datos no encontrada en {db_path}")
        print("Ejecuta scripts/init_db.ps1 primero.")
        sys.exit(1)
    
    # Crear app minimal para contexto
    from app import create_app
    app = create_app(enable_collectors=False)
    
    with app.app_context():
        # Iniciar scheduler
        init_scheduler(app)
        
        print("=" * 50)
        print("PrintWatch Pro - Colectores SNMP")
        print("=" * 50)
        print("Colectores iniciados. Presiona Ctrl+C para detener.\n")
        
        # Mantener proceso corriendo
        def signal_handler(sig, frame):
            print("\nDeteniendo schedulers...")
            scheduler.shutdown(wait=False)
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        while True:
            time.sleep(1)


def run_counter_collection():
    """Ejecutar captura de contómetros"""
    from app.collectors.counter_collector import collect_all_counters
    
    try:
        logger.info("Iniciando captura de contómetros...")
        count = collect_all_counters()
        logger.info(f"Captura de contómetros completada: {count} impresoras procesadas")
    except Exception as e:
        logger.error(f"Error en captura de contómetros: {e}", exc_info=True)


def run_paper_collection():
    """Ejecutar captura de papel"""
    from app.collectors.paper_collector import collect_all_paper_levels
    
    try:
        # Verificar si hay alertas activas para reducir intervalo
        from app.services.notification_service import has_active_paper_alerts
        
        if has_active_paper_alerts():
            logger.debug("Alertas de papel activas - usando intervalo rápido (15s)")
        else:
            logger.debug("Sin alertas de papel - usando intervalo normal (60s)")
        
        count = collect_all_paper_levels()
        logger.info(f"Captura de papel completada: {count} impresoras procesadas")
    except Exception as e:
        logger.error(f"Error en captura de papel: {e}", exc_info=True)


def run_toner_collection():
    """Ejecutar captura de tóner"""
    from app.collectors.toner_collector import collect_all_toner_levels
    
    try:
        logger.info("Iniciando captura de tóner...")
        count = collect_all_toner_levels()
        logger.info(f"Captura de tóner completada: {count} impresoras procesadas")
    except Exception as e:
        logger.error(f"Error en captura de tóner: {e}", exc_info=True)


def process_notifications():
    """Procesar y crear notificaciones"""
    from app.services.notification_service import check_and_create_notifications
    
    try:
        created = check_and_create_notifications()
        if created > 0:
            logger.info(f"{created} nuevas notificaciones creadas")
    except Exception as e:
        logger.error(f"Error procesando notificaciones: {e}", exc_info=True)


def cleanup_old_data():
    """Limpiar datos antiguos según políticas de retención"""
    from app.services.cleanup_service import cleanup_old_readings, cleanup_old_notifications
    
    try:
        logger.info("Iniciando limpieza de datos antiguos...")
        
        deleted_readings = cleanup_old_readings()
        deleted_notifications = cleanup_old_notifications()
        
        logger.info(f"Limpieza completada: {deleted_readings} lecturas, "
                   f"{deleted_notifications} notificaciones eliminadas")
    except Exception as e:
        logger.error(f"Error en limpieza de datos: {e}", exc_info=True)
