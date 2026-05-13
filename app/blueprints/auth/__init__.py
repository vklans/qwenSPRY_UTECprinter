"""
Blueprint de Autenticación
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required
from functools import wraps

auth_bp = Blueprint('auth_bp', __name__, template_folder='../../templates/auth')


def admin_required(f):
    """Decorator para requerir rol admin o superior"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask_login import current_user
        
        if not current_user.is_authenticated:
            return redirect(url_for('auth_bp.login'))
        
        if not current_user.is_admin:
            flash('Acceso denegado. Se requiere rol de administrador.', 'error')
            return redirect(url_for('dashboard_bp.index'))
        
        return f(*args, **kwargs)
    
    return decorated_function


def superadmin_required(f):
    """Decorator para requerir rol superadmin"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask_login import current_user
        
        if not current_user.is_authenticated:
            return redirect(url_for('auth_bp.login'))
        
        if current_user.role != 'superadmin':
            flash('Acceso denegado. Se requiere rol de superadministrador.', 'error')
            return redirect(url_for('dashboard_bp.index'))
        
        return f(*args, **kwargs)
    
    return decorated_function


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Página de login"""
    from flask_login import current_user
    
    # Si ya está logueado, redirigir al dashboard
    if current_user.is_authenticated:
        return redirect(url_for('dashboard_bp.index'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        remember = request.form.get('remember', False)
        
        if not username or not password:
            flash('Por favor ingrese usuario y contraseña.', 'warning')
            return render_template('auth/login.html')
        
        # Intentar autenticar
        from app.models.user import User
        
        user = User.authenticate(username, password)
        
        if user:
            login_user(user, remember=remember)
            
            # Actualizar último login
            User.update_last_login(user.id, request.remote_addr)
            
            flash(f'Bienvenido, {user.full_name}!', 'success')
            
            # Redirigir a la página que intentaba acceder o al dashboard
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('dashboard_bp.index'))
        else:
            flash('Usuario o contraseña incorrectos.', 'error')
    
    return render_template('auth/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    """Cerrar sesión"""
    logout_user()
    flash('Sesión cerrada exitosamente.', 'info')
    return redirect(url_for('auth_bp.login'))


@auth_bp.route('/setup', methods=['GET', 'POST'])
def setup():
    """Configuración inicial - crear primer usuario superadmin"""
    from flask import current_app
    import sqlite3
    from pathlib import Path
    
    db_path = Path(current_app.config['DATABASE_PATH'])
    
    # Verificar si ya existe algún usuario
    if db_path.exists():
        conn = sqlite3.connect(db_path)
        cursor = conn.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
        conn.close()
        
        if count > 0:
            flash('El sistema ya está configurado. Inicie sesión con su usuario.', 'info')
            return redirect(url_for('auth_bp.login'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        password_confirm = request.form.get('password_confirm', '')
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip()
        
        # Validaciones
        errors = []
        
        if not username or len(username) < 3:
            errors.append('El usuario debe tener al menos 3 caracteres.')
        
        if not password or len(password) < 8:
            errors.append('La contraseña debe tener al menos 8 caracteres.')
        
        if password != password_confirm:
            errors.append('Las contraseñas no coinciden.')
        
        if not full_name:
            errors.append('El nombre completo es obligatorio.')
        
        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('auth/setup.html')
        
        # Crear usuario superadmin
        from app.models.user import User
        
        try:
            user_id = User.create(
                username=username,
                password=password,
                full_name=full_name,
                role='superadmin',
                email=email if email else None
            )
            
            flash(f'Usuario "{username}" creado exitosamente. Ahora puede iniciar sesión.', 'success')
            return redirect(url_for('auth_bp.login'))
            
        except Exception as e:
            flash(f'Error al crear usuario: {str(e)}', 'error')
    
    return render_template('auth/setup.html')
