"""
PrintWatch Pro - Blueprint Dashboard
Rutas para el dashboard principal con KPIs y resúmenes
"""
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
from datetime import datetime, timedelta
from app.queries.counter_queries import (
    get_consumption_summary,
    get_consumption_by_printer,
    get_consumption_by_location,
    get_today_consumption,
    get_consumption_trend
)
from app.queries.paper_queries import get_all_printers_paper_status, get_paper_events_summary
from app.queries.toner_queries import get_all_printers_toner_status, get_toner_alerts_count
from app.database.connection import get_db

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')


@dashboard_bp.route('/')
@login_required
def index():
    """Dashboard principal con KPIs y gráficas"""
    
    # Obtener filtros de la URL
    start_date = request.args.get('start', (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
    end_date = request.args.get('end', datetime.now().strftime('%Y-%m-%d'))
    printer_id = request.args.get('printer', type=int)
    location_id = request.args.get('location', type=int)
    
    db = get_db()
    
    # KPIs principales
    summary = get_consumption_summary(db, start_date, end_date, printer_id, location_id)
    
    # Consumo por impresora (top 10)
    by_printer = get_consumption_by_printer(db, start_date, end_date, location_id, limit=10)
    
    # Consumo por ubicación (top 10)
    by_location = get_consumption_by_location(db, start_date, end_date, limit=10)
    
    # Consumo de hoy
    today = get_today_consumption(db, printer_id, location_id)
    
    # Tendencia de consumo (últimos 30 días)
    trend = get_consumption_trend(db, end_date, days=30, printer_id=printer_id, location_id=location_id)
    
    # Estado actual de papel
    paper_status = get_all_printers_paper_status(db)
    paper_summary = {
        'ok': sum(1 for p in paper_status if p['status'] == 'OK'),
        'low': sum(1 for p in paper_status if p['status'] == 'LOW'),
        'critical': sum(1 for p in paper_status if p['status'] == 'CRITICAL'),
        'empty': sum(1 for p in paper_status if p['status'] == 'EMPTY'),
        'offline': sum(1 for p in paper_status if p['status'] == 'OFFLINE')
    }
    
    # Estado actual de tóner
    toner_status = get_all_printers_toner_status(db)
    toner_alerts = get_toner_alerts_count(db)
    
    # Contar alertas activas
    active_alerts = sum(1 for p in paper_status if p['status'] not in ['OK', 'OFFLINE'])
    active_alerts += toner_alerts.get('total', 0)
    
    return render_template('dashboard/index.html',
                         summary=summary,
                         by_printer=by_printer,
                         by_location=by_location,
                         today=today,
                         trend=trend,
                         paper_status=paper_status,
                         paper_summary=paper_summary,
                         toner_status=toner_status,
                         toner_alerts=toner_alerts,
                         active_alerts=active_alerts,
                         start_date=start_date,
                         end_date=end_date,
                         selected_printer=printer_id,
                         selected_location=location_id)


@dashboard_bp.route('/api/kpis')
@login_required
def api_kpis():
    """API para obtener KPIs en tiempo real (AJAX)"""
    
    start_date = request.args.get('start', (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
    end_date = request.args.get('end', datetime.now().strftime('%Y-%m-%d'))
    printer_id = request.args.get('printer', type=int)
    location_id = request.args.get('location', type=int)
    
    db = get_db()
    summary = get_consumption_summary(db, start_date, end_date, printer_id, location_id)
    
    return jsonify({
        'total_impressions': summary.get('total_impressions', 0),
        'bn_impressions': summary.get('bn_impressions', 0),
        'color_impressions': summary.get('color_impressions', 0),
        'reading_intervals': summary.get('reading_intervals', 0),
        'avg_daily_consumption': summary.get('avg_daily_consumption', 0)
    })


@dashboard_bp.route('/api/trend')
@login_required
def api_trend():
    """API para obtener tendencia de consumo (gráficas)"""
    
    days = request.args.get('days', 30, type=int)
    printer_id = request.args.get('printer', type=int)
    location_id = request.args.get('location', type=int)
    
    db = get_db()
    end_date = datetime.now().strftime('%Y-%m-%d')
    trend = get_consumption_trend(db, end_date, days=days, printer_id=printer_id, location_id=location_id)
    
    # Formatear para Chart.js/Plotly
    labels = [item['date'] for item in trend]
    total_data = [item['total'] for item in trend]
    bn_data = [item['bn'] for item in trend]
    color_data = [item['color'] for item in trend]
    
    return jsonify({
        'labels': labels,
        'datasets': [
            {'label': 'Total', 'data': total_data},
            {'label': 'B/N', 'data': bn_data},
            {'label': 'Color', 'data': color_data}
        ]
    })
