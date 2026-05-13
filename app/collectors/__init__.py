"""
Collectors Package - Módulos de recolección SNMP
"""
from .base_client import BaseSNMPClient, SNMPResult, PrinterData, SNMPOIDRegistry
from .snmp_client import PySNMPClient, get_snmp_client
from .counter_collector import collect_counters, test_single_printer
from .paper_collector import collect_paper
from .toner_collector import collect_toner

__all__ = [
    'BaseSNMPClient',
    'SNMPResult',
    'PrinterData',
    'SNMPOIDRegistry',
    'PySNMPClient',
    'get_snmp_client',
    'collect_counters',
    'test_single_printer',
    'collect_paper',
    'collect_toner',
]
