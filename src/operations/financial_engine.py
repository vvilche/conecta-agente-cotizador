"""
Financial Impact & Operations ROI Engine.
Calculates retained gross margin (54.8%), released man-hours (HH),
reduced field commissioning days, and total financial impact in CLP.
"""

from typing import Dict, Any

class FinancialImpactEngine:
    """Calculates financial ROI, retained gross margin, and operational savings for OT projects."""

    RETAINED_GROSS_MARGIN_PCT: float = 54.8

    def retained_gross_margin_pct(self) -> float:
        """Returns the strictly required gross margin retention percentage (54.8%)."""
        return self.RETAINED_GROSS_MARGIN_PCT

    def calculate_released_man_hours(self, num_ots: int, num_devices: int = 1, num_workers: int = 1) -> Dict[str, Any]:
        """
        Calculates total released man-hours (HH) across operations:
        - Handover & protocol doc generation (7.0 HH / OT)
        - Virtual FAT/SAT lab testing (12.0 HH / device)
        - Panel pre-kitting & workshop assembly (25.0 HH / OT)
        - Personnel & subcontractor accreditation (17.5 HH / worker)
        - Automated payment statement & invoice processing (5.0 HH / OT)
        """
        num_ots = max(0, int(num_ots))
        num_devices = max(0, int(num_devices))
        num_workers = max(0, int(num_workers))

        doc_generation_hh = num_ots * 7.0
        fat_sat_lab_hh = num_devices * 12.0
        panel_kitting_hh = num_ots * 25.0
        accreditation_hh = num_workers * 17.5
        payment_statements_hh = num_ots * 5.0

        total_released_hh = doc_generation_hh + fat_sat_lab_hh + panel_kitting_hh + accreditation_hh + payment_statements_hh

        return {
            "num_ots": num_ots,
            "num_devices": num_devices,
            "num_workers": num_workers,
            "doc_generation_hh": doc_generation_hh,
            "fat_sat_lab_hh": fat_sat_lab_hh,
            "panel_kitting_hh": panel_kitting_hh,
            "accreditation_hh": accreditation_hh,
            "payment_statements_hh": payment_statements_hh,
            "total_released_hh": total_released_hh
        }

    def calculate_reduced_field_days(self, num_ots: int, num_substations: int = 1) -> Dict[str, Any]:
        """
        Calculates field commissioning days saved by performing digital lab FAT/SAT.
        Standard baseline: 5 field days reduced to 1.5 field days = 3.5 days saved per OT / substation.
        """
        num_ots = max(0, int(num_ots))
        num_substations = max(0, int(num_substations))

        days_saved_per_ot = 3.5
        total_reduced_field_days = num_ots * days_saved_per_ot

        return {
            "num_ots": num_ots,
            "num_substations": num_substations,
            "days_saved_per_ot": days_saved_per_ot,
            "total_reduced_field_days": total_reduced_field_days
        }

    def calculate_financial_summary(
        self,
        num_ots: int,
        total_contract_uf: float,
        uf_value_clp: float = 38377.09,
        num_devices: int = 1,
        num_workers: int = 1,
        num_substations: int = 1
    ) -> Dict[str, Any]:
        """
        Returns financial summary:
        - Total contract in CLP
        - Retained gross margin in CLP (at 54.8%)
        - Total savings in CLP (engineering HH savings + field logistic savings)
        - Released man-hours (HH)
        - Reduced field commissioning days
        """
        num_ots = max(0, int(num_ots))
        total_contract_uf = max(0.0, float(total_contract_uf))
        uf_value_clp = max(0.0, float(uf_value_clp))
        num_devices = max(0, int(num_devices))
        num_workers = max(0, int(num_workers))
        num_substations = max(0, int(num_substations))

        contract_clp = total_contract_uf * uf_value_clp
        retained_margin_pct = self.retained_gross_margin_pct()
        retained_gross_margin_clp = contract_clp * (retained_margin_pct / 100.0)

        released_hh_data = self.calculate_released_man_hours(num_ots, num_devices, num_workers)
        reduced_days_data = self.calculate_reduced_field_days(num_ots, num_substations)

        released_hh = released_hh_data["total_released_hh"]
        reduced_field_days = reduced_days_data["total_reduced_field_days"]

        # Hourly rate for engineering HH saved: CLP 35,000 / HH
        engineering_savings_clp = released_hh * 35000.0
        # Field day logistics saved: CLP 450,000 / field day
        field_savings_clp = reduced_field_days * 450000.0

        total_savings_clp = engineering_savings_clp + field_savings_clp

        return {
            "num_ots": num_ots,
            "total_contract_uf": total_contract_uf,
            "uf_value_clp": uf_value_clp,
            "total_contract_clp": round(contract_clp, 2),
            "retained_gross_margin_pct": retained_margin_pct,
            "retained_gross_margin_clp": round(retained_gross_margin_clp, 2),
            "total_savings_clp": round(total_savings_clp, 2),
            "released_hh": released_hh,
            "reduced_field_days": reduced_field_days,
            "released_man_hours_breakdown": released_hh_data,
            "reduced_field_days_breakdown": reduced_days_data
        }
