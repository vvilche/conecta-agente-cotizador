"""
Operations Software Engine & Automation Capabilities.
Includes:
- ConfigAutomator: DNP3/IEC61850 configuration generator.
- FatSatSimulator: Digital FAT/SAT testing & protocol generator.
- KittingEngine: Standardized BOM assembly kit generator.
- DocAutomator: Automatic engineering handover & protocol document generator.
- PaymentStatementAutomator: Automatic Payment Milestone (Estado de Pago) generator.
- AccreditationAutomator: Subcontractor & Personnel Accreditation Dossier compiler.
"""

from .config_automator import ConfigAutomator
from .fat_sat_simulator import FatSatSimulator
from .kitting_engine import KittingEngine
from .doc_automator import DocAutomator
from .payment_statement_automator import PaymentStatementAutomator
from .accreditation_automator import AccreditationAutomator
from .financial_engine import FinancialImpactEngine
from .quantity_parser import QuantityParser, parse_quantities, extract_device_quantity
from .official_word_quote_builder import OfficialWordQuoteBuilder

__all__ = [
    "ConfigAutomator",
    "FatSatSimulator",
    "KittingEngine",
    "DocAutomator",
    "PaymentStatementAutomator",
    "AccreditationAutomator",
    "FinancialImpactEngine",
    "QuantityParser",
    "parse_quantities",
    "extract_device_quantity",
    "OfficialWordQuoteBuilder"
]



