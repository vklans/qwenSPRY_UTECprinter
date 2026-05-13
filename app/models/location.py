"""
Modelo de Ubicación
"""

from typing import Optional, Dict, Any, List


class Location:
    """Clase para manejar ubicaciones sin ORM"""
    
    def __init__(self, id: int, name: str, building: Optional[str] = None,
                 floor: Optional[str] = None, description: Optional[str] = None,
                 is_active: bool = True):
        self.id = id
        self.name = name
        self.building = building
        self.floor = floor
        self.description = description
        self.is_active = is_active
    
    @classmethod
    def from_row(cls, row):
        """Crear instancia desde una fila de DB"""
        if row is None:
            return None
        return cls(
            id=row['id'],
            name=row['name'],
            building=row['building'],
            floor=row['floor'],
            description=row['description'],
            is_active=bool(row['is_active'])
        )
    
    @classmethod
    def get_by_id(cls, location_id: int):
        """Obtener ubicación por ID"""
        from app.database import query_db
        
        row = query_db("SELECT * FROM locations WHERE id = ?", (location_id,), one=True)
        return cls.from_row(row)
    
    @classmethod
    def get_all(cls, active_only: bool = False) -> List['Location']:
        """Obtener todas las ubicaciones"""
        from app.database import query_db
        
        query = "SELECT * FROM locations"
        if active_only:
            query += " WHERE is_active = 1"
        query += " ORDER BY name"
        
        rows = query_db(query)
        return [cls.from_row(row) for row in rows]
    
    @classmethod
    def get_with_printer_count(cls) -> List[Dict[str, Any]]:
        """Obtener ubicaciones con cantidad de impresoras"""
        from app.database import query_db
        
        rows = query_db(
            """SELECT l.*, COUNT(p.id) as printer_count
               FROM locations l
               LEFT JOIN printers p ON l.id = p.location_id AND p.status = 'active'
               GROUP BY l.id
               ORDER BY l.name"""
        )
        
        result = []
        for row in rows:
            loc_dict = dict(row)
            loc_dict['printer_count'] = row['printer_count']
            result.append(loc_dict)
        
        return result
    
    @classmethod
    def create(cls, name: str, building: Optional[str] = None,
               floor: Optional[str] = None, description: Optional[str] = None) -> int:
        """Crear nueva ubicación"""
        from app.database import execute_db
        
        location_id = execute_db(
            """INSERT INTO locations (name, building, floor, description)
               VALUES (?, ?, ?, ?)""",
            (name, building, floor, description)
        )
        
        return location_id
    
    @classmethod
    def update(cls, location_id: int, **kwargs) -> bool:
        """Actualizar ubicación"""
        from app.database import execute_db
        
        allowed_fields = ['name', 'building', 'floor', 'description']
        
        updates = []
        values = []
        
        for field in allowed_fields:
            if field in kwargs:
                updates.append(f"{field} = ?")
                values.append(kwargs[field])
        
        if not updates:
            return False
        
        values.append(location_id)
        
        query = f"""UPDATE locations 
                    SET {', '.join(updates)}, 
                        updated_at = strftime('%Y-%m-%d %H:%M:%S','now','localtime')
                    WHERE id = ?"""
        
        execute_db(query, tuple(values))
        return True
    
    @classmethod
    def toggle_active(cls, location_id: int) -> bool:
        """Activar/desactivar ubicación"""
        from app.database import execute_db
        
        execute_db(
            """UPDATE locations 
               SET is_active = NOT is_active,
                   updated_at = strftime('%Y-%m-%d %H:%M:%S','now','localtime')
               WHERE id = ?""",
            (location_id,)
        )
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir a diccionario"""
        return {
            'id': self.id,
            'name': self.name,
            'building': self.building,
            'floor': self.floor,
            'description': self.description,
            'is_active': self.is_active
        }
