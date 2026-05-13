"""
PrintWatch Pro - Blueprint Paper
Rutas para monitoreo de papel en tiempo real
"""
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime
from app.queries.paper_queries import (
    get_all_printers_paper_status,
    get_paper_events,
    get_paper_events_summary,
    resolve_paper_event,
    get_printer_paper_history
)
from app.services.paper_processor import create_paper_event, check_paper_alerts
from app.database.connection import get_db

paper_bp = Blueprint('paper', __name__, url_prefix='/paper')


@paper_bp.route('/')
@login_required
def index():
    """Vista operativa de papel con grid en tiempo real"""
    
    db = get_db()
    printers_status = get_all_printers_paper_status(db)
    
    # Resumen de estados
    summary = {
        'ok': sum(1 for p in printers_status if p['status'] == 'OK'),
        'low': sum(1 for p in printers_status if p['status'] == 'LOW'),
        'critical': sum(1 for p in printers_status if p['status'] == 'CRITICAL'),
        'empty': sum(1 for p in printers_status if p['status'] == 'EMPTY'),
        'offline': sum(1 for p in printers_status if p['status'] == 'OFFLINE')
    }
    
    return render_template('paper/index.html',
                         printers_status=printers_status,
                         summary=summary)


@paper_bp.route('/events')
@login_required
def events():
    """Historial de eventos de papel con filtros"""
    
    # Filtros
    printer_id = request.args.get('printer', type=int)
    event_type = request.args.get('type')
    start_date = request.args.get('start', (datetime.now().replace(day=1)).strftime('%Y-%m-%d'))
    end_date = request.args.get('end', datetime.now().strftime('%Y-%m-%d'))
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    db = get_db()
    events = get_paper_events(db, printer_id, event_type, start_date, end_date, page, per_page)
    summary = get_paper_events_summary(db, printer_id, event_type, start_date, end_date)
    
    return render_template('paper/events.html',
                         events=events,
                         summary=summary,
                         selected_printer=printer_id,
                         selected_type=event_type,
                         start_date=start_date,
                         end_date=end_date)


@paper_bp.route('/refill/<int:printer_id>', methods=['POST'])
@login_required
def refill(printer_id):
    """Registrar refill manual de papel"""
    
    quantity_packs = request.form.get('quantity_packs', type=int)
    notes = request.form.get('notes', '')
    
    if not quantity_packs or quantity_packs <= 0:
        flash('Cantidad inválida', 'error')
        return redirect(url_for('paper.index'))
    
    db = get_db()
    
    # Registrar evento de refill
    create_paper_event(db, printer_id, 'PAPER_REFILLED', 
                      previous_level=0, new_level=quantity_packs * 500,
                      performed_by=current_user.id, notes=notes)
    
    # Registrar movimiento de stock automático
    from app.services.stock_service import create_printer_refill_movement
    create_printer_refill_movement(db, printer_id, quantity_packs, current_user.id, notes)
    
    flash('Refill registrado exitosamente', 'success')
    return redirect(url_for('paper.index'))


@paper_bp.route('/api/status')
@login_required
def api_status():
    """API para obtener estado de papel en tiempo real (polling)"""
    
    db = get_db()
    printers_status = get_all_printers_paper_status(db)
    
    # Obtener alertas activas para notificaciones
    active_alerts = [p for p in printers_status if p['status'] in ['LOW', 'CRITICAL', 'EMPTY']]
    
    return jsonify({
        'printers': printers_status,
        'active_alerts': active_alerts,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })


@paper_bp.route('/api/<int:printer_id>/history')
@login_required
def api_printer_history(printer_id):
    """API para obtener histórico de papel de una impresora"""
    
    days = request.args.get('days', 7, type=int)
    start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    end_date = datetime.now().strftime('%Y-%m-%d')
    
    db = get_db()
    history = get_printer_paper_history(db, printer_id, start_date, end_date)
    
    # Formatear para gráfica
    labels = [item['captured_at'] for item in history]
    levels = [item['level_percent'] for item in history]
    sheets = [item['sheets_available'] for item in history]
    
    return jsonify({
        'labels': labels,
        'level_percent': levels,
        'sheets_available': sheets
    })
