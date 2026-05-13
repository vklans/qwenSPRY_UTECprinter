"""
PrintWatch Pro - Blueprint Toner
Rutas para monitoreo de niveles de tóner
"""
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from app.queries.toner_queries import (
    get_all_printers_toner_status,
    get_toner_readings_by_printer,
    get_toner_catalog,
    get_toner_alerts_count,
    create_toner_change_record
)
from app.database.connection import get_db

toner_bp = Blueprint('toner', __name__, url_prefix='/toner')


@toner_bp.route('/')
@login_required
def index():
    """Grid de tóner con barras CMYK por impresora"""
    
    db = get_db()
    printers_status = get_all_printers_toner_status(db)
    alerts_count = get_toner_alerts_count(db)
    
    return render_template('toner/index.html',
                         printers_status=printers_status,
                         alerts_count=alerts_count)


@toner_bp.route('/<int:printer_id>')
@login_required
def detail(printer_id):
    """Detalle de tóner por impresora con histórico"""
    
    days = request.args.get('days', 30, type=int)
    start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    end_date = datetime.now().strftime('%Y-%m-%d')
    
    db = get_db()
    history = get_toner_readings_by_printer(db, printer_id, start_date, end_date)
    
    # Obtener información de la impresora
    from app.models.printer import Printer
    printer = Printer.get_by_id(db, printer_id)
    
    if not printer:
        flash('Impresora no encontrada', 'error')
        return redirect(url_for('toner.index'))
    
    return render_template('toner/detail.html',
                         printer=printer,
                         history=history,
                         days=days)


@toner_bp.route('/change/<int:printer_id>', methods=['POST'])
@login_required
def change_cartridge(printer_id):
    """Registrar cambio de cartucho de tóner"""
    
    color = request.form.get('color')  # black, cyan, magenta, yellow
    new_level = request.form.get('new_level', type=int)
    notes = request.form.get('notes', '')
    
    if not color or color not in ['black', 'cyan', 'magenta', 'yellow']:
        flash('Color inválido', 'error')
        return redirect(url_for('toner.detail', printer_id=printer_id))
    
    db = get_db()
    
    # Registrar cambio en el catálogo
    create_toner_change_record(db, printer_id, color, new_level, 
                              current_user.id, notes)
    
    flash(f'Cambio de tóner {color} registrado exitosamente', 'success')
    return redirect(url_for('toner.detail', printer_id=printer_id))


@toner_bp.route('/api/status')
@login_required
def api_status():
    """API para obtener estado de tóner en tiempo real"""
    
    db = get_db()
    printers_status = get_all_printers_toner_status(db)
    alerts_count = get_toner_alerts_count(db)
    
    return jsonify({
        'printers': printers_status,
        'alerts_count': alerts_count,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })


@toner_bp.route('/api/<int:printer_id>/history')
@login_required
def api_printer_history(printer_id):
    """API para obtener histórico de tóner (gráficas)"""
    
    days = request.args.get('days', 30, type=int)
    start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    end_date = datetime.now().strftime('%Y-%m-%d')
    
    db = get_db()
    history = get_toner_readings_by_printer(db, printer_id, start_date, end_date)
    
    # Formatear para Plotly.js
    labels = [item['captured_at'] for item in history]
    black_pct = [item['black_pct'] for item in history]
    cyan_pct = [item['cyan_pct'] for item in history]
    magenta_pct = [item['magenta_pct'] for item in history]
    yellow_pct = [item['yellow_pct'] for item in history]
    
    return jsonify({
        'labels': labels,
        'datasets': {
            'black': black_pct,
            'cyan': cyan_pct,
            'magenta': magenta_pct,
            'yellow': yellow_pct
        }
    })


@toner_bp.route('/catalog')
@login_required
def catalog():
    """Catálogo de cartuchos de tóner (solo admin)"""
    
    db = get_db()
    catalog = get_toner_catalog(db, active_only=False)
    
    return render_template('toner/catalog.html', catalog=catalog)
