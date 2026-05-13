"""
Services Package - Lógica de negocio
"""
from .processor import process_counter_reading, calculate_daily_consumption, detect_counter_anomaly
from .paper_processor import process_paper_reading, check_paper_alerts
from .toner_processor import process_toner_reading, check_toner_alerts
from .notification_service import (
    create_notification,
    get_active_notifications,
    dismiss_notification,
    resolve_notification,
    auto_resolve_paper_alerts,
    get_notification_history
)

__all__ = [
    'process_counter_reading',
    'calculate_daily_consumption',
    'detect_counter_anomaly',
    'process_paper_reading',
    'check_paper_alerts',
    'process_toner_reading',
    'check_toner_alerts',
    'create_notification',
    'get_active_notifications',
    'dismiss_notification',
    'resolve_notification',
    'auto_resolve_paper_alerts',
    'get_notification_history',
]
