"""
Modelo de Usuario
"""

import bcrypt
from typing import Optional, Dict, Any


class User:
    """Clase para manejar usuarios sin ORM"""
    
    def __init__(self, id: int, username: str, full_name: str, role: str, 
                 email: Optional[str] = None, is_active: bool = True):
        self.id = id
        self.username = username
        self.full_name = full_name
        self.role = role
        self.email = email
        self.is_active = is_active
    
    @property
    def is_authenticated(self):
        return True
    
    @property
    def is_anonymous(self):
        return False
    
    @property
    def is_admin(self):
        return self.role in ['superadmin', 'admin']
    
    @property
    def is_operator(self):
        return self.role in ['superadmin', 'admin', 'operator']
    
    def get_id(self):
        return str(self.id)
    
    @classmethod
    def from_row(cls, row):
        """Crear instancia desde una fila de DB"""
        if row is None:
            return None
        return cls(
            id=row['id'],
            username=row['username'],
            full_name=row['full_name'],
            role=row['role'],
            email=row['email'],
            is_active=bool(row['is_active'])
        )
    
    @classmethod
    def get_by_id(cls, user_id: int):
        """Obtener usuario por ID"""
        from app.database import query_db
        
        row = query_db(
            "SELECT * FROM users WHERE id = ? AND is_active = 1",
            (user_id,),
            one=True
        )
        return cls.from_row(row)
    
    @classmethod
    def get_by_username(cls, username: str):
        """Obtener usuario por username"""
        from app.database import query_db
        
        row = query_db(
            "SELECT * FROM users WHERE username = ? AND is_active = 1",
            (username,),
            one=True
        )
        return cls.from_row(row)
    
    @classmethod
    def authenticate(cls, username: str, password: str) -> Optional['User']:
        """Autenticar usuario con contraseña"""
        from app.database import query_db
        
        row = query_db(
            "SELECT * FROM users WHERE username = ? AND is_active = 1",
            (username,),
            one=True
        )
        
        if not row:
            return None
        
        # Verificar contraseña con bcrypt
        password_hash = row['password_hash']
        if bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8')):
            return cls.from_row(row)
        
        return None
    
    @classmethod
    def create(cls, username: str, password: str, full_name: str, role: str,
               email: Optional[str] = None) -> int:
        """Crear nuevo usuario"""
        from app.database import execute_db
        
        # Hash de contraseña con bcrypt
        password_hash = bcrypt.hashpw(
            password.encode('utf-8'), 
            bcrypt.gensalt(rounds=12)
        ).decode('utf-8')
        
        user_id = execute_db(
            """INSERT INTO users (username, password_hash, full_name, role, email)
               VALUES (?, ?, ?, ?, ?)""",
            (username, password_hash, full_name, role, email)
        )
        
        return user_id
    
    @classmethod
    def update_last_login(cls, user_id: int, ip_address: str):
        """Actualizar último login"""
        from app.database import execute_db
        from datetime import datetime
        
        execute_db(
            """UPDATE users 
               SET last_login_at = strftime('%Y-%m-%d %H:%M:%S','now','localtime'),
                   last_login_ip = ?
               WHERE id = ?""",
            (ip_address, user_id)
        )
    
    def can_access(self, module: str, action: str = 'view') -> bool:
        """Verificar permisos por rol"""
        
        # Matriz de permisos simplificada
        permissions = {
            'viewer': ['dashboard', 'charts', 'export', 'paper', 'toner'],
            'operator': ['dashboard', 'charts', 'export', 'paper', 'toner', 
                        'print_jobs', 'stock_view', 'notifications'],
            'admin': ['dashboard', 'charts', 'export', 'paper', 'toner',
                     'print_jobs', 'stock', 'notifications', 'admin_printers',
                     'admin_locations', 'audit'],
            'superadmin': ['all']
        }
        
        user_perms = permissions.get(self.role, [])
        
        if 'all' in user_perms:
            return True
        
        return module in user_perms
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir a diccionario"""
        return {
            'id': self.id,
            'username': self.username,
            'full_name': self.full_name,
            'role': self.role,
            'email': self.email,
            'is_active': self.is_active,
            'is_admin': self.is_admin,
            'is_operator': self.is_operator
        }
