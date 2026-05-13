"""
PrintWatch Pro - Blueprint Notifications
Rutas para sistema de notificaciones y popups
"""
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime
from app.queries.notification_queries import (
    get_active_notifications,
    get_notification_history,
    dismiss_notification,
    dismiss_all_notifications,
    resolve_notification,
    get_notifications_count
)
from app.database.connection import get_db

notifications_bp = Blueprint('notifications', __name__, url_prefix='/notifications')


@notifications_bp.route('/history')
@login_required
def history():
    """Historial completo de notificaciones con filtros"""
    
    # Filtros
    printer_id = request.args.get('printer', type=int)
    notification_type = request.args.get('type')
    severity = request.args.get('severity')
    start_date = request.args.get('start', (datetime.now().replace(day=1)).strftime('%Y-%m-%d'))
    end_date = request.args.get('end', datetime.now().strftime('%Y-%m-%d'))
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    db = get_db()
    notifications = get_notification_history(db, printer_id, notification_type, severity, 
                                            start_date, end_date, page, per_page)
    
    return render_template('notifications/history.html',
                         notifications=notifications,
                         selected_printer=printer_id,
                         selected_type=notification_type,
                         selected_severity=severity,
                         start_date=start_date,
                         end_date=end_date)


@notifications_bp.route('/api/active')
@login_required
def api_active():
    """API para polling de notificaciones activas (cada 5s)"""
    
    db = get_db()
    active = get_active_notifications(db)
    count = get_notifications_count(db, active_only=True)
    
    # Formatear para frontend
    formatted = []
    for notif in active:
        formatted.append({
            'id': notif['id'],
            'printer_code': notif['printer_code'],
            'printer_name': notif['printer_name'],
            'location_name': notif['location_name'],
            'type': notif['notification_type'],
            'severity': notif['severity'],
            'title': notif['title'],
            'message': notif['message'],
            'created_at': notif['created_at'],
            'is_new': True  # Para animación en frontend
        })
    
    return jsonify({
        'notifications': formatted,
        'count': count,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })


@notifications_bp.route('/<int:notification_id>/dismiss', methods=['POST'])
@login_required
def dismiss(notification_id):
    """Cerrar notificación (sin resolver)"""
    
    db = get_db()
    dismiss_notification(db, notification_id, current_user.id)
    
    return jsonify({'success': True})


@notifications_bp.route('/dismiss-all', methods=['POST'])
@login_required
def dismiss_all():
    """Cerrar todas las notificaciones visibles"""
    
    db = get_db()
    dismissed_count = dismiss_all_notifications(db, current_user.id)
    
    return jsonify({'success': True, 'dismissed_count': dismissed_count})


@notifications_bp.route('/<int:notification_id>/resolve', methods=['POST'])
@login_required
def resolve(notification_id):
    """Marcar notificación como resuelta (solo admin/operator)"""
    
    if current_user.role not in ['admin', 'operator', 'superadmin']:
        return jsonify({'success': False, 'error': 'Permisos insuficientes'}), 403
    
    notes = request.form.get('notes', '')
    
    db = get_db()
    resolve_notification(db, notification_id, current_user.id, notes)
    
    return jsonify({'success': True})
