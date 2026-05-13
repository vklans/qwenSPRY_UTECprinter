"""
Base Client - Interfaz común para clientes SNMP
Define la interfaz que deben implementar todos los clientes SNMP
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime


@dataclass
class SNMPResult:
    """Resultado de una consulta SNMP"""
    oid: str
    value: Any
    timestamp: datetime
    success: bool
    error_message: Optional[str] = None


@dataclass
class PrinterData:
    """Datos completos de una impresora"""
    printer_id: int
    printer_code: str
    ip_address: str
    timestamp: datetime
    
    # Contómetros
    total_impressions: Optional[int] = None
    bn_impressions: Optional[int] = None
    color_impressions: Optional[int] = None
    
    # Papel
    paper_sheets_available: Optional[int] = None
    paper_capacity: Optional[int] = None
    paper_level_percent: Optional[float] = None
    paper_alert_code: Optional[int] = None
    paper_alert_description: Optional[str] = None
    
    # Tóner (niveles raw y máximos)
    toner_black_level: Optional[int] = None
    toner_black_max: Optional[int] = None
    toner_cyan_level: Optional[int] = None
    toner_cyan_max: Optional[int] = None
    toner_magenta_level: Optional[int] = None
    toner_magenta_max: Optional[int] = None
    toner_yellow_level: Optional[int] = None
    toner_yellow_max: Optional[int] = None
    
    # Alertas generales
    alert_group: Optional[int] = None
    alert_code: Optional[int] = None
    alert_description: Optional[str] = None


class BaseSNMPClient(ABC):
    """Clase base abstracta para clientes SNMP"""
    
    def __init__(self, community: str = 'public', version: str = 'v2c', timeout: int = 5, retries: int = 2):
        self.community = community
        self.version = version
        self.timeout = timeout
        self.retries = retries
    
    @abstractmethod
    def connect(self, ip_address: str) -> bool:
        """Establece conexión con la impresora"""
        pass
    
    @abstractmethod
    def disconnect(self):
        """Cierra la conexión"""
        pass
    
    @abstractmethod
    def get_value(self, oid: str) -> SNMPResult:
        """Obtiene un valor SNMP específico"""
        pass
    
    @abstractmethod
    def get_values(self, oids: List[str]) -> Dict[str, SNMPResult]:
        """Obtiene múltiples valores SNMP en una sola consulta"""
        pass
    
    @abstractmethod
    def walk(self, oid: str) -> List[SNMPResult]:
        """Realiza un SNMP walk desde un OID raíz"""
        pass
    
    def is_available(self) -> bool:
        """Verifica si el cliente está disponible/conectado"""
        raise NotImplementedError


class SNMPOIDRegistry:
    """Registro de OIDs comunes para impresoras Ricoh y Kyocera"""
    
    # OIDs estándar MIB-II y Printer MIB (RFC 3805)
    PRINTER_MIB = "1.3.6.1.2.1.43"
    
    # Contómetros
    OID_TOTAL_IMPRESSIONS = f"{PRINTER_MIB}.10.2.1.4.1.1"  # Total de impresiones
    OID_BN_IMPRESSIONS = f"{PRINTER_MIB}.10.2.1.4.1.2"     # Impresiones monocromáticas
    OID_COLOR_IMPRESSIONS = f"{PRINTER_MIB}.10.2.1.4.1.3"  # Impresiones a color
    
    # Niveles de tóner (Supply)
    OID_TONER_LEVEL_TEMPLATE = f"{PRINTER_MIB}.11.1.1.9"   # Nivel actual
    OID_TONER_MAX_CAPACITY_TEMPLATE = f"{PRINTER_MIB}.11.1.1.7"  # Capacidad máxima
    
    # Estado de bandeja de papel
    OID_PAPER_LEVEL_TEMPLATE = f"{PRINTER_MIB}.8.2.1.10"   # Nivel actual de bandeja
    OID_PAPER_CAPACITY_TEMPLATE = f"{PRINTER_MIB}.8.2.1.12"  # Capacidad máxima
    
    # Alertas y errores
    OID_ALERT_GROUP = f"{PRINTER_MIB}.16.5.1.2"  # Grupo de alerta
    OID_ALERT_CODE = f"{PRINTER_MIB}.16.5.1.3"   # Código de alerta
    OID_ALERT_DESCRIPTION = f"{PRINTER_MIB}.16.5.1.4"  # Descripción
    
    # Información del dispositivo
    OID_DEVICE_NAME = f"{PRINTER_MIB}.15.1.1.5"  # Nombre del dispositivo
    OID_DEVICE_STATUS = f"{PRINTER_MIB}.15.1.1.3"  # Estado general
    
    # OIDs específicos Ricoh (empresarial)
    RICOH_ENTERPRISE = "1.3.6.1.4.1.36"
    
    # OIDs específicos Kyocera
    KYOCERA_ENTERPRISE = "1.3.6.1.4.1.1347"
    
    @classmethod
    def get_toner_oid(cls, color_index: int, is_max: bool = False) -> str:
        """
        Obtiene el OID para nivel de tóner por color
        color_index: 1=Black, 2=Cyan, 3=Magenta, 4=Yellow
        """
        base_oid = cls.OID_TONER_LEVEL_TEMPLATE if not is_max else cls.OID_TONER_MAX_CAPACITY_TEMPLATE
        return f"{base_oid}.{color_index}"
    
    @classmethod
    def get_paper_oid(cls, tray_index: int = 1, is_capacity: bool = False) -> str:
        """
        Obtiene el OID para nivel de papel
        tray_index: número de bandeja (generalmente 1)
        """
        base_oid = cls.OID_PAPER_CAPACITY_TEMPLATE if is_capacity else cls.OID_PAPER_LEVEL_TEMPLATE
        return f"{base_oid}.{tray_index}"
    
    @classmethod
    def get_printer_profile_oids(cls, brand: str, profile: str) -> Dict[str, str]:
        """
        Retorna los OIDs específicos según marca y perfil de impresora
        
        brand: 'RICOH', 'KYOCERA', 'OTHER'
        profile: 'mono_total', 'ricoh_color', 'kyocera_mono'
        """
        oids = {
            'total': cls.OID_TOTAL_IMPRESSIONS,
            'bn': cls.OID_BN_IMPRESSIONS if profile != 'mono_total' else cls.OID_TOTAL_IMPRESSIONS,
            'color': cls.OID_COLOR_IMPRESSIONS if 'color' in profile else None,
        }
        
        # Configurar índices de tóner según perfil
        if 'kyocera' in profile:
            # Kyocera usa índices diferentes
            oids['toner_indices'] = {'black': 1}
            oids['toner_unit'] = 'absolute'  # Kyocera usa conteo absoluto
        else:
            # Ricoh y otros usan porcentajes
            oids['toner_indices'] = {'black': 1, 'cyan': 2, 'magenta': 3, 'yellow': 4}
            oids['toner_unit'] = 'percent'
        
        return oids
