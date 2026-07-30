"""
Quantity Parser Module for Conecta Engineering Proposals & Inventories.
Extracts device quantities and Spanish number words while masking voltage and power ratings
(e.g., 220kV, 110kV, 9MW) to prevent false-positive device counts.
"""

import re
from typing import Dict, Any, Optional

VOLTAGE_POWER_PATTERN = re.compile(
    r'\b\d+(?:\.\d+)?\s*(?:kV|kVAC|kVDC|V|VAC|VDC|MW|kW|MVA|kVA|Hz)\b',
    re.IGNORECASE
)

SPANISH_NUMBER_WORDS: Dict[str, int] = {
    "un": 1,
    "una": 1,
    "uno": 1,
    "dos": 2,
    "tres": 3,
    "cuatro": 4,
    "cinco": 5,
    "seis": 6,
    "siete": 7,
    "ocho": 8,
    "nueve": 9,
    "diez": 10
}

_NUMBER_PATTERN_STR = r'(?:\b(?:un|una|uno|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez)\b|\b\d+(?:\.\d+)?\b)'


STOP_PHRASES_PATTERN = re.compile(
    r'\b(?:un|una|uno)\s+(?:cotizaci[oó]n|oferta|propuesta|licitaci[oó]n|rfp|proyecto|subestaci[oó]n|se|d[ií]as|semanas|meses|a[nñ]os|rev|revisi[oó]n)\b',
    re.IGNORECASE
)


class QuantityParser:
    """
    Parser for device quantities in unstructured commercial/technical prompt strings.
    Strips voltage, power specifications, and non-device stop-phrases before parsing numeric values.
    """

    VOLTAGE_POWER_PATTERN = VOLTAGE_POWER_PATTERN
    STOP_PHRASES_PATTERN = STOP_PHRASES_PATTERN
    SPANISH_NUMBER_WORDS = SPANISH_NUMBER_WORDS

    @classmethod
    def strip_voltage_and_power(cls, text: str) -> str:
        """
        Strips voltage/power expressions (e.g., '220kV') and non-device stop-phrases (e.g., 'una cotización').
        """
        if not text:
            return ""
        cleaned = cls.VOLTAGE_POWER_PATTERN.sub(" ", text)
        return cls.STOP_PHRASES_PATTERN.sub(" ", cleaned)

    @classmethod
    def parse_number_token(cls, token: str) -> Optional[float]:
        """
        Converts a string token (digit string or Spanish number word) to float.
        """
        token_lower = token.strip().lower()
        if token_lower in cls.SPANISH_NUMBER_WORDS:
            return float(cls.SPANISH_NUMBER_WORDS[token_lower])
        try:
            return float(token_lower)
        except ValueError:
            return None

    @classmethod
    def parse_quantities(cls, text: str) -> Dict[str, float]:
        """
        Extracts device quantities from text into a dictionary of device counts.
        Uses tight proximity patterns to avoid cross-contamination when multiple
        device types appear in the same sentence (e.g., '3 RTUs y 2 switches').
        """
        if not text:
            return {}

        cleaned_text = cls.strip_voltage_and_power(text)
        results: Dict[str, float] = {}

        device_mappings = [
            ("num_rtus",      ["rtus", "rtu", "orion", "remota", "remotas"]),
            ("num_switches",  ["switches", "switch", "belden", "hirschmann"]),
            ("num_pmus",      ["pmus", "pmu", "vizimax", "synchroteq"]),
            ("num_medidores", ["medidores", "medidor", "sel-735", "sel"]),
            ("num_reles",     ["relés", "reles", "relé", "rele"]),
            ("num_equipos",   ["equipos", "equipo"]),
        ]

        for key, synonyms in device_mappings:
            synonym_pattern = r'|'.join(re.escape(s) for s in synonyms)

            # Pattern 1: NUMBER immediately before device keyword (0-1 intermediate word max)
            # Tight: e.g. "3 RTUs", "3 remotas NovaTech"
            tight_pattern = re.compile(
                r'\b(' + _NUMBER_PATTERN_STR + r')\s+(?:\w+\s+){0,1}(' + synonym_pattern + r')\b',
                re.IGNORECASE
            )
            for num_str, _ in tight_pattern.findall(cleaned_text):
                val = cls.parse_number_token(num_str)
                if val is not None and val > 0:
                    results[key] = val
                    results[key.replace("num_", "")] = val
                    break

            if key in results:
                continue

            # Pattern 2: device=NUMBER assignment (e.g., "switches: 2")
            eq_pattern = re.compile(
                r'\b(' + synonym_pattern + r')\s*[:=]\s*(' + _NUMBER_PATTERN_STR + r')\b',
                re.IGNORECASE
            )
            for _, num_str in eq_pattern.findall(cleaned_text):
                val = cls.parse_number_token(num_str)
                if val is not None and val > 0:
                    results[key] = val
                    results[key.replace("num_", "")] = val
                    break

            if key in results:
                continue

            # Pattern 3: device keyword followed immediately by NUMBER
            # e.g. "remota 1", "PMU x3"
            reverse_pattern = re.compile(
                r'\b(' + synonym_pattern + r')\s*[xX]?\s*(' + _NUMBER_PATTERN_STR + r')\b',
                re.IGNORECASE
            )
            for _, num_str in reverse_pattern.findall(cleaned_text):
                val = cls.parse_number_token(num_str)
                if val is not None and val > 0:
                    results[key] = val
                    results[key.replace("num_", "")] = val
                    break

        # Fallback implicit count = 1.0 if device synonym exists in text without explicit number
        for key, synonyms in device_mappings:
            if key in results:
                continue
            synonym_pattern = r'|'.join(re.escape(s) for s in synonyms)
            if re.search(r'\b(' + synonym_pattern + r')\b', cleaned_text, re.IGNORECASE):
                results[key] = 1.0
                results[key.replace("num_", "")] = 1.0

        return results

    @classmethod
    def extract_device_quantity(cls, text: str, default: float = 1.0) -> float:
        """
        Extracts the main device quantity from text, ignoring voltage/power values.
        Returns default if no explicit quantity is found.
        """
        if not text:
            return default

        parsed = cls.parse_quantities(text)

        for key in ["num_rtus", "num_pmus", "num_remotas", "num_switches", "num_medidores", "num_reles", "num_equipos"]:
            if key in parsed and parsed[key] > 0:
                return parsed[key]

        if parsed:
            for val in parsed.values():
                if val > 0:
                    return val

        cleaned = cls.strip_voltage_and_power(text)
        pattern = re.compile(r'\b(' + _NUMBER_PATTERN_STR + r')\b', re.IGNORECASE)
        matches = pattern.findall(cleaned)
        for num_str in matches:
            val = cls.parse_number_token(num_str)
            if val is not None and val > 0:
                return val

        return default


def parse_quantities(text: str) -> Dict[str, float]:
    """Helper function wrapping QuantityParser.parse_quantities."""
    return QuantityParser.parse_quantities(text)


def extract_device_quantity(text: str, default: float = 1.0) -> float:
    """Helper function wrapping QuantityParser.extract_device_quantity."""
    return QuantityParser.extract_device_quantity(text, default=default)
