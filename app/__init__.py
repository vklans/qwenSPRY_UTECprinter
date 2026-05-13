"""
PrintWatch Pro - Aplicación principal
Sistema de monitoreo de impresoras con SNMP
"""

import os
from pathlib import Path
from flask import Flask, g, redirect, url_for
from flask_login import LoginManager, current_user
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def create_app(enable_collectors=True):
    """Factory pattern para crear la aplicación Flask"""
    
    app = Flask(__name__)
    
    # Configuración básica
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key-change-in-production')
    app.config['DATABASE_PATH'] = os.getenv('PRINTWATCH_DB_PATH', './data/printwatch.db')
    app.config['ENVIRONMENT'] = os.getenv('PRINTWATCH_ENV', 'development')
    app.config['SNMP_SOURCE'] = os.getenv('PRINTWATCH_SNMP_SOURCE', 'api')
    app.config['SNMP_API_URL'] = os.getenv('PRINTWATCH_API_URL', 'http://localhost:5000')
    
    # Configurar logging
    if app.config['ENVIRONMENT'] == 'production':
        app.config['DEBUG'] = False
    else:
        app.config['DEBUG'] = True
    
    # Inicializar extensiones
    init_extensions(app)
    
    # Registrar blueprints
    register_blueprints(app)
    
    # Configurar base de datos
    setup_database(app)
    
    # Inicializar schedulers si está habilitado
    if enable_collectors:
        from app.scheduler import init_scheduler
        init_scheduler(app)
    
    # Context processors
    @app.context_processor
    def inject_globals():
        """Inyectar variables globales en todos los templates"""
        from app.services.notification_service import get_active_notifications_count
        
        return {
            'current_user': current_user,
            'active_notifications_count': get_active_notifications_count() if current_user.is_authenticated else 0,
            'app_name': 'PrintWatch Pro',
            'environment': app.config['ENVIRONMENT']
        }
    
    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return redirect(url_for('dashboard_bp.index'))
    
    @app.errorhandler(403)
    def forbidden_error(error):
        return redirect(url_for('dashboard_bp.index'))
    
    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f'Error interno: {error}')
        return "Error interno del servidor", 500
    
    return app


def init_extensions(app):
    """Inicializar extensiones de Flask"""
    
    # CSRF Protection
    csrf = CSRFProtect()
    csrf.init_app(app)
    
    # Login Manager
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth_bp.login'
    login_manager.login_message_category = 'info'
    
    @login_manager.user_loader
    def load_user(user_id):
        from app.models.user import User
        return User.get_by_id(int(user_id))
    
    # Rate Limiter
    limiter = Limiter(
        key_func=get_remote_address,
        app=app,
        default_limits=["200 per day", "50 per hour"],
        storage_uri="memory://"
    )
    
    # Guardar referencias en app para acceso global
    app.extensions['csrf'] = csrf
    app.extensions['login_manager'] = login_manager
    app.extensions['limiter'] = limiter


def register_blueprints(app):
    """Registrar todos los blueprints de la aplicación"""
    
    from app.blueprints.auth import auth_bp
    from app.blueprints.dashboard import dashboard_bp
    from app.blueprints.paper import paper_bp
    from app.blueprints.toner import toner_bp
    from app.blueprints.stock.routes_paper import stock_paper_bp
    from app.blueprints.stock.routes_toner import stock_toner_bp
    from app.blueprints.print_jobs import print_jobs_bp
    from app.blueprints.notifications import notifications_bp
    from app.blueprints.charts import charts_bp
    from app.blueprints.export import export_bp
    from app.blueprints.admin.routes_printers import admin_printers_bp
    from app.blueprints.admin.routes_locations import admin_locations_bp
    from app.blueprints.admin.routes_users import admin_users_bp
    from app.blueprints.admin.routes_config import admin_config_bp
    from app.blueprints.admin.routes_audit import admin_audit_bp
    
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
    app.register_blueprint(paper_bp, url_prefix='/paper')
    app.register_blueprint(toner_bp, url_prefix='/toner')
    app.register_blueprint(stock_paper_bp, url_prefix='/stock/paper')
    app.register_blueprint(stock_toner_bp, url_prefix='/stock/toner')
    app.register_blueprint(print_jobs_bp, url_prefix='/print-jobs')
    app.register_blueprint(notifications_bp, url_prefix='/notifications')
    app.register_blueprint(charts_bp, url_prefix='/charts')
    app.register_blueprint(export_bp, url_prefix='/export')
    app.register_blueprint(admin_printers_bp, url_prefix='/admin/printers')
    app.register_blueprint(admin_locations_bp, url_prefix='/admin/locations')
    app.register_blueprint(admin_users_bp, url_prefix='/admin/users')
    app.register_blueprint(admin_config_bp, url_prefix='/admin/config')
    app.register_blueprint(admin_audit_bp, url_prefix='/admin/audit')
    
    # Redirección raíz a dashboard
    @app.route('/')
    def index():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard_bp.index'))
        return redirect(url_for('auth_bp.login'))


def setup_database(app):
    """Configurar conexión a base de datos"""
    
    @app.before_request
    def before_request():
        """Crear conexión a DB antes de cada request"""
        g.db = None
    
    @app.teardown_request
    def teardown_request(exception):
        """Cerrar conexión a DB después de cada request"""
        db = getattr(g, 'db', None)
        if db is not None:
            db.close()
    
    @app.before_first_request
    def before_first_request():
        """Verificar que la BD existe y está migrada"""
        from app.database.migrations import ensure_migrated
        
        db_path = app.config['DATABASE_PATH']
        if not Path(db_path).exists():
            app.logger.warning(f"Base de datos no encontrada en {db_path}")
            app.logger.warning("Ejecuta scripts/init_db.ps1 para inicializar")
        else:
            ensure_migrated(db_path)
