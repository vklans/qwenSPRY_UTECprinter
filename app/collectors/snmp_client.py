"""
SNMP Client - Implementación con pysnmp
Cliente SNMP para consultas directas desde el servidor
"""
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

try:
    from pysnmp.hlapi import (
        SnmpEngine, UdpTransportTarget, ContextData,
        ObjectType, ObjectIdentity,
        getCmd, bulkCmd
    )
    from pysnmp.proto.rfc1902 import OctetString, Integer, Counter32, Counter64
    PYSNMP_AVAILABLE = True
except ImportError:
    PYSNMP_AVAILABLE = False

from .base_client import BaseSNMPClient, SNMPResult, PrinterData, SNMPOIDRegistry

logger = logging.getLogger(__name__)


class PySNMPClient(BaseSNMPClient):
    """Cliente SNMP implementado con pysnmp"""
    
    def __init__(self, community: str = 'public', version: str = 'v2c', 
                 timeout: int = 5, retries: int = 2):
        if not PYSNMP_AVAILABLE:
            raise ImportError("pysnmp no está instalado. Ejecuta: pip install pysnmp")
        
        super().__init__(community, version, timeout, retries)
        self.snmp_engine = SnmpEngine()
        self._current_target = None
    
    def connect(self, ip_address: str) -> bool:
        """Establece conexión con la impresora"""
        try:
            self._current_target = UdpTransportTarget(
                (ip_address, 161),
                timeout=self.timeout,
                retries=self.retries
            )
            logger.debug(f"Conectado a {ip_address}")
            return True
        except Exception as e:
            logger.error(f"Error al conectar a {ip_address}: {e}")
            return False
    
    def disconnect(self):
        """Cierra la conexión (limpia el target actual)"""
        self._current_target = None
        logger.debug("Conexión cerrada")
    
    def _get_auth_data(self):
        """Obtiene los datos de autenticación según versión SNMP"""
        if self.version == 'v2c':
            from pysnmp.hlapi import CommunityData
            return CommunityData(self.community, mpModel=1)
        elif self.version == 'v1':
            from pysnmp.hlapi import CommunityData
            return CommunityData(self.community, mpModel=0)
        else:
            # SNMPv3 (no implementado por ahora)
            raise NotImplementedError("SNMPv3 no soportado aún")
    
    def _convert_value(self, value: Any) -> Any:
        """Convierte valores SNMP a tipos Python nativos"""
        if value is None:
            return None
        
        if isinstance(value, (Counter32, Counter64, Integer)):
            return int(value)
        elif isinstance(value, OctetString):
            return str(value).strip("'")
        else:
            return value
    
    def get_value(self, oid: str) -> SNMPResult:
        """Obtiene un valor SNMP específico"""
        if not self._current_target:
            return SNMPResult(
                oid=oid,
                value=None,
                timestamp=datetime.now(),
                success=False,
                error_message="No hay conexión activa"
            )
        
        try:
            iterator = getCmd(
                self.snmp_engine,
                self._get_auth_data(),
                self._current_target,
                ContextData(),
                ObjectType(ObjectIdentity(oid))
            )
            
            response = next(iterator)
            
            if response[2]:  # Error en la consulta
                error_msg = f"SNMP Error: {response[2]}"
                logger.warning(error_msg)
                return SNMPResult(
                    oid=oid,
                    value=None,
                    timestamp=datetime.now(),
                    success=False,
                    error_message=error_msg
                )
            
            if response[3]:  # Respuesta exitosa
                var_bind = response[3][0]
                value = self._convert_value(var_bind[1])
                logger.debug(f"OID {oid} = {value}")
                
                return SNMPResult(
                    oid=oid,
                    value=value,
                    timestamp=datetime.now(),
                    success=True
                )
            
            return SNMPResult(
                oid=oid,
                value=None,
                timestamp=datetime.now(),
                success=False,
                error_message="Respuesta vacía"
            )
            
        except Exception as e:
            error_msg = f"Excepción al consultar OID {oid}: {str(e)}"
            logger.error(error_msg)
            return SNMPResult(
                oid=oid,
                value=None,
                timestamp=datetime.now(),
                success=False,
                error_message=error_msg
            )
    
    def get_values(self, oids: List[str]) -> Dict[str, SNMPResult]:
        """Obtiene múltiples valores SNMP en una sola consulta"""
        if not self._current_target or not oids:
            return {oid: SNMPResult(oid=oid, value=None, timestamp=datetime.now(), 
                                   success=False, error_message="Sin conexión o OIDs vacíos") 
                    for oid in oids}
        
        try:
            object_types = [ObjectType(ObjectIdentity(oid)) for oid in oids]
            
            iterator = getCmd(
                self.snmp_engine,
                self._get_auth_data(),
                self._current_target,
                ContextData(),
                *object_types
            )
            
            response = next(iterator)
            results = {}
            
            if response[2]:  # Error en la consulta
                error_msg = f"SNMP Error: {response[2]}"
                logger.warning(error_msg)
                for oid in oids:
                    results[oid] = SNMPResult(
                        oid=oid,
                        value=None,
                        timestamp=datetime.now(),
                        success=False,
                        error_message=error_msg
                    )
                return results
            
            if response[3]:  # Respuesta exitosa
                for i, var_bind in enumerate(response[3]):
                    oid = oids[i] if i < len(oids) else str(var_bind[0])
                    value = self._convert_value(var_bind[1])
                    results[oid] = SNMPResult(
                        oid=oid,
                        value=value,
                        timestamp=datetime.now(),
                        success=True
                    )
                
                # Manejar caso donde haya menos respuestas que OIDs solicitados
                for i in range(len(results), len(oids)):
                    oid = oids[i]
                    results[oid] = SNMPResult(
                        oid=oid,
                        value=None,
                        timestamp=datetime.now(),
                        success=False,
                        error_message="Sin respuesta"
                    )
                
                return results
            
            # Respuesta vacía
            for oid in oids:
                results[oid] = SNMPResult(
                    oid=oid,
                    value=None,
                    timestamp=datetime.now(),
                    success=False,
                    error_message="Respuesta vacía"
                )
            return results
            
        except Exception as e:
            error_msg = f"Excepción en consulta múltiple: {str(e)}"
            logger.error(error_msg)
            return {oid: SNMPResult(oid=oid, value=None, timestamp=datetime.now(),
                                   success=False, error_message=error_msg) 
                    for oid in oids}
    
    def walk(self, oid: str) -> List[SNMPResult]:
        """Realiza un SNMP walk desde un OID raíz"""
        if not self._current_target:
            return [SNMPResult(oid=oid, value=None, timestamp=datetime.now(),
                              success=False, error_message="No hay conexión activa")]
        
        try:
            results = []
            iterator = bulkCmd(
                self.snmp_engine,
                self._get_auth_data(),
                self._current_target,
                ContextData(),
                0,  # non-repeaters
                10, # max-repetitions
                ObjectType(ObjectIdentity(oid)),
                lexicographicMode=True
            )
            
            for response in iterator:
                if response[2]:  # Error
                    logger.warning(f"Error en SNMP walk: {response[2]}")
                    break
                
                for var_bind in response[3]:
                    oid_result = str(var_bind[0])
                    value = self._convert_value(var_bind[1])
                    results.append(SNMPResult(
                        oid=oid_result,
                        value=value,
                        timestamp=datetime.now(),
                        success=True
                    ))
            
            logger.debug(f"SNMP walk completado: {len(results)} resultados")
            return results
            
        except Exception as e:
            error_msg = f"Excepción en SNMP walk: {str(e)}"
            logger.error(error_msg)
            return [SNMPResult(oid=oid, value=None, timestamp=datetime.now(),
                              success=False, error_message=error_msg)]
    
    def is_available(self) -> bool:
        """Verifica si el cliente está disponible"""
        return self._current_target is not None and PYSNMP_AVAILABLE
    
    def test_connection(self, ip_address: str) -> bool:
        """Prueba de conectividad básica consultando sysDescr"""
        try:
            if not self.connect(ip_address):
                return False
            
            # Consultar sysDescr (1.3.6.1.2.1.1.1.0) como prueba
            result = self.get_value("1.3.6.1.2.1.1.1.0")
            self.disconnect()
            
            if result.success:
                logger.info(f"Conexión exitosa a {ip_address}: {result.value[:50]}...")
                return True
            else:
                logger.warning(f"Conexión fallida a {ip_address}: {result.error_message}")
                return False
                
        except Exception as e:
            logger.error(f"Error en prueba de conexión: {e}")
            self.disconnect()
            return False
    
    def collect_printer_data(self, printer_id: int, printer_code: str, 
                            ip_address: str, brand: str, profile: str,
                            paper_capacity: int = 500) -> Optional[PrinterData]:
        """
        Recolecta todos los datos de una impresora en una sola sesión
        
        Returns: PrinterData con toda la información o None si falla
        """
        if not self.connect(ip_address):
            return None
        
        try:
            # Obtener OIDs según perfil
            oids_config = SNMPOIDRegistry.get_printer_profile_oids(brand, profile)
            
            # Construir lista de OIDs a consultar
            oids_to_query = [
                oids_config['total'],
                oids_config['bn']
            ]
            
            if oids_config.get('color'):
                oids_to_query.append(oids_config['color'])
            
            # Agregar tóner según configuración
            toner_indices = oids_config.get('toner_indices', {})
            for color, idx in toner_indices.items():
                oids_to_query.append(SNMPOIDRegistry.get_toner_oid(idx, is_max=False))
                oids_to_query.append(SNMPOIDRegistry.get_toner_oid(idx, is_max=True))
            
            # Agregar papel y alertas
            oids_to_query.extend([
                SNMPOIDRegistry.get_paper_oid(1, is_capacity=False),
                SNMPOIDRegistry.OID_ALERT_CODE,
                SNMPOIDRegistry.OID_ALERT_DESCRIPTION
            ])
            
            # Consultar todos los valores
            results = self.get_values(oids_to_query)
            
            # Procesar resultados
            data = PrinterData(
                printer_id=printer_id,
                printer_code=printer_code,
                ip_address=ip_address,
                timestamp=datetime.now()
            )
            
            # Extraer contómetros
            if results.get(oids_config['total'], {}).success:
                data.total_impressions = results[oids_config['total']].value
            
            if results.get(oids_config['bn'], {}).success:
                data.bn_impressions = results[oids_config['bn']].value
            
            if oids_config.get('color') and results.get(oids_config['color'], {}).success:
                data.color_impressions = results[oids_config['color']].value
            
            # Extraer tóner
            toner_colors = ['black', 'cyan', 'magenta', 'yellow']
            for i, color in enumerate(toner_colors, start=1):
                if color in toner_indices:
                    idx = toner_indices[color]
                    level_oid = SNMPOIDRegistry.get_toner_oid(idx, is_max=False)
                    max_oid = SNMPOIDRegistry.get_toner_oid(idx, is_max=True)
                    
                    if results.get(level_oid, {}).success:
                        setattr(data, f'toner_{color}_level', results[level_oid].value)
                    if results.get(max_oid, {}).success:
                        setattr(data, f'toner_{color}_max', results[max_oid].value)
            
            # Extraer papel
            paper_oid = SNMPOIDRegistry.get_paper_oid(1, is_capacity=False)
            if results.get(paper_oid, {}).success:
                data.paper_sheets_available = results[paper_oid].value
                data.paper_capacity = paper_capacity
                if data.paper_sheets_available and data.paper_capacity:
                    data.paper_level_percent = round(
                        (data.paper_sheets_available / data.paper_capacity) * 100, 2
                    )
            
            # Extraer alertas
            if results.get(SNMPOIDRegistry.OID_ALERT_CODE, {}).success:
                data.alert_code = results[SNMPOIDRegistry.OID_ALERT_CODE].value
            if results.get(SNMPOIDRegistry.OID_ALERT_DESCRIPTION, {}).success:
                data.alert_description = results[SNMPOIDRegistry.OID_ALERT_DESCRIPTION].value
            
            self.disconnect()
            return data
            
        except Exception as e:
            logger.error(f"Error al recolectar datos de {printer_code}: {e}")
            self.disconnect()
            return None


# Factory function para obtener el cliente adecuado
def get_snmp_client(source: str = 'local_snmp', **kwargs) -> BaseSNMPClient:
    """
    Factory para crear el cliente SNMP apropiado
    
    source: 'local_snmp' (pysnmp directo) o 'api' (consulta a API remota)
    """
    if source == 'local_snmp':
        return PySNMPClient(**kwargs)
    else:
        # En el futuro se podría implementar APIClient para modo laptop
        raise ValueError(f"Fuente SNMP desconocida: {source}")
