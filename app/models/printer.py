"""
Modelo de Impresora
"""

from typing import Optional, Dict, Any, List


class Printer:
    """Clase para manejar impresoras sin ORM"""
    
    def __init__(self, id: int, printer_code: str, name: str, ip_address: str,
                 brand: str, profile: str, location_id: Optional[int] = None,
                 model: Optional[str] = None, serial_number: Optional[str] = None,
                 status: str = 'active', is_capture_active: bool = True,
                 monitor_paper: bool = True, monitor_toner: bool = True,
                 paper_capacity: int = 500, toner_unit_type: str = 'percent'):
        self.id = id
        self.printer_code = printer_code
        self.name = name
        self.ip_address = ip_address
        self.brand = brand
        self.profile = profile
        self.location_id = location_id
        self.model = model
        self.serial_number = serial_number
        self.status = status
        self.is_capture_active = is_capture_active
        self.monitor_paper = monitor_paper
        self.monitor_toner = monitor_toner
        self.paper_capacity = paper_capacity
        self.toner_unit_type = toner_unit_type
    
    @property
    def is_ricoh(self):
        return self.brand == 'RICOH'
    
    @property
    def is_kyocera(self):
        return self.brand == 'KYOCERA'
    
    @property
    def is_color(self):
        return self.profile == 'ricoh_color'
    
    @classmethod
    def from_row(cls, row):
        """Crear instancia desde una fila de DB"""
        if row is None:
            return None
        return cls(
            id=row['id'],
            printer_code=row['printer_code'],
            name=row['name'],
            ip_address=row['ip_address'],
            brand=row['brand'],
            profile=row['profile'],
            location_id=row['location_id'],
            model=row['model'],
            serial_number=row['serial_number'],
            status=row['status'],
            is_capture_active=bool(row['is_capture_active']),
            monitor_paper=bool(row['monitor_paper']),
            monitor_toner=bool(row['monitor_toner']),
            paper_capacity=row['paper_capacity'],
            toner_unit_type=row['toner_unit_type']
        )
    
    @classmethod
    def get_by_id(cls, printer_id: int):
        """Obtener impresora por ID"""
        from app.database import query_db
        
        row = query_db("SELECT * FROM printers WHERE id = ?", (printer_id,), one=True)
        return cls.from_row(row)
    
    @classmethod
    def get_by_code(cls, printer_code: str):
        """Obtener impresora por código"""
        from app.database import query_db
        
        row = query_db("SELECT * FROM printers WHERE printer_code = ?", (printer_code,), one=True)
        return cls.from_row(row)
    
    @classmethod
    def get_all(cls, active_only: bool = False) -> List['Printer']:
        """Obtener todas las impresoras"""
        from app.database import query_db
        
        query = "SELECT * FROM printers"
        if active_only:
            query += " WHERE status = 'active' AND is_capture_active = 1"
        query += " ORDER BY name"
        
        rows = query_db(query)
        return [cls.from_row(row) for row in rows]
    
    @classmethod
    def get_active_monitored(cls) -> List['Printer']:
        """Obtener impresoras activas y monitoreadas"""
        from app.database import query_db
        
        rows = query_db(
            """SELECT * FROM printers 
               WHERE status = 'active' AND is_capture_active = 1
               ORDER BY name"""
        )
        return [cls.from_row(row) for row in rows]
    
    @classmethod
    def create(cls, printer_code: str, name: str, ip_address: str, brand: str,
               profile: str, location_id: Optional[int] = None, **kwargs) -> int:
        """Crear nueva impresora"""
        from app.database import execute_db
        
        printer_id = execute_db(
            """INSERT INTO printers 
               (printer_code, name, ip_address, brand, profile, location_id, 
                model, serial_number, status, is_capture_active, 
                monitor_paper, monitor_toner, paper_capacity, toner_unit_type)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                printer_code, name, ip_address, brand, profile, location_id,
                kwargs.get('model'), kwargs.get('serial_number'),
                kwargs.get('status', 'active'),
                kwargs.get('is_capture_active', True),
                kwargs.get('monitor_paper', True),
                kwargs.get('monitor_toner', True),
                kwargs.get('paper_capacity', 500),
                kwargs.get('toner_unit_type', 'percent')
            )
        )
        
        return printer_id
    
    @classmethod
    def update(cls, printer_id: int, **kwargs) -> bool:
        """Actualizar impresora"""
        from app.database import execute_db
        
        # Construir UPDATE dinámicamente solo con campos proporcionados
        allowed_fields = [
            'name', 'ip_address', 'brand', 'profile', 'location_id',
            'model', 'serial_number', 'status', 'is_capture_active',
            'monitor_paper', 'monitor_toner', 'paper_capacity', 
            'toner_unit_type', 'notes'
        ]
        
        updates = []
        values = []
        
        for field in allowed_fields:
            if field in kwargs:
                updates.append(f"{field} = ?")
                values.append(kwargs[field])
        
        if not updates:
            return False
        
        values.append(printer_id)
        
        query = f"""UPDATE printers 
                    SET {', '.join(updates)}, 
                        updated_at = strftime('%Y-%m-%d %H:%M:%S','now','localtime')
                    WHERE id = ?"""
        
        execute_db(query, tuple(values))
        return True
    
    @classmethod
    def delete(cls, printer_id: int) -> bool:
        """Eliminar impresora (soft delete cambiando status)"""
        from app.database import execute_db
        
        execute_db(
            """UPDATE printers 
               SET status = 'retired', 
                   updated_at = strftime('%Y-%m-%d %H:%M:%S','now','localtime')
               WHERE id = ?""",
            (printer_id,)
        )
        return True
    
    @classmethod
    def get_with_location(cls) -> List[Dict[str, Any]]:
        """Obtener impresoras con información de ubicación"""
        from app.database import query_db
        
        rows = query_db(
            """SELECT p.*, l.name as location_name, l.building, l.floor
               FROM printers p
               LEFT JOIN locations l ON p.location_id = l.id
               ORDER BY p.name"""
        )
        
        result = []
        for row in rows:
            printer_dict = dict(row)
            printer_dict['location'] = {
                'id': row['location_id'],
                'name': row['location_name'],
                'building': row['building'],
                'floor': row['floor']
            } if row['location_id'] else None
            result.append(printer_dict)
        
        return result
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir a diccionario"""
        return {
            'id': self.id,
            'printer_code': self.printer_code,
            'name': self.name,
            'ip_address': self.ip_address,
            'brand': self.brand,
            'profile': self.profile,
            'location_id': self.location_id,
            'model': self.model,
            'serial_number': self.serial_number,
            'status': self.status,
            'is_capture_active': self.is_capture_active,
            'monitor_paper': self.monitor_paper,
            'monitor_toner': self.monitor_toner,
            'paper_capacity': self.paper_capacity,
            'toner_unit_type': self.toner_unit_type,
            'is_ricoh': self.is_ricoh,
            'is_kyocera': self.is_kyocera,
            'is_color': self.is_color
        }
