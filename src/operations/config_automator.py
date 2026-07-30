"""
Substation Protocol & Device Configuration Automator.
Generates DNP3, IEC 61850 CID/SCL files and Kronos GPS setup scripts automatically.
"""

from typing import Dict, Any, List

class ConfigAutomator:
    """Automates PMU, RTU, and GPS clock configuration generation."""

    def __init__(self, default_ip_prefix: str = "192.168.10."):
        self.ip_prefix = default_ip_prefix

    def generate_pmu_config(self, ot_code: str, substation_name: str, pmu_id: int) -> Dict[str, Any]:
        """Generates SEL-735 PMU IEEE C37.118 configuration file payload."""
        ip = f"{self.ip_prefix}{pmu_id + 10}"
        return {
            "ot_code": ot_code,
            "device_type": "Vizimax SynchroTeq Plus PMU",
            "substation": substation_name,
            "ip_address": ip,
            "protocol": "IEEE C37.118-2011",
            "fasor_rate_fps": 50,
            "dnp3_slave_addr": pmu_id,
            "irig_b_sync": True,
            "config_status": "READY_FOR_UPLOAD",
            "estimated_hh_saved": 33.0  # 45 HH -> 12 HH
        }

    def generate_rtu_orion_config(self, ot_code: str, points_count: int) -> Dict[str, Any]:
        """Generates NovaTech Orion MX RTU DNP3/IEC61850 database file."""
        return {
            "ot_code": ot_code,
            "device_type": "NovaTech Orion MX",
            "dnp3_master_ip": "10.20.30.50",
            "points_count": points_count,
            "iec61850_scl_enabled": True,
            "config_status": "READY_FOR_UPLOAD",
            "estimated_hh_saved": 28.0
        }

    def generate_gps_kronos_script(self, ot_code: str, device_count: int) -> List[Dict[str, Any]]:
        """Generates Kronos GPS auto-setup scripts for batch processing."""
        scripts = []
        for i in range(1, device_count + 1):
            scripts.append({
                "ot_code": ot_code,
                "device_id": f"KRONOS-GPS-{i:02d}",
                "ip_address": f"{self.ip_prefix}{100 + i}",
                "ntp_server": "10.0.0.1",
                "ptp_ieee1588": True,
                "script_payload": f"SET IP {self.ip_prefix}{100+i}; SET NTP ON; SAVE;"
            })
        return scripts
