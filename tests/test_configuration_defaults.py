"""Regression checks for user-facing integration defaults."""

import importlib.util
import json
import struct
from pathlib import Path

import yaml

ROOT = Path(__file__).parents[1]
CONST = ROOT / "custom_components/vehicle_maintenance/const.py"
spec = importlib.util.spec_from_file_location("vehicle_maintenance_const", CONST)
const = importlib.util.module_from_spec(spec)
spec.loader.exec_module(const)


def test_new_vehicles_select_the_complete_catalog() -> None:
    assert const.DEFAULT_SERVICES == list(const.SERVICE_CATALOG)


def test_every_service_has_a_short_why_it_matters_bluf() -> None:
    for definition in const.SERVICE_CATALOG.values():
        bluf = definition.get("why")
        assert isinstance(bluf, str) and bluf.strip()
        assert len(bluf) <= 150


def test_modern_subaru_defaults_and_supported_icons() -> None:
    catalog = const.SERVICE_CATALOG

    assert catalog["oil_change"]["interval"] == 6000
    assert catalog["tire_rotation"]["interval"] == 6000
    assert catalog["spark_plugs"]["interval"] == 60000
    assert catalog["fuel_filter"]["interval"] == 72000
    assert catalog["coolant"]["initial_interval"] == 137500
    assert catalog["coolant"]["interval"] == 75000
    assert catalog["spark_plugs"]["icon"] == "mdi:flash"
    assert catalog["wheel_alignment"]["icon"] == "mdi:steering"


def test_service_selection_uses_a_persistent_multi_select_list() -> None:
    source = (ROOT / "custom_components/vehicle_maintenance/config_flow.py").read_text()

    assert "multiple=True" in source
    assert "mode=selector.SelectSelectorMode.LIST" in source
    assert "mode=selector.SelectSelectorMode.DROPDOWN" not in source
    assert "async_step_services" in source
    for group in (
        "scheduled_services",
        "inspection_services",
        "condition_services",
        "milestone_services",
    ):
        assert group in source


def test_batch_log_action_is_declared_for_home_assistant_and_the_card() -> None:
    component = ROOT / "custom_components/vehicle_maintenance"
    integration_source = (component / "__init__.py").read_text()
    service_actions = (component / "services.yaml").read_text()
    card_source = (component / "www/vehicle-maint-card.js").read_text()

    assert "log_maintenance_batch" in integration_source
    assert "log_maintenance_batch:" in service_actions
    assert '"log_maintenance_batch"' in card_source

    actions = yaml.safe_load(service_actions)
    options = actions["log_maintenance_batch"]["fields"]["services"]["selector"][
        "select"
    ]["options"]
    assert all(set(option) == {"label", "value"} for option in options)
    assert {option["value"] for option in options} == set(const.SERVICE_CATALOG)


def test_card_displays_the_why_it_matters_sensor_attribute() -> None:
    component = ROOT / "custom_components/vehicle_maintenance"
    sensor_source = (component / "sensor.py").read_text()
    card_source = (component / "www/vehicle-maint-card.js").read_text()

    assert '"why_it_matters": definition["why"]' in sensor_source
    assert "Why it matters" in card_source
    assert "attributes.why_it_matters" in card_source


def test_local_brand_icons_are_valid_png_sizes() -> None:
    brand = ROOT / "custom_components/vehicle_maintenance/brand"
    for filename, expected_size in (("icon.png", 256), ("icon@2x.png", 512)):
        payload = (brand / filename).read_bytes()
        assert payload.startswith(b"\x89PNG\r\n\x1a\n")
        width, height = struct.unpack(">II", payload[16:24])
        assert (width, height) == (expected_size, expected_size)


def test_manifest_classifies_each_config_entry_as_a_device() -> None:
    manifest = json.loads(
        (ROOT / "custom_components/vehicle_maintenance/manifest.json").read_text()
    )

    assert manifest["integration_type"] == "device"


def test_release_and_frontend_cache_versions_stay_aligned() -> None:
    component = ROOT / "custom_components/vehicle_maintenance"
    manifest = json.loads((component / "manifest.json").read_text())
    integration_source = (component / "__init__.py").read_text()
    card_source = (component / "www/vehicle-maint-card.js").read_text()

    version = manifest["version"]
    assert f'?v={version}"' in integration_source
    assert f'CARD_VERSION = "{version}"' in card_source


def test_service_actions_never_offer_not_set() -> None:
    services = (
        ROOT / "custom_components/vehicle_maintenance/services.yaml"
    ).read_text()

    assert "label: Not set" not in services
    assert "label: Never performed" in services
