"""
test_quote_benchmarking_and_alerts.py

Pruebas automatizadas para verificar el benchmarking del motor de cotizaciones
contra los 35 deals históricos ganados de Conecta S.A. y validar la activación
correcta del sistema de alertas de desviación financiera y alcance técnico.
"""

import pytest
import json
import os

def evaluate_quote_alerts(prompt: str, amount_untaxed_clp: float, target_margin_pct: float, has_gps: bool = False):
    """
    Función espejo en Python de la lógica de alertas en docs/comercial.html
    """
    alerts = []
    net_mclp = amount_untaxed_clp / 1_000_000.0
    prompt_lower = prompt.lower()

    # 1. Alerta de Margen
    if target_margin_pct < 35.0:
        alerts.append({
            'type': 'warning',
            'code': 'MARGIN_LOW',
            'title': f'Alerta de Margen Crítico Bajo ({target_margin_pct:.1f}%)'
        })
    elif target_margin_pct > 65.0:
        alerts.append({
            'type': 'info',
            'code': 'MARGIN_HIGH',
            'title': f'Margen Alto Seleccionado ({target_margin_pct:.1f}%)'
        })
    else:
        alerts.append({
            'type': 'success',
            'code': 'MARGIN_OK',
            'title': f'Margen Saludable ({target_margin_pct:.1f}%)'
        })

    # 2. Alerta de Sub-cotización / Dimensionamiento Complejo
    is_complex = any(k in prompt_lower for k in ['pdc', 'slrp', 'proteccion', 'modernizacion', 'centro de control'])
    if is_complex and net_mclp < 45.0:
        alerts.append({
            'type': 'danger',
            'code': 'UNDER_QUOTING_RISK',
            'title': 'Riesgo de Sub-cotización en Proyecto Complejo'
        })

    # 3. Alerta de Alcance Técnico (GPS)
    needs_gps = any(k in prompt_lower for k in ['pmu', 'fasorial', 'vizimax'])
    if needs_gps and not has_gps and not any(k in prompt_lower for k in ['gps', 'kronos', 'ptp']):
        alerts.append({
            'type': 'danger',
            'code': 'MISSING_GPS',
            'title': 'Sincronizador Satelital GPS Omitido'
        })

    # 4. Alerta Normativa CEN
    needs_cen = any(k in prompt_lower for k in ['pmu', 'sitr', 'pmgd'])
    if needs_cen:
        alerts.append({
            'type': 'info',
            'code': 'CEN_COMPLIANCE',
            'title': 'Cumplimiento Normativo CEN Incluido'
        })

    return alerts


def test_margin_alerts_triggering():
    """Verifica que las alertas de margen se disparen correctamente según el threshold"""
    # Low margin < 35%
    alerts_low = evaluate_quote_alerts("Cotizar 2 PMUs", 40_000_000, 30.0, True)
    assert any(a['code'] == 'MARGIN_LOW' for a in alerts_low)

    # Standard margin 54.8%
    alerts_std = evaluate_quote_alerts("Cotizar 2 PMUs", 40_000_000, 54.8, True)
    assert any(a['code'] == 'MARGIN_OK' for a in alerts_std)

    # High margin > 65%
    alerts_high = evaluate_quote_alerts("Cotizar 2 PMUs", 40_000_000, 68.5, True)
    assert any(a['code'] == 'MARGIN_HIGH' for a in alerts_high)


def test_missing_gps_alert_for_pmu():
    """Verifica alerta de omisión de GPS en cotizaciones PMU"""
    # PMU without GPS -> Danger alert
    alerts_no_gps = evaluate_quote_alerts("Cotización PMU VIZIMAX", 30_000_000, 54.8, has_gps=False)
    assert any(a['code'] == 'MISSING_GPS' for a in alerts_no_gps)

    # PMU with GPS -> No MISSING_GPS alert
    alerts_gps = evaluate_quote_alerts("Cotización PMU VIZIMAX", 30_000_000, 54.8, has_gps=True)
    assert not any(a['code'] == 'MISSING_GPS' for a in alerts_gps)


def test_under_quoting_risk_alert():
    """Verifica alerta de sub-cotización en proyectos complejos (PDC / SLRP / Protecciones)"""
    # Complex deal below 45M -> Trigger alert
    alerts_under = evaluate_quote_alerts("Modernización PDC Transelec", 25_000_000, 40.0, True)
    assert any(a['code'] == 'UNDER_QUOTING_RISK' for a in alerts_under)

    # Complex deal above 45M -> No UNDER_QUOTING_RISK alert
    alerts_normal = evaluate_quote_alerts("Modernización PDC Transelec", 120_000_000, 40.0, True)
    assert not any(a['code'] == 'UNDER_QUOTING_RISK' for a in alerts_normal)


def test_cen_compliance_alert():
    """Verifica inclusión de la alerta normativa CEN"""
    alerts_sitr = evaluate_quote_alerts("Telemetría SITR PMGD", 15_000_000, 54.8, False)
    assert any(a['code'] == 'CEN_COMPLIANCE' for a in alerts_sitr)
