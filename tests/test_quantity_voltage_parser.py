import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from src.operations.quantity_parser import (
    QuantityParser,
    parse_quantities,
    extract_device_quantity,
    VOLTAGE_POWER_PATTERN,
    SPANISH_NUMBER_WORDS,
)


def test_voltage_and_power_stripping():
    sample_text = "Subestación Ancud 220kV, línea 110kV, transformador 500kV, 13.8kV, generador 9MW, 15kW, 24VDC, 50Hz"
    stripped = QuantityParser.strip_voltage_and_power(sample_text)

    assert "220" not in stripped
    assert "110" not in stripped
    assert "500" not in stripped
    assert "13.8" not in stripped
    assert "9" not in stripped
    assert "15" not in stripped
    assert "24" not in stripped
    assert "50" not in stripped


def test_spanish_number_words_mapping():
    assert SPANISH_NUMBER_WORDS["dos"] == 2
    assert SPANISH_NUMBER_WORDS["tres"] == 3
    assert SPANISH_NUMBER_WORDS["cuatro"] == 4
    assert SPANISH_NUMBER_WORDS["un"] == 1
    assert SPANISH_NUMBER_WORDS["una"] == 1
    assert SPANISH_NUMBER_WORDS["diez"] == 10


def test_complex_voltage_quantity_parsing():
    prompt = "Cotizar dos RTUs Novatech Orion LX+ y tres switches Belden en SE Ancud 220kV"

    parsed = parse_quantities(prompt)
    assert parsed.get("num_rtus") == 2.0
    assert parsed.get("num_switches") == 3.0

    dev_qty = extract_device_quantity(prompt)
    assert dev_qty == 2.0
    assert dev_qty != 220.0


def test_extract_device_quantity_defaults():
    prompt_voltage_only = "Cotización para Subestación Ancud 220kV"
    qty = extract_device_quantity(prompt_voltage_only, default=1.0)
    assert qty == 1.0

    prompt_pmu = "Requiero cuatro PMUs Vizimax en SE Ancoa 500kV"
    qty_pmu = extract_device_quantity(prompt_pmu)
    assert qty_pmu == 4.0


def test_cotizacion_inventario_integration():
    from src.swarm_engine.agents.cotizacion_inventario import CotizacionInventarioAgent

    agent = CotizacionInventarioAgent()
    prompt = "Cotizar tres RTUs Novatech Orion LX+ en SE Ancud 220kV"
    action = agent.guide_quotation(prompt_or_line=prompt, user_params={"prompt": prompt})

    assert action.target_model == "sale.order"
    lines = action.proposed_payload["order_line"]
    rtu_lines = [l for l in lines if "rtu" in l["item_code"].lower() or "pmu" in l["item_code"].lower()]
    assert len(rtu_lines) > 0
    assert rtu_lines[0]["product_uom_qty"] == 3.0


# =====================================================================
# EXPANDED EDGE CASE & PARAMETERIZED TEST SUITE FOR QUANTITY PARSER
# =====================================================================

@pytest.mark.parametrize("voltage_str, expected_absent", [
    ("Línea 500kV/220kV/13.8kV", ["500", "220", "13.8"]),
    ("Alimentador 440VAC y banco 110kVDC", ["440", "110"]),
    ("Central Hídrica 66kV / 23kV", ["66", "23"]),
    ("Generación 9MW / 15kW / 50MVA", ["9", "15", "50"]),
    ("Sistema 50Hz con auxiliar 24VDC", ["50", "24"]),
    ("Transformador 10kVA a 380V", ["10", "380"]),
])
def test_mixed_voltage_and_power_ratings_stripping(voltage_str, expected_absent):
    stripped = QuantityParser.strip_voltage_and_power(voltage_str)
    for val in expected_absent:
        assert val not in stripped


@pytest.mark.parametrize("prompt, expected_rtus, expected_pmus, expected_switches", [
    ("Cotizar dos RTUs y 3 PMUs en SE San Clemente 220kV", 2.0, 3.0, None),
    ("Requiero cinco RTUs, una PMU y 4 switches Belden", 5.0, 1.0, 4.0),
    ("Instalar 1 RTU NovaTech y 6 switches industrial 110kV", 1.0, None, 6.0),
    ("Proveer tres PMUs Vizimax y 2 RTUs Orion MX", 2.0, 3.0, None),
    ("Cuatro RTUs y diez medidores en Subestación Ancud", 4.0, None, None),
])
def test_combined_spanish_numbers_and_digits(prompt, expected_rtus, expected_pmus, expected_switches):
    parsed = parse_quantities(prompt)
    if expected_rtus is not None:
        assert parsed.get("num_rtus") == expected_rtus
    if expected_pmus is not None:
        assert parsed.get("num_pmus") == expected_pmus
    if expected_switches is not None:
        assert parsed.get("num_switches") == expected_switches


@pytest.mark.parametrize("word, expected_val", [
    ("un", 1.0),
    ("una", 1.0),
    ("uno", 1.0),
    ("dos", 2.0),
    ("tres", 3.0),
    ("cuatro", 4.0),
    ("cinco", 5.0),
    ("seis", 6.0),
    ("siete", 7.0),
    ("ocho", 8.0),
    ("nueve", 9.0),
    ("diez", 10.0),
])
def test_all_spanish_number_words_tokens(word, expected_val):
    assert QuantityParser.parse_number_token(word) == expected_val
    assert QuantityParser.parse_number_token(word.upper()) == expected_val


@pytest.mark.parametrize("prompt, expected_parsed_key, expected_val", [
    ("RTU: 4 unidades en SE Ancoa 500kV", "num_rtus", 4.0),
    ("switches = 5 para gabinete SCADA", "num_switches", 5.0),
    ("PMUs: dos para medición fasorial", "num_pmus", 2.0),
    ("medidores = tres SEL-735 en 110kV", "num_medidores", 3.0),
    ("relés: 6 SEL-421 en tablero de control", "num_reles", 6.0),
])
def test_colon_and_equals_parsing_syntax(prompt, expected_parsed_key, expected_val):
    parsed = parse_quantities(prompt)
    assert parsed.get(expected_parsed_key) == expected_val


@pytest.mark.parametrize("input_text, default_val, expected_output", [
    ("", 1.0, 1.0),
    ("", 5.0, 5.0),
    ("Subestación sin equipos especificados 220kV 50Hz", 1.0, 1.0),
    ("Solamente texto técnico sin números", 2.5, 2.5),
    ("Cinco equipos de comunicación 66kV", 1.0, 5.0),
])
def test_extract_device_quantity_boundary_defaults(input_text, default_val, expected_output):
    res = extract_device_quantity(input_text, default=default_val)
    assert res == expected_output


def test_parse_number_token_invalid_strings():
    assert QuantityParser.parse_number_token("abc") is None
    assert QuantityParser.parse_number_token("12.3.4") is None
    assert QuantityParser.parse_number_token("") is None
